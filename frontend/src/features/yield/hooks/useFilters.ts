import { useContext } from 'react';
import { YieldFiltersContext, type YieldFiltersContextType } from '../contexts/yieldFiltersContextDef';

export function useFilters(): YieldFiltersContextType {
  const context = useContext(YieldFiltersContext);
  if (!context) {
    throw new Error('useFilters must be used within YieldFiltersProvider');
  }
  return context;
}

