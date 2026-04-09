import { useEffect, useRef } from 'react';
import { useTheme } from '../../../contexts/ThemeContext';
import type { ChartDataset } from '../types';
import type { ChartInstance } from './chartTypes';

type DashboardChartsProps = {
  statusData: ChartDataset;
  priorityData: ChartDataset;
  categoryData: ChartDataset;
  loading?: boolean;
  totalTickets?: number;
  overdueTickets?: number;
};

const numberFormatter = new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 });

export const DashboardCharts = ({ statusData, priorityData, categoryData, loading = false, totalTickets, overdueTickets }: DashboardChartsProps) => {
  const { theme } = useTheme();
  const statusChartRef = useRef<ChartInstance | null>(null);
  const priorityChartRef = useRef<ChartInstance | null>(null);
  const categoryChartRef = useRef<ChartInstance | null>(null);
  const statusCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const priorityCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const categoryCanvasRef = useRef<HTMLCanvasElement | null>(null);
  
  const chartContainerBg = theme === 'dark'
    ? 'linear-gradient(to bottom right, rgba(15, 23, 42, 0.9), rgba(30, 41, 59, 0.6))'
    : 'linear-gradient(to bottom right, rgba(255, 255, 255, 0.95), rgba(248, 250, 252, 0.9))';
  const chartContainerBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(203, 213, 225, 0.8)';
  const chartContainerShadow = theme === 'dark' 
    ? '0 20px 25px -5px rgba(0, 0, 0, 0.4)' 
    : '0 10px 15px -3px rgba(0, 0, 0, 0.1)';
  const chartTitleText = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';
  const chartCenterText = theme === 'dark' ? '#60a5fa' : '#0072ce';
  const chartCenterSubtext = theme === 'dark' ? '#94a3b8' : '#64748b';
  const loadingText = theme === 'dark' ? '#94a3b8' : '#64748b';
  const loadingBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(203, 213, 225, 0.8)';
  const loadingBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.5)' : '#ffffff';

  // Load Chart.js and ChartDataLabels from CDN
  useEffect(() => {
    if (window.Chart && window.ChartDataLabels) {
      return;
    }

    const loadChartJS = () => {
      if (window.Chart) return Promise.resolve();

      return new Promise<void>((resolve, reject) => {
        const script = document.createElement('script');
        script.src = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js';
        script.onload = () => resolve();
        script.onerror = () => reject(new Error('Failed to load Chart.js'));
        document.head.appendChild(script);
      });
    };

    const loadDataLabels = () => {
      if (window.ChartDataLabels) return Promise.resolve();

      return new Promise<void>((resolve, reject) => {
        const script = document.createElement('script');
        script.src = 'https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.2.0/dist/chartjs-plugin-datalabels.min.js';
        script.onload = () => resolve();
        script.onerror = () => reject(new Error('Failed to load ChartDataLabels'));
        document.head.appendChild(script);
      });
    };

    Promise.all([loadChartJS(), loadDataLabels()]).catch((err) => {
      console.error('Failed to load chart libraries:', err);
    });
  }, []);

  // Initialize charts
  useEffect(() => {
    if (!window.Chart || !window.ChartDataLabels || loading) {
      return;
    }

    // Destroy existing charts
    if (statusChartRef.current) {
      statusChartRef.current.destroy();
      statusChartRef.current = null;
    }
    if (priorityChartRef.current) {
      priorityChartRef.current.destroy();
      priorityChartRef.current = null;
    }
    if (categoryChartRef.current) {
      categoryChartRef.current.destroy();
      categoryChartRef.current = null;
    }

    // Status donut chart (Total Tickets)
    if (statusCanvasRef.current && statusData.labels.length > 0) {
      const ctx = statusCanvasRef.current.getContext('2d');
      if (ctx) {
        const statusBgColors = ['#0d6efd', '#198754', '#ffc107', '#dc3545', '#6c757d', '#6610f2'];
        statusChartRef.current = new window.Chart(ctx, {
          type: 'doughnut',
          data: {
            labels: statusData.labels,
            datasets: [
              {
                data: statusData.values,
                backgroundColor: statusBgColors,
                borderWidth: 0,
              },
            ],
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '70%',
            plugins: {
              legend: { 
                position: 'bottom', 
                labels: { 
                  boxWidth: 12, 
                  font: { size: 10 },
                  color: theme === 'dark' ? '#e2e8f0' : '#1a1a1a',
                  generateLabels: function(chart: { data: { labels: string[]; datasets: Array<{ data: number[]; backgroundColor?: string[] }> } }) {
                    const labels = chart.data.labels || [];
                    const dataset = chart.data.datasets[0];
                    const bgColors = dataset.backgroundColor || statusBgColors;
                    return labels.map((label, index) => {
                      const value = dataset.data[index];
                      return {
                        text: `${label} (${Math.round(value)})`,
                        fillStyle: bgColors[index] || '#ccc',
                        strokeStyle: bgColors[index] || '#ccc',
                        fontColor: theme === 'dark' ? '#e2e8f0' : '#1a1a1a',
                        lineWidth: 0,
                        hidden: false,
                        index: index,
                      };
                    });
                  },
                } 
              },
              tooltip: {
                callbacks: {
                  label: function (context: { label: string; parsed: number }) {
                    return context.label + ': ' + Math.round(context.parsed);
                  },
                },
              },
              datalabels: {
                display: false,
              },
            },
          },
          plugins: [window.ChartDataLabels],
        } as never);
      }
    }

    // Priority bar chart
    if (priorityCanvasRef.current && priorityData.labels.length > 0) {
      const ctx = priorityCanvasRef.current.getContext('2d');
      if (ctx) {
        // Calculate max value and add padding for data labels
        const maxValue = Math.max(...priorityData.values.map((v) => Number(v) || 0));
        const yAxisMax = Math.ceil(maxValue * 1.15); // Add 15% padding for data labels
        
        // Create gradient backgrounds for glowing effect
        const priorityColors = ['#198754', '#fd7e14', '#ff5722', '#dc3545'];
        const gradientBackgrounds = priorityColors.map((color) => {
          const gradient = ctx.createLinearGradient(0, 0, 0, 400);
          gradient.addColorStop(0, color);
          gradient.addColorStop(1, color + 'CC');
          return gradient;
        });
        
        priorityChartRef.current = new window.Chart(ctx, {
          type: 'bar',
          data: {
            labels: priorityData.labels,
            datasets: [
              {
                data: priorityData.values,
                backgroundColor: gradientBackgrounds,
                borderColor: priorityColors,
                borderWidth: 2,
                borderRadius: {
                  topLeft: 6,
                  topRight: 6,
                  bottomLeft: 0,
                  bottomRight: 0,
                },
              },
            ],
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
              y: {
                beginAtZero: true,
                max: yAxisMax,
                ticks: {
                  stepSize: Math.max(1, Math.ceil(yAxisMax / 10)),
                  color: theme === 'dark' ? '#cbd5e1' : '#475569',
                  callback: function (value: unknown) {
                    return Math.round(Number(value));
                  },
                },
                grid: {
                  color: theme === 'dark' ? 'rgba(51, 65, 85, 0.5)' : 'rgba(226, 232, 240, 0.8)',
                },
              },
              x: {
                ticks: {
                  color: theme === 'dark' ? '#cbd5e1' : '#475569',
                },
                grid: {
                  color: theme === 'dark' ? 'rgba(51, 65, 85, 0.5)' : 'rgba(226, 232, 240, 0.8)',
                },
              },
            },
            plugins: {
              legend: { display: false },
              tooltip: {
                callbacks: {
                  label: function (context: { parsed: { y: number } }) {
                    return Math.round(context.parsed.y);
                  },
                },
              },
              datalabels: {
                anchor: 'end',
                align: 'top',
                color: theme === 'dark' ? '#e2e8f0' : '#1a1a1a',
                font: {
                  weight: 'bold',
                  size: 11,
                },
                formatter: function (value: number) {
                  return Math.round(value);
                },
                display: function (context: { dataset: { data: number[] }; dataIndex: number }) {
                  const value = context.dataset.data[context.dataIndex];
                  return value !== null && value !== undefined && Number(value) >= 0;
                },
              },
            },
          },
          plugins: [window.ChartDataLabels],
        } as never);
      }
    }

    // Category donut chart (Overdue Tickets)
    if (categoryCanvasRef.current && categoryData.labels.length > 0) {
      const ctx = categoryCanvasRef.current.getContext('2d');
      if (ctx) {
        const categoryBgColors = ['#0d6efd', '#6f42c1', '#20c997', '#ffc107', '#adb5bd'];
        categoryChartRef.current = new window.Chart(ctx, {
          type: 'doughnut',
          data: {
            labels: categoryData.labels,
            datasets: [
              {
                data: categoryData.values,
                backgroundColor: categoryBgColors,
                borderWidth: 0,
              },
            ],
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '70%',
            plugins: {
              legend: { 
                position: 'bottom', 
                labels: { 
                  boxWidth: 12, 
                  font: { size: 10 },
                  color: theme === 'dark' ? '#e2e8f0' : '#1a1a1a',
                  generateLabels: function(chart: { data: { labels: string[]; datasets: Array<{ data: number[]; backgroundColor?: string[] }> } }) {
                    const labels = chart.data.labels || [];
                    const dataset = chart.data.datasets[0];
                    const bgColors = dataset.backgroundColor || categoryBgColors;
                    return labels.map((label, index) => {
                      const value = dataset.data[index];
                      return {
                        text: `${label} (${Math.round(value)})`,
                        fillStyle: bgColors[index] || '#ccc',
                        strokeStyle: bgColors[index] || '#ccc',
                        fontColor: theme === 'dark' ? '#e2e8f0' : '#1a1a1a',
                        lineWidth: 0,
                        hidden: false,
                        index: index,
                      };
                    });
                  },
                } 
              },
              tooltip: {
                callbacks: {
                  label: function (context: { label: string; parsed: number }) {
                    return context.label + ': ' + Math.round(context.parsed);
                  },
                },
              },
              datalabels: {
                display: false,
              },
            },
          },
          plugins: [window.ChartDataLabels],
        } as never);
      }
    }

    return () => {
      if (statusChartRef.current) {
        statusChartRef.current.destroy();
      }
      if (priorityChartRef.current) {
        priorityChartRef.current.destroy();
      }
      if (categoryChartRef.current) {
        categoryChartRef.current.destroy();
      }
    };
  }, [statusData, priorityData, categoryData, loading, theme]);

  if (loading) {
    return (
      <section className="grid gap-4 lg:grid-cols-3">
        {[1, 2, 3].map((i) => (
          <div 
            key={i} 
            className="rounded-xl border p-4 shadow-sm"
            style={{
              borderColor: loadingBorder,
              backgroundColor: loadingBg,
            }}
          >
            <div 
              className="flex h-[220px] items-center justify-center"
              style={{ color: loadingText }}
            >
              Loading chart…
            </div>
          </div>
        ))}
      </section>
    );
  }

  return (
    <>
      {/* Add CSS for glowing effects on bar charts */}
      <style>{`
        canvas[data-chart="priority"] {
          filter: drop-shadow(0 2px 8px rgba(25, 135, 84, 0.4));
        }
        canvas[data-chart="priority"]:hover {
          filter: drop-shadow(0 4px 15px rgba(25, 135, 84, 0.6));
        }
      `}</style>
      <section className="grid gap-4 lg:grid-cols-3">
      {/* Total Tickets Donut Chart */}
      <div 
        className="rounded-xl border p-4 shadow-xl"
        style={{
          borderColor: chartContainerBorder,
          background: chartContainerBg,
          boxShadow: chartContainerShadow,
        }}
      >
        <div 
          className="mb-3 text-sm font-semibold uppercase tracking-wide"
          style={{ color: chartTitleText }}
        >
          Total Tickets
        </div>
        <div className="relative h-48">
          <canvas ref={statusCanvasRef} />
          {totalTickets !== undefined && (
            <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
              <div className="text-center">
                <div 
                  className="text-3xl font-bold"
                  style={{ color: chartCenterText }}
                >
                  {numberFormatter.format(totalTickets)}
                </div>
                <div 
                  className="mt-1 text-xs"
                  style={{ color: chartCenterSubtext }}
                >
                  Raised
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Priority Bar Chart */}
      <div 
        className="rounded-xl border p-4 shadow-xl"
        style={{
          borderColor: chartContainerBorder,
          background: chartContainerBg,
          boxShadow: chartContainerShadow,
        }}
      >
        <div 
          className="mb-3 text-sm font-semibold uppercase tracking-wide"
          style={{ color: chartTitleText }}
        >
          Tickets by Count (Priority)
        </div>
        <div className="h-48">
          <canvas ref={priorityCanvasRef} data-chart="priority" />
        </div>
      </div>

      {/* Overdue Tickets Category Donut Chart */}
      <div 
        className="rounded-xl border p-4 shadow-xl"
        style={{
          borderColor: chartContainerBorder,
          background: chartContainerBg,
          boxShadow: chartContainerShadow,
        }}
      >
        <div 
          className="mb-3 text-sm font-semibold uppercase tracking-wide"
          style={{ color: chartTitleText }}
        >
          Overdue Tickets (Category)
        </div>
        <div className="relative h-48">
          <canvas ref={categoryCanvasRef} />
          {overdueTickets !== undefined && (
            <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
              <div className="text-center">
                <div 
                  className="text-3xl font-bold"
                  style={{ color: theme === 'dark' ? '#fb7185' : '#e11d48' }}
                >
                  {numberFormatter.format(overdueTickets)}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
    </>
  );
};

