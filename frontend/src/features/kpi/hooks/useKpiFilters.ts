import { useCallback, useMemo, useState } from 'react';

import type { KpiFilterState } from '../types';
import { useFilterPersistence } from '../../../hooks/useFilterPersistence';
import { loadFilters, clearFilters } from '../../../utils/filterPersistence';

// Get today's date in YYYY-MM-DD format
const getTodayDate = (): string => {
  const today = new Date();
  const year = today.getFullYear();
  const month = String(today.getMonth() + 1).padStart(2, '0');
  const day = String(today.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
};

const DASHBOARD_ID = 'kpi';

const initialState: KpiFilterState = {
  countries: [],
  portfolios: [],
  assets: [],
  date: null, // Deprecated: use startDate/endDate instead
  startDate: getTodayDate(), // Default to today's date
  endDate: getTodayDate(), // Default to today's date
  view: 'gauges',
};

function loadFiltersFromStorage(): KpiFilterState {
  const stored = loadFilters<KpiFilterState>(DASHBOARD_ID);
  const today = getTodayDate();
  
  if (stored) {
    // Migrate old date field to date range if needed
    let startDate = stored.startDate || null;
    let endDate = stored.endDate || null;
    
    // If we have old date field but no range, use it for both start and end
    if (stored.date && !startDate && !endDate) {
      startDate = stored.date;
      endDate = stored.date;
    }
    
    // Always initialize with today's date when the dashboard loads if no dates set,
    // regardless of any previously persisted date selection.
    // Users can still change the date afterward.
    if (!startDate) startDate = today;
    if (!endDate) endDate = today;
    
    return {
      countries: Array.isArray(stored.countries) ? (stored.countries as string[]) : [],
      portfolios: Array.isArray(stored.portfolios) ? (stored.portfolios as string[]) : [],
      assets: Array.isArray(stored.assets) ? (stored.assets as string[]) : [],
      date: null, // Deprecated
      startDate,
      endDate,
      view: stored.view === 'monthly' ? 'monthly' : 'gauges',
    };
  }
  return initialState;
}

export const useKpiFilters = () => {
  const [state, setState] = useState<KpiFilterState>(loadFiltersFromStorage);

  // Persist filters globally for download / restore
  useFilterPersistence(DASHBOARD_ID, state);

  const setCountries = useCallback((countries: string[]) => {
    setState((prev) => ({
      ...prev,
      countries,
      portfolios: countries.length === 0 ? prev.portfolios : [],
      assets: [],
    }));
  }, []);

  const setPortfolios = useCallback((portfolios: string[]) => {
    setState((prev) => ({
      ...prev,
      portfolios,
      assets: portfolios.length === 0 ? prev.assets : [],
    }));
  }, []);

  const setAssets = useCallback((assets: string[]) => {
    setState((prev) => ({
      ...prev,
      assets,
    }));
  }, []);

  const setDate = useCallback((date: string | null) => {
    // Deprecated: kept for backward compatibility
    setState((prev) => ({
      ...prev,
      date,
      startDate: date,
      endDate: date,
    }));
  }, []);

  const setStartDate = useCallback((startDate: string | null) => {
    setState((prev) => ({
      ...prev,
      startDate,
      date: null, // Clear deprecated field
    }));
  }, []);

  const setEndDate = useCallback((endDate: string | null) => {
    setState((prev) => ({
      ...prev,
      endDate,
      date: null, // Clear deprecated field
    }));
  }, []);

  const setDateRange = useCallback((startDate: string | null, endDate: string | null) => {
    setState((prev) => ({
      ...prev,
      startDate,
      endDate,
      date: null, // Clear deprecated field
    }));
  }, []);

  const setView = useCallback((view: 'gauges' | 'monthly') => {
    setState((prev) => ({
      ...prev,
      view,
    }));
  }, []);

  const reset = useCallback(() => {
    setState(initialState);
    clearFilters(DASHBOARD_ID);
  }, []);

  const filters = useMemo(() => state, [state]);

  return {
    filters,
    setCountries,
    setPortfolios,
    setAssets,
    setDate, // Deprecated: use setStartDate/setEndDate instead
    setStartDate,
    setEndDate,
    setDateRange,
    setView,
    reset,
  };
};

