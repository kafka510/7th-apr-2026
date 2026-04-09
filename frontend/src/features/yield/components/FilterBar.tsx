import type { YieldFilters, YieldOptions } from '../types';
import type { Period } from '../../generation/components/PeriodPicker';
import { useTheme } from '../../../contexts/ThemeContext';
import { useResponsiveFontSize } from '../../../utils/fontScaling';

import { CompactMultiSelectDropdown } from './CompactMultiSelectDropdown';
import { PeriodPicker } from '../../generation/components/PeriodPicker';

type FilterBarProps = {
  filters: YieldFilters;
  options: YieldOptions;
  disabled?: boolean;
  onCountriesChange: (values: string[]) => void;
  onPortfoliosChange: (values: string[]) => void;
  onAssetsChange: (values: string[]) => void;
  onMonthChange: (value: string | null) => void;
  onYearChange: (value: string | null) => void;
  onRangeChange: (value: { start: string; end: string } | null) => void;
  onReset: () => void;
};


export const FilterBar = ({
  filters,
  options,
  disabled = false,
  onCountriesChange,
  onPortfoliosChange,
  onAssetsChange,
  onMonthChange,
  onYearChange,
  onRangeChange,
  onReset,
}: FilterBarProps) => {
  const { theme } = useTheme();
  
  // Responsive font sizes (scaled up by 1.25x)
  const FONT_SCALE = 1.25;
  const buttonFontSize = useResponsiveFontSize(9, 13, 8) * FONT_SCALE;
  const labelFontSize = useResponsiveFontSize(8, 12, 7) * FONT_SCALE;
  const isDark = theme === 'dark';
  const labelColor = isDark ? '#94a3b8' : '#718096';
  
  const hasActiveFilters =
    filters.countries.length > 0 ||
    filters.portfolios.length > 0 ||
    filters.assets.length > 0 ||
    Boolean(filters.month) ||
    Boolean(filters.year) ||
    Boolean(filters.range);

  // Cascading filters are handled in useYieldData hook
  // Options here already reflect cascaded filtering

  const containerBg = theme === 'dark'
    ? 'linear-gradient(to bottom right, rgba(15, 23, 42, 0.9), rgba(30, 41, 59, 0.6), rgba(15, 23, 42, 0.9))'
    : 'linear-gradient(to bottom right, rgba(255, 255, 255, 0.95), rgba(248, 250, 252, 0.9), rgba(255, 255, 255, 0.95))';
  const containerBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(203, 213, 225, 0.8)';
  const containerShadow = theme === 'dark' 
    ? '0 20px 25px -5px rgba(0, 0, 0, 0.4)' 
    : '0 10px 15px -3px rgba(0, 0, 0, 0.1)';
  const resetButtonBg = theme === 'dark' 
    ? 'linear-gradient(to right, rgba(30, 41, 59, 0.9), rgba(15, 23, 42, 0.9))' 
    : 'linear-gradient(to right, rgba(255, 255, 255, 0.9), rgba(248, 250, 252, 0.9))';
  const resetButtonBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(203, 213, 225, 0.7)';
  const resetButtonText = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';

  // Map Yield filters to PeriodPicker Period
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

      // Treat full-year range as "year" selection
      if (start === `${year}-01` && end === `${year}-12`) {
        onMonthChange(null);
        onRangeChange(null);
        onYearChange(year);
      } else {
        onMonthChange(null);
        onYearChange(null);
        onRangeChange({ start, end });
      }
    } else if (period.month) {
      // Single-month selection:
      // Use explicit month filter and clear any existing year/range filters,
      // so downstream hooks treat this as a true single-month view.
      onMonthChange(period.month);
      onYearChange(null);
      onRangeChange(null);
    } else {
      onMonthChange(null);
      onYearChange(null);
      onRangeChange(null);
    }
  };

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
      <div className="relative flex items-end gap-2">
        <div className="min-w-0 flex-1">
          <CompactMultiSelectDropdown
            label="Countries"
            icon="🌍"
            options={options.countries}
            selected={filters.countries}
            onChange={onCountriesChange}
            placeholder={options.countries.length === 0 ? 'No countries available' : 'All Countries'}
            disabled={disabled || options.countries.length === 0}
          />
        </div>

        <div className="min-w-0 flex-1">
          <CompactMultiSelectDropdown
            label="Portfolios"
            icon="📊"
            options={options.portfolios}
            selected={filters.portfolios}
            onChange={onPortfoliosChange}
            placeholder={
              filters.countries.length === 0
                ? 'Select countries first'
                : options.portfolios.length === 0
                ? 'No portfolios available'
                : 'All Portfolios'
            }
            disabled={disabled || options.portfolios.length === 0}
          />
        </div>

        <div className="min-w-0 flex-1">
          <CompactMultiSelectDropdown
            label="Assets"
            icon="🏢"
            options={options.assets}
            selected={filters.assets}
            onChange={onAssetsChange}
            placeholder={
              filters.portfolios.length === 0
                ? 'Select portfolios first'
                : options.assets.length === 0
                ? 'No assets available'
                : 'All Assets'
            }
            disabled={disabled || options.assets.length === 0}
          />
        </div>

        <div className="min-w-0 flex-1">
          <div
            className="relative space-y-0.5"
            style={{ position: 'relative', overflow: 'visible' }}
          >
            <div
              className="flex items-center gap-0.5 font-semibold uppercase tracking-wide"
              style={{
                color: labelColor,
                fontSize: `${labelFontSize}px`,
              }}
            >
              <span style={{ fontSize: `${buttonFontSize}px` }}>📅</span>
              <span>Period</span>
            </div>
            <PeriodPicker
              defaultPeriod={defaultPeriod}
              onPeriodChange={handlePeriodChange}
              onReset={onReset}
            />
          </div>
        </div>

        <button
          type="button"
          onClick={onReset}
          disabled={disabled || !hasActiveFilters}
          className="shrink-0 self-end rounded-lg border px-3 py-1.5 font-semibold uppercase tracking-wide shadow-md transition-all duration-200 disabled:cursor-not-allowed disabled:opacity-40"
          style={{
            fontSize: `${buttonFontSize}px`,
            borderColor: resetButtonBorder,
            background: resetButtonBg,
            color: resetButtonText,
          }}
          onMouseEnter={(e) => {
            if (!disabled && hasActiveFilters) {
              e.currentTarget.style.borderColor = '#3b82f6';
              e.currentTarget.style.color = theme === 'dark' ? '#ffffff' : '#1a1a1a';
            }
          }}
          onMouseLeave={(e) => {
            if (!disabled && hasActiveFilters) {
              e.currentTarget.style.borderColor = resetButtonBorder;
              e.currentTarget.style.color = resetButtonText;
            }
          }}
        >
          Reset
        </button>
      </div>
    </section>
  );
};

