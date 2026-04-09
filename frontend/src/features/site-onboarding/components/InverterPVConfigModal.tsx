/**
 * Inverter PV Configuration Modal
 * Modal for configuring inverter-level SDM groups (tilt_configs),
 * weather_device_config and power_model_id.
 */
import React, { useEffect, useState } from 'react';
import { devicePVConfigApi, powerModelApi } from '../api/pvModules';
import { WeatherDeviceSelector } from './WeatherDeviceSelector';
import { usePVModules } from '../hooks/usePVModules';
import type { DevicePVConfig, InverterTiltConfig, PowerModel } from '../types/pvModules';

interface InverterPVConfigModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (deviceId: string, config: Partial<DevicePVConfig>) => Promise<boolean>;
  device: DevicePVConfig | null;
}

export const InverterPVConfigModal: React.FC<InverterPVConfigModalProps> = ({
  isOpen,
  onClose,
  onSave,
  device,
}) => {
  const [powerModels, setPowerModels] = useState<PowerModel[]>([]);
  const { modules } = usePVModules();
  const [tiltConfigs, setTiltConfigs] = useState<InverterTiltConfig[]>([]);
  const [moduleId, setModuleId] = useState<number | undefined>(undefined);
  const [powerModelId, setPowerModelId] = useState<number | undefined>(undefined);
  const [weatherConfig, setWeatherConfig] = useState<DevicePVConfig['weather_device_config'] | undefined>(undefined);
  const [saving, setSaving] = useState(false);
  const [loadingDevice, setLoadingDevice] = useState(false);

  // Load power models when modal opens
  useEffect(() => {
    const fetchPowerModels = async () => {
      try {
        const models = await powerModelApi.list();
        setPowerModels(models || []);
      } catch (error) {
        console.error('Failed to fetch power models for inverter config:', error);
        setPowerModels([]);
      }
    };
    if (isOpen) {
      fetchPowerModels();
    }
  }, [isOpen]);

  // When modal opens, fetch this inverter's full config by device_id so tilt_configs from device_list are loaded
  useEffect(() => {
    if (!isOpen || !device?.device_id) return;

    let cancelled = false;
    setLoadingDevice(true);

    const applyDevice = (d: DevicePVConfig) => {
      if (cancelled) return;
      const configs = d.tilt_configs;
      setTiltConfigs(Array.isArray(configs) ? configs : []);
      setModuleId(d.module_datasheet_id as number | undefined);
      setPowerModelId(d.power_model_id);
      setWeatherConfig(
        d.weather_device_config || {
          irradiance_devices: [],
          temperature_devices: [],
          wind_devices: [],
        }
      );
    };

    (async () => {
      try {
        const fetched = await devicePVConfigApi.get(device.device_id);
        if (fetched) {
          applyDevice(fetched);
        } else {
          applyDevice(device);
        }
      } catch (err) {
        console.error('Failed to fetch inverter config for tilt_configs:', err);
        applyDevice(device);
      } finally {
        if (!cancelled) setLoadingDevice(false);
      }
    })();

    return () => { cancelled = true; };
  }, [isOpen, device?.device_id]);

  if (!isOpen || !device) return null;

  const handleTiltConfigChange = (index: number, field: keyof InverterTiltConfig, value: string | number) => {
    setTiltConfigs(prev => {
      const updated = [...prev];
      const cfg = { ...(updated[index] || {}) } as InverterTiltConfig;
      if (field === 'tilt_deg' || field === 'azimuth_deg') {
        (cfg as any)[field] = value === '' ? 0 : Number(value);
      } else if (field === 'string_count' || field === 'modules_in_series' || field === 'panel_count') {
        (cfg as any)[field] = value === '' ? 0 : Number(value);
      } else if (field === 'orientation') {
        (cfg as any)[field] = value as string;
      }
      updated[index] = cfg;
      return updated;
    });
  };

  const addTiltConfigRow = () => {
    setTiltConfigs(prev => [
      ...prev,
      {
        tilt_deg: 0,
        azimuth_deg: 0,
        orientation: '',
        string_count: 1,
        modules_in_series: 1,
        panel_count: 1,
      },
    ]);
  };

  const removeTiltConfigRow = (index: number) => {
    setTiltConfigs(prev => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!device) return;

    setSaving(true);
    try {
      const success = await onSave(device.device_id, {
        tilt_configs: tiltConfigs,
        module_datasheet_id: moduleId,
        power_model_id: powerModelId,
        weather_device_config: weatherConfig,
      });
      if (success) {
        onClose();
      }
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="modal-overlay fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="modal-content max-h-[90vh] w-full max-w-4xl overflow-y-auto rounded-lg bg-white p-6 shadow-xl">
        <div className="modal-header mb-6 flex items-center justify-between">
          <h3 className="fw-bold text-dark text-2xl">
            ⚙️ Configure Inverter: {device.device_id}
          </h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
            type="button"
          >
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          {/* Inverter info */}
          <div className="bg-light mb-6 rounded-lg border p-4">
            <div className="text-dark">
              <strong>Inverter:</strong> {device.device_name}
              <span className="text-muted ms-3">Type: {device.device_type}</span>
              {device.parent_code && <span className="text-muted ms-3">Site: {device.parent_code}</span>}
            </div>
            {(device.dc_cap || device.ac_capacity) && (
              <div className="mt-2 text-sm text-gray-700">
                {device.dc_cap != null && <span className="me-3">DC Cap: {device.dc_cap} kW</span>}
                {device.ac_capacity != null && <span>AC Cap: {device.ac_capacity} kW</span>}
              </div>
            )}
          </div>

          {/* Inverter-level PV module (fallback when no strings are available) */}
          <div className="mb-6 rounded-lg border border-gray-200 p-4">
            <h4 className="fw-semibold text-dark mb-4 text-lg">☀️ PV Module (Inverter-level)</h4>
            <p className="text-muted small mb-3">
              Select a PV module to be used as the base datasheet for inverter-level SDM calculations
              when no configured strings are available under this inverter. If strings with modules are
              configured, they will be used instead; this acts as a fallback for inverter-only assets.
            </p>

            <div className="mb-3">
              <label className="fw-medium text-dark mb-2 block text-sm">
                Select PV Module from Library
              </label>
              <select
                className="text-dark form-select"
                value={moduleId || ''}
                onChange={(e) => {
                  const value = e.target.value;
                  setModuleId(value ? parseInt(value, 10) : undefined);
                }}
              >
                <option value="" className="text-dark">
                  -- Optional: select PV Module --
                </option>
                {modules.map((module) => (
                  <option key={module.id} value={module.id} className="text-dark">
                    {module.manufacturer} {module.module_model} ({module.pmax_stc}Wp)
                  </option>
                ))}
              </select>
              <small className="form-text text-muted">
                Recommended for sites without string-level configuration. You can still override string layout per
                SDM group in the table below.
              </small>
            </div>
          </div>

          {/* Tilt configs / SDM groups — from device_list.tilt_configs, displayed for reconfirmation */}
          <div className="mb-6 rounded-lg border border-gray-200 p-4">
            <h4 className="fw-semibold text-dark mb-4 text-lg">📐 Inverter SDM Groups (Tilt Configs)</h4>
            <p className="text-muted small mb-3">
              These groups are stored in <strong>device_list.tilt_configs</strong> for this inverter.
              They are shown here so you can <strong>reconfirm</strong> the configuration; you do not need to add them again.
              Each row is a group of strings with the same tilt, azimuth, and modules per string, used as array inputs to the Single Diode Model at inverter level.
            </p>

            {loadingDevice && (
              <p className="mb-3 text-sm text-muted">Loading group details from device_list…</p>
            )}

            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-100">
                  <tr>
                    <th className="p-2 text-left">Tilt (°)</th>
                    <th className="p-2 text-left">Azimuth (°)</th>
                    <th className="p-2 text-left">Orientation</th>
                    <th className="p-2 text-left">String Count</th>
                    <th className="p-2 text-left">Modules in Series</th>
                    <th className="p-2 text-left">Panel Count</th>
                    <th className="p-2 text-center">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {tiltConfigs.map((cfg, idx) => (
                    <tr key={idx} className="border-t">
                      <td className="p-2">
                        <input
                          type="number"
                          step="0.1"
                          className="form-control form-control-sm text-dark"
                          value={cfg.tilt_deg}
                          onChange={(e) => handleTiltConfigChange(idx, 'tilt_deg', e.target.value)}
                        />
                      </td>
                      <td className="p-2">
                        <input
                          type="number"
                          step="0.1"
                          className="form-control form-control-sm text-dark"
                          value={cfg.azimuth_deg}
                          onChange={(e) => handleTiltConfigChange(idx, 'azimuth_deg', e.target.value)}
                        />
                      </td>
                      <td className="p-2">
                        <input
                          type="text"
                          className="form-control form-control-sm text-dark"
                          value={cfg.orientation || ''}
                          onChange={(e) => handleTiltConfigChange(idx, 'orientation', e.target.value)}
                          placeholder="North / South / East / West"
                        />
                      </td>
                      <td className="p-2">
                        <input
                          type="number"
                          className="form-control form-control-sm text-dark"
                          value={cfg.string_count}
                          onChange={(e) => handleTiltConfigChange(idx, 'string_count', e.target.value)}
                        />
                      </td>
                      <td className="p-2">
                        <input
                          type="number"
                          className="form-control form-control-sm text-dark"
                          value={cfg.modules_in_series}
                          onChange={(e) => handleTiltConfigChange(idx, 'modules_in_series', e.target.value)}
                        />
                      </td>
                      <td className="p-2">
                        <input
                          type="number"
                          className="form-control form-control-sm text-dark"
                          value={cfg.panel_count}
                          onChange={(e) => handleTiltConfigChange(idx, 'panel_count', e.target.value)}
                        />
                      </td>
                      <td className="p-2 text-center">
                        <button
                          type="button"
                          className="btn btn-sm btn-outline-danger"
                          onClick={() => removeTiltConfigRow(idx)}
                        >
                          ✕
                        </button>
                      </td>
                    </tr>
                  ))}
                  {tiltConfigs.length === 0 && (
                    <tr>
                      <td colSpan={7} className="p-3 text-center text-gray-500">
                        No SDM groups configured yet. Click &quot;Add Group&quot; to define tilt/azimuth and string layout.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            <div className="mt-3 flex flex-wrap items-center gap-3">
              <button
                type="button"
                className="btn btn-sm btn-outline-primary"
                onClick={addTiltConfigRow}
              >
                ➕ Add Group
              </button>
              <span className="text-muted small">
                Edit rows or add/remove groups only if you need to correct the stored configuration.
              </span>
            </div>
          </div>

          {/* Power model selection */}
          <div className="mb-6 rounded-lg border border-gray-200 p-4">
            <h4 className="fw-semibold text-dark mb-4 text-lg">🧮 Inverter Power Model</h4>
            <div className="mb-3">
              <label className="fw-medium text-dark mb-1 block text-sm">
                Calculation Model
              </label>
              <select
                className="text-dark form-select"
                value={powerModelId || ''}
                onChange={(e) => {
                  const value = e.target.value;
                  setPowerModelId(value ? parseInt(value, 10) : undefined);
                }}
                disabled={powerModels.length === 0}
              >
                <option value="" className="text-dark">-- Use Default Model --</option>
                {powerModels.map((model) => (
                  <option key={model.id} value={model.id} className="text-dark">
                    {model.name} v{model.version}
                  </option>
                ))}
              </select>
              {powerModels.length === 0 && (
                <small className="form-text text-warning">
                  No power models available. Using default model.
                </small>
              )}
            </div>
          </div>

          {/* Weather configuration */}
          <div className="mb-6 rounded-lg border border-gray-200 p-4">
            <h4 className="fw-semibold text-dark mb-4 text-lg">🌤️ Weather Device Configuration</h4>
            <p className="text-muted small mb-4">
              Configure which irradiance, temperature, and wind sensors feed this inverter’s SDM calculations.
              Multiple devices can be configured for automatic fallback.
              For transposed GII, use the synthetic irradiance “devices” stored in <code>timeseries_data</code>
              (for example, <code>{device.parent_code}_gii_tilt_azimuth</code> with metric <code>gii</code>).
            </p>

            {device.parent_code ? (
              <>
                <WeatherDeviceSelector
                  label="☀️ Irradiance Sensors (device + metric, order matches SDM groups)"
                  selectedDevices={weatherConfig?.irradiance_devices || []}
                  onChange={(deviceMetrics) => {
                    setWeatherConfig(prev => ({
                      ...(prev || {}),
                      irradiance_devices: deviceMetrics,
                      temperature_devices: prev?.temperature_devices || [],
                      wind_devices: prev?.wind_devices || [],
                    }));
                  }}
                  assetCode={device.parent_code}
                />

                <WeatherDeviceSelector
                  label="🌡️ Temperature Sensors"
                  selectedDevices={weatherConfig?.temperature_devices || []}
                  onChange={(deviceMetrics) => {
                    setWeatherConfig(prev => ({
                      ...(prev || {}),
                      irradiance_devices: prev?.irradiance_devices || [],
                      temperature_devices: deviceMetrics,
                      wind_devices: prev?.wind_devices || [],
                    }));
                  }}
                  assetCode={device.parent_code}
                />

                <WeatherDeviceSelector
                  label="💨 Wind Speed Sensors (Optional)"
                  selectedDevices={weatherConfig?.wind_devices || []}
                  onChange={(deviceMetrics) => {
                    setWeatherConfig(prev => ({
                      ...(prev || {}),
                      irradiance_devices: prev?.irradiance_devices || [],
                      temperature_devices: prev?.temperature_devices || [],
                      wind_devices: deviceMetrics,
                    }));
                  }}
                  assetCode={device.parent_code}
                />
              </>
            ) : (
              <div className="alert alert-warning">
                <small>Inverter must have a parent asset (parent_code) to configure weather devices.</small>
              </div>
            )}
          </div>

          {/* Action buttons */}
          <div className="flex justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="btn btn-secondary"
              disabled={saving}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={saving}
            >
              {saving ? 'Saving...' : '💾 Save Inverter Configuration'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

