import { useEffect, useRef } from 'react';
import { FILTER_SAVE_EVENT, saveFilters, clearFilters, type FilterState } from '../utils/filterPersistence';

/**
 * React hook for persisting dashboard filters to localStorage
 * This ensures filters are saved when download is requested and restored on page load
 * 
 * ⚠️ CRITICAL: This hook ONLY saves filters. It NEVER reloads or overwrites active filters.
 * Filters must be loaded ONCE in useState initializer, not here.
 * 
 * Usage:
 * ```tsx
 * const [filters, setFilters] = useState(() => loadFilters('dashboard-id') || defaultFilters);
 * useFilterPersistence('dashboard-id', filters);
 * ```
 * 
 * @param dashboardId - Unique identifier for the dashboard (e.g., 'bess-v1', 'yield', 'kpi')
 * @param filters - Current filter state object
 */
export function useFilterPersistence<T extends FilterState>(
  dashboardId: string,
  filters: T
): void {
  // FIX 1: Track if this is the initial mount to skip saving on first render
  // This prevents overwriting filters that were just loaded from storage
  const isInitialMount = useRef(true);
  const previousFiltersRef = useRef<T | null>(null);

  // Listen for filter save requests (from DownloadImageButton)
  useEffect(() => {
    const handleSaveRequest = () => {
      // Save current filters to localStorage IMMEDIATELY when download is requested
      // This is synchronous to ensure filters are saved before Playwright navigates
      saveFilters(dashboardId, filters);
    };

    window.addEventListener(FILTER_SAVE_EVENT, handleSaveRequest);
    return () => {
      window.removeEventListener(FILTER_SAVE_EVENT, handleSaveRequest);
    };
  }, [dashboardId, filters]);

  // FIX 1 & 3: Save filters to localStorage whenever they change
  // CRITICAL: This hook ONLY saves. It NEVER calls setFilters or reloads from storage.
  useEffect(() => {
    // Skip saving on initial mount to avoid race conditions
    if (isInitialMount.current) {
      isInitialMount.current = false;
      previousFiltersRef.current = filters;
      return;
    }

    // Only save if filters actually changed (not just a re-render)
    const filtersChanged = JSON.stringify(previousFiltersRef.current) !== JSON.stringify(filters);
    
    if (filtersChanged && filters && Object.keys(filters).length > 0) {
      saveFilters(dashboardId, filters);
      previousFiltersRef.current = filters;
    }
  }, [dashboardId, filters]);

  // FIX 3: Explicitly ensure we never reload filters
  // This hook must NEVER call setFilters or loadFilters - it's save-only
  // If you see any code here that calls setFilters or loadFilters, that's a bug
}

/**
 * Helper function to clear filters for a dashboard
 */
export function clearDashboardFilters(dashboardId: string): void {
  clearFilters(dashboardId);
}

