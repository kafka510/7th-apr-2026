import { useState, useEffect, useMemo } from 'react';
import { fetchAOCData } from '../api';
import type { AOCData, AOCFilters, AOCFilterOptions } from '../types';

interface UseAOCDataReturn {
  aocData: AOCData[];
  filterOptions: AOCFilterOptions;
  filteredData: AOCData[];
  loading: boolean;
  error: Error | null;
}

// Convert month format from "YY-MMM" (e.g., "25-Jun") to "YYYY-MM" (e.g., "2025-06")
function normalizeMonthFormat(month: string): string {
  if (!month) return '';
  
  // If already in YYYY-MM format, return as is
  if (month.match(/^\d{4}-\d{2}$/)) {
    return month;
  }
  
  // If in YY-MMM format (e.g., "25-Jun"), convert to YYYY-MM
  const match = month.match(/^(\d{2})-([A-Za-z]{3})$/);
  if (match) {
    const [, yearShort, monthName] = match;
    const year = parseInt(yearShort) < 50 ? `20${yearShort}` : `19${yearShort}`;
    const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const monthIndex = monthNames.findIndex(m => m.toLowerCase() === monthName.toLowerCase());
    if (monthIndex >= 0) {
      return `${year}-${String(monthIndex + 1).padStart(2, '0')}`;
    }
  }
  
  return month;
}

function isInSelectedMonth(rowMonth: string | null | undefined, selectedMonth: string | null, selectedYear: string | null): boolean {
  if (!rowMonth) return false;

  // Normalize row month format
  const normalizedRowMonth = normalizeMonthFormat(rowMonth);

  if (selectedMonth) {
    // Compare normalized formats
    const normalizedSelectedMonth = normalizeMonthFormat(selectedMonth);
    return normalizedRowMonth === normalizedSelectedMonth;
  } else if (selectedYear) {
    // Check if year matches
    const rowYear = normalizedRowMonth.slice(0, 4);
    return rowYear === String(selectedYear);
  }

  return false;
}

function getAvailableMonths(data: AOCData[]): string[] {
  const now = new Date();
  const currentYear = now.getFullYear();
  const currentMonth = now.getMonth() + 1;

  // Get unique months from data (preserve original format)
  const monthSet = new Set<string>();
  
  data.forEach((r) => {
    if (!r.month) return;
    
    // Normalize to check if it's valid and not in the future
    const normalizedMonth = normalizeMonthFormat(r.month);
    if (!normalizedMonth || normalizedMonth.length !== 7) return;

    const [year, month] = normalizedMonth.split('-');
    const dataYear = parseInt(year);
    const dataMonth = parseInt(month);

    if (dataYear > currentYear) return;
    if (dataYear === currentYear && dataMonth > currentMonth) return;

    // Store in normalized format (YYYY-MM) for consistency
    monthSet.add(normalizedMonth);
  });

  const months = Array.from(monthSet);

  months.sort((a, b) => {
    const [aYear, aMonth] = a.split('-');
    const [bYear, bMonth] = b.split('-');
    if (aYear !== bYear) return parseInt(aYear) - parseInt(bYear);
    return parseInt(aMonth) - parseInt(bMonth);
  });

  return months;
}

export function useAOCData(filters: AOCFilters): UseAOCDataReturn {
  const [aocData, setAocData] = useState<AOCData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    fetchAOCData(controller.signal)
      .then((data) => {
        setAocData(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err);
        setAocData([]);
        setLoading(false);
      });

    return () => {
      controller.abort();
    };
  }, []);

  const filterOptions = useMemo<AOCFilterOptions>(() => {
    const months = getAvailableMonths(aocData);
    const years = Array.from(new Set(months.map((m) => m.slice(0, 4)))).sort();
    const countries = Array.from(
      new Set(
        aocData
          .map((r) => r.country)
          .filter((c) => c && c.toLowerCase() !== 'all countries' && c.toLowerCase() !== 'all country')
      )
    ).sort();
    const portfolios = Array.from(
      new Set(
        aocData
          .map((r) => r.portfolio)
          .filter((p) => p && p.toLowerCase() !== 'all portfolio')
      )
    ).sort();

    return { months, years, countries, portfolios };
  }, [aocData]);

  const filteredData = useMemo<AOCData[]>(() => {
    let filtered = aocData.slice();

    // Filter by month/year
    if (filters.month || filters.year) {
      filtered = filtered.filter((r) => isInSelectedMonth(r.month, filters.month || null, filters.year || null));
    }

    // Filter by country
    if (filters.country && filters.country !== '__all__') {
      filtered = filtered.filter((r) => r.country === filters.country);
    }

    // Filter by portfolio
    if (filters.portfolio && filters.portfolio !== '__all__') {
      filtered = filtered.filter((r) => r.portfolio === filters.portfolio);
    }

    return filtered;
  }, [aocData, filters]);

  return {
    aocData,
    filterOptions,
    filteredData,
    loading,
    error,
  };
}

