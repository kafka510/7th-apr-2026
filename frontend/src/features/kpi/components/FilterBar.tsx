import type { KpiFilterOptions, KpiFilterState } from '../types';
import { useTheme } from '../../../contexts/ThemeContext';
import { useResponsiveFontSize } from '../../../utils/fontScaling';

import { DateRangePicker } from './DateRangePicker';
import { MultiSelectDropdown } from './MultiSelectDropdown';

type FilterBarProps = {
  filters: KpiFilterState;
  options: KpiFilterOptions;
  disabled?: boolean;
  onCountriesChange: (values: string[]) => void;
  onPortfoliosChange: (values: string[]) => void;
  onAssetsChange: (values: string[]) => void;
  onDateChange?: (value: string | null) => void; // Deprecated: use onStartDateChange/onEndDateChange
  onStartDateChange?: (value: string | null) => void;
  onEndDateChange?: (value: string | null) => void;
  onReset: () => void;
};

export const FilterBar = ({
  filters,
  options,
  disabled = false,
  onCountriesChange,
  onPortfoliosChange,
  onAssetsChange,
  onDateChange, // Deprecated
  onStartDateChange,
  onEndDateChange,
  onReset,
}: FilterBarProps) => {
  const { theme } = useTheme();
  
  // Responsive font sizes
  const labelFontSize = useResponsiveFontSize(9, 13, 8);
  const buttonFontSize = useResponsiveFontSize(9, 13, 8);
  
  const hasActiveFilters =
    filters.countries.length > 0 ||
    filters.portfolios.length > 0 ||
    filters.assets.length > 0 ||
    Boolean(filters.startDate) ||
    Boolean(filters.endDate) ||
    Boolean(filters.date); // Backward compatibility

  const containerBg = theme === 'dark'
    ? 'linear-gradient(to bottom right, rgba(15, 23, 42, 0.9), rgba(30, 41, 59, 0.6), rgba(15, 23, 42, 0.9))'
    : 'linear-gradient(to bottom right, rgba(255, 255, 255, 0.95), rgba(248, 250, 252, 0.9), rgba(255, 255, 255, 0.95))';
  const containerShadow = theme === 'dark' 
    ? '0 20px 25px -5px rgba(0, 0, 0, 0.5)' 
    : '0 10px 15px -3px rgba(0, 0, 0, 0.1)';
  const labelColor = theme === 'dark' ? '#94a3b8' : '#64748b';
  const resetButtonBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.8)' : '#ffffff';
  const resetButtonBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(203, 213, 225, 0.7)';
  const resetButtonText = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';

  return (
    <section 
      className="relative rounded-xl p-1.5"
      style={{
        background: containerBg,
        boxShadow: containerShadow,
      }}
    >
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(56,189,248,0.08),_transparent_55%),radial-gradient(circle_at_bottom,_rgba(167,139,250,0.08),_transparent_60%)]" />
      <div className="relative">
        <div className="flex items-center gap-2">
          <div className="grid flex-1 grid-cols-5 gap-2">
            <MultiSelectDropdown
              label="Countries"
              icon="🌍"
              options={options.countries}
              selected={filters.countries}
              onChange={onCountriesChange}
              placeholder={options.countries.length === 0 ? 'No countries available' : 'All Countries'}
              disabled={disabled || options.countries.length === 0}
            />

            <MultiSelectDropdown
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
              disabled={disabled || filters.countries.length === 0 || options.portfolios.length === 0}
            />

            <MultiSelectDropdown
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
              disabled={disabled || filters.portfolios.length === 0 || options.assets.length === 0}
            />

            <div className="relative col-span-2 space-y-1">
              <div 
                className="flex items-center gap-1 font-semibold uppercase tracking-wide"
                style={{ color: labelColor, fontSize: `${labelFontSize}px` }}
              >
                <span className="text-xs">🗓️</span>
                <span>Date Range</span>
              </div>
              <DateRangePicker
                startDate={filters.startDate}
                endDate={filters.endDate}
                onStartDateChange={(value) => {
                  if (onStartDateChange) {
                    onStartDateChange(value);
                  } else if (onDateChange) {
                    // Fallback for backward compatibility
                    onDateChange(value);
                  }
                }}
                onEndDateChange={(value) => {
                  if (onEndDateChange) {
                    onEndDateChange(value);
                  } else if (onDateChange) {
                    // Fallback for backward compatibility
                    onDateChange(value);
                  }
                }}
                disabled={disabled}
                maxDate={new Date().toISOString().slice(0, 10)}
              />
            </div>
          </div>

          <button
            type="button"
            onClick={onReset}
            disabled={disabled || !hasActiveFilters}
            className="shrink-0 self-end rounded-full border px-3 py-1 font-semibold uppercase tracking-wide transition hover:border-sky-500 disabled:cursor-not-allowed disabled:opacity-40"
            style={{
              borderColor: resetButtonBorder,
              backgroundColor: resetButtonBg,
              color: resetButtonText,
              fontSize: `${buttonFontSize}px`,
            }}
            onMouseEnter={(e) => {
              if (!disabled && hasActiveFilters) {
                e.currentTarget.style.color = theme === 'dark' ? '#ffffff' : '#1a1a1a';
              }
            }}
            onMouseLeave={(e) => {
              if (!disabled && hasActiveFilters) {
                e.currentTarget.style.color = resetButtonText;
              }
            }}
          >
            Reset All
          </button>
        </div>
      </div>
    </section>
  );
};

