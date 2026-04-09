/**
 * Chart Display Component using Chart.js
 */
 
import { useEffect, useRef, useState } from 'react';
import type { TimeSeriesData, ZoomMode, PanMode } from '../types';

interface ChartDisplayProps {
  data: TimeSeriesData[];
  timezone: string | null;
  recordCount?: number;
  dataQuality?: {
    valid_records: number;
    total_records: number;
    filter_percentage: number;
  };
}

// Colors for different series
const CHART_COLORS = [
  '#667eea', '#764ba2', '#f093fb', '#4facfe',
  '#43e97b', '#fa709a', '#fee140', '#30cfd0',
  '#a8edea', '#fed6e3', '#ff9a9e', '#fecfef',
  '#ffecd2', '#fcb69f', '#ff8a80', '#ffb74d'
];

// Chart.js types (simplified)
interface ChartInstance {
  destroy: () => void;
  update: (mode?: string) => void;
  resetZoom: () => void;
  options: {
    plugins: {
      zoom: {
        zoom: { mode: string };
        pan: { mode: string };
      };
    };
  };
}

interface ChartConstructor {
  new (ctx: CanvasRenderingContext2D, config: unknown): ChartInstance;
}

type WindowWithChart = Window & {
  Chart?: ChartConstructor;
};

export function ChartDisplay({ data, timezone, recordCount, dataQuality }: ChartDisplayProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const chartInstanceRef = useRef<ChartInstance | null>(null);
  const [zoomMode, setZoomMode] = useState<ZoomMode>('xy');
  const [panMode, setPanMode] = useState<PanMode>('xy');

  useEffect(() => {
    if (!canvasRef.current || !data || data.length === 0) {
      return;
    }

    // Dynamically load Chart.js and plugins
    const loadChartJS = async () => {
      try {
        const win = window as WindowWithChart;
        
        // Check if Chart.js is already loaded
        if (typeof window !== 'undefined' && win.Chart) {
          renderChart();
          return;
        }

        // Load scripts sequentially to ensure proper initialization order
        // 1. Load Chart.js first
        await loadScript('https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.js');
        
        // Verify Chart.js is loaded and wait for it to be fully available
        let retries = 0;
        while (retries < 10) {
          const Chart = win.Chart as ChartConstructor & { registerables?: unknown };
          if (Chart && Chart.registerables) {
            break;
          }
          await new Promise(resolve => setTimeout(resolve, 50));
          retries++;
        }
        
        if (!win.Chart) {
          throw new Error('Chart.js failed to load');
        }
        
        // 2. Load Hammer.js (required for zoom plugin)
        await loadScript('https://cdn.jsdelivr.net/npm/hammerjs@2.0.8/hammer.min.js');
        
        // 3. Load date adapter (must be after Chart.js is fully initialized)
        await loadScript('https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns@3.0.0/dist/chartjs-adapter-date-fns.bundle.min.js');
        
        // Wait for adapter to register
        await new Promise(resolve => setTimeout(resolve, 100));
        
        // 4. Load zoom plugin (must be after Chart.js and Hammer.js)
        await loadScript('https://cdn.jsdelivr.net/npm/chartjs-plugin-zoom@2.0.1/dist/chartjs-plugin-zoom.min.js');

        // Final wait to ensure all plugins are registered
        await new Promise(resolve => setTimeout(resolve, 100));

        renderChart();
      } catch (error) {
        console.error('Failed to load Chart.js:', error);
      }
    };

    const loadScript = (src: string): Promise<void> => {
      return new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = src;
        script.onload = () => resolve();
        script.onerror = () => reject(new Error(`Failed to load ${src}`));
        document.head.appendChild(script);
      });
    };

    const renderChart = () => {
      try {
        const win = window as WindowWithChart;
        const Chart = win.Chart;
        if (!Chart) {
          console.error('Chart.js not available');
          return;
        }

      // Destroy existing chart
      if (chartInstanceRef.current) {
        chartInstanceRef.current.destroy();
      }

      // Convert timezone-aware timestamps to Date objects
      const convertToDate = (timestamp: string): Date => {
        // Remove timezone info and treat as local time
        const localTimestamp = timestamp.replace(/[+-]\d{2}:\d{2}$/, '');
        return new Date(localTimestamp);
      };

      // Group metrics by units for multiple Y-axes
      const metricsByUnit: Record<string, Array<{ label: string; data: Array<{ x: Date; y: number }>; color: string; units: string }>> = {};

      data.forEach((series, index) => {
        // Skip series with no data points
        if (!series.data_points || series.data_points.length === 0) {
          return;
        }

        const unit = series.units || 'no-unit';
        if (!metricsByUnit[unit]) {
          metricsByUnit[unit] = [];
        }

        const color = CHART_COLORS[index % CHART_COLORS.length];
        
        // Filter out invalid data points
        const validDataPoints = series.data_points
          .map((dp) => {
            try {
              const date = convertToDate(dp.timestamp);
              const value = parseFloat(String(dp.value));
              if (isNaN(value) || !isFinite(value)) {
                return null;
              }
              return { x: date, y: value };
            } catch {
              return null;
            }
          })
          .filter((dp): dp is { x: Date; y: number } => dp !== null);

        if (validDataPoints.length === 0) {
          return;
        }

        const deviceLabel = (series.device_name && series.device_name.trim()) ? series.device_name.trim() : series.device_id;
        metricsByUnit[unit].push({
          label: `${deviceLabel} - ${series.metric}`,
          data: validDataPoints,
          color,
          units: unit,
        });
      });
      
      // Check if we have any data to render
      const totalDataPoints = Object.values(metricsByUnit).reduce((sum, series) => sum + series.reduce((s, ds) => s + ds.data.length, 0), 0);
      
      if (totalDataPoints === 0) {
        console.error('No valid data points to render after processing');
        return;
      }

      // Create datasets with Y-axis assignments
      const datasets: Array<{
        label: string;
        data: Array<{ x: Date; y: number }>;
        borderColor: string;
        backgroundColor: string;
        borderWidth: number;
        tension: number;
        pointRadius: number;
        pointHoverRadius: number;
        pointHitRadius: number;
        yAxisID: string;
      }> = [];
      const unitKeys = Object.keys(metricsByUnit);

      unitKeys.forEach((unit, unitIndex) => {
        metricsByUnit[unit].forEach((dataset) => {
          datasets.push({
            label: dataset.label,
            data: dataset.data,
            borderColor: dataset.color,
            backgroundColor: dataset.color + '20',
            borderWidth: 1.5,
            tension: 0.4,
            pointRadius: 1.5,
            pointHoverRadius: 4,
            pointHitRadius: 10,
            yAxisID: `y${unitIndex}`,
          });
        });
      });

      // Create chart
      if (!canvasRef.current) {
        return;
      }
      const ctx = canvasRef.current.getContext('2d');
      if (!ctx) {
        return;
      }

      const chartInstance = new Chart(ctx, {
        type: 'line',
        data: { datasets },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          interaction: {
            mode: 'index',
            intersect: false,
          },
          plugins: {
            legend: {
              position: 'bottom',
              labels: {
                padding: 15,
                font: {
                  size: 13,
                  weight: 'bold',
                },
                color: '#1e293b',
              },
            },
            tooltip: {
              backgroundColor: 'rgba(0,0,0,0.85)',
              padding: 12,
              titleFont: {
                size: 14,
                weight: 'bold',
              },
              bodyFont: {
                size: 13,
                weight: '500',
              },
              titleColor: '#ffffff',
              bodyColor: '#ffffff',
              callbacks: {
                title: (context: Array<{ parsed: { x: number } }>) => {
                  return new Date(context[0].parsed.x).toLocaleString();
                },
              },
            },
            zoom: {
              pan: {
                enabled: true,
                mode: panMode,
                modifierKey: 'ctrl',
              },
              zoom: {
                wheel: {
                  enabled: true,
                  speed: 0.1,
                },
                pinch: {
                  enabled: true,
                },
                mode: zoomMode,
              },
              limits: {
                x: { min: 'original', max: 'original' },
                y: { min: 'original', max: 'original' },
              },
            },
          },
          scales: {
            x: {
              type: 'time',
              time: {
                unit: 'hour',
                displayFormats: {
                  hour: 'MMM dd HH:mm',
                },
              },
              title: {
                display: true,
                text: `Time (${timezone || 'UTC'})`,
                font: {
                  size: 14,
                  weight: 'bold',
                },
                color: '#1e293b',
              },
              ticks: {
                font: {
                  size: 12,
                  weight: '600',
                },
                color: '#334155',
              },
              grid: {
                color: 'rgba(0,0,0,0.05)',
              },
            },
            // Create multiple Y-axes for different units
            y: {
              type: 'linear',
              display: true,
              position: 'left',
              title: {
                display: true,
                text: unitKeys[0] || 'Value',
                font: {
                  size: 14,
                  weight: 'bold',
                },
                color: '#1e293b',
              },
              grid: {
                color: 'rgba(0,0,0,0.05)',
              },
              ticks: {
                font: {
                  size: 12,
                  weight: '600',
                },
                color: '#334155',
                callback: (value: number) => value.toFixed(2),
              },
              beginAtZero: true,
              suggestedMin: 0,
            },
            // Add additional Y-axes for other units
            ...unitKeys.slice(1).reduce((axes: Record<string, unknown>, unit, index) => {
              axes[`y${index + 1}`] = {
                type: 'linear',
                display: true,
                position: 'right',
                title: {
                  display: true,
                  text: unit,
                  font: {
                    size: 14,
                    weight: 'bold',
                  },
                  color: '#1e293b',
                },
                grid: {
                  drawOnChartArea: false,
                },
                ticks: {
                  font: {
                    size: 12,
                    weight: '600',
                  },
                  color: '#334155',
                  callback: (value: number) => value.toFixed(2),
                },
                beginAtZero: true,
                suggestedMin: 0,
              };
              return axes;
            }, {}),
          },
        },
      }) as unknown as ChartInstance;

        chartInstanceRef.current = chartInstance;

        // Set fixed height
        if (canvasRef.current) {
          canvasRef.current.style.height = '500px';
        }
      } catch (error) {
        console.error('Error rendering chart:', error);
      }
    };

    loadChartJS();

    // Cleanup
    return () => {
      if (chartInstanceRef.current) {
        chartInstanceRef.current.destroy();
        chartInstanceRef.current = null;
      }
    };
  }, [data, timezone, zoomMode, panMode]);

  const updateZoomMode = (mode: ZoomMode) => {
    setZoomMode(mode);
    if (chartInstanceRef.current) {
      chartInstanceRef.current.options.plugins.zoom.zoom.mode = mode;
      chartInstanceRef.current.update('none');
    }
  };

  const updatePanMode = (mode: PanMode) => {
    setPanMode(mode);
    if (chartInstanceRef.current) {
      chartInstanceRef.current.options.plugins.zoom.pan.mode = mode;
      chartInstanceRef.current.update('none');
    }
  };

  const resetZoom = () => {
    if (chartInstanceRef.current) {
      chartInstanceRef.current.resetZoom();
    }
  };

  if (!data || data.length === 0) {
    return null;
  }

  return (
    <div className="rounded-lg bg-white p-6 shadow-md">
      <div className="mb-4 flex items-center justify-between border-b-2 border-slate-200 pb-4">
        <h3 className="text-xl font-semibold text-slate-800">Time-Series Visualization</h3>
        <div className="flex items-center gap-4 text-sm text-slate-600">
          {timezone && (
            <span className="rounded-full bg-blue-100 px-3 py-1 font-semibold text-blue-700">
              Timezone: {timezone}
            </span>
          )}
          {recordCount !== undefined && <span>{recordCount} data points</span>}
          {dataQuality && dataQuality.filter_percentage > 0 && (
            <span
              className={`rounded-full px-3 py-1 text-xs font-semibold ${
                dataQuality.filter_percentage > 10
                  ? 'bg-yellow-100 text-yellow-700'
                  : 'bg-blue-100 text-blue-700'
              }`}
            >
              {dataQuality.filter_percentage.toFixed(1)}% filtered
            </span>
          )}
        </div>
      </div>

      {/* Chart Controls */}
      <div className="mb-4 flex flex-wrap items-center justify-between gap-4 text-xs text-slate-600">
        <div>
          <strong>Chart Controls:</strong> Scroll wheel to zoom | Hold Ctrl + Drag to pan
        </div>
        <div className="flex items-center gap-2">
          {/* Zoom Controls */}
          <div className="flex rounded border border-slate-300">
            <button
              type="button"
              onClick={() => updateZoomMode('x')}
              className={`px-3 py-1 text-xs transition-colors ${
                zoomMode === 'x' ? 'bg-blue-500 text-white' : 'bg-white text-slate-700 hover:bg-slate-50'
              }`}
              title="Zoom X-axis (Time)"
            >
              Zoom Time
            </button>
            <button
              type="button"
              onClick={() => updateZoomMode('y')}
              className={`px-3 py-1 text-xs transition-colors ${
                zoomMode === 'y' ? 'bg-blue-500 text-white' : 'bg-white text-slate-700 hover:bg-slate-50'
              }`}
              title="Zoom Y-axis (Values)"
            >
              Zoom Values
            </button>
            <button
              type="button"
              onClick={() => updateZoomMode('xy')}
              className={`px-3 py-1 text-xs transition-colors ${
                zoomMode === 'xy' ? 'bg-blue-500 text-white' : 'bg-white text-slate-700 hover:bg-slate-50'
              }`}
              title="Zoom Both Axes"
            >
              Zoom Both
            </button>
          </div>

          {/* Pan Controls */}
          <div className="flex rounded border border-slate-300">
            <button
              type="button"
              onClick={() => updatePanMode('x')}
              className={`px-3 py-1 text-xs transition-colors ${
                panMode === 'x' ? 'bg-teal-500 text-white' : 'bg-white text-slate-700 hover:bg-slate-50'
              }`}
              title="Pan X-axis (Time)"
            >
              Pan Time
            </button>
            <button
              type="button"
              onClick={() => updatePanMode('y')}
              className={`px-3 py-1 text-xs transition-colors ${
                panMode === 'y' ? 'bg-teal-500 text-white' : 'bg-white text-slate-700 hover:bg-slate-50'
              }`}
              title="Pan Y-axis (Values)"
            >
              Pan Values
            </button>
            <button
              type="button"
              onClick={() => updatePanMode('xy')}
              className={`px-3 py-1 text-xs transition-colors ${
                panMode === 'xy' ? 'bg-teal-500 text-white' : 'bg-white text-slate-700 hover:bg-slate-50'
              }`}
              title="Pan Both Axes"
            >
              Pan Both
            </button>
          </div>

          {/* Reset Zoom */}
          <button
            type="button"
            onClick={resetZoom}
            className="rounded border border-slate-300 bg-white px-3 py-1 text-xs text-slate-700 transition-colors hover:bg-slate-50"
          >
            Reset Zoom
          </button>
        </div>
      </div>

      {/* Chart Canvas */}
      <div className="relative">
        <canvas ref={canvasRef} style={{ height: '500px' }}></canvas>
      </div>
    </div>
  );
}

