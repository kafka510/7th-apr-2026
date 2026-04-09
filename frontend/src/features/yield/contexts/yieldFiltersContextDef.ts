import { createContext } from 'react';
import { useYieldFilters } from '../hooks/useYieldFilters';

export type YieldFiltersContextType = ReturnType<typeof useYieldFilters>;

export const YieldFiltersContext = createContext<YieldFiltersContextType | null>(null);

