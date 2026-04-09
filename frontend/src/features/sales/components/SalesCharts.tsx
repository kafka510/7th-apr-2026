/**
 * Sales Charts Component using ECharts - React Style V1
 */
 
import { useEffect, useRef } from 'react';
import type { ChartDataPoint } from '../types';
import { useTheme } from '../../../contexts/ThemeContext';

interface SalesChartsProps {
  solarGenData: ChartDataPoint[];
  bessGenData: ChartDataPoint[];
  co2Data: ChartDataPoint[];
  treesData: ChartDataPoint[];
}

// Import ECharts types
import type { EChartsInstance } from '../../../echarts';

function loadECharts(): Promise<void> {
  return new Promise((resolve, reject) => {
    if (window.echarts) {
      resolve();
      return;
    }

    const script = document.createElement('script');
    script.src = 'https://cdn.jsdelivr.net/npm/echarts/dist/echarts.min.js';
    script.onload = () => resolve();
    script.onerror = () => reject(new Error('Failed to load ECharts'));
    document.head.appendChild(script);
  });
}

function getMonthAbbr(ym: string): string {
  if (!ym) return '';
  const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const match = ym.match(/\d{4}-(\d{1,2})/);
  if (match) {
    const m = parseInt(match[1], 10);
    return monthNames[m - 1] || ym;
  }
  return ym;
}

export function SalesCharts({ solarGenData, bessGenData, co2Data, treesData }: SalesChartsProps) {
  const { theme } = useTheme();
  const solarChartRef = useRef<HTMLDivElement>(null);
  const bessChartRef = useRef<HTMLDivElement>(null);
  const co2ChartRef = useRef<HTMLDivElement>(null);
  const treesChartRef = useRef<HTMLDivElement>(null);

  const chartInstancesRef = useRef<{
    solar?: EChartsInstance;
    bess?: EChartsInstance;
    co2?: EChartsInstance;
    trees?: EChartsInstance;
  }>({});

  useEffect(() => {
    let mounted = true;

    loadECharts()
      .then(() => {
        if (!mounted || !window.echarts) return;

        // Cleanup existing charts
        Object.values(chartInstancesRef.current).forEach((chart) => {
          if (chart) chart.dispose();
        });
        chartInstancesRef.current = {};

        // Get all unique months and sort them
        const allMonths = [
          ...new Set([...solarGenData, ...bessGenData, ...co2Data, ...treesData].map((d) => d.month)),
        ].sort();
        const labels = allMonths.map(getMonthAbbr);

        // Create data arrays aligned with months
        const getDataForMonths = (data: ChartDataPoint[]): number[] => {
          return allMonths.map((month) => {
            const point = data.find((d) => d.month === month);
            return point ? Number(point.value) : 0;
          });
        };

        const solarValues = getDataForMonths(solarGenData);
        const bessValues = getDataForMonths(bessGenData);
        const co2Values = getDataForMonths(co2Data);
        const treesValues = getDataForMonths(treesData);

        // Theme-aware colors
        const isDark = theme === 'dark';
        const titleColor = isDark ? '#38bdf8' : '#0072ce';
        const tooltipBg = isDark ? 'rgba(15, 23, 42, 0.95)' : 'rgba(255, 255, 255, 0.95)';
        const tooltipBorder = isDark ? 'rgba(56, 189, 248, 0.5)' : 'rgba(0, 114, 206, 0.5)';
        const tooltipText = isDark ? '#e2e8f0' : '#1a1a1a';
        const axisLabelColor = isDark ? '#cbd5e1' : '#4a5568';
        const axisLineColor = isDark ? '#475569' : '#cbd5e0';
        const splitLineColor = isDark ? '#334155' : '#e2e8f0';
        const labelColor = isDark ? '#e2e8f0' : '#1a1a1a';

        // Common chart options for React Style V1
        const getChartOption = (title: string, data: number[], color: string) => ({
          backgroundColor: 'transparent',
          title: {
            text: title,
            left: 'center',
            top: 5,
            textStyle: {
              color: titleColor,
              fontSize: 14,
              fontWeight: 'bold',
            },
          },
          tooltip: {
            trigger: 'axis',
            backgroundColor: tooltipBg,
            borderColor: tooltipBorder,
            borderWidth: 1,
            textStyle: {
              color: tooltipText,
              fontSize: 12,
            },
            formatter: (params: Array<{ value: number; axisValue: string }>) => {
              if (!params || params.length === 0) return '';
              const param = params[0];
              return `${param.axisValue}<br/>${title}: <b>${param.value.toLocaleString()}</b>`;
            },
          },
          toolbox: {
            feature: {
              saveAsImage: {
                title: 'Save',
                iconStyle: {
                  borderColor: '#38bdf8',
                },
              },
              dataZoom: {
                title: {
                  zoom: 'Zoom',
                  back: 'Reset',
                },
                iconStyle: {
                  borderColor: '#38bdf8',
                },
              },
              restore: {
                title: 'Restore',
                iconStyle: {
                  borderColor: '#38bdf8',
                },
              },
            },
            itemSize: 10,
            iconStyle: {
              borderColor: '#38bdf8',
              borderWidth: 1,
            },
            emphasis: {
              iconStyle: {
                borderColor: '#0ea5e9',
              },
            },
            right: 20,
            top: 10,
            itemGap: 10,
          },
          grid: {
            left: '3%',
            right: '3%',
            top: '22%',
            bottom: '12%',
            containLabel: true,
          },
          xAxis: {
            type: 'category',
            data: labels,
            axisLabel: {
              color: axisLabelColor,
              fontSize: 11,
              rotate: 45,
            },
            axisLine: {
              lineStyle: {
                color: axisLineColor,
              },
            },
          },
          yAxis: {
            type: 'value',
            axisLabel: {
              color: axisLabelColor,
              fontSize: 11,
              formatter: (value: number) => {
                if (value >= 1000) {
                  return `${Math.round(value / 1000)}K`;
                }
                return value.toLocaleString();
              },
            },
            axisLine: {
              lineStyle: {
                color: axisLineColor,
              },
            },
            splitLine: {
              lineStyle: {
                color: splitLineColor,
                type: 'dashed',
              },
            },
          },
          series: [
            {
              type: 'bar',
              data: data,
              barWidth: '30px',
              barGap: '20%',
              itemStyle: {
                color: {
                  type: 'linear',
                  x: 0,
                  y: 0,
                  x2: 0,
                  y2: 1,
                  colorStops: [
                    { offset: 0, color: color },
                    { offset: 1, color: color + 'CC' },
                  ],
                },
                borderRadius: [6, 6, 0, 0],
                shadowColor: color,
                shadowBlur: 8,
                shadowOffsetY: 2,
              },
              label: {
                show: true,
                position: 'top',
                color: labelColor,
                fontSize: 11,
                fontWeight: 'bold',
                formatter: (params: { value: number }) => {
                  if (params.value >= 1000) {
                    return Math.round(params.value / 1000) + 'K';
                  }
                  return params.value > 0 ? Math.round(params.value).toString() : '';
                },
              },
              emphasis: {
                itemStyle: {
                  shadowBlur: 15,
                  shadowOffsetX: 0,
                  shadowColor: color,
                },
              },
            },
          ],
        });

        // Initialize charts
        if (solarChartRef.current) {
          chartInstancesRef.current.solar = window.echarts!.init(solarChartRef.current);
          chartInstancesRef.current.solar.setOption(
            getChartOption('Solar Generation (MWh)', solarValues, '#facc15')
          );
        }

        if (bessChartRef.current) {
          chartInstancesRef.current.bess = window.echarts!.init(bessChartRef.current);
          chartInstancesRef.current.bess.setOption(
            getChartOption('BESS Discharge (MWh)', bessValues, '#8b5cf6')
          );
        }

        if (co2ChartRef.current) {
          chartInstancesRef.current.co2 = window.echarts!.init(co2ChartRef.current);
          chartInstancesRef.current.co2.setOption(
            getChartOption('Emissions Reduced (tCO₂)', co2Values, '#14b8a6')
          );
        }

        if (treesChartRef.current) {
          chartInstancesRef.current.trees = window.echarts!.init(treesChartRef.current);
          chartInstancesRef.current.trees.setOption(
            getChartOption('Trees Protected', treesValues, '#22c55e')
          );
        }

        // Handle window resize
        const handleResize = () => {
          Object.values(chartInstancesRef.current).forEach((chart) => {
            if (chart) chart.resize();
          });
        };

        window.addEventListener('resize', handleResize);
        return () => {
          window.removeEventListener('resize', handleResize);
        };
      })
      .catch((error) => {
        console.error('Failed to load ECharts:', error);
      });

    return () => {
      mounted = false;
      Object.values(chartInstancesRef.current).forEach((chart) => {
        if (chart) chart.dispose();
      });
      chartInstancesRef.current = {};
    };
  }, [solarGenData, bessGenData, co2Data, treesData, theme]);

  const chartBg = theme === 'dark' 
    ? 'linear-gradient(to bottom right, rgba(15, 23, 42, 0.9), rgba(30, 41, 59, 0.6))'
    : 'linear-gradient(to bottom right, #ffffff, #f8fafc)';
  const chartBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(226, 232, 240, 0.8)';

  return (
    <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
      {/* Solar Generation Chart */}
      <div 
        className="rounded-xl p-2 shadow-xl"
        style={{
          border: `1px solid ${chartBorder}`,
          background: chartBg,
          transition: 'background 0.3s ease, border-color 0.3s ease',
        }}
      >
        <div ref={solarChartRef} style={{ width: '100%', height: '280px' }} />
      </div>

      {/* BESS Discharge Chart */}
      <div 
        className="rounded-xl p-2 shadow-xl"
        style={{
          border: `1px solid ${chartBorder}`,
          background: chartBg,
          transition: 'background 0.3s ease, border-color 0.3s ease',
        }}
      >
        <div ref={bessChartRef} style={{ width: '100%', height: '280px' }} />
      </div>

      {/* CO₂ Saved Chart */}
      <div 
        className="rounded-xl p-2 shadow-xl"
        style={{
          border: `1px solid ${chartBorder}`,
          background: chartBg,
          transition: 'background 0.3s ease, border-color 0.3s ease',
        }}
      >
        <div ref={co2ChartRef} style={{ width: '100%', height: '280px' }} />
      </div>

      {/* Trees Protected Chart */}
      <div 
        className="rounded-xl p-2 shadow-xl"
        style={{
          border: `1px solid ${chartBorder}`,
          background: chartBg,
          transition: 'background 0.3s ease, border-color 0.3s ease',
        }}
      >
        <div ref={treesChartRef} style={{ width: '100%', height: '280px' }} />
      </div>
    </div>
  );
}
