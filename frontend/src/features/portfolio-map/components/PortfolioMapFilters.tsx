/**
 * Portfolio Map Filters Component
 */
 
import { useMemo } from 'react';
import type { MapDataEntry, PortfolioMapFilters } from '../types';
import { normalizeValue, formatCODDate } from '../utils/performance';
import { CompactMultiSelectDropdown } from '../../yield/components/CompactMultiSelectDropdown';
import { useTheme } from '../../../contexts/ThemeContext';
import { useResponsiveFontSize } from '../../../utils/fontScaling';

interface PortfolioMapFiltersProps {
  mapData: MapDataEntry[];
  filters: PortfolioMapFilters;
  onFiltersChange: (filters: PortfolioMapFilters) => void;
  onReset: () => void;
}

type FilterField =
  | 'country'
  | 'plantType'
  | 'installationType'
  | 'portfolio'
  | 'assetNo'
  | 'offtaker'
  | 'cod';

interface FilterConfig {
  field: FilterField;
  label: string;
  icon: string;
  column: keyof MapDataEntry;
  formatter?: (value: string) => string;
}

const filterConfigs: FilterConfig[] = [
  { field: 'country', label: 'Country', icon: '🌍', column: 'country' },
  { field: 'plantType', label: 'Plant Type', icon: '⚡', column: 'plant_type' },
  { field: 'installationType', label: 'Installation', icon: '🏗️', column: 'installation_type' },
  { field: 'portfolio', label: 'Portfolio', icon: '📂', column: 'portfolio' },
  { field: 'assetNo', label: 'Asset No', icon: '🏭', column: 'asset_no' },
  { field: 'offtaker', label: 'Offtaker', icon: '🤝', column: 'offtaker' },
  {
    field: 'cod',
    label: 'COD',
    icon: '📅',
    column: 'cod',
    formatter: formatCODDate,
  },
];

export function PortfolioMapFilters({
  mapData,
  filters,
  onFiltersChange,
  onReset,
}: PortfolioMapFiltersProps) {
  const { theme } = useTheme();
  
  // Responsive font sizes
  const labelFontSize = useResponsiveFontSize(8, 12, 7);
  const buttonFontSize = useResponsiveFontSize(9, 13, 8);
  
  // Theme-aware colors
  const containerBg = theme === 'dark'
    ? 'linear-gradient(to bottom right, rgba(15, 23, 42, 0.9), rgba(30, 41, 59, 0.6), rgba(15, 23, 42, 0.9))'
    : 'linear-gradient(to bottom right, rgba(255, 255, 255, 0.95), rgba(248, 250, 252, 0.9), rgba(255, 255, 255, 0.95))';
  const containerBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(226, 232, 240, 0.8)';
  const resetButtonBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.8)' : '#ffffff';
  const resetButtonBorder = theme === 'dark' ? 'rgba(71, 85, 105, 0.7)' : 'rgba(203, 213, 225, 0.7)';
  const resetButtonText = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';
  
  // Get unique values for each filter from the filtered data
  const getFilterOptions = useMemo(() => {
    return (config: FilterConfig): string[] => {
      // Build active filters excluding the current filter
      const activeFilters: Record<string, string[]> = {};
      filterConfigs.forEach((cfg) => {
        if (cfg.field !== config.field) {
          const filterValues = filters[cfg.field];
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

      // Get unique values - use ALL mapData for initial options, not just filtered
      const dataSource = Object.keys(activeFilters).length === 0 ? mapData : filteredData;
      const rawValues = dataSource
        .map((row) => {
          const val = row[config.column as keyof MapDataEntry];
          return normalizeValue(val);
        })
        .filter(Boolean);

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

  const hasActiveFilters = Object.values(filters).some(
    (value) => Array.isArray(value) && value.length > 0,
  );

  return (
    <section 
      className="relative rounded-xl p-2 shadow-xl"
      style={{
        border: `1px solid ${containerBorder}`,
        background: containerBg,
        transition: 'background 0.3s ease, border-color 0.3s ease',
      }}
    >
      <div 
        className="pointer-events-none absolute inset-0 rounded-xl" 
        style={{
          background: theme === 'dark'
            ? 'radial-gradient(circle at top, rgba(56,189,248,0.12), transparent 55%), radial-gradient(circle at bottom, rgba(167,139,250,0.12), transparent 60%)'
            : 'radial-gradient(circle at top, rgba(0, 114, 206, 0.08), transparent 55%), radial-gradient(circle at bottom, rgba(0, 198, 255, 0.08), transparent 60%)',
        }}
      />
      <div className="relative grid grid-cols-2 gap-2 md:grid-cols-4 lg:grid-cols-8">
        {filterConfigs.map((config) => {
          const options = getFilterOptions(config);
          const selected = filters[config.field] || [];

          return (
            <div key={config.field} className="min-w-0">
              <CompactMultiSelectDropdown
                label={config.label}
                icon={config.icon}
                options={options}
                selected={selected}
                placeholder="All"
                onChange={(values) => handleFilterChange(config.field, values)}
                optionFormatter={config.formatter}
              />
            </div>
          );
        })}
        
        <div>
          <div className="font-semibold uppercase tracking-wide text-transparent" style={{ fontSize: `${labelFontSize}px` }}>
            &nbsp;
          </div>
          <button
            type="button"
            onClick={onReset}
            disabled={!hasActiveFilters}
            className="rounded-lg px-2 py-0.5 font-semibold uppercase tracking-wide shadow-inner transition hover:border-red-500 hover:bg-red-500/20 hover:text-red-300 focus:outline-none focus:ring-1 focus:ring-red-500 disabled:cursor-not-allowed disabled:opacity-30"
            style={{
              fontSize: `${buttonFontSize}px`,
              border: `1px solid ${resetButtonBorder}`,
              background: resetButtonBg,
              color: resetButtonText,
              boxShadow: theme === 'dark' ? 'inset 0 2px 4px rgba(0, 0, 0, 0.4)' : 'inset 0 2px 4px rgba(0, 0, 0, 0.1)',
            }}
          >
            Reset
          </button>
        </div>
      </div>
    </section>
  );
}
