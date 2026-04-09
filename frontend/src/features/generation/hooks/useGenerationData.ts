/**
 * Hook to fetch and manage generation report data
 */
import { useState, useEffect, useCallback } from 'react';
import { fetchGenerationData } from '../api';
import type { GenerationReportData, GenerationFilters } from '../types';

export function useGenerationData(filters?: GenerationFilters) {
  const [data, setData] = useState<GenerationReportData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchGenerationData(filters);
      
      // Handle both paginated and non-paginated responses
      let data: GenerationReportData | null = null;
      
      // Check if response is paginated (has 'results' and 'count' properties)
      if (result && 'results' in result && 'count' in result) {
        const paginatedResult = result as { count: number; results: unknown };
        const results = paginatedResult.results;
        
        // DRF pagination wraps the Response object, so results should be the data object itself
        if (results && typeof results === 'object' && !Array.isArray(results)) {
          // results is the data object (this is what we expect)
          data = results as GenerationReportData;
        } else if (Array.isArray(results) && results.length > 0) {
          // If results is an array, it might contain the data object
          
          // Check if the array contains data objects with the expected structure
          const firstItem = results[0];
          if (firstItem && typeof firstItem === 'object') {
            // Check if this looks like our data structure
            if ('icApprovedBudgetDaily' in firstItem || 'yieldData' in firstItem || 'mapData' in firstItem) {
              data = firstItem as GenerationReportData;
            } else {
              // The array might be one of our data arrays that got paginated
              // In this case, we need to reconstruct the data object
              // This shouldn't happen, but if it does, we'll need to handle it differently
              console.error('[useGenerationData] Unexpected pagination structure - results is an array of data items, not a single data object');
            }
          }
        }
      } else {
        // Direct response (not paginated) - result is the data object itself
        data = result as GenerationReportData;
      }
      
      // Ensure all required arrays exist to prevent undefined errors
      if (data) {
        data = {
          ...data,
          icApprovedBudgetDaily: data.icApprovedBudgetDaily || [],
          expectedBudgetDaily: data.expectedBudgetDaily || [],
          actualGenerationDaily: data.actualGenerationDaily || [],
          budgetGIIDaily: data.budgetGIIDaily || [],
          actualGIIDaily: data.actualGIIDaily || [],
          yieldData: data.yieldData || [],
          mapData: data.mapData || [],
        };
      }
      
      setData(data);
    } catch (err) {
      console.error('[useGenerationData] Error:', err);
      setError(err instanceof Error ? err.message : 'Failed to load generation report data');
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  return { data, loading, error, refetch: loadData };
}

