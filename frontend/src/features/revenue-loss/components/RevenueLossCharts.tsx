import { useEffect, useRef, useState } from 'react';
import { useTheme } from '../../../contexts/ThemeContext';
import { getResponsiveFontSize, useResponsiveFontSize } from '../../../utils/fontScaling';
import type { EChartsInstance } from '../../../echarts';
import type { RevenueLossDataPoint, RevenueLossData } from '../types';

interface RevenueLossChartsProps {
  expectedData: RevenueLossDataPoint[];
  operationalData: RevenueLossDataPoint[];
  selectedMonth?: string;
  selectedYear?: string;
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

// Use centralized font scaling utility
const getBigFont = getResponsiveFontSize;

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

// Format value as K (thousands) or M (millions)
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
  selectedYear?: string,
  theme: 'light' | 'dark' = 'dark'
): string {
  const textColor = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';
  const secondaryTextColor = theme === 'dark' ? '#cbd5e1' : '#4a5568';
  const titleColor = theme === 'dark' ? '#38bdf8' : '#0072ce';
  const mutedTextColor = theme === 'dark' ? '#94a3b8' : '#64748b';
  const matches = revenueData.filter((r) => {
    const asset = r.asset_no || r.assetno || r.asset || 'Unknown';
    const assetMatch = String(asset).trim() === String(assetNo).trim();
    const monthMatch = isInSelectedMonth(r.month, selectedMonth || null, selectedYear || null);
    return assetMatch && monthMatch;
  });

  if (matches.length === 0) {
    return `<div style="padding: 15px; text-align: center;">
      <h3 style="margin: 0 0 10px 0; color: ${titleColor};">No Data Available</h3>
      <p style="margin: 5px 0; color: ${textColor};"><b>Asset:</b> ${assetNo}</p>
      <p style="margin: 5px 0; color: ${textColor};"><b>Period:</b> ${period}</p>
      <p style="margin: 5px 0; color: ${mutedTextColor};">No revenue loss data available for this period</p>
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
        <div style="margin-bottom: 10px; border-bottom: 2px solid ${titleColor}; padding-bottom: 10px;">
          <h3 style="margin: 0 0 10px 0; color: ${titleColor};">Revenue Details</h3>
          <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
            <tbody>
              <tr>
                <td style="padding: 8px 8px 8px 0; font-weight: bold; color: ${secondaryTextColor}; width: 120px;">Country:</td>
                <td style="padding: 8px 0; color: ${textColor};">${country}</td>
              </tr>
              <tr>
                <td style="padding: 8px 8px 8px 0; font-weight: bold; color: ${secondaryTextColor};">Portfolio:</td>
                <td style="padding: 8px 0; color: ${textColor};">${portfolio}</td>
              </tr>
              <tr>
                <td style="padding: 8px 8px 8px 0; font-weight: bold; color: ${secondaryTextColor};">Asset No:</td>
                <td style="padding: 8px 0; color: ${textColor};">${assetNo}</td>
              </tr>
              <tr>
                <td style="padding: 8px 8px 8px 0; font-weight: bold; color: ${secondaryTextColor};">${revenueType}:</td>
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
        <div style="margin-bottom: 15px; border-bottom: 2px solid ${titleColor}; padding-bottom: 10px;">
          <h3 style="margin: 0 0 5px 0; color: ${titleColor};">Revenue Loss Details</h3>
          <p style="margin: 3px 0; color: ${textColor};"><b>Asset:</b> ${assetNo}</p>
          <p style="margin: 3px 0; color: ${textColor};"><b>Period:</b> ${period}</p>
          <p style="margin: 3px 0; color: ${textColor};"><b>Data Points:</b> ${matches.length}</p>
          <p style="margin: 3px 0; color: ${textColor};"><b>Total ${revenueType}:</b> $${formatNumberWithSeparator(totalLoss)}</p>
        </div>
        ${observations.length > 0 || actions.length > 0 ? `
          <div style="margin-bottom: 15px;">
            <h4 style="margin: 0 0 10px 0; color: ${titleColor};">Observations & Actions</h4>
            ${observations.length > 0 ? `
              <div style="margin-bottom: 10px;">
                <p style="margin: 0 0 5px 0; font-weight: bold; color: ${secondaryTextColor};">Observations:</p>
                <ul style="margin: 0; padding-left: 20px; color: ${textColor};">
                  ${observations.map((obs) => `<li style="margin-bottom: 3px;">${obs}</li>`).join('')}
                </ul>
              </div>
            ` : ''}
            ${actions.length > 0 ? `
              <div>
                <p style="margin: 0 0 5px 0; font-weight: bold; color: ${secondaryTextColor};">Actions Needed:</p>
                <ul style="margin: 0; padding-left: 20px; color: ${textColor};">
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

export function RevenueLossCharts({
  expectedData,
  operationalData,
  selectedMonth,
  selectedYear,
  revenueData = [],
  onAssetClick,
}: RevenueLossChartsProps) {
  const { theme } = useTheme();
  
  // Responsive font sizes
  const bodyFontSize = useResponsiveFontSize(10, 14, 9);
  
  const expectedChartRef = useRef<HTMLDivElement>(null);
  const operationalChartRef = useRef<HTMLDivElement>(null);
  const chartInstance1Ref = useRef<EChartsChart | undefined>(undefined);
  
  // Theme-aware colors
  const chartContainerBg = theme === 'dark'
    ? 'linear-gradient(to bottom right, rgba(15, 23, 42, 0.9), rgba(30, 41, 59, 0.6))'
    : 'linear-gradient(to bottom right, rgba(255, 255, 255, 0.95), rgba(248, 250, 252, 0.9))';
  const chartContainerBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(203, 213, 225, 0.8)';
  const chartContainerShadow = theme === 'dark' 
    ? '0 20px 25px -5px rgba(0, 0, 0, 0.4)' 
    : '0 10px 15px -3px rgba(0, 0, 0, 0.1)';
  const textColor = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';
  const secondaryTextColor = theme === 'dark' ? '#cbd5e1' : '#4a5568';
  const axisLineColor = theme === 'dark' ? '#475569' : '#cbd5e0';
  const splitLineColor = theme === 'dark' ? '#334155' : '#e2e8f0';
  const tooltipBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.95)' : 'rgba(255, 255, 255, 0.98)';
  const tooltipBorder = theme === 'dark' ? '#38bdf8' : '#0072ce';
  const chartBg = theme === 'dark' ? '#0f172a' : '#ffffff';
  const chartInstance2Ref = useRef<EChartsChart | undefined>(undefined);
  const [toolboxOpen, setToolboxOpen] = useState(false);
  const [toolboxContent, setToolboxContent] = useState<{
    asset: string;
    period: string;
    loss: string;
    detailsHtml: string;
  } | null>(null);

  useEffect(() => {
    let mounted = true;

    loadECharts()
      .then(() => {
        if (!mounted || !window.echarts) return;

        const isYearMode = !!selectedYear && !selectedMonth;
        const suffix = isYearMode
          ? ` (${selectedYear} - Full Year)`
          : selectedMonth
            ? ` (${selectedMonth})`
            : '';

        // Initialize first chart (Expected Budget) - left side
        if (expectedChartRef.current) {
          if (chartInstance1Ref.current) {
            chartInstance1Ref.current.dispose();
          }
          const chartInstance1 = initChart(expectedChartRef.current);
          if (!chartInstance1) return;
          chartInstance1Ref.current = chartInstance1;

          if (expectedData.length === 0) {
            chartInstance1.setOption({
              title: {
                text: 'No data found for selected filters',
                left: 'center',
                top: 'middle',
                textStyle: { color: '#f87171', fontSize: 16 },
              },
            });
          } else {
            // Sort by loss value, then reverse (largest to smallest in absolute terms)
            const sortedData = [...expectedData].sort((a, b) => a.loss - b.loss).reverse();
            const x1 = sortedData.map((d) => d.asset);
            const y1 = sortedData.map((d) => Math.abs(d.loss));
            const colors1 = sortedData.map((d) => d.color);

            const option1 = {
              title: {
                show: true,
                text: `Revenue Loss/Gain wrt Expected Budget${suffix}`,
                left: 'center',
                top: 8,
                textStyle: {
                  fontSize: getBigFont(16, 30, 14),
                  fontWeight: 'bold',
                  fontFamily: 'Segoe UI, Arial, sans-serif',
                  color: '#38bdf8',
                },
              },
              tooltip: {
                show: false,
                trigger: 'none',
                confine: true,
                axisPointer: { type: 'shadow' },
              },
              grid: { left: 120, right: 100, bottom: 50, top: 50 },
              toolbox: {
                show: true,
                feature: {
                  saveAsImage: {
                    title: 'Save',
                    name: 'revenue_expected_budget_chart',
                    iconStyle: { borderColor: '#38bdf8' },
                  },
                  dataZoom: {
                    title: { zoom: 'Zoom', back: 'Reset' },
                    iconStyle: { borderColor: '#38bdf8' },
                  },
                  restore: {
                    title: 'Restore',
                    iconStyle: { borderColor: '#38bdf8' },
                  },
                },
                right: 15,
                top: 8,
                iconStyle: { borderWidth: 1.5 },
                emphasis: { iconStyle: { borderColor: '#0ea5e9' } },
              },
              xAxis: {
                type: 'value',
                axisLabel: {
                  fontSize: getBigFont(12, 18, 9),
                  formatter: (v: number) => formatYAxis(v),
                  color: secondaryTextColor,
                },
                axisLine: { lineStyle: { color: axisLineColor } },
                splitLine: { lineStyle: { color: splitLineColor, type: 'dashed', width: 1 } },
              },
              yAxis: {
                type: 'category',
                data: x1,
                axisLabel: {
                  fontSize: getBigFont(12, 18, 9),
                  fontWeight: 'bold',
                  color: textColor,
                  interval: 'auto',
                  margin: 12,
                  rotate: 0,
                },
                axisLine: { lineStyle: { color: axisLineColor } },
              },
              dataZoom: [
                {
                  type: 'slider',
                  yAxisIndex: 0,
                  start: 0,
                  end: 100,
                },
              ],
              series: [
                {
                  type: 'bar',
                  data: y1,
                  barWidth: 8,
                  barCategoryGap: '25%',
                  itemStyle: {
                    color: (params: { dataIndex: number }) => colors1[params.dataIndex],
                    borderRadius: 6,
                    shadowBlur: 5,
                    shadowColor: '#ffd43b55',
                  },
                  label: {
                    show: true,
                    position: 'right',
                    fontSize: getBigFont(12, 16, 10),
                    fontWeight: 'bold',
                    color: textColor,
                    formatter: (params: { dataIndex: number }) => formatYAxis(y1[params.dataIndex]),
                    distance: 8,
                  },
                },
              ],
            };

            chartInstance1.setOption(option1);

            // Add click handler
            chartInstance1.on('click', (params: EChartsEventParams) => {
              if (params.componentType === 'xAxis' || params.componentType === 'series') {
                const assetNo = params.name || (typeof params.dataIndex === 'number' ? x1[params.dataIndex] : '');
                if (assetNo) {
                  const periodStr = isYearMode ? `${selectedYear} (Year)` : selectedMonth || '';
                  const lossValue = params.value ? String(params.value) : '0';
                  const detailsHtml = createRevenueLossTooltip(
                    String(assetNo),
                    periodStr,
                    revenueData,
                    'expected',
                    selectedMonth,
                    selectedYear,
                    theme
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
          }
        }

        // Initialize second chart (Operational Budget) - right side
        if (operationalChartRef.current) {
          if (chartInstance2Ref.current) {
            chartInstance2Ref.current.dispose();
          }
          const chartInstance2 = initChart(operationalChartRef.current);
          if (!chartInstance2) return;
          chartInstance2Ref.current = chartInstance2;

          if (operationalData.length === 0) {
            chartInstance2.setOption({
              title: {
                text: 'No data found for selected filters',
                left: 'center',
                top: 'middle',
                textStyle: { color: '#f87171', fontSize: 16 },
              },
            });
          } else {
            // Sort by loss value, then reverse (largest to smallest in absolute terms)
            const sortedData = [...operationalData].sort((a, b) => a.loss - b.loss).reverse();
            const x2 = sortedData.map((d) => d.asset);
            const y2 = sortedData.map((d) => Math.abs(d.loss));
            const colors2 = sortedData.map((d) => d.color);

            const option2 = {
              backgroundColor: chartBg,
              title: {
                show: true,
                text: `Revenue Loss/Gain wrt Operational Budget${suffix}`,
                left: 'center',
                top: 8,
                textStyle: {
                  fontSize: getBigFont(16, 30, 14),
                  fontWeight: 'bold',
                  fontFamily: 'Segoe UI, Arial, sans-serif',
                  color: theme === 'dark' ? '#38bdf8' : '#0072ce',
                },
              },
              tooltip: {
                show: false,
                trigger: 'none',
                confine: true,
                axisPointer: { type: 'shadow' },
                backgroundColor: tooltipBg,
                borderColor: tooltipBorder,
                textStyle: { color: textColor },
              },
              grid: { left: 120, right: 100, bottom: 50, top: 50 },
              toolbox: {
                show: true,
                feature: {
                  saveAsImage: {
                    title: 'Save',
                    name: 'revenue_operational_budget_chart',
                    iconStyle: { borderColor: theme === 'dark' ? '#38bdf8' : '#0072ce' },
                  },
                  dataZoom: {
                    title: { zoom: 'Zoom', back: 'Reset' },
                    iconStyle: { borderColor: theme === 'dark' ? '#38bdf8' : '#0072ce' },
                  },
                  restore: {
                    title: 'Restore',
                    iconStyle: { borderColor: theme === 'dark' ? '#38bdf8' : '#0072ce' },
                  },
                },
                right: 15,
                top: 8,
                iconStyle: { borderWidth: 1.5 },
                emphasis: { iconStyle: { borderColor: theme === 'dark' ? '#0ea5e9' : '#0056a3' } },
              },
              xAxis: {
                type: 'value',
                axisLabel: {
                  fontSize: getBigFont(12, 18, 9),
                  formatter: (v: number) => formatYAxis(v),
                  color: secondaryTextColor,
                },
                axisLine: { lineStyle: { color: axisLineColor } },
                splitLine: { lineStyle: { color: splitLineColor, type: 'dashed', width: 1 } },
              },
              yAxis: {
                type: 'category',
                data: x2,
                axisLabel: {
                  fontSize: getBigFont(12, 18, 9),
                  fontWeight: 'bold',
                  color: textColor,
                  interval: 'auto',
                  margin: 12,
                  rotate: 0,
                },
                axisLine: { lineStyle: { color: axisLineColor } },
              },
              dataZoom: [
                {
                  type: 'slider',
                  yAxisIndex: 0,
                  start: 0,
                  end: 100,
                },
              ],
              series: [
                {
                  type: 'bar',
                  data: y2,
                  barWidth: 8,
                  barCategoryGap: '25%',
                  itemStyle: {
                    color: (params: { dataIndex: number }) => colors2[params.dataIndex],
                    borderRadius: 6,
                    shadowBlur: 5,
                    shadowColor: '#ffd43b55',
                  },
                  label: {
                    show: true,
                    position: 'right',
                    fontSize: getBigFont(12, 16, 10),
                    fontWeight: 'bold',
                    color: textColor,
                    formatter: (params: { dataIndex: number }) => formatYAxis(y2[params.dataIndex]),
                    distance: 8,
                  },
                },
              ],
            };

            chartInstance2.setOption(option2);

            // Add click handler
            chartInstance2.on('click', (params: EChartsEventParams) => {
              if (params.componentType === 'xAxis' || params.componentType === 'series') {
                const assetNo = params.name || (typeof params.dataIndex === 'number' ? x2[params.dataIndex] : '');
                if (assetNo) {
                  const periodStr = isYearMode ? `${selectedYear} (Year)` : selectedMonth || '';
                  const lossValue = params.value ? String(params.value) : '0';
                  const detailsHtml = createRevenueLossTooltip(
                    String(assetNo),
                    periodStr,
                    revenueData,
                    'operational',
                    selectedMonth,
                    selectedYear,
                    theme
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
          }
        }

        // Handle window resize
        const handleResize = () => {
          chartInstance1Ref.current?.resize();
          chartInstance2Ref.current?.resize();
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
      chartInstance1Ref.current?.dispose();
      chartInstance1Ref.current = undefined;
      chartInstance2Ref.current?.dispose();
      chartInstance2Ref.current = undefined;
    };
  }, [expectedData, operationalData, selectedMonth, selectedYear, revenueData, onAssetClick, theme]);

  const handleCloseToolbox = () => {
    setToolboxOpen(false);
    setToolboxContent(null);
  };

  return (
    <div className="relative flex min-h-0 w-full flex-1 flex-row gap-2">
      {/* Custom Toolbox Modal */}
      {toolboxOpen && toolboxContent && (
        <div 
          className="absolute left-4 top-4 z-50 flex max-h-[calc(100%-2rem)] w-[800px] max-w-[calc(100%-2rem)] flex-col overflow-hidden rounded-xl border shadow-2xl backdrop-blur-md"
          style={{
            borderColor: theme === 'dark' ? 'rgba(59, 130, 246, 0.5)' : 'rgba(0, 114, 206, 0.5)',
            background: theme === 'dark'
              ? 'linear-gradient(to bottom right, rgba(15, 23, 42, 0.98), rgba(30, 41, 59, 0.98))'
              : 'linear-gradient(to bottom right, rgba(255, 255, 255, 0.98), rgba(248, 250, 252, 0.98))',
            boxShadow: theme === 'dark' ? '0 20px 25px -5px rgba(0, 0, 0, 0.7)' : '0 10px 15px -3px rgba(0, 0, 0, 0.2)',
          }}
        >
          {/* Header */}
          <div 
            className="flex shrink-0 items-center justify-between border-b px-4 py-2.5"
            style={{
              borderColor: theme === 'dark' ? 'rgba(51, 65, 85, 0.5)' : 'rgba(226, 232, 240, 0.8)',
              background: theme === 'dark'
                ? 'linear-gradient(to right, rgba(59, 130, 246, 0.3), rgba(30, 41, 59, 0.3))'
                : 'linear-gradient(to right, rgba(59, 130, 246, 0.1), rgba(248, 250, 252, 0.9))',
            }}
          >
            <div>
              <h3 
                className="text-sm font-semibold"
                style={{ color: theme === 'dark' ? '#60a5fa' : '#0072ce' }}
              >
                Revenue Loss Details
              </h3>
              <p 
                className="mt-0.5"
                style={{ color: theme === 'dark' ? '#94a3b8' : '#64748b', fontSize: `${bodyFontSize}px` }}
              >
                {toolboxContent.asset} - {toolboxContent.period}
              </p>
            </div>
            <button
              onClick={handleCloseToolbox}
              className="rounded-full p-1.5 transition-all"
              style={{ color: theme === 'dark' ? '#94a3b8' : '#64748b' }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = 'rgba(239, 68, 68, 0.2)';
                e.currentTarget.style.color = theme === 'dark' ? '#fca5a5' : '#dc2626';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = 'transparent';
                e.currentTarget.style.color = theme === 'dark' ? '#94a3b8' : '#64748b';
              }}
              aria-label="Close details"
            >
              <svg className="size-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          
          {/* Content */}
          <div className="min-h-0 flex-1 overflow-y-auto p-4">
            <div dangerouslySetInnerHTML={{ __html: toolboxContent.detailsHtml }} />
          </div>
          
          {/* Footer */}
          <div 
            className="shrink-0 border-t px-4 py-2"
            style={{
              fontSize: `${bodyFontSize}px`,
              borderColor: theme === 'dark' ? 'rgba(51, 65, 85, 0.5)' : 'rgba(226, 232, 240, 0.8)',
              backgroundColor: theme === 'dark' ? 'rgba(30, 41, 59, 0.5)' : 'rgba(248, 250, 252, 0.9)',
              color: theme === 'dark' ? '#94a3b8' : '#64748b',
            }}
          >
            Click on chart bars to view detailed revenue loss information
          </div>
        </div>
      )}

      <div
        ref={expectedChartRef}
        className="min-h-0 min-w-0 flex-1 rounded-xl border shadow-xl"
        style={{
          borderColor: chartContainerBorder,
          background: chartContainerBg,
          boxShadow: chartContainerShadow,
          minHeight: 'calc(100vh - 220px)',
          height: 'calc(100vh - 220px)',
        }}
      />
      <div
        ref={operationalChartRef}
        className="min-h-0 min-w-0 flex-1 rounded-xl border shadow-xl"
        style={{
          borderColor: chartContainerBorder,
          background: chartContainerBg,
          boxShadow: chartContainerShadow,
          minHeight: 'calc(100vh - 220px)',
          height: 'calc(100vh - 220px)',
        }}
      />
    </div>
  );
}
