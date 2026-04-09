import { useEffect, useRef, useCallback } from 'react';
import type { EChartsInstance } from '../../../echarts';
import type { YieldDataEntry } from '../api';

type ChartType = 'bar' | 'stacked';

type MonthlyChartProps = {
  data: YieldDataEntry[];
  chartType: ChartType;
  parameters: string[];
  loading: boolean;
  hasFilters: boolean;
  selectedCountries: string[];
  selectedPortfolios: string[];
  darkMode?: boolean;
  onThemeChange?: (dark: boolean) => void;
  /** When set, the chart x-axis shows all months in this range (YYYY-MM), filling missing data with 0 */
  displayMonthRange?: { start: string; end: string } | null;
};

// Component-specific ECharts instance extensions
interface ExtendedEChartsInstance extends EChartsInstance {
  getWidth: () => number;
  __retryCount?: number;
}

// Type for echarts series item
interface EChartsSeriesItem {
  name: string;
  type: string;
  stack?: string | null;
  yAxisIndex: number;
  data: number[];
  barWidth?: string;
  barGap?: string;
  barCategoryGap?: string;
  itemStyle?: {
    color?: string;
    borderRadius?: number[];
    shadowBlur?: number;
    shadowColor?: string;
    shadowOffsetY?: number;
  };
  emphasis?: {
    itemStyle?: {
      shadowBlur?: number;
      shadowColor?: string;
      shadowOffsetY?: number;
    };
  };
  label?: {
    show: boolean;
    position?: string;
    align?: string;
    verticalAlign?: string;
    offset?: number[];
    formatter?: (params: EChartsFormatterParams) => string;
    fontSize?: number | (() => number);
    fontWeight?: number;
    fontFamily?: string;
    color?: string;
    backgroundColor?: string;
    borderColor?: string;
    borderWidth?: number;
    borderRadius?: number;
    padding?: number[];
    shadowBlur?: number;
    shadowColor?: string;
  };
  tooltip?: {
    show: boolean;
  };
}

interface EChartsFormatterParams {
  value: number;
  dataIndex: number;
  seriesName: string;
  color: string;
  axisValue: string;
}

interface EChartsTooltipParams {
  axisValue: string;
  seriesName: string;
  value: number;
  color: string;
}

const PARAMETER_LABELS: Record<string, string> = {
  ic_approved_budget: 'IC Approved Budget',
  expected_budget: 'Expected Budget',
  actual_generation: 'Actual Generation',
  weather_loss_or_gain: 'Weather Loss/Gain',
  grid_curtailment: 'Grid Curtailment',
  grid_outage: 'Grid Outage',
  operation_budget: 'Operation Budget',
  breakdown_loss: 'Breakdown Loss',
  unclassified_loss: 'Unclassified Loss',
  expected_pr: 'Expected PR',
  actual_pr: 'Actual PR',
};

const PARAMETER_UNITS: Record<string, string> = {
  ic_approved_budget: 'MWh',
  expected_budget: 'MWh',
  actual_generation: 'MWh',
  weather_loss_or_gain: 'MWh',
  grid_curtailment: 'MWh',
  grid_outage: 'MWh',
  operation_budget: 'MWh',
  breakdown_loss: 'MWh',
  unclassified_loss: 'MWh',
  expected_pr: '%',
  actual_pr: '%',
};

// Known percentage parameters
const PERCENTAGE_PARAMS = ['expected_pr', 'actual_pr'];

// Known MWh parameters
const MWH_PARAMS = [
  'ic_approved_budget',
  'expected_budget',
  'actual_generation',
  'weather_loss_or_gain',
  'grid_curtailment',
  'grid_outage',
  'operation_budget',
  'breakdown_loss',
  'unclassified_loss',
];

// Enhanced color palette - modern, vibrant colors with better contrast
const STACK_COLORS = [
  '#3b82f6', // Blue - IC Approved Budget
  '#10b981', // Emerald - Expected Budget
  '#ef4444', // Red - Actual Generation (or losses)
  '#f59e0b', // Amber - Weather Loss/Gain
  '#8b5cf6', // Violet - Grid Curtailment
  '#06b6d4', // Cyan - Grid Outage
  '#14b8a6', // Teal - Operation Budget
  '#f97316', // Orange - Breakdown Loss
  '#ec4899', // Pink - Unclassified Loss
  '#6366f1', // Indigo - Additional parameters
];

// Normalize country names
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

// Normalize portfolio names
const normalizePortfolio = (val: string | null | undefined): string => {
  return (val || '').toString().trim();
};

/** Generate ordered list of month keys (YYYY-MM) from start to end inclusive */
function getMonthsInRange(start: string, end: string): string[] {
  const [startY, startM] = start.split('-').map(Number);
  const [endY, endM] = end.split('-').map(Number);
  const months: string[] = [];
  let y = startY;
  let m = startM;
  while (y < endY || (y === endY && m <= endM)) {
    months.push(`${y}-${String(m).padStart(2, '0')}`);
    if (m === 12) {
      m = 1;
      y += 1;
    } else {
      m += 1;
    }
  }
  return months;
}

export const MonthlyChart = ({
  data,
  chartType,
  parameters,
  loading,
  hasFilters,
  selectedCountries: _selectedCountries, // eslint-disable-line @typescript-eslint/no-unused-vars
  selectedPortfolios,
  darkMode = true,
  displayMonthRange,
}: MonthlyChartProps) => {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstanceRef = useRef<ExtendedEChartsInstance | null>(null);
  const resizeObserverRef = useRef<ResizeObserver | null>(null);

  const handleResize = useCallback(() => {
    if (chartInstanceRef.current) {
      chartInstanceRef.current.resize();
    }
  }, []);

  const initializeChartRef = useRef<(() => void) | null>(null);
  const updateChartRef = useRef<(() => void) | null>(null);

  const updateChart = useCallback(() => {
    if (!chartInstanceRef.current || !window.echarts) return;
    
    // Handle empty parameters - show empty state
    if (parameters.length === 0) {
      chartInstanceRef.current.setOption({
        title: {
          text: 'Please select at least one parameter',
          left: 'center',
          top: 'center',
          textStyle: { color: darkMode ? '#94a3b8' : '#666', fontSize: 16 },
        },
        backgroundColor: darkMode ? 'transparent' : '#ffffff',
      });
      return;
    }
    
    // Ensure chart instance is valid
    try {
      if (typeof chartInstanceRef.current.setOption !== 'function') {
        return;
      }
    } catch {
      return;
    }

    // Determine effective chart type
    // If user explicitly selects stacked chart, respect that choice
    // Only force bar chart if no filters AND user hasn't selected stacked
    let effectiveChartType = chartType;
    if (!hasFilters && chartType !== 'stacked') {
      effectiveChartType = 'bar'; // Force bar chart when no filters and user hasn't selected stacked
    }

    // Separate parameters by type
    const mwhParameters = parameters.filter((param) => {
      const paramLower = param.toLowerCase();
      const isKnownPercentage = PERCENTAGE_PARAMS.includes(param);
      const isKnownMwh = MWH_PARAMS.some((known) => paramLower.includes(known.toLowerCase()));
      
      if (isKnownPercentage) return false;
      if (isKnownMwh) return true;
      return true; // Default to MWh
    });

    const percentageParameters = parameters.filter((param) => PERCENTAGE_PARAMS.includes(param));

    // When user selected a year or range, show all months in that range on the x-axis (even if data exists only for some)
    const sortedMonths =
      displayMonthRange && displayMonthRange.start && displayMonthRange.end
        ? getMonthsInRange(displayMonthRange.start, displayMonthRange.end)
        : (() => {
            const monthsSet = new Set<string>();
            data.forEach((entry) => {
              if (entry.month) {
                monthsSet.add(String(entry.month).trim());
              }
            });
            return Array.from(monthsSet).sort();
          })();

    if (sortedMonths.length === 0) {
      chartInstanceRef.current.setOption({
        title: {
          text: 'No data available',
          left: 'center',
          top: 'center',
          textStyle: { color: darkMode ? '#94a3b8' : '#666', fontSize: 16 },
        },
        backgroundColor: darkMode ? 'transparent' : '#ffffff',
      });
      return;
    }

    // Format month labels
    const monthLabels = sortedMonths.map((month) => {
      const [year, monthNum] = month.split('-');
      const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
      const monthName = monthNames[parseInt(monthNum) - 1] || monthNum;
      return `${monthName} ${year}`;
    });

    // Determine stack items (country or portfolio)
    let stackItems: string[] = [];
    let stackItemType: 'country' | 'portfolio' = 'country';

    // If stacked chart is selected, determine stack items even if no filters are applied
    if (effectiveChartType === 'stacked') {
      if (hasFilters && selectedPortfolios.length > 0) {
        // Stack by portfolio (when portfolios are filtered)
        stackItemType = 'portfolio';
        const uniquePortfolios = new Set<string>();
        data.forEach((row) => {
          const portfolio = normalizePortfolio(row.portfolio);
          if (portfolio && portfolio !== 'Unknown') {
            uniquePortfolios.add(portfolio);
          }
        });
        stackItems = Array.from(uniquePortfolios).sort();
      } else {
        // Stack by country (default - works even when no filters are applied)
        stackItemType = 'country';
        const uniqueCountries = new Set<string>();
        data.forEach((row) => {
          const country = normalizeCountry(row.country);
          if (country && country !== 'Unknown') {
            uniqueCountries.add(country);
          }
        });
        stackItems = Array.from(uniqueCountries).sort();
      }
    }

    const series: EChartsSeriesItem[] = [];
    interface EChartsYAxis {
      type: string;
      name: string;
      nameLocation: string;
      nameGap: number;
      position: string;
      nameTextStyle: {
        color: string;
        fontSize: number;
        fontWeight: number;
        fontFamily: string;
      };
      axisLabel: {
        formatter?: (value: number) => string;
        color: string;
        fontSize: number;
        fontWeight: number;
        fontFamily: string;
      };
    }
    const yAxis: EChartsYAxis[] = [];

    // Validate that we have data to display
    if (sortedMonths.length === 0 || (mwhParameters.length === 0 && percentageParameters.length === 0)) {
      chartInstanceRef.current.setOption({
        title: {
          text: 'No data available',
          left: 'center',
          top: 'center',
          textStyle: { color: darkMode ? '#94a3b8' : '#666', fontSize: 16 },
        },
        backgroundColor: darkMode ? 'transparent' : '#ffffff',
      });
      return;
    }

    // Calculate total number of bar series for spacing
    const totalBarSeries = mwhParameters.length + percentageParameters.length;
    // Calculate bar width based on number of series to prevent overlapping
    // In ECharts: barGap is percentage of bar width, not category width
    // Formula: Total space = N * W + (N-1) * W * G where N = bars, W = bar width, G = gap ratio (30%)
    // We want: N * W + (N-1) * W * G <= 100
    // W * (N + (N-1) * G) <= 100
    // W <= 100 / (N + (N-1) * G)
    let barWidthPercent: number;
    let barCategoryGapPercent: string;
    if (totalBarSeries === 1) {
      barWidthPercent = 65; // Single bar can be wider
      barCategoryGapPercent = '20%';
    } else if (totalBarSeries === 2) {
      // For 2 bars: W <= 100 / (2 + 1 * 0.3) = 100 / 2.3 = 43.5%
      barWidthPercent = 18; // Use 18% per bar for 2 bars
      barCategoryGapPercent = '20%';
    } else if (totalBarSeries === 3) {
      // For 3 bars: W <= 100 / (3 + 2 * 0.3) = 100 / 3.6 = 27.8%
      barWidthPercent = 14; // Use 14% per bar for 3 bars
      barCategoryGapPercent = '20%';
    } else {
      // For 4 bars: W <= 100 / (4 + 3 * 0.3) = 100 / 4.9 = 20.4%
      // Use 13% per bar for 4 bars to ensure no overlap with comfortable margin
      // Calculation: 4 * 13% + 3 * (13% * 30%) = 52% + 11.7% = 63.7% (very safe)
      barWidthPercent = 13;
      barCategoryGapPercent = '25%'; // Slightly more space between months for 4 bars
    }
    // Set gap between bars in the same category (month) - as percentage of bar width
    const barGapPercent = totalBarSeries > 1 ? '30%' : '0%';

    // Process MWh parameters
    mwhParameters.forEach((param, paramIndex) => {
      if (effectiveChartType === 'bar') {
        // Simple bar chart - calculate totals
        const monthlyTotals = sortedMonths.map((month) => {
          const monthData = data.filter((row) => {
            if (!row.month) return false;
            const rowMonth = String(row.month).trim();
            return rowMonth === month;
          });

          return monthData.reduce((total, row) => {
            const value = parseFloat(String((row as Record<string, unknown>)[param])) || 0;
            return total + (isNaN(value) ? 0 : value);
          }, 0);
        });

        const paramLabel = PARAMETER_LABELS[param] || param.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase());
        const barColor = STACK_COLORS[paramIndex % STACK_COLORS.length];

        series.push({
          name: paramLabel,
          type: 'bar',
          stack: null,
          yAxisIndex: 0,
          data: monthlyTotals,
          barWidth: `${barWidthPercent}%`,
          barGap: barGapPercent,
          barCategoryGap: barCategoryGapPercent,
          itemStyle: {
            color: {
              type: 'linear',
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color: barColor },
                { offset: 1, color: barColor + 'CC' },
              ],
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
            } as any,
            borderRadius: [6, 6, 0, 0],
            shadowColor: barColor,
            shadowBlur: 8,
            shadowOffsetY: 2,
          },
          emphasis: {
            itemStyle: {
              shadowBlur: 15,
              shadowColor: barColor,
            },
          },
          label: {
            show: true,
            position: 'top',
            formatter: (params: EChartsFormatterParams) => {
              const value = params.value;
              if (value === 0) return '';
              // Format with K suffix for large numbers (integers only)
              if (Math.abs(value) >= 1000) {
                const kValue = Math.round(value / 1000);
                return kValue + 'K';
              }
              return Math.round(value).toString();
            },
            fontSize: () => {
              try {
                const chartWidth = chartInstanceRef.current && typeof chartInstanceRef.current.getWidth === 'function' 
                  ? chartInstanceRef.current.getWidth() 
                  : 800;
                const dataPoints = sortedMonths.length;
                const barWidth = chartWidth / (dataPoints * 2);
                if (barWidth < 30) return 10;
                if (barWidth < 50) return 11;
                if (barWidth < 80) return 12;
                if (barWidth < 120) return 13;
                return 14;
              } catch {
                return 12; // Default font size if error
              }
            },
            fontWeight: 600,
            fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
            color: darkMode ? '#f1f5f9' : '#0f172a',
          },
        });
      } else {
        // Stacked chart - create series for each stack item
        stackItems.forEach((stackItem, stackIndex) => {
          const monthlyData = sortedMonths.map((month) => {
            const monthData = data.filter((row) => {
              if (!row.month) return false;
              const rowMonth = String(row.month).trim();
              if (rowMonth !== month) return false;

              if (stackItemType === 'portfolio') {
                const rowPortfolio = normalizePortfolio(row.portfolio);
                return rowPortfolio === stackItem;
              } else {
                const rowCountry = normalizeCountry(row.country);
                return rowCountry === stackItem;
              }
            });

            return monthData.reduce((total, row) => {
              const value = parseFloat(String((row as Record<string, unknown>)[param])) || 0;
              return total + (isNaN(value) ? 0 : value);
            }, 0);
          });

          // Calculate monthly totals for label positioning
          const monthlyTotals = sortedMonths.map((month) => {
            const monthData = data.filter((row) => {
              if (!row.month) return false;
              const rowMonth = String(row.month).trim();
              return rowMonth === month;
            });
            return monthData.reduce((total, row) => {
              const value = parseFloat(String((row as Record<string, unknown>)[param])) || 0;
              return total + (isNaN(value) ? 0 : value);
            }, 0);
          });

          const paramLabel = PARAMETER_LABELS[param] || param.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase());
          const seriesName = `${stackItem} - ${paramLabel}`;

          const stackColor = STACK_COLORS[stackIndex % STACK_COLORS.length];
          series.push({
            name: seriesName,
            type: 'bar',
            stack: param,
            yAxisIndex: 0,
            data: monthlyData,
            barWidth: '75%',
            itemStyle: {
              color: {
                type: 'linear',
                x: 0,
                y: 0,
                x2: 0,
                y2: 1,
                colorStops: [
                  { offset: 0, color: stackColor },
                  { offset: 1, color: stackColor + 'CC' },
                ],
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
              } as any,
              borderRadius: stackIndex === stackItems.length - 1 ? [6, 6, 0, 0] : [0, 0, 0, 0],
              shadowColor: stackColor,
              shadowBlur: 8,
              shadowOffsetY: 2,
            },
            emphasis: {
              itemStyle: {
                shadowBlur: 15,
                shadowColor: stackColor,
              },
            },
            label: {
              show: true,
              position: 'inside',
              formatter: (params: EChartsFormatterParams & { dataIndex: number }) => {
                const value = params.value;
                if (value === 0) return '';

                const monthIndex = params.dataIndex;
                const totalValue = monthlyTotals[monthIndex] || 0;

                // Hide label for very small segments (< 3% of total)
                if (totalValue > 0 && value / totalValue < 0.03) {
                  return '';
                }

                // Format with K suffix for large numbers (integers only)
                if (Math.abs(value) >= 1000) {
                  const kValue = Math.round(value / 1000);
                  return kValue + 'K';
                }
                return Math.round(value).toString();
              },
              fontSize: () => {
                try {
                  const chartWidth = chartInstanceRef.current && typeof chartInstanceRef.current.getWidth === 'function' 
                    ? chartInstanceRef.current.getWidth() 
                    : 800;
                  const dataPoints = sortedMonths.length;
                  const barWidth = chartWidth / (dataPoints * 2);
                  if (barWidth < 30) return 9;
                  if (barWidth < 50) return 10;
                  if (barWidth < 80) return 11;
                  if (barWidth < 120) return 12;
                  return 13;
                } catch {
                  return 11; // Default font size if error
                }
              },
              fontWeight: 600,
              fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
              color: darkMode ? '#f1f5f9' : '#ffffff',
            },
          });
        });
      }
    });

    // Process percentage parameters
    percentageParameters.forEach((param, paramIndex) => {
      if (effectiveChartType === 'bar') {
        // Calculate weighted averages
        const monthlyAverages = sortedMonths.map((month) => {
          const monthData = data.filter((row) => {
            if (!row.month) return false;
            const rowMonth = String(row.month).trim();
            return rowMonth === month;
          });

          if (monthData.length === 0) return 0;

          // Calculate weighted average by capacity
          // PR values are stored as decimals (0.0-1.0), need to convert to percentages (0-100) for display
          let totalWeighted = 0;
          let totalWeight = 0;

          monthData.forEach((row) => {
            const rawValue = (row as Record<string, unknown>)[param];
            // Handle both direct property access and nested access
            let value: number;
            if (rawValue !== undefined && rawValue !== null) {
              value = parseFloat(String(rawValue));
            } else {
              // Try direct property access as fallback
              const directValue = (row as Record<string, unknown>)[param];
              value = parseFloat(String(directValue || 0));
            }
            
            const weight = parseFloat(String(row.dc_capacity_mw)) || 1;
            
            // Include valid numeric values (including 0, but not NaN, null, or undefined)
            // Allow 0 values as they are valid (0% PR is still a valid data point)
            if (!isNaN(value) && (rawValue !== null && rawValue !== undefined && rawValue !== '')) {
              // PR values are decimals (0.0-1.0), convert to percentage (0-100)
              // If value is > 1, assume it's already a percentage, otherwise multiply by 100
              const percentageValue = Math.abs(value) > 1 ? value : value * 100;
              totalWeighted += percentageValue * weight;
              totalWeight += weight;
            }
          });

          // Return weighted average, or 0 if no valid data
          return totalWeight > 0 ? totalWeighted / totalWeight : 0;
        });

        const paramLabel = PARAMETER_LABELS[param] || param.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase());

        const percentColor = STACK_COLORS[(mwhParameters.length + paramIndex) % STACK_COLORS.length];
        // Expected PR and Actual PR always use yAxisIndex 1 (second axis - Percentage)
        // This ensures they always appear on the percentage axis regardless of other parameter selection
        series.push({
          name: paramLabel,
          type: 'bar',
          stack: null,
          yAxisIndex: 1, // Always use second axis (index 1) for percentage parameters
          data: monthlyAverages,
          barWidth: `${barWidthPercent}%`,
          barGap: barGapPercent,
          barCategoryGap: barCategoryGapPercent,
          itemStyle: {
            color: {
              type: 'linear',
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color: percentColor },
                { offset: 1, color: percentColor + 'CC' },
              ],
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
            } as any,
            borderRadius: [6, 6, 0, 0],
            shadowColor: percentColor,
            shadowBlur: 8,
            shadowOffsetY: 2,
          },
          emphasis: {
            itemStyle: {
              shadowBlur: 15,
              shadowColor: percentColor,
            },
          },
          label: {
            show: true,
            position: 'top',
            formatter: (params: EChartsFormatterParams) => {
              const value = params.value;
              // Show label even for 0 values to indicate the parameter is selected
              if (value === 0 || isNaN(value)) return '0%';
              return Math.round(value).toString() + '%';
            },
            fontSize: () => {
              try {
                const chartWidth = chartInstanceRef.current && typeof chartInstanceRef.current.getWidth === 'function' 
                  ? chartInstanceRef.current.getWidth() 
                  : 800;
                const dataPoints = sortedMonths.length;
                const barWidth = chartWidth / (dataPoints * 2);
                if (barWidth < 30) return 10;
                if (barWidth < 50) return 11;
                if (barWidth < 80) return 12;
                if (barWidth < 120) return 13;
                return 14;
              } catch {
                return 12; // Default font size if error
              }
            },
            fontWeight: 600,
            fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
            color: darkMode ? '#f1f5f9' : '#0f172a',
          },
        });
      } else {
        // Stacked chart for percentages
        stackItems.forEach((stackItem, stackIndex) => {
          const monthlyData = sortedMonths.map((month) => {
            const monthData = data.filter((row) => {
              if (!row.month) return false;
              const rowMonth = String(row.month).trim();
              if (rowMonth !== month) return false;

              if (stackItemType === 'portfolio') {
                const rowPortfolio = normalizePortfolio(row.portfolio);
                return rowPortfolio === stackItem;
              } else {
                const rowCountry = normalizeCountry(row.country);
                return rowCountry === stackItem;
              }
            });

            if (monthData.length === 0) return 0;

            // Calculate weighted average
            // PR values are stored as decimals (0.0-1.0), need to convert to percentages (0-100) for display
            let totalWeighted = 0;
            let totalWeight = 0;

            monthData.forEach((row) => {
              const rawValue = (row as Record<string, unknown>)[param];
              // Handle both direct property access and nested access
              let value: number;
              if (rawValue !== undefined && rawValue !== null) {
                value = parseFloat(String(rawValue));
              } else {
                // Try direct property access as fallback
                const directValue = (row as Record<string, unknown>)[param];
                value = parseFloat(String(directValue || 0));
              }
              
              const weight = parseFloat(String(row.dc_capacity_mw)) || 1;
              
              // Include valid numeric values (including 0, but not NaN, null, or undefined)
              // Allow 0 values as they are valid (0% PR is still a valid data point)
              if (!isNaN(value) && (rawValue !== null && rawValue !== undefined && rawValue !== '')) {
                // PR values are decimals (0.0-1.0), convert to percentage (0-100)
                // If value is > 1, assume it's already a percentage, otherwise multiply by 100
                const percentageValue = Math.abs(value) > 1 ? value : value * 100;
                totalWeighted += percentageValue * weight;
                totalWeight += weight;
              }
            });

            return totalWeight > 0 ? totalWeighted / totalWeight : 0;
          });

          const paramLabel = PARAMETER_LABELS[param] || param.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase());
          const seriesName = `${stackItem} - ${paramLabel}`;

          const percentStackColor = STACK_COLORS[stackIndex % STACK_COLORS.length];
          // Expected PR and Actual PR always use yAxisIndex 1 (second axis - Percentage)
          series.push({
            name: seriesName,
            type: 'bar',
            stack: param,
            yAxisIndex: 1, // Always use second axis (index 1) for percentage parameters
            data: monthlyData,
            barWidth: '75%',
            itemStyle: {
              color: {
                type: 'linear',
                x: 0,
                y: 0,
                x2: 0,
                y2: 1,
                colorStops: [
                  { offset: 0, color: percentStackColor },
                  { offset: 1, color: percentStackColor + 'CC' },
                ],
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
              } as any,
              borderRadius: stackIndex === stackItems.length - 1 ? [6, 6, 0, 0] : [0, 0, 0, 0],
              shadowColor: percentStackColor,
              shadowBlur: 8,
              shadowOffsetY: 2,
            },
            emphasis: {
              itemStyle: {
                shadowBlur: 15,
                shadowColor: percentStackColor,
              },
            },
            label: {
              show: true,
              position: 'inside',
              formatter: (params: EChartsFormatterParams) => {
                const value = params.value;
                if (value === 0) return '';
                return Math.round(value).toString() + '%';
              },
              fontSize: () => {
                try {
                  const chartWidth = chartInstanceRef.current && typeof chartInstanceRef.current.getWidth === 'function' 
                    ? chartInstanceRef.current.getWidth() 
                    : 800;
                  const dataPoints = sortedMonths.length;
                  const barWidth = chartWidth / (dataPoints * 2);
                  if (barWidth < 30) return 9;
                  if (barWidth < 50) return 10;
                  if (barWidth < 80) return 11;
                  if (barWidth < 120) return 12;
                  return 13;
                } catch {
                  return 11; // Default font size if error
                }
              },
              fontWeight: 600,
              fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
              color: darkMode ? '#f1f5f9' : '#ffffff',
            },
          });
        });
      }
    });

    // Add y-axes with enhanced styling
    // IMPORTANT: yAxisIndex mapping - Always use fixed indices:
    // - yAxisIndex 0 = MWh (for all non-PR parameters)
    // - yAxisIndex 1 = Percentage (for Expected PR and Actual PR only)
    // When PR parameters are selected, always create both axes:
    //   - First axis (left) = MWh (index 0)
    //   - Second axis (right/left) = Percentage (index 1)
    
    // Create MWh axis at index 0
    // Always create it when we have MWh parameters OR when we have PR parameters (to maintain axis structure)
    if (mwhParameters.length > 0 || percentageParameters.length > 0) {
      yAxis.push({
        type: 'value',
        name: 'MWh',
        nameLocation: 'middle',
        nameGap: 50,
        position: 'left', // Always on the left (first axis)
        nameTextStyle: {
          color: darkMode ? '#cbd5e1' : '#64748b',
          fontSize: 13,
          fontWeight: 600,
          fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
        },
        axisLabel: {
          formatter: (value: number) => {
            if (Math.abs(value) >= 1000) {
              return Math.round(value / 1000) + 'K';
            }
            return value.toLocaleString();
          },
          color: darkMode ? '#94a3b8' : '#64748b',
          fontSize: 11,
          fontWeight: 500,
          fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
        },
      });
    }

    // Always create Percentage axis at index 1 when PR parameters are selected
    if (percentageParameters.length > 0) {
      yAxis.push({
        type: 'value',
        name: 'Percentage (%)',
        nameLocation: 'middle',
        nameGap: 50,
        position: mwhParameters.length > 0 ? 'right' : 'left', // Right when MWh params exist, left when only PR params
        nameTextStyle: {
          color: darkMode ? '#cbd5e1' : '#64748b',
          fontSize: 13,
          fontWeight: 600,
          fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
        },
        axisLabel: {
          formatter: (value: number) => `${Math.round(value)}%`,
          color: darkMode ? '#94a3b8' : '#64748b',
          fontSize: 11,
          fontWeight: 500,
          fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
        },
      });
    }

    // Validate that series have valid yAxisIndex references
    if (series.length > 0) {
      const maxYAxisIndex = Math.max(
        ...series.map((s) => (s.yAxisIndex !== undefined ? s.yAxisIndex : 0)),
        -1
      );
      
      // Ensure we have enough yAxis for all series
      // maxYAxisIndex is 0-indexed, so if maxYAxisIndex is 1, we need at least 2 yAxis (indices 0 and 1)
      // If maxYAxisIndex is 0, we need at least 1 yAxis (index 0)
      // Note: This validation was too strict - removed early return to allow ECharts to handle gracefully
      if (maxYAxisIndex >= 0 && maxYAxisIndex >= yAxis.length) {
        // Don't return early - let ECharts handle it, it will use the available yAxis
      }
    }

    const option = {
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'shadow',
          shadowStyle: {
            color: darkMode ? 'rgba(148, 163, 184, 0.15)' : 'rgba(0, 0, 0, 0.1)',
          },
        },
        backgroundColor: darkMode ? 'rgba(15, 23, 42, 0.95)' : 'rgba(255, 255, 255, 0.95)',
        borderColor: darkMode ? 'rgba(71, 85, 105, 0.8)' : 'rgba(226, 232, 240, 0.8)',
        borderWidth: 1,
        textStyle: {
          color: darkMode ? '#e2e8f0' : '#1e293b',
          fontSize: 12,
        },
        padding: [10, 12],
        formatter: (params: EChartsTooltipParams[]) => {
          let result = `<div style="font-weight: 600; margin-bottom: 6px; color: ${darkMode ? '#f1f5f9' : '#0f172a'}; border-bottom: 1px solid ${darkMode ? 'rgba(71, 85, 105, 0.5)' : 'rgba(226, 232, 240, 0.5)'}; padding-bottom: 4px;">${params[0]?.axisValue || ''}</div>`;
          params.forEach((param: EChartsTooltipParams) => {
            // Skip "Total Labels" series from display
            if (param.seriesName === 'Total Labels' || param.seriesName.startsWith('Total_')) {
              return;
            }
            const unit = PARAMETER_UNITS[param.seriesName.split(' - ')[1] || param.seriesName] || '';
            const value = param.value;
            const formattedValue = unit === '%' ? `${Math.round(value)}%` : Math.round(value).toLocaleString();
            result += `<div style="margin-top: 4px; display: flex; align-items: center; gap: 6px;">
              <span style="display: inline-block; width: 10px; height: 10px; border-radius: 2px; background: ${param.color};"></span>
              <span style="color: ${darkMode ? '#cbd5e1' : '#475569'}; font-weight: 500;">${param.seriesName}:</span>
              <span style="color: ${darkMode ? '#f1f5f9' : '#0f172a'}; font-weight: 600;">${formattedValue}${unit === 'MWh' ? ' ' + unit : ''}</span>
            </div>`;
          });
          return result;
        },
      },
      legend: {
        data: series.map((s) => s.name),
        top: 10,
        textStyle: {
          color: darkMode ? '#cbd5e1' : '#475569',
          fontSize: 12,
          fontWeight: 500,
        },
        type: 'scroll',
        orient: 'horizontal',
        itemGap: 20,
        itemWidth: 14,
        itemHeight: 14,
        icon: 'roundRect',
        backgroundColor: darkMode ? 'rgba(15, 23, 42, 0.8)' : 'rgba(255, 255, 255, 0.8)',
        borderColor: darkMode ? 'rgba(71, 85, 105, 0.5)' : 'rgba(226, 232, 240, 0.8)',
        borderWidth: 1,
        borderRadius: 6,
        padding: [8, 12],
      },
      grid: {
        left: '4%',
        right: '4%',
        bottom: '4%',
        top: effectiveChartType === 'stacked' ? '15%' : '8%',
        containLabel: true,
        backgroundColor: darkMode ? 'transparent' : 'transparent',
      },
      xAxis: {
        type: 'category',
        data: monthLabels,
        axisLabel: {
          color: darkMode ? '#cbd5e1' : '#64748b',
          rotate: sortedMonths.length > 6 ? 45 : 0,
          fontSize: 11,
          fontWeight: 500,
          margin: 10,
        },
        axisLine: {
          lineStyle: {
            color: darkMode ? '#475569' : '#e2e8f0',
            width: 1,
          },
        },
        axisTick: {
          lineStyle: {
            color: darkMode ? '#475569' : '#e2e8f0',
          },
        },
      },
      yAxis: yAxis.map((axis) => ({
        ...axis,
        nameTextStyle: {
          color: darkMode ? '#cbd5e1' : '#64748b',
          fontSize: 12,
          fontWeight: 600,
          padding: [0, 0, 0, 8],
        },
        axisLabel: {
          ...axis.axisLabel,
          color: darkMode ? '#94a3b8' : '#64748b',
          fontSize: 11,
          fontWeight: 500,
        },
        axisLine: {
          show: true,
          lineStyle: {
            color: darkMode ? '#475569' : '#e2e8f0',
            width: 1,
          },
        },
        axisTick: {
          lineStyle: {
            color: darkMode ? '#475569' : '#e2e8f0',
          },
        },
        splitLine: {
          show: true,
          lineStyle: {
            color: darkMode ? 'rgba(71, 85, 105, 0.3)' : 'rgba(226, 232, 240, 0.6)',
            type: 'dashed',
            width: 1,
          },
        },
      })),
      series,
      backgroundColor: darkMode ? 'transparent' : '#ffffff',
      toolbox: {
        feature: {
          saveAsImage: { 
            title: 'Save', 
            name: 'monthly_chart',
            iconStyle: { borderColor: darkMode ? '#38bdf8' : '#3b82f6' } 
          },
          dataZoom: { 
            title: { zoom: 'Zoom', back: 'Reset' }, 
            iconStyle: { borderColor: darkMode ? '#38bdf8' : '#3b82f6' } 
          },
          restore: { 
            title: 'Restore', 
            iconStyle: { borderColor: darkMode ? '#38bdf8' : '#3b82f6' } 
          },
        },
        right: 15,
        top: 10,
        itemSize: 10,
        iconStyle: { borderWidth: 1 },
        emphasis: { iconStyle: { borderColor: darkMode ? '#0ea5e9' : '#2563eb' } },
      },
    };

    // Add total labels for stacked charts (MWh parameters only)
    if (effectiveChartType === 'stacked' && mwhParameters.length > 0) {
      const totalValues: number[] = [];
      
      // Calculate totals for each month (sum across all stacked MWh series)
      sortedMonths.forEach((_month, idx) => {
        let total = 0;
        series.forEach((s) => {
          // Only sum stacked MWh series (yAxisIndex === 0 and has stack property)
          if (s.stack && s.yAxisIndex === 0 && Array.isArray(s.data) && !s.name.startsWith('Total_') && !s.name.includes('Total Labels')) {
            const val = parseFloat(String(s.data[idx])) || 0;
            total += val;
          }
        });
        totalValues.push(total);
      });

      // Add transparent overlay bar for total labels - must match stacked bar width
      option.series.push({
        name: 'Total Labels',
        type: 'bar',
        stack: null,
        yAxisIndex: 0,
        data: totalValues,
        barWidth: '75%', // Match the stacked bars width
        barGap: '-100%', // Overlay exactly on top of stacked bars
        barCategoryGap: '20%', // Match the category gap of stacked bars
        itemStyle: {
          color: 'transparent',
        },
        label: {
          show: true,
          position: 'top',
          align: 'center',
          verticalAlign: 'middle',
          offset: [0, -5], // Slight offset above the bar
          fontSize: 13,
          fontWeight: 600,
          fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
          color: darkMode ? '#f1f5f9' : '#0f172a',
          backgroundColor: darkMode ? 'rgba(15, 23, 42, 0.95)' : 'rgba(255, 255, 255, 0.95)',
          borderColor: darkMode ? 'rgba(71, 85, 105, 0.6)' : 'rgba(226, 232, 240, 0.8)',
          borderWidth: 1.5,
          borderRadius: 6,
          padding: [6, 10],
          shadowBlur: 4,
          shadowColor: darkMode ? 'rgba(0, 0, 0, 0.3)' : 'rgba(0, 0, 0, 0.1)',
          formatter: (params: EChartsFormatterParams) => {
            const total = params.value;
            if (total === 0 || total === null || total === undefined) return '';
            if (Math.abs(total) >= 1000) {
              const kValue = Math.round(total / 1000);
              return kValue + 'K';
            } else {
              return Math.round(total).toString();
            }
          },
        },
        tooltip: {
          show: false, // Hide tooltip for total labels series
        },
      });

      // Exclude total labels from legend
      option.legend.data = series.map((s) => s.name).filter((name) => !name.startsWith('Total_') && name !== 'Total Labels');
    }

    // Validate option structure before setting
    if (!option.xAxis) {
      chartInstanceRef.current.setOption({
        title: {
          text: 'No data available',
          left: 'center',
          top: 'center',
          textStyle: { color: darkMode ? '#94a3b8' : '#666', fontSize: 16 },
        },
        backgroundColor: darkMode ? 'transparent' : '#ffffff',
      });
      return;
    }
    
    // If we have parameters but no series, show message
    if (parameters.length > 0 && (!option.series || option.series.length === 0)) {
      chartInstanceRef.current.setOption({
        title: {
          text: 'No data available for selected parameters',
          left: 'center',
          top: 'center',
          textStyle: { color: darkMode ? '#94a3b8' : '#666', fontSize: 16 },
        },
        backgroundColor: darkMode ? 'transparent' : '#ffffff',
      });
      return;
    }

    // Ensure yAxis array matches series requirements
    if (option.yAxis && Array.isArray(option.yAxis) && option.yAxis.length === 0 && series.length > 0) {
      // If we have series but no yAxis, something went wrong
      return;
    }

    try {
      chartInstanceRef.current.setOption(option, true);
    } catch {
      // Silently handle errors - don't spam console with repeated errors
      // The error is likely due to chart initialization timing issues
      if (chartRef.current && window.echarts && chartInstanceRef.current) {
        // Only try to reinitialize once, avoid infinite loops
        const retryCount = chartInstanceRef.current.__retryCount || 0;
        if (retryCount < 1 && initializeChartRef.current) {
          chartInstanceRef.current.__retryCount = retryCount + 1;
          setTimeout(() => {
            if (chartInstanceRef.current && initializeChartRef.current) {
              initializeChartRef.current();
            }
          }, 100);
        }
      }
    }
  }, [data, chartType, parameters, hasFilters, selectedPortfolios, darkMode, displayMonthRange]);

  // Update refs in useEffect to avoid updating during render
  useEffect(() => {
    updateChartRef.current = updateChart;
  }, [updateChart]);

  const initializeChart = useCallback(() => {
    if (!chartRef.current || !window.echarts) return;

    if (chartInstanceRef.current) {
      chartInstanceRef.current.dispose();
    }

    chartInstanceRef.current = window.echarts.init(chartRef.current, null, {
      renderer: 'canvas',
      width: 'auto',
      height: 'auto',
    }) as unknown as ExtendedEChartsInstance;

    setTimeout(() => {
      if (chartInstanceRef.current) {
        chartInstanceRef.current.resize();
      }
      // Call updateChart after initialization
      if (updateChartRef.current) {
        updateChartRef.current();
      }
    }, 100);
  }, []);

  // Update ref in useEffect to avoid updating during render
  useEffect(() => {
    initializeChartRef.current = initializeChart;
  }, [initializeChart]);

  useEffect(() => {
    // Load ECharts if not already loaded
    if (!window.echarts) {
      const script = document.createElement('script');
      script.src = 'https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js';
      script.onload = () => {
        if (chartRef.current && window.echarts) {
          initializeChart();
          window.addEventListener('resize', handleResize);
          if (chartRef.current && window.ResizeObserver) {
            resizeObserverRef.current = new ResizeObserver(() => {
              handleResize();
            });
            resizeObserverRef.current.observe(chartRef.current);
          }
        }
      };
      document.head.appendChild(script);
      return () => {
        window.removeEventListener('resize', handleResize);
        if (resizeObserverRef.current) {
          resizeObserverRef.current.disconnect();
        }
      };
    }

    if (chartRef.current) {
      initializeChart();
      window.addEventListener('resize', handleResize);
      if (window.ResizeObserver) {
        resizeObserverRef.current = new ResizeObserver(() => {
          handleResize();
        });
        resizeObserverRef.current.observe(chartRef.current);
      }
    }

    return () => {
      window.removeEventListener('resize', handleResize);
      if (resizeObserverRef.current) {
        resizeObserverRef.current.disconnect();
      }
      if (chartInstanceRef.current) {
        chartInstanceRef.current.dispose();
        chartInstanceRef.current = null;
      }
    };
  }, [initializeChart, handleResize]);

  useEffect(() => {
    if (chartInstanceRef.current && !loading) {
      // Small delay to ensure chart instance is ready and all state is updated
      const timeoutId = setTimeout(() => {
        updateChart();
      }, 50);
      return () => clearTimeout(timeoutId);
    }
  }, [updateChart, loading, data, parameters, chartType, hasFilters]);

  return (
    <div
      className={`group relative w-full overflow-hidden rounded-xl transition-all duration-300 ${
        darkMode
          ? 'border border-slate-800/70 bg-gradient-to-br from-slate-900/90 via-slate-900/50 to-slate-950 shadow-2xl shadow-slate-950/50'
          : 'border border-gray-200 bg-gradient-to-br from-white via-gray-50/50 to-white shadow-lg'
      }`}
      style={{ height: '500px', padding: 0 }}
    >
      {/* Decorative gradient overlay */}
      <div className={`pointer-events-none absolute inset-0 ${
        darkMode 
          ? 'bg-[radial-gradient(circle_at_top_right,_rgba(59,130,246,0.08),_transparent_60%),radial-gradient(circle_at_bottom_left,_rgba(139,92,246,0.06),_transparent_60%)]'
          : 'bg-[radial-gradient(circle_at_top_right,_rgba(59,130,246,0.04),_transparent_60%),radial-gradient(circle_at_bottom_left,_rgba(16,185,129,0.03),_transparent_60%)]'
      }`} />

      <div
        ref={chartRef}
        className="size-full"
        style={{ width: '100%', height: '100%', minHeight: '500px' }}
      />
      {loading && (
        <div
          className={`absolute inset-0 z-10 flex items-center justify-center rounded-lg ${
            darkMode ? 'bg-slate-900/90 text-slate-400' : 'bg-white/90 text-gray-600'
          }`}
        >
          <div>Loading chart data...</div>
        </div>
      )}
    </div>
  );
};
