import { useState, useMemo } from 'react';
import Plot from 'react-plotly.js';
import { YieldFilters } from './components/YieldFilters';
import { useYieldData } from './hooks/useYieldData';
import { formatNumber } from './utils/waterfall';
import type { YieldFilters as YieldFiltersType } from './types';

const CATEGORY_TITLES: Record<string, string> = {
  ic_approved_budget: 'IC Approved Budget',
  expected_budget: 'Expected Budget',
  weather_loss_or_gain: 'Weather Loss or Gain',
  grid_curtailment: 'Grid Curtailment',
  grid_outage: 'Grid Outage',
  operation_budget: 'Operation Budget',
  breakdown_loss: 'Breakdown Loss',
  scheduled_outage_loss: 'Scheduled Outage Loss',
  unclassified_loss: 'Unclassified Loss or Gain',
  actual_generation: 'Actual Generation',
};

function toNum(val: number | string): number {
  if (typeof val === 'number') return isNaN(val) ? 0 : val;
  if (typeof val === 'string') {
    const num = parseFloat(val);
    return isNaN(num) ? 0 : num;
  }
  return 0;
}

export function YieldDrilldown() {
  // Get category from DOM data attribute or URL path
  const category = useMemo(() => {
    if (typeof document === 'undefined') return null;
    
    const root = document.getElementById('react-root');
    const categoryFromData = root?.dataset.category;
    if (categoryFromData) {
      return categoryFromData;
    }

    // Extract from URL path: /yield-drilldown/{category}/
    const pathParts = window.location.pathname.split('/');
    const drilldownIndex = pathParts.indexOf('yield-drilldown');
    if (drilldownIndex >= 0 && pathParts[drilldownIndex + 1]) {
      const urlCategory = pathParts[drilldownIndex + 1];
      return urlCategory;
    }

    return null;
  }, []);

  // Initialize filters from URL params
  const [filters, setFilters] = useState<YieldFiltersType>(() => {
    const defaultFilters: YieldFiltersType = {
      countries: [],
      portfolios: [],
      assets: [],
      month: null,
      year: null,
      range: null,
    };

    if (typeof window === 'undefined') return defaultFilters;
    
    const urlParams = new URLSearchParams(window.location.search);
    const initialFilters: YieldFiltersType = { ...defaultFilters };
    const countries = urlParams.get('countries');
    const portfolios = urlParams.get('portfolios');
    const assets = urlParams.get('assets');
    const month = urlParams.get('month');
    const year = urlParams.get('year');

    if (countries) initialFilters.countries = countries.split(',');
    if (portfolios) initialFilters.portfolios = portfolios.split(',');
    if (assets) initialFilters.assets = assets.split(',');
    if (month) initialFilters.month = month;
    if (year) initialFilters.year = year;

    return initialFilters;
  });

  const { data, filterOptions, loading, error } = useYieldData(filters);

  const handleFiltersChange = (newFilters: YieldFiltersType) => {
    setFilters(newFilters);
  };

  const handleReset = () => {
    setFilters({
      countries: [],
      portfolios: [],
      assets: [],
      month: null,
      year: null,
      range: null,
    });
  };

  const handleBack = () => {
    // If in iframe, use parent window navigation or postMessage
    if (window.parent && window.parent !== window) {
      try {
        window.parent.postMessage({
          type: 'NAVIGATE_TO_YIELD_REPORT',
          url: '/yield-report/',
          preserveHeader: true
        }, '*');
        // Fallback: navigate parent window
        setTimeout(() => {
          window.location.href = '/yield-report/';
        }, 100);
      } catch {
        window.location.href = '/yield-report/';
      }
    } else {
      window.location.href = '/yield-report/';
    }
  };

  // Group data by country for the selected category
  const countryData = useMemo(() => {
    if (!category || !data.length) {
      return { countries: [], values: [] };
    }

    const grouped: Record<string, number> = {};
    data.forEach((row) => {
      const country = String(row.country || '');
      if (!country) return;

      // Get value for the selected category
      const categoryKey = category as keyof typeof row;
      let value = row[categoryKey];

      if (value === undefined || value === null || value === '') {
        value = 0;
      }

      const numValue = toNum(value);
      grouped[country] = (grouped[country] || 0) + numValue;
    });

    const countries = Object.keys(grouped).sort();
    const values = countries.map((country) => grouped[country]);

    return { countries, values };
  }, [category, data]);

  const chartTitle = category
    ? CATEGORY_TITLES[category] || category.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())
    : 'Drill-down Analysis';

  if (!category) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 text-slate-100">
        <main className="mx-auto flex max-w-[2400px] flex-col gap-2 px-6 pb-10 pt-4">
          <div className="rounded-lg border border-rose-300 bg-rose-50 p-6 text-sm text-rose-900 shadow-md">
            Invalid drill-down category. Please navigate from the yield report.
          </div>
        </main>
      </div>
    );
  }

  const trace = {
    x: countryData.countries,
    y: countryData.values,
    type: 'bar' as const,
    name: chartTitle,
    marker: { color: '#FF7043' },
    text: countryData.values.map((val) => formatNumber(val)),
    textposition: 'outside' as const,
    texttemplate: '%{text}',
    textfont: {
      size: 14,
      color: '#e2e8f0',
      family: 'Arial, sans-serif',
      weight: 'bold',
    },
    showlegend: false,
  };

  // Calculate min/max values for y-axis range
  const minValue = countryData.values.length > 0 ? Math.min(...countryData.values, 0) : 0;
  const maxValue = countryData.values.length > 0 ? Math.max(...countryData.values, 0) : 100;
  const valueRange = maxValue - minValue;
  const padding = valueRange * 0.1 || 10;

  const layout = {
    title: {
      text: chartTitle,
      font: { size: 18, family: 'Arial Black, Arial, sans-serif', color: '#e2e8f0' },
    },
    xaxis: {
      title: { text: 'Country', font: { size: 14, color: '#cbd5e1' } },
      tickfont: { size: 12, color: '#cbd5e1' },
      gridcolor: '#334155',
    },
    yaxis: {
      title: { text: 'Energy (MWh)', font: { size: 14, color: '#cbd5e1' } },
      tickfont: { size: 12, color: '#cbd5e1' },
      range: [minValue - padding, maxValue + padding],
      gridcolor: '#334155',
    },
    height: 500,
    margin: { t: 50, b: 80, l: 80, r: 40 },
    autosize: true,
    plot_bgcolor: '#0f172a',
    paper_bgcolor: '#0f172a',
  };

  const config = {
    responsive: true,
    displayModeBar: true,
    modeBarButtonsToRemove: ['zoom2d', 'pan2d', 'select2d', 'lasso2d', 'zoomIn2d', 'zoomOut2d', 'autoScale2d', 'resetScale2d'],
    displaylogo: false,
    toImageButtonOptions: {
      format: 'png',
      filename: 'yield_drilldown_chart',
      height: 1000,
      width: 1400,
      scale: 2
    },
    staticPlot: false,
    editable: false,
    scrollZoom: false,
    doubleClick: 'reset',
    showTips: false,
  } as Partial<Plotly.Config>;

  return (
    <div className="flex w-full flex-col bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 text-slate-100" style={{ minHeight: '100%' }}>
      <div className="flex-1">
      <main className="mx-auto flex max-w-[2400px] flex-col gap-2 px-6 pb-10 pt-4">
        {/* Header */}
        <div className="sticky top-0 z-10 mb-2 flex items-center justify-between rounded-b-2xl border-b border-slate-700/50 bg-gradient-to-r from-slate-800/80 to-slate-800/60 p-4 shadow-sm backdrop-blur-md">
          <div className="flex-1 text-center">
            <h1 className="bg-gradient-to-r from-sky-600 to-emerald-600 bg-clip-text text-xl font-bold text-transparent">
              {chartTitle} - Detailed Analysis
            </h1>
          </div>
          <button
            onClick={handleBack}
            className="rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-sky-700"
          >
            ← Back to Yield Report
          </button>
        </div>

        {/* Filters */}
        {filterOptions && (
          <YieldFilters
            filters={filters}
            options={filterOptions}
            loading={loading}
            onFiltersChange={handleFiltersChange}
            onReset={handleReset}
          />
        )}

        {/* Error Message */}
        {error && (
          <div className="rounded-lg border border-rose-300 bg-rose-50 p-6 text-sm text-rose-900 shadow-md">
            Failed to load yield data: {error}
          </div>
        )}

        {/* Chart */}
        {!loading && data.length > 0 && countryData.countries.length > 0 && (
          <div className="rounded-2xl border border-slate-700/50 bg-slate-800/90 p-6 shadow-md">
            <Plot data={[trace]} layout={layout} config={config} />
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="rounded-lg border border-slate-700/50 bg-slate-800/90 p-8 text-center text-slate-400">
            Loading chart data...
          </div>
        )}

        {/* Empty State */}
        {!loading && !error && (data.length === 0 || countryData.countries.length === 0) && (
          <div className="rounded-lg border border-slate-700/50 bg-slate-800/90 p-8 text-center text-slate-400">
            No yield data available for the selected filters
          </div>
        )}
      </main>
      </div>
    </div>
  );
}

