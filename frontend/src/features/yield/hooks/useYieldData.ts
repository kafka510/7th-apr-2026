import { useEffect, useState, useMemo } from 'react';
import { fetchYieldData } from '../api';
import type { YieldDataEntry, YieldFilters, YieldFilterOptions, YieldSummary } from '../types';

function toNumber(val: number | string | undefined | null): number {
  if (val === null || val === undefined || val === '') return 0;
  if (typeof val === 'number') return isNaN(val) ? 0 : val;
  const parsed = parseFloat(String(val));
  return isNaN(parsed) ? 0 : parsed;
}

/**
 * Pure hook that fetches and filters yield data
 * NEVER mutates the filters parameter - it's read-only
 * NEVER returns filters - only returns data, options, and summary
 */
export function useYieldData(filters: YieldFilters) {
  // Store raw fetched data (never mutated after fetch)
  const [data, setData] = useState<YieldDataEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch data ONCE on mount - never refetch based on filters
  useEffect(() => {
    const abortController = new AbortController();

    fetchYieldData(abortController.signal)
      .then((fetchedData) => {
        // Normalize data by trimming whitespace from string fields to avoid duplicates
        const normalizedData = fetchedData.map((row) => ({
          ...row,
          country: typeof row.country === 'string' ? row.country.trim() : row.country,
          portfolio: typeof row.portfolio === 'string' ? row.portfolio.trim() : row.portfolio,
          assetno: typeof row.assetno === 'string' ? String(row.assetno).trim() : row.assetno,
        }));
        setData(normalizedData);
      })
      .catch((err) => {
        if (err.name !== 'AbortError') {
          setError(err.message);
        }
      })
      .finally(() => setLoading(false));

    return () => {
      abortController.abort();
    };
  }, []); // Empty deps - fetch only once

  // Extract options from data with cascading filter support
  // This is PURE - it only reads filters, never mutates them
  const options: YieldFilterOptions = useMemo(() => {
    // Start with all data, then filter based on current selections
    let filteredData = data;

    // Filter by selected countries
    if (filters.countries.length > 0) {
      filteredData = filteredData.filter(d => filters.countries.includes(d.country));
    }

    // Extract portfolios from filtered data (data is already normalized/trimmed)
    const portfolios = [...new Set(filteredData.map(d => d.portfolio).filter(Boolean))].sort();

    // Filter by selected portfolios
    if (filters.portfolios.length > 0) {
      filteredData = filteredData.filter(d => filters.portfolios.includes(d.portfolio));
    }

    // Extract assets from filtered data
    const assets = [...new Set(filteredData.map(d => String(d.assetno)).filter(Boolean))].sort();

    // Countries are always from all data (data is already normalized/trimmed)
    const countries = [...new Set(data.map(d => d.country).filter(Boolean))].sort();
    const months = [...new Set(data.map(d => d.month).filter(Boolean))].sort();
    const years = [...new Set(data.map(d => d.month.split('-')[0]).filter(Boolean))].sort();

    return { countries, portfolios, assets, months, years };
  }, [data, filters.countries, filters.portfolios]);


  // Filter data based on filters - matches original logic
  // This is PURE - it only reads filters, never mutates them
  const filteredData = useMemo(() => {
    // Start with all data - filters object is READ-ONLY
    let filteredRows = data;

    // Apply country/portfolio/asset filters first (data is already normalized/trimmed)
    filteredRows = filteredRows.filter((row) => {
      if (filters.countries.length > 0 && !filters.countries.includes(row.country)) {
        return false;
      }
      if (filters.portfolios.length > 0 && !filters.portfolios.includes(row.portfolio)) {
        return false;
      }
      if (filters.assets.length > 0 && !filters.assets.includes(String(row.assetno))) {
        return false;
      }
      return true;
    });

    // Apply month/year/range filters
    // Read filters.month, filters.year, filters.range - NEVER mutate them
    const hasRange = filters.range && filters.range.start && filters.range.end;
    const hasMonth = Boolean(filters.month);
    const hasYear = Boolean(filters.year);
    
    if (hasRange) {
      // Range selected: show data for the selected month range
      filteredRows = filteredRows.filter((r) => {
        const monthValue = r.month;
        return monthValue >= filters.range!.start && monthValue <= filters.range!.end;
      });
    } else if (hasMonth) {
      // Month selected: show only that month
      filteredRows = filteredRows.filter((r) => r.month === filters.month);
    } else if (hasYear) {
      // Year selected but no specific month: show all months for that year
      filteredRows = filteredRows.filter((r) => {
        const [rowYear] = r.month.split('-');
        return rowYear === filters.year!.toString();
      });
    } else {
      // No month or year selected: show YTD (Jan to latest month) within current site filters.
      const availableMonthsForCurrentFilters = [
        ...new Set(filteredRows.map((row) => row.month).filter(Boolean)),
      ].sort();
      const latestMonth =
        availableMonthsForCurrentFilters.length > 0
          ? availableMonthsForCurrentFilters[availableMonthsForCurrentFilters.length - 1]
          : null;
      if (latestMonth) {
        const [selectedYearYTD, selectedMonthNumYTD] = latestMonth.split('-');
        filteredRows = filteredRows.filter((r) => {
          const [rowYear, rowMonth] = r.month.split('-');
          return rowYear === selectedYearYTD && rowMonth <= selectedMonthNumYTD;
        });
      } else {
        filteredRows = [];
      }
    }

    return filteredRows;
  }, [
    data,
    filters.month,
    filters.year,
    filters.range,
    filters.countries,
    filters.portfolios,
    filters.assets,
  ]);

  // Calculate summary totals
  const summary: YieldSummary = useMemo(() => {
    return {
      totalIcApprovedBudget: filteredData.reduce((sum, row) => sum + toNumber(row.ic_approved_budget), 0),
      totalExpectedBudget: filteredData.reduce((sum, row) => sum + toNumber(row.expected_budget), 0),
      totalActualGeneration: filteredData.reduce((sum, row) => sum + toNumber(row.actual_generation), 0),
      totalWeatherLossOrGain: filteredData.reduce((sum, row) => sum + toNumber(row.weather_loss_or_gain), 0),
      totalGridCurtailment: filteredData.reduce((sum, row) => sum + toNumber(row.grid_curtailment), 0),
      totalGridOutage: filteredData.reduce((sum, row) => sum + toNumber(row.grid_outage), 0),
      totalOperationBudget: filteredData.reduce((sum, row) => sum + toNumber(row.operation_budget), 0),
      totalBreakdownLoss: filteredData.reduce((sum, row) => sum + toNumber(row.breakdown_loss), 0),
      totalUnclassifiedLoss: filteredData.reduce((sum, row) => sum + toNumber(row.unclassified_loss), 0),
    };
  }, [filteredData]);

  // Return ONLY data, options, and summary - NEVER return filters
  // This hook is PURE - it never mutates the filters parameter
  return {
    loading,
    error,
    data: filteredData,
    allData: data, // Return unfiltered data for capacity calculations
    options,
    filterOptions: options,
    summary,
  };
}

