import { useEffect, useRef, useState } from 'react';

import { FilterBar } from './components/FilterBar';
import { GaugeSection } from './components/GaugeSection';
import { SummaryCards } from './components/SummaryCards';
import { Tabs } from './components/Tabs';
import { MonthlyDataView } from './components/MonthlyDataView';
import { useKpiFilters } from './hooks/useKpiFilters';
import { useKpiData } from './hooks/useKpiData';
import { exportKpiGaugesToCSV } from './components/exportKpiGaugesCsv';
import { useTheme } from '../../contexts/ThemeContext';

const KpiDashboard = () => {
  const { theme } = useTheme();
  const {
    filters,
    setCountries,
    setPortfolios,
    setAssets,
    setDate, // Deprecated: kept for backward compatibility
    setStartDate,
    setEndDate,
    setView,
    reset,
  } = useKpiFilters();
 
  const { loading, error, summary, options, gaugeValues, filteredMetrics } =
    useKpiData(filters);
  const hasInitializedCountries = useRef(false);
  const [activeTab, setActiveTab] = useState<'gauges' | 'monthly'>(() =>
    filters.view === 'monthly' ? 'monthly' : 'gauges',
  );

  // Mark filters as ready once data has loaded so Playwright/export can capture the filtered state
  // For gauges tab, we rely on useKpiData's loading state; for monthly tab,
  // MonthlyDataView is responsible for setting data-filters-ready when its own data is ready.
  useEffect(() => {
    if (activeTab !== 'gauges') {
      return;
    }

    if (!loading) {
      document.body.setAttribute('data-filters-ready', 'true');
      window.dispatchEvent(new CustomEvent('dashboard-filters-ready', {
        detail: { dashboardId: 'kpi' },
      }));
    } else {
      document.body.removeAttribute('data-filters-ready');
    }
  }, [loading, activeTab]);
  
  // Theme-aware colors
  const bgGradient = theme === 'dark'
    ? 'linear-gradient(to bottom right, #0f172a, #1e293b, #0f172a)'
    : 'linear-gradient(to bottom right, #f8fbff, #ffffff, #f8fbff)';
  const textColor = theme === 'dark' ? '#f1f5f9' : '#1a1a1a';

  useEffect(() => {
    if (
      !hasInitializedCountries.current &&
      !loading &&
      options.countries.length > 0 &&
      filters.countries.length === 0
    ) {
      setCountries(options.countries);
      hasInitializedCountries.current = true;
    }
  }, [loading, options.countries, filters.countries.length, setCountries]);

  const handleReset = () => {
    hasInitializedCountries.current = false;
    reset();
  };

  useEffect(() => {
    const handleDownloadRequest = () => {
      if (!loading && filteredMetrics.length > 0) {
        exportKpiGaugesToCSV(filteredMetrics);
      } else {
        window.alert('No KPI gauge data available to export for the current filters.');
      }
    };

    window.addEventListener('kpi:download-requested', handleDownloadRequest);
    return () =>
      window.removeEventListener(
        'kpi:download-requested',
        handleDownloadRequest,
      );
  }, [loading, filteredMetrics]);

  const tabs = [
    {
      id: 'gauges',
      label: 'KPI Gauges',
      content: (
        <div className="flex flex-col gap-2 p-2">
          <FilterBar
            filters={filters}
            options={options}
            disabled={loading}
            onCountriesChange={setCountries}
            onPortfoliosChange={setPortfolios}
            onAssetsChange={setAssets}
            onDateChange={setDate} // Deprecated: kept for backward compatibility
            onStartDateChange={setStartDate}
            onEndDateChange={setEndDate}
            onReset={handleReset}
          />

          <div className="flex justify-end">
            <button
              type="button"
              disabled={loading || filteredMetrics.length === 0}
              onClick={() => exportKpiGaugesToCSV(filteredMetrics)}
              className="rounded-full bg-gradient-to-r from-sky-500 to-indigo-500 px-4 py-1.5 text-xs font-semibold uppercase tracking-wide text-white shadow shadow-sky-500/40 transition hover:from-sky-400 hover:to-indigo-400 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Export Gauges CSV
            </button>
          </div>

          <SummaryCards
            summary={summary}
            filteredMetrics={filteredMetrics}
            loading={loading}
          />

          <GaugeSection values={gaugeValues} loading={loading} />

          {error && (
            <section 
              className="rounded-xl border p-3 text-xs shadow-xl"
              style={{
                borderColor: theme === 'dark' ? 'rgba(239, 68, 68, 0.4)' : 'rgba(220, 38, 38, 0.3)',
                backgroundColor: theme === 'dark' ? 'rgba(127, 29, 29, 0.3)' : 'rgba(254, 242, 242, 0.8)',
                color: theme === 'dark' ? '#fca5a5' : '#991b1b',
                boxShadow: theme === 'dark' ? '0 20px 25px -5px rgba(127, 29, 29, 0.4)' : '0 10px 15px -3px rgba(220, 38, 38, 0.1)',
              }}
            >
              Failed to load KPI data: {error}
            </section>
          )}
        </div>
      ),
    },
    {
      id: 'monthly',
      label: 'Monthly Generation Data',
      content: <MonthlyDataView options={options} />,
    },
  ];

  return (
    <div 
      className="flex flex-col overflow-hidden"
      style={{
        width: '100%',
        height: '100vh',
        minHeight: '100vh',
        background: bgGradient,
        color: textColor,
        transition: 'background 0.3s ease, color 0.3s ease',
      }}
    >
      <div className="w-full flex-1 overflow-y-auto p-0" style={{ minHeight: 0 }}>
        <Tabs
          tabs={tabs}
          activeTab={activeTab}
          onTabChange={(tabId) => {
            const nextTab = tabId as 'gauges' | 'monthly';
            setActiveTab(nextTab);
            setView(nextTab);
          }}
        />
      </div>
    </div>
  );
};

export default KpiDashboard;
