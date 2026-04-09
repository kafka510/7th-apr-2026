import { useEffect, useRef, useState } from 'react';
import { useTheme } from '../../../contexts/ThemeContext';
import { getResponsiveFontSize, useResponsiveFontSize } from '../../../utils/fontScaling';
import type { PrGapDataPoint } from '../types';

interface PrGapChartsProps {
  data: PrGapDataPoint[];
  selectedMonth?: string | null;
  selectedYear?: string | null;
  onAssetClick?: (asset: string, month: string) => void;
  prData?: Array<{
    asset_no?: string;
    assetno?: string;
    asset?: string;
    month?: string;
    pr_gap?: number | string;
    pr_gap_observation?: string;
    pr_gap_action_need_to_taken?: string;
  }>;
  lossData?: Array<{
    asset_no?: string;
    asset?: string;
    month?: string;
    l?: string;
    breakdown_dc_capacity_kw?: number | string;
    breakdown_dc_capacity?: number | string;
    dc_capacity?: number | string;
    bd_description?: string;
    action_to_be_taken?: string;
    status_of_bd?: string;
    generation_loss_kwh?: number | string;
    'generation_loss_(kwh)'?: number | string;
  }>;
}

// Extend the existing EChartsInstance from MonthlyChart
interface EChartsChart extends EChartsInstance {
  on: (event: string, handler: (params: EChartsEventParams) => void) => void;
  getZr: () => {
    on: (event: string, handler: (params: EChartsZrEvent) => void) => void;
  };
  convertFromPixel: (coord: { seriesIndex: number }, point: [number, number]) => [number, number] | null;
  clear: () => void;
}

interface EChartsInstance {
  setOption: (option: unknown, notMerge?: boolean) => void;
  resize: () => void;
  dispose: () => void;
  getWidth: () => number;
}

interface EChartsEventParams {
  componentType?: string;
  name?: string;
  value?: unknown;
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

// Type guard to check if echarts is available and get chart instance
function initChart(dom: HTMLElement | null): EChartsChart | undefined {
  if (!window.echarts || !dom) return undefined;
  // Cast to EChartsChart since EChartsInstance from MonthlyChart doesn't have all methods
  // but the actual ECharts library does provide them
  return window.echarts.init(dom) as unknown as EChartsChart;
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

function isInSelectedMonth(rowMonth: string | null | undefined, selectedMonth: string | null | undefined, selectedYear: string | null | undefined): boolean {
  const monthStr = normalizeMonthValue(rowMonth);
  if (!monthStr) return false;

  if (selectedYear) {
    return monthStr.slice(0, 4) === String(selectedYear);
  } else if (selectedMonth) {
    return monthStr === selectedMonth;
  }

  return false;
}

function getBreakdownDetails(
  assetNo: string,
  month: string,
  lossData: Array<{
    asset_no?: string;
    asset?: string;
    month?: string;
    l?: string;
    breakdown_dc_capacity_kw?: number | string;
    breakdown_dc_capacity?: number | string;
    dc_capacity?: number | string;
    bd_description?: string;
    action_to_be_taken?: string;
    status_of_bd?: string;
    generation_loss_kwh?: number | string;
    'generation_loss_(kwh)'?: number | string;
  }>
): Array<Record<string, unknown>> {
  if (!lossData || lossData.length === 0) {
    return [];
  }

  // Convert month format if needed (e.g., "2025-01" to "Jan-25")
  let searchMonth = month;
  if (month && month.includes('-')) {
    const [year, monthNum] = month.split('-');
    if (year && monthNum) {
      const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
      const monthName = monthNames[parseInt(monthNum) - 1];
      searchMonth = `${monthName}-${year.slice(-2)}`;
    }
  }

  const results = lossData.filter((row) => {
    const rowAsset = (row.asset_no || row.asset || 'Unknown') as string;
    const rowMonth = (row.month || row.l || 'Unknown') as string;

    // Match asset number (case insensitive and handle partial matches)
    const assetMatch =
      String(rowAsset).toLowerCase().includes(String(assetNo).toLowerCase()) ||
      String(assetNo).toLowerCase().includes(String(rowAsset).toLowerCase());

    // Match month - handle different formats
    let monthMatch = false;
    const rowMonthStr = String(rowMonth).toLowerCase();
    const searchMonthStr = String(searchMonth).toLowerCase();

    // Direct match
    if (rowMonthStr === searchMonthStr) {
      monthMatch = true;
    }
    // Handle "25-Jan" vs "Jan-25" format
    else if (rowMonthStr.includes('-') && searchMonthStr.includes('-')) {
      const rowParts = rowMonthStr.split('-');
      const searchParts = searchMonthStr.split('-');

      // Check if month names match (e.g., "jan" in both)
      if (rowParts.length >= 2 && searchParts.length >= 2) {
        const rowMonthName = rowParts[1]; // "jan" from "25-jan"
        const searchMonthName = searchParts[0]; // "jan" from "jan-25"

        if (rowMonthName === searchMonthName) {
          monthMatch = true;
        }
      }
    }

    // Additional check for "25-Jan" format specifically
    if (!monthMatch && rowMonthStr.includes('-')) {
      const rowParts = rowMonthStr.split('-');
      if (rowParts.length >= 2) {
        const rowMonthName = rowParts[1]; // "jan" from "25-jan"
        const searchMonthName = searchMonthStr.split('-')[0]; // "jan" from "jan-25"

        if (rowMonthName === searchMonthName) {
          monthMatch = true;
        }
      }
    }

    return assetMatch && monthMatch;
  });

  // Filter to only include those with generation loss data
  return results.filter((breakdown) => {
    const hasGenerationLoss =
      (breakdown['generation_loss_kwh'] !== null && breakdown['generation_loss_kwh'] !== undefined) ||
      (breakdown['generation_loss_(kwh)'] !== null && breakdown['generation_loss_(kwh)'] !== undefined);
    return hasGenerationLoss;
  });
}


export function PrGapCharts({ data, selectedMonth, selectedYear, onAssetClick, prData = [], lossData = [] }: PrGapChartsProps) {
  const { theme } = useTheme();
  
  // Responsive font sizes
  const bodyFontSize = useResponsiveFontSize(10, 14, 9);
  const observationFontSize = useResponsiveFontSize(11, 15, 10);
  
  const prGapChartRef = useRef<HTMLDivElement>(null);
  const prGapCapacityChartRef = useRef<HTMLDivElement>(null);
  const chartInstance1Ref = useRef<EChartsChart | undefined>(undefined);
  const chartInstance2Ref = useRef<EChartsChart | undefined>(undefined);
  const [toolboxOpen, setToolboxOpen] = useState(false);
  
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
  const [toolboxContent, setToolboxContent] = useState<{
    asset: string;
    month: string;
    prGap: string;
    observations: string[];
    actions: string[];
    breakdowns: Array<Record<string, unknown>>;
  } | null>(null);

  useEffect(() => {
    let mounted = true;

    loadECharts()
      .then(() => {
        if (!mounted || !window.echarts) return;

        // Initialize first chart (PR Gap * DC Capacity) - left side
        if (prGapCapacityChartRef.current) {
          if (chartInstance2Ref.current) {
            chartInstance2Ref.current.dispose();
          }
          const chartInstance2 = initChart(prGapCapacityChartRef.current);
          if (!chartInstance2) return;
          chartInstance2Ref.current = chartInstance2;

          if (data.length === 0) {
            chartInstance2.setOption({
              title: {
                text: 'No data found for selected filters',
                left: 'center',
                top: 'middle',
                textStyle: { color: '#f87171', fontSize: 16 },
              },
            });
          } else {
            // Sort by gapDc ascending, then reverse
            const sortedData = [...data].sort((a, b) => a.gapDc - b.gapDc).reverse();
            const x2 = sortedData.map((d) => d.asset);
            const y2Sorted = sortedData.map((d) => Math.abs(d.gapDc));
            const colors2 = sortedData.map((d) => d.color);

            let suffix = '';
            if (selectedMonth) {
              const [year, month] = selectedMonth.split('-');
              const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
              const monthName = monthNames[parseInt(month) - 1];
              suffix = ` (${monthName} ${year})`;
            } else if (selectedYear) {
              suffix = ` (${selectedYear} - Yearly Average)`;
            }

            const option2 = {
              title: {
                text: `PR Gap * DC Capacity${suffix}`,
                left: 'center',
                top: 8,
                textStyle: {
                  fontSize: getBigFont(16, 30, 14),
                  fontWeight: 'bold',
                  fontFamily: 'Segoe UI, Arial, sans-serif',
                  color: '#38bdf8',
                },
              },
              grid: { left: 180, right: 100, bottom: 50, top: 50 },
              xAxis: {
                type: 'value',
                axisLabel: { fontSize: getBigFont(12, 18, 9), color: secondaryTextColor },
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
                  data: y2Sorted,
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
                    formatter: (params: { dataIndex: number }) => y2Sorted[params.dataIndex].toFixed(2),
                    distance: 8,
                  },
                },
              ],
              toolbox: {
                feature: {
                  saveAsImage: { 
                    title: 'Save', 
                    name: 'pr_gap_details_chart',
                    iconStyle: { borderColor: '#38bdf8' } 
                  },
                  dataZoom: { 
                    title: { zoom: 'Zoom', back: 'Reset' }, 
                    iconStyle: { borderColor: '#38bdf8' } 
                  },
                  restore: { 
                    title: 'Restore', 
                    iconStyle: { borderColor: '#38bdf8' } 
                  },
                },
                right: 15,
                top: 8,
                iconStyle: { borderWidth: 1.5 },
                emphasis: { iconStyle: { borderColor: '#0ea5e9' } },
              },
            };

            chartInstance2.setOption(option2);

            // Add click handler
            chartInstance2.on('click', (params: EChartsEventParams) => {
              if (onAssetClick && params.name) {
                const month = selectedMonth || selectedYear || 'Current Period';
                onAssetClick(String(params.name), month);
              }
            });
          }
        }

        // Initialize second chart (PR Gap %) - right side
        if (prGapChartRef.current) {
          if (chartInstance1Ref.current) {
            chartInstance1Ref.current.dispose();
          }
          const chartInstance = initChart(prGapChartRef.current);
          if (!chartInstance) return;
          chartInstance1Ref.current = chartInstance;

          if (data.length === 0) {
            chartInstance.setOption({
              title: {
                text: 'No data found for selected filters',
                left: 'center',
                top: 'middle',
                textStyle: { color: '#f87171', fontSize: 16 },
              },
            });
          } else {
            const x = data.map((d) => d.asset);
            const y = data.map((d) => Math.abs(d.gap * 100));
            const colors = data.map((d) => d.color);
            const labels = data.map((d) => d.displayGap);

            let suffix = '';
            if (selectedMonth) {
              const [year, month] = selectedMonth.split('-');
              const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
              const monthName = monthNames[parseInt(month) - 1];
              suffix = ` (${monthName} ${year})`;
            } else if (selectedYear) {
              suffix = ` (${selectedYear} - Yearly Average)`;
            }

            const tooltipFontSize = getBigFont(14, 22, 10);

            const option = {
              backgroundColor: chartBg,
              title: {
                text: `PR Gap (%)${suffix}`,
                left: 'center',
                top: 8,
                textStyle: {
                  fontSize: getBigFont(16, 36, 14),
                  fontWeight: 'bold',
                  fontFamily: 'Segoe UI, Arial, sans-serif',
                  color: theme === 'dark' ? '#38bdf8' : '#0072ce',
                  textShadow: theme === 'dark' ? '0 3px 12px rgba(0,0,0,0.5)' : '0 2px 8px rgba(0,0,0,0.1)',
                },
              },
              tooltip: {
                show: false, // Disable tooltip on hover - only open on click
                trigger: 'none',
                confine: true,
                axisPointer: { type: 'shadow' },
                backgroundColor: tooltipBg,
                borderColor: tooltipBorder,
                textStyle: { color: textColor },
                extraCssText: `
                  z-index: 9999 !important;
                  max-width: 500px !important;
                  min-width: 200px;
                  background: ${theme === 'dark' ? '#0f172a' : '#ffffff'} !important;
                  color: ${theme === 'dark' ? '#e2e8f0' : '#1a1a1a'} !important;
                  font-size: ${tooltipFontSize}px !important;
                  font-family: 'Segoe UI', Arial, sans-serif !important;
                  font-weight: 600 !important;
                  box-shadow: 0 8px 32px #0f2027aa !important;
                  border-radius: 16px !important;
                  padding: 0 !important;
                  line-height: 1.7 !important;
                  white-space: pre-line !important;
                  word-break: break-word !important;
                  overflow-wrap: break-word !important;
                `,
                formatter: (params: unknown) => {
                  try {
                    // Theme-aware colors - declared once at the top
                    const tooltipTextColor = theme === 'dark' ? '#38bdf8' : '#0072ce';
                    const tooltipHeaderBg = theme === 'dark' ? '#38bdf8' : '#0072ce';
                    const tableRowBg1 = theme === 'dark' ? 'rgba(30, 41, 59, 0.5)' : '#f8f9fa';
                    const tableRowBg2 = theme === 'dark' ? 'rgba(51, 65, 85, 0.5)' : '#ffffff';
                    const tableBorder = theme === 'dark' ? 'rgba(71, 85, 105, 0.7)' : '#ddd';
                    
                    // ECharts tooltip formatter - handle both single object and array
                    let param: { name?: string; value?: number | string; dataIndex?: number; seriesName?: string; data?: unknown };
                    if (Array.isArray(params)) {
                      param = params[0] as typeof param;
                    } else {
                      param = params as typeof param;
                    }
                    
                    let assetName = String(param?.name || '').trim();
                    let value: number = 0;
                    
                    // Handle different value types
                    if (typeof param?.value === 'number') {
                      value = param.value;
                    } else if (typeof param?.value === 'string') {
                      value = parseFloat(param.value) || 0;
                    } else if (Array.isArray(param?.data) && param.data.length > 0) {
                      const dataVal = param.data[0];
                      if (typeof dataVal === 'number') {
                        value = dataVal;
                      } else if (typeof dataVal === 'string') {
                        value = parseFloat(dataVal) || 0;
                      }
                    }
                    
                    // If no assetName, try to get from dataIndex
                    if (!assetName && typeof param?.dataIndex === 'number' && x.length > param.dataIndex) {
                      assetName = String(x[param.dataIndex]).trim();
                    }
                    
                    // Final fallback - if still no assetName, return basic tooltip
                    if (!assetName) {
                      console.warn('Tooltip: No asset name found', param);
                      return `<div style="padding: 9px 11px;">
                        <div style="font-weight: bold; margin-bottom: 4px; color: ${tooltipTextColor};">Value: ${value.toFixed(2)}%</div>
                      </div>`;
                    }
                    
                    const matches = prData.filter((r) => {
                      const asset = r.asset_no || r.assetno || r.asset || 'Unknown';
                      return String(asset).trim() === assetName && isInSelectedMonth(r.month, selectedMonth || null, selectedYear || null);
                    });
                    
                    const obsList = [...new Set(matches.map((m) => m.pr_gap_observation).filter(Boolean))];
                    const actionList = [...new Set(matches.map((m) => m.pr_gap_action_need_to_taken).filter(Boolean))];
                    
                    // Get breakdown details
                    const currentMonth = selectedMonth || selectedYear || '';
                    const breakdowns = getBreakdownDetails(assetName, currentMonth, lossData);
                    
                    let breakdownTable = '';
                    if (breakdowns.length > 0) {
                      breakdownTable = `
                        <div style="margin-top: 12px; border-top: 2px solid ${tooltipHeaderBg}; padding-top: 10px;">
                          <div style="font-weight: bold; margin-bottom: 8px; color: ${tooltipTextColor};">Breakdown Details (${breakdowns.length} instance${breakdowns.length > 1 ? 's' : ''})</div>
                          <div style="overflow-x: auto; max-height: 300px; overflow-y: auto;">
                            <table style="width: 100%; border-collapse: collapse; font-size: 12px;">
                              <thead>
                                <tr style="background: ${tooltipHeaderBg}; color: white;">
                                  <th style="padding: 6px; text-align: left; border: 1px solid #ddd; width: 5%;">#</th>
                                  <th style="padding: 6px; text-align: left; border: 1px solid #ddd; width: 12%;">DC Capacity</th>
                                  <th style="padding: 6px; text-align: left; border: 1px solid #ddd; width: 30%;">BD Description</th>
                                  <th style="padding: 6px; text-align: left; border: 1px solid #ddd; width: 25%;">Action</th>
                                  <th style="padding: 6px; text-align: left; border: 1px solid #ddd; width: 8%;">Status</th>
                                  <th style="padding: 6px; text-align: left; border: 1px solid #ddd; width: 10%;">Gen Loss (kWh)</th>
                                </tr>
                              </thead>
                              <tbody>
                                ${breakdowns.map((breakdown, index) => {
                                  const dcCapacity = (breakdown['breakdown_dc_capacity_kw'] || breakdown['breakdown_dc_capacity'] || breakdown['dc_capacity'] || 'N/A') as string | number;
                                  const bdDescription = String(breakdown['bd_description'] || 'N/A');
                                  const actionToBeTaken = String(breakdown['action_to_be_taken'] || 'N/A');
                                  const bdStatus = String(breakdown['status_of_bd'] || 'N/A');
                                  let generationLoss: string | number = 'N/A';
                                  if (breakdown['generation_loss_kwh'] !== null && breakdown['generation_loss_kwh'] !== undefined) {
                                    const val = breakdown['generation_loss_kwh'];
                                    generationLoss = typeof val === 'number' ? Math.round(val) : String(val);
                                  } else if (breakdown['generation_loss_(kwh)'] !== null && breakdown['generation_loss_(kwh)'] !== undefined) {
                                    const val = breakdown['generation_loss_(kwh)'];
                                    generationLoss = typeof val === 'number' ? Math.round(val) : String(val);
                                  }
                                  
                                  let formattedDcCapacity = dcCapacity;
                                  if (typeof dcCapacity === 'number' && !isNaN(dcCapacity)) {
                                    formattedDcCapacity = `${dcCapacity.toFixed(2)} kW`;
                                  }
                                  
                                  const shortDescription = bdDescription.length > 50 ? bdDescription.substring(0, 50) + '...' : bdDescription;
                                  const shortAction = actionToBeTaken.length > 40 ? actionToBeTaken.substring(0, 40) + '...' : actionToBeTaken;
                                  
                                  const statusColor = bdStatus.toLowerCase() === 'closed' ? '#28a745' : 
                                                     bdStatus.toLowerCase() === 'open' ? '#dc3545' : '#ffc107';
                                  
                                  return `
                                    <tr style="background: ${index % 2 === 0 ? tableRowBg1 : tableRowBg2};">
                                      <td style="padding: 6px; border: 1px solid ${tableBorder}; font-weight: bold; text-align: center;">${index + 1}</td>
                                      <td style="padding: 6px; border: 1px solid ${tableBorder}; text-align: center;">${formattedDcCapacity}</td>
                                      <td style="padding: 6px; border: 1px solid ${tableBorder};" title="${bdDescription}">${shortDescription}</td>
                                      <td style="padding: 6px; border: 1px solid ${tableBorder};" title="${actionToBeTaken}">${shortAction}</td>
                                      <td style="padding: 6px; border: 1px solid ${tableBorder}; color: ${statusColor}; font-weight: bold; text-align: center;">${bdStatus}</td>
                                      <td style="padding: 6px; border: 1px solid ${tableBorder}; font-weight: bold; text-align: center;">${generationLoss}</td>
                                    </tr>
                                  `;
                                }).join('')}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      `;
                    }
                    
                    return `<div style="padding: 9px 11px;">
                      <div style="font-weight: bold; margin-bottom: 4px; color: ${tooltipTextColor};">Asset: ${assetName}</div>
                      <div style="margin-bottom: 4px;">Avg PR Gap: ${value.toFixed(2)}%</div>
                      ${obsList.length > 0 ? `<div style="margin-bottom: 4px;"><b>Observation:</b> ${obsList.join('<br>')}</div>` : ''}
                      ${actionList.length > 0 ? `<div style="margin-bottom: 4px;"><b>Action Needed:</b> ${actionList.join('<br>')}</div>` : ''}
                      ${breakdownTable}
                    </div>`;
                  } catch (error) {
                    console.error('Tooltip formatter error:', error, params);
                    return '';
                  }
                },
              },
              grid: { left: 180, right: 100, bottom: 50, top: 50 },
              xAxis: {
                type: 'value',
                axisLabel: { fontSize: getBigFont(12, 18, 9), color: secondaryTextColor },
                axisLine: { lineStyle: { color: axisLineColor } },
                splitLine: { lineStyle: { color: splitLineColor, type: 'dashed', width: 1 } },
              },
              yAxis: {
                type: 'category',
                data: x,
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
                  // Use data with names for better tooltip support
                  data: y.map((val, idx) => ({
                    value: val,
                    name: x[idx],
                  })),
                  barWidth: 8,
                  barCategoryGap: '25%',
                  itemStyle: {
                    color: (params: { dataIndex: number }) => {
                      return colors[params.dataIndex] || '#38bdf8';
                    },
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
                    formatter: (params: { dataIndex: number }) => labels[params.dataIndex],
                    distance: 8,
                  },
                },
              ],
              toolbox: {
                feature: {
                  saveAsImage: { 
                    title: 'Save', 
                    name: 'pr_gap_chart',
                    iconStyle: { borderColor: theme === 'dark' ? '#38bdf8' : '#0072ce' } 
                  },
                },
                right: 15,
                top: 8,
                itemSize: 10,
                iconStyle: { borderWidth: 1 },
                emphasis: { iconStyle: { borderColor: theme === 'dark' ? '#0ea5e9' : '#0056a3' } },
              },
            };

            chartInstance.setOption(option);

            // Add click handler
            chartInstance.on('click', (params: EChartsEventParams) => {
              if (params.componentType === 'series' && params.name) {
                const assetName = String(params.name);
                const month = selectedMonth || selectedYear || 'Current Period';
                
                // Find matching data for this asset
                const matches = prData.filter((r) => {
                  const asset = r.asset_no || r.assetno || r.asset || 'Unknown';
                  return String(asset).trim() === assetName.trim();
                });
                
                const obsList = [...new Set(matches.map((m) => m.pr_gap_observation).filter(Boolean))] as string[];
                const actionList = [...new Set(matches.map((m) => m.pr_gap_action_need_to_taken).filter(Boolean))] as string[];
                
                // Get breakdown details with full information
                const breakdowns = getBreakdownDetails(assetName, month, lossData);
                
                setToolboxContent({ 
                  asset: assetName, 
                  month,
                  prGap: String(params.value),
                  observations: obsList,
                  actions: actionList,
                  breakdowns
                });
                setToolboxOpen(true);
                
                if (onAssetClick) {
                  onAssetClick(assetName, month);
                }
              }
            });
          }
        }

        // Initialize second chart (PR Gap * DC Capacity)
        if (prGapCapacityChartRef.current) {
          if (chartInstance2Ref.current) {
            chartInstance2Ref.current.dispose();
          }
          const chartInstance2 = initChart(prGapCapacityChartRef.current);
          if (!chartInstance2) return;
          chartInstance2Ref.current = chartInstance2;

          if (data.length === 0) {
            chartInstance2.setOption({
              title: {
                text: 'No data found for selected filters',
                left: 'center',
                top: 'middle',
                textStyle: { color: '#f87171', fontSize: 16 },
              },
            });
          } else {
            // Sort by gapDc ascending, then reverse
            const sortedData = [...data].sort((a, b) => a.gapDc - b.gapDc).reverse();
            const x2 = sortedData.map((d) => d.asset);
            const y2Sorted = sortedData.map((d) => Math.abs(d.gapDc));
            const colors2 = sortedData.map((d) => d.color);

            let suffix = '';
            if (selectedMonth) {
              const [year, month] = selectedMonth.split('-');
              const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
              const monthName = monthNames[parseInt(month) - 1];
              suffix = ` (${monthName} ${year})`;
            } else if (selectedYear) {
              suffix = ` (${selectedYear} - Yearly Average)`;
            }

            const option2 = {
              title: {
                text: `PR Gap * DC Capacity${suffix}`,
                left: 'center',
                top: 8,
                textStyle: {
                  fontSize: getBigFont(16, 30, 14),
                  fontWeight: 'bold',
                  fontFamily: 'Segoe UI, Arial, sans-serif',
                  color: '#38bdf8',
                },
              },
              grid: { left: 180, right: 100, bottom: 50, top: 50 },
              xAxis: {
                type: 'value',
                axisLabel: { fontSize: getBigFont(12, 18, 9), color: secondaryTextColor },
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
                  data: y2Sorted,
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
                    formatter: (params: { dataIndex: number }) => y2Sorted[params.dataIndex].toFixed(2),
                    distance: 8,
                  },
                },
              ],
              toolbox: {
                feature: {
                  saveAsImage: { 
                    title: 'Save', 
                    name: 'pr_gap_details_chart',
                    iconStyle: { borderColor: '#38bdf8' } 
                  },
                  dataZoom: { 
                    title: { zoom: 'Zoom', back: 'Reset' }, 
                    iconStyle: { borderColor: '#38bdf8' } 
                  },
                  restore: { 
                    title: 'Restore', 
                    iconStyle: { borderColor: '#38bdf8' } 
                  },
                },
                right: 15,
                top: 8,
                iconStyle: { borderWidth: 1.5 },
                emphasis: { iconStyle: { borderColor: '#0ea5e9' } },
              },
            };

            chartInstance2.setOption(option2);

            // Add click handler
            chartInstance2.on('click', (params: EChartsEventParams) => {
              if (onAssetClick && params.name) {
                const month = selectedMonth || selectedYear || 'Current Period';
                onAssetClick(String(params.name), month);
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
  }, [data, selectedMonth, selectedYear, onAssetClick, prData, lossData, theme]);

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
                Asset Details
              </h3>
              <p 
                className="mt-0.5"
                style={{ color: theme === 'dark' ? '#94a3b8' : '#64748b', fontSize: `${bodyFontSize}px` }}
              >
                {toolboxContent.asset} - {toolboxContent.month}
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
              aria-label="Close toolbox"
            >
              <svg className="size-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          
          {/* Content */}
          <div className="min-h-0 flex-1 overflow-y-auto p-4">
            {/* Basic Info */}
            <div 
              className="mb-4 rounded-lg border p-3"
              style={{
                backgroundColor: theme === 'dark' ? 'rgba(30, 41, 59, 0.5)' : 'rgba(241, 245, 249, 0.8)',
                borderColor: theme === 'dark' ? 'rgba(51, 65, 85, 0.5)' : 'rgba(203, 213, 225, 0.7)',
              }}
            >
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div>
                  <span style={{ color: theme === 'dark' ? '#94a3b8' : '#64748b' }}>PR Gap:</span>
                  <span 
                    className="ml-2 font-semibold"
                    style={{ color: theme === 'dark' ? '#60a5fa' : '#0072ce' }}
                  >
                    {parseFloat(String(toolboxContent.prGap)).toFixed(2)}%
                  </span>
                </div>
              </div>
            </div>

            {/* Observations */}
            {toolboxContent.observations.length > 0 && (
              <div className="mb-4">
                <h4 
                  className="mb-2 text-xs font-semibold"
                  style={{ color: theme === 'dark' ? '#60a5fa' : '#0072ce' }}
                >
                  Observations
                </h4>
                <div className="space-y-1">
                  {toolboxContent.observations.map((obs, idx) => (
                    <div 
                      key={idx} 
                      className="rounded border-l-2 px-2 py-1.5"
                      style={{
                        fontSize: `${observationFontSize}px`,
                        color: theme === 'dark' ? '#cbd5e1' : '#475569',
                        backgroundColor: theme === 'dark' ? 'rgba(30, 41, 59, 0.3)' : 'rgba(248, 250, 252, 0.6)',
                        borderColor: 'rgba(250, 204, 21, 0.5)',
                      }}
                    >
                      {obs}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Actions */}
            {toolboxContent.actions.length > 0 && (
              <div className="mb-4">
                <h4 
                  className="mb-2 text-xs font-semibold"
                  style={{ color: theme === 'dark' ? '#60a5fa' : '#0072ce' }}
                >
                  Actions Needed
                </h4>
                <div className="space-y-1">
                  {toolboxContent.actions.map((action, idx) => (
                    <div 
                      key={idx} 
                      className="rounded border-l-2 px-2 py-1.5"
                      style={{
                        fontSize: `${observationFontSize}px`,
                        color: theme === 'dark' ? '#cbd5e1' : '#475569',
                        backgroundColor: theme === 'dark' ? 'rgba(30, 41, 59, 0.3)' : 'rgba(248, 250, 252, 0.6)',
                        borderColor: 'rgba(249, 115, 22, 0.5)',
                      }}
                    >
                      {action}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Breakdown Details Table */}
            {toolboxContent.breakdowns.length > 0 && (
              <div>
                <h4 
                  className="mb-2 text-xs font-semibold"
                  style={{ color: theme === 'dark' ? '#60a5fa' : '#0072ce' }}
                >
                  Breakdown Details ({toolboxContent.breakdowns.length} instances)
                </h4>
                <div className="overflow-x-auto">
                  <table className="w-full border-collapse" style={{ fontSize: `${bodyFontSize}px` }}>
                    <thead>
                      <tr 
                        style={{
                          backgroundColor: theme === 'dark' ? 'rgba(59, 130, 246, 0.3)' : 'rgba(59, 130, 246, 0.1)',
                          color: theme === 'dark' ? '#93c5fd' : '#1e40af',
                        }}
                      >
                        <th 
                          className="border px-2 py-1.5 text-left"
                          style={{ borderColor: theme === 'dark' ? 'rgba(51, 65, 85, 0.5)' : 'rgba(203, 213, 225, 0.7)' }}
                        >
                          #
                        </th>
                        <th 
                          className="border px-2 py-1.5 text-left"
                          style={{ borderColor: theme === 'dark' ? 'rgba(51, 65, 85, 0.5)' : 'rgba(203, 213, 225, 0.7)' }}
                        >
                          DC Capacity
                        </th>
                        <th 
                          className="border px-2 py-1.5 text-left"
                          style={{ borderColor: theme === 'dark' ? 'rgba(51, 65, 85, 0.5)' : 'rgba(203, 213, 225, 0.7)' }}
                        >
                          Description
                        </th>
                        <th 
                          className="border px-2 py-1.5 text-left"
                          style={{ borderColor: theme === 'dark' ? 'rgba(51, 65, 85, 0.5)' : 'rgba(203, 213, 225, 0.7)' }}
                        >
                          Action
                        </th>
                        <th 
                          className="border px-2 py-1.5 text-left"
                          style={{ borderColor: theme === 'dark' ? 'rgba(51, 65, 85, 0.5)' : 'rgba(203, 213, 225, 0.7)' }}
                        >
                          Status
                        </th>
                        <th 
                          className="border px-2 py-1.5 text-right"
                          style={{ borderColor: theme === 'dark' ? 'rgba(51, 65, 85, 0.5)' : 'rgba(203, 213, 225, 0.7)' }}
                        >
                          Gen Loss (kWh)
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {toolboxContent.breakdowns.map((breakdown, idx) => {
                        const dcCapacity = breakdown['breakdown_dc_capacity_kw'] || 
                                         breakdown['breakdown_dc_capacity'] || 
                                         breakdown['dc_capacity'] || 'N/A';
                        const bdDescription = String(breakdown['bd_description'] || 'N/A');
                        const actionToBeTaken = String(breakdown['action_to_be_taken'] || 'N/A');
                        const bdStatus = String(breakdown['status_of_bd'] || 'N/A');
                        
                        let generationLoss: string | number = 'N/A';
                        if (breakdown['generation_loss_kwh'] !== null && breakdown['generation_loss_kwh'] !== undefined) {
                          const val = breakdown['generation_loss_kwh'];
                          generationLoss = typeof val === 'number' ? Math.round(val).toLocaleString() : String(val);
                        } else if (breakdown['generation_loss_(kwh)'] !== null && breakdown['generation_loss_(kwh)'] !== undefined) {
                          const val = breakdown['generation_loss_(kwh)'];
                          generationLoss = typeof val === 'number' ? Math.round(val).toLocaleString() : String(val);
                        }

                        const statusColor = bdStatus.toLowerCase() === 'closed' 
                          ? (theme === 'dark' ? '#4ade80' : '#16a34a')
                          : bdStatus.toLowerCase() === 'open' 
                          ? (theme === 'dark' ? '#f87171' : '#dc2626')
                          : (theme === 'dark' ? '#fbbf24' : '#ca8a04');

                        return (
                          <tr 
                            key={idx}
                            style={{
                              backgroundColor: idx % 2 === 0
                                ? (theme === 'dark' ? 'rgba(30, 41, 59, 0.2)' : 'rgba(248, 250, 252, 0.5)')
                                : (theme === 'dark' ? 'rgba(30, 41, 59, 0.4)' : 'rgba(241, 245, 249, 0.8)'),
                            }}
                          >
                            <td 
                              className="border px-2 py-1.5 text-center font-semibold"
                              style={{
                                borderColor: theme === 'dark' ? 'rgba(51, 65, 85, 0.5)' : 'rgba(203, 213, 225, 0.7)',
                                color: theme === 'dark' ? '#cbd5e1' : '#475569',
                              }}
                            >
                              {idx + 1}
                            </td>
                            <td 
                              className="border px-2 py-1.5"
                              style={{
                                borderColor: theme === 'dark' ? 'rgba(51, 65, 85, 0.5)' : 'rgba(203, 213, 225, 0.7)',
                                color: theme === 'dark' ? '#e2e8f0' : '#1a1a1a',
                              }}
                            >
                              {typeof dcCapacity === 'number' ? `${dcCapacity.toFixed(2)} kW` : String(dcCapacity)}
                            </td>
                            <td 
                              className="max-w-[200px] border px-2 py-1.5"
                              style={{
                                borderColor: theme === 'dark' ? 'rgba(51, 65, 85, 0.5)' : 'rgba(203, 213, 225, 0.7)',
                                color: theme === 'dark' ? '#e2e8f0' : '#1a1a1a',
                              }}
                            >
                              <div className="truncate" title={bdDescription}>
                                {bdDescription.length > 50 ? bdDescription.substring(0, 50) + '...' : bdDescription}
                              </div>
                            </td>
                            <td 
                              className="max-w-[180px] border px-2 py-1.5"
                              style={{
                                borderColor: theme === 'dark' ? 'rgba(51, 65, 85, 0.5)' : 'rgba(203, 213, 225, 0.7)',
                                color: theme === 'dark' ? '#e2e8f0' : '#1a1a1a',
                              }}
                            >
                              <div className="truncate" title={actionToBeTaken}>
                                {actionToBeTaken.length > 40 ? actionToBeTaken.substring(0, 40) + '...' : actionToBeTaken}
                              </div>
                            </td>
                            <td 
                              className="border px-2 py-1.5 font-semibold"
                              style={{
                                borderColor: theme === 'dark' ? 'rgba(51, 65, 85, 0.5)' : 'rgba(203, 213, 225, 0.7)',
                                color: statusColor,
                              }}
                            >
                              {bdStatus}
                            </td>
                            <td 
                              className="border px-2 py-1.5 text-right font-semibold"
                              style={{
                                borderColor: theme === 'dark' ? 'rgba(51, 65, 85, 0.5)' : 'rgba(203, 213, 225, 0.7)',
                                color: theme === 'dark' ? '#e2e8f0' : '#1a1a1a',
                              }}
                            >
                              {generationLoss}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* No Breakdown Data Message */}
            {toolboxContent.breakdowns.length === 0 && (
              <div className="rounded-lg border border-slate-700/30 bg-slate-800/20 py-4 text-center text-xs text-slate-400">
                No breakdown details available for this asset
              </div>
            )}
          </div>
          
          {/* Footer */}
          <div className="shrink-0 border-t border-slate-700/50 bg-slate-900/50 px-4 py-2 text-slate-400" style={{ fontSize: `${bodyFontSize}px` }}>
            Click on chart bars to view detailed breakdown information
          </div>
        </div>
      )}

      <div
        ref={prGapCapacityChartRef}
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
        ref={prGapChartRef}
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

