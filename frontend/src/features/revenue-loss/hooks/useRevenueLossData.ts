import { useState, useEffect, useMemo } from 'react';
import { fetchRevenueLossData } from '../api';
import type { RevenueLossData, RevenueLossFilters, RevenueLossFilterOptions, RevenueLossDataPoint } from '../types';

interface UseRevenueLossDataReturn {
  revenueData: RevenueLossData[];
  filterOptions: RevenueLossFilterOptions;
  expectedData: RevenueLossDataPoint[];
  operationalData: RevenueLossDataPoint[];
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

function isInSelectedMonth(rowMonth: string | null | undefined, selectedMonth: string | null, selectedYear: string | null): boolean {
  const monthStr = normalizeMonthValue(rowMonth);
  if (!monthStr) return false;

  if (selectedYear) {
    return monthStr.slice(0, 4) === String(selectedYear);
  } else if (selectedMonth) {
    return monthStr === selectedMonth;
  }

  return false;
}

function getAvailableMonths(data: RevenueLossData[]): string[] {
  const months = Array.from(
    new Set(
      data
        .filter((r) => {
          const revenueLoss = parseFloat(String(r.revenue_loss));
          if (isNaN(revenueLoss) || !r.month) return false;

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

// Format value as K (thousands) or M (millions)
function formatK(v: number): string {
  if (isNaN(v)) return '';
  // If value is >= 1 million, use M format with no decimals
  if (Math.abs(v) >= 1000000) {
    const millions = v / 1000000;
    return Math.round(millions) + 'M';
  }
  // If value is >= 1 thousand, use K format with no decimals
  if (Math.abs(v) >= 1000) {
    const thousands = v / 1000;
    return Math.round(thousands) + 'K';
  }
  // Otherwise, return rounded value
  return Math.round(v).toString();
}

export function useRevenueLossData(filters: RevenueLossFilters): UseRevenueLossDataReturn {
  const [revenueData, setRevenueData] = useState<RevenueLossData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    fetchRevenueLossData(controller.signal)
      .then((data) => {
        setRevenueData(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err);
        setRevenueData([]);
        setLoading(false);
      });

    return () => {
      controller.abort();
    };
  }, []);

  const filterOptions = useMemo<RevenueLossFilterOptions>(() => {
    const months = getAvailableMonths(revenueData);
    const years = Array.from(new Set(months.map((m) => m.slice(0, 4)))).sort();
    const countries = Array.from(new Set(revenueData.map((r) => r.country).filter(Boolean))).sort();
    const portfolios = Array.from(new Set(revenueData.map((r) => r.portfolio).filter(Boolean))).sort();

    return { months, years, countries, portfolios };
  }, [revenueData]);

  // Helper function to process data for a specific budget type
  const processDataForBudgetType = (budgetType: 'expected' | 'operational'): RevenueLossDataPoint[] => {
    let filtered = revenueData.slice();

    // Filter by month/year/range
    if (filters.month || filters.year) {
      filtered = filtered.filter((r) =>
        isInSelectedMonth(r.month, filters.month || null, filters.year || null)
      );
    }
    if (filters.range) {
      filtered = filtered.filter((r) => {
        const monthStr = normalizeMonthValue(r.month);
        if (!monthStr) return false;
        return monthStr >= filters.range!.start && monthStr <= filters.range!.end;
      });
    }

    // Filter by country
    if (filters.countries && filters.countries.length > 0) {
      filtered = filtered.filter((r) => filters.countries!.includes(r.country));
    }

    // Filter by portfolio
    if (filters.portfolios && filters.portfolios.length > 0) {
      filtered = filtered.filter((r) => filters.portfolios!.includes(r.portfolio));
    }

    // Get revenue field based on budget type
    const revenueField = budgetType === 'operational' ? 'revenue_loss_op' : 'revenue_loss';

    // Aggregate data by asset
    const assetMap: Record<
      string,
      { total: number; count: number; details: Array<{ month: string; value: number }> }
    > = {};

    filtered.forEach((r) => {
      const asset = r.asset_no || r.assetno || r.asset || 'Unknown';
      const revenueValue = parseFloat(String(r[revenueField]));

      if (!isNaN(revenueValue)) {
        if (!assetMap[asset]) {
          assetMap[asset] = {
            total: 0,
            count: 0,
            details: [],
          };
        }

        assetMap[asset].total += revenueValue;
        assetMap[asset].count += 1;
        assetMap[asset].details.push({ month: r.month || '', value: revenueValue });
      }
    });

    // Prepare data points for charting
    const dataPoints: RevenueLossDataPoint[] = Object.keys(assetMap).map((asset) => {
      const data = assetMap[asset];

      // For year mode: use total, for month mode: use average
      const isYearMode = !!filters.year && !filters.month;
      const value = isYearMode ? data.total : data.total / data.count;

      return {
        asset,
        loss: value,
        color: value >= 0 ? '#1aaa55' : '#e73323',
        displayValue: formatK(value),
      };
    });

    // Sort by loss descending
    dataPoints.sort((a, b) => b.loss - a.loss);

    return dataPoints;
  };

  const expectedData = useMemo<RevenueLossDataPoint[]>(() => {
    return processDataForBudgetType('expected');
  }, [revenueData, filters, processDataForBudgetType]);

  const operationalData = useMemo<RevenueLossDataPoint[]>(() => {
    return processDataForBudgetType('operational');
  }, [revenueData, filters, processDataForBudgetType]);

  return {
    revenueData,
    filterOptions,
    expectedData,
    operationalData,
    loading,
    error,
  };
}

