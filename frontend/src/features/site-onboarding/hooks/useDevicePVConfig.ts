/**
 * Custom hook for managing device PV configurations
 */
import { useState, useEffect, useCallback } from 'react';
import { devicePVConfigApi } from '../api/pvModules';
import type { DevicePVConfig, BulkAssignConfig, ImportResult } from '../types/pvModules';

export const useDevicePVConfig = (assetCode?: string) => {
  const [devices, setDevices] = useState<DevicePVConfig[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchDevices = useCallback(async (
    asset?: string,
    inverterIds?: string | string[],
    jbIds?: string | string[],
    configured?: boolean,
    level: 'string' | 'inverter' = 'string'
  ) => {
    setLoading(true);
    setError(null);
    try {
      // Cast to any here to keep call-site flexible while API evolves
      const data = await (devicePVConfigApi as any).list(asset || assetCode, inverterIds, jbIds, configured, level);
      setDevices(data);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch device configurations';
      setError(errorMessage);
      console.error('Error fetching devices:', err);
    } finally {
      setLoading(false);
    }
  }, [assetCode]);

  const updateDevice = useCallback(async (deviceId: string, config: Partial<DevicePVConfig>) => {
    setLoading(true);
    setError(null);
    try {
      await devicePVConfigApi.update(deviceId, config);
      await fetchDevices(); // Refresh list
      return true;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to update device configuration';
      setError(errorMessage);
      console.error('Error updating device:', err);
      return false;
    } finally {
      setLoading(false);
    }
  }, [fetchDevices]);

  const bulkAssign = useCallback(async (deviceIds: string[], config: Partial<BulkAssignConfig>) => {
    setLoading(true);
    setError(null);
    try {
      const result = await devicePVConfigApi.bulkAssign(deviceIds, config);
      await fetchDevices(); // Refresh list
      return result;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to bulk assign configurations';
      setError(errorMessage);
      console.error('Error in bulk assign:', err);
      return null;
    } finally {
      setLoading(false);
    }
  }, [fetchDevices]);

  const importConfigs = useCallback(async (file: File): Promise<ImportResult | null> => {
    setLoading(true);
    setError(null);
    try {
      const result = await devicePVConfigApi.import(file);
      await fetchDevices(); // Refresh list
      return result;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to import configurations';
      setError(errorMessage);
      console.error('Error importing configs:', err);
      return null;
    } finally {
      setLoading(false);
    }
  }, [fetchDevices]);

  const exportConfigs = useCallback(async (asset?: string) => {
    setLoading(true);
    setError(null);
    try {
      await devicePVConfigApi.export(asset || assetCode);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to export configurations';
      setError(errorMessage);
      console.error('Error exporting configs:', err);
    } finally {
      setLoading(false);
    }
  }, [assetCode]);

  // Don't auto-fetch on mount - wait for user to select filters
  // This prevents loading thousands of strings unnecessarily
  useEffect(() => {
    if (assetCode) {
      fetchDevices(assetCode);
    }
  }, [assetCode, fetchDevices]);

  return {
    devices,
    loading,
    error,
    fetchDevices,
    updateDevice,
    bulkAssign,
    importConfigs,
    exportConfigs,
    setDevices, // Export for manual device list clearing
  };
};


