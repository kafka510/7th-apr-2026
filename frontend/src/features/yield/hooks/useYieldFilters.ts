import { useState, useCallback } from 'react';
import type { YieldFilters } from '../types';

export function useYieldFilters() {
  const [filters, setFilters] = useState<YieldFilters>({
    countries: [],
    portfolios: [],
    assets: [],
    month: null,
    year: null,
    range: null,
  });

  const setCountries = useCallback((countries: string[]) => {
    const normalizedCountries = countries.map((c) => c.trim());
    setFilters(prev => {
      // Changing country should reset downstream selections to avoid stale filters.
      const countryChanged =
        prev.countries.length !== normalizedCountries.length ||
        prev.countries.some((c, idx) => c !== normalizedCountries[idx]);

      if (!countryChanged) {
        return prev;
      }

      return {
        ...prev,
        countries: normalizedCountries,
        portfolios: [],
        assets: [],
      };
    });
  }, []);

  const setPortfolios = useCallback((portfolios: string[]) => {
    const normalizedPortfolios = portfolios.map((p) => p.trim());
    setFilters(prev => {
      // Changing portfolio should reset asset selections to avoid stale filters.
      const portfolioChanged =
        prev.portfolios.length !== normalizedPortfolios.length ||
        prev.portfolios.some((p, idx) => p !== normalizedPortfolios[idx]);

      if (!portfolioChanged) {
        return prev;
      }

      return { ...prev, portfolios: normalizedPortfolios, assets: [] };
    });
  }, []);

  const setAssets = useCallback((assets: string[]) => {
    setFilters(prev => ({ ...prev, assets: assets.map((a) => a.trim()) }));
  }, []);

  const setMonth = useCallback((month: string | null) => {
    setFilters(prev => {
      // IF user selects a month → clear year & range
      // IF user selects null → DO NOT clear range (preserve it)
      const newFilters = { 
        ...prev, 
        month: month, 
        year: month ? null : prev.year,  // Only clear year when selecting a month
        range: month ? null : prev.range  // Only clear range when selecting a month
      };
      return newFilters;
    });
  }, []); // Empty deps - function should be stable

  const setYear = useCallback((year: string | null) => {
    setFilters(prev => ({
      ...prev,
      year,
      // Only clear month when a year is being set (non-null)
      // DO NOT clear range - range can coexist with year selection
      month: year !== null ? null : prev.month,
    }));
  }, []);

  const setRange = useCallback((range: { start: string; end: string } | null) => {
    setFilters(prev => ({
      ...prev,
      range,
      // DO NOT automatically clear month/year - let the caller decide
      // This prevents range from being wiped out when month is cleared elsewhere
    }));
  }, []);

  const reset = useCallback(() => {
    setFilters({
      countries: [],
      portfolios: [],
      assets: [],
      month: null,
      year: null,
      range: null,
    });
  }, []);

  return {
    filters,
    setCountries,
    setPortfolios,
    setAssets,
    setMonth,
    setYear,
    setRange,
    reset,
  };
}

