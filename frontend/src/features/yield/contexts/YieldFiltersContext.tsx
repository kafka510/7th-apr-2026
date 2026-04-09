import React from 'react';
import { useYieldFilters } from '../hooks/useYieldFilters';
import { YieldFiltersContext } from './yieldFiltersContextDef';

export function YieldFiltersProvider({ children }: { children: React.ReactNode }) {
  const filtersApi = useYieldFilters();
  
  return (
    <YieldFiltersContext.Provider value={filtersApi}>
      {children}
    </YieldFiltersContext.Provider>
  );
}

