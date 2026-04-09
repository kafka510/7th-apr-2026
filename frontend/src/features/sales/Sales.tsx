/**
 * Main Sales Dashboard Component
 */
 
import { useState, useMemo, useEffect } from 'react';
import { useSalesData } from './hooks/useSalesData';
import { SalesFilters } from './components/SalesFilters';
import { KPICards } from './components/KPICards';
import { SalesCharts } from './components/SalesCharts';
import { InsightsBox } from './components/InsightsBox';
import type { SalesFilters as SalesFiltersType } from './types';
import { filterYieldData, filterMapData, calculateKPIs, calculateChartData } from './utils/calculations';
import { normalizeMonth } from './utils/dataUtils';
import { useTheme } from '../../contexts/ThemeContext';

export function Sales() {
  const { theme } = useTheme();
  const { data, loading, error } = useSalesData();
  const [filters, setFilters] = useState<SalesFiltersType>({});
  const [isInitialized, setIsInitialized] = useState(false);

  // Initialize with current year when data is loaded
  useEffect(() => {
    if (!loading && data && data.yieldData.length > 0 && !isInitialized) {
      const currentYear = new Date().getFullYear().toString();
      const availableMonths = [...new Set(data.yieldData.map((row) => row.month).filter(Boolean))].sort();
      
      // Normalize months to YYYY-MM format for comparison
      const normalizedMonths = availableMonths
        .map((month) => normalizeMonth(month))
        .filter(Boolean)
        .sort();
      
      // Find months from current year
      const currentYearMonths = normalizedMonths.filter((month) => month.startsWith(currentYear));

      if (currentYearMonths.length > 0) {
        // Set range from first month of current year to latest month of current year
        const startMonth = currentYearMonths[0];
        const endMonth = currentYearMonths[currentYearMonths.length - 1];
        
        setFilters({
          selectedYear: null,
          selectedMonth: null,
          selectedRange: { start: startMonth, end: endMonth },
        });
        setIsInitialized(true);
      } else {
        // If no current year data, use latest available year
        const latestMonth = normalizedMonths[normalizedMonths.length - 1];
        if (latestMonth) {
          const latestYear = latestMonth.split('-')[0];
          const latestYearMonths = normalizedMonths.filter((month) => month.startsWith(latestYear));
          if (latestYearMonths.length > 0) {
            const startMonth = latestYearMonths[0];
            const endMonth = latestYearMonths[latestYearMonths.length - 1];
            setFilters({
              selectedYear: null,
              selectedMonth: null,
              selectedRange: { start: startMonth, end: endMonth },
            });
            setIsInitialized(true);
          }
        }
      }
    }
  }, [data, loading, isInitialized]);

  // Filter data based on current filters
  const filteredData = useMemo(() => {
    if (!data) return { yieldData: [], mapData: [] };

    const filteredYield = filterYieldData(data.yieldData, filters);
    const filteredMap = filterMapData(data.mapData, filters);

    return {
      yieldData: filteredYield,
      mapData: filteredMap,
    };
  }, [data, filters]);

  // Calculate KPIs
  const kpis = useMemo(() => {
    if (!filteredData.yieldData.length || !filteredData.mapData.length) {
      return {
        solarEnergy: 0,
        bessEnergy: 0,
        totalCO2: 0,
        treesSaved: 0,
        solarAssetsCount: 0,
        solarDcCapacity: 0,
        bessCapacity: 0,
      };
    }
    return calculateKPIs(filteredData.yieldData);
  }, [filteredData]);

  // Calculate chart data
  const chartData = useMemo(() => {
    if (!filteredData.yieldData.length) {
      return {
        solarGen: [],
        bessGen: [],
        co2: [],
        trees: [],
      };
    }
    return calculateChartData(filteredData.yieldData);
  }, [filteredData.yieldData]);

  const handleFiltersChange = (newFilters: SalesFiltersType) => {
    setFilters(newFilters);
  };

  const handleResetFilters = () => {
    // Reset to current year on reset
    const currentYear = new Date().getFullYear().toString();
    if (data && data.yieldData.length > 0) {
      const availableMonths = [...new Set(data.yieldData.map((row) => row.month).filter(Boolean))].sort();
      const normalizedMonths = availableMonths
        .map((month) => normalizeMonth(month))
        .filter(Boolean)
        .sort();
      const currentYearMonths = normalizedMonths.filter((month) => month.startsWith(currentYear));
      
      if (currentYearMonths.length > 0) {
        const startMonth = currentYearMonths[0];
        const endMonth = currentYearMonths[currentYearMonths.length - 1];
        setFilters({
          selectedYear: null,
          selectedMonth: null,
          selectedRange: { start: startMonth, end: endMonth },
        });
      } else {
        setFilters({});
      }
    } else {
      setFilters({});
    }
  };

  const bgColor = theme === 'dark' ? '#1a2233' : '#f8fbff';
  const textColor = theme === 'dark' ? '#f1f5f9' : '#1a1a1a';

  if (loading) {
    return (
      <div 
        className="flex size-full items-center justify-center"
        style={{ 
          backgroundColor: bgColor,
          color: textColor,
          transition: 'background-color 0.3s ease, color 0.3s ease',
        }}
      >
        <div className="text-center">
          <div className="mb-4 text-lg font-semibold" style={{ color: theme === 'dark' ? '#60a5fa' : '#0072ce' }}>Loading sales data...</div>
          <div className="h-2 w-64 overflow-hidden rounded-full" style={{ backgroundColor: theme === 'dark' ? '#334155' : '#e2e8f0' }}>
            <div className="h-full animate-pulse" style={{ width: '60%', backgroundColor: theme === 'dark' ? '#3b82f6' : '#0072ce' }} />
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div 
        className="flex size-full items-center justify-center"
        style={{ 
          backgroundColor: bgColor,
          color: textColor,
          transition: 'background-color 0.3s ease, color 0.3s ease',
        }}
      >
        <div className="rounded-xl border p-6 text-center shadow-xl" style={{ 
          borderColor: theme === 'dark' ? 'rgba(239, 68, 68, 0.5)' : 'rgba(220, 38, 38, 0.3)',
          backgroundColor: theme === 'dark' ? 'rgba(127, 29, 29, 0.3)' : 'rgba(254, 242, 242, 0.8)',
        }}>
          <div className="mb-2 text-lg font-semibold" style={{ color: theme === 'dark' ? '#f87171' : '#dc2626' }}>Error loading sales data</div>
          <div className="text-sm" style={{ color: theme === 'dark' ? '#fca5a5' : '#991b1b' }}>{error}</div>
        </div>
      </div>
    );
  }

  if (!data || !data.yieldData.length || !data.mapData.length) {
    return (
      <div 
        className="flex size-full items-center justify-center"
        style={{ 
          backgroundColor: bgColor,
          color: textColor,
          transition: 'background-color 0.3s ease, color 0.3s ease',
        }}
      >
        <div className="text-center">
          <div className="mb-2 text-lg font-semibold" style={{ color: textColor }}>No data available</div>
          <div className="text-sm" style={{ color: theme === 'dark' ? '#94a3b8' : '#718096' }}>Please check your data sources.</div>
        </div>
      </div>
    );
  }

  return (
    <div 
      className="flex w-full flex-col"
      style={{ 
        backgroundColor: bgColor,
        color: textColor,
        transition: 'background-color 0.3s ease, color 0.3s ease',
        minHeight: '100%',
      }}
    >
      <div className="flex min-h-full flex-col gap-2 p-2">
      {/* Filters Section */}
      <SalesFilters
        mapData={data.mapData}
        yieldData={data.yieldData}
        filters={filters}
        onFiltersChange={handleFiltersChange}
        onReset={handleResetFilters}
      />

      {/* KPI Cards */}
      <KPICards metrics={kpis} />

      {/* Charts Section */}
      <SalesCharts
        solarGenData={chartData.solarGen}
        bessGenData={chartData.bessGen}
        co2Data={chartData.co2}
        treesData={chartData.trees}
      />

      {/* Insights Box */}
      <InsightsBox metrics={kpis} />
      </div>
    </div>
  );
}

