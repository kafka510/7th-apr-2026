import { useEffect, useMemo, useState } from 'react';
import { useTheme } from '../../contexts/ThemeContext';
import { bulkDeleteTickets } from './api';
import { PaginationControls } from './components/PaginationControls';
import { TicketListControls } from './components/TicketListControls';
import { TicketListSummary } from './components/TicketListSummary';
import { TicketTable } from './components/TicketTable';
import { DEFAULT_TICKET_LIST_QUERY, useTicketList } from './hooks/useTicketList';
import { useFilterPersistence } from '../../hooks/useFilterPersistence';
import { loadFilters, clearFilters } from '../../utils/filterPersistence';
import type { TicketListQueryState } from './types';

const DASHBOARD_ID = 'ticket-list';

const TicketList = () => {
  const {
    items,
    filters,
    summary,
    loading,
    error,
    page,
    totalPages,
    totalCount,
    query,
    setQuery,
    refresh,
    permissions,
  } = useTicketList();
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [deleting, setDeleting] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [summaryExpanded, setSummaryExpanded] = useState(false);
  const [filtersExpanded, setFiltersExpanded] = useState(false);

  const canDelete = permissions?.canDelete ?? false;

  const tableSort = useMemo(() => ({ sort: query.sort, order: query.order ?? 'asc' }), [query.order, query.sort]);

  // Load any previously persisted filters/query + UI state on mount
  useEffect(() => {
    const stored = loadFilters<
      TicketListQueryState & { summaryExpanded?: boolean; filtersExpanded?: boolean }
    >(DASHBOARD_ID);
    if (stored && typeof stored === 'object' && Object.keys(stored).length > 0) {
      const { summaryExpanded: storedSummaryExpanded, filtersExpanded: storedFiltersExpanded, ...storedQuery } = stored;

      if (Object.keys(storedQuery).length > 0) {
        setQuery((prev) => ({
          ...prev,
          ...storedQuery,
        }));
      }

      if (typeof storedSummaryExpanded === 'boolean') {
        setSummaryExpanded(storedSummaryExpanded);
      }
      if (typeof storedFiltersExpanded === 'boolean') {
        setFiltersExpanded(storedFiltersExpanded);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Persist current query (filters) + UI expansion state globally for Playwright export/download
  useFilterPersistence(DASHBOARD_ID, {
    ...query,
    summaryExpanded,
    filtersExpanded,
  });

  const handleSortChange = (sortKey: string, order: 'asc' | 'desc') => {
    setQuery((state) => ({
      ...state,
      sort: sortKey,
      order,
      page: 1,
    }));
  };

  const handleRowClick = (ticketId: string) => {
    window.location.href = `/tickets/${ticketId}/`;
  };

  const handleStatusFilter = (statuses: string[] | null) => {
    setQuery((state) => ({
      ...state,
      statuses: statuses ?? [],
      page: 1,
    }));
  };

  const handleResetFilters = () => {
    setQuery((state) => ({
      ...DEFAULT_TICKET_LIST_QUERY,
      pageSize: state.pageSize,
    }));
    setSelectedIds(new Set());
    clearFilters(DASHBOARD_ID);
  };

  const handleSelectChange = (ticketId: string, selected: boolean) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (selected) {
        next.add(ticketId);
      } else {
        next.delete(ticketId);
      }
      return next;
    });
  };

  const handleBulkDelete = async () => {
    if (selectedIds.size === 0 || !canDelete) {
      return;
    }

    if (
      !window.confirm(
        `Are you sure you want to delete ${selectedIds.size} ticket(s)? This action cannot be undone.`,
      )
    ) {
      return;
    }

    setDeleting(true);
    try {
      await bulkDeleteTickets(Array.from(selectedIds));
      setSelectedIds(new Set());
      await refresh();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete tickets');
    } finally {
      setDeleting(false);
    }
  };

  const handleExportCSV = () => {
    if (exporting) {
      return;
    }

    setExporting(true);
    
    try {
      // Build query parameters for export
      const params = new URLSearchParams();
      params.append('export', '1');
      
      // Add all current filters
      query.statuses.forEach(status => params.append('status', status));
      query.priorities.forEach(priority => params.append('priority', priority));
      query.categories.forEach(category => params.append('category', category));
      query.sites.forEach(site => params.append('asset_code', site));
      query.assignees.forEach(assignee => params.append('assigned_to', assignee));
      query.assetNumbers.forEach(assetNum => params.append('asset_number', assetNum));
      
      if (query.dateFrom) params.append('date_from', query.dateFrom);
      if (query.dateTo) params.append('date_to', query.dateTo);
      if (query.search) params.append('search', query.search);
      if (query.sort) params.append('sort', query.sort);
      if (query.order) params.append('order', query.order);

      const exportUrl = `/tickets/?${params.toString()}`;
      
      // Navigate directly to the export URL
      // Since Django returns Content-Disposition: attachment, it will download without navigating away
      window.location.href = exportUrl;
      
      // Reset exporting state after a short delay
      setTimeout(() => {
        setExporting(false);
      }, 1000);
      
    } catch {
      setExporting(false);
    }
  };

  const { theme } = useTheme();
  const bgGradient = theme === 'dark'
    ? 'linear-gradient(to bottom right, #0f172a, #1e293b, #0f172a)'
    : 'linear-gradient(to bottom right, #f8fbff, #ffffff, #f8fbff)';
  const textColor = theme === 'dark' ? '#f1f5f9' : '#1a1a1a';
  const containerBg = theme === 'dark'
    ? 'linear-gradient(to bottom right, rgba(15, 23, 42, 0.9), rgba(30, 41, 59, 0.6), rgba(15, 23, 42, 0.9))'
    : 'linear-gradient(to bottom right, rgba(255, 255, 255, 0.95), rgba(248, 250, 252, 0.9), rgba(255, 255, 255, 0.95))';
  const containerBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(203, 213, 225, 0.8)';
  const containerShadow = theme === 'dark' 
    ? '0 20px 25px -5px rgba(0, 0, 0, 0.4)' 
    : '0 10px 15px -3px rgba(0, 0, 0, 0.1)';
  const sectionHeaderText = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';
  const sectionHeaderBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.7)' : 'rgba(241, 245, 249, 0.9)';
  const errorBg = theme === 'dark' ? 'rgba(127, 29, 29, 0.3)' : '#fef2f2';
  const errorBorder = theme === 'dark' ? 'rgba(248, 113, 113, 0.5)' : '#fecaca';
  const errorText = theme === 'dark' ? '#fca5a5' : '#991b1b';
  const bulkActionBg = theme === 'dark' 
    ? 'linear-gradient(to bottom right, rgba(14, 165, 233, 0.4), rgba(59, 130, 246, 0.3))' 
    : 'linear-gradient(to bottom right, rgba(59, 130, 246, 0.15), rgba(59, 130, 246, 0.1))';
  const bulkActionBorder = theme === 'dark' ? 'rgba(59, 130, 246, 0.5)' : 'rgba(59, 130, 246, 0.7)';
  const bulkActionText = theme === 'dark' ? '#93c5fd' : '#1e40af';

  // Signal when Ticket List data + filters are ready for export/download
  useEffect(() => {
    const hasData = items.length > 0 || !!summary;

    if (!loading && hasData) {
      document.body.setAttribute('data-filters-ready', 'true');
      window.dispatchEvent(
        new CustomEvent('dashboard-filters-ready', { detail: { dashboardId: DASHBOARD_ID } }),
      );
    } else {
      document.body.removeAttribute('data-filters-ready');
    }
  }, [loading, items.length, summary]);

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
        {error ? (
          <div 
            className="rounded-xl border p-3 text-xs shadow-xl"
            style={{
              borderColor: errorBorder,
              background: errorBg,
              color: errorText,
              boxShadow: containerShadow,
            }}
          >
            Failed to load tickets: {error}
          </div>
        ) : null}

        {/* Summary Cards Container with Toggle */}
        <div 
          className="rounded-xl border shadow-xl"
          style={{
            borderColor: containerBorder,
            background: containerBg,
            boxShadow: containerShadow,
          }}
        >
          <button
            type="button"
            onClick={() => setSummaryExpanded(!summaryExpanded)}
            className="flex w-full items-center justify-between rounded-xl px-3 py-2 text-left transition"
            style={{
              color: sectionHeaderText,
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = sectionHeaderBg;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = 'transparent';
            }}
          >
            <span className="text-xs font-semibold uppercase tracking-wide">Summary Cards</span>
            <svg
              className={`size-3 transition-transform ${summaryExpanded ? 'rotate-180' : ''}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              style={{ color: theme === 'dark' ? '#94a3b8' : '#64748b' }}
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          {summaryExpanded && (
            <div className="px-2 pb-2">
              <TicketListSummary
                summary={summary}
                loading={loading && !summary}
                activeStatuses={query.statuses}
                onStatusFilter={handleStatusFilter}
              />
            </div>
          )}
        </div>

        {/* Filters Container with Toggle */}
        <div 
          className="rounded-xl border shadow-xl"
          style={{
            borderColor: containerBorder,
            background: containerBg,
            boxShadow: containerShadow,
          }}
        >
          <button
            type="button"
            onClick={() => setFiltersExpanded(!filtersExpanded)}
            className="flex w-full items-center justify-between rounded-xl px-3 py-2 text-left transition"
            style={{
              color: sectionHeaderText,
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = sectionHeaderBg;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = 'transparent';
            }}
          >
            <span className="text-xs font-semibold uppercase tracking-wide">Filters</span>
            <svg
              className={`size-3 transition-transform ${filtersExpanded ? 'rotate-180' : ''}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              style={{ color: theme === 'dark' ? '#94a3b8' : '#64748b' }}
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          {filtersExpanded && (
            <div className="px-2 pb-2">
              <TicketListControls
                filters={filters}
                query={query}
                disabled={loading}
                loading={loading}
                onChange={setQuery}
                onRefresh={refresh}
                onReset={handleResetFilters}
                onExportCSV={handleExportCSV}
              />
            </div>
          )}
        </div>

        {canDelete && selectedIds.size > 0 && (
          <div 
            className="flex items-center justify-between rounded-xl border px-3 py-2 shadow-xl"
            style={{
              borderColor: bulkActionBorder,
              background: bulkActionBg,
              boxShadow: containerShadow,
            }}
          >
            <span 
              className="text-xs font-semibold"
              style={{ color: bulkActionText }}
            >
              {selectedIds.size} ticket(s) selected
            </span>
            <button
              type="button"
              onClick={handleBulkDelete}
              disabled={deleting || loading}
              className="rounded-lg border px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-white shadow-lg transition disabled:cursor-not-allowed disabled:opacity-50"
              style={{
                borderColor: theme === 'dark' ? 'rgba(239, 68, 68, 0.5)' : 'rgba(220, 38, 38, 0.7)',
                backgroundColor: theme === 'dark' ? 'rgba(239, 68, 68, 0.8)' : '#dc2626',
              }}
              onMouseEnter={(e) => {
                if (!deleting && !loading) {
                  e.currentTarget.style.backgroundColor = theme === 'dark' ? 'rgba(220, 38, 38, 0.9)' : '#b91c1c';
                }
              }}
              onMouseLeave={(e) => {
                if (!deleting && !loading) {
                  e.currentTarget.style.backgroundColor = theme === 'dark' ? 'rgba(239, 68, 68, 0.8)' : '#dc2626';
                }
              }}
            >
              {deleting ? 'Deleting...' : `Delete ${selectedIds.size} ticket(s)`}
            </button>
          </div>
        )}

        <TicketTable
          items={items}
          loading={loading}
          sort={tableSort.sort}
          order={tableSort.order}
          onSortChange={handleSortChange}
          onRowClick={(ticket) => handleRowClick(ticket.id)}
          selectedIds={selectedIds}
          onSelectChange={handleSelectChange}
          canDelete={canDelete}
          page={page}
          pageSize={query.pageSize}
          filters={filters}
        />

        <PaginationControls
          page={page}
          totalPages={totalPages}
          totalCount={totalCount}
          pageSize={query.pageSize}
          onPageChange={(nextPage) =>
            setQuery((state) => ({
              ...state,
              page: nextPage,
            }))
          }
          onPageSizeChange={(pageSize) =>
            setQuery((state) => ({
              ...state,
              pageSize,
              page: 1,
            }))
          }
        />
      </main>
    </div>
  );
};

export default TicketList;

