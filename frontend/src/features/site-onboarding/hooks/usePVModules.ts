/**
 * Custom hook for managing PV module datasheets
 */
import { useState, useEffect, useCallback } from 'react';
import { pvModuleApi } from '../api/pvModules';
import type { PVModuleDatasheet, ImportResult } from '../types/pvModules';

export const usePVModules = () => {
  const [modules, setModules] = useState<PVModuleDatasheet[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchModules = useCallback(async (search?: string, technology?: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await pvModuleApi.list(search, technology);
      setModules(data);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch modules';
      setError(errorMessage);
      console.error('Error fetching modules:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  const createModule = useCallback(async (moduleData: Partial<PVModuleDatasheet>) => {
    setLoading(true);
    setError(null);
    try {
      await pvModuleApi.create(moduleData);
      await fetchModules(); // Refresh list
      return true;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to create module';
      setError(errorMessage);
      console.error('Error creating module:', err);
      return false;
    } finally {
      setLoading(false);
    }
  }, [fetchModules]);

  const updateModule = useCallback(async (moduleId: number, moduleData: Partial<PVModuleDatasheet>) => {
    setLoading(true);
    setError(null);
    try {
      await pvModuleApi.update(moduleId, moduleData);
      await fetchModules(); // Refresh list
      return true;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to update module';
      setError(errorMessage);
      console.error('Error updating module:', err);
      return false;
    } finally {
      setLoading(false);
    }
  }, [fetchModules]);

  const deleteModule = useCallback(async (moduleId: number, force: boolean = false) => {
    setLoading(true);
    setError(null);
    try {
      await pvModuleApi.delete(moduleId, force);
      await fetchModules(); // Refresh list
      return true;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to delete module';
      setError(errorMessage);
      console.error('Error deleting module:', err);
      return false;
    } finally {
      setLoading(false);
    }
  }, [fetchModules]);

  const importModules = useCallback(async (file: File, mode: 'create' | 'update' | 'both' = 'create'): Promise<ImportResult | null> => {
    setLoading(true);
    setError(null);
    try {
      const result = await pvModuleApi.import(file, mode);
      await fetchModules(); // Refresh list
      return result;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to import modules';
      setError(errorMessage);
      console.error('Error importing modules:', err);
      return null;
    } finally {
      setLoading(false);
    }
  }, [fetchModules]);

  const exportModules = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      await pvModuleApi.export();
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to export modules';
      setError(errorMessage);
      console.error('Error exporting modules:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  // Auto-fetch on mount
  useEffect(() => {
    fetchModules();
  }, [fetchModules]);

  return {
    modules,
    loading,
    error,
    fetchModules,
    createModule,
    updateModule,
    deleteModule,
    importModules,
    exportModules,
  };
};




