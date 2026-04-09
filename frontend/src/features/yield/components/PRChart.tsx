import { useMemo } from 'react';
import Plot from 'react-plotly.js';
import type { YieldDataEntry } from '../types';

type PRChartProps = {
  data: YieldDataEntry[];
  loading?: boolean;
};

function toNumber(val: number | string | undefined | null): number {
  if (val === null || val === undefined || val === '') return 0;
  if (typeof val === 'number') return isNaN(val) ? 0 : val;
  const parsed = parseFloat(String(val));
  return isNaN(parsed) ? 0 : parsed;
}

export const PRChart = ({ data, loading = false }: PRChartProps) => {
  const chartData = useMemo(() => {
    if (loading || data.length === 0) {
      return null;
    }

    // Group by month and calculate averages
    const monthlyData: Record<string, { expected: number[]; actual: number[]; count: number }> = {};

    data.forEach((row) => {
      if (!row.month) return;
      if (!monthlyData[row.month]) {
        monthlyData[row.month] = { expected: [], actual: [], count: 0 };
      }
      const expected = toNumber(row.expected_pr);
      const actual = toNumber(row.actual_pr);
      if (expected > 0 || actual > 0) {
        monthlyData[row.month].expected.push(expected);
        monthlyData[row.month].actual.push(actual);
        monthlyData[row.month].count++;
      }
    });

    const months = Object.keys(monthlyData).sort();
    const expectedPR = months.map((month) => {
      const values = monthlyData[month].expected;
      return values.length > 0 ? values.reduce((a, b) => a + b, 0) / values.length : 0;
    });
    const actualPR = months.map((month) => {
      const values = monthlyData[month].actual;
      return values.length > 0 ? values.reduce((a, b) => a + b, 0) / values.length : 0;
    });

    const formatMonthLabel = (ym: string): string => {
      const [y, m] = ym.split('-');
      const date = new Date(Number(y), Number(m) - 1, 1);
      return date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
    };

    const trace1 = {
      x: months.map(formatMonthLabel),
      y: expectedPR,
      name: 'Expected PR',
      type: 'scatter' as const,
      mode: 'lines+markers' as const,
      line: { color: '#1976D2', width: 2 },
      marker: { color: '#1976D2', size: 8 },
    };

    const trace2 = {
      x: months.map(formatMonthLabel),
      y: actualPR,
      name: 'Actual PR',
      type: 'scatter' as const,
      mode: 'lines+markers' as const,
      line: { color: '#4CAF50', width: 2 },
      marker: { color: '#4CAF50', size: 8 },
    };

    const layout = {
      title: {
        text: 'Performance Ratio (PR) Comparison',
        font: { size: 16, color: '#fff' },
      },
      xaxis: {
        title: { text: 'Month', font: { size: 12, color: '#94a3b8' } },
        tickfont: { size: 10, color: '#94a3b8' },
      },
      yaxis: {
        title: { text: 'PR (%)', font: { size: 12, color: '#94a3b8' } },
        tickfont: { size: 10, color: '#94a3b8' },
      },
      plot_bgcolor: 'rgba(0,0,0,0)',
      paper_bgcolor: 'rgba(0,0,0,0)',
      font: { color: '#94a3b8' },
      legend: {
        x: 0.5,
        y: -0.15,
        xanchor: 'center' as const,
        orientation: 'h' as const,
        font: { size: 12, color: '#94a3b8' },
      },
      margin: { t: 50, b: 80, l: 60, r: 20 },
      height: 400,
    };

    return { data: [trace1, trace2], layout };
  }, [data, loading]);

  if (loading) {
    return (
      <div className="flex h-[400px] items-center justify-center rounded-3xl border border-slate-800/80 bg-slate-900/80">
        <div className="text-slate-400">Loading chart...</div>
      </div>
    );
  }

  if (!chartData) {
    return (
      <div className="flex h-[400px] items-center justify-center rounded-3xl border border-slate-800/80 bg-slate-900/80">
        <div className="text-slate-400">No data available</div>
      </div>
    );
  }

  return (
    <div className="rounded-3xl border border-slate-800/80 bg-slate-900/80 p-6 shadow-2xl shadow-slate-950/50">
      <div className="mb-4">
        <h2 className="text-lg font-semibold text-white">Performance Ratio</h2>
        <p className="mt-1 text-sm text-slate-400">Expected vs Actual PR over time</p>
      </div>
      <Plot
        data={chartData.data}
        layout={chartData.layout}
        config={{
          responsive: true,
          displayModeBar: true,
          modeBarButtonsToRemove: ['zoom2d', 'pan2d', 'select2d', 'lasso2d', 'zoomIn2d', 'zoomOut2d', 'autoScale2d', 'resetScale2d'],
          displaylogo: false,
          modeBarButtonsToAdd: [],
          toImageButtonOptions: {
            format: 'png',
            filename: 'pr_comparison_chart',
            height: 800,
            width: 1200,
            scale: 2
          },
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        } as any}
        style={{ width: '100%', height: '400px' }}
      />
    </div>
  );
};

