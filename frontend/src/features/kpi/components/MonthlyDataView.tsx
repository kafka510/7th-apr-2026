import { useState, useEffect, useMemo } from 'react';
import { useTheme } from '../../../contexts/ThemeContext';
import { useResponsiveFontSize } from '../../../utils/fontScaling';

import { fetchYieldData } from '../api';
import type { YieldDataEntry } from '../api';
import { MultiSelectDropdown } from './MultiSelectDropdown';
import { MonthlyChart } from './MonthlyChart';
import { PeriodPicker, type Period } from '../../generation/components/PeriodPicker';

type ChartType = 'bar' | 'stacked';

const MONTHLY_FILTERS_STORAGE_KEY = 'dashboard-filters-kpi-monthly';

type MonthlyFiltersState = {
  chartType: ChartType;
  selectedParameters: string[];
  selectedCountries: string[];
  selectedPortfolios: string[];
  selectedAssets: string[];
  selectedMonth: string | null;
  selectedYear: number | null;
  selectedRange: { start: string; end: string } | null;
};

type MonthlyDataViewProps = {
  options?: {
    countries: string[];
    portfolios: string[];
    assets: string[];
  };
};

const CHART_TYPES: { value: ChartType; label: string }[] = [
  { value: 'bar', label: 'Bar Chart' },
  { value: 'stacked', label: 'Stacked Chart' },
];

const PARAMETERS = [
  { value: 'ic_approved_budget', label: 'IC Approved Budget' },
  { value: 'expected_budget', label: 'Expected Budget' },
  { value: 'actual_generation', label: 'Actual Generation' },
  { value: 'weather_loss_or_gain', label: 'Weather Loss/Gain' },
  { value: 'grid_curtailment', label: 'Grid Curtailment' },
  { value: 'grid_outage', label: 'Grid Outage' },
  { value: 'operation_budget', label: 'Operation Budget' },
  { value: 'breakdown_loss', label: 'Breakdown Loss' },
  { value: 'unclassified_loss', label: 'Unclassified Loss' },
  { value: 'expected_pr', label: 'Expected PR' },
  { value: 'actual_pr', label: 'Actual PR' },
];

// Normalize country names (matches old implementation)
const normalizeCountry = (val: string | null | undefined): string => {
  const v = (val || '').toString().trim();
  const lower = v.toLowerCase();
  const map: Record<string, string> = {
    jp: 'jp',
    japan: 'jp',
    kr: 'kr',
    korea: 'kr',
    sg: 'sg',
    singapore: 'sg',
    tw: 'tw',
    taiwan: 'tw',
  };
  return map[lower] || lower;
};

// Helper to check if row matches filter (matches old implementation)
const matchesFilter = (
  row: YieldDataEntry,
  filterValues: string[],
  field: 'countries' | 'portfolios' | 'assets'
): boolean => {
  if (!filterValues || filterValues.length === 0) {
    return true; // No filter = show all
  }

  let rowValue: string;
  if (field === 'countries') {
    rowValue = (row.country || '').trim();
    const rowCountry = normalizeCountry(rowValue);
    const filterCountries = filterValues.map(normalizeCountry);
    return filterCountries.includes(rowCountry);
  } else if (field === 'portfolios') {
    rowValue = (row.portfolio || '').trim();
  } else if (field === 'assets') {
    // Check multiple asset fields (matches old implementation)
    const rowRecord = row as Record<string, unknown>;
    rowValue =
      (rowRecord.asset_code as string) ||
      row.assetno ||
      (rowRecord.asset_number as string) ||
      (rowRecord.asset as string) ||
      '';
  } else {
    const rowRecord = row as Record<string, unknown>;
    rowValue = (rowRecord[field] as string) || '';
  }

  const rowValueNormalized = (rowValue || '').toString().trim().toLowerCase();
  const filterValuesNormalized = filterValues.map((v) => (v || '').toString().trim().toLowerCase());
  return filterValuesNormalized.includes(rowValueNormalized);
};

export const MonthlyDataView = ({ options }: MonthlyDataViewProps) => {
  const [loading, setLoading] = useState(true);
  const [yieldData, setYieldData] = useState<YieldDataEntry[]>([]);
  const [error, setError] = useState<string | null>(null);

  // Load saved monthly filters from localStorage (if any)
  const initialFilters: MonthlyFiltersState = (() => {
    try {
      if (typeof window === 'undefined') {
        const currentYear = new Date().getFullYear();
        return {
          chartType: 'bar',
          selectedParameters: ['actual_generation'],
          selectedCountries: [],
          selectedPortfolios: [],
          selectedAssets: [],
          selectedMonth: null,
          selectedYear: currentYear, // Initialize with current year
          selectedRange: null,
        };
      }
      const raw = window.localStorage.getItem(MONTHLY_FILTERS_STORAGE_KEY);
      if (!raw) {
        // Default to current year when no saved filters exist
        const currentYear = new Date().getFullYear();
        return {
          chartType: 'bar',
          selectedParameters: ['actual_generation'],
          selectedCountries: [],
          selectedPortfolios: [],
          selectedAssets: [],
          selectedMonth: null,
          selectedYear: currentYear, // Initialize with current year
          selectedRange: null,
        };
      }
      const parsed = JSON.parse(raw) as Partial<MonthlyFiltersState>;
      return {
        chartType: parsed.chartType === 'stacked' ? 'stacked' : 'bar',
        selectedParameters: Array.isArray(parsed.selectedParameters) && parsed.selectedParameters.length > 0
          ? parsed.selectedParameters
          : ['actual_generation'],
        selectedCountries: Array.isArray(parsed.selectedCountries) ? parsed.selectedCountries : [],
        selectedPortfolios: Array.isArray(parsed.selectedPortfolios) ? parsed.selectedPortfolios : [],
        selectedAssets: Array.isArray(parsed.selectedAssets) ? parsed.selectedAssets : [],
        selectedMonth: parsed.selectedMonth ?? null,
        // If no saved year and no saved month/range, default to current year
        selectedYear: typeof parsed.selectedYear === 'number' 
          ? parsed.selectedYear 
          : (parsed.selectedMonth || (parsed.selectedRange && parsed.selectedRange.start)) 
            ? null // If month or range exists, let MonthPicker derive year from it
            : new Date().getFullYear(), // Otherwise default to current year
        selectedRange: parsed.selectedRange && typeof parsed.selectedRange === 'object'
          ? { start: (parsed.selectedRange as any).start, end: (parsed.selectedRange as any).end }
          : null,
      };
    } catch {
      const currentYear = new Date().getFullYear();
      return {
        chartType: 'bar',
        selectedParameters: ['actual_generation'],
        selectedCountries: [],
        selectedPortfolios: [],
        selectedAssets: [],
        selectedMonth: null,
        selectedYear: currentYear, // Initialize with current year
        selectedRange: null,
      };
    }
  })();

  // Filter states
  const [chartType, setChartType] = useState<ChartType>(initialFilters.chartType);
  const [selectedParameters, setSelectedParameters] = useState<string[]>(initialFilters.selectedParameters);
  const [selectedCountries, setSelectedCountries] = useState<string[]>(initialFilters.selectedCountries);
  const [selectedPortfolios, setSelectedPortfolios] = useState<string[]>(initialFilters.selectedPortfolios);
  const [selectedAssets, setSelectedAssets] = useState<string[]>(initialFilters.selectedAssets);
  const [selectedMonth, setSelectedMonth] = useState<string | null>(initialFilters.selectedMonth);
  const [selectedYear, setSelectedYear] = useState<number | null>(initialFilters.selectedYear);
  const [selectedRange, setSelectedRange] = useState<{ start: string; end: string } | null>(initialFilters.selectedRange);
  const [updateKey, setUpdateKey] = useState(0);
  
  const { theme } = useTheme();
  
  // Responsive font sizes
  const labelFontSize = useResponsiveFontSize(9, 13, 8);
  const darkMode = theme === 'dark';

  // Extract unique options from yield data
  const yieldOptions = useMemo(() => {
    const countries = new Set<string>();
    const portfolios = new Set<string>();
    const assets = new Set<string>();
    const months = new Set<string>();

    yieldData.forEach((entry) => {
      if (entry.country) {
        countries.add(entry.country.trim());
      }
      if (entry.portfolio) {
        portfolios.add(entry.portfolio.trim());
      }
      // Check multiple asset fields
      const entryRecord = entry as Record<string, unknown>;
      const assetValue =
        (entryRecord.asset_code as string) || entry.assetno || (entryRecord.asset_number as string) || (entryRecord.asset as string) || '';
      if (assetValue) {
        assets.add(String(assetValue).trim());
      }
      // Extract months
      if (entry.month) {
        const monthStr = String(entry.month).trim();
        if (monthStr.includes('-')) {
          months.add(monthStr);
        }
      }
    });

    return {
      countries: Array.from(countries).sort(),
      portfolios: Array.from(portfolios).sort(),
      assets: Array.from(assets).sort(),
      months: Array.from(months).sort(),
    };
  }, [yieldData]);

  // Use yield options if available, otherwise fall back to passed options
  const filterOptions = useMemo(() => {
    if (yieldOptions.countries.length > 0 || yieldOptions.portfolios.length > 0 || yieldOptions.assets.length > 0) {
      return yieldOptions;
    }
    return options || { countries: [], portfolios: [], assets: [] };
  }, [yieldOptions, options]);

  // Fetch yield data
  useEffect(() => {
    let cancelled = false;

    async function loadData() {
      try {
        setLoading(true);
        setError(null);
        const data = await fetchYieldData();
        if (!cancelled) {
          setYieldData(data);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load yield data');
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadData();

    return () => {
      cancelled = true;
    };
  }, []);

  // Filter data based on selections (matches old getFilteredYieldData logic)
  const filteredData = useMemo(() => {
    if (!yieldData || yieldData.length === 0) {
      return [];
    }

    return yieldData.filter((row) => {
      // Country filter
      const countryMatch = matchesFilter(row, selectedCountries, 'countries');

      // Portfolio filter
      const portfolioMatch = matchesFilter(row, selectedPortfolios, 'portfolios');

      // Asset filter
      const assetMatch = matchesFilter(row, selectedAssets, 'assets');

      // Period filter - priority: Range > Month > Year (matches Yield Report logic)
      let periodMatch = true;
      if (!row.month) {
        periodMatch = false;
      } else {
        const rowMonth = String(row.month).trim();
        
        const hasRange = selectedRange && selectedRange.start && selectedRange.end;
        const hasMonth = Boolean(selectedMonth);
        const hasYear = Boolean(selectedYear);
        
        if (hasRange) {
          // Range selected: show data for the selected month range
          periodMatch = rowMonth >= selectedRange!.start && rowMonth <= selectedRange!.end;
        } else if (hasMonth) {
          // Month selected: show only that month
          periodMatch = rowMonth === selectedMonth;
        } else if (hasYear) {
          // Year selected but no specific month: show all months for that year
          periodMatch = rowMonth.startsWith(String(selectedYear));
        }
      }

      return countryMatch && portfolioMatch && assetMatch && periodMatch;
    });
  }, [yieldData, selectedCountries, selectedPortfolios, selectedAssets, selectedMonth, selectedYear, selectedRange]);

  // When Monthly view's data has finished loading, signal that filters/data are ready
  // so Playwright/export can capture the correct monthly chart state.
  useEffect(() => {
    if (!loading) {
      document.body.setAttribute('data-filters-ready', 'true');
      window.dispatchEvent(
        new CustomEvent('dashboard-filters-ready', { detail: { dashboardId: 'kpi' } }),
      );
    } else {
      document.body.removeAttribute('data-filters-ready');
    }
  }, [loading]);

  // Persist monthly filters to localStorage whenever they change
  useEffect(() => {
    try {
      const state: MonthlyFiltersState = {
        chartType,
        selectedParameters,
        selectedCountries,
        selectedPortfolios,
        selectedAssets,
        selectedMonth,
        selectedYear,
        selectedRange,
      };
      if (typeof window !== 'undefined') {
        window.localStorage.setItem(MONTHLY_FILTERS_STORAGE_KEY, JSON.stringify(state));
      }
    } catch (e) {
      console.warn('Failed to save monthly KPI filters to localStorage:', e);
    }
  }, [chartType, selectedParameters, selectedCountries, selectedPortfolios, selectedAssets, selectedMonth, selectedYear, selectedRange]);

  const handleReset = () => {
    // Reset to current year only - explicitly clear month and range
    // This ensures the chart shows only current year monthly data
    const currentYear = new Date().getFullYear();
    setChartType('bar');
    setSelectedParameters(['actual_generation']); // Reset to default parameter
    setSelectedCountries([]);
    setSelectedPortfolios([]);
    setSelectedAssets([]);
    setSelectedMonth(null);
    setSelectedYear(currentYear); // Reset to current year, not null
    setSelectedRange(null);
    try {
      if (typeof window !== 'undefined') {
        window.localStorage.removeItem(MONTHLY_FILTERS_STORAGE_KEY);
      }
    } catch (e) {
      console.warn('Failed to clear monthly KPI filters from localStorage:', e);
    }
  };

  const handleUpdate = () => {
    // Force chart update by incrementing key to trigger full re-render
    // This ensures the chart component remounts and recalculates everything
    setUpdateKey((prev) => prev + 1);
    // Also trigger a small delay to ensure state updates are processed
    setTimeout(() => {
      // Additional update trigger if needed
    }, 100);
  };

  // Limit parameters based on chart type
  const maxParameters = chartType === 'stacked' ? 1 : 4;
  const parameterOptions = PARAMETERS.map((p) => ({ value: p.value, label: p.label }));

  // Determine if filters are applied
  const hasFilters = selectedCountries.length > 0 || selectedPortfolios.length > 0 || selectedAssets.length > 0 || 
    selectedMonth !== null || selectedYear !== null || selectedRange !== null;


  const filtersBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.5)' : 'rgba(248, 250, 252, 0.9)';
  const filtersBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : 'rgba(203, 213, 225, 0.7)';
  const errorBg = theme === 'dark' ? 'rgba(127, 29, 29, 0.3)' : 'rgba(254, 242, 242, 0.8)';
  const errorBorder = theme === 'dark' ? 'rgba(239, 68, 68, 0.4)' : 'rgba(220, 38, 38, 0.3)';
  const errorText = theme === 'dark' ? '#fca5a5' : '#991b1b';

  // Map current period filters to Generation Report style Period
  const defaultPeriod: Period = useMemo(() => {
    if (selectedRange) {
      return { range: { start: selectedRange.start, end: selectedRange.end } };
    }
    if (selectedMonth) {
      return { month: selectedMonth };
    }
    if (selectedYear !== null) {
      return {
        range: {
          start: `${selectedYear}-01`,
          end: `${selectedYear}-12`,
        },
      };
    }
    return {};
  }, [selectedMonth, selectedYear, selectedRange]);

  // When user selects a year or range, pass the full month range so the chart shows all months on the x-axis (even if data exists only for some)
  const displayMonthRange = useMemo((): { start: string; end: string } | null => {
    if (selectedRange && selectedRange.start && selectedRange.end) {
      return { start: selectedRange.start, end: selectedRange.end };
    }
    if (selectedYear !== null) {
      return { start: `${selectedYear}-01`, end: `${selectedYear}-12` };
    }
    if (selectedMonth) {
      return { start: selectedMonth, end: selectedMonth };
    }
    return null;
  }, [selectedMonth, selectedYear, selectedRange]);

  const handlePeriodChange = (period: Period) => {
    if (period.range) {
      const { start, end } = period.range;
      const year = start.split('-')[0];

      // Treat full-year range as "year" selection
      if (start === `${year}-01` && end === `${year}-12`) {
        setSelectedMonth(null);
        setSelectedYear(Number(year));
        setSelectedRange(null);
      } else {
        setSelectedMonth(null);
        setSelectedYear(null);
        setSelectedRange({ start, end });
      }
    } else if (period.month) {
      const year = period.month.split('-')[0];
      setSelectedMonth(period.month);
      setSelectedYear(Number(year));
      setSelectedRange(null);
    } else {
      // No period selected
      setSelectedMonth(null);
      setSelectedYear(null);
      setSelectedRange(null);
    }
  };

  return (
    <div className="w-full space-y-2 overflow-x-hidden p-1">
      {/* Filters - Single Row */}
      <div 
        className="overflow-visible rounded-lg border p-2"
        style={{
          borderColor: filtersBorder,
          backgroundColor: filtersBg,
        }}
      >
        <div className="flex flex-wrap items-end gap-2">
          {/* Chart Type */}
          <div className="relative flex min-w-[120px] flex-col space-y-1">
            <label 
              className="flex items-center gap-1 font-semibold uppercase tracking-wide"
              style={{ color: theme === 'dark' ? '#94a3b8' : '#64748b', fontSize: `${labelFontSize}px` }}
            >
              <span>Chart Type</span>
            </label>
            <select
              value={chartType}
              onChange={(e) => {
                setChartType(e.target.value as ChartType);
                if (e.target.value === 'stacked' && selectedParameters.length > 1) {
                  setSelectedParameters([selectedParameters[0] || 'actual_generation']);
                }
              }}
              className="flex h-auto w-full items-center justify-between rounded-lg border px-2 py-1 text-left text-xs font-medium shadow-inner transition hover:border-sky-500 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500/30"
              style={{
                borderColor: theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : 'rgba(203, 213, 225, 0.7)',
                backgroundColor: theme === 'dark' ? 'rgba(15, 23, 42, 0.8)' : '#ffffff',
                color: theme === 'dark' ? '#e2e8f0' : '#1a1a1a',
                boxShadow: theme === 'dark' ? 'inset 0 2px 4px rgba(0, 0, 0, 0.4)' : 'inset 0 2px 4px rgba(0, 0, 0, 0.1)',
              }}
            >
              {CHART_TYPES.map((type) => (
                <option key={type.value} value={type.value}>
                  {type.label}
                </option>
              ))}
            </select>
          </div>

          {/* Parameters */}
          <div className="flex min-w-[150px] flex-col">
            <MultiSelectDropdown
              label={`Parameters (Max ${maxParameters})`}
              options={parameterOptions.map((p) => p.value)}
              selected={selectedParameters}
              onChange={(values: string[]) => {
                // Allow empty selection (for reset) or up to maxParameters
                if (values.length === 0 || values.length <= maxParameters) {
                  setSelectedParameters(values);
                }
              }}
              placeholder={`Select Parameters (Max ${maxParameters})`}
              disabled={loading}
              optionFormatter={(value: string) => {
                const param = parameterOptions.find((p) => p.value === value);
                return param ? param.label : value.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase());
              }}
            />
          </div>

          {/* Country Filter */}
          <div className="flex min-w-[120px] flex-col">
            <MultiSelectDropdown
              label="Country"
              options={filterOptions.countries}
              selected={selectedCountries}
              onChange={setSelectedCountries}
              placeholder="All Countries"
              disabled={loading}
            />
          </div>

          {/* Portfolio Filter */}
          <div className="flex min-w-[120px] flex-col">
            <MultiSelectDropdown
              label="Portfolio"
              options={filterOptions.portfolios}
              selected={selectedPortfolios}
              onChange={setSelectedPortfolios}
              placeholder="All Portfolios"
              disabled={loading}
            />
          </div>

          {/* Asset Filter */}
          <div className="flex min-w-[120px] flex-col">
            <MultiSelectDropdown
              label="Asset"
              options={filterOptions.assets}
              selected={selectedAssets}
              onChange={setSelectedAssets}
              placeholder="All Assets"
              disabled={loading}
            />
          </div>

          {/* Period Filter - MonthPicker Component */}
          <div className="flex min-w-[180px] flex-col">
            <PeriodPicker
              defaultPeriod={defaultPeriod}
              onPeriodChange={handlePeriodChange}
              onReset={handleReset}
            />
          </div>

          {/* Action Buttons */}
          <div className="flex gap-1">
            <button
              onClick={handleUpdate}
              className="h-7 rounded-lg bg-gradient-to-r from-blue-600 to-blue-700 px-3 text-xs font-semibold text-white transition-all hover:from-blue-700 hover:to-blue-800 hover:shadow-lg disabled:opacity-50"
              disabled={loading}
            >
              Update
            </button>
            <button
              onClick={handleReset}
              className="h-7 rounded-lg bg-gradient-to-r from-red-500 to-red-600 px-3 text-xs font-semibold text-white transition-all hover:from-red-600 hover:to-red-700 hover:shadow-lg disabled:opacity-50"
              disabled={loading}
            >
              Reset
            </button>
          </div>
        </div>
      </div>

      {/* Chart */}
      {error ? (
        <div 
          className="rounded-lg border p-3 text-xs"
          style={{
            borderColor: errorBorder,
            backgroundColor: errorBg,
            color: errorText,
          }}
        >
          Error loading yield data: {error}
        </div>
      ) : (
        <MonthlyChart
          key={updateKey}
          data={filteredData}
          chartType={chartType}
          parameters={selectedParameters}
          loading={loading}
          hasFilters={hasFilters}
          selectedCountries={selectedCountries}
          selectedPortfolios={selectedPortfolios}
          darkMode={darkMode}
          displayMonthRange={displayMonthRange}
        />
      )}
    </div>
  );
};
