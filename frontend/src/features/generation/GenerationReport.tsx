/**
 * Generation Report Main Component
 */
import { useState, useMemo, useCallback, useEffect, useRef } from 'react';
import { useGenerationData } from './hooks/useGenerationData';
import { PeriodPicker, type Period } from './components/PeriodPicker';
import { GenerationTable, exportGenerationToCSV } from './components/GenerationTable';
import { RevenueTable, exportRevenueToCSV } from './components/RevenueTable';
import { buildGenerationTableRows, buildRevenueTableRows } from './utils/tableBuilder';
import type { GenerationFilters } from './types';
import { useTheme } from '../../contexts/ThemeContext';
import { getGradientBg } from '../../utils/themeColors';
import { useResponsiveFontSize } from '../../utils/fontScaling';
import { useFilterPersistence } from '../../hooks/useFilterPersistence';
import { loadFilters, clearFilters } from '../../utils/filterPersistence';

const DASHBOARD_ID = 'generation-report';

export function GenerationReport() {
  const { theme } = useTheme();
  
  // Responsive font sizes (increased by 1.5x for filter pane and legends)
  const labelFontSize = useResponsiveFontSize(12, 18, 10.5); // For labels
  const valueFontSize = useResponsiveFontSize(15, 21, 13.5); // For values
  
  const [filters, setFilters] = useState<GenerationFilters>(() => {
    const stored = loadFilters<GenerationFilters>(DASHBOARD_ID);
    if (stored && typeof stored === 'object') {
      return stored;
    }
    // Default to full year
    const currentYear = new Date().getFullYear();
    return {
      startMonth: `${currentYear}-01`,
      endMonth: `${currentYear}-12`,
    };
  });

  // Persist filters globally for download / restore
  useFilterPersistence(DASHBOARD_ID, filters);

  // Expand all rows by default to show all data
  const [expandedGenRows, setExpandedGenRows] = useState<Set<string>>(new Set());
  const [expandedRevRows, setExpandedRevRows] = useState<Set<string>>(new Set());
  
  // Track the last filter key to detect filter changes
  const lastFilterKey = useRef<string>('');

  const { data, loading, error } = useGenerationData(filters);

  const handlePeriodChange = useCallback((period: Period) => {
    if (period.range) {
      setFilters({
        startMonth: period.range.start,
        endMonth: period.range.end,
      });
    } else if (period.month) {
      setFilters({
        startMonth: period.month,
        endMonth: period.month,
      });
    }
  }, []);

  const handleResetPeriod = useCallback(() => {
    const currentYear = new Date().getFullYear();
    setFilters({
      startMonth: `${currentYear}-01`,
      endMonth: `${currentYear}-12`,
    });
    clearFilters(DASHBOARD_ID);
  }, []);

  const generationRows = useMemo(() => {
    if (!data) {
      return [];
    }

    // Ensure all required arrays exist
    const icBudget = data.icApprovedBudgetDaily || [];
    const expBudget = data.expectedBudgetDaily || [];
    const actualGen = data.actualGenerationDaily || [];
    const budgetGii = data.budgetGIIDaily || [];
    const actualGii = data.actualGIIDaily || [];
    const yieldData = data.yieldData || [];
    const mapData = data.mapData || [];

    const rows = buildGenerationTableRows({
      icBudget,
      expBudget,
      actualGen,
      budgetGii,
      actualGii,
      yieldData,
      mapData,
      startMonth: filters.startMonth || '',
      endMonth: filters.endMonth || '',
      latestReportDate: data.latestReportDate,
    });
    
    return rows;
  }, [data, filters]);
  
  // Reset expanded state when filters change (users can manually expand rows)
  useEffect(() => {
    const filterKey = `${filters.startMonth}-${filters.endMonth}`;
    if (filterKey !== lastFilterKey.current) {
      lastFilterKey.current = filterKey;
      // Reset expanded state when filters change - use requestAnimationFrame to schedule update
      requestAnimationFrame(() => {
        setExpandedGenRows(new Set());
      });
    }
  }, [filters.startMonth, filters.endMonth]);

  const revenueRows = useMemo(() => {
    if (!data) {
      return [];
    }

    // Ensure all required arrays exist
    const icBudget = data.icApprovedBudgetDaily || [];
    const expBudget = data.expectedBudgetDaily || [];
    const actualGen = data.actualGenerationDaily || [];
    const budgetGii = data.budgetGIIDaily || [];
    const actualGii = data.actualGIIDaily || [];
    const yieldData = data.yieldData || [];
    const mapData = data.mapData || [];

    const rows = buildRevenueTableRows({
      icBudget,
      expBudget,
      actualGen,
      budgetGii,
      actualGii,
      yieldData,
      mapData,
      startMonth: filters.startMonth || '',
      endMonth: filters.endMonth || '',
      latestReportDate: data.latestReportDate,
    });
    
    return rows;
  }, [data, filters]);

  // Signal when Generation Report data + filters are ready for export/download
  useEffect(() => {
    const hasData = generationRows.length > 0 || revenueRows.length > 0;
    if (!loading && data && hasData) {
      document.body.setAttribute('data-filters-ready', 'true');
      window.dispatchEvent(
        new CustomEvent('dashboard-filters-ready', { detail: { dashboardId: DASHBOARD_ID } }),
      );
    } else {
      document.body.removeAttribute('data-filters-ready');
    }
  }, [loading, data, generationRows.length, revenueRows.length]);
  
  // Reset expanded state when filters change (users can manually expand rows)
  useEffect(() => {
    const filterKey = `${filters.startMonth}-${filters.endMonth}`;
    if (filterKey !== lastFilterKey.current) {
      lastFilterKey.current = filterKey;
      // Reset expanded state when filters change - use requestAnimationFrame to schedule update
      requestAnimationFrame(() => {
        setExpandedRevRows(new Set());
      });
    }
  }, [filters.startMonth, filters.endMonth]);

  const handleToggleGenExpand = useCallback((rowId: string) => {
    setExpandedGenRows((prev) => {
      const next = new Set(prev);
      if (next.has(rowId)) {
        next.delete(rowId);
      } else {
        next.add(rowId);
      }
      return next;
    });
  }, []);

  const handleToggleRevExpand = useCallback((rowId: string) => {
    setExpandedRevRows((prev) => {
      const next = new Set(prev);
      if (next.has(rowId)) {
        next.delete(rowId);
      } else {
        next.add(rowId);
      }
      return next;
    });
  }, []);

  const formatReportDate = (dateStr?: string): string => {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return dateStr;
    return d.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  const defaultPeriod: Period = filters.startMonth === filters.endMonth
    ? { month: filters.startMonth }
    : { range: { start: filters.startMonth || '', end: filters.endMonth || '' } };

  // Theme-aware colors
  const bgGradient = getGradientBg(theme);
  const textPrimary = theme === 'dark' ? '#f1f5f9' : '#1a1a1a';
  const textSecondary = theme === 'dark' ? '#94a3b8' : '#64748b';
  const cardBg = theme === 'dark' 
    ? 'linear-gradient(to bottom right, rgba(30, 41, 59, 0.9), rgba(51, 65, 85, 0.6))'
    : 'linear-gradient(to bottom right, rgba(255, 255, 255, 0.95), rgba(248, 250, 252, 0.9))';
  const cardBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(203, 213, 225, 0.8)';
  const accentColor = theme === 'dark' ? '#38bdf8' : '#0072ce';
  const errorBorder = theme === 'dark' ? 'rgba(248, 113, 113, 0.5)' : 'rgba(239, 68, 68, 0.5)';
  const errorBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.9)' : 'rgba(255, 255, 255, 0.95)';
  const errorText = theme === 'dark' ? '#fca5a5' : '#dc2626';
  const errorTextSecondary = theme === 'dark' ? '#f87171' : '#b91c1c';
  const loadingBg = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(226, 232, 240, 0.8)';
  const exportButtonBg = theme === 'dark' ? 'rgba(56, 189, 248, 0.2)' : 'rgba(0, 114, 206, 0.1)';
  const exportButtonText = theme === 'dark' ? '#7dd3fc' : '#0072ce';
  const exportButtonHoverBg = theme === 'dark' ? 'rgba(56, 189, 248, 0.3)' : 'rgba(0, 114, 206, 0.15)';
  
  // Responsive font sizes for buttons
  const buttonFontSize = useResponsiveFontSize(10, 14, 9);

  if (loading) {
    return (
      <div 
        className="flex size-full items-center justify-center"
        style={{ background: bgGradient }}
      >
        <div className="text-center">
          <div className="mb-4 text-lg font-medium" style={{ color: textPrimary }}>Loading generation report...</div>
          <div className="h-2 w-64 overflow-hidden rounded-full" style={{ backgroundColor: loadingBg }}>
            <div className="size-full animate-pulse" style={{ backgroundColor: accentColor }} />
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div 
        className="flex size-full items-center justify-center"
        style={{ background: bgGradient }}
      >
        <div className="rounded-lg border p-6 text-center" style={{ borderColor: errorBorder, backgroundColor: errorBg }}>
          <div className="mb-2 text-lg font-semibold" style={{ color: errorText }}>Error Loading Report</div>
          <div style={{ color: errorTextSecondary }}>{error}</div>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div 
        className="flex size-full items-center justify-center"
        style={{ background: bgGradient }}
      >
        <div className="text-center" style={{ color: textSecondary }}>No data available</div>
      </div>
    );
  }

  return (
    <div 
      className="flex w-full flex-col"
      style={{ 
        background: bgGradient,
        color: textPrimary,
        minHeight: '100%',
      }}
    >
      <div className="flex flex-col gap-2 p-2">
        {/* Filter Bar */}
        <div 
          className="shrink-0 rounded-xl border p-2 shadow-xl"
          style={{ 
            borderColor: cardBorder,
            background: cardBg
          }}
        >
          <div className="flex flex-wrap items-center gap-3">
            {/* Report Date */}
            {data.latestReportDate && (
              <div className="flex items-center gap-2">
                <span className="font-semibold uppercase tracking-wide" style={{ color: textSecondary, fontSize: `${labelFontSize}px` }}>
                  📅 Report Date:
                </span>
                <span className="font-medium" style={{ color: accentColor, fontSize: `${valueFontSize}px` }}>
                  {formatReportDate(data.latestReportDate)}
                </span>
              </div>
            )}

            {/* Period Selector */}
            <div className="flex items-center gap-2">
              <span className="font-semibold uppercase tracking-wide" style={{ color: textSecondary, fontSize: `${labelFontSize}px` }}>
                📊 Period:
              </span>
              <PeriodPicker
                defaultPeriod={defaultPeriod}
                onPeriodChange={handlePeriodChange}
                onReset={handleResetPeriod}
              />
            </div>

            {/* Legends */}
            <div className="ml-auto flex items-center gap-2">
              <span className="font-semibold uppercase tracking-wide" style={{ color: textSecondary, fontSize: `${labelFontSize}px` }}>
                Legends:
              </span>
              <div className="flex items-center gap-2">
                <div className="flex items-center gap-1">
                  <div className="h-2.5 w-5 rounded" style={{ backgroundColor: '#22c55e' }}></div>
                  <span className="font-medium" style={{ color: textPrimary, fontSize: `${labelFontSize}px` }}>Target Met</span>
                </div>
                <div className="flex items-center gap-1">
                  <div className="h-2.5 w-5 rounded" style={{ backgroundColor: '#f97316' }}></div>
                  <span className="font-medium" style={{ color: textPrimary, fontSize: `${labelFontSize}px` }}>Below</span>
                </div>
                <div className="flex items-center gap-1">
                  <div className="h-2.5 w-5 rounded" style={{ backgroundColor: '#3b82f6' }}></div>
                  <span className="font-medium" style={{ color: textPrimary, fontSize: `${labelFontSize}px` }}>Forecast</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Scrollable Tables Container */}
        <div className="flex-1 space-y-2 overflow-y-auto overflow-x-hidden">
          {/* Generation Table */}
          <div 
            className="rounded-xl border p-3 shadow-xl"
            style={{ 
              borderColor: cardBorder,
              background: cardBg
            }}
          >
            <div className="mb-2 flex items-center justify-between">
              <h2 className="text-sm font-semibold" style={{ color: accentColor }}>⚡ Generation Data</h2>
              <button
                onClick={() => exportGenerationToCSV(generationRows)}
                className="flex items-center gap-1 rounded-lg px-3 py-1.5 font-semibold transition-all hover:shadow-md"
                style={{
                  backgroundColor: exportButtonBg,
                  color: exportButtonText,
                  fontSize: `${buttonFontSize}px`,
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = exportButtonHoverBg;
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = exportButtonBg;
                }}
              >
                <svg 
                  xmlns="http://www.w3.org/2000/svg" 
                  width="12" 
                  height="12" 
                  viewBox="0 0 24 24" 
                  fill="none" 
                  stroke="currentColor" 
                  strokeWidth="2" 
                  strokeLinecap="round" 
                  strokeLinejoin="round"
                >
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                  <polyline points="7 10 12 15 17 10" />
                  <line x1="12" y1="15" x2="12" y2="3" />
                </svg>
                Export to CSV
              </button>
            </div>
            <GenerationTable
              rows={generationRows}
              onToggleExpand={handleToggleGenExpand}
              expandedRows={expandedGenRows}
              renderExportButton={false}
            />
          </div>

          {/* Revenue Table */}
          <div 
            className="rounded-xl border p-3 shadow-xl"
            style={{ 
              borderColor: cardBorder,
              background: cardBg
            }}
          >
            <div className="mb-2 flex items-center justify-between">
              <h2 className="text-sm font-semibold" style={{ color: accentColor }}>💰 Revenue Data</h2>
              <button
                onClick={() => exportRevenueToCSV(revenueRows)}
                className="flex items-center gap-1 rounded-lg px-3 py-1.5 font-semibold transition-all hover:shadow-md"
                style={{
                  backgroundColor: exportButtonBg,
                  color: exportButtonText,
                  fontSize: `${buttonFontSize}px`,
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = exportButtonHoverBg;
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = exportButtonBg;
                }}
              >
                <svg 
                  xmlns="http://www.w3.org/2000/svg" 
                  width="12" 
                  height="12" 
                  viewBox="0 0 24 24" 
                  fill="none" 
                  stroke="currentColor" 
                  strokeWidth="2" 
                  strokeLinecap="round" 
                  strokeLinejoin="round"
                >
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                  <polyline points="7 10 12 15 17 10" />
                  <line x1="12" y1="15" x2="12" y2="3" />
                </svg>
                Export to CSV
              </button>
            </div>
            <RevenueTable
              rows={revenueRows}
              onToggleExpand={handleToggleRevExpand}
              expandedRows={expandedRevRows}
              renderExportButton={false}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

