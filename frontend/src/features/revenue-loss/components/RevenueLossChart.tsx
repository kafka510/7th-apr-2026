import { useEffect, useRef, useState } from 'react';
import { useResponsiveFontSize } from '../../../utils/fontScaling';
import type { EChartsInstance } from '../../../echarts';
import type { RevenueLossDataPoint, RevenueLossData } from '../types';

interface RevenueLossChartProps {
  data: RevenueLossDataPoint[];
  selectedMonth?: string;
  selectedYear?: string;
  budgetType?: 'expected' | 'operational';
  revenueData?: RevenueLossData[];
  onAssetClick?: (asset: string, period: string) => void;
}

// Component-specific ECharts instance extensions
interface EChartsChart extends EChartsInstance {
  on: (event: string, handler: (params: EChartsEventParams) => void) => void;
  getZr: () => {
    on: (event: string, handler: (params: EChartsZrEvent) => void) => void;
  };
  convertFromPixel: (coord: { seriesIndex: number }, point: [number, number]) => [number, number] | null;
  clear: () => void;
  getWidth: () => number;
}

interface EChartsStatic {
  init: (dom: HTMLElement | null, theme?: string | null, opts?: { renderer?: string; width?: string; height?: string }) => EChartsChart;
}

// Type guard to ensure window.echarts matches our EChartsStatic interface
function isEChartsStatic(echarts: unknown): echarts is EChartsStatic {
  return typeof echarts === 'object' && echarts !== null && 'init' in echarts;
}

interface EChartsEventParams {
  componentType?: string;
  name?: string;
  value?: unknown;
  dataIndex?: number;
  event?: {
    event: MouseEvent;
  };
}

interface EChartsZrEvent {
  offsetX: number;
  offsetY: number;
  event: MouseEvent;
}

function loadECharts(): Promise<void> {
  return new Promise((resolve, reject) => {
    if (window.echarts && isEChartsStatic(window.echarts)) {
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

function initChart(dom: HTMLElement | null): EChartsChart | undefined {
  if (!window.echarts || !dom) return undefined;
  return window.echarts.init(dom) as EChartsChart;
}

function getBigFont(base = 32, max = 66, min = 16): number {
  const width = window.innerWidth;
  return Math.max(min, Math.min(max, Math.round(base * (width / 1920))));
}

function getYAxisNameGap(): number {
  const width = window.innerWidth;
  if (width <= 1200) return 40;
  if (width <= 1400) return 45;
  if (width <= 1600) return 50;
  return 55;
}

const MONTH_LOOKUP: Record<string, string> = {
  jan: '01',
  feb: '02',
  mar: '03',
  apr: '04',
  may: '05',
  jun: '06',
  jul: '07',
  aug: '08',
  sep: '09',
  oct: '10',
  nov: '11',
  dec: '12',
};

function normalizeMonthValue(value: string | null | undefined): string | null {
  if (!value) return null;
  const raw = String(value).trim();
  if (!raw) return null;

  const yyyymmMatch = raw.match(/^(\d{4})[-/](\d{1,2})/);
  if (yyyymmMatch) {
    const year = yyyymmMatch[1];
    const month = yyyymmMatch[2].padStart(2, '0');
    const monthNum = Number(month);
    if (monthNum >= 1 && monthNum <= 12) {
      return `${year}-${month}`;
    }
  }

  const mmyyyyMatch = raw.match(/^(\d{1,2})[-/](\d{4})/);
  if (mmyyyyMatch) {
    const month = mmyyyyMatch[1].padStart(2, '0');
    const year = mmyyyyMatch[2];
    const monthNum = Number(month);
    if (monthNum >= 1 && monthNum <= 12) {
      return `${year}-${month}`;
    }
  }

  const monthNameMatch = raw.match(/^([A-Za-z]{3,9})[-/\s](\d{2,4})$/);
  if (monthNameMatch) {
    const monthName = monthNameMatch[1].slice(0, 3).toLowerCase();
    const month = MONTH_LOOKUP[monthName];
    if (month) {
      const yearRaw = monthNameMatch[2];
      const year = yearRaw.length === 2 ? `20${yearRaw}` : yearRaw;
      return `${year}-${month}`;
    }
  }

  const yearNameMatch = raw.match(/^(\d{2,4})[-/\s]([A-Za-z]{3,9})$/);
  if (yearNameMatch) {
    const yearRaw = yearNameMatch[1];
    const year = yearRaw.length === 2 ? `20${yearRaw}` : yearRaw;
    const monthName = yearNameMatch[2].slice(0, 3).toLowerCase();
    const month = MONTH_LOOKUP[monthName];
    if (month) {
      return `${year}-${month}`;
    }
  }

  return null;
}

// Format value as K (thousands) or M (millions) for Y-axis
function formatYAxis(v: number): string {
  if (isNaN(v)) return '';
  if (Math.abs(v) >= 1000000) {
    const millions = v / 1000000;
    return Math.round(millions) + 'M';
  }
  if (Math.abs(v) >= 1000) {
    const thousands = v / 1000;
    return Math.round(thousands) + 'K';
  }
  return Math.round(v).toString();
}

// Format currency with thousand separators
function formatCurrency(value: number): string {
  if (isNaN(value)) return '0';
  return value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// Format number with thousand separators but no decimals (for tooltips)
function formatNumberWithSeparator(value: number): string {
  if (isNaN(value)) return '0';
  return Math.round(value).toLocaleString('en-US');
}

function isInSelectedMonth(rowMonth: string | null | undefined, selectedMonth: string | null, selectedYear: string | null): boolean {
  const monthStr = normalizeMonthValue(rowMonth);
  if (!monthStr) return false;

  if (selectedYear) {
    return monthStr.slice(0, 4) === String(selectedYear);
  } else if (selectedMonth) {
    return monthStr === selectedMonth;
  }

  return false;
}

function createRevenueLossTooltip(
  assetNo: string,
  period: string,
  revenueData: RevenueLossData[],
  budgetType: 'expected' | 'operational',
  selectedMonth?: string,
  selectedYear?: string
): string {
  const matches = revenueData.filter((r) => {
    const asset = r.asset_no || r.assetno || r.asset || 'Unknown';
    const assetMatch = String(asset).trim() === String(assetNo).trim();
    const monthMatch = isInSelectedMonth(r.month, selectedMonth || null, selectedYear || null);
    return assetMatch && monthMatch;
  });

  if (matches.length === 0) {
    return `<div style="padding: 15px; text-align: center;">
      <h3 style="margin: 0 0 10px 0; color: #38bdf8;">No Data Available</h3>
      <p style="margin: 5px 0; color: #e2e8f0;"><b>Asset:</b> ${assetNo}</p>
      <p style="margin: 5px 0; color: #e2e8f0;"><b>Period:</b> ${period}</p>
      <p style="margin: 5px 0; color: #94a3b8;">No revenue loss data available for this period</p>
    </div>`;
  }

  const firstMatch = matches[0];
  const country = firstMatch.country || 'N/A';
  const portfolio = firstMatch.portfolio || 'N/A';

  const revenueField = budgetType === 'operational' ? 'revenue_loss_op' : 'revenue_loss';
                    const totalLoss = matches.reduce((sum, m) => sum + (parseFloat(String(m[revenueField])) || 0), 0);
  const observations = [...new Set(matches.map((m) => m.revenue_loss_observation).filter(Boolean))];
  const actions = [...new Set(matches.map((m) => m.revenue_loss_action_need_to_taken).filter(Boolean))];

  const isLoss = totalLoss < 0;
  const revenueType = isLoss ? 'Revenue Loss' : 'Revenue Gain';
  const revenueValue = Math.abs(totalLoss);

  const isYearMode = !!selectedYear && !selectedMonth;

  if (isYearMode) {
    return `
      <div style="padding: 15px; max-width: 500px; font-family: 'Segoe UI', Arial, sans-serif;">
        <div style="margin-bottom: 10px; border-bottom: 2px solid #38bdf8; padding-bottom: 10px;">
          <h3 style="margin: 0 0 10px 0; color: #38bdf8;">Revenue Details</h3>
          <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
            <tbody>
              <tr>
                <td style="padding: 8px 8px 8px 0; font-weight: bold; color: #cbd5e1; width: 120px;">Country:</td>
                <td style="padding: 8px 0; color: #e2e8f0;">${country}</td>
              </tr>
              <tr>
                <td style="padding: 8px 8px 8px 0; font-weight: bold; color: #cbd5e1;">Portfolio:</td>
                <td style="padding: 8px 0; color: #e2e8f0;">${portfolio}</td>
              </tr>
              <tr>
                <td style="padding: 8px 8px 8px 0; font-weight: bold; color: #cbd5e1;">Asset No:</td>
                <td style="padding: 8px 0; color: #e2e8f0;">${assetNo}</td>
              </tr>
              <tr>
                <td style="padding: 8px 8px 8px 0; font-weight: bold; color: #cbd5e1;">${revenueType}:</td>
                <td style="padding: 8px 0; font-weight: bold; color: ${isLoss ? '#f87171' : '#4ade80'};">
                  $${formatCurrency(revenueValue)}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    `;
  } else {
    return `
      <div style="padding: 15px; max-width: 800px; font-family: 'Segoe UI', Arial, sans-serif;">
        <div style="margin-bottom: 15px; border-bottom: 2px solid #38bdf8; padding-bottom: 10px;">
          <h3 style="margin: 0 0 5px 0; color: #38bdf8;">Revenue Loss Details</h3>
          <p style="margin: 3px 0; color: #e2e8f0;"><b>Asset:</b> ${assetNo}</p>
          <p style="margin: 3px 0; color: #e2e8f0;"><b>Period:</b> ${period}</p>
          <p style="margin: 3px 0; color: #e2e8f0;"><b>Data Points:</b> ${matches.length}</p>
          <p style="margin: 3px 0; color: #e2e8f0;"><b>Total ${revenueType}:</b> $${formatNumberWithSeparator(totalLoss)}</p>
        </div>
        ${observations.length > 0 || actions.length > 0 ? `
          <div style="margin-bottom: 15px;">
            <h4 style="margin: 0 0 10px 0; color: #38bdf8;">Observations & Actions</h4>
            ${observations.length > 0 ? `
              <div style="margin-bottom: 10px;">
                <p style="margin: 0 0 5px 0; font-weight: bold; color: #cbd5e1;">Observations:</p>
                <ul style="margin: 0; padding-left: 20px; color: #e2e8f0;">
                  ${observations.map((obs) => `<li style="margin-bottom: 3px;">${obs}</li>`).join('')}
                </ul>
              </div>
            ` : ''}
            ${actions.length > 0 ? `
              <div>
                <p style="margin: 0 0 5px 0; font-weight: bold; color: #cbd5e1;">Actions Needed:</p>
                <ul style="margin: 0; padding-left: 20px; color: #e2e8f0;">
                  ${actions.map((action) => `<li style="margin-bottom: 3px;">${action}</li>`).join('')}
                </ul>
              </div>
            ` : ''}
          </div>
        ` : ''}
      </div>
    `;
  }
}

export function RevenueLossChart({
  data,
  selectedMonth,
  selectedYear,
  budgetType = 'expected',
  revenueData = [],
  onAssetClick,
}: RevenueLossChartProps) {
  // Responsive font sizes
  const bodyFontSize = useResponsiveFontSize(10, 14, 9);
  
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstanceRef = useRef<EChartsChart | undefined>(undefined);
  const [toolboxOpen, setToolboxOpen] = useState(false);
  const [toolboxContent, setToolboxContent] = useState<{
    asset: string;
    period: string;
    loss: string;
    detailsHtml: string;
  } | null>(null);

  useEffect(() => {
    let mounted = true;
    let resizeHandler: (() => void) | null = null;

    loadECharts()
      .then(() => {
        if (!mounted || !window.echarts) return;

        if (chartRef.current) {
          if (chartInstanceRef.current) {
            chartInstanceRef.current.dispose();
          }
          const chartInstance = initChart(chartRef.current);
          if (!chartInstance) return;
          chartInstanceRef.current = chartInstance;

          if (data.length === 0) {
            chartInstance.setOption({
              title: {
                text: 'No data found for selected filters',
                left: 'center',
                top: 'middle',
                textStyle: { color: 'red', fontSize: 16 },
              },
            });
          } else {
            // Chart setup for when data exists
            const x = data.map((d) => d.asset);
            const y = data.map((d) => d.loss);
            const colors = data.map((d) => d.color);

            const isYearMode = !!selectedYear && !selectedMonth;
            const suffix = isYearMode
              ? ` (${selectedYear} - Full Year)`
              : selectedMonth
                ? ` (${selectedMonth})`
                : '';

            const chartTitleText =
              budgetType === 'operational'
                ? 'Revenue Loss/Gain ($) based on Operational Budget'
                : 'Revenue Loss/Gain ($) based on Expected Budget';

            const option = {
              title: {
                show: true,
                text: chartTitleText + suffix,
                left: 'center',
                top: 10,
                textStyle: {
                  fontSize: getBigFont(14, 22, 12),
                  fontWeight: 'bold',
                  color: '#38bdf8',
                },
              },
              tooltip: {
                show: false, // Disable tooltip on hover - only open on click
                trigger: 'none',
                confine: true,
                axisPointer: { type: 'shadow' },
              },
              grid: { left: 25, right: 60, top: 60, bottom: 50, containLabel: true },
              toolbox: {
                show: true,
                feature: {
                  saveAsImage: {
                    title: 'Save as Image',
                    backgroundColor: 'transparent',
                  },
                  dataZoom: {
                    title: { zoom: 'Zoom', back: 'Reset' },
                  },
                  restore: { title: 'Restore' },
                },
                iconStyle: {
                  borderColor: '#38bdf8',
                  borderWidth: 1,
                },
                emphasis: {
                  iconStyle: {
                    borderColor: '#0ea5e9',
                    borderWidth: 1.5,
                  },
                },
                right: 20,
                top: 10,
                itemSize: 10,
                itemGap: 10,
              },
              xAxis: {
                type: 'category',
                data: x,
                axisLabel: {
                  rotate: 45,
                  fontSize: getBigFont(11, 15, 8),
                  interval: 'auto',
                  color: '#cbd5e1',
                  margin: 10,
                },
                axisLine: {
                  lineStyle: {
                    color: '#475569',
                  },
                },
              },
              yAxis: {
                type: 'value',
                name: 'Revenue',
                nameLocation: 'middle',
                nameGap: getYAxisNameGap(),
                axisLabel: {
                  fontSize: getBigFont(12, 17, 9),
                  formatter: (v: number) => formatYAxis(v),
                  color: '#e2e8f0',
                  interval: 'auto',
                  margin: 6,
                },
                nameTextStyle: {
                  fontSize: getBigFont(13, 19, 10),
                  fontWeight: 'bold',
                  color: '#e2e8f0',
                },
                axisLine: {
                  lineStyle: {
                    color: '#475569',
                  },
                },
                splitLine: {
                  lineStyle: {
                    color: '#334155',
                    opacity: 0.3,
                  },
                },
                min: (v: { min: number }) => Math.min(0, v.min),
              },
              dataZoom: [
                {
                  type: 'slider',
                  xAxisIndex: 0,
                  bottom: 0,
                  height: 30,
                  handleSize: 12,
                  backgroundColor: '#1e293b',
                  borderColor: '#475569',
                  fillerColor: 'rgba(56, 189, 248, 0.2)',
                  handleStyle: {
                    color: '#38bdf8',
                    borderColor: '#0ea5e9',
                  },
                  textStyle: {
                    color: '#cbd5e1',
                  },
                  dataBackground: {
                    lineStyle: {
                      color: '#475569',
                    },
                    areaStyle: {
                      color: '#334155',
                    },
                  },
                  selectedDataBackground: {
                    lineStyle: {
                      color: '#38bdf8',
                    },
                    areaStyle: {
                      color: 'rgba(56, 189, 248, 0.3)',
                    },
                  },
                },
              ],
              series: [
                {
                  type: 'bar',
                  data: y.map((val, idx) => ({
                    value: val,
                    name: x[idx],
                  })),
                  itemStyle: {
                    color: (p: { dataIndex: number }) => colors[p.dataIndex],
                    borderRadius: 2,
                  },
                  barWidth: 8,
                  barCategoryGap: '25%',
                  label: {
                    show: true,
                    position: 'top',
                    fontSize: getBigFont(13, 18, 10),
                    fontWeight: 'bold',
                    color: '#e2e8f0',
                    formatter: (p: { value: number }) => {
                      return formatYAxis(p.value);
                    },
                    distance: 8,
                    textBorderColor: '#0f172a',
                    textBorderWidth: 2,
                    overflow: 'none',
                  },
                },
              ],
              legend: {
                show: true,
                textStyle: {
                  fontSize: getBigFont(12, 18, 9),
                  color: '#cbd5e1',
                  fontWeight: 'bold',
                },
              },
              backgroundColor: 'transparent',
            };

            chartInstance.setOption(option);

            // Add click event handlers to open modal with details
            chartInstance.on('click', (params: EChartsEventParams) => {
              if (params.componentType === 'xAxis' || params.componentType === 'series') {
                const assetNo = params.name || (typeof params.dataIndex === 'number' ? x[params.dataIndex] : '');
                if (assetNo) {
                  const periodStr = isYearMode ? `${selectedYear} (Year)` : selectedMonth || '';
                  const lossValue = params.value ? String(params.value) : '0';
                  const detailsHtml = createRevenueLossTooltip(
                    String(assetNo),
                    periodStr,
                    revenueData,
                    budgetType,
                    selectedMonth,
                    selectedYear
                  );
                  
                  setToolboxContent({
                    asset: String(assetNo),
                    period: periodStr,
                    loss: lossValue,
                    detailsHtml,
                  });
                  setToolboxOpen(true);
                  
                  if (onAssetClick) {
                    onAssetClick(String(assetNo), periodStr);
                  }
                }
              }
            });

            // Add custom click handler for X-axis labels as fallback
            chartInstance.getZr().on('click', (params: EChartsZrEvent) => {
              const pointInPixel: [number, number] = [params.offsetX, params.offsetY];
              const pointInGrid = chartInstance.convertFromPixel({ seriesIndex: 0 }, pointInPixel);

              if (pointInGrid && pointInGrid[0] !== undefined && pointInGrid[0] >= 0 && pointInGrid[0] < x.length) {
                const assetIndex = Math.floor(pointInGrid[0]);
                const assetNo = x[assetIndex];
                if (assetNo) {
                  const periodStr = isYearMode ? `${selectedYear} (Year)` : selectedMonth || '';
                  const lossValue = y[assetIndex] ? String(y[assetIndex]) : '0';
                  const detailsHtml = createRevenueLossTooltip(
                    assetNo,
                    periodStr,
                    revenueData,
                    budgetType,
                    selectedMonth,
                    selectedYear
                  );
                  
                  setToolboxContent({
                    asset: assetNo,
                    period: periodStr,
                    loss: lossValue,
                    detailsHtml,
                  });
                  setToolboxOpen(true);
                  
                  if (onAssetClick) {
                    onAssetClick(assetNo, periodStr);
                  }
                }
              }
            });

            // Handle window resize
            resizeHandler = () => {
              if (chartInstanceRef.current) {
                chartInstanceRef.current.resize();
              }
            };

            window.addEventListener('resize', resizeHandler);
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
        if (chartInstanceRef.current) {
          chartInstanceRef.current.dispose();
          chartInstanceRef.current = undefined;
        }
      };
    }, [data, selectedMonth, selectedYear, budgetType, revenueData, onAssetClick]);

  const handleCloseToolbox = () => {
    setToolboxOpen(false);
    setToolboxContent(null);
  };

  return (
    <div className="relative flex size-full flex-col overflow-hidden rounded-xl border border-slate-800/80 bg-gradient-to-br from-slate-900/90 to-slate-800/60 shadow-xl">
      {/* Custom Toolbox Modal */}
      {toolboxOpen && toolboxContent && (
        <div className="from-slate-900/98 to-slate-800/98 absolute left-4 top-4 z-50 flex max-h-[calc(100%-2rem)] w-[800px] max-w-[calc(100%-2rem)] flex-col overflow-hidden rounded-xl border border-sky-500/50 bg-gradient-to-br shadow-2xl backdrop-blur-md">
          {/* Header */}
          <div className="flex shrink-0 items-center justify-between border-b border-slate-700/50 bg-gradient-to-r from-sky-900/30 to-slate-800/30 px-4 py-2.5">
            <div>
              <h3 className="text-sm font-semibold text-sky-400">Revenue Loss Details</h3>
              <p className="mt-0.5 text-slate-400" style={{ fontSize: `${bodyFontSize}px` }}>{toolboxContent.asset} - {toolboxContent.period}</p>
            </div>
            <button
              onClick={handleCloseToolbox}
              className="rounded-full p-1.5 text-slate-400 transition-all hover:bg-red-500/20 hover:text-red-400"
              aria-label="Close details"
            >
              <svg className="size-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          
          {/* Content */}
          <div className="flex-1 overflow-y-auto p-4">
            <div dangerouslySetInnerHTML={{ __html: toolboxContent.detailsHtml }} />
          </div>
          
          {/* Footer */}
          <div className="shrink-0 border-t border-slate-700/50 bg-slate-900/50 px-4 py-2 text-slate-400" style={{ fontSize: `${bodyFontSize}px` }}>
            Click on chart bars to view detailed revenue loss information
          </div>
        </div>
      )}

      <div
        ref={chartRef}
        style={{
          width: '100%',
          height: '100%',
          minHeight: 0,
        }}
      />
    </div>
  );
}

