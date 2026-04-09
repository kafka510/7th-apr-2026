import type { RevenueLossFilters, RevenueLossFilterOptions } from '../types';
import type { Period } from '../../generation/components/PeriodPicker';
import { useTheme } from '../../../contexts/ThemeContext';
import { useResponsiveFontSize } from '../../../utils/fontScaling';
import { PeriodPicker } from '../../generation/components/PeriodPicker';
import { CompactMultiSelectDropdown } from '../../yield/components/CompactMultiSelectDropdown';

interface RevenueLossFiltersProps {
  filters: RevenueLossFilters;
  options: RevenueLossFilterOptions;
  loading: boolean;
  onFiltersChange: (filters: RevenueLossFilters) => void;
  onReset: () => void;
}

export function RevenueLossFilters({
  filters,
  options,
  loading,
  onFiltersChange,
  onReset,
}: RevenueLossFiltersProps) {
  const { theme } = useTheme();
  
  // Responsive font sizes
  const buttonFontSize = useResponsiveFontSize(9, 13, 8);
  
  const containerBg = theme === 'dark'
    ? 'linear-gradient(to bottom right, rgba(15, 23, 42, 0.9), rgba(30, 41, 59, 0.6), rgba(15, 23, 42, 0.9))'
    : 'linear-gradient(to bottom right, rgba(255, 255, 255, 0.95), rgba(248, 250, 252, 0.9), rgba(255, 255, 255, 0.95))';
  const containerBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(203, 213, 225, 0.8)';
  const containerShadow = theme === 'dark' 
    ? '0 20px 25px -5px rgba(0, 0, 0, 0.4)' 
    : '0 10px 15px -3px rgba(0, 0, 0, 0.1)';
  const resetButtonBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.8)' : '#ffffff';
  const resetButtonBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : 'rgba(203, 213, 225, 0.7)';
  const resetButtonText = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';
  const defaultPeriod: Period = (() => {
    if (filters.range) {
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

  const handlePeriodChange = (period: Period) => {
    if (period.range) {
      const { start, end } = period.range;
      const year = start.split('-')[0];

      if (start === `${year}-01` && end === `${year}-12`) {
        onFiltersChange({
          ...filters,
          month: undefined,
          range: undefined,
          year,
        });
      } else {
        onFiltersChange({
          ...filters,
          month: undefined,
          year: undefined,
          range: { start, end },
        });
      }
    } else if (period.month) {
      const year = period.month.split('-')[0];
      onFiltersChange({
        ...filters,
        month: period.month,
        year,
        range: undefined,
      });
    } else {
      onFiltersChange({
        ...filters,
        month: undefined,
        year: undefined,
        range: undefined,
      });
    }
  };

  const handleCountryChange = (values: string[]) => {
    onFiltersChange({
      ...filters,
      countries: values.length > 0 ? values : undefined,
    });
  };

  const handlePortfolioChange = (values: string[]) => {
    onFiltersChange({
      ...filters,
      portfolios: values.length > 0 ? values : undefined,
    });
  };

  const hasActiveFilters =
    Boolean(filters.month) ||
    Boolean(filters.year) ||
    Boolean(filters.range) ||
    Boolean(filters.countries && filters.countries.length > 0) ||
    Boolean(filters.portfolios && filters.portfolios.length > 0);

  return (
    <section 
      className="relative rounded-xl border p-2 shadow-xl"
      style={{
        borderColor: containerBorder,
        background: containerBg,
        boxShadow: containerShadow,
      }}
    >
      {theme === 'dark' ? (
      <div className="pointer-events-none absolute inset-0 rounded-xl bg-[radial-gradient(circle_at_top,_rgba(56,189,248,0.12),_transparent_55%),radial-gradient(circle_at_bottom,_rgba(167,139,250,0.12),_transparent_60%)]" />
      ) : (
        <div className="pointer-events-none absolute inset-0 rounded-xl bg-[radial-gradient(circle_at_top,_rgba(59,130,246,0.08),_transparent_55%),radial-gradient(circle_at_bottom,_rgba(167,139,250,0.06),_transparent_60%)]" />
      )}
      <div className="relative flex items-center gap-2">
        <div className="min-w-0 flex-1">
          <PeriodPicker
            defaultPeriod={defaultPeriod}
            onPeriodChange={handlePeriodChange}
            onReset={onReset}
          />
        </div>

        <div className="min-w-0 flex-1">
          <CompactMultiSelectDropdown
            label="Country"
            icon="🌍"
            options={options.countries}
            selected={filters.countries || []}
            placeholder="All Countries"
            onChange={handleCountryChange}
            disabled={loading}
          />
        </div>

        <div className="min-w-0 flex-1">
          <CompactMultiSelectDropdown
            label="Portfolio"
            icon="📂"
            options={options.portfolios}
            selected={filters.portfolios || []}
            placeholder="All Portfolios"
            onChange={handlePortfolioChange}
            disabled={loading}
          />
        </div>

        <div>
          <div className="text-[8px] font-semibold uppercase tracking-wide text-transparent">
            &nbsp;
          </div>
          <button
            type="button"
            onClick={onReset}
            disabled={loading || !hasActiveFilters}
            className="rounded-lg border px-2 py-0.5 font-semibold uppercase tracking-wide shadow-inner transition focus:outline-none focus:ring-1 focus:ring-red-500 disabled:cursor-not-allowed disabled:opacity-30"
            style={{
              fontSize: `${buttonFontSize}px`,
              borderColor: resetButtonBorder,
              backgroundColor: resetButtonBg,
              color: resetButtonText,
              boxShadow: theme === 'dark' ? 'inset 0 2px 4px rgba(0, 0, 0, 0.4)' : 'inset 0 2px 4px rgba(0, 0, 0, 0.1)',
            }}
            onMouseEnter={(e) => {
              if (!loading && hasActiveFilters) {
                e.currentTarget.style.borderColor = '#ef4444';
                e.currentTarget.style.backgroundColor = theme === 'dark' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(239, 68, 68, 0.1)';
                e.currentTarget.style.color = theme === 'dark' ? '#fca5a5' : '#dc2626';
              }
            }}
            onMouseLeave={(e) => {
              if (!loading && hasActiveFilters) {
                e.currentTarget.style.borderColor = resetButtonBorder;
                e.currentTarget.style.backgroundColor = resetButtonBg;
                e.currentTarget.style.color = resetButtonText;
              }
            }}
          >
            Reset
          </button>
        </div>
      </div>
    </section>
  );
}
