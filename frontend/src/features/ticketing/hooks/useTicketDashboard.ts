import { startTransition, useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { fetchTicketDashboard, fetchTicketFilters } from '../api';
import type { TicketDashboardFilterParams, TicketDashboardFilters, TicketDashboardSummary } from '../types';

type UseTicketDashboardState = {
  summary: TicketDashboardSummary | null;
  filters: TicketDashboardFilters | null;
  loading: boolean;
  error: string | null;
  reload: (filters?: TicketDashboardFilterParams) => Promise<void>;
};

export const useTicketDashboard = (
  params?: TicketDashboardFilterParams,
): UseTicketDashboardState => {
  const [summary, setSummary] = useState<TicketDashboardSummary | null>(null);
  const [filters, setFilters] = useState<TicketDashboardFilters | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const latestParamsRef = useRef<TicketDashboardFilterParams | undefined>(params);

  const serialisedParams = useMemo(
    () => JSON.stringify(params ?? {}),
    [params],
  );

  const load = useCallback(
    async (override?: TicketDashboardFilterParams) => {
      const effectiveParams = override ?? latestParamsRef.current;

      startTransition(() => {
        setLoading(true);
        setError(null);
      });

      try {
        const [summaryPayload, filterOptions] = await Promise.all([
          fetchTicketDashboard(effectiveParams),
          fetchTicketFilters(),
        ]);
        setSummary(summaryPayload);
        setFilters(filterOptions);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load ticket dashboard');
      } finally {
        startTransition(() => {
          setLoading(false);
        });
      }
    },
    [],
  );

  useEffect(() => {
    latestParamsRef.current = params;
  }, [serialisedParams, params]);

  useEffect(() => {
    load(params).catch((err) => {
      console.error('Failed to load ticket dashboard', err);
    });
  }, [load, serialisedParams, params]);

  return {
    summary,
    filters,
    loading,
    error,
    reload: load,
  };
};

