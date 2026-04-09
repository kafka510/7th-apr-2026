import { useState, useMemo, useEffect } from 'react';
import { useTheme } from '../../contexts/ThemeContext';
import { RevenueLossFilters } from './components/RevenueLossFilters';
import { RevenueLossCharts } from './components/RevenueLossCharts';
import { useRevenueLossData } from './hooks/useRevenueLossData';
import type { RevenueLossFilters as RevenueLossFiltersType } from './types';

export function RevenueLoss() {
  const { theme } = useTheme();
  // Start with empty filters - will compute default after data loads
  const [userFilters, setUserFilters] = useState<RevenueLossFiltersType>({});
  
  // Theme-aware colors
  const bgGradient = theme === 'dark'
    ? 'linear-gradient(to bottom right, #0f172a, #1e293b, #0f172a)'
    : 'linear-gradient(to bottom right, #f8fbff, #ffffff, #f8fbff)';
  const textColor = theme === 'dark' ? '#f1f5f9' : '#1a1a1a';

  // First fetch with empty filters to get filterOptions and revenueData
  const { filterOptions, revenueData, loading: optionsLoading, error: optionsError } = useRevenueLossData({});

  // Compute effective filters: use user filters if set, otherwise default to latest month
  const effectiveFilters = useMemo<RevenueLossFiltersType>(() => {
    // If user has set filters, use those
    if (userFilters.month || userFilters.year || userFilters.range || userFilters.countries || userFilters.portfolios) {
      return userFilters;
    }

    // Otherwise, default to latest available month when data is loaded
    if (!optionsLoading && filterOptions.months.length > 0) {
      const latestMonth = filterOptions.months[filterOptions.months.length - 1];
      return { month: latestMonth };
    }

    // Return empty filters while loading
    return {};
  }, [userFilters, optionsLoading, filterOptions.months]);

  // Use effective filters for actual data fetching
  const { expectedData, operationalData, loading, error: dataError } = useRevenueLossData(effectiveFilters);

  // Combine errors from both calls
  const error: Error | null = optionsError || dataError;

  // Ensure the component fills the viewport, especially in iframes
  useEffect(() => {
    const root = document.getElementById('react-root');
    if (root) {
      // Set explicit height for iframe compatibility
      const setHeight = () => {
        if (window.self !== window.top) {
          // In iframe - use parent's available height or viewport
          root.style.height = '100%';
          root.style.minHeight = '100vh';
        } else {
          // Standalone - use viewport height
          root.style.height = '100vh';
          root.style.minHeight = '100vh';
        }
      };

      setHeight();
      window.addEventListener('resize', setHeight);
      return () => window.removeEventListener('resize', setHeight);
    }
  }, []);

  const handleFiltersChange = (newFilters: RevenueLossFiltersType) => {
    setUserFilters(newFilters);
  };

  const handleReset = () => {
    setUserFilters({});
  };

  const handleAssetClick = (asset: string, period: string) => {
    // Asset click handler - can be enhanced with breakdown details modal
    console.log('Asset clicked:', asset, 'Period:', period);
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
        {/* Filter Bar */}
        <div className="flex shrink-0">
          <div className="min-w-0 flex-1">
            <RevenueLossFilters
              filters={effectiveFilters}
              options={filterOptions}
              loading={loading}
              onFiltersChange={handleFiltersChange}
              onReset={handleReset}
            />
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
              <span>Failed to load revenue loss data: {error?.message || 'Unknown error'}</span>
            </div>
          </div>
        )}

        {/* Main Content - Dual Charts */}
        {!loading && !error && (expectedData.length > 0 || operationalData.length > 0) && (
          <div className="flex min-h-0 flex-1">
            <RevenueLossCharts
              expectedData={expectedData}
              operationalData={operationalData}
              selectedMonth={effectiveFilters.month ?? undefined}
              selectedYear={effectiveFilters.year ?? undefined}
              revenueData={revenueData}
              onAssetClick={handleAssetClick}
            />
          </div>
        )}

        {/* Loading State */}
        {(loading || optionsLoading) && (
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
                  className="size-12 animate-spin" 
                  fill="none" 
                  viewBox="0 0 24 24"
                  style={{ color: theme === 'dark' ? '#60a5fa' : '#0072ce' }}
                >
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
              </div>
              <h2 
                className="mb-2 text-lg font-semibold"
                style={{ color: textColor }}
              >
                Loading Data
              </h2>
              <p 
                className="text-sm"
                style={{ color: theme === 'dark' ? '#94a3b8' : '#64748b' }}
              >
                Please wait while we fetch the revenue loss data...
              </p>
            </div>
          </div>
        )}

        {/* No Data Message */}
        {!loading && !error && expectedData.length === 0 && operationalData.length === 0 && (
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
}

