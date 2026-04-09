import { useCallback, useEffect, useRef, useState } from 'react';

import { fetchTicketAnalytics } from '../api';
import type { TicketAnalyticsParams, TicketAnalyticsResponse, TicketDashboardFilterParams } from '../types';
import type { ChartInstance } from './chartTypes';
import { useTheme } from '../../../contexts/ThemeContext';

type AnalyticsWidgetProps = {
  filters?: TicketDashboardFilterParams;
  loading?: boolean;
  expanded?: boolean;
  onExpandedChange?: (expanded: boolean) => void;
};

const VIEW_BY_OPTIONS = [
  { value: 'device_tickets', label: 'Device - Tickets' },
  { value: 'device_loss', label: 'Device - Loss Value' },
  { value: 'category_tickets', label: 'Category - Tickets' },
  { value: 'category_loss', label: 'Category - Loss Value' },
  { value: 'make_tickets', label: 'Make - Tickets' },
  { value: 'model_tickets', label: 'Model - Tickets' },
];

const TOP_N_OPTIONS = [
  { value: 5, label: 'Top 5' },
  { value: 10, label: 'Top 10' },
  { value: 20, label: 'Top 20' },
  { value: 50, label: 'Top 50' },
];

const TREND_DAYS_OPTIONS = [
  { value: 7, label: '7 days' },
  { value: 30, label: '30 days' },
];

export const AnalyticsWidget = ({
  filters,
  loading: parentLoading = false,
  expanded: expandedProp,
  onExpandedChange,
}: AnalyticsWidgetProps) => {
  const { theme } = useTheme();
  const [expanded, setExpanded] = useState<boolean>(expandedProp ?? false); // Collapsed by default
  const [viewBy, setViewBy] = useState<string>('device_tickets');
  const [topN, setTopN] = useState<number>(10);
  const [trendDays, setTrendDays] = useState<number>(7);
  const [page, setPage] = useState<number>(1);
  const [analyticsData, setAnalyticsData] = useState<TicketAnalyticsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const chartRef = useRef<HTMLCanvasElement | null>(null);
  const chartInstanceRef = useRef<ChartInstance | null>(null);
  const sparklineRefs = useRef<Map<number, HTMLCanvasElement>>(new Map());

  // Theme-aware colors
  const containerBg = theme === 'dark' 
    ? 'linear-gradient(to bottom right, rgba(30, 41, 59, 0.9), rgba(51, 65, 85, 0.6))'
    : '#ffffff';
  const containerBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(226, 232, 240, 1)';
  const headerBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(226, 232, 240, 1)';
  const textPrimary = theme === 'dark' ? '#f1f5f9' : '#1e293b';
  const textSecondary = theme === 'dark' ? '#94a3b8' : '#64748b';
  const textTertiary = theme === 'dark' ? '#64748b' : '#94a3b8';
  const inputBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.8)' : '#ffffff';
  const inputBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : 'rgba(203, 213, 225, 1)';
  const inputText = theme === 'dark' ? '#e2e8f0' : '#1e293b';
  const inputHoverBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.8)' : 'rgba(248, 250, 252, 1)';
  const tableHeaderBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.5)' : 'rgba(248, 250, 252, 1)';
  const tableHeaderText = theme === 'dark' ? '#cbd5e1' : '#475569';
  const tableRowBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.5)' : '#ffffff';
  const tableRowHoverBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.7)' : 'rgba(248, 250, 252, 1)';
  const tableRowText = theme === 'dark' ? '#e2e8f0' : '#1e293b';
  const tableDivider = theme === 'dark' ? 'rgba(51, 65, 85, 0.5)' : 'rgba(226, 232, 240, 1)';
  const errorBg = theme === 'dark' ? 'rgba(127, 29, 29, 0.3)' : 'rgba(254, 242, 242, 1)';
  const errorBorder = theme === 'dark' ? 'rgba(248, 113, 113, 0.5)' : 'rgba(254, 202, 202, 1)';
  const errorText = theme === 'dark' ? '#fca5a5' : '#991b1b';
  const chartTextColor = theme === 'dark' ? '#e2e8f0' : '#222222';
  const chartLineColor = theme === 'dark' ? '#60a5fa' : '#0d6efd';
  const chartLineBg = theme === 'dark' ? 'rgba(96, 165, 250, 0.1)' : 'rgba(13, 110, 253, 0.1)';

  // Keep local expanded state in sync with controlled prop
  useEffect(() => {
    if (typeof expandedProp === 'boolean') {
      setExpanded(expandedProp);
    }
  }, [expandedProp]);

  // Load Chart.js from CDN
  useEffect(() => {
    if (window.Chart) {
      return;
    }

    const script = document.createElement('script');
    script.src = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js';
    script.onload = () => {
      // Chart.js loaded
    };
    script.onerror = () => {
      console.error('Failed to load Chart.js');
    };
    document.head.appendChild(script);
  }, []);

  // Fetch analytics data
  const loadAnalytics = useCallback(async () => {
    if (parentLoading) {
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const params: TicketAnalyticsParams = {
        ...filters,
        viewBy: viewBy,
        perPage: topN,
        page: page,
        trendDays: trendDays,
      };

      const data = await fetchTicketAnalytics(params);
      setAnalyticsData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load analytics');
    } finally {
      setLoading(false);
    }
  }, [filters, viewBy, topN, trendDays, page, parentLoading]);

  useEffect(() => {
    if (expanded) {
      loadAnalytics();
    }
  }, [expanded, loadAnalytics]);

  // Update mini chart
  useEffect(() => {
    if (!window.Chart || !analyticsData || !chartRef.current || loading) {
      return;
    }

    if (chartInstanceRef.current) {
      chartInstanceRef.current.destroy();
      chartInstanceRef.current = null;
    }

    const ctx = chartRef.current.getContext('2d');
    if (ctx && analyticsData.labels.length > 0 && window.Chart) {
      const total = analyticsData.values.reduce((a, b) => a + Number(b || 0), 0) || 1;
      const max = Math.max(...analyticsData.values.map((v) => Number(v) || 0), 1);
      
      // Color scale: green -> orange -> red based on ratio
      const colorForRatio = (r: number) => {
        if (r >= 0.75) return '#dc3545'; // red
        if (r >= 0.45) return '#fd7e14'; // orange
        return '#198754'; // green
      };
      
      const bgColors = analyticsData.values.map((v) => colorForRatio((Number(v) || 0) / max));
      
      // Create gradient backgrounds for glowing effect
      const gradientBackgrounds = bgColors.map((color) => {
        const gradient = ctx.createLinearGradient(0, 0, 0, 400);
        gradient.addColorStop(0, color);
        gradient.addColorStop(1, color + 'CC');
        return gradient;
      });

      chartInstanceRef.current = new window.Chart(ctx, {
        type: 'bar',
        data: {
          labels: analyticsData.labels,
          datasets: [
            {
              data: analyticsData.values,
              backgroundColor: gradientBackgrounds,
              borderColor: bgColors,
              borderWidth: 2,
              borderRadius: {
                topLeft: 6,
                topRight: 6,
                bottomLeft: 0,
                bottomRight: 0,
              },
              barThickness: 18,
            },
          ],
        },
        options: {
          indexAxis: 'y',
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            x: { display: false },
            y: {
              ticks: { font: { size: 12 }, color: chartTextColor },
              grid: { display: false },
            },
          },
          plugins: {
            legend: { display: false },
            tooltip: {
              callbacks: {
                label: function (context: { parsed: { x: number } }) {
                  const value = context.parsed.x;
                  const pct = Math.round((value / total) * 100);
                  return `${value} (${pct}%)`;
                },
              },
            },
          },
        },
      } as never);
    }

    return () => {
      if (chartInstanceRef.current) {
        chartInstanceRef.current.destroy();
      }
    };
  }, [analyticsData, viewBy, loading, theme, chartTextColor]);

  // Render sparklines
  useEffect(() => {
    if (!window.Chart || !analyticsData || loading) {
      return;
    }

    const cleanup: (() => void)[] = [];

    analyticsData.items.forEach((item, index) => {
      const canvas = sparklineRefs.current.get(index);
      if (!canvas || !item.trend || item.trend.length === 0 || !window.Chart) {
        return;
      }

      const ctx = canvas.getContext('2d');
      if (!ctx) {
        return;
      }

      const chart = new window.Chart(ctx, {
        type: 'line',
        data: {
          labels: item.trend.map((_, i) => i + 1),
          datasets: [
            {
              data: item.trend,
              borderColor: chartLineColor,
              backgroundColor: chartLineBg,
              borderWidth: 2,
              pointRadius: 0,
              fill: true,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            x: { display: false },
            y: { display: false },
          },
          plugins: {
            legend: { display: false },
            tooltip: { enabled: false },
          },
        },
      } as never);

      cleanup.push(() => chart.destroy());
    });

    return () => {
      cleanup.forEach((fn) => fn());
    };
  }, [analyticsData, loading, theme, chartLineColor, chartLineBg]);

  const handleExportCSV = useCallback(() => {
    if (!analyticsData) {
      return;
    }

    const headers = ['Name', 'Value', 'Secondary', 'Trend'];
    const rows = analyticsData.items.map((item) => [
      item.label,
      item.value.toString(),
      item.secondary.toString(),
      item.trend.join(','),
    ]);

    const csv = [headers.join(','), ...rows.map((row) => row.join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `analytics_${viewBy}_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }, [analyticsData, viewBy]);

  const handleRefresh = useCallback(() => {
    loadAnalytics();
  }, [loadAnalytics]);

  const handleToggleExpanded = useCallback(() => {
    setExpanded((prev) => {
      const next = !prev;
      if (onExpandedChange) {
        onExpandedChange(next);
      }
      return next;
    });
  }, [onExpandedChange]);

  const pagination = analyticsData?.pagination;
  const totalPages = pagination?.totalPages ?? 0;
  const totalItems = pagination?.totalItems ?? 0;

  return (
    <section 
      className="rounded-xl border shadow-sm"
      style={{
        borderColor: containerBorder,
        background: containerBg,
      }}
    >
      <div 
        className="flex items-center justify-between border-b p-4"
        style={{ borderColor: headerBorder }}
      >
        <div className="flex items-center gap-2">
          <strong style={{ color: textPrimary }}>Analytics</strong>
          <small style={{ color: textSecondary }}>Switch metric & see details</small>
        </div>
        <div className="flex items-center gap-4">
          <select
            value={viewBy}
            onChange={(e) => {
              setViewBy(e.target.value);
              setPage(1);
            }}
            className="rounded border px-3 py-1 text-xs"
            style={{
              borderColor: inputBorder,
              backgroundColor: inputBg,
              color: inputText,
            }}
            disabled={loading || parentLoading}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = inputHoverBg;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = inputBg;
            }}
          >
            {VIEW_BY_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          <select
            value={topN}
            onChange={(e) => {
              setTopN(Number(e.target.value));
              setPage(1);
            }}
            className="rounded border px-3 py-1 pr-8 text-xs"
            style={{ 
              paddingRight: '2rem', 
              minWidth: '80px',
              borderColor: inputBorder,
              backgroundColor: inputBg,
              color: inputText,
            }}
            disabled={loading || parentLoading}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = inputHoverBg;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = inputBg;
            }}
          >
            {TOP_N_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          <select
            value={trendDays}
            onChange={(e) => {
              setTrendDays(Number(e.target.value));
              setPage(1);
            }}
            className="rounded border px-3 py-1 pr-8 text-xs"
            style={{ 
              paddingRight: '2rem', 
              minWidth: '90px',
              borderColor: inputBorder,
              backgroundColor: inputBg,
              color: inputText,
            }}
            disabled={loading || parentLoading}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = inputHoverBg;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = inputBg;
            }}
          >
            {TREND_DAYS_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={handleRefresh}
            disabled={loading || parentLoading}
            className="rounded border px-3 py-1 text-xs disabled:opacity-50"
            style={{
              borderColor: inputBorder,
              backgroundColor: inputBg,
              color: inputText,
            }}
            onMouseEnter={(e) => {
              if (!loading && !parentLoading) {
                e.currentTarget.style.backgroundColor = inputHoverBg;
              }
            }}
            onMouseLeave={(e) => {
              if (!loading && !parentLoading) {
                e.currentTarget.style.backgroundColor = inputBg;
              }
            }}
          >
            Refresh
          </button>
          <button
            type="button"
            onClick={handleExportCSV}
            disabled={!analyticsData || loading}
            className="rounded border px-3 py-1 text-xs disabled:opacity-50"
            style={{
              borderColor: inputBorder,
              backgroundColor: inputBg,
              color: inputText,
            }}
            onMouseEnter={(e) => {
              if (!loading && analyticsData) {
                e.currentTarget.style.backgroundColor = inputHoverBg;
              }
            }}
            onMouseLeave={(e) => {
              if (!loading && analyticsData) {
                e.currentTarget.style.backgroundColor = inputBg;
              }
            }}
            title="Export CSV"
          >
            📊 CSV
          </button>
          <div 
            className="ml-4 border-l pl-3"
            style={{ borderColor: inputBorder }}
          >
            <button
              type="button"
              onClick={handleToggleExpanded}
              className="rounded border px-2 py-1 text-xs"
              style={{
                borderColor: inputBorder,
                backgroundColor: inputBg,
                color: inputText,
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = inputHoverBg;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = inputBg;
              }}
            >
              {expanded ? '▼' : '▶'}
            </button>
          </div>
        </div>
      </div>

      {expanded && (
        <div className="p-4">
          {error ? (
            <div 
              className="rounded border p-3 text-sm"
              style={{
                borderColor: errorBorder,
                backgroundColor: errorBg,
                color: errorText,
              }}
            >
              {error}
            </div>
          ) : loading ? (
            <div className="p-4 text-center" style={{ color: textTertiary }}>Loading analytics...</div>
          ) : analyticsData && analyticsData.items.length > 0 ? (
            <div className="grid gap-4 lg:grid-cols-2">
              {/* Table */}
              <div className="overflow-auto">
                <table 
                  className="min-w-full divide-y text-sm"
                  style={{ borderColor: tableDivider }}
                >
                  <thead style={{ backgroundColor: tableHeaderBg }}>
                    <tr>
                      <th 
                        className="px-3 py-2 text-left font-medium" 
                        style={{ width: '38%', color: tableHeaderText }}
                      >
                        Name
                      </th>
                      <th 
                        className="px-3 py-2 text-right font-medium" 
                        style={{ width: '16%', color: tableHeaderText }}
                      >
                        Value
                      </th>
                      <th 
                        className="px-3 py-2 text-right text-xs font-medium" 
                        style={{ width: '16%', color: textSecondary }}
                      >
                        Secondary
                      </th>
                      <th 
                        className="px-3 py-2 text-left font-medium" 
                        style={{ width: '30%', color: tableHeaderText }}
                      >
                        Trend
                      </th>
                    </tr>
                  </thead>
                  <tbody 
                    className="divide-y"
                    style={{ 
                      borderColor: tableDivider,
                      backgroundColor: tableRowBg,
                    }}
                  >
                    {analyticsData.items.map((item, index) => (
                      <tr 
                        key={index}
                        style={{
                          borderColor: tableDivider,
                          backgroundColor: tableRowBg,
                          color: tableRowText,
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.backgroundColor = tableRowHoverBg;
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.backgroundColor = tableRowBg;
                        }}
                      >
                        <td className="px-3 py-2">
                          <div className="font-semibold" style={{ color: tableRowText }}>{item.label}</div>
                          {item.subLabel && <small style={{ color: textSecondary }}>{item.subLabel}</small>}
                        </td>
                        <td className="px-3 py-2 text-right">
                          <strong style={{ color: tableRowText }}>
                            {viewBy.includes('loss')
                              ? Number(item.value).toFixed(2)
                              : Math.round(Number(item.value)).toString()}
                          </strong>
                        </td>
                        <td className="px-3 py-2 text-right">
                          <small style={{ color: textSecondary }}>
                            {viewBy.includes('loss')
                              ? `${Math.round(Number(item.secondary))} tickets`
                              : Number(item.secondary).toFixed(2)}
                          </small>
                        </td>
                        <td className="px-3 py-2">
                          <div className="flex items-center gap-2">
                            <div style={{ width: '120px', height: '36px' }}>
                              <canvas
                                ref={(el) => {
                                  if (el) {
                                    sparklineRefs.current.set(index, el);
                                  }
                                }}
                                style={{ height: '36px' }}
                              />
                            </div>
                            <div className="text-xs" style={{ color: textSecondary }}>
                              <div className="font-semibold">{item.trend[item.trend.length - 1]}</div>
                              <div>last</div>
                            </div>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Chart */}
              <div>
                <style>{`
                  canvas[data-chart="analytics"] {
                    filter: drop-shadow(0 2px 8px rgba(0, 0, 0, 0.3));
                  }
                `}</style>
                <div className="mb-3" style={{ height: '320px' }}>
                  <canvas ref={chartRef} data-chart="analytics" />
                </div>
                {/* Pagination */}
                <div className="flex items-center justify-between">
                  <div className="text-xs" style={{ color: textSecondary }}>
                    Page {page} of {totalPages} ({totalItems} items)
                  </div>
                  <div className="flex gap-1">
                    <button
                      type="button"
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                      disabled={page <= 1 || loading}
                      className="rounded border px-2 py-1 text-xs disabled:opacity-50"
                      style={{
                        borderColor: inputBorder,
                        backgroundColor: inputBg,
                        color: inputText,
                      }}
                      onMouseEnter={(e) => {
                        if (page > 1 && !loading) {
                          e.currentTarget.style.backgroundColor = inputHoverBg;
                        }
                      }}
                      onMouseLeave={(e) => {
                        if (page > 1 && !loading) {
                          e.currentTarget.style.backgroundColor = inputBg;
                        }
                      }}
                    >
                      Prev
                    </button>
                    <button
                      type="button"
                      onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                      disabled={page >= totalPages || loading}
                      className="rounded border px-2 py-1 text-xs disabled:opacity-50"
                      style={{
                        borderColor: inputBorder,
                        backgroundColor: inputBg,
                        color: inputText,
                      }}
                      onMouseEnter={(e) => {
                        if (page < totalPages && !loading) {
                          e.currentTarget.style.backgroundColor = inputHoverBg;
                        }
                      }}
                      onMouseLeave={(e) => {
                        if (page < totalPages && !loading) {
                          e.currentTarget.style.backgroundColor = inputBg;
                        }
                      }}
                    >
                      Next
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="p-4 text-center" style={{ color: textTertiary }}>No data available</div>
          )}
        </div>
      )}
    </section>
  );
};

