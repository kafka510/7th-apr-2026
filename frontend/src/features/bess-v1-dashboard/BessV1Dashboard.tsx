import { useEffect, useState } from 'react';
import { BessV1Filters } from './components/BessV1Filters';
import { BessV1KPIs } from './components/BessV1KPIs';
import { BessV1Charts } from './components/BessV1Charts';
import { useBessV1Data } from './hooks/useBessV1Data';
import type { BessV1Filters as FiltersType } from './types';
import { useTheme } from '../../contexts/ThemeContext';
import { useFilterPersistence, clearDashboardFilters } from '../../hooks/useFilterPersistence';
import { loadFilters } from '../../utils/filterPersistence';

const DASHBOARD_ID = 'bess-v1';

const defaultFilters: FiltersType = {
  countries: [],
  portfolios: [],
  assets: [],
  month: null,
  year: null,
  range: null,
};

function loadFiltersFromStorage(): FiltersType {
  const stored = loadFilters<FiltersType>(DASHBOARD_ID);
  if (stored) {
    // Validate the structure and normalize year to string
    const normalizedYear = stored.year ? String(stored.year).trim() : null;
    return {
      countries: Array.isArray(stored.countries) ? stored.countries : [],
      portfolios: Array.isArray(stored.portfolios) ? stored.portfolios : [],
      assets: Array.isArray(stored.assets) ? stored.assets : [],
      month: stored.month || null,
      year: normalizedYear,
      range: stored.range && typeof stored.range === 'object' && stored.range.start && stored.range.end
        ? { start: stored.range.start, end: stored.range.end }
        : null,
      startMonth: stored.startMonth || undefined,
      endMonth: stored.endMonth || undefined,
    };
  }
  return defaultFilters;
}

// FIX 2: Default year constant - used ONLY for initialization and reset
// This ensures default year logic is centralized and consistent
const CURRENT_YEAR = new Date().getFullYear().toString();

export function BessV1Dashboard() {
  const { theme } = useTheme();
  // FIX 2: Enforce default year ONLY in Dashboard initialization
  // Default year logic belongs in state initialization, not in data filtering
  // This allows user to override the default year (e.g., select 2026)
  const [filters, setFilters] = useState<FiltersType>(() => {
    const stored = loadFiltersFromStorage();

    // If stored filters already have a year, use them as-is
    // This respects user's previous selection
    if (stored.year) {
      return stored;
    }

    // 🔴 DEFAULT YEAR LOGIC (ONLY for initial load)
    // Set default year to current year if no year is stored
    // This ensures dashboard never starts with year: null (which shows all data)
    // User can override this by selecting a different year later
    return {
      ...stored,
      year: CURRENT_YEAR,
      // Create a full-year range for the default year (Jan to Dec)
      // This tells the data layer it's a full-year query
      range: {
        start: `${CURRENT_YEAR}-01`,
        end: `${CURRENT_YEAR}-12`,
      },
      // Clear month when setting default year (year selection takes precedence)
      month: null,
      startMonth: undefined,
      endMonth: undefined,
    };
  });

  // FIX 1 & 3: Use global filter persistence hook (save-only, never reloads)
  // This hook ONLY saves filters when they change. It NEVER overwrites active filters.
  useFilterPersistence(DASHBOARD_ID, filters);


  const { filterOptions, filteredData, aggregates, loading, error } = useBessV1Data(filters);

  // Mark filters as ready once data has loaded
  // This helps Playwright know when the page is ready with filters applied
  useEffect(() => {
    if (!loading) {
      // Add data attribute to signal that filters are applied and data is loaded
      document.body.setAttribute('data-filters-ready', 'true');
      // Also dispatch a custom event for Playwright to listen to
      window.dispatchEvent(new CustomEvent('dashboard-filters-ready', { 
        detail: { dashboardId: DASHBOARD_ID } 
      }));
    } else {
      document.body.removeAttribute('data-filters-ready');
    }
  }, [loading]);

  useEffect(() => {
    const root = document.getElementById('react-root');
    if (!root) return;
    root.style.display = 'flex';
    root.style.flexDirection = 'column';
    root.style.height = '100%';
    root.style.width = '100%';
    root.style.overflow = 'visible';
  }, []);

  // Support both direct value and functional update (like React setState)
  // This prevents stale state issues when MonthPicker calls multiple handlers in sequence
  const handleFiltersChange = (nextFilters: FiltersType | ((prev: FiltersType) => FiltersType)) => {
    if (typeof nextFilters === 'function') {
      setFilters(nextFilters);
    } else {
      setFilters(nextFilters);
    }
  };

  // FIX 3: Reset must restore CURRENT YEAR, not null
  // Reset = Current Year (Full Year), NOT All Years
  // This ensures dashboard never operates without a year filter
  // Uses the same CURRENT_YEAR constant for consistency
  const handleReset = () => {
    const resetFilters = {
      countries: [],
      portfolios: [],
      assets: [],
      month: null,
      year: CURRENT_YEAR, // ✅ Reset to current year, not null
      range: {
        start: `${CURRENT_YEAR}-01`,
        end: `${CURRENT_YEAR}-12`,
      },
      startMonth: undefined,
      endMonth: undefined,
    };

    setFilters(resetFilters);
    clearDashboardFilters(DASHBOARD_ID);
  };

  const bgGradient = theme === 'dark'
    ? 'linear-gradient(to bottom right, #0f172a, #1e293b, #0f172a)'
    : 'linear-gradient(to bottom right, #f8fbff, #ffffff, #f8fbff)';
  const textColor = theme === 'dark' ? '#f1f5f9' : '#1a1a1a';
  const errorTextColor = theme === 'dark' ? '#e2e8f0' : '#4a5568';

  if (error) {
    return (
      <div 
        className="flex size-full flex-col"
        style={{ 
          background: bgGradient,
          transition: 'background 0.3s ease',
        }}
      >
        <div style={{ padding: '20px', textAlign: 'center', color: '#f87171' }}>
          <h2 style={{ fontSize: '1.25rem', marginBottom: '8px', color: '#f87171' }}>Unable to load BESS data</h2>
          <p style={{ color: errorTextColor }}>{error.message}</p>
        </div>
      </div>
    );
  }

  return (
    <div 
      className="flex w-full flex-col" 
      style={{ 
        overflow: 'visible',
        background: bgGradient,
        color: textColor,
        transition: 'background 0.3s ease, color 0.3s ease',
        minHeight: '100%',
      }}
    >
      <main className="flex flex-col gap-2 p-2" style={{ overflow: 'visible', position: 'relative' }}>
        {/* Filters Section */}
        <div style={{ position: 'relative', zIndex: 1000, overflow: 'visible' }}>
          <BessV1Filters
            filters={filters}
            options={filterOptions}
            loading={loading}
            onFiltersChange={handleFiltersChange}
            onReset={handleReset}
          />
        </div>

        {/* KPI Cards */}
        <div style={{ position: 'relative', zIndex: 1, overflow: 'visible' }}>
          <BessV1KPIs aggregates={aggregates} loading={loading} />
        </div>

        {/* Charts Section */}
        <BessV1Charts aggregates={aggregates} loading={loading} />

        {filteredData.length === 0 && !loading ? (
          <div style={{ textAlign: 'center', color: theme === 'dark' ? '#94a3b8' : '#718096', paddingBottom: '40px' }}>
            No data found for the selected filters.
          </div>
        ) : null}
      </main>
    </div>
  );
}

