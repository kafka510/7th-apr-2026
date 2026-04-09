import { useState, useEffect, useMemo } from 'react';
import { fetchPrGapData, fetchLossCalculationData } from '../api';
import type { PrGapData, LossCalculationData, PrGapFilters, PrGapFilterOptions, PrGapDataPoint } from '../types';

interface UsePrGapDataReturn {
  prData: PrGapData[];
  lossData: LossCalculationData[];
  filterOptions: PrGapFilterOptions;
  filteredData: PrGapDataPoint[];
  loading: boolean;
  error: Error | null;
}

const MONTH_LOOKUP: Record<string, string> = {
  jan: '01',
  feb: '02',
  mar: '03',
  apr: '04',
  may: '05',
  jun: '06',
  jul: '07',
  aug: '08',
  sep: '09',
  oct: '10',
  nov: '11',
  dec: '12',
};

function normalizeMonthValue(value: string | null | undefined): string | null {
  if (!value) return null;
  const raw = String(value).trim();
  if (!raw) return null;

  const yyyymmMatch = raw.match(/^(\d{4})[-/](\d{1,2})/);
  if (yyyymmMatch) {
    const year = yyyymmMatch[1];
    const month = yyyymmMatch[2].padStart(2, '0');
    const monthNum = Number(month);
    if (monthNum >= 1 && monthNum <= 12) {
      return `${year}-${month}`;
    }
  }

  const mmyyyyMatch = raw.match(/^(\d{1,2})[-/](\d{4})/);
  if (mmyyyyMatch) {
    const month = mmyyyyMatch[1].padStart(2, '0');
    const year = mmyyyyMatch[2];
    const monthNum = Number(month);
    if (monthNum >= 1 && monthNum <= 12) {
      return `${year}-${month}`;
    }
  }

  const monthNameMatch = raw.match(/^([A-Za-z]{3,9})[-/\s](\d{2,4})$/);
  if (monthNameMatch) {
    const monthName = monthNameMatch[1].slice(0, 3).toLowerCase();
    const month = MONTH_LOOKUP[monthName];
    if (month) {
      const yearRaw = monthNameMatch[2];
      const year = yearRaw.length === 2 ? `20${yearRaw}` : yearRaw;
      return `${year}-${month}`;
    }
  }

  const yearNameMatch = raw.match(/^(\d{2,4})[-/\s]([A-Za-z]{3,9})$/);
  if (yearNameMatch) {
    const yearRaw = yearNameMatch[1];
    const year = yearRaw.length === 2 ? `20${yearRaw}` : yearRaw;
    const monthName = yearNameMatch[2].slice(0, 3).toLowerCase();
    const month = MONTH_LOOKUP[monthName];
    if (month) {
      return `${year}-${month}`;
    }
  }

  return null;
}

function isInSelectedMonth(
  rowMonth: string | null | undefined,
  selectedMonth: string | null,
  selectedYear: string | null,
  selectedRange: { start: string; end: string } | null | undefined
): boolean {
  const monthStr = normalizeMonthValue(rowMonth);
  if (!monthStr) return false;

  if (selectedRange) {
    return monthStr >= selectedRange.start && monthStr <= selectedRange.end;
  } else if (selectedYear) {
    return monthStr.slice(0, 4) === String(selectedYear);
  } else if (selectedMonth) {
    return monthStr === selectedMonth;
  }

  return false;
}

function aggregateDataByYear(data: PrGapData[], selectedYear: string): PrGapData[] {
  const yearData: Record<string, { totalGap: number; count: number; totalDc: number; dcCount: number; months: Set<string> }> = {};

  data.forEach((row) => {
    const monthStr = normalizeMonthValue(row.month);
    if (monthStr && monthStr.slice(0, 4) === selectedYear) {
      const asset = row.asset_no || row.assetno || row.asset || 'Unknown';
      const gap = parseFloat(String(row.pr_gap));
      const dcCapacity = parseFloat(String(row.dc_capacity_mw));

      if (!yearData[asset]) {
        yearData[asset] = {
          totalGap: 0,
          count: 0,
          totalDc: 0,
          dcCount: 0,
          months: new Set(),
        };
      }

      if (!isNaN(gap)) {
        yearData[asset].totalGap += gap;
        yearData[asset].count += 1;
      }

      if (!isNaN(dcCapacity)) {
        yearData[asset].totalDc += dcCapacity;
        yearData[asset].dcCount += 1;
      }

      const month = monthStr.slice(5, 7);
      if (month) yearData[asset].months.add(month);
    }
  });

  return Object.keys(yearData).map((asset) => {
    const data = yearData[asset];
    const avgGap = data.count ? data.totalGap / data.count : 0;
    const avgDc = data.dcCount ? data.totalDc / data.dcCount : 0;

    return {
      asset_no: asset,
      pr_gap: avgGap,
      dc_capacity_mw: avgDc,
      month: `${selectedYear}-AVG`,
      country: '',
      portfolio: '',
    };
  });
}

function getAvailableMonths(data: PrGapData[]): string[] {
  const months = Array.from(
    new Set(
      data
        .filter((r) => {
          const prGap = parseFloat(String(r.pr_gap));
          if (isNaN(prGap) || !r.month) return false;

          const monthStr = normalizeMonthValue(r.month);
          if (!monthStr) return false;

          return true;
        })
        .map((r) => normalizeMonthValue(r.month))
        .filter((value): value is string => Boolean(value))
    )
  );

  months.sort((a, b) => {
    const [aYear, aMonth] = a.split('-');
    const [bYear, bMonth] = b.split('-');
    if (aYear !== bYear) return parseInt(aYear) - parseInt(bYear);
    return parseInt(aMonth) - parseInt(bMonth);
  });

  return months;
}

export function usePrGapData(filters: PrGapFilters): UsePrGapDataReturn {
  const [prData, setPrData] = useState<PrGapData[]>([]);
  const [lossData, setLossData] = useState<LossCalculationData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    Promise.allSettled([
      fetchPrGapData(controller.signal),
      fetchLossCalculationData(controller.signal),
    ]).then((results) => {
      const prResult = results[0];
      const lossResult = results[1];

      if (prResult.status === 'fulfilled') {
        setPrData(prResult.value);
      } else {
        setError(prResult.reason);
        setPrData([]);
      }

      if (lossResult.status === 'fulfilled') {
        setLossData(lossResult.value);
      } else {
        console.warn('Failed to load loss calculation data:', lossResult.reason);
        setLossData([]);
      }

      setLoading(false);
    });

    return () => {
      controller.abort();
    };
  }, []);

  const filterOptions = useMemo<PrGapFilterOptions>(() => {
    const months = getAvailableMonths(prData);
    const years = Array.from(new Set(months.map((m) => m.slice(0, 4)))).sort();
    const countries = Array.from(new Set(prData.map((r) => r.country).filter(Boolean))).sort();
    const portfolios = Array.from(new Set(prData.map((r) => r.portfolio).filter(Boolean))).sort();

    return { months, years, countries, portfolios };
  }, [prData]);

  const filteredData = useMemo<PrGapDataPoint[]>(() => {
    let filtered = prData.slice();

    // Filter by month/year/range
    if (filters.month || filters.year || filters.range) {
      filtered = filtered.filter((r) =>
        isInSelectedMonth(r.month, filters.month || null, filters.year || null, filters.range || null)
      );
    }

    // Filter by countries
    if (filters.countries && filters.countries.length > 0) {
      filtered = filtered.filter((r) => filters.countries.includes(r.country));
    }

    // Filter by portfolios
    if (filters.portfolios && filters.portfolios.length > 0) {
      filtered = filtered.filter((r) => filters.portfolios.includes(r.portfolio));
    }

    // Aggregate by year if year is selected
    if (filters.year && !filters.month && !filters.range) {
      filtered = aggregateDataByYear(filtered, filters.year);
    }

    // Aggregate data by asset
    const assetMap: Record<
      string,
      { totalGap: number; count: number; totalDc: number; dcCount: number; rawData: Array<{ gap: number; dcCapacity: number }> }
    > = {};

    filtered.forEach((r) => {
      const asset = r.asset_no || r.assetno || r.asset || 'Unknown';
      const gap = parseFloat(String(r.pr_gap));
      const dcCapacity = parseFloat(String(r.dc_capacity_mw));

      if (!assetMap[asset]) {
        assetMap[asset] = {
          totalGap: 0,
          count: 0,
          totalDc: 0,
          dcCount: 0,
          rawData: [],
        };
      }

      if (!isNaN(gap)) {
        assetMap[asset].totalGap += gap;
        assetMap[asset].count += 1;
        assetMap[asset].rawData.push({ gap, dcCapacity: dcCapacity || 0 });
      }

      if (!isNaN(dcCapacity)) {
        assetMap[asset].totalDc += dcCapacity;
        assetMap[asset].dcCount += 1;
      }
    });

    // Prepare data points for charting
    const dataPoints: PrGapDataPoint[] = Object.keys(assetMap).map((asset) => {
      const data = assetMap[asset];

      // For year or range selection, use average values
      if ((filters.year && !filters.month && !filters.range) || filters.range) {
        const avgGap = data.count ? data.totalGap / data.count : 0;
        const avgDc = data.dcCount ? data.totalDc / data.dcCount : 0;
        return {
          asset,
          gap: avgGap,
          dc: avgDc,
          gapDc: avgGap * avgDc,
          gapDcDisplay: (avgGap * avgDc).toFixed(2),
          displayGap: (avgGap * 100).toFixed(2),
          color: avgGap >= 0 ? '#1aaa55' : '#e73323',
        };
      } else {
        // For single month selection, use the actual value
        const rawData = data.rawData;
        if (rawData.length === 1) {
          const gap = rawData[0].gap;
          const dc = rawData[0].dcCapacity;
          return {
            asset,
            gap: gap,
            dc: dc,
            gapDc: gap * dc,
            gapDcDisplay: (gap * dc).toFixed(2),
            displayGap: (gap * 100).toFixed(2),
            color: gap >= 0 ? '#1aaa55' : '#e73323',
          };
        } else if (rawData.length > 1) {
          // This should not happen for single month, but if it does, use average
          const avgGap = rawData.reduce((sum, d) => sum + d.gap, 0) / rawData.length;
          const avgDc = rawData.reduce((sum, d) => sum + d.dcCapacity, 0) / rawData.length;
          return {
            asset,
            gap: avgGap,
            dc: avgDc,
            gapDc: avgGap * avgDc,
            gapDcDisplay: (avgGap * avgDc).toFixed(2),
            displayGap: (avgGap * 100).toFixed(2),
            color: avgGap >= 0 ? '#1aaa55' : '#e73323',
          };
        } else {
          return {
            asset,
            gap: 0,
            dc: 0,
            gapDc: 0,
            gapDcDisplay: '0.00',
            displayGap: '0.00',
            color: '#e73323',
          };
        }
      }
    });

    // Sort by gap descending
    dataPoints.sort((a, b) => b.gap - a.gap);

    return dataPoints;
  }, [prData, filters]);

  return {
    prData,
    lossData,
    filterOptions,
    filteredData,
    loading,
    error,
  };
}

