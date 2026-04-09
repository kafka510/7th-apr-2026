import { useState, useEffect } from 'react';
import { useTheme } from '../../contexts/ThemeContext';
import { BESSFilters } from './components/BESSFilters';
import { BESSKPICards } from './components/BESSKPICards';
import { BESSCharts } from './components/BESSCharts';
import { useBESSData } from './hooks/useBESSData';
import type { BESSFilters as BESSFiltersType } from './types';
import { useFilterPersistence } from '../../hooks/useFilterPersistence';
import { loadFilters, clearFilters } from '../../utils/filterPersistence';

const DASHBOARD_ID = 'bess-performance';

function loadFiltersFromStorage(): BESSFiltersType {
  const stored = loadFilters<BESSFiltersType>(DASHBOARD_ID);
  if (stored && typeof stored === 'object') {
    return {
      month: stored.month ?? null,
      year: stored.year ?? null,
      range: stored.range ?? null,
      country: Array.isArray(stored.country) ? stored.country : [],
      portfolio: Array.isArray(stored.portfolio) ? stored.portfolio : [],
      asset: Array.isArray(stored.asset) ? stored.asset : [],
    };
  }
  return {
    country: [],
    portfolio: [],
    asset: [],
    month: null,
    year: null,
    range: null,
  };
}

export function BESSPerformance() {
  const { theme } = useTheme();
  const [userFilters, setUserFilters] = useState<BESSFiltersType>(loadFiltersFromStorage);

  // Persist user-selected filters for download / restore
  useFilterPersistence(DASHBOARD_ID, userFilters);

  // Fetch data with empty filters to get filterOptions
  const { filterOptions, loading: optionsLoading } = useBESSData({});

  // Use user filters for actual data filtering
  const { filteredData, kpiData, chartData, loading, error } = useBESSData(userFilters);

  // Ensure the component fills the viewport, especially in iframes
  useEffect(() => {
    const root = document.getElementById('react-root');
    if (root) {
      const setHeight = () => {
        if (window.self !== window.top) {
          root.style.height = '100%';
          root.style.minHeight = '100vh';
        } else {
          root.style.height = '100vh';
          root.style.minHeight = '100vh';
        }
      };

      setHeight();
      window.addEventListener('resize', setHeight);
      return () => window.removeEventListener('resize', setHeight);
    }
  }, []);

  const handleFiltersChange = (newFilters: BESSFiltersType) => {
    setUserFilters(newFilters);
  };

  const handleReset = () => {
    setUserFilters({
      country: [],
      portfolio: [],
      asset: [],
      month: null,
      year: null,
      range: null,
    });
    clearFilters(DASHBOARD_ID);
  };

  const bgGradient = theme === 'dark'
    ? 'linear-gradient(to bottom right, #0f172a, #1e293b, #0f172a)'
    : 'linear-gradient(to bottom right, #f8fbff, #ffffff, #f8fbff)';
  const textColor = theme === 'dark' ? '#f1f5f9' : '#1a1a1a';
  const errorTextColor = theme === 'dark' ? '#e2e8f0' : '#4a5568';
  const loadingTextColor = theme === 'dark' ? '#94a3b8' : '#64748b';

  // Signal when BESS performance data + filters are ready for export/download
  useEffect(() => {
    const hasData = filteredData.length > 0;
    if (!loading && !optionsLoading && hasData) {
      document.body.setAttribute('data-filters-ready', 'true');
      window.dispatchEvent(
        new CustomEvent('dashboard-filters-ready', { detail: { dashboardId: DASHBOARD_ID } }),
      );
    } else {
      document.body.removeAttribute('data-filters-ready');
    }
  }, [loading, optionsLoading, filteredData.length]);

  if (error) {
    return (
      <div 
        className="flex w-full flex-col"
        style={{
          background: bgGradient,
          color: textColor,
          transition: 'background 0.3s ease, color 0.3s ease',
          minHeight: '100%',
        }}
      >
        <div style={{ padding: '20px', textAlign: 'center', color: '#f87171' }}>
          <h2 style={{ color: '#f87171' }}>Error loading data</h2>
          <p style={{ color: errorTextColor }}>{error.message}</p>
        </div>
      </div>
    );
  }

  return (
    <div
      className="flex size-full flex-col"
      style={{
        margin: 0,
        padding: 0,
        boxSizing: 'border-box',
        overflow: 'visible',
        background: bgGradient,
        color: textColor,
        transition: 'background 0.3s ease, color 0.3s ease',
      }}
    >

      {/* Filters */}
      <BESSFilters
        filters={userFilters}
        options={filterOptions}
        loading={loading || optionsLoading}
        onFiltersChange={handleFiltersChange}
        onReset={handleReset}
      />

      {/* KPI Cards */}
      <BESSKPICards kpiData={kpiData} loading={loading || optionsLoading} />

      {/* Charts */}
      <div
        className="flex h-full flex-col gap-2 p-2"
        style={{
          flex: 1,
          minHeight: 0,
          overflow: 'auto',
        }}
      >
        {loading || optionsLoading ? (
          <div style={{ padding: '60px 0', textAlign: 'center', fontSize: '1.4rem', color: loadingTextColor }}>
            Loading charts...
          </div>
        ) : filteredData.length === 0 ? (
          <div style={{ padding: '60px 0', textAlign: 'center', fontSize: '1.4rem', color: loadingTextColor }}>
            No data available for the selected filters
          </div>
        ) : (
          <BESSCharts chartData={chartData} filteredData={filteredData} loading={loading || optionsLoading} />
        )}
      </div>
    </div>
  );
}

