/**
 * Global utility for persisting dashboard filters to localStorage
 * This ensures that when Playwright captures screenshots, it can restore filter state
 */

export interface FilterState {
  [key: string]: unknown;
}

const FILTER_STORAGE_PREFIX = 'dashboard-filters-';

/**
 * Get the storage key for a specific dashboard
 */
export function getFilterStorageKey(dashboardId: string): string {
  return `${FILTER_STORAGE_PREFIX}${dashboardId}`;
}

/**
 * Save filters to localStorage for a specific dashboard
 */
export function saveFilters(dashboardId: string, filters: FilterState): void {
  try {
    const key = getFilterStorageKey(dashboardId);
    localStorage.setItem(key, JSON.stringify(filters));
  } catch (error) {
    console.warn(`Failed to save filters for ${dashboardId}:`, error);
  }
}

/**
 * Load filters from localStorage for a specific dashboard
 */
export function loadFilters<T extends FilterState>(dashboardId: string): T | null {
  try {
    const key = getFilterStorageKey(dashboardId);
    const stored = localStorage.getItem(key);
    if (stored) {
      return JSON.parse(stored) as T;
    }
  } catch (error) {
    console.warn(`Failed to load filters for ${dashboardId}:`, error);
  }
  return null;
}

/**
 * Clear filters from localStorage for a specific dashboard
 */
export function clearFilters(dashboardId: string): void {
  try {
    const key = getFilterStorageKey(dashboardId);
    localStorage.removeItem(key);
  } catch (error) {
    console.warn(`Failed to clear filters for ${dashboardId}:`, error);
  }
}

/**
 * Get all dashboard filter keys from localStorage
 */
export function getAllFilterKeys(): string[] {
  const keys: string[] = [];
  try {
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && key.startsWith(FILTER_STORAGE_PREFIX)) {
        keys.push(key);
      }
    }
  } catch (error) {
    console.warn('Failed to get filter keys:', error);
  }
  return keys;
}

/**
 * Custom event name for filter save requests
 */
export const FILTER_SAVE_EVENT = 'dashboard:save-filters-before-download';

/**
 * Dispatch event to request all dashboards to save their filters
 * This is called by DownloadImageButton before capturing screenshot
 */
export function requestFilterSave(): void {
  window.dispatchEvent(new CustomEvent(FILTER_SAVE_EVENT));
}

