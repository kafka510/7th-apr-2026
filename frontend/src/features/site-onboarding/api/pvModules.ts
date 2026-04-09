/**
 * API client for PV Module management
 */
import { createJSONHeadersWithCSRF, createHeadersWithCSRF } from '../../../utils/csrf';
import type {
  PVModuleDatasheet,
  DevicePVConfig,
  BulkAssignConfig,
  ImportResult,
  PowerModel
} from '../types/pvModules';
import type { WeatherDevice } from '../types/pvModules';

const API_BASE = '/api/site-onboarding';

/**
 * PV Module Datasheet APIs
 */

export const pvModuleApi = {
  /**
   * Get list of all PV module datasheets
   */
  async list(search?: string, technology?: string): Promise<PVModuleDatasheet[]> {
    const params = new URLSearchParams();
    if (search) params.append('search', search);
    if (technology) params.append('technology', technology);
    
    const url = `${API_BASE}/pv-modules/${params.toString() ? '?' + params.toString() : ''}`;
    const response = await fetch(url);
    
    if (!response.ok) {
      throw new Error(`Failed to fetch modules: ${response.statusText}`);
    }
    
    const data = await response.json();
    return data.modules || [];
  },

  /**
   * Get single PV module datasheet details
   */
  async get(moduleId: number): Promise<PVModuleDatasheet> {
    const response = await fetch(`${API_BASE}/pv-modules/${moduleId}/`);
    
    if (!response.ok) {
      throw new Error(`Failed to fetch module: ${response.statusText}`);
    }
    
    const data = await response.json();
    return data.module;
  },

  /**
   * Create new PV module datasheet
   */
  async create(moduleData: Partial<PVModuleDatasheet>): Promise<{ module_id: number; message: string }> {
    const headers = createJSONHeadersWithCSRF();
    const response = await fetch(`${API_BASE}/pv-modules/create/`, {
      method: 'POST',
      headers,
      body: JSON.stringify(moduleData),
    });
    
    const data = await response.json();
    
    if (!response.ok || !data.success) {
      throw new Error(data.error || 'Failed to create module');
    }
    
    return data;
  },

  /**
   * Update existing PV module datasheet
   */
  async update(moduleId: number, moduleData: Partial<PVModuleDatasheet>): Promise<void> {
    const headers = createJSONHeadersWithCSRF();
    const response = await fetch(`${API_BASE}/pv-modules/update/${moduleId}/`, {
      method: 'PUT',
      headers,
      body: JSON.stringify(moduleData),
    });
    
    const data = await response.json();
    
    if (!response.ok || !data.success) {
      throw new Error(data.error || 'Failed to update module');
    }
  },

  /**
   * Delete PV module datasheet (superuser only)
   */
  async delete(moduleId: number, force: boolean = false): Promise<{ devices_unlinked: number }> {
    const url = `${API_BASE}/pv-modules/delete/${moduleId}/${force ? '?force=true' : ''}`;
    const headers = createHeadersWithCSRF();
    const response = await fetch(url, {
      method: 'DELETE',
      headers,
    });
    
    const data = await response.json();
    
    if (!response.ok || !data.success) {
      // Check if it requires confirmation
      if (data.requires_confirmation) {
        throw new Error(data.error);
      }
      throw new Error(data.error || 'Failed to delete module');
    }
    
    return { devices_unlinked: data.devices_unlinked || 0 };
  },

  /**
   * Import PV modules from CSV
   */
  async import(file: File, mode: 'create' | 'update' | 'both' = 'create'): Promise<ImportResult> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('mode', mode);
    
    const headers = createHeadersWithCSRF();
    const response = await fetch(`${API_BASE}/pv-modules/import/`, {
      method: 'POST',
      headers,
      body: formData,
    });
    
    const data = await response.json();
    
    if (!response.ok || !data.success) {
      throw new Error(data.error || 'Failed to import modules');
    }
    
    return data;
  },

  /**
   * Export PV modules to CSV
   */
  async export(): Promise<void> {
    const response = await fetch(`${API_BASE}/pv-modules/export/`);
    
    if (!response.ok) {
      throw new Error('Failed to export modules');
    }
    
    // Trigger download
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'pv_module_datasheets.csv';
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  },

  /**
   * Download CSV template for PV modules
   */
  async downloadTemplate(): Promise<void> {
    const response = await fetch(`${API_BASE}/pv-modules/download-template/`);
    
    if (!response.ok) {
      throw new Error('Failed to download template');
    }
    
    // Trigger download
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'pv_module_template.csv';
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  },
};

/**
 * Device PV Configuration APIs
 */

export const devicePVConfigApi = {
  /**
   * Get list of string devices with PV configuration (with hierarchical filtering)
   */
  async list(
    assetCode?: string,
    inverterIds?: string | string[],
    jbIds?: string | string[],
    configured?: boolean,
    level: 'string' | 'inverter' = 'string'
  ): Promise<DevicePVConfig[]> {
    const params = new URLSearchParams();
    if (assetCode) params.append('asset_code', assetCode);
    // Handle inverter_id as array or string
    if (inverterIds) {
      const invIds = Array.isArray(inverterIds) ? inverterIds.join(',') : inverterIds;
      if (invIds) params.append('inverter_id', invIds);
    }
    // Handle jb_id as array or string
    if (jbIds) {
      const jIds = Array.isArray(jbIds) ? jbIds.join(',') : jbIds;
      if (jIds) params.append('jb_id', jIds);
    }
    if (configured !== undefined) params.append('configured', configured.toString());
    if (level) params.append('level', level);
    
    const url = `${API_BASE}/device-pv-config/${params.toString() ? '?' + params.toString() : ''}`;
    const response = await fetch(url);
    
    if (!response.ok) {
      throw new Error(`Failed to fetch device configs: ${response.statusText}`);
    }
    
    const data = await response.json();
    return data.devices || [];
  },

  /**
   * Get a single device's PV configuration by device_id (loads tilt_configs from device_list).
   */
  async get(deviceId: string): Promise<DevicePVConfig | null> {
    const params = new URLSearchParams({ device_id: deviceId });
    const url = `${API_BASE}/device-pv-config/get/?${params.toString()}`;
    const response = await fetch(url);
    if (!response.ok) {
      if (response.status === 404) return null;
      throw new Error(`Failed to fetch device config: ${response.statusText}`);
    }
    const data = await response.json();
    return data.success && data.device ? data.device : null;
  },

  /**
   * Update single device PV configuration
   */
  async update(deviceId: string, config: Partial<DevicePVConfig>): Promise<void> {
    const headers = createJSONHeadersWithCSRF();
    const response = await fetch(`${API_BASE}/device-pv-config/update/`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        device_id: deviceId,
        ...config,
      }),
    });
    
    const data = await response.json();
    
    if (!response.ok || !data.success) {
      throw new Error(data.error || 'Failed to update device configuration');
    }
  },

  /**
   * Bulk assign module configuration to multiple devices
   */
  async bulkAssign(deviceIds: string[], config: Partial<BulkAssignConfig>): Promise<{ updated_count: number; failed_count: number }> {
    const headers = createJSONHeadersWithCSRF();
    const response = await fetch(`${API_BASE}/device-pv-config/bulk-assign/`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        device_ids: deviceIds,
        config,
      }),
    });
    
    const data = await response.json();
    
    if (!response.ok || !data.success) {
      throw new Error(data.error || 'Failed to bulk assign configurations');
    }
    
    return {
      updated_count: data.updated_count || 0,
      failed_count: data.failed_count || 0,
    };
  },

  /**
   * Import device PV configurations from CSV
   */
  async import(file: File): Promise<ImportResult> {
    const formData = new FormData();
    formData.append('file', file);
    
    const headers = createHeadersWithCSRF();
    const response = await fetch(`${API_BASE}/device-pv-config/import/`, {
      method: 'POST',
      headers,
      body: formData,
    });
    
    const data = await response.json();
    
    if (!response.ok || !data.success) {
      throw new Error(data.error || 'Failed to import device configurations');
    }
    
    return data;
  },

  /**
   * Export device PV configurations to CSV
   */
  async export(assetCode?: string): Promise<void> {
    const url = assetCode 
      ? `${API_BASE}/device-pv-config/export/?asset_code=${assetCode}`
      : `${API_BASE}/device-pv-config/export/`;
    
    const response = await fetch(url);
    
    if (!response.ok) {
      throw new Error('Failed to export device configurations');
    }
    
    // Trigger download
    const blob = await response.blob();
    const downloadUrl = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = downloadUrl;
    a.download = assetCode ? `device_pv_config_${assetCode}.csv` : 'device_pv_config_all.csv';
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(downloadUrl);
    document.body.removeChild(a);
  },

  /**
   * Download CSV template for device PV configuration
   */
  async downloadTemplate(): Promise<void> {
    const response = await fetch(`${API_BASE}/device-pv-config/download-template/`);
    
    if (!response.ok) {
      throw new Error('Failed to download template');
    }
    
    // Trigger download
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'device_pv_config_template.csv';
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  },
};

/**
 * Power Model APIs (Plugin Architecture)
 */

export const powerModelApi = {
  /**
   * Get list of available power calculation models
   */
  async list(): Promise<PowerModel[]> {
    const response = await fetch('/api/power-models/list/');
    
    if (!response.ok) {
      throw new Error('Failed to fetch power models');
    }
    
    const data = await response.json();
    return data.models || [];
  },
};

/**
 * Weather Device APIs
 */
export const weatherDeviceApi = {
  /**
   * Get list of weather devices for an asset
   */
  async list(assetCode: string): Promise<WeatherDevice[]> {
    if (!assetCode) {
      return [];
    }
    
    const response = await fetch(`${API_BASE}/weather-devices/?asset_code=${encodeURIComponent(assetCode)}`);
    
    if (!response.ok) {
      throw new Error(`Failed to fetch weather devices: ${response.statusText}`);
    }
    
    const data = await response.json();
    return data.devices || [];
  }
};

/**
 * Weather Metric interface
 */
export interface WeatherMetric {
  metric: string;
  oem_tag: string;
  units: string;
  description: string;
}

/**
 * Weather Metrics API
 */
export const weatherMetricsApi = {
  /**
   * Get list of unique metrics for weather devices (device_type='wst') for a specific asset
   */
  async list(assetCode: string): Promise<WeatherMetric[]> {
    if (!assetCode) {
      return [];
    }
    
    const response = await fetch(`${API_BASE}/weather-metrics/?asset_code=${encodeURIComponent(assetCode)}`);
    
    if (!response.ok) {
      throw new Error(`Failed to fetch weather metrics: ${response.statusText}`);
    }
    
    const data = await response.json();
    return data.metrics || [];
  }
};

