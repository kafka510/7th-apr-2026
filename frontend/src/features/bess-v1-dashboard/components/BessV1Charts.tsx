import { useEffect, useRef } from 'react';
import type { BessV1Aggregates } from '../types';
import { useTheme } from '../../../contexts/ThemeContext';
import { getEChartsThemeOptions } from '../../../utils/chartExport';

interface BessV1ChartsProps {
  aggregates: BessV1Aggregates | null;
  loading: boolean;
}

// ECharts type definitions - using existing types from MonthlyChart
// Note: Window.echarts is already declared globally in MonthlyChart.tsx
interface EChartsInstance {
  setOption: (option: unknown, notMerge?: boolean, lazyUpdate?: boolean) => void;
  resize: () => void;
  dispose: () => void;
  on: (eventName: string, handler: () => void) => void;
}

let echartsLoader: Promise<void> | null = null;
function loadECharts(): Promise<void> {
  if (window.echarts) {
    return Promise.resolve();
  }
  if (!echartsLoader) {
    echartsLoader = new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = 'https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js';
      script.async = true;
      script.onload = () => resolve();
      script.onerror = () => reject(new Error('Failed to load ECharts'));
      document.head.appendChild(script);
    });
  }
  return echartsLoader;
}

// Type guard to ensure echarts is available
function initChart(dom: HTMLElement | null): EChartsInstance | undefined {
  if (!window.echarts || !dom) return undefined;
  return window.echarts.init(dom) as unknown as EChartsInstance;
}

function useChart(
  ref: React.RefObject<HTMLDivElement | null>,
  instanceRef: React.MutableRefObject<EChartsInstance | undefined>,
  optionBuilder: () => unknown,
  deps: unknown[],
  recalculateOnResize = false,
) {
  useEffect(() => {
    let disposed = false;
    let resizeHandler: (() => void) | null = null;
    let resizeObserver: ResizeObserver | null = null;

    // Helper function to check if container has valid dimensions
    const waitForContainerDimensions = (container: HTMLElement, maxAttempts = 20): Promise<boolean> => {
      return new Promise((resolve) => {
        let attempts = 0;
        const checkDimensions = () => {
          if (disposed) {
            resolve(false);
            return;
          }
          const rect = container.getBoundingClientRect();
          if (rect.width > 0 && rect.height > 0) {
            resolve(true);
          } else if (attempts < maxAttempts) {
            attempts++;
            setTimeout(checkDimensions, 50);
          } else {
            resolve(false);
          }
        };
        checkDimensions();
      });
    };

    loadECharts()
      .then(async () => {
        if (disposed || !ref.current || !window.echarts) return;

        // Wait for container to have valid dimensions
        const hasDimensions = await waitForContainerDimensions(ref.current);
        if (disposed || !hasDimensions || !ref.current) return;

        if (instanceRef.current) {
          instanceRef.current.dispose();
        }

        const chart = initChart(ref.current);
        if (!chart) return;
        instanceRef.current = chart;
        chart.setOption(optionBuilder());

        // Resize after a short delay to ensure container has final dimensions
        setTimeout(() => {
          if (!disposed && instanceRef.current) {
            instanceRef.current.resize();
          }
        }, 100);

        // Notify parent iframe to recalc height after chart renders
        window.setTimeout(() => {
          if (window.parent) {
            window.parent.postMessage({ type: "iframe-resize-request" }, "*");
          }
        }, 50);

        // ALSO notify on ECharts "finished" event (when chart completes rendering)
        chart.on("finished", () => {
          if (window.parent) {
            window.parent.postMessage({ type: "iframe-resize-request" }, "*");
          }
        });

        resizeHandler = () => {
          if (recalculateOnResize) {
            // Recalculate options with new dimensions (important for dynamic bar widths)
            chart.setOption(optionBuilder(), true);
          }
          chart.resize();
        };
        window.addEventListener('resize', resizeHandler);

        // Use ResizeObserver for better responsiveness
        if (window.ResizeObserver && ref.current) {
          resizeObserver = new ResizeObserver(() => {
            if (recalculateOnResize) {
              chart.setOption(optionBuilder(), true);
            }
            chart.resize();
          });
          resizeObserver.observe(ref.current);
        }
      })
      .catch((error) => {
        console.error('Failed to load ECharts:', error);
      });

    return () => {
      disposed = true;
      if (resizeHandler) {
        window.removeEventListener('resize', resizeHandler);
      }
      if (resizeObserver) {
        resizeObserver.disconnect();
      }
      if (instanceRef.current) {
        instanceRef.current.dispose();
        instanceRef.current = undefined;
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
}

function formatMonthLabel(month: string): string {
  const [year, monthStr] = month.split('-');
  const date = new Date(Number(year), Number(monthStr) - 1, 1);
  const monthName = date.toLocaleDateString('en-US', { month: 'short' });
  const yearShort = year.slice(2); // Get last 2 digits of year
  return `${monthName}-${yearShort}`; // Format: Jan-25
}

function formatDateLabel(dateStr: string): string {
  // Format: YYYY-MM-DD to DD-MMM
  try {
    const [year, month, day] = dateStr.split('-');
    const date = new Date(Number(year), Number(month) - 1, Number(day));
    const dayNum = date.getDate();
    const monthName = date.toLocaleDateString('en-US', { month: 'short' });
    return `${dayNum}-${monthName}`; // Format: 15-Jan
  } catch {
    return dateStr;
  }
}

export function BessV1Charts({ aggregates, loading }: BessV1ChartsProps) {
  const { theme } = useTheme();
  const energyRef = useRef<HTMLDivElement | null>(null);
  const energyInstance = useRef<EChartsInstance | undefined>(undefined);

  const cufRef = useRef<HTMLDivElement | null>(null);
  const cufInstance = useRef<EChartsInstance | undefined>(undefined);

  const cyclesRef = useRef<HTMLDivElement | null>(null);
  const cyclesInstance = useRef<EChartsInstance | undefined>(undefined);

  const waterfallRef = useRef<HTMLDivElement | null>(null);
  const waterfallInstance = useRef<EChartsInstance | undefined>(undefined);

  // Theme-aware text colors
  const isDark = theme === 'dark';
  const textColor = isDark ? '#e2e8f0' : '#1a1a1a';
  const secondaryTextColor = isDark ? '#cbd5e1' : '#4a5568';
  const axisLineColor = isDark ? '#475569' : '#cbd5e0';
  const splitLineColor = isDark ? '#334155' : '#e2e8f0';
  const tooltipBg = isDark ? 'rgba(15, 23, 42, 0.95)' : 'rgba(255, 255, 255, 0.98)';
  const tooltipBorder = isDark ? '#38bdf8' : '#0072ce';
  
  // Get theme-aware base options
  const themeOptions = getEChartsThemeOptions(isDark);
  
  useChart(
    energyRef,
    energyInstance,
    () => {
      if (!aggregates) return {};
      
      // Color scheme matching HTML template - light and dark pairs per category
      const colors = [
        { budget: '#FFD966', actual: '#E6B800' }, // PV Generation - yellow
        { budget: '#A7E3E3', actual: '#00A6A6' }, // PV to BESS - cyan
        { budget: '#A7C7FF', actual: '#1F77B4' }, // PV to Grid - blue
        { budget: '#F4CCCC', actual: '#CC0000' }, // System Losses - red
        { budget: '#F9CB9C', actual: '#E69138' }, // BESS to Grid - orange
        { budget: '#B6D7A8', actual: '#38761D' }, // Total Export - green
      ];
      
      // Calculate percentages relative to PV Generation
      const pvGenBudget = aggregates.energyFlow.budget[0];
      const pvGenActual = aggregates.energyFlow.actual[0];
      
      return {
        ...themeOptions,
        backgroundColor: themeOptions.backgroundColor, // Explicitly set based on theme
        tooltip: { 
          trigger: 'axis', 
          axisPointer: { type: 'shadow' },
          backgroundColor: tooltipBg,
          borderColor: tooltipBorder,
          textStyle: { color: textColor },
          formatter: (params: { seriesName: string; value: number; dataIndex: number; marker: string }[]) => {
            const idx = params[0]?.dataIndex;
            if (idx === undefined) return '';
            
            let result = `<strong>${aggregates.energyFlow.labels[idx]}</strong><br/>`;
            params.forEach((param) => {
              const value = param.value;
              const formattedValue = value.toLocaleString('en-US', { maximumFractionDigits: 0 });
              let pctText = '';
              if (idx >= 1 && idx <= 5) {
                const pvGen = param.seriesName === 'Budget' ? pvGenBudget : pvGenActual;
                const pct = pvGen > 0 ? Math.round((Math.abs(value) / pvGen) * 100) : 0;
                pctText = ` (${pct}%)`;
              }
              result += `${param.marker} ${param.seriesName}: ${formattedValue} MWh${pctText}<br/>`;
            });
            return result;
          },
        },
        legend: {
          data: ['Budget', 'Actual'],
          bottom: 5,
          left: 'center',
          textStyle: { color: textColor, fontSize: 11 },
          itemWidth: 20,
          itemHeight: 12,
        },
        grid: { left: 60, right: 30, bottom: 60, top: 65 },
        xAxis: {
          type: 'category',
          data: aggregates.energyFlow.labels,
          axisLabel: { 
            color: secondaryTextColor, 
            fontSize: 9,
            interval: 0,
            rotate: 0,
            lineHeight: 14,
          },
          axisLine: { lineStyle: { color: axisLineColor } },
        },
        yAxis: {
          type: 'value',
          name: 'Energy (MWh)',
          nameTextStyle: { color: textColor, fontSize: 11 },
          axisLabel: { color: secondaryTextColor, fontSize: 10 },
          splitLine: { lineStyle: { color: splitLineColor, type: 'dashed' } },
          axisLine: { lineStyle: { color: axisLineColor } },
        },
        series: [
          {
            name: 'Budget',
            type: 'bar',
            color: '#FFD966', // Light yellow (PV Generation budget color) for legend
            data: aggregates.energyFlow.budget.map((value, idx) => {
              const barColor = colors[idx]?.budget || '#fbbf24';
              return {
                value: Math.abs(value),
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
                  },
                  borderRadius: [6, 6, 0, 0],
                  shadowColor: barColor,
                  shadowBlur: 8,
                  shadowOffsetY: 2,
                },
              };
            }),
            barWidth: 22,
            barGap: '40%',
            emphasis: {
              itemStyle: {
                shadowBlur: 15,
                shadowOffsetX: 0,
              },
            },
            label: { 
              show: true,
              position: 'top',
              distance: 10,
              offset: [0, -12], // Offset upward to position above Actual labels
              color: textColor,
              fontSize: 12,
              fontWeight: 600,
              rich: {
                value: {
                  fontSize: 12,
                  fontWeight: 600,
                  color: textColor,
                },
                percent: {
                  fontSize: 11,
                  fontWeight: 500,
                  color: textColor,
                  padding: [6, 0, 0, 0], // Add spacing between value and percentage
                },
              },
              formatter: (params: { value: number; dataIndex: number }) => {
                const value = params.value;
                const idx = params.dataIndex;
                const formattedValue = value.toLocaleString('en-US', { maximumFractionDigits: 0 });
                if (idx >= 1 && idx <= 5) {
                  const pct = pvGenBudget > 0 ? Math.round((Math.abs(value) / pvGenBudget) * 100) : 0;
                  return `{value|${formattedValue}}\n{percent|(${pct}%)}`;
                }
                return `{value|${formattedValue}}`;
              },
            },
          },
          {
            name: 'Actual',
            type: 'bar',
            color: '#E6B800', // Dark yellow (PV Generation actual color) for legend
            data: aggregates.energyFlow.actual.map((value, idx) => {
              const barColor = colors[idx]?.actual || '#38bdf8';
              return {
                value: Math.abs(value),
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
                  },
                  borderRadius: [6, 6, 0, 0],
                  shadowColor: barColor,
                  shadowBlur: 8,
                  shadowOffsetY: 2,
                },
              };
            }),
            barWidth: 22,
            emphasis: {
              itemStyle: {
                shadowBlur: 15,
                shadowOffsetX: 0,
              },
            },
            label: { 
              show: true,
              position: 'top',
              distance: 8,
              offset: [0, 0], // Position at top of bar, below Budget labels
              color: textColor,
              fontSize: 12,
              fontWeight: 600,
              rich: {
                value: {
                  fontSize: 12,
                  fontWeight: 600,
                  color: textColor,
                },
                percent: {
                  fontSize: 11,
                  fontWeight: 500,
                  color: textColor,
                  padding: [6, 0, 0, 0], // Add spacing between value and percentage
                },
              },
              formatter: (params: { value: number; dataIndex: number }) => {
                const value = params.value;
                const idx = params.dataIndex;
                const formattedValue = value.toLocaleString('en-US', { maximumFractionDigits: 0 });
                if (idx >= 1 && idx <= 5) {
                  const pct = pvGenActual > 0 ? Math.round((Math.abs(value) / pvGenActual) * 100) : 0;
                  return `{value|${formattedValue}}\n{percent|(${pct}%)}`;
                }
                return `{value|${formattedValue}}`;
              },
            },
          },
        ],
        title: {
          text: 'Energy Distribution (MWh)',
          left: 'center',
          top: 8,
          textStyle: { fontSize: 13, color: theme === 'dark' ? '#38bdf8' : '#0072ce', fontWeight: 600 },
        },
        toolbox: {
          feature: {
            saveAsImage: { 
              title: 'Save', 
              pixelRatio: 2,
              backgroundColor: themeOptions.backgroundColor, // Critical: set backgroundColor for export
              iconStyle: { borderColor: '#38bdf8' } 
            },
            dataZoom: { title: { zoom: 'Zoom', back: 'Reset' }, iconStyle: { borderColor: '#38bdf8' } },
            restore: { title: 'Restore', iconStyle: { borderColor: '#38bdf8' } },
          },
          right: 10,
          top: 8,
          itemSize: 10,
          iconStyle: { borderWidth: 1 },
          emphasis: { iconStyle: { borderColor: '#0ea5e9' } },
        },
      };
    },
    [aggregates, theme, textColor, secondaryTextColor, axisLineColor, splitLineColor, tooltipBg, tooltipBorder, themeOptions],
  );

  useChart(
    cufRef,
    cufInstance,
    () => {
      if (!aggregates) return {};
      
      // Use daily data if available (single month selected), otherwise use monthly data
      const isDailyView = aggregates.dailyCUFData && aggregates.dailyCUFData.length > 0;
      
      // Responsive font sizes based on screen width
      const screenWidth = typeof window !== 'undefined' ? window.innerWidth : 1920;
      const isMobile = screenWidth < 768;
      const isLaptop = screenWidth >= 768 && screenWidth < 1440;
      
      // Title font sizes: mobile (10), laptop (11), large (13)
      const titleFontSize = isMobile ? 10 : isLaptop ? 11 : 13;
      
      // Label font sizes: mobile (9), laptop (10), large (12)
      const labelFontSize = isMobile ? 9 : isLaptop ? 10 : 12;
      
      // Axis label font sizes: mobile (7), laptop (8), large (9-10)
      const xAxisFontSize = isMobile ? 7 : isLaptop ? 8 : (isDailyView ? 8 : 9);
      const yAxisFontSize = isMobile ? 8 : isLaptop ? 9 : 10;
      
      // Legend font sizes: mobile (9), laptop (10), large (11)
      const legendFontSize = isMobile ? 9 : isLaptop ? 10 : 11;
      
      // Y-axis name font sizes: mobile (9), laptop (10), large (11)
      const yAxisNameFontSize = isMobile ? 9 : isLaptop ? 10 : 11;
      const labels = isDailyView && aggregates.dailyCUFData
        ? aggregates.dailyCUFData.map((item) => formatDateLabel(item.date))
        : aggregates.monthCUFData.map((item) => formatMonthLabel(item.month));
      const actualData = isDailyView && aggregates.dailyCUFData
        ? aggregates.dailyCUFData.map((item) => item.cufActual ?? null)
        : aggregates.monthCUFData.map((item) => item.cufActual ?? null);
      const budgetData = isDailyView && aggregates.dailyCUFData
        ? aggregates.dailyCUFData.map((item) => item.cufBudget ?? null)
        : aggregates.monthCUFData.map((item) => item.cufBudget ?? null);
      
      return {
        ...themeOptions,
        backgroundColor: themeOptions.backgroundColor, // Explicitly set based on theme
        tooltip: { 
          trigger: 'axis',
          backgroundColor: tooltipBg,
          borderColor: tooltipBorder,
          textStyle: { color: textColor, fontSize: isMobile ? 11 : isLaptop ? 12 : 13 },
          formatter: (params: { seriesName: string; value: number; marker: string; axisValue: string }[]) => {
            let result = `<strong>${params[0]?.axisValue || ''}</strong><br/>`;
            params.forEach((param) => {
              const formattedValue = param.value ? param.value.toLocaleString('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 1 }) : 'N/A';
              result += `${param.marker} ${param.seriesName}: <strong>${formattedValue}%</strong><br/>`;
            });
            return result;
          },
        },
         legend: {
           data: ['Budget CUF (%)', 'Actual CUF (%)'],
           bottom: 5,
           left: 'center',
           textStyle: { color: textColor, fontSize: legendFontSize },
           itemWidth: isMobile ? 18 : isLaptop ? 19 : 20,
           itemHeight: isMobile ? 10 : isLaptop ? 11 : 12,
         },
         grid: { 
           left: isMobile ? 45 : isLaptop ? 50 : 55, 
           right: isMobile ? 20 : isLaptop ? 25 : 30, 
           bottom: isMobile ? 60 : isLaptop ? 65 : 75, 
           top: isMobile ? 65 : isLaptop ? 70 : 80 
         },
         xAxis: {
           type: 'category',
           data: labels,
           axisLabel: { 
             color: secondaryTextColor, 
             rotate: isDailyView ? 45 : 0, 
             fontSize: xAxisFontSize,
             interval: isDailyView ? 'auto' : 0,
           },
           axisLine: { lineStyle: { color: axisLineColor } },
         },
         yAxis: {
           type: 'value',
           name: 'CUF (%)',
           nameTextStyle: { color: textColor, fontSize: yAxisNameFontSize },
           axisLabel: { 
             color: secondaryTextColor,
             fontSize: yAxisFontSize,
             formatter: '{value}%',
           },
           splitLine: { lineStyle: { color: splitLineColor, type: 'dashed' } },
           axisLine: { lineStyle: { color: axisLineColor } },
         },
         series: [
           ...(budgetData ? [{
             name: 'Budget CUF (%)',
             type: 'line',
             data: budgetData,
             smooth: true,
             lineStyle: { width: 2.5, type: 'dashed', color: '#FF9800' },
             itemStyle: { color: '#FF9800' },
             symbol: 'circle',
             symbolSize: isMobile ? 7 : isLaptop ? 8 : 9,
             label: {
               show: true,
               position: 'top',
               distance: isMobile ? 5 : isLaptop ? 6 : 7,
               offset: [0, -2],
               color: textColor,
               fontSize: labelFontSize,
               fontWeight: 600,
               formatter: (params: { value: number }) => params.value ? Math.round(params.value).toString() : '',
             },
           }] : []),
           {
             name: 'Actual CUF (%)',
             type: 'line',
             data: actualData,
             smooth: true,
             lineStyle: { width: 3.5, color: '#00B050' },
             itemStyle: { color: '#00B050' },
             symbol: 'square',
             symbolSize: isMobile ? 8 : isLaptop ? 9 : 10,
             label: {
               show: true,
               position: (params: { value: number; dataIndex: number }) => {
                 // Get corresponding budget value for comparison
                 const budgetValue = budgetData && budgetData[params.dataIndex] ? budgetData[params.dataIndex] : null;
                 const actualValue = params.value;
                 
                 if (!actualValue) return 'bottom';
                 
                 // If actual is higher than budget, position above to avoid overlap
                 // If actual is lower than budget, position below
                 if (budgetValue !== null && actualValue !== null) {
                   return actualValue > budgetValue ? 'top' : 'bottom';
                 }
                 // Default: position below for low values, above for high values
                 return actualValue > 50 ? 'top' : 'bottom';
               },
               // Distance: when 'top' (actual > budget), need larger distance to be above budget label
               // Budget uses distance 5-7px, so actual needs more (12-16px) to avoid overlap
               // When 'bottom', this distance is from below the point, so it's fine
               distance: isMobile ? 12 : isLaptop ? 14 : 16,
               // Offset: when 'top', negative offset pushes label further up to ensure it's above budget
               // When 'bottom', negative offset pulls label slightly up (closer to line, which is desired)
               offset: [0, -(isMobile ? 4 : isLaptop ? 5 : 6)],
               color: textColor,
               fontSize: labelFontSize,
               fontWeight: 600,
               formatter: (params: { value: number }) => params.value ? Math.round(params.value).toString() : '',
             },
           },
         ],
        title: {
          text: 'Capacity Utilization Factor (%)',
          left: 'center',
          top: 8,
          textStyle: { fontSize: titleFontSize, color: theme === 'dark' ? '#38bdf8' : '#0072ce', fontWeight: 600 },
        },
        toolbox: {
          feature: {
            saveAsImage: { 
              title: 'Save', 
              pixelRatio: 2,
              backgroundColor: themeOptions.backgroundColor, // Critical: set backgroundColor for export
              iconStyle: { borderColor: '#38bdf8' } 
            },
            dataZoom: { title: { zoom: 'Zoom', back: 'Reset' }, iconStyle: { borderColor: '#38bdf8' } },
            restore: { title: 'Restore', iconStyle: { borderColor: '#38bdf8' } },
          },
          right: 10,
          top: 8,
          itemSize: isMobile ? 8 : isLaptop ? 9 : 10,
          iconStyle: { borderWidth: 1 },
          emphasis: { iconStyle: { borderColor: '#0ea5e9' } },
        },
      };
    },
    [aggregates, theme, textColor, secondaryTextColor, axisLineColor, splitLineColor, tooltipBg, tooltipBorder, themeOptions],
    true, // Enable recalculate on resize for responsive fonts
  );

  useChart(
    cyclesRef,
    cyclesInstance,
    () => {
      if (!aggregates) return {};
      
      // Use daily data if available (single month selected), otherwise use monthly data
      const isDailyView = aggregates.dailyCycleData && aggregates.dailyCycleData.length > 0;
      const labels = isDailyView && aggregates.dailyCycleData
        ? aggregates.dailyCycleData.map((item) => formatDateLabel(item.date))
        : aggregates.monthCycleData.map((item) => formatMonthLabel(item.month));
      const actualData = isDailyView && aggregates.dailyCycleData
        ? aggregates.dailyCycleData.map((item) => item.cyclesActual ?? null)
        : aggregates.monthCycleData.map((item) => item.cyclesActual ?? null);
      const budgetData = isDailyView && aggregates.dailyCycleData
        ? aggregates.dailyCycleData.map((item) => item.cyclesBudget ?? null)
        : aggregates.monthCycleData.map((item) => item.cyclesBudget ?? null);
      
      return {
        ...themeOptions,
        backgroundColor: themeOptions.backgroundColor, // Explicitly set based on theme
        tooltip: { 
          trigger: 'axis',
          backgroundColor: tooltipBg,
          borderColor: tooltipBorder,
          textStyle: { color: textColor },
          formatter: (params: { seriesName: string; value: number; marker: string; axisValue: string }[]) => {
            let result = `<strong>${params[0]?.axisValue || ''}</strong><br/>`;
            params.forEach((param) => {
              const formattedValue = param.value ? param.value.toLocaleString('en-US', { maximumFractionDigits: 0 }) : 'N/A';
              result += `${param.marker} ${param.seriesName}: <strong>${formattedValue}</strong><br/>`;
            });
            return result;
          },
        },
         legend: {
           data: ['Budget Cycles', 'Actual Cycles'],
           bottom: 5,
           left: 'center',
           textStyle: { color: textColor, fontSize: 11 },
           itemWidth: 20,
           itemHeight: 12,
         },
         grid: { left: 55, right: 30, bottom: 60, top: 65 },
         xAxis: {
           type: 'category',
           data: labels,
           axisLabel: { 
             color: secondaryTextColor, 
             rotate: isDailyView ? 45 : 0, 
             fontSize: isDailyView ? 8 : 9,
             interval: isDailyView ? 'auto' : 0,
           },
           axisLine: { lineStyle: { color: axisLineColor } },
         },
         yAxis: {
           type: 'value',
           name: 'Cycles',
           nameTextStyle: { color: textColor, fontSize: 11 },
           axisLabel: { color: secondaryTextColor, fontSize: 10 },
           splitLine: { lineStyle: { color: splitLineColor, type: 'dashed' } },
           axisLine: { lineStyle: { color: axisLineColor } },
         },
         series: [
           ...(budgetData ? [{
             name: 'Budget Cycles',
             type: 'line',
             data: budgetData,
             smooth: true,
             lineStyle: { width: 2.5, type: 'dashed', color: '#FF9800' },
             itemStyle: { color: '#FF9800' },
             symbol: 'circle',
             symbolSize: 9,
             label: {
               show: true,
               position: 'top',
               color: textColor,
               fontSize: 13,
               fontWeight: 600,
               formatter: (params: { value: number }) => params.value ? Math.round(params.value).toString() : '',
             },
           }] : []),
           {
             name: 'Actual Cycles',
             type: 'line',
             data: actualData,
             smooth: true,
             lineStyle: { width: 3.5, color: '#00B050' },
             itemStyle: { color: '#00B050' },
             symbol: 'square',
             symbolSize: 10,
             label: {
               show: true,
               position: 'bottom',
               color: textColor,
               fontSize: 13,
               fontWeight: 600,
               formatter: (params: { value: number }) => params.value ? Math.round(params.value).toString() : '',
             },
           },
         ],
        title: {
          text: 'Battery Cycles',
          left: 'center',
          top: 8,
          textStyle: { fontSize: 13, color: theme === 'dark' ? '#38bdf8' : '#0072ce', fontWeight: 600 },
        },
        toolbox: {
          feature: {
            saveAsImage: { 
              title: 'Save', 
              pixelRatio: 2,
              backgroundColor: themeOptions.backgroundColor, // Critical: set backgroundColor for export
              iconStyle: { borderColor: '#38bdf8' } 
            },
            dataZoom: { title: { zoom: 'Zoom', back: 'Reset' }, iconStyle: { borderColor: '#38bdf8' } },
            restore: { title: 'Restore', iconStyle: { borderColor: '#38bdf8' } },
          },
          right: 10,
          top: 8,
          itemSize: 10,
          iconStyle: { borderWidth: 1 },
          emphasis: { iconStyle: { borderColor: '#0ea5e9' } },
        },
      };
    },
    [aggregates, theme, textColor, secondaryTextColor, axisLineColor, splitLineColor, tooltipBg, tooltipBorder, themeOptions],
  );

  useChart(
    waterfallRef,
    waterfallInstance,
    () => {
      if (!aggregates) return {};
      
      const pvGen = aggregates.waterfall.pvGeneration;
      const gridImport = aggregates.waterfall.gridImport;
      const sysLoss = -Math.abs(aggregates.waterfall.systemLosses); // negative bar
      const bessToGrid = aggregates.waterfall.bessToGrid;
      const pvToGrid = aggregates.waterfall.pvToGrid;

      const categories = [
        'PV Generation',
        'Grid Import',
        'System Losses',
        'Export to Grid',
      ];

      // Calculate waterfall cumulative positions
      // Waterfall flow: PV Gen → + Grid Import → - System Losses → = Export to Grid
      const totalExport = bessToGrid + pvToGrid;
      
      // Calculate cumulative values for display (must be calculated first)
      const afterPvGen = pvGen;
      const afterGridImport = pvGen + gridImport;
      const afterSysLoss = pvGen + gridImport + sysLoss;
      const finalExport = totalExport;
      
      // Calculate base positions for each bar (where each bar starts)
      const pvGenBase = 0;
      const gridImportBase = pvGen;
      const sysLossBase = afterSysLoss; // Start the red bar segment at the end position (after loss)
      const exportBase = 0; // Final result starts from 0
      
      // Determine dynamic bar width based on container width and number of categories
      const containerWidth = waterfallRef.current?.clientWidth ?? 600;
      const numCategories = categories.length; // 4 categories
      
      // Calculate bar width: divide container by (categories * spacing multiplier)
      // Spacing multiplier: 3.5 = bar + generous gaps for small screens, 2.5 = bar + moderate gaps for large
      const spacingMultiplier = containerWidth < 600 ? 4 : containerWidth < 900 ? 3 : 2.5;
      const calculatedBarWidth = containerWidth / (numCategories * spacingMultiplier);
      
      // Constrain between reasonable min/max values
      const dynamicBarWidth = Math.max(18, Math.min(60, calculatedBarWidth));

      return {
        ...themeOptions,
        backgroundColor: themeOptions.backgroundColor, // Explicitly set based on theme (NOT transparent)
        animation: true,
        animationDuration: 300,
        barCategoryGap: '30%', // Control spacing between category groups
        tooltip: {
          trigger: 'axis',
          axisPointer: { type: 'shadow' },
          backgroundColor: tooltipBg,
          borderColor: tooltipBorder,
          textStyle: { color: textColor },
          formatter: (params: Array<{ seriesName: string; value: string | number; dataIndex: number; marker: string }>) => {
            const idx = params[0]?.dataIndex;
            if (idx === undefined) return '';
            
            const categoryName = categories[idx];
            let result = `<strong>${categoryName}</strong><br/>`;
            
            // Show the incremental value and cumulative total
            if (idx === 0) {
              result += `Value: ${pvGen.toLocaleString('en-US', { maximumFractionDigits: 0 })} MWh<br/>`;
              result += `Total: ${afterPvGen.toLocaleString('en-US', { maximumFractionDigits: 0 })} MWh`;
            } else if (idx === 1) {
              result += `Value: +${gridImport.toLocaleString('en-US', { maximumFractionDigits: 0 })} MWh<br/>`;
              result += `Total: ${afterGridImport.toLocaleString('en-US', { maximumFractionDigits: 0 })} MWh`;
            } else if (idx === 2) {
              result += `Value: ${sysLoss.toLocaleString('en-US', { maximumFractionDigits: 0 })} MWh<br/>`;
              result += `Total: ${afterSysLoss.toLocaleString('en-US', { maximumFractionDigits: 0 })} MWh`;
            } else if (idx === 3) {
              result += `BESS to Grid: ${bessToGrid.toLocaleString('en-US', { maximumFractionDigits: 0 })} MWh<br/>`;
              result += `PV to Grid: ${pvToGrid.toLocaleString('en-US', { maximumFractionDigits: 0 })} MWh<br/>`;
              result += `<strong>Total Export: ${finalExport.toLocaleString('en-US', { maximumFractionDigits: 0 })} MWh</strong>`;
            }
            
            return result;
          },
        },
        xAxis: {
          type: 'category',
          data: categories,
          axisLabel: {
            color: secondaryTextColor,
            fontSize: containerWidth < 700 ? 9 : 10,
            rotate: 0,
            interval: 0,
            lineHeight: 14,
          },
          axisLine: { lineStyle: { color: axisLineColor } },
          boundaryGap: true, // Ensure bars are positioned within boundaries
        },
        yAxis: {
          type: 'value',
          name: 'Energy (MWh)',
          nameTextStyle: { color: textColor, fontSize: 11 },
          axisLabel: { color: secondaryTextColor, fontSize: 10 },
          splitLine: { lineStyle: { color: splitLineColor, type: 'dashed', width: 1 } },
          axisLine: { lineStyle: { color: axisLineColor } },
        },
        title: {
          text: 'Actual Energy Flow (MWh)',
          left: 'center',
          top: 8,
          textStyle: { fontSize: 13, color: theme === 'dark' ? '#38bdf8' : '#0072ce', fontWeight: 600 },
        },
         grid: { 
          left: containerWidth < 700 ? 50 : 60, 
          right: containerWidth < 700 ? 20 : 30, 
          top: 60, 
          bottom: 65, 
          containLabel: true 
        },
        legend: {
          bottom: 5,
          left: 'center',
          textStyle: { 
            color: textColor, 
            fontSize: containerWidth < 600 ? 9 : 11 
          },
          itemWidth: containerWidth < 600 ? 15 : 20,
          itemHeight: containerWidth < 600 ? 10 : 12,
          itemGap: containerWidth < 600 ? 8 : 10,
          data: [
            'PV Generation',
            'Grid Import',
            'System Losses',
            'BESS to Grid',
            'PV to Grid',
          ],
        },
        series: [
          // Invisible helper bars to position waterfall bars
          {
            name: 'helper',
            type: 'bar',
            stack: 'waterfall',
            itemStyle: {
              color: 'transparent',
              borderColor: 'transparent',
            },
            emphasis: { itemStyle: { color: 'transparent' } },
            data: [pvGenBase, gridImportBase, sysLossBase, exportBase],
            barWidth: dynamicBarWidth,
            label: { show: false },
            tooltip: { show: false },
          },
          // PV Generation (visible bar)
          {
            name: 'PV Generation',
            type: 'bar',
            stack: 'waterfall',
            data: [pvGen, '-', '-', '-'],
            barWidth: dynamicBarWidth,
            itemStyle: {
              color: {
                type: 'linear',
                x: 0,
                y: 0,
                x2: 0,
                y2: 1,
                colorStops: [
                  { offset: 0, color: '#E6B800' },
                  { offset: 1, color: '#E6B800CC' },
                ],
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              } as any,
              borderRadius: [6, 6, 0, 0],
              shadowColor: '#E6B800',
              shadowBlur: 8,
              shadowOffsetY: 2,
            },
            emphasis: {
              itemStyle: {
                shadowBlur: 15,
                shadowColor: '#E6B800',
              },
            },
            label: {
              show: true,
              position: 'top',
              color: textColor,
              fontSize: containerWidth < 600 ? 12 : 14,
              fontWeight: 'bold',
              formatter: () => `${pvGen.toLocaleString('en-US', { maximumFractionDigits: 0 })}`, // Show actual value, not cumulative
            },
          },
          // Grid Import (visible bar)
          {
            name: 'Grid Import',
            type: 'bar',
            stack: 'waterfall',
            data: ['-', gridImport, '-', '-'],
            barWidth: dynamicBarWidth,
            itemStyle: {
              color: {
                type: 'linear',
                x: 0,
                y: 0,
                x2: 0,
                y2: 1,
                colorStops: [
                  { offset: 0, color: '#9E9E9E' },
                  { offset: 1, color: '#9E9E9ECC' },
                ],
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              } as any,
              borderRadius: [6, 6, 0, 0],
              shadowColor: '#9E9E9E',
              shadowBlur: 8,
              shadowOffsetY: 2,
            },
            emphasis: {
              itemStyle: {
                shadowBlur: 15,
                shadowColor: '#9E9E9E',
              },
            },
            label: {
              show: true, // Always show label to display "0" when no import
              position: 'top',
              fontSize: containerWidth < 600 ? 12 : 14,
              color: textColor,
              fontWeight: 'bold',
              formatter: () => `${gridImport.toLocaleString('en-US', { maximumFractionDigits: 0 })}`, // Show actual import value (0)
            },
          },
          // System Losses (visible bar as positive segment at top)
          {
            name: 'System Losses',
            type: 'bar',
            stack: 'waterfall',
            data: ['-', '-', Math.abs(sysLoss), '-'], // Use absolute value to show as positive bar at top
            barWidth: dynamicBarWidth,
            itemStyle: {
              color: {
                type: 'linear',
                x: 0,
                y: 0,
                x2: 0,
                y2: 1,
                colorStops: [
                  { offset: 0, color: '#CC0000' },
                  { offset: 1, color: '#CC0000CC' },
                ],
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              } as any,
              borderRadius: [6, 6, 0, 0],
              shadowColor: '#CC0000',
              shadowBlur: 8,
              shadowOffsetY: 2,
            },
            emphasis: {
              itemStyle: {
                shadowBlur: 15,
                shadowColor: '#CC0000',
              },
            },
            label: {
              show: true,
              position: 'top',
              color: textColor,
              fontSize: containerWidth < 600 ? 12 : 13,
              fontWeight: 'bold',
              formatter: () => `${sysLoss.toLocaleString('en-US', { maximumFractionDigits: 0 })}`, // Show as negative value
            },
          },
          // Export to Grid - BESS portion (bottom of stack)
          {
            name: 'BESS to Grid',
            type: 'bar',
            stack: 'waterfall',
            data: ['-', '-', '-', bessToGrid],
            barWidth: dynamicBarWidth,
            itemStyle: {
              color: {
                type: 'linear',
                x: 0,
                y: 0,
                x2: 0,
                y2: 1,
                colorStops: [
                  { offset: 0, color: '#E69138' },
                  { offset: 1, color: '#E69138CC' },
                ],
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              } as any,
              shadowColor: '#E69138',
              shadowBlur: 8,
              shadowOffsetY: 2,
            },
            emphasis: {
              itemStyle: {
                shadowBlur: 15,
                shadowColor: '#E69138',
              },
            },
            label: {
              show: true,
              position: 'inside',
              color: theme === 'dark' ? '#fff' : '#1a1a1a',
              fontSize: containerWidth < 600 ? 12 : 13,
              fontWeight: 'bold',
              formatter: () => bessToGrid.toLocaleString('en-US', { maximumFractionDigits: 0 }),
            },
          },
          // Export to Grid - PV portion (top of stack)
          {
            name: 'PV to Grid',
            type: 'bar',
            stack: 'waterfall',
            data: ['-', '-', '-', pvToGrid],
            barWidth: dynamicBarWidth,
            itemStyle: {
              color: {
                type: 'linear',
                x: 0,
                y: 0,
                x2: 0,
                y2: 1,
                colorStops: [
                  { offset: 0, color: '#1F77B4' },
                  { offset: 1, color: '#1F77B4CC' },
                ],
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              } as any,
              borderRadius: [6, 6, 0, 0],
              shadowColor: '#1F77B4',
              shadowBlur: 8,
              shadowOffsetY: 2,
            },
            emphasis: {
              itemStyle: {
                shadowBlur: 15,
                shadowColor: '#1F77B4',
              },
            },
            label: {
              show: true,
              position: 'inside',
              color: theme === 'dark' ? '#fff' : '#1a1a1a',
              fontSize: containerWidth < 600 ? 12 : 13,
              fontWeight: 'bold',
              formatter: () => `${pvToGrid.toLocaleString('en-US', { maximumFractionDigits: 0 })}`,
            },
          },
          // Invisible series to display total export label on top of stacked bar
          {
            name: 'Total Export',
            type: 'bar',
            stack: 'waterfall',
            data: ['-', '-', '-', 0.5], // Very small fixed value to position label at top (invisible on scale)
            barWidth: dynamicBarWidth,
            itemStyle: {
              color: 'transparent',
              borderColor: 'transparent',
              borderWidth: 0,
            },
            emphasis: {
              itemStyle: {
                color: 'transparent',
              },
            },
            label: {
              show: true,
              position: 'top',
              color: textColor,
              fontSize: containerWidth < 600 ? 12 : 13,
              fontWeight: 'bold',
              formatter: () => `${finalExport.toLocaleString('en-US', { maximumFractionDigits: 0 })}`,
              offset: [0, -2],
            },
            tooltip: {
              show: false,
            },
            silent: true, // Make it non-interactive
            z: 1, // Ensure it's on top
          },
        ],
        toolbox: {
          feature: {
            saveAsImage: { 
              title: 'Save', 
              pixelRatio: 2,
              backgroundColor: themeOptions.backgroundColor, // Critical: set backgroundColor for export
              iconStyle: { borderColor: '#38bdf8' } 
            },
            dataZoom: { title: { zoom: 'Zoom', back: 'Reset' }, iconStyle: { borderColor: '#38bdf8' } },
            restore: { title: 'Restore', iconStyle: { borderColor: '#38bdf8' } },
          },
          right: 10,
          top: 8,
          itemSize: 10,
          iconStyle: { borderWidth: 1 },
          emphasis: { iconStyle: { borderColor: '#0ea5e9' } },
        },
      };
    },
    [aggregates, theme, textColor, secondaryTextColor, axisLineColor, splitLineColor, tooltipBg, tooltipBorder, themeOptions],
    true, // Enable recalculate on resize for responsive bar width
  );

  // Theme-aware colors
  const loadingColor = theme === 'dark' ? '#38bdf8' : '#0072ce';
  const noDataColor = theme === 'dark' ? '#94a3b8' : '#718096';
  const chartCardBg = theme === 'dark'
    ? 'linear-gradient(to bottom right, rgb(15 23 42 / 0.95), rgb(30 41 59 / 0.7), rgb(15 23 42 / 0.95))'
    : 'linear-gradient(to bottom right, rgba(255, 255, 255, 0.98), rgba(248, 250, 252, 0.95), rgba(255, 255, 255, 0.98))';
  const chartCardBorder = theme === 'dark' ? 'rgba(148, 163, 184, 0.25)' : 'rgba(203, 213, 225, 0.5)';
  const chartCardShadow = theme === 'dark'
    ? '0 4px 6px -1px rgba(0, 0, 0, 0.4), 0 2px 4px -1px rgba(0, 0, 0, 0.3)'
    : '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)';

  if (loading) {
    return (
      <div style={{ padding: '40px 0', textAlign: 'center', color: loadingColor }}>
        Loading charts...
      </div>
    );
  }

  if (!aggregates) {
    return (
      <div style={{ padding: '40px 0', textAlign: 'center', color: noDataColor }}>
        No chart data available for the selected filters.
      </div>
    );
  }

  const chartCardStyle: React.CSSProperties = {
    borderRadius: '10px',
    border: `1px solid ${chartCardBorder}`,
    background: chartCardBg,
    boxShadow: chartCardShadow,
    padding: '10px',
    transition: 'background 0.3s ease, border-color 0.3s ease, box-shadow 0.3s ease',
  };

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(2, 1fr)',
        gap: '10px',
        width: '100%',
        padding: '0 8px 8px 8px',
        overflow: 'visible',
        position: 'relative',
        zIndex: 1,
      }}
    >
      <div style={chartCardStyle}>
        <div ref={energyRef} style={{ width: '100%', height: '340px' }} />
      </div>
      <div style={chartCardStyle}>
        <div ref={waterfallRef} style={{ width: '100%', height: '340px' }} />
      </div>
      <div style={chartCardStyle}>
        <div ref={cyclesRef} style={{ width: '100%', height: '340px' }} />
      </div>
      <div style={chartCardStyle}>
        <div ref={cufRef} style={{ width: '100%', height: '340px' }} />
      </div>
    </div>
  );
}

