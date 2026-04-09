/**
 * Main Portfolio Map Component
 */
 
import { useState, useMemo, useCallback, useEffect } from 'react';
import { usePortfolioMapData } from './hooks/usePortfolioMapData';
import { PortfolioMapFilters } from './components/PortfolioMapFilters';
import { KPICards } from './components/KPICards';
import { PerformanceLegend } from './components/PerformanceLegend';
import { PortfolioMapComponent } from './components/PortfolioMapComponent';
import type { PortfolioMapFilters as FiltersType, PerformanceFilter, KPIMetrics } from './types';
import { useTheme } from '../../contexts/ThemeContext';
import { useFilterPersistence } from '../../hooks/useFilterPersistence';
import { loadFilters, clearFilters } from '../../utils/filterPersistence';

const DASHBOARD_ID = 'portfolio-map';

export function PortfolioMap() {
  const { theme } = useTheme();
  const { data, loading, error } = usePortfolioMapData();
  const [mapFilters, setMapFilters] = useState<FiltersType>(() => {
    const stored = loadFilters<FiltersType>(DASHBOARD_ID);
    if (stored && typeof stored === 'object') {
      return stored;
    }
    return {};
  });
  const [performanceFilter, setPerformanceFilter] = useState<PerformanceFilter>('all');
  const [kpis, setKPIs] = useState<KPIMetrics>({
    siteCount: 0,
    pvCapacity: 0,
    bessCapacity: 0,
  });

  // Persist filters globally for download / restore
  useFilterPersistence(DASHBOARD_ID, mapFilters);

  // Log data when it changes
  useEffect(() => {
    if (data) {
      console.log('[PortfolioMap] Data loaded:', {
        mapDataLength: data.mapData.length,
        yieldDataLength: data.yieldData.length,
        firstMapEntry: data.mapData[0],
      });
    }
  }, [data]);

  // Prepare map filters in the format expected by the map component
  const mapFiltersFormatted = useMemo(() => {
    const formatted: Record<string, string[]> = {};
    if (mapFilters.country) formatted.country = mapFilters.country;
    if (mapFilters.plantType) formatted.plant_type = mapFilters.plantType;
    if (mapFilters.installationType) formatted.installation_type = mapFilters.installationType;
    if (mapFilters.portfolio) formatted.portfolio = mapFilters.portfolio;
    if (mapFilters.assetNo) formatted.asset_no = mapFilters.assetNo;
    if (mapFilters.offtaker) formatted.offtaker = mapFilters.offtaker;
    if (mapFilters.cod) formatted.cod = mapFilters.cod;
    return formatted;
  }, [mapFilters]);

  const handleFiltersChange = useCallback((newFilters: FiltersType) => {
    setMapFilters(newFilters);
  }, []);

  const handleResetFilters = useCallback(() => {
    setMapFilters({});
    setPerformanceFilter('all');
    clearFilters(DASHBOARD_ID);
  }, []);

  const handlePerformanceFilterChange = useCallback((filter: PerformanceFilter) => {
    setPerformanceFilter(filter);
  }, []);

  const handleKPIsUpdate = useCallback((newKPIs: KPIMetrics) => {
    setKPIs((prevKPIs) => {
      // Only update if values actually changed to prevent infinite loops
      if (
        prevKPIs.siteCount === newKPIs.siteCount &&
        prevKPIs.pvCapacity === newKPIs.pvCapacity &&
        prevKPIs.bessCapacity === newKPIs.bessCapacity
      ) {
        return prevKPIs;
      }
      return newKPIs;
    });
  }, []);

  const handleMapReady = useCallback(() => {
    // Map is ready, can be used for future enhancements
  }, []);

  const bgGradient = theme === 'dark'
    ? 'linear-gradient(to bottom right, #0f172a, #1e293b, #0f172a)'
    : 'linear-gradient(to bottom right, #f8fbff, #ffffff, #f8fbff)';
  const textColor = theme === 'dark' ? '#f1f5f9' : '#1a1a1a';
  const cardBg = theme === 'dark'
    ? 'linear-gradient(to bottom right, rgba(15, 23, 42, 0.9), rgba(30, 41, 59, 0.6))'
    : 'linear-gradient(to bottom right, #ffffff, #f8fafc)';
  const cardBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(226, 232, 240, 0.8)';

  // Signal when Portfolio Map data + filters are ready for export/download
  useEffect(() => {
    const hasData = !!data && data.mapData.length > 0;
    if (!loading && hasData) {
      document.body.setAttribute('data-filters-ready', 'true');
      window.dispatchEvent(
        new CustomEvent('dashboard-filters-ready', { detail: { dashboardId: DASHBOARD_ID } }),
      );
    } else {
      document.body.removeAttribute('data-filters-ready');
    }
  }, [loading, data]);

  if (loading) {
    return (
      <div 
        className="fixed inset-0 z-50 flex flex-col items-center justify-center"
        style={{ background: bgGradient, transition: 'background 0.3s ease' }}
      >
        <div className="flex flex-col items-center">
          <svg className="mb-4 animate-spin" width="64" height="64" viewBox="0 0 100 100">
            <circle cx="50" cy="50" r="36" stroke="#38bdf8" strokeWidth="8" fill="none" strokeLinecap="round" strokeDasharray="180" strokeDashoffset="30" />
            <circle cx="50" cy="50" r="36" stroke="#0ea5e9" strokeWidth="8" fill="none" strokeLinecap="round" strokeDasharray="100" strokeDashoffset="70" />
          </svg>
          <span 
            className="text-2xl font-semibold tracking-wide"
            style={{ color: textColor, transition: 'color 0.3s ease' }}
          >
            Loading dashboard...
          </span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div 
        className="fixed inset-0 z-50 flex items-center justify-center text-center"
        style={{ background: bgGradient, transition: 'background 0.3s ease' }}
      >
        <div className="text-3xl font-bold text-red-400">
          ⚠️ Error Loading Portfolio Map: {error}
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div 
        className="flex min-h-screen items-center justify-center"
        style={{ background: bgGradient, transition: 'background 0.3s ease' }}
      >
        <div 
          className="text-center text-lg font-semibold"
          style={{ color: textColor, transition: 'color 0.3s ease' }}
        >
          No data available
        </div>
      </div>
    );
  }
  
  // Log data structure for debugging
  console.log('[PortfolioMap] Rendering with data:', {
    mapDataLength: data.mapData?.length || 0,
    yieldDataLength: data.yieldData?.length || 0,
    sampleMapEntry: data.mapData?.[0],
    sampleYieldEntry: data.yieldData?.[0],
  });

  return (
    <div 
      className="flex w-full flex-col"
      style={{
        background: bgGradient,
        color: textColor,
        transition: 'background 0.3s ease, color 0.3s ease',
      }}
    >
      <div className="flex flex-col gap-2 p-2">

      {/* Filters Section */}
      <PortfolioMapFilters
        mapData={data.mapData}
        filters={mapFilters}
        onFiltersChange={handleFiltersChange}
        onReset={handleResetFilters}
      />

      {/* KPI + Legend Row */}
      <div className="mb-1 flex w-full shrink-0 flex-col gap-1 lg:flex-row">
        {/* KPI Cards (70%) */}
        <div className="w-full lg:max-w-[70%] lg:basis-[70%]">
          <KPICards metrics={kpis} />
        </div>

        {/* Performance Legend (30%) */}
        <div className="w-full lg:max-w-[30%] lg:basis-[30%]">
          <PerformanceLegend filter={performanceFilter} onFilterChange={handlePerformanceFilterChange} />
        </div>
      </div>

      {/* Map Section */}
      <div 
        className="relative overflow-hidden rounded-xl shadow-xl" 
        style={{ 
          zIndex: 1, 
          height: 'calc(100vh - 280px)', /* Viewport minus navbar, filters, KPIs, padding */
          minHeight: '400px',
          border: `1px solid ${cardBorder}`,
          background: cardBg,
          transition: 'background 0.3s ease, border-color 0.3s ease',
        }}
      >
        <PortfolioMapComponent
          mapData={data.mapData}
          yieldData={data.yieldData}
          filters={{
            mapFilters: mapFiltersFormatted,
            performanceFilter,
          }}
          onKPIsUpdate={handleKPIsUpdate}
          onMapReady={handleMapReady}
        />
      </div>
    </div>
    </div>
  );
}

