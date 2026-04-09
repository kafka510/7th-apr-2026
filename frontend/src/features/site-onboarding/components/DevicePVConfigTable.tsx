/**
 * Device PV Configuration Table Component
 * Displays and manages PV configuration for string devices
 */
import React, { useState } from 'react';
import { useDevicePVConfig } from '../hooks/useDevicePVConfig';
import { BulkAssignModal } from './BulkAssignModal';
import { DeviceConfigImportModal } from './DeviceConfigImportModal';
import { DevicePVConfigModal } from './DevicePVConfigModal';
import { InverterPVConfigModal } from './InverterPVConfigModal';
import { HierarchicalFilter } from './HierarchicalFilter';
import type { FilterState } from './HierarchicalFilter';
import { devicePVConfigApi } from '../api/pvModules';
import type { BulkAssignConfig, DevicePVConfig } from '../types/pvModules';

interface DevicePVConfigTableProps {
  selectedAsset: string;
  onAssetChange: (asset: string) => void;
  onConfigChange: () => void;
}

export const DevicePVConfigTable: React.FC<DevicePVConfigTableProps> = ({
  selectedAsset,
  onAssetChange,
  onConfigChange,
}) => {
  const { devices, loading, error, bulkAssign, importConfigs, exportConfigs, fetchDevices, setDevices } = useDevicePVConfig();
  const [viewLevel, setViewLevel] = useState<'string' | 'inverter'>('string');
  const [selectedDevices, setSelectedDevices] = useState<string[]>([]);
  const [filterConfigured, setFilterConfigured] = useState<'all' | 'configured' | 'unconfigured'>('all');
  const [bulkAssignModalOpen, setBulkAssignModalOpen] = useState(false);
  const [importModalOpen, setImportModalOpen] = useState(false);
  const [configModalOpen, setConfigModalOpen] = useState(false);
  const [inverterConfigModalOpen, setInverterConfigModalOpen] = useState(false);
  const [editingDevice, setEditingDevice] = useState<DevicePVConfig | null>(null);
  const [hierarchicalFilters, setHierarchicalFilters] = useState<FilterState>({ level: 'asset' });
  
  const handleFilterChange = (filters: FilterState) => {
    setHierarchicalFilters(filters);
    
    if (viewLevel === 'string') {
      // Only fetch devices when we reach the final level (strings)
      // This prevents loading thousands of strings prematurely
      if (filters.level === 'string') {
        fetchDevices(filters.asset_code, filters.inverter_ids, filters.jb_ids, undefined, 'string');
      } else {
        // Clear devices to show the "Please Select Filters" message
        setDevices([]);
      }
    } else if (viewLevel === 'inverter') {
      // In inverter view we care mainly about the asset; fetch all inverters for that asset
      if (filters.asset_code) {
        fetchDevices(filters.asset_code, undefined, undefined, undefined, 'inverter');
      } else {
        setDevices([]);
      }
    }
    
    onAssetChange(filters.asset_code || '');
  };

  const handleBulkAssign = async (config: Partial<BulkAssignConfig>) => {
    const result = await bulkAssign(selectedDevices, config);
    if (result) {
      onConfigChange();
      setSelectedDevices([]); // Clear selection after successful assignment
      // Transform the result to match the expected format
      return {
        success: result.updated_count,
        failed: result.failed_count,
      };
    }
    return null;
  };

  const handleImport = async (file: File) => {
    const result = await importConfigs(file);
    if (result) onConfigChange();
    return result;
  };

  const handleDownloadTemplate = async () => {
    await devicePVConfigApi.downloadTemplate();
  };

  const handleExport = async () => {
    await exportConfigs(selectedAsset);
  };

  const handleSelectAll = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.checked) {
      setSelectedDevices(filteredDevices.map(d => d.device_id));
    } else {
      setSelectedDevices([]);
    }
  };

  const handleSelectDevice = (deviceId: string, checked: boolean) => {
    if (checked) {
      setSelectedDevices(prev => [...prev, deviceId]);
    } else {
      setSelectedDevices(prev => prev.filter(id => id !== deviceId));
    }
  };
  
  const handleConfigureDevice = (device: DevicePVConfig) => {
    setEditingDevice(device);
    if (viewLevel === 'inverter') {
      setInverterConfigModalOpen(true);
    } else {
      setConfigModalOpen(true);
    }
  };
  
  const handleSaveDeviceConfig = async (deviceId: string, config: Partial<DevicePVConfig>) => {
    try {
      await devicePVConfigApi.update(deviceId, config);
      onConfigChange();
      return true;
    } catch (error) {
      window.alert(`Failed to save configuration: ${error instanceof Error ? error.message : 'Unknown error'}`);
      return false;
    }
  };

  const handleSaveInverterConfig = async (deviceId: string, config: Partial<DevicePVConfig>) => {
    try {
      await devicePVConfigApi.update(deviceId, config);
      // Refresh inverter list for current asset
      if (hierarchicalFilters.asset_code) {
        await fetchDevices(hierarchicalFilters.asset_code, undefined, undefined, undefined, 'inverter');
      }
      onConfigChange();
      return true;
    } catch (error) {
      window.alert(`Failed to save inverter configuration: ${error instanceof Error ? error.message : 'Unknown error'}`);
      return false;
    }
  };

  // Filter devices based on configuration status (string view only)
  const filteredDevices = devices.filter(device => {
    if (viewLevel === 'inverter') {
      // Simple configured filter: presence of tilt_configs
      if (filterConfigured === 'configured') return Array.isArray(device.tilt_configs) && device.tilt_configs.length > 0;
      if (filterConfigured === 'unconfigured') return !device.tilt_configs || device.tilt_configs.length === 0;
      return true;
    }
    if (filterConfigured === 'configured') return device.module_datasheet_id;
    if (filterConfigured === 'unconfigured') return !device.module_datasheet_id;
    return true;
  });

  const configuredCount = devices.filter(d => {
    if (viewLevel === 'inverter') {
      return Array.isArray(d.tilt_configs) && d.tilt_configs.length > 0;
    }
    return d.module_datasheet_id;
  }).length;
  const unconfiguredCount = devices.length - configuredCount;

  return (
    <div className="device-pv-config-table rounded bg-white p-4 shadow">
      <div className="mb-4">
        <h3 className="text-dark mb-3 text-xl font-semibold">⚙️ Device Configuration</h3>
        
        {/* Hierarchical Filter */}
        <HierarchicalFilter onFilterChange={handleFilterChange} />
      </div>

      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-700">View:</span>
          <div className="btn-group btn-group-sm" role="group" aria-label="View level">
            <button
              type="button"
              className={`btn ${viewLevel === 'string' ? 'btn-primary' : 'btn-outline-secondary'}`}
              onClick={() => {
                setViewLevel('string');
                setDevices([]);
              }}
            >
              Strings
            </button>
            <button
              type="button"
              className={`btn ${viewLevel === 'inverter' ? 'btn-primary' : 'btn-outline-secondary'}`}
              onClick={() => {
                setViewLevel('inverter');
                setDevices([]);
                if (hierarchicalFilters.asset_code) {
                  fetchDevices(hierarchicalFilters.asset_code, undefined, undefined, undefined, 'inverter');
                }
              }}
            >
              Inverters
            </button>
          </div>
        </div>
        <div className="flex gap-2">
          <button 
            className="btn btn-primary"
            onClick={() => setBulkAssignModalOpen(true)}
            disabled={selectedDevices.length === 0}
          >
            🔧 Bulk Assign ({selectedDevices.length})
          </button>
          <button 
            className="btn btn-outline-secondary"
            onClick={() => setImportModalOpen(true)}
          >
            📥 Import CSV
          </button>
          <button 
            className="btn btn-outline-secondary"
            onClick={handleExport}
          >
            📤 Export CSV
          </button>
        </div>
      </div>

      {/* Help Banner */}
      <div className="border-start border-primary bg-light mb-4 rounded-lg border-4 p-3">
        <p className="text-dark fw-semibold mb-2">💡 How to Use:</p>
        <ul className="text-dark mb-0 text-sm">
          <li><strong>Step 1:</strong> Select Asset → Inverter → JB (if applicable) to filter devices</li>
          <li><strong>Step 2:</strong> Configure individual devices or select multiple for bulk assignment</li>
          <li><strong>Tip:</strong> Use hierarchical filters to manage thousands of strings efficiently</li>
        </ul>
      </div>

      {/* Summary Stats */}
      <div className="mb-4 flex gap-4">
        <div className="rounded bg-green-50 px-4 py-2">
          <span className="text-sm font-medium text-green-700">
            ✓ Configured: {configuredCount}
          </span>
        </div>
        <div className="rounded bg-yellow-50 px-4 py-2">
          <span className="text-sm font-medium text-yellow-700">
            ⋯ Pending: {unconfiguredCount}
          </span>
        </div>
        <div className="ml-auto flex gap-2">
          <button
            className={`btn btn-sm ${filterConfigured === 'all' ? 'btn-primary' : 'btn-outline-secondary'}`}
            onClick={() => setFilterConfigured('all')}
          >
            All
          </button>
          <button
            className={`btn btn-sm ${filterConfigured === 'configured' ? 'btn-primary' : 'btn-outline-secondary'}`}
            onClick={() => setFilterConfigured('configured')}
          >
            Configured
          </button>
          <button
            className={`btn btn-sm ${filterConfigured === 'unconfigured' ? 'btn-primary' : 'btn-outline-secondary'}`}
            onClick={() => setFilterConfigured('unconfigured')}
          >
            Unconfigured
          </button>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="mb-4 rounded bg-red-50 p-3 text-red-700">
          {error}
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="py-8 text-center">
          <div className="text-gray-500">Loading devices...</div>
        </div>
      )}

      {/* Devices Table */}
      {!loading && !error && (
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="table-light">
              <tr>
                <th className="p-2">
                  <input
                    type="checkbox"
                    checked={selectedDevices.length === filteredDevices.length && filteredDevices.length > 0}
                    onChange={handleSelectAll}
                  />
                </th>
                <th className="fw-semibold text-dark p-2 text-left text-sm">Device ID</th>
                <th className="fw-semibold text-dark p-2 text-left text-sm">Device Name</th>
                <th className="fw-semibold text-dark p-2 text-left text-sm">Module Type</th>
                <th className="fw-semibold text-dark p-2 text-left text-sm"># Modules</th>
                <th className="fw-semibold text-dark p-2 text-left text-sm">Rated Power</th>
                <th className="fw-semibold text-dark p-2 text-left text-sm">Installation</th>
                <th className="fw-semibold text-dark p-2 text-left text-sm">Tilt/Azimuth</th>
                <th className="fw-semibold text-dark p-2 text-center text-sm">Status</th>
                <th className="fw-semibold text-dark p-2 text-center text-sm">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredDevices.map(device => (
                <tr key={device.device_id} className="border-t hover:bg-gray-50">
                  <td className="p-2">
                    <input
                      type="checkbox"
                      checked={selectedDevices.includes(device.device_id)}
                      onChange={(e) => handleSelectDevice(device.device_id, e.target.checked)}
                    />
                  </td>
                  <td className="text-dark p-2 text-sm">{device.device_id}</td>
                  <td className="text-dark p-2 text-sm">{device.device_name}</td>
                  <td className="text-dark p-2 text-sm">
                    {device.module_model ? (
                      <div>
                        <div className="font-medium">{device.module_model}</div>
                        <div className="text-xs text-gray-500">{device.manufacturer}</div>
                      </div>
                    ) : (
                      <span className="italic text-gray-400">Not assigned</span>
                    )}
                  </td>
                  <td className="text-dark p-2 text-sm">{device.modules_in_series || '-'}</td>
                  <td className="text-dark p-2 text-sm">
                    {device.string_rated_power ? `${(device.string_rated_power / 1000).toFixed(1)} kW` : '-'}
                  </td>
                  <td className="text-dark p-2 text-sm">{device.installation_date || '-'}</td>
                  <td className="text-dark p-2 text-sm">
                    {device.tilt_angle && device.azimuth_angle
                      ? `${device.tilt_angle}° / ${device.azimuth_angle}°`
                      : '-'}
                  </td>
                  <td className="p-2 text-center">
                    {device.module_datasheet_id ? (
                      <span className="rounded-full bg-green-100 px-2 py-1 text-xs text-green-700">
                        ✓ Configured
                      </span>
                    ) : (
                      <span className="rounded-full bg-yellow-100 px-2 py-1 text-xs text-yellow-700">
                        ⋯ Pending
                      </span>
                    )}
                  </td>
                  <td className="p-2 text-center">
                    <button
                      className="btn btn-sm btn-outline-primary"
                      onClick={() => handleConfigureDevice(device)}
                      title={device.module_datasheet_id ? 'Edit PV Configuration' : 'Configure PV Module'}
                    >
                      {device.module_datasheet_id ? '✏️ Edit' : '⚙️ Configure'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && filteredDevices.length === 0 && !hierarchicalFilters.asset_code && (
        <div className="border-info bg-light rounded border-2 border-dashed p-8 text-center">
          <h4 className="text-dark fw-bold mb-3">👆 Please Select Filters Above</h4>
          <p className="text-dark mb-0">
            Use the hierarchical filters to navigate: Asset → Inverter → JB → Strings
            <br />
            <small className="text-muted">This prevents loading thousands of devices at once</small>
          </p>
        </div>
      )}
      
      {!loading && !error && filteredDevices.length === 0 && hierarchicalFilters.asset_code && (
        <div className="py-8 text-center text-gray-500">
          <p>No string devices found with current filters.</p>
          <p className="mt-2 text-sm">
            {filterConfigured !== 'all' 
              ? `No ${filterConfigured} devices to display.` 
              : 'Select an asset to view and configure devices.'}
          </p>
        </div>
      )}

      {/* Bulk Assign Modal */}
      <BulkAssignModal
        isOpen={bulkAssignModalOpen}
        onClose={() => setBulkAssignModalOpen(false)}
        onAssign={handleBulkAssign}
        selectedDeviceIds={selectedDevices}
      />

      {/* Import Modal */}
      <DeviceConfigImportModal
        isOpen={importModalOpen}
        onClose={() => setImportModalOpen(false)}
        onImport={handleImport}
        onDownloadTemplate={handleDownloadTemplate}
      />

      {/* Individual Device Configuration Modal */}
      <DevicePVConfigModal
        isOpen={configModalOpen}
        onClose={() => {
          setConfigModalOpen(false);
          setEditingDevice(null);
        }}
        onSave={handleSaveDeviceConfig}
        device={editingDevice}
      />

      {/* Inverter Configuration Modal */}
      <InverterPVConfigModal
        isOpen={inverterConfigModalOpen}
        onClose={() => {
          setInverterConfigModalOpen(false);
          setEditingDevice(null);
        }}
        onSave={handleSaveInverterConfig}
        device={editingDevice}
      />
    </div>
  );
};

