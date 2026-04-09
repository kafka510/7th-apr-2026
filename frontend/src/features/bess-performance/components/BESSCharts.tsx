import { useEffect, useRef, useState } from 'react';
import { useTheme } from '../../../contexts/ThemeContext';
import type { EChartsInstance } from '../../../echarts';
import type { BESSChartData, BESSData } from '../types';

interface BESSChartsProps {
  chartData: BESSChartData;
  filteredData: BESSData[];
  loading: boolean;
}

// Component-specific ECharts instance extensions
interface ExtendedEChartsInstance extends EChartsInstance {
  getWidth: () => number;
}

function loadECharts(): Promise<void> {
  return new Promise((resolve, reject) => {
    if (window.echarts) {
      resolve();
      return;
    }

    const script = document.createElement('script');
    script.src = 'https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js';
    script.onload = () => resolve();
    script.onerror = () => reject(new Error('Failed to load ECharts'));
    document.head.appendChild(script);
  });
}

function initChart(dom: HTMLElement | null): ExtendedEChartsInstance | undefined {
  if (!window.echarts || !dom) return undefined;
  return window.echarts.init(dom) as unknown as ExtendedEChartsInstance;
}

function getBarWidth(monthCount: number): number {
  const screenWidth = window.innerWidth;
  if (screenWidth <= 1200) {
    return Math.max(12, Math.min(18, 200 / monthCount));
  } else if (screenWidth <= 1440) {
    return Math.max(15, Math.min(22, 250 / monthCount));
  } else {
    return Math.max(20, Math.min(30, 300 / monthCount));
  }
}

function getCategoryGap(screenWidth: number): string {
  if (screenWidth <= 1200) return '15%';
  if (screenWidth <= 1440) return '12%';
  return '10%';
}

export function BESSCharts({ chartData, filteredData, loading }: BESSChartsProps) {
  const { theme } = useTheme();
  const [activeTab, setActiveTab] = useState<'all-energy' | 'charge-discharge' | 'soc-temp'>('all-energy');
  
  // Theme-aware colors
  const chartContainerBg = theme === 'dark'
    ? 'linear-gradient(to bottom right, rgba(15, 23, 42, 0.9), rgba(30, 41, 59, 0.6))'
    : 'linear-gradient(to bottom right, rgba(255, 255, 255, 0.95), rgba(248, 250, 252, 0.9))';
  const chartContainerBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(203, 213, 225, 0.8)';
  const chartContainerShadow = theme === 'dark' 
    ? '0 4px 12px rgba(0,0,0,0.3)' 
    : '0 1px 3px 0 rgba(0, 0, 0, 0.1)';
  const textColor = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';
  const secondaryTextColor = theme === 'dark' ? '#cbd5e1' : '#4a5568';
  const axisLineColor = theme === 'dark' ? '#475569' : '#cbd5e0';
  const splitLineColor = theme === 'dark' ? '#334155' : '#e2e8f0';
  const chartBg = theme === 'dark' ? '#0f172a' : '#ffffff';
  const tabActiveBg = theme === 'dark' ? '#38bdf8' : '#0072ce';
  const tabActiveText = theme === 'dark' ? '#0f172a' : '#ffffff';
  const tabInactiveText = theme === 'dark' ? '#cbd5e1' : '#4a5568';
  const tabBorder = theme === 'dark' ? '#334155' : '#cbd5e1';
  const barChartRef = useRef<HTMLDivElement>(null);
  const chargeDischargeRef = useRef<HTMLDivElement>(null);
  const socTempRef = useRef<HTMLDivElement>(null);
  const barChartInstanceRef = useRef<EChartsInstance | undefined>(undefined);
  const chargeDischargeInstanceRef = useRef<EChartsInstance | undefined>(undefined);
  const socTempInstanceRef = useRef<EChartsInstance | undefined>(undefined);

  // Bar Chart - All Energy
  useEffect(() => {
    if (loading || !barChartRef.current || activeTab !== 'all-energy') return;

    let mounted = true;
    let resizeHandler: (() => void) | null = null;
    let resizeObserver: ResizeObserver | null = null;

    // Helper function to check if container has valid dimensions
    const waitForContainerDimensions = (container: HTMLElement, maxAttempts = 20): Promise<boolean> => {
      return new Promise((resolve) => {
        let attempts = 0;
        const checkDimensions = () => {
          if (!mounted) {
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
        if (!mounted || !window.echarts || !barChartRef.current) return;

        // Wait for container to have valid dimensions
        const hasDimensions = await waitForContainerDimensions(barChartRef.current);
        if (!mounted || !hasDimensions || !barChartRef.current) return;

        if (barChartInstanceRef.current) {
          barChartInstanceRef.current.dispose();
        }

        const chartInstance = initChart(barChartRef.current);
        if (!chartInstance) return;
        barChartInstanceRef.current = chartInstance;

        if (chartData.months.length === 0) {
          chartInstance.setOption({
            backgroundColor: chartBg,
            title: { text: 'All Energy', left: 'center', textStyle: { fontSize: 16, fontWeight: 'bold', color: theme === 'dark' ? '#38bdf8' : '#0072ce' } },
            graphic: [{ type: 'text', left: 'center', top: 'middle', style: { text: 'No data available', fontSize: 16, fill: secondaryTextColor } }],
          });
        } else {
          const barWidth = getBarWidth(chartData.months.length);
          const categoryGap = getCategoryGap(window.innerWidth);

          const option = {
            backgroundColor: chartBg,
            title: { text: 'All Energy', left: 'center', textStyle: { fontSize: 16, fontWeight: 'bold', color: theme === 'dark' ? '#38bdf8' : '#0072ce' } },
            tooltip: {
              trigger: 'axis',
              backgroundColor: theme === 'dark' ? 'rgba(15, 23, 42, 0.95)' : 'rgba(255, 255, 255, 0.98)',
              borderColor: theme === 'dark' ? '#38bdf8' : '#0072ce',
              textStyle: { fontSize: 13, fontWeight: 'bold', color: textColor },
              formatter: (params: unknown) => {
                const p = params as Array<{ axisValue: string; marker: string; seriesName: string; value: number }>;
                let result = p[0].axisValue + '<br/>';
                p.forEach((item) => {
                  const formattedValue = Math.round(item.value).toLocaleString();
                  result += item.marker + ' ' + item.seriesName + ': ' + formattedValue + ' kWh<br/>';
                });
                return result;
              },
            },
            legend: {
              data: ['PV Energy', 'Export Energy', 'Charge Energy', 'Discharge Energy'],
              textStyle: { fontSize: 14, fontWeight: 'bold', color: secondaryTextColor },
              bottom: 25,
              left: 'center',
            },
            grid: { left: 100, right: 20, bottom: 80, top: 40 },
            xAxis: {
              type: 'category',
              data: chartData.months,
              axisLabel: { formatter: '{value}', fontSize: 13, fontWeight: 'bold', color: secondaryTextColor },
              axisTick: { alignWithLabel: true },
              axisLine: { lineStyle: { color: axisLineColor } },
            },
            yAxis: {
              type: 'value',
              name: 'Energy (MWh)',
              nameLocation: 'middle',
              nameGap: 80,
              nameTextStyle: { fontSize: 14, fontWeight: 'bold', color: textColor },
              axisLabel: {
                formatter: (value: number) => Math.round(value / 1000) + 'K',
                fontSize: 13,
                fontWeight: 'bold',
                color: textColor,
              },
              axisLine: { lineStyle: { color: axisLineColor } },
              splitLine: { lineStyle: { color: splitLineColor, type: 'dashed', width: 1 } },
            },
            series: [
              {
                name: 'PV Energy',
                type: 'bar',
                data: chartData.pvEnergy,
                barWidth,
                barCategoryGap: categoryGap,
                itemStyle: {
                  color: {
                    type: 'linear',
                    x: 0,
                    y: 0,
                    x2: 0,
                    y2: 1,
                    colorStops: [
                      { offset: 0, color: '#facc15' },
                      { offset: 1, color: '#facc15CC' },
                    ],
                  },
                  borderRadius: [6, 6, 0, 0],
                  shadowColor: '#facc15',
                  shadowBlur: 8,
                  shadowOffsetY: 2,
                },
                emphasis: {
                  itemStyle: {
                    shadowBlur: 15,
                    shadowOffsetX: 0,
                    shadowColor: '#facc15',
                  },
                },
                label: {
                  show: true,
                  position: 'top',
                  fontWeight: 'bold',
                  fontSize: 13,
                  color: textColor,
                  formatter: (params: { value: number | null }) => (params.value == null ? '' : Math.round(params.value / 1000)),
                },
              },
              {
                name: 'Export Energy',
                type: 'bar',
                data: chartData.exportEnergy,
                barWidth,
                barCategoryGap: categoryGap,
                itemStyle: {
                  color: {
                    type: 'linear',
                    x: 0,
                    y: 0,
                    x2: 0,
                    y2: 1,
                    colorStops: [
                      { offset: 0, color: '#3b82f6' },
                      { offset: 1, color: '#3b82f6CC' },
                    ],
                  },
                  borderRadius: [6, 6, 0, 0],
                  shadowColor: '#3b82f6',
                  shadowBlur: 8,
                  shadowOffsetY: 2,
                },
                emphasis: {
                  itemStyle: {
                    shadowBlur: 15,
                    shadowOffsetX: 0,
                    shadowColor: '#3b82f6',
                  },
                },
                label: {
                  show: true,
                  position: 'top',
                  fontWeight: 'bold',
                  fontSize: 13,
                  color: textColor,
                  formatter: (params: { value: number | null }) => (params.value == null ? '' : Math.round(params.value / 1000)),
                },
              },
              {
                name: 'Charge Energy',
                type: 'bar',
                data: chartData.chargeEnergy,
                barWidth,
                barCategoryGap: categoryGap,
                itemStyle: {
                  color: {
                    type: 'linear',
                    x: 0,
                    y: 0,
                    x2: 0,
                    y2: 1,
                    colorStops: [
                      { offset: 0, color: '#8b5cf6' },
                      { offset: 1, color: '#8b5cf6CC' },
                    ],
                  },
                  borderRadius: [6, 6, 0, 0],
                  shadowColor: '#8b5cf6',
                  shadowBlur: 8,
                  shadowOffsetY: 2,
                },
                emphasis: {
                  itemStyle: {
                    shadowBlur: 15,
                    shadowOffsetX: 0,
                    shadowColor: '#8b5cf6',
                  },
                },
                label: {
                  show: true,
                  position: 'top',
                  fontWeight: 'bold',
                  fontSize: 13,
                  color: textColor,
                  formatter: (params: { value: number | null }) => (params.value == null ? '' : Math.round(params.value / 1000)),
                },
              },
              {
                name: 'Discharge Energy',
                type: 'bar',
                data: chartData.dischargeEnergy,
                barWidth,
                barCategoryGap: categoryGap,
                itemStyle: {
                  color: {
                    type: 'linear',
                    x: 0,
                    y: 0,
                    x2: 0,
                    y2: 1,
                    colorStops: [
                      { offset: 0, color: '#14b8a6' },
                      { offset: 1, color: '#14b8a6CC' },
                    ],
                  },
                  borderRadius: [6, 6, 0, 0],
                  shadowColor: '#14b8a6',
                  shadowBlur: 8,
                  shadowOffsetY: 2,
                },
                emphasis: {
                  itemStyle: {
                    shadowBlur: 15,
                    shadowOffsetX: 0,
                    shadowColor: '#14b8a6',
                  },
                },
                label: {
                  show: true,
                  position: 'top',
                  fontWeight: 'bold',
                  fontSize: 13,
                  color: textColor,
                  formatter: (params: { value: number | null }) => (params.value == null ? '' : Math.round(params.value / 1000)),
                },
              },
            ],
            toolbox: {
              feature: {
                saveAsImage: { 
                  title: 'Save', 
                  name: 'bess_energy_chart',
                  iconStyle: { borderColor: theme === 'dark' ? '#38bdf8' : '#0072ce' } 
                },
                dataZoom: { 
                  title: { zoom: 'Zoom', back: 'Reset' }, 
                  iconStyle: { borderColor: theme === 'dark' ? '#38bdf8' : '#0072ce' } 
                },
                restore: { 
                  title: 'Restore', 
                  iconStyle: { borderColor: theme === 'dark' ? '#38bdf8' : '#0072ce' } 
                },
              },
              right: 15,
              top: 10,
              itemSize: 10,
              iconStyle: { borderWidth: 1 },
              emphasis: { iconStyle: { borderColor: theme === 'dark' ? '#0ea5e9' : '#0056a3' } },
            },
          };

          chartInstance.setOption(option);

          // Resize after a short delay to ensure container has final dimensions
          setTimeout(() => {
            if (mounted && barChartInstanceRef.current) {
              barChartInstanceRef.current.resize();
            }
          }, 100);

          resizeHandler = () => {
            if (barChartInstanceRef.current) {
              barChartInstanceRef.current.resize();
            }
          };
          window.addEventListener('resize', resizeHandler);

          // Use ResizeObserver for better responsiveness
          if (window.ResizeObserver && barChartRef.current) {
            resizeObserver = new ResizeObserver(() => {
              if (barChartInstanceRef.current) {
                barChartInstanceRef.current.resize();
              }
            });
            resizeObserver.observe(barChartRef.current);
          }
        }
      })
      .catch((error) => {
        console.error('Failed to load ECharts:', error);
      });

    return () => {
      mounted = false;
      if (resizeHandler) {
        window.removeEventListener('resize', resizeHandler);
      }
      if (resizeObserver) {
        resizeObserver.disconnect();
      }
      if (barChartInstanceRef.current) {
        barChartInstanceRef.current.dispose();
        barChartInstanceRef.current = undefined;
      }
    };
  }, [chartData, loading, activeTab, theme]);

  // Charge/Discharge Line Chart
  useEffect(() => {
    if (loading || !chargeDischargeRef.current || activeTab !== 'charge-discharge') return;

    let mounted = true;
    let resizeHandler: (() => void) | null = null;
    let resizeObserver: ResizeObserver | null = null;

    // Helper function to check if container has valid dimensions
    const waitForContainerDimensions = (container: HTMLElement, maxAttempts = 20): Promise<boolean> => {
      return new Promise((resolve) => {
        let attempts = 0;
        const checkDimensions = () => {
          if (!mounted) {
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
        if (!mounted || !window.echarts || !chargeDischargeRef.current) return;

        // Wait for container to have valid dimensions
        const hasDimensions = await waitForContainerDimensions(chargeDischargeRef.current);
        if (!mounted || !hasDimensions || !chargeDischargeRef.current) return;

        if (chargeDischargeInstanceRef.current) {
          chargeDischargeInstanceRef.current.dispose();
        }

        const chartInstance = initChart(chargeDischargeRef.current);
        if (!chartInstance) return;
        chargeDischargeInstanceRef.current = chartInstance;

        // Group data by date
        const dateGroups: Record<string, { charge: number; discharge: number }> = {};
        filteredData.forEach((row) => {
          if (!row.date) return;
          if (!dateGroups[row.date]) {
            dateGroups[row.date] = { charge: 0, discharge: 0 };
          }
          const charge = typeof row.charge_energy_kwh === 'string' ? parseFloat(row.charge_energy_kwh) : row.charge_energy_kwh;
          const discharge = typeof row.discharge_energy_kwh === 'string' ? parseFloat(row.discharge_energy_kwh) : row.discharge_energy_kwh;
          if (typeof charge === 'number' && !isNaN(charge)) dateGroups[row.date].charge += charge;
          if (typeof discharge === 'number' && !isNaN(discharge)) dateGroups[row.date].discharge += discharge;
        });

        const sortedDates = Object.keys(dateGroups).sort((a, b) => new Date(a).getTime() - new Date(b).getTime());
        const chargeData = sortedDates.map((date) => Math.round(dateGroups[date].charge));
        const dischargeData = sortedDates.map((date) => Math.round(dateGroups[date].discharge));

        if (sortedDates.length === 0) {
          chartInstance.setOption({
            backgroundColor: chartBg,
            title: { text: 'Charge Energy Vs Discharge Energy', left: 'center', textStyle: { fontSize: 18, fontWeight: 'bold', color: theme === 'dark' ? '#38bdf8' : '#0072ce' } },
            graphic: [{ type: 'text', left: 'center', top: 'middle', style: { text: 'No data available', fontSize: 16, fill: secondaryTextColor } }],
          });
        } else {
          const option = {
            backgroundColor: chartBg,
            title: { text: 'Charge Energy Vs Discharge Energy', left: 'center', textStyle: { fontSize: 18, fontWeight: 'bold', color: theme === 'dark' ? '#38bdf8' : '#0072ce' } },
            tooltip: { 
              trigger: 'axis', 
              backgroundColor: theme === 'dark' ? 'rgba(15, 23, 42, 0.95)' : 'rgba(255, 255, 255, 0.98)',
              borderColor: theme === 'dark' ? '#38bdf8' : '#0072ce',
              textStyle: { fontSize: 17, fontWeight: 'bold', color: textColor } 
            },
            legend: {
              data: ['Charge Energy', 'Discharge Energy'],
              textStyle: { fontSize: 16, fontWeight: 'bold', color: secondaryTextColor },
              bottom: 25,
              left: 'center',
            },
            grid: { left: 80, right: 30, bottom: 80, top: 60 },
            xAxis: { 
              type: 'category', 
              data: sortedDates, 
              axisLabel: { formatter: '{value}', fontSize: 13, fontWeight: 'bold', color: secondaryTextColor }, 
              axisLine: { lineStyle: { color: axisLineColor } } 
            },
            yAxis: {
              type: 'value',
              name: 'Energy (MWh)',
              nameLocation: 'middle',
              nameGap: 60,
              nameTextStyle: { fontSize: 14, fontWeight: 'bold', color: textColor },
              axisLabel: { formatter: '{value}', fontSize: 13, fontWeight: 'bold', color: textColor },
              axisLine: { lineStyle: { color: axisLineColor } },
              splitLine: { lineStyle: { color: splitLineColor, type: 'dashed', width: 1 } },
            },
            series: [
              { name: 'Charge Energy', type: 'line', data: chargeData, lineStyle: { width: 2.5 } },
              { name: 'Discharge Energy', type: 'line', data: dischargeData, lineStyle: { width: 2.5 } },
            ],
            toolbox: {
              feature: {
                saveAsImage: { 
                  title: 'Save', 
                  name: 'charge_discharge_chart',
                  iconStyle: { borderColor: theme === 'dark' ? '#38bdf8' : '#0072ce' } 
                },
                dataZoom: { 
                  title: { zoom: 'Zoom', back: 'Reset' }, 
                  iconStyle: { borderColor: theme === 'dark' ? '#38bdf8' : '#0072ce' } 
                },
                restore: { 
                  title: 'Restore', 
                  iconStyle: { borderColor: theme === 'dark' ? '#38bdf8' : '#0072ce' } 
                },
              },
              right: 15,
              top: 10,
              iconStyle: { borderWidth: 1.5 },
              emphasis: { iconStyle: { borderColor: theme === 'dark' ? '#0ea5e9' : '#0056a3' } },
            },
          };

          chartInstance.setOption(option);

          // Resize after a short delay to ensure container has final dimensions
          setTimeout(() => {
            if (mounted && chargeDischargeInstanceRef.current) {
              chargeDischargeInstanceRef.current.resize();
            }
          }, 100);

          resizeHandler = () => {
            if (chargeDischargeInstanceRef.current) {
              chargeDischargeInstanceRef.current.resize();
            }
          };
          window.addEventListener('resize', resizeHandler);

          // Use ResizeObserver for better responsiveness
          if (window.ResizeObserver && chargeDischargeRef.current) {
            resizeObserver = new ResizeObserver(() => {
              if (chargeDischargeInstanceRef.current) {
                chargeDischargeInstanceRef.current.resize();
              }
            });
            resizeObserver.observe(chargeDischargeRef.current);
          }
        }
      })
      .catch((error) => {
        console.error('Failed to load ECharts:', error);
      });

    return () => {
      mounted = false;
      if (resizeHandler) {
        window.removeEventListener('resize', resizeHandler);
      }
      if (resizeObserver) {
        resizeObserver.disconnect();
      }
      if (chargeDischargeInstanceRef.current) {
        chargeDischargeInstanceRef.current.dispose();
        chargeDischargeInstanceRef.current = undefined;
      }
    };
  }, [filteredData, loading, activeTab, theme]);

  // SOC & Temperature Line Chart
  useEffect(() => {
    if (loading || !socTempRef.current || activeTab !== 'soc-temp') return;

    let mounted = true;
    let resizeHandler: (() => void) | null = null;
    let resizeObserver: ResizeObserver | null = null;

    // Helper function to check if container has valid dimensions
    const waitForContainerDimensions = (container: HTMLElement, maxAttempts = 20): Promise<boolean> => {
      return new Promise((resolve) => {
        let attempts = 0;
        const checkDimensions = () => {
          if (!mounted) {
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
        if (!mounted || !window.echarts || !socTempRef.current) return;

        // Wait for container to have valid dimensions
        const hasDimensions = await waitForContainerDimensions(socTempRef.current);
        if (!mounted || !hasDimensions || !socTempRef.current) return;

        if (socTempInstanceRef.current) {
          socTempInstanceRef.current.dispose();
        }

        const chartInstance = initChart(socTempRef.current);
        if (!chartInstance) return;
        socTempInstanceRef.current = chartInstance;

        // Group data by date
        const dateGroups: Record<string, { minSoc: number[]; maxSoc: number[]; minTemp: number[]; maxTemp: number[] }> = {};
        filteredData.forEach((row) => {
          if (!row.date) return;
          if (!dateGroups[row.date]) {
            dateGroups[row.date] = { minSoc: [], maxSoc: [], minTemp: [], maxTemp: [] };
          }
          const minSoc = typeof row.min_soc === 'string' ? parseFloat(row.min_soc) : row.min_soc;
          const maxSoc = typeof row.max_soc === 'string' ? parseFloat(row.max_soc) : row.max_soc;
          const minTemp = typeof row.min_ess_temperature === 'string' ? parseFloat(row.min_ess_temperature) : row.min_ess_temperature;
          const maxTemp = typeof row.max_ess_temperature === 'string' ? parseFloat(row.max_ess_temperature) : row.max_ess_temperature;
          if (typeof minSoc === 'number' && !isNaN(minSoc)) dateGroups[row.date].minSoc.push(minSoc);
          if (typeof maxSoc === 'number' && !isNaN(maxSoc)) dateGroups[row.date].maxSoc.push(maxSoc);
          if (typeof minTemp === 'number' && !isNaN(minTemp)) dateGroups[row.date].minTemp.push(minTemp);
          if (typeof maxTemp === 'number' && !isNaN(maxTemp)) dateGroups[row.date].maxTemp.push(maxTemp);
        });

        const sortedDates = Object.keys(dateGroups).sort((a, b) => new Date(a).getTime() - new Date(b).getTime());
        const minSocData = sortedDates.map((date) => {
          const values = dateGroups[date].minSoc;
          return values.length > 0 ? Math.round(Math.min(...values)) : null;
        });
        const maxSocData = sortedDates.map((date) => {
          const values = dateGroups[date].maxSoc;
          return values.length > 0 ? Math.round(Math.max(...values)) : null;
        });
        const minTempData = sortedDates.map((date) => {
          const values = dateGroups[date].minTemp;
          return values.length > 0 ? Math.round(Math.min(...values)) : null;
        });
        const maxTempData = sortedDates.map((date) => {
          const values = dateGroups[date].maxTemp;
          return values.length > 0 ? Math.round(Math.max(...values)) : null;
        });

        if (sortedDates.length === 0) {
          chartInstance.setOption({
            backgroundColor: chartBg,
            title: { text: 'SOC & Temperature Trend', left: 'center', textStyle: { fontSize: 18, fontWeight: 'bold', color: theme === 'dark' ? '#38bdf8' : '#0072ce' } },
            graphic: [{ type: 'text', left: 'center', top: 'middle', style: { text: 'No data available', fontSize: 16, fill: secondaryTextColor } }],
          });
        } else {
          const option = {
            backgroundColor: chartBg,
            title: { text: 'SOC & Temperature Trend', left: 'center', textStyle: { fontSize: 18, fontWeight: 'bold', color: theme === 'dark' ? '#38bdf8' : '#0072ce' } },
            tooltip: { 
              trigger: 'axis', 
              backgroundColor: theme === 'dark' ? 'rgba(15, 23, 42, 0.95)' : 'rgba(255, 255, 255, 0.98)',
              borderColor: theme === 'dark' ? '#38bdf8' : '#0072ce',
              textStyle: { fontSize: 17, fontWeight: 'bold', color: textColor } 
            },
            legend: {
              data: ['Min SOC', 'Max SOC', 'Min ESS Temperature', 'Max ESS Temperature'],
              textStyle: { fontSize: 16, fontWeight: 'bold', color: secondaryTextColor },
              bottom: 25,
              left: 'center',
            },
            grid: { left: 80, right: 80, bottom: 80, top: 60 },
            xAxis: { 
              type: 'category', 
              data: sortedDates, 
              axisLabel: { formatter: '{value}', fontSize: 13, fontWeight: 'bold', color: secondaryTextColor }, 
              axisLine: { lineStyle: { color: axisLineColor } } 
            },
            yAxis: [
              {
                type: 'value',
                name: 'Temperature (°C)',
                nameLocation: 'middle',
                nameGap: 60,
                nameTextStyle: { fontSize: 14, fontWeight: 'bold', color: textColor },
                axisLabel: { formatter: '{value}', fontSize: 13, fontWeight: 'bold', color: textColor },
                position: 'left',
                axisLine: { lineStyle: { color: axisLineColor } },
                splitLine: { lineStyle: { color: splitLineColor, type: 'dashed', width: 1 } },
              },
              {
                type: 'value',
                name: 'SOC (%)',
                nameLocation: 'middle',
                nameGap: 60,
                nameTextStyle: { fontSize: 14, fontWeight: 'bold', color: textColor },
                axisLabel: { formatter: '{value}', fontSize: 13, fontWeight: 'bold', color: textColor },
                position: 'right',
                axisLine: { lineStyle: { color: axisLineColor } },
                splitLine: { lineStyle: { color: splitLineColor, type: 'dashed', width: 1 } },
              },
            ],
            series: [
              { name: 'Min SOC', type: 'line', data: minSocData, lineStyle: { width: 2.5 }, yAxisIndex: 1 },
              { name: 'Max SOC', type: 'line', data: maxSocData, lineStyle: { width: 2.5 }, yAxisIndex: 1 },
              { name: 'Min ESS Temperature', type: 'line', data: minTempData, lineStyle: { width: 2.5 }, yAxisIndex: 0 },
              { name: 'Max ESS Temperature', type: 'line', data: maxTempData, lineStyle: { width: 2.5 }, yAxisIndex: 0 },
            ],
            toolbox: {
              feature: {
                saveAsImage: { 
                  title: 'Save', 
                  name: 'soc_temperature_chart',
                  iconStyle: { borderColor: theme === 'dark' ? '#38bdf8' : '#0072ce' } 
                },
                dataZoom: { 
                  title: { zoom: 'Zoom', back: 'Reset' }, 
                  iconStyle: { borderColor: theme === 'dark' ? '#38bdf8' : '#0072ce' } 
                },
                restore: { 
                  title: 'Restore', 
                  iconStyle: { borderColor: theme === 'dark' ? '#38bdf8' : '#0072ce' } 
                },
              },
              right: 15,
              top: 10,
              iconStyle: { borderWidth: 1.5 },
              emphasis: { iconStyle: { borderColor: theme === 'dark' ? '#0ea5e9' : '#0056a3' } },
            },
          };

          chartInstance.setOption(option);

          // Resize after a short delay to ensure container has final dimensions
          setTimeout(() => {
            if (mounted && socTempInstanceRef.current) {
              socTempInstanceRef.current.resize();
            }
          }, 100);

          resizeHandler = () => {
            if (socTempInstanceRef.current) {
              socTempInstanceRef.current.resize();
            }
          };
          window.addEventListener('resize', resizeHandler);

          // Use ResizeObserver for better responsiveness
          if (window.ResizeObserver && socTempRef.current) {
            resizeObserver = new ResizeObserver(() => {
              if (socTempInstanceRef.current) {
                socTempInstanceRef.current.resize();
              }
            });
            resizeObserver.observe(socTempRef.current);
          }
        }
      })
      .catch((error) => {
        console.error('Failed to load ECharts:', error);
      });

    return () => {
      mounted = false;
      if (resizeHandler) {
        window.removeEventListener('resize', resizeHandler);
      }
      if (resizeObserver) {
        resizeObserver.disconnect();
      }
      if (socTempInstanceRef.current) {
        socTempInstanceRef.current.dispose();
        socTempInstanceRef.current = undefined;
      }
    };
  }, [filteredData, loading, activeTab, theme]);

  // Resize charts when tab changes
  useEffect(() => {
    const timeout = setTimeout(() => {
      if (activeTab === 'all-energy' && barChartInstanceRef.current) {
        barChartInstanceRef.current.resize();
      } else if (activeTab === 'charge-discharge' && chargeDischargeInstanceRef.current) {
        chargeDischargeInstanceRef.current.resize();
      } else if (activeTab === 'soc-temp' && socTempInstanceRef.current) {
        socTempInstanceRef.current.resize();
      }
    }, 100);
    return () => clearTimeout(timeout);
  }, [activeTab]);

  const loadingTextColor = theme === 'dark' ? '#94a3b8' : '#64748b';

  if (loading) {
    return (
      <div style={{ padding: '60px 0', textAlign: 'center', fontSize: '1.4rem', color: loadingTextColor }}>
        Loading charts...
      </div>
    );
  }

  return (
    <div style={{ width: 'calc(100% - 32px)', margin: '0 16px 1rem 16px' }}>
      {/* Tab Navigation */}
      <div
        className="border"
        style={{
          display: 'flex',
          borderRadius: '8px 8px 0 0',
          marginTop: 0,
          overflow: 'hidden',
          boxShadow: chartContainerShadow,
          borderColor: chartContainerBorder,
          background: chartContainerBg,
        }}
      >
        <button
          type="button"
          onClick={() => setActiveTab('all-energy')}
          style={{
            flex: 1,
            padding: '0.4rem 0.6rem',
            background: activeTab === 'all-energy' ? tabActiveBg : 'transparent',
            border: 'none',
            color: activeTab === 'all-energy' ? tabActiveText : tabInactiveText,
            fontSize: '1.1rem',
            fontWeight: activeTab === 'all-energy' ? 700 : 600,
            cursor: 'pointer',
            transition: 'all 0.3s ease',
            borderRight: `1px solid ${tabBorder}`,
            letterSpacing: '0.5px',
            whiteSpace: 'nowrap',
          }}
        >
          📊 All Energy (Bar Chart)
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('charge-discharge')}
          style={{
            flex: 1,
            padding: '0.4rem 0.6rem',
            background: activeTab === 'charge-discharge' ? tabActiveBg : 'transparent',
            border: 'none',
            color: activeTab === 'charge-discharge' ? tabActiveText : tabInactiveText,
            fontSize: '1.1rem',
            fontWeight: activeTab === 'charge-discharge' ? 700 : 600,
            cursor: 'pointer',
            transition: 'all 0.3s ease',
            borderRight: `1px solid ${tabBorder}`,
            letterSpacing: '0.5px',
            whiteSpace: 'nowrap',
          }}
        >
          📈 Charge vs Discharge (Line Chart)
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('soc-temp')}
          style={{
            flex: 1,
            padding: '0.4rem 0.6rem',
            background: activeTab === 'soc-temp' ? tabActiveBg : 'transparent',
            border: 'none',
            color: activeTab === 'soc-temp' ? tabActiveText : tabInactiveText,
            fontSize: '1.1rem',
            fontWeight: activeTab === 'soc-temp' ? 700 : 600,
            cursor: 'pointer',
            transition: 'all 0.3s ease',
            letterSpacing: '0.5px',
            whiteSpace: 'nowrap',
          }}
        >
          🌡️ SOC & Temperature (Line Chart)
        </button>
      </div>

      {/* Tab Content */}
      <div
        className="rounded-xl border shadow-xl"
        style={{
          borderTop: 'none',
          borderRadius: '0 0 8px 8px',
          minHeight: '450px',
          borderColor: chartContainerBorder,
          background: chartContainerBg,
          boxShadow: chartContainerShadow,
        }}
      >
        {activeTab === 'all-energy' && (
          <div ref={barChartRef} style={{ height: '100%', minHeight: '450px', width: '100%' }} />
        )}
        {activeTab === 'charge-discharge' && (
          <div ref={chargeDischargeRef} style={{ height: '100%', minHeight: '350px', width: '100%' }} />
        )}
        {activeTab === 'soc-temp' && (
          <div ref={socTempRef} style={{ height: '100%', minHeight: '350px', width: '100%' }} />
        )}
      </div>
    </div>
  );
}

