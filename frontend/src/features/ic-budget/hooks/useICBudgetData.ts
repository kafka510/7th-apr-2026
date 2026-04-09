/**
 * Generation Budget Insights - Data Hook
 * React hook for fetching and managing IC Budget data
 */
import { useState, useEffect, useCallback } from 'react';
import { fetchICBudgetData } from '../api';
import type { ICBudgetDataEntry } from '../types';

interface UseICBudgetDataReturn {
  data: ICBudgetDataEntry[];
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useICBudgetData(): UseICBudgetDataReturn {
  const [data, setData] = useState<ICBudgetDataEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const result = await fetchICBudgetData();
      setData(result.data);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch IC Budget data';
      setError(errorMessage);
      console.error('Error fetching IC Budget data:', err);
      setData([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return {
    data,
    loading,
    error,
    refetch: fetchData,
  };
}

