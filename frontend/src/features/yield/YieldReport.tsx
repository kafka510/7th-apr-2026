import { useEffect, useRef } from 'react';
import { useTheme } from '../../contexts/ThemeContext';

import { BreakdownChart } from './components/BreakdownChart';
import { BreakdownTable } from './components/BreakdownTable';
import { CapacityCards } from './components/CapacityCards';
import { FilterBar } from './components/FilterBar';
import { YieldFiltersProvider } from './contexts/YieldFiltersContext';
import { useFilters } from './hooks/useFilters';
import { useYieldData } from './hooks/useYieldData';

const YieldReportDashboard = () => {
  const { theme } = useTheme();
  const {
    filters,
    setCountries,
    setPortfolios,
    setAssets,
    setMonth,
    setYear,
    setRange,
    reset,
  } = useFilters();

  const { loading, error, data, options } = useYieldData(filters);
  
  const hasInitializedCountries = useRef(false);
  
  // Theme-aware colors
  const bgGradient = theme === 'dark'
    ? 'linear-gradient(to bottom right, #0f172a, #1e293b, #0f172a)'
    : 'linear-gradient(to bottom right, #f8fbff, #ffffff, #f8fbff)';
  const textColor = theme === 'dark' ? '#f1f5f9' : '#1a1a1a';

  // Auto-select all countries ONLY on initial page load
  // This effect should only run once when data finishes loading for the first time
  useEffect(() => {
    // Only run if:
    // 1. We haven't initialized countries yet (using ref to ensure it only runs once)
    // 2. Data has finished loading
    // 3. Countries are available
    // 4. No countries are currently selected
    if (
      !hasInitializedCountries.current &&
      !loading &&
      options.countries.length > 0 &&
      filters.countries.length === 0
    ) {
      // setCountries uses functional update (prev => ({ ...prev, countries }))
      // so it will preserve month, year, range, portfolios, and assets
      setCountries(options.countries);
      hasInitializedCountries.current = true;
    }
    // Depend on loading and options.countries.length (not the array itself to avoid re-runs)
    // The ref guard (hasInitializedCountries.current) ensures this only runs once
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loading, options.countries.length]);

  // Handle reset - ensure countries get re-selected after reset
  const handleReset = () => {
    hasInitializedCountries.current = false;
    reset();
  };

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
      <main className="flex flex-col gap-2 p-2">
        {/* Filter Bar and Capacity Cards in Single Row */}
        <div className="flex shrink-0 items-stretch gap-2">
          {/* Filter Bar - Takes more space */}
          <div className="min-w-0 flex-[2]">
            <FilterBar
              filters={filters}
              options={options}
              disabled={loading}
              onCountriesChange={setCountries}
              onPortfoliosChange={setPortfolios}
              onAssetsChange={setAssets}
              onMonthChange={setMonth}
              onYearChange={setYear}
              onRangeChange={setRange}
              onReset={handleReset}
            />
          </div>

          {/* Capacity Cards - Takes less space */}
          <div className="min-w-0 flex-1">
            <CapacityCards data={data} loading={loading} />
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div 
            className="shrink-0 rounded-lg border p-2 text-xs shadow-lg"
            style={{
              borderColor: theme === 'dark' ? 'rgba(239, 68, 68, 0.5)' : 'rgba(220, 38, 38, 0.3)',
              background: theme === 'dark' 
                ? 'linear-gradient(to right, rgba(127, 29, 29, 0.3), rgba(153, 27, 27, 0.2))' 
                : 'linear-gradient(to right, rgba(254, 242, 242, 0.8), rgba(254, 226, 226, 0.6))',
              color: theme === 'dark' ? '#fca5a5' : '#991b1b',
              boxShadow: theme === 'dark' 
                ? '0 10px 15px -3px rgba(127, 29, 29, 0.3)' 
                : '0 10px 15px -3px rgba(220, 38, 38, 0.1)',
            }}
          >
            <div className="flex items-center gap-2">
              <svg className="size-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>Failed to load yield data: {error}</span>
            </div>
          </div>
        )}

        {/* Main Content - Chart and Table Side by Side */}
        {!loading && !error && data.length > 0 && (
          <div className="flex flex-col gap-2 sm:flex-row">
            {/* Chart - Left Side */}
            <div className="flex min-w-0 flex-1 flex-col">
              <BreakdownChart data={data} filters={filters} options={options} loading={loading} />
            </div>

            {/* Table - Right Side */}
            <div className="flex min-w-0 flex-1 flex-col">
              <BreakdownTable data={data} loading={loading} />
            </div>
          </div>
        )}

        {/* No Data Message */}
        {!loading && !error && data.length === 0 && (
          <div 
            className="flex flex-1 items-center justify-center rounded-xl border shadow-xl"
            style={{
              borderColor: theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(203, 213, 225, 0.8)',
              background: theme === 'dark'
                ? 'linear-gradient(to bottom right, rgba(30, 41, 59, 0.9), rgba(51, 65, 85, 0.6))'
                : 'linear-gradient(to bottom right, rgba(255, 255, 255, 0.95), rgba(248, 250, 252, 0.9))',
              boxShadow: theme === 'dark' 
                ? '0 20px 25px -5px rgba(0, 0, 0, 0.4)' 
                : '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
            }}
          >
            <div className="text-center">
              <div className="mb-3 flex justify-center">
                <svg 
                  className="size-12" 
                  fill="none" 
                  viewBox="0 0 24 24" 
                  stroke="currentColor"
                  style={{ color: theme === 'dark' ? '#64748b' : '#94a3b8' }}
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <h2 
                className="mb-2 text-lg font-semibold"
                style={{ color: textColor }}
              >
                No Data Available
              </h2>
              <p 
                className="text-sm"
                style={{ color: theme === 'dark' ? '#94a3b8' : '#64748b' }}
              >
                No records found with the current filters. Try adjusting your filter selections.
              </p>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

const YieldReport = () => (
  <YieldFiltersProvider>
    <YieldReportDashboard />
  </YieldFiltersProvider>
);

export default YieldReport;

