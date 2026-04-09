import { useEffect, useMemo, useRef, useState } from 'react';
import { useTheme } from '../../contexts/ThemeContext';
import { AnalyticsWidget } from './components/AnalyticsWidget';
import { DashboardCharts } from './components/DashboardCharts';
import { DashboardSummaryCards } from './components/DashboardSummaryCards';
import { TicketFilters } from './components/TicketFilters';
import { useTicketDashboard } from './hooks/useTicketDashboard';
import { useFilterPersistence } from '../../hooks/useFilterPersistence';
import { loadFilters, clearFilters } from '../../utils/filterPersistence';
import type {
  RecentTicket,
  TicketDashboardFilterParams,
  TicketFilterState,
} from './types';

const DASHBOARD_ID = 'ticket-dashboard';

const RecentTickets = ({
  tickets,
  loading,
  expanded,
  onToggle,
}: {
  tickets: RecentTicket[];
  loading?: boolean;
  expanded: boolean;
  onToggle: () => void;
}) => {
  const { theme } = useTheme();
  
  const containerBg = theme === 'dark'
    ? 'linear-gradient(to bottom right, rgba(15, 23, 42, 0.9), rgba(30, 41, 59, 0.6))'
    : 'linear-gradient(to bottom right, rgba(255, 255, 255, 0.95), rgba(248, 250, 252, 0.9))';
  const containerBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(203, 213, 225, 0.8)';
  const containerShadow = theme === 'dark' 
    ? '0 20px 25px -5px rgba(0, 0, 0, 0.4)' 
    : '0 10px 15px -3px rgba(0, 0, 0, 0.1)';
  const headerBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.5)' : 'rgba(226, 232, 240, 0.8)';
  const headerText = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';
  const headerSecondaryText = theme === 'dark' ? '#94a3b8' : '#64748b';
  const toggleButtonBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.8)' : '#ffffff';
  const toggleButtonBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : 'rgba(203, 213, 225, 0.8)';
  const toggleButtonText = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';
  const toggleButtonHoverBorder = theme === 'dark' ? 'rgba(59, 130, 246, 0.5)' : '#3b82f6';
  const tableHeaderBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.8)' : 'rgba(241, 245, 249, 0.9)';
  const tableHeaderText = theme === 'dark' ? '#cbd5e1' : '#1a1a1a';
  const tableBodyBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.5)' : '#ffffff';
  const tableBodyText = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';
  const tableRowHoverBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.7)' : 'rgba(248, 250, 252, 0.9)';
  const tableDivider = theme === 'dark' ? 'rgba(51, 65, 85, 0.5)' : 'rgba(226, 232, 240, 0.8)';
  const linkColor = theme === 'dark' ? '#60a5fa' : '#0072ce';
  const linkHoverColor = theme === 'dark' ? '#93c5fd' : '#0056a3';

  if (loading) {
    return (
      <section 
        className="rounded-xl border p-4 shadow-xl"
        style={{
          borderColor: containerBorder,
          background: containerBg,
          boxShadow: containerShadow,
        }}
      >
        <div 
          className="mb-3 flex items-center justify-between border-b pb-3"
          style={{ borderColor: headerBorder }}
        >
          <h2 
            className="text-sm font-semibold uppercase tracking-wide"
            style={{ color: headerText }}
          >
            Recent Tickets
          </h2>
          <div className="flex items-center gap-2">
            <small className="text-xs" style={{ color: headerSecondaryText }}>Latest 10</small>
            <button
              type="button"
              onClick={onToggle}
              className="rounded-lg border px-2 py-1 text-xs shadow-inner transition"
              style={{
                borderColor: toggleButtonBorder,
                backgroundColor: toggleButtonBg,
                color: toggleButtonText,
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = toggleButtonHoverBorder;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = toggleButtonBorder;
              }}
            >
              {expanded ? '▼' : '▶'}
            </button>
          </div>
        </div>
        {expanded && (
          <div className="p-4">
            <p className="text-xs" style={{ color: headerSecondaryText }}>Loading recent activity…</p>
          </div>
        )}
      </section>
    );
  }

  if (!tickets.length) {
    return (
      <section 
        className="rounded-xl border p-4 shadow-xl"
        style={{
          borderColor: containerBorder,
          background: containerBg,
          boxShadow: containerShadow,
        }}
      >
        <div 
          className="mb-3 flex items-center justify-between border-b pb-3"
          style={{ borderColor: headerBorder }}
        >
          <h2 
            className="text-sm font-semibold uppercase tracking-wide"
            style={{ color: headerText }}
          >
            Recent Tickets
          </h2>
          <div className="flex items-center gap-2">
            <small className="text-xs" style={{ color: headerSecondaryText }}>Latest 10</small>
            <button
              type="button"
              onClick={onToggle}
              className="rounded-lg border px-2 py-1 text-xs shadow-inner transition"
              style={{
                borderColor: toggleButtonBorder,
                backgroundColor: toggleButtonBg,
                color: toggleButtonText,
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = toggleButtonHoverBorder;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = toggleButtonBorder;
              }}
            >
              {expanded ? '▼' : '▶'}
            </button>
          </div>
        </div>
        {expanded && (
          <div className="p-4">
            <p className="text-xs" style={{ color: headerSecondaryText }}>No ticket activity in the current filter selection.</p>
          </div>
        )}
      </section>
    );
  }

  return (
    <section 
      className="rounded-xl border p-4 shadow-xl"
      style={{
        borderColor: containerBorder,
        background: containerBg,
        boxShadow: containerShadow,
      }}
    >
      <div 
        className="mb-3 flex items-center justify-between border-b pb-3"
        style={{ borderColor: headerBorder }}
      >
        <h2 
          className="text-sm font-semibold uppercase tracking-wide"
          style={{ color: headerText }}
        >
          Recent Tickets
        </h2>
        <div className="flex items-center gap-2">
          <small className="text-xs" style={{ color: headerSecondaryText }}>Latest 10</small>
          <button
            type="button"
            onClick={onToggle}
            className="rounded-lg border px-2 py-1 text-xs shadow-inner transition"
            style={{
              borderColor: toggleButtonBorder,
              backgroundColor: toggleButtonBg,
              color: toggleButtonText,
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = toggleButtonHoverBorder;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = toggleButtonBorder;
            }}
          >
            {expanded ? '▼' : '▶'}
          </button>
        </div>
      </div>

      {expanded && (
        <div 
          className="overflow-hidden rounded-lg border"
          style={{ borderColor: tableDivider }}
        >
        <table className="min-w-full divide-y text-sm" style={{ borderColor: tableDivider }}>
          <thead style={{ backgroundColor: tableHeaderBg }}>
            <tr>
              <th 
                className="px-4 py-2 text-left text-xs font-medium uppercase tracking-wide"
                style={{ color: tableHeaderText }}
              >
                Ticket #
              </th>
              <th 
                className="px-4 py-2 text-left text-xs font-medium uppercase tracking-wide"
                style={{ color: tableHeaderText }}
              >
                Title
              </th>
              <th 
                className="px-4 py-2 text-left text-xs font-medium uppercase tracking-wide"
                style={{ color: tableHeaderText }}
              >
                Status
              </th>
              <th 
                className="px-4 py-2 text-left text-xs font-medium uppercase tracking-wide"
                style={{ color: tableHeaderText }}
              >
                Priority
              </th>
              <th 
                className="px-4 py-2 text-left text-xs font-medium uppercase tracking-wide"
                style={{ color: tableHeaderText }}
              >
                Site
              </th>
              <th 
                className="px-4 py-2 text-left text-xs font-medium uppercase tracking-wide"
                style={{ color: tableHeaderText }}
              >
                Created
              </th>
              <th 
                className="px-4 py-2 text-right text-xs font-medium uppercase tracking-wide"
                style={{ color: tableHeaderText }}
              >
                Action
              </th>
            </tr>
          </thead>
          <tbody 
            className="divide-y"
            style={{ 
              backgroundColor: tableBodyBg,
              color: tableBodyText,
              borderColor: tableDivider,
            }}
          >
            {tickets.slice(0, 10).map((ticket) => (
              <tr 
                key={`${ticket.id}-${ticket.created_at}`} 
                className="transition"
                style={{ borderColor: tableDivider }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = tableRowHoverBg;
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = tableBodyBg;
                }}
              >
                <td className="px-4 py-2">
                  <a
                    href={`/tickets/${ticket.id}/`}
                    className="text-xs font-semibold transition-colors"
                    style={{ color: linkColor }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.color = linkHoverColor;
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.color = linkColor;
                    }}
                  >
                    {ticket.ticket_number}
                  </a>
                </td>
                <td className="px-4 py-2 text-xs">{ticket.title}</td>
                <td className="px-4 py-2">
                  <span 
                    className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium"
                    style={{
                      backgroundColor: theme === 'dark' ? 'rgba(59, 130, 246, 0.2)' : 'rgba(59, 130, 246, 0.1)',
                      color: theme === 'dark' ? '#93c5fd' : '#1e40af',
                      borderColor: theme === 'dark' ? 'rgba(59, 130, 246, 0.5)' : 'rgba(59, 130, 246, 0.7)',
                    }}
                  >
                    {ticket.status_display}
                  </span>
                </td>
                <td className="px-4 py-2">
                  <span 
                    className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium"
                    style={{
                      backgroundColor: 
                        ticket.priority === 'critical' ? (theme === 'dark' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(239, 68, 68, 0.1)') :
                        ticket.priority === 'high' ? (theme === 'dark' ? 'rgba(236, 72, 153, 0.2)' : 'rgba(236, 72, 153, 0.1)') :
                        ticket.priority === 'medium' ? (theme === 'dark' ? 'rgba(249, 115, 22, 0.2)' : 'rgba(249, 115, 22, 0.1)') :
                        (theme === 'dark' ? 'rgba(51, 65, 85, 0.2)' : 'rgba(203, 213, 225, 0.3)'),
                      color: 
                        ticket.priority === 'critical' ? (theme === 'dark' ? '#fca5a5' : '#dc2626') :
                        ticket.priority === 'high' ? (theme === 'dark' ? '#f9a8d4' : '#db2777') :
                        ticket.priority === 'medium' ? (theme === 'dark' ? '#fb923c' : '#ea580c') :
                        (theme === 'dark' ? '#cbd5e1' : '#475569'),
                    }}
                  >
                    {ticket.priority_display}
                  </span>
                </td>
                <td className="px-4 py-2 text-xs" style={{ color: tableBodyText }}>{ticket.site_name || '—'}</td>
                <td className="px-4 py-2 text-xs" style={{ color: headerSecondaryText }}>{ticket.created_at}</td>
                <td className="px-4 py-2 text-right">
                  <a
                    href={`/tickets/${ticket.id}/`}
                    className="text-xs transition-colors"
                    style={{ color: linkColor }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.color = linkHoverColor;
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.color = linkColor;
                    }}
                  >
                    View
                  </a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>
      )}
    </section>
  );
};


const TicketDashboard = () => {
  const { theme } = useTheme();
  const [filterState, setFilterState] = useState<TicketFilterState>(() => {
    const stored = loadFilters<TicketFilterState & { recentExpanded?: boolean; analyticsExpanded?: boolean }>(
      DASHBOARD_ID,
    );
    if (stored && typeof stored === 'object') {
      const { recentExpanded, analyticsExpanded, ...filters } = stored;
      return filters;
    }
    return {};
  });
  const [appliedFilterState, setAppliedFilterState] = useState<TicketFilterState>(() => {
    const stored = loadFilters<TicketFilterState & { recentExpanded?: boolean; analyticsExpanded?: boolean }>(
      DASHBOARD_ID,
    );
    if (stored && typeof stored === 'object') {
      const { recentExpanded, analyticsExpanded, ...filters } = stored;
      return filters;
    }
    return {};
  });
  const [initialFiltersSet, setInitialFiltersSet] = useState<boolean>(() => {
    const stored = loadFilters<TicketFilterState & { recentExpanded?: boolean; analyticsExpanded?: boolean }>(
      DASHBOARD_ID,
    );
    if (stored && typeof stored === 'object') {
      const { recentExpanded, analyticsExpanded, ...filters } = stored;
      return Object.keys(filters).length > 0;
    }
    return false;
  });

  const [recentExpanded, setRecentExpanded] = useState<boolean>(() => {
    const stored = loadFilters<TicketFilterState & { recentExpanded?: boolean }>(DASHBOARD_ID);
    return !!stored && typeof stored === 'object' ? stored.recentExpanded === true : false;
  });

  const [analyticsExpanded, setAnalyticsExpanded] = useState<boolean>(() => {
    const stored = loadFilters<TicketFilterState & { analyticsExpanded?: boolean }>(DASHBOARD_ID);
    return !!stored && typeof stored === 'object' ? stored.analyticsExpanded === true : false;
  });

  // Create effective filters - don't send status filter if all statuses are selected
  // We'll check this after getting filterOptions, but for now send filters as-is
  // Create effective filters - exclude status filter if all statuses are selected
  // We need to check this after getting filterOptions, so we'll use a ref to track if we've already optimized
  const [hasOptimizedFilters, setHasOptimizedFilters] = useState(false);
  
  const appliedFilters = useMemo<TicketDashboardFilterParams>(() => {
    const filters: TicketDashboardFilterParams = {};
    // Only apply status filter if status is selected
    if (appliedFilterState.status) {
      const statusArray = Array.isArray(appliedFilterState.status) 
        ? appliedFilterState.status 
        : [appliedFilterState.status];
      if (statusArray.length > 0) {
        filters.status = statusArray[0];
      }
    }
    if (appliedFilterState.priority) {
      filters.priority = Array.isArray(appliedFilterState.priority) 
        ? appliedFilterState.priority[0] 
        : appliedFilterState.priority;
    }
    if (appliedFilterState.category) {
      filters.category = Array.isArray(appliedFilterState.category) 
        ? appliedFilterState.category[0] 
        : appliedFilterState.category;
    }
    if (appliedFilterState.site) {
      filters.site = Array.isArray(appliedFilterState.site) 
        ? appliedFilterState.site[0] 
        : appliedFilterState.site;
    }
    if (appliedFilterState.dateFrom) filters.dateFrom = appliedFilterState.dateFrom;
    if (appliedFilterState.dateTo) filters.dateTo = appliedFilterState.dateTo;
    return filters;
  }, [appliedFilterState]);

  // Create effective filters that exclude status if all statuses are selected
  const effectiveFilters = useMemo<TicketDashboardFilterParams>(() => {
    // If we haven't gotten filterOptions yet, return filters as-is
    if (!hasOptimizedFilters) {
      return appliedFilters;
    }
    // Check if all statuses are selected (this will be set by useEffect after filterOptions loads)
    return appliedFilters;
  }, [appliedFilters, hasOptimizedFilters]);

  const {
    summary,
    filters: filterOptions,
    loading,
    error,
    reload,
  } = useTicketDashboard(effectiveFilters);

  // Track if we've optimized filters to prevent infinite reload loops
  const optimizationKeyRef = useRef<string>('');
  const hasOptimizedFiltersRef = useRef<boolean>(false);
  
  // After getting filterOptions, optimize filters by removing status if all are selected
  useEffect(() => {
    if (filterOptions && appliedFilterState.status && !loading) {
      const statusArray = Array.isArray(appliedFilterState.status) 
        ? appliedFilterState.status 
        : [appliedFilterState.status];
      const allStatusesSelected = filterOptions.statusOptions.length > 0 
        && statusArray.length === filterOptions.statusOptions.length
        && filterOptions.statusOptions.every(opt => statusArray.includes(opt.value));
      
      // Create a unique key for this filter state
      const currentKey = JSON.stringify(appliedFilterState.status);
      
      // If all statuses are selected and we're sending a status filter, reload without it (only once per filter state)
      if (allStatusesSelected && appliedFilters.status && optimizationKeyRef.current !== currentKey) {
        optimizationKeyRef.current = currentKey;
        hasOptimizedFiltersRef.current = true;
        // Defer state update to avoid cascading renders
        setTimeout(() => {
          setHasOptimizedFilters(true);
        }, 0);
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        const { status, ...rest } = appliedFilters;
        reload(rest);
      } else if (!allStatusesSelected) {
        // Reset optimization flag when filters change
        optimizationKeyRef.current = '';
        hasOptimizedFiltersRef.current = false;
        setTimeout(() => {
          setHasOptimizedFilters(false);
        }, 0);
      }
    } else if (!appliedFilterState.status) {
      optimizationKeyRef.current = '';
      hasOptimizedFiltersRef.current = false;
      setTimeout(() => {
        setHasOptimizedFilters(false);
      }, 0);
    }
  }, [filterOptions, appliedFilterState.status, appliedFilters, reload, loading]);

  // Set default filters: select all statuses on initial load
  useEffect(() => {
    if (filterOptions && !initialFiltersSet && filterOptions.statusOptions.length > 0) {
      const allStatuses = filterOptions.statusOptions.map((opt) => opt.value);
      const defaultFilterState: TicketFilterState = {
        status: allStatuses,
      };
      // Use setTimeout to defer state updates and avoid cascading renders
      setTimeout(() => {
        setFilterState(defaultFilterState);
        setAppliedFilterState(defaultFilterState);
        setInitialFiltersSet(true);
      }, 0);
    }
  }, [filterOptions, initialFiltersSet]);

  // Persist the applied filters + UI expansion state globally for Playwright export/download
  useFilterPersistence(DASHBOARD_ID, {
    ...appliedFilterState,
    recentExpanded,
    analyticsExpanded,
  });

  const handleApplyFilters = () => {
    setAppliedFilterState(filterState);
  };

  const handleClearFilters = () => {
    if (filterOptions && filterOptions.statusOptions.length > 0) {
      const allStatuses = filterOptions.statusOptions.map((opt) => opt.value);
      const defaultFilterState: TicketFilterState = {
        status: allStatuses,
      };
      setFilterState(defaultFilterState);
      setAppliedFilterState(defaultFilterState);
    } else {
      setFilterState({});
      setAppliedFilterState({});
    }
    clearFilters(DASHBOARD_ID);
  };

  // Signal when Ticket Dashboard data + filters are ready for export/download
  useEffect(() => {
    const hasData =
      !!summary &&
      (!!summary.recentTickets?.length ||
        !!summary.kpis ||
        !!summary.charts);

    if (!loading && hasData) {
      document.body.setAttribute('data-filters-ready', 'true');
      window.dispatchEvent(
        new CustomEvent('dashboard-filters-ready', { detail: { dashboardId: DASHBOARD_ID } }),
      );
    } else {
      document.body.removeAttribute('data-filters-ready');
    }
  }, [loading, summary]);

  const textColor = theme === 'dark' ? '#f1f5f9' : '#1a1a1a';
  
  return (
    <div 
      className="flex w-full flex-col"
      style={{
        background: theme === 'dark' 
          ? 'linear-gradient(to bottom right, #0f172a, #1e293b, #0f172a)'
          : 'linear-gradient(to bottom right, #f8fbff, #ffffff, #f8fbff)',
        color: textColor,
        transition: 'background 0.3s ease, color 0.3s ease',
        minHeight: '100%',
      }}
    >
      <div className="flex-1">
      <main className="mx-auto flex max-w-full flex-col gap-4 p-4">
        {error ? (
          <div 
            className="rounded-xl border p-4 text-sm shadow-xl"
            style={{
              borderColor: theme === 'dark' ? 'rgba(248, 113, 113, 0.5)' : '#fecaca',
              background: theme === 'dark' ? 'rgba(127, 29, 29, 0.3)' : '#fef2f2',
              color: theme === 'dark' ? '#fca5a5' : '#991b1b',
              boxShadow: theme === 'dark' 
                ? '0 20px 25px -5px rgba(0, 0, 0, 0.4)' 
                : '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
            }}
          >
            Failed to load dashboard data: {error}
          </div>
        ) : null}

        {/* Filter Container with Apply/Clear buttons */}
        <div>
          <TicketFilters
            state={filterState}
            options={filterOptions}
            disabled={loading}
            onReset={handleClearFilters}
            onChange={(changes) =>
              setFilterState((prev) => {
                const next: TicketFilterState = { ...prev, ...changes };
                (Object.keys(next) as Array<keyof TicketFilterState>).forEach((key) => {
                  if (!next[key]) {
                    delete next[key];
                  }
                });
                return next;
              })
            }
            onApply={handleApplyFilters}
          />
        </div>

        {/* Summary Cards */}
        <DashboardSummaryCards 
          kpis={summary?.kpis ?? null} 
          statusData={summary?.charts?.status ?? null}
          loading={loading} 
        />

        {/* Summary Cards with Charts */}
        {summary?.charts && (
          <DashboardCharts
            statusData={summary.charts.status}
            priorityData={summary.charts.priority}
            categoryData={summary.charts.category}
            loading={loading}
            totalTickets={summary.kpis.total_tickets}
            overdueTickets={summary.kpis.overdue_tickets}
          />
        )}

        {/* Recent Tickets Table */}
        <RecentTickets
          tickets={summary?.recentTickets ?? []}
          loading={loading}
          expanded={recentExpanded}
          onToggle={() => setRecentExpanded((prev) => !prev)}
        />

        {/* Device-Tickets Analytics Widget */}
        <AnalyticsWidget
          filters={appliedFilters}
          loading={loading}
          expanded={analyticsExpanded}
          onExpandedChange={setAnalyticsExpanded}
        />
      </main>
      </div>
    </div>
  );
};

export default TicketDashboard;

