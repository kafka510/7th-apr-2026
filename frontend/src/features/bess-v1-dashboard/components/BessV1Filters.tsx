import type { BessV1FilterOptions, BessV1Filters } from '../types';
import { CompactMultiSelectDropdown } from '../../yield/components/CompactMultiSelectDropdown';
import { PeriodPicker, type Period } from '../../generation/components/PeriodPicker';
import { useTheme } from '../../../contexts/ThemeContext';

interface BessV1FiltersProps {
  filters: BessV1Filters;
  options: BessV1FilterOptions;
  loading: boolean;
  // Support both direct value and functional update (like React setState)
  onFiltersChange: (filters: BessV1Filters | ((prev: BessV1Filters) => BessV1Filters)) => void;
  onReset: () => void;
}

export function BessV1Filters({
  filters,
  options,
  loading,
  onFiltersChange,
  onReset,
}: BessV1FiltersProps) {
  const { theme } = useTheme();
  
  // Theme-aware colors
  const containerBg = theme === 'dark'
    ? 'radial-gradient(circle at top, rgba(56,189,248,0.12), transparent 55%), radial-gradient(circle at bottom, rgba(167,139,250,0.12), transparent 60%), linear-gradient(to bottom right, rgb(15 23 42 / 0.9), rgb(30 41 59 / 0.6), rgb(15 23 42 / 0.9))'
    : 'radial-gradient(circle at top, rgba(0, 114, 206, 0.08), transparent 55%), radial-gradient(circle at bottom, rgba(0, 198, 255, 0.08), transparent 60%), linear-gradient(to bottom right, rgba(255, 255, 255, 0.95), rgba(248, 250, 252, 0.9), rgba(255, 255, 255, 0.95))';
  const containerBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(226, 232, 240, 0.8)';
  
  // Use functional updates for all handlers to avoid stale state issues
  // This is especially important when MonthPicker calls multiple handlers in sequence
  const handleCountryChange = (values: string[]) => {
    onFiltersChange((prevFilters) => ({ ...prevFilters, countries: values }));
  };

  const handlePortfolioChange = (values: string[]) => {
    onFiltersChange((prevFilters) => ({ ...prevFilters, portfolios: values }));
  };

  const handleAssetChange = (values: string[]) => {
    onFiltersChange((prevFilters) => ({ ...prevFilters, assets: values }));
  };

  // Map current filters to Generation Report style Period for PeriodPicker
  const defaultPeriod: Period = (() => {
    if (filters.range && filters.range.start && filters.range.end) {
      return { range: { start: filters.range.start, end: filters.range.end } };
    }
    if (filters.month) {
      return { month: filters.month };
    }
    if (filters.year) {
      return {
        range: {
          start: `${filters.year}-01`,
          end: `${filters.year}-12`,
        },
      };
    }
    return {};
  })();

  // Handle period changes from PeriodPicker (single month vs range vs full year)
  const handlePeriodChange = (period: Period) => {
    onFiltersChange((prevFilters) => {
      // Range selection (including full year and single-month-as-range)
      if (period.range) {
        const { start, end } = period.range;
        const year = start.split('-')[0] || null;

        // Treat single-month range as "single month" selection so that
        // useBessV1Data can switch charts to day-wise view.
        if (start === end) {
          return {
            ...prevFilters,
            month: start,
            year,
            range: null,
            startMonth: undefined,
            endMonth: undefined,
          };
        }

        // Treat full-year range as year selection
        if (year && start === `${year}-01` && end === `${year}-12`) {
          return {
            ...prevFilters,
            month: null,
            year,
            range: {
              start,
              end,
            },
            startMonth: undefined,
            endMonth: undefined,
          };
        }

        // Custom month range
        return {
          ...prevFilters,
          month: null,
          // Keep year for context if the range is within a single year
          year,
          range: {
            start,
            end,
          },
          startMonth: undefined,
          endMonth: undefined,
        };
      }

      // Single month selection via Period.month (not commonly used, but supported)
      if (period.month) {
        const year = period.month.split('-')[0] || null;
        return {
          ...prevFilters,
          month: period.month,
          year,
          range: null,
          startMonth: undefined,
          endMonth: undefined,
        };
      }

      // No period selected
      return {
        ...prevFilters,
        month: null,
        year: null,
        range: null,
        startMonth: undefined,
        endMonth: undefined,
      };
    });
  };

  return (
    <div
      className="rounded-xl p-2 shadow-xl"
      style={{
        margin: '0 8px 8px 8px',
        border: `1px solid ${containerBorder}`,
        background: containerBg,
        overflow: 'visible',
        position: 'relative',
        zIndex: 50,
        transition: 'background 0.3s ease, border-color 0.3s ease',
      }}
    >
      <div className="flex flex-wrap items-end gap-2">
        {/* Countries Filter */}
        <div className="min-w-0 flex-1" style={{ minWidth: '160px' }}>
          <CompactMultiSelectDropdown
            label="Countries"
            icon="🌍"
            options={options.countries}
            selected={filters.countries}
            onChange={handleCountryChange}
            placeholder="All Countries"
            disabled={loading}
          />
        </div>

        {/* Portfolios Filter */}
        <div className="min-w-0 flex-1" style={{ minWidth: '160px' }}>
          <CompactMultiSelectDropdown
            label="Portfolios"
            icon="📂"
            options={options.portfolios}
            selected={filters.portfolios}
            onChange={handlePortfolioChange}
            placeholder="All Portfolios"
            disabled={loading}
          />
        </div>

        {/* Assets Filter */}
        <div className="min-w-0 flex-1" style={{ minWidth: '200px' }}>
          <CompactMultiSelectDropdown
            label="Assets"
            icon="🏭"
            options={options.assets}
            selected={filters.assets}
            onChange={handleAssetChange}
            placeholder="All Assets"
            disabled={loading}
          />
        </div>

        {/* Period Picker (matches Generation Report calendar) */}
        <div className="min-w-0 flex-1" style={{ minWidth: '200px' }}>
          <PeriodPicker
            defaultPeriod={defaultPeriod}
            onPeriodChange={handlePeriodChange}
            onReset={onReset}
          />
        </div>

        {/* Reset Button */}
        <div style={{ minWidth: '80px' }}>
          <button
            type="button"
            onClick={onReset}
            disabled={loading}
            className="text-[9px] font-semibold uppercase tracking-wide"
            style={{
              width: '100%',
              padding: '6px 12px',
              borderRadius: '8px',
              border: 'none',
              background: '#f87171',
              color: 'white', // Red button always has white text for contrast
              cursor: loading ? 'not-allowed' : 'pointer',
              transition: 'background 0.3s ease',
            }}
            onMouseEnter={(e) => {
              if (!loading) e.currentTarget.style.background = '#ef4444';
            }}
            onMouseLeave={(e) => {
              if (!loading) e.currentTarget.style.background = '#f87171';
            }}
          >
            Reset
          </button>
        </div>
      </div>
    </div>
  );
}

