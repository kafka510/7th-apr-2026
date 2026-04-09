/**
 * Custom hook for fetching and managing sales dashboard data
 */
import { useState, useEffect, useCallback } from 'react';
import { fetchSalesData } from '../api';
import type { SalesData } from '../types';

export function useSalesData() {
  const [data, setData] = useState<SalesData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchSalesData();
      setData(result);
    } catch (err) {
      console.error('[useSalesData] Error:', err);
      setError(err instanceof Error ? err.message : 'Failed to load sales data');
      setData(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  return { data, loading, error, refetch: loadData };
}

