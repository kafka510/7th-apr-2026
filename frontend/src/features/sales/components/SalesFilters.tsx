/**
 * Sales Dashboard Filters Component - React Style V1
 */
 
import { useMemo } from 'react';
import type { MapDataEntry, YieldDataEntry, SalesFilters } from '../types';
import { normalizeValue } from '../utils/dataUtils';
import { CompactMultiSelectDropdown } from '../../yield/components/CompactMultiSelectDropdown';
import { PeriodPicker, type Period } from '../../generation/components/PeriodPicker';
import { useTheme } from '../../../contexts/ThemeContext';
import { useResponsiveFontSize } from '../../../utils/fontScaling';

interface SalesFiltersProps {
  mapData: MapDataEntry[];
  yieldData: YieldDataEntry[];
  filters: SalesFilters;
  onFiltersChange: (filters: SalesFilters) => void;
  onReset: () => void;
}

type FilterField = 'country' | 'portfolio' | 'installation';

interface FilterConfig {
  field: FilterField;
  label: string;
  column: keyof MapDataEntry;
  icon: string;
}

const filterConfigs: FilterConfig[] = [
  { field: 'country', label: 'Country', column: 'country', icon: '🌍' },
  { field: 'portfolio', label: 'Portfolio', column: 'portfolio', icon: '📂' },
  { field: 'installation', label: 'Installation', column: 'installation_type', icon: '🏗️' },
];

export function SalesFilters(props: SalesFiltersProps) {
  const { mapData, filters, onFiltersChange, onReset } = props;
  const { theme } = useTheme();
  
  // Responsive font sizes
  const buttonFontSize = useResponsiveFontSize(10, 14, 9);
  
  // Get unique values for each filter from the filtered data
  const getFilterOptions = useMemo(() => {
    return (config: FilterConfig): string[] => {
      // Build active filters excluding the current filter
      const activeFilters: Record<string, string[]> = {};
      filterConfigs.forEach((cfg) => {
        if (cfg.field !== config.field) {
          const filterValues = cfg.field === 'country' ? filters.country :
                              cfg.field === 'portfolio' ? filters.portfolio :
                              cfg.field === 'installation' ? filters.installation : undefined;
          if (filterValues && filterValues.length > 0) {
            activeFilters[cfg.column] = filterValues;
          }
        }
      });

      // Filter data based on active filters
      let filteredData = mapData;
      Object.entries(activeFilters).forEach(([col, values]) => {
        filteredData = filteredData.filter((row) => {
          const rowVal = normalizeValue(row[col as keyof MapDataEntry]);
          return values.includes(rowVal);
        });
      });

      // Get unique values - use ALL mapData for initial options
      const dataSource = Object.keys(activeFilters).length === 0 ? mapData : filteredData;
      const rawValues = dataSource.map((row) => {
        const val = row[config.column as keyof MapDataEntry];
        return normalizeValue(val);
      }).filter(Boolean);

      const uniqueValues = [...new Set(rawValues)].sort((a, b) => a.localeCompare(b));
      return uniqueValues;
    };
  }, [mapData, filters]);

  const handleFilterChange = (field: FilterField, values: string[]) => {
    onFiltersChange({
      ...filters,
      [field]: values.length > 0 ? values : undefined,
    });
  };

  // Map existing sales filters to PeriodPicker Period
  const defaultPeriod: Period = (() => {
    if (filters.selectedRange) {
      return { range: { start: filters.selectedRange.start, end: filters.selectedRange.end } };
    }
    if (filters.selectedMonth) {
      return { month: filters.selectedMonth };
    }
    if (filters.selectedYear) {
      return {
        range: {
          start: `${filters.selectedYear}-01`,
          end: `${filters.selectedYear}-12`,
        },
      };
    }
    return {};
  })();

  const handlePeriodChange = (period: Period) => {
    if (period.range) {
      const { start, end } = period.range;
      const year = start.split('-')[0];

      // Full-year selection -> treat as year filter
      if (start === `${year}-01` && end === `${year}-12`) {
        onFiltersChange({
          ...filters,
          selectedMonth: null,
          selectedRange: null,
          selectedYear: year,
        });
      } else {
        onFiltersChange({
          ...filters,
          selectedMonth: null,
          selectedYear: null,
          selectedRange: { start, end },
        });
      }
    } else if (period.month) {
      const year = period.month.split('-')[0];
      onFiltersChange({
        ...filters,
        selectedMonth: period.month,
        selectedYear: year,
        selectedRange: null,
      });
    } else {
      onFiltersChange({
        ...filters,
        selectedMonth: null,
        selectedYear: null,
        selectedRange: null,
      });
    }
  };

  const bgColor = theme === 'dark' 
    ? 'linear-gradient(to bottom right, rgba(15, 23, 42, 0.9), rgba(30, 41, 59, 0.6), rgba(15, 23, 42, 0.9))'
    : 'linear-gradient(to bottom right, #ffffff, #f8fafc, #ffffff)';
  const borderColor = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(226, 232, 240, 0.8)';
  const textColor = theme === 'dark' ? '#f1f5f9' : '#1a1a1a';

  return (
    <div 
      className="rounded-xl p-2 shadow-xl"
      style={{ 
        position: 'relative', 
        zIndex: 1000,
        background: bgColor,
        border: `1px solid ${borderColor}`,
        transition: 'background 0.3s ease, border-color 0.3s ease',
      }}
    >
      <div className="grid grid-cols-2 items-end gap-2 md:grid-cols-4 lg:grid-cols-5">
        {filterConfigs.map((config) => {
          const options = getFilterOptions(config);
          const selected = config.field === 'country' ? (filters.country || []) :
                          config.field === 'portfolio' ? (filters.portfolio || []) :
                          config.field === 'installation' ? (filters.installation || []) : [];

          return (
            <CompactMultiSelectDropdown
              key={config.field}
              label={config.label}
              options={options}
              selected={selected}
              onChange={(values) => handleFilterChange(config.field, values)}
              icon={<span>{config.icon}</span>}
            />
          );
        })}

        {/* Period Filter - PeriodPicker (shared with Generation Report) */}
        <PeriodPicker
          defaultPeriod={defaultPeriod}
          onPeriodChange={handlePeriodChange}
          onReset={onReset}
        />

        {/* Reset Button */}
        <button
          type="button"
          onClick={onReset}
          className="flex w-full items-center justify-center rounded-lg px-2 py-1 font-medium transition"
          style={{
            border: `1px solid ${theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : 'rgba(203, 213, 225, 0.7)'}`,
            backgroundColor: theme === 'dark' ? 'rgba(15, 23, 42, 0.8)' : 'rgba(248, 250, 252, 0.8)',
            color: textColor,
            boxShadow: theme === 'dark' ? 'inset 0 2px 4px rgba(0, 0, 0, 0.4)' : 'inset 0 2px 4px rgba(0, 0, 0, 0.1)',
            fontSize: `${buttonFontSize}px`,
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.borderColor = '#0072ce';
            e.currentTarget.style.color = theme === 'dark' ? '#fff' : '#0072ce';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.borderColor = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : 'rgba(203, 213, 225, 0.7)';
            e.currentTarget.style.color = textColor;
          }}
        >
          Reset
        </button>
      </div>
    </div>
  );
}
