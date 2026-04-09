/**
 * Generation Budget Insights - Main Component
 * Displays IC Budget vs Expected Generation analysis
 * React Style V1 - Dark theme design system
 */
import { useState, useMemo, useEffect } from 'react';
import { useTheme } from '../../contexts/ThemeContext';
import { useResponsiveFontSize } from '../../utils/fontScaling';
import { useICBudgetData } from './hooks/useICBudgetData';
import { ICBudgetFilters } from './components/ICBudgetFilters';
import { MainTable } from './components/MainTable';
import { SummaryTable } from './components/SummaryTable';
import type { ICBudgetFilters as ICBudgetFiltersType } from './types';
import { filterICBudgetData } from './utils/filterUtils';

export function ICBudgetVsExpected() {
  const { theme } = useTheme();
  
  // Responsive font sizes
  const tabButtonFontSize = useResponsiveFontSize(10, 14, 9);
  
  const { data, loading, error, refetch } = useICBudgetData();
  
  const bgGradient = theme === 'dark'
    ? 'linear-gradient(to bottom right, #0f172a, #1e293b, #0f172a)'
    : 'linear-gradient(to bottom right, #f8fbff, #ffffff, #f8fbff)';
  const textColor = theme === 'dark' ? '#f1f5f9' : '#1a1a1a';
  const containerBg = theme === 'dark'
    ? 'linear-gradient(to bottom right, rgba(15, 23, 42, 0.9), rgba(30, 41, 59, 0.6))'
    : 'linear-gradient(to bottom right, rgba(255, 255, 255, 0.95), rgba(248, 250, 252, 0.9))';
  const containerBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(203, 213, 225, 0.8)';
  const containerShadow = theme === 'dark' 
    ? '0 20px 25px -5px rgba(0, 0, 0, 0.4)' 
    : '0 10px 15px -3px rgba(0, 0, 0, 0.1)';
  const tabContainerBg = theme === 'dark'
    ? 'linear-gradient(to bottom right, rgba(15, 23, 42, 0.5), rgba(30, 41, 59, 0.3))'
    : 'linear-gradient(to bottom right, rgba(248, 250, 252, 0.9), rgba(241, 245, 249, 0.8))';
  const tabActiveBg = theme === 'dark' ? 'rgba(59, 130, 246, 0.2)' : 'rgba(59, 130, 246, 0.1)';
  const tabActiveText = theme === 'dark' ? '#93c5fd' : '#1e40af';
  const tabActiveShadow = theme === 'dark' 
    ? '0 4px 6px -1px rgba(59, 130, 246, 0.2)' 
    : '0 2px 4px -1px rgba(59, 130, 246, 0.15)';
  const tabInactiveText = theme === 'dark' ? '#94a3b8' : '#64748b';
  const tabHoverBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.7)' : 'rgba(241, 245, 249, 0.9)';
  const tabHoverText = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';
  const [filters, setFilters] = useState<ICBudgetFiltersType>({
    country: undefined,
    portfolio: undefined,
    selectedMonth: null,
    selectedYear: null,
    selectedRange: null,
  });
  const [isInitialized, setIsInitialized] = useState(false);
  const [activeTab, setActiveTab] = useState<'main' | 'summary'>('main');

  // Initialize with current year when data is loaded
  useEffect(() => {
    if (!isInitialized && data && data.length > 0) {
      const currentYear = new Date().getFullYear().toString();

      // Collect unique month keys in YYYY-MM format from month_sort
      const monthKeys = Array.from(
        new Set(
          data
            .map((row) => row.month_sort)
            .filter((m): m is string => Boolean(m))
            .map((m) => m.substring(0, 7))
        )
      ).sort();

      // Prefer months from the current year
      const currentYearMonths = monthKeys.filter((m) => m.startsWith(currentYear));

      if (currentYearMonths.length > 0) {
        const startMonth = currentYearMonths[0];
        const endMonth = currentYearMonths[currentYearMonths.length - 1];
        setFilters({
          country: undefined,
          portfolio: undefined,
          selectedMonth: null,
          selectedYear: null,
          selectedRange: { start: startMonth, end: endMonth },
        });
        setIsInitialized(true);
      } else if (monthKeys.length > 0) {
        // Fallback: use the latest year available
        const latestMonth = monthKeys[monthKeys.length - 1];
        const latestYear = latestMonth.split('-')[0];
        const latestYearMonths = monthKeys.filter((m) => m.startsWith(latestYear));
        if (latestYearMonths.length > 0) {
          const startMonth = latestYearMonths[0];
          const endMonth = latestYearMonths[latestYearMonths.length - 1];
          setFilters({
            country: undefined,
            portfolio: undefined,
            selectedMonth: null,
            selectedYear: null,
            selectedRange: { start: startMonth, end: endMonth },
          });
          setIsInitialized(true);
        }
      }
    }
  }, [data, isInitialized]);

  // Filter data based on current filters
  const filteredData = useMemo(() => {
    return filterICBudgetData(data, filters);
  }, [data, filters]);

  const handleFiltersChange = (newFilters: ICBudgetFiltersType) => {
    setFilters(newFilters);
  };

  const handleReset = () => {
    const currentYear = new Date().getFullYear().toString();

    if (data && data.length > 0) {
      const monthKeys = Array.from(
        new Set(
          data
            .map((row) => row.month_sort)
            .filter((m): m is string => Boolean(m))
            .map((m) => m.substring(0, 7))
        )
      ).sort();

      const currentYearMonths = monthKeys.filter((m) => m.startsWith(currentYear));

      if (currentYearMonths.length > 0) {
        const startMonth = currentYearMonths[0];
        const endMonth = currentYearMonths[currentYearMonths.length - 1];
        setFilters({
          country: undefined,
          portfolio: undefined,
          selectedMonth: null,
          selectedYear: null,
          selectedRange: { start: startMonth, end: endMonth },
        });
        return;
      }
    }

    // Fallback: clear filters if no current-year data
    setFilters({
      country: undefined,
      portfolio: undefined,
      selectedMonth: null,
      selectedYear: null,
      selectedRange: null,
    });
  };

  const loadingTextColor = theme === 'dark' ? '#94a3b8' : '#64748b';
  const retryButtonBg = theme === 'dark' ? 'rgba(59, 130, 246, 0.2)' : 'rgba(59, 130, 246, 0.1)';
  const retryButtonText = theme === 'dark' ? '#93c5fd' : '#1e40af';
  const retryButtonHoverBg = theme === 'dark' ? 'rgba(59, 130, 246, 0.3)' : 'rgba(59, 130, 246, 0.15)';

  if (loading) {
    return (
      <div 
        className="flex size-full items-center justify-center"
        style={{
          background: bgGradient,
          color: textColor,
          transition: 'background 0.3s ease, color 0.3s ease',
        }}
      >
        <div className="text-lg" style={{ color: loadingTextColor }}>Loading IC Budget data...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div 
        className="flex size-full items-center justify-center"
        style={{
          background: bgGradient,
          color: textColor,
          transition: 'background 0.3s ease, color 0.3s ease',
        }}
      >
        <div className="text-center">
          <div className="mb-4 text-lg" style={{ color: '#f87171' }}>
            Error loading data: {error}
          </div>
          <button
            onClick={refetch}
            className="rounded-lg px-4 py-2 text-sm font-semibold transition-all"
            style={{
              backgroundColor: retryButtonBg,
              color: retryButtonText,
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = retryButtonHoverBg;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = retryButtonBg;
            }}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

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
      {/* Main Content */}
      <div className="flex h-full flex-col gap-1 px-2 py-1">
        {/* Filters */}
        <div className="shrink-0">
          <ICBudgetFilters
            data={data}
            filters={filters}
            onFiltersChange={handleFiltersChange}
            onReset={handleReset}
          />
        </div>

        {/* Tab Navigation */}
        <div 
          className="flex shrink-0 gap-1 px-2 py-0.5"
          style={{
            background: tabContainerBg,
          }}
        >
          <button
            type="button"
            onClick={() => setActiveTab('main')}
            className="flex-1 rounded-lg px-3 py-0.5 font-semibold uppercase tracking-wide transition-all duration-200"
            style={{
              fontSize: `${tabButtonFontSize}px`,
              backgroundColor: activeTab === 'main' ? tabActiveBg : 'transparent',
              color: activeTab === 'main' ? tabActiveText : tabInactiveText,
              boxShadow: activeTab === 'main' ? tabActiveShadow : 'none',
            }}
            onMouseEnter={(e) => {
              if (activeTab !== 'main') {
                e.currentTarget.style.backgroundColor = tabHoverBg;
                e.currentTarget.style.color = tabHoverText;
              }
            }}
            onMouseLeave={(e) => {
              if (activeTab !== 'main') {
                e.currentTarget.style.backgroundColor = 'transparent';
                e.currentTarget.style.color = tabInactiveText;
              }
            }}
          >
            Main Table
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('summary')}
            className="flex-1 rounded-lg px-3 py-0.5 font-semibold uppercase tracking-wide transition-all duration-200"
            style={{
              fontSize: `${tabButtonFontSize}px`,
              backgroundColor: activeTab === 'summary' ? tabActiveBg : 'transparent',
              color: activeTab === 'summary' ? tabActiveText : tabInactiveText,
              boxShadow: activeTab === 'summary' ? tabActiveShadow : 'none',
            }}
            onMouseEnter={(e) => {
              if (activeTab !== 'summary') {
                e.currentTarget.style.backgroundColor = tabHoverBg;
                e.currentTarget.style.color = tabHoverText;
              }
            }}
            onMouseLeave={(e) => {
              if (activeTab !== 'summary') {
                e.currentTarget.style.backgroundColor = 'transparent';
                e.currentTarget.style.color = tabInactiveText;
              }
            }}
          >
            Summary & Notes
          </button>
        </div>

        {/* Tab Content */}
        <div 
          key={`${filters.selectedMonth}-${filters.selectedYear}-${filters.selectedRange?.start}-${filters.selectedRange?.end}-${filters.country}-${filters.portfolio}`}
          className="min-h-0 flex-1 overflow-hidden rounded-xl border shadow-xl"
          style={{
            borderColor: containerBorder,
            background: containerBg,
            boxShadow: containerShadow,
          }}
        >
          <div className="h-full overflow-auto p-2">
            {activeTab === 'main' && <MainTable data={filteredData} />}
            {activeTab === 'summary' && <SummaryTable data={filteredData} />}
          </div>
        </div>
      </div>
    </div>
  );
}

