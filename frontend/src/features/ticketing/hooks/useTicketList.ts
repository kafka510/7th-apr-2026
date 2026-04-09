import { useCallback, useEffect, useMemo, useState } from 'react';

import { fetchTicketList, fetchTicketDashboard } from '../api';
import type {
  TicketListFilters,
  TicketListItem,
  TicketListQueryState,
  TicketListSummary,
  TicketListResponse,
  TicketDashboardSummary,
} from '../types';

export const DEFAULT_TICKET_LIST_QUERY: TicketListQueryState = {
  statuses: [],
  priorities: [],
  categories: [],
  sites: [],
  assignees: [],
  assetNumbers: [],
  page: 1,
  pageSize: 20,
};

type UseTicketListResult = {
  items: TicketListItem[];
  filters: TicketListFilters | null;
  summary: TicketListSummary | null;
  loading: boolean;
  error: string | null;
  page: number;
  totalCount: number;
  totalPages: number;
  query: TicketListQueryState;
  setQuery: (updater: (state: TicketListQueryState) => TicketListQueryState) => void;
  refresh: () => Promise<void>;
  permissions?: {
    canDelete: boolean;
  };
};

export const useTicketList = (): UseTicketListResult => {
  const [items, setItems] = useState<TicketListItem[]>([]);
  const [filters, setFilters] = useState<TicketListFilters | null>(null);
  const [summary, setSummary] = useState<TicketListSummary | null>(null);
  const [query, setQueryState] = useState<TicketListQueryState>(() => ({ ...DEFAULT_TICKET_LIST_QUERY }));
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [permissions, setPermissions] = useState<{ canDelete: boolean } | undefined>(undefined);
  const [meta, setMeta] = useState<{ count: number; pageSize: number }>({
    count: 0,
    pageSize: DEFAULT_TICKET_LIST_QUERY.pageSize,
  });

  // Extract unique asset numbers from items to populate filter if backend doesn't provide it
  const enrichedFilters = useMemo(() => {
    if (!filters) return null;
    
    // If assetNumberOptions is missing or empty, try to extract from items
    if (!filters.assetNumberOptions || filters.assetNumberOptions.length === 0) {
      const assetNumberSet = new Set<string>();
      items.forEach((item) => {
        // Priority 1: Use asset_number if available
        const assetNumber = item.asset_number?.trim();
        if (assetNumber) {
          assetNumberSet.add(assetNumber);
        }
        // Note: We don't use asset_code here because we want only asset_number
        // The backend should provide asset_number for tickets
      });
      
      const assetNumberOptions = Array.from(assetNumberSet)
        .sort()
        .map((assetNumber) => ({
          value: assetNumber,
          label: assetNumber,
        }));
      
      // Only enrich if we found asset numbers
      if (assetNumberOptions.length > 0) {
        return {
          ...filters,
          assetNumberOptions,
        };
      }
    }
    
    return filters;
  }, [filters, items]);

  // Load summary separately without any filters to show total counts
  const loadSummary = useCallback(async () => {
    try {
      // Use dashboard endpoint without filters to get unfiltered summary
      const dashboardSummary: TicketDashboardSummary = await fetchTicketDashboard(undefined);
      
      // Convert dashboard summary format to TicketListSummary format
      if (dashboardSummary && dashboardSummary.kpis && dashboardSummary.ticketsByStatus) {
        // Map ticketsByStatus to statusBreakdown array
        const statusBreakdown = Object.entries(dashboardSummary.ticketsByStatus).map(([status, count]) => {
          // Map status keys to display labels
          const statusLabels: Record<string, string> = {
            raised: 'Raised',
            in_progress: 'In Progress',
            submitted: 'Submitted',
            waiting_for_approval: 'Waiting for Approval',
            closed: 'Closed',
            reopened: 'Reopened',
            cancelled: 'Cancelled',
          };
          
          return {
            status,
            label: statusLabels[status] || status.charAt(0).toUpperCase() + status.slice(1).replace(/_/g, ' '),
            count: count || 0,
          };
        });
        
        const convertedSummary: TicketListSummary = {
          generatedAt: dashboardSummary.meta?.generatedAt || new Date().toISOString(),
          total: dashboardSummary.kpis.total_tickets || 0,
          open: dashboardSummary.kpis.open_tickets || 0,
          awaitingApproval: 0, // Not available in dashboard KPIs
          unassigned: dashboardSummary.kpis.unassigned_tickets || 0,
          critical: 0, // Not available in dashboard KPIs, could be calculated from priority if needed
          statusBreakdown,
        };
        setSummary(convertedSummary);
      }
    } catch {
      // Fallback: try ticket list endpoint with empty filters
      try {
        const summaryQuery: TicketListQueryState = {
          statuses: [],
          priorities: [],
          categories: [],
          sites: [],
          assignees: [],
          assetNumbers: [],
          page: 1,
          pageSize: 1,
        };
        const summaryResponse: TicketListResponse = await fetchTicketList(summaryQuery, undefined, false);
        if (summaryResponse.summary) {
          setSummary(summaryResponse.summary);
        }
      } catch (fallbackErr) {
        // Silently fail summary fetch - don't block the main load
        console.error('Failed to load summary:', fallbackErr);
      }
    }
  }, []);

  const load = useCallback(
    async (override?: TicketListQueryState) => {
      const currentQuery = override ?? query;
      setLoading(true);
      setError(null);

      try {
        // Fetch summary first without filters to show total counts across all tickets
        await loadSummary();
        
        // Then fetch tickets with current filters
        const response: TicketListResponse = await fetchTicketList(currentQuery, undefined, !filters);
        setItems(response.results);
        setMeta({ count: response.count, pageSize: currentQuery.pageSize });
        if (response.filterOptions) {
          setFilters(response.filterOptions);
        }
        if (response.permissions) {
          setPermissions(response.permissions);
        }
        // Don't overwrite summary with filtered summary - keep the unfiltered one
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load tickets');
      } finally {
        setLoading(false);
      }
    },
    [query, filters, loadSummary],
  );

  useEffect(() => {
    load().catch((err) => {
      console.error('Failed to load tickets', err);
    });
  }, [load]);

  const totalPages = useMemo(() => {
    if (meta.count === 0) {
      return 1;
    }
    return Math.max(1, Math.ceil(meta.count / meta.pageSize));
  }, [meta.count, meta.pageSize]);

  const paginationSafeQuery = useMemo(() => {
    if (query.page > totalPages) {
      return { ...query, page: totalPages };
    }
    return query;
  }, [query, totalPages]);

  useEffect(() => {
    if (paginationSafeQuery !== query) {
      setQueryState(paginationSafeQuery);
    }
  }, [paginationSafeQuery, query]);

  const setQuery = useCallback(
    (updater: (state: TicketListQueryState) => TicketListQueryState) => {
      setQueryState((prev) => {
        const next = updater(prev);
        return {
          ...next,
          page: Math.max(1, next.page),
          pageSize: Math.max(1, next.pageSize),
        };
      });
    },
    [],
  );

  return {
    items,
    filters: enrichedFilters,
    summary,
    loading,
    error,
    page: paginationSafeQuery.page,
    totalCount: meta.count,
    totalPages,
    query: paginationSafeQuery,
    setQuery,
    refresh: () => load(paginationSafeQuery),
    permissions,
  };
};

