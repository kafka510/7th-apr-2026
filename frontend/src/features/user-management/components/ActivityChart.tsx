 
import { useEffect, useRef } from 'react';
import Plot from 'react-plotly.js';
import type { ActivityDataPoint } from '../types';

interface ActivityChartProps {
  activityData: ActivityDataPoint[];
}

export function ActivityChart({ activityData }: ActivityChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Chart will be rendered by Plot component
  }, [activityData]);

  if (!activityData || activityData.length === 0) {
    return (
      <div className="mb-4 rounded bg-white p-4 shadow-sm">
        <h4 className="mb-3">User Activity (Last 24 Hours)</h4>
        <p className="text-muted mb-0">No activity data available</p>
      </div>
    );
  }

  const hours = activityData.map((point) => point.hour);
  const counts = activityData.map((point) => point.count);

  const data = [
    {
      x: hours,
      y: counts,
      type: 'scatter',
      mode: 'lines+markers',
      marker: { color: '#667eea', size: 8 },
      line: { color: '#667eea', width: 2 },
      fill: 'tozeroy',
      fillcolor: 'rgba(102, 126, 234, 0.1)',
    } as const,
  ];

  const layout = {
    title: '',
    xaxis: {
      title: 'Time (Hours)',
      showgrid: true,
      gridcolor: '#e0e0e0',
    },
    yaxis: {
      title: 'Activity Count',
      showgrid: true,
      gridcolor: '#e0e0e0',
    },
    margin: { l: 50, r: 20, t: 20, b: 50 },
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    hovermode: 'x unified' as const,
  };

  const config = {
    displayModeBar: true,
    modeBarButtonsToRemove: ['zoom2d', 'pan2d', 'select2d', 'lasso2d', 'zoomIn2d', 'zoomOut2d', 'autoScale2d', 'resetScale2d'],
    displaylogo: false,
    toImageButtonOptions: {
      format: 'png',
      filename: 'user_activity_chart',
      height: 600,
      width: 1000,
      scale: 2
    },
    responsive: true,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  } as any;

  return (
    <div className="mb-4 rounded bg-white p-4 shadow-sm">
      <h4 className="mb-3">User Activity (Last 24 Hours)</h4>
      <div ref={chartContainerRef} style={{ width: '100%', height: '300px' }}>
        <Plot data={data} layout={layout} config={config} style={{ width: '100%', height: '100%' }} />
      </div>
    </div>
  );
}

