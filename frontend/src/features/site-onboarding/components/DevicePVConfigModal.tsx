/**
 * Individual Device PV Configuration Modal
 * Modal for configuring PV settings for a single device
 */
import React, { useState, useEffect } from 'react';
import { usePVModules } from '../hooks/usePVModules';
import { powerModelApi } from '../api/pvModules';
import { WeatherDeviceSelector } from './WeatherDeviceSelector';
import type { DevicePVConfig, PowerModel } from '../types/pvModules';

interface DevicePVConfigModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (deviceId: string, config: Partial<DevicePVConfig>) => Promise<boolean>;
  device: DevicePVConfig | null;
}

export const DevicePVConfigModal: React.FC<DevicePVConfigModalProps> = ({
  isOpen,
  onClose,
  onSave,
  device,
}) => {
  const { modules } = usePVModules();
  const [powerModels, setPowerModels] = useState<PowerModel[]>([]);
  const [formData, setFormData] = useState<Partial<DevicePVConfig>>({});
  const [saving, setSaving] = useState(false);

  // Fetch power models
  useEffect(() => {
    const fetchPowerModels = async () => {
      try {
        const models = await powerModelApi.list();
        setPowerModels(models || []);
        if (models && models.length === 0) {
          console.warn('No power models available');
        }
      } catch (error) {
        console.error('Failed to fetch power models:', error);
        setPowerModels([]);
      }
    };
    if (isOpen) {
      fetchPowerModels();
    }
  }, [isOpen]);

  // Populate form when device changes
  useEffect(() => {
    if (isOpen && device) {
      setFormData({
        module_datasheet_id: device.module_datasheet_id,
        modules_in_series: device.modules_in_series,
        installation_date: device.installation_date,
        tilt_angle: device.tilt_angle,
        azimuth_angle: device.azimuth_angle,
        mounting_type: device.mounting_type,
        expected_soiling_loss: device.expected_soiling_loss ?? 2.0,
        shading_factor: device.shading_factor ?? 0.0,
        measured_degradation_rate: device.measured_degradation_rate,
        last_performance_test_date: device.last_performance_test_date,
        operational_notes: device.operational_notes,
        power_model_id: device.power_model_id,
        weather_device_config: device.weather_device_config || {
          irradiance_devices: [],
          temperature_devices: [],
          wind_devices: [],
        },
      });
    }
  }, [isOpen, device]);

  const handleChange = (field: keyof DevicePVConfig, value: string | number | boolean | null) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!device) return;

    setSaving(true);
    try {
      const success = await onSave(device.device_id, formData);
      if (success) {
        onClose();
      }
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen || !device) return null;

  const selectedModule = formData.module_datasheet_id
    ? modules.find((m) => m.id === formData.module_datasheet_id)
    : null;

  return (
    <div className="modal-overlay fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="modal-content max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-lg bg-white p-6 shadow-xl">
        <div className="modal-header mb-6 flex items-center justify-between">
          <h3 className="fw-bold text-dark text-2xl">
            ⚙️ Configure Device: {device.device_id}
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
          {/* Device Info */}
          <div className="bg-light mb-6 rounded-lg border p-4">
            <div className="text-dark">
              <strong>Device:</strong> {device.device_name}
              <span className="text-muted ms-3">Type: {device.device_type}</span>
              {device.parent_code && <span className="text-muted ms-3">Site: {device.parent_code}</span>}
            </div>
          </div>

          {/* Module Selection */}
          <div className="mb-6 rounded-lg border border-gray-200 p-4">
            <h4 className="fw-semibold text-dark mb-4 text-lg">☀️ PV Module</h4>
            
            <div className="mb-4">
              <label className="fw-medium text-dark mb-2 block text-sm">
                Select PV Module <span className="text-danger">*</span>
              </label>
              <select
                className="text-dark form-select"
                value={formData.module_datasheet_id || ''}
                onChange={(e) => handleChange('module_datasheet_id', e.target.value ? parseInt(e.target.value, 10) : null)}
                required
              >
                <option value="" className="text-dark">-- Select PV Module from Library --</option>
                {modules.map((module) => (
                  <option key={module.id} value={module.id} className="text-dark">
                    {module.manufacturer} {module.module_model} ({module.pmax_stc}Wp)
                  </option>
                ))}
              </select>
              <small className="form-text text-muted">
                Choose from your Module Library. Don&apos;t see your module? Add it first in &quot;Module Library&quot; tab.
              </small>
            </div>

            {selectedModule && (
              <div className="bg-light rounded p-3">
                <div className="row text-dark text-sm">
                  <div className="col-md-4"><strong className="text-dark">Pmax:</strong> <span className="text-dark">{selectedModule.pmax_stc} Wp</span></div>
                  <div className="col-md-4"><strong className="text-dark">Efficiency:</strong> <span className="text-dark">{selectedModule.module_efficiency_stc}%</span></div>
                  <div className="col-md-4"><strong className="text-dark">Technology:</strong> <span className="text-dark">{selectedModule.technology}</span></div>
                </div>
              </div>
            )}
          </div>

          {/* String Configuration */}
          <div className="mb-6 rounded-lg border border-gray-200 p-4">
            <h4 className="fw-semibold text-dark mb-4 text-lg">🔌 String Configuration</h4>
            
            <div className="row">
              <div className="col-md-6 mb-3">
                <label className="fw-medium text-dark mb-1 block text-sm">
                  Modules in Series <span className="text-danger">*</span>
                </label>
                <input
                  type="number"
                  className="form-control text-dark"
                  value={formData.modules_in_series || ''}
                  onChange={(e) => handleChange('modules_in_series', e.target.value ? parseInt(e.target.value, 10) : null)}
                  required
                  placeholder="e.g., 24"
                />
                <small className="form-text text-muted">Number of modules connected in series per string</small>
              </div>

              <div className="col-md-6 mb-3">
                <label className="fw-medium text-dark mb-1 block text-sm">
                  Installation Date
                </label>
                <input
                  type="date"
                  className="form-control text-dark"
                  value={formData.installation_date || ''}
                  onChange={(e) => handleChange('installation_date', e.target.value || null)}
                />
              </div>
            </div>
          </div>

          {/* Installation Details */}
          <div className="mb-6 rounded-lg border border-gray-200 p-4">
            <h4 className="fw-semibold text-dark mb-4 text-lg">📐 Installation Details</h4>
            
            <div className="row">
              <div className="col-md-4 mb-3">
                <label className="fw-medium text-dark mb-1 block text-sm">
                  Tilt Angle (°)
                </label>
                <input
                  type="number"
                  step="0.1"
                  className="form-control text-dark"
                  value={formData.tilt_angle || ''}
                  onChange={(e) => handleChange('tilt_angle', e.target.value ? parseFloat(e.target.value) : null)}
                  placeholder="30.0"
                />
                <small className="form-text text-muted">Angle from horizontal (0-90°)</small>
              </div>

              <div className="col-md-4 mb-3">
                <label className="fw-medium text-dark mb-1 block text-sm">
                  Azimuth Angle (°)
                </label>
                <input
                  type="number"
                  step="0.1"
                  className="form-control text-dark"
                  value={formData.azimuth_angle || ''}
                  onChange={(e) => handleChange('azimuth_angle', e.target.value ? parseFloat(e.target.value) : null)}
                  placeholder="180.0"
                />
                <small className="form-text text-muted">0°=North, 90°=East, 180°=South, 270°=West</small>
              </div>

              <div className="col-md-4 mb-3">
                <label className="fw-medium text-dark mb-1 block text-sm">
                  Mounting Type
                </label>
                <select
                  className="text-dark form-select"
                  value={formData.mounting_type || ''}
                  onChange={(e) => handleChange('mounting_type', e.target.value || null)}
                >
                  <option value="" className="text-dark">-- Select --</option>
                  <option value="Fixed" className="text-dark">Fixed</option>
                  <option value="Single-Axis Tracker" className="text-dark">Single-Axis Tracker</option>
                  <option value="Dual-Axis Tracker" className="text-dark">Dual-Axis Tracker</option>
                  <option value="Ground Mount" className="text-dark">Ground Mount</option>
                  <option value="Rooftop" className="text-dark">Rooftop</option>
                </select>
              </div>
            </div>
          </div>

          {/* Loss Factors */}
          <div className="mb-6 rounded-lg border border-gray-200 p-4">
            <h4 className="fw-semibold text-dark mb-4 text-lg">📉 Loss Factors</h4>
            
            <div className="row">
              <div className="col-md-6 mb-3">
                <label className="fw-medium text-dark mb-1 block text-sm">
                  Expected Soiling Loss (%)
                </label>
                <input
                  type="number"
                  step="0.1"
                  className="form-control text-dark"
                  value={formData.expected_soiling_loss ?? 2.0}
                  onChange={(e) => handleChange('expected_soiling_loss', e.target.value ? parseFloat(e.target.value) : 2.0)}
                  placeholder="2.0"
                />
                <small className="form-text text-muted">Typical: 1-5% depending on location</small>
              </div>

              <div className="col-md-6 mb-3">
                <label className="fw-medium text-dark mb-1 block text-sm">
                  Shading Factor (%)
                </label>
                <input
                  type="number"
                  step="0.1"
                  className="form-control text-dark"
                  value={formData.shading_factor ?? 0.0}
                  onChange={(e) => handleChange('shading_factor', e.target.value ? parseFloat(e.target.value) : 0.0)}
                  placeholder="0.0"
                />
                <small className="form-text text-muted">% loss from nearby obstructions</small>
              </div>
            </div>
          </div>

          {/* Performance Tracking */}
          <div className="mb-6 rounded-lg border border-gray-200 p-4">
            <h4 className="fw-semibold text-dark mb-4 text-lg">📊 Performance Tracking (Optional)</h4>
            
            <div className="row">
              <div className="col-md-6 mb-3">
                <label className="fw-medium text-dark mb-1 block text-sm">
                  Measured Degradation Rate (%/year)
                </label>
                <input
                  type="number"
                  step="0.01"
                  className="form-control text-dark"
                  value={formData.measured_degradation_rate || ''}
                  onChange={(e) => handleChange('measured_degradation_rate', e.target.value ? parseFloat(e.target.value) : null)}
                  placeholder="0.5"
                />
              </div>

              <div className="col-md-6 mb-3">
                <label className="fw-medium text-dark mb-1 block text-sm">
                  Last Performance Test Date
                </label>
                <input
                  type="date"
                  className="form-control text-dark"
                  value={formData.last_performance_test_date || ''}
                  onChange={(e) => handleChange('last_performance_test_date', e.target.value || null)}
                />
              </div>
            </div>
          </div>

          {/* Power Model Selection */}
          <div className="mb-6 rounded-lg border border-gray-200 p-4">
            <h4 className="fw-semibold text-dark mb-4 text-lg">🧮 Power Calculation Model</h4>
            
            <div className="mb-3">
              <label className="fw-medium text-dark mb-1 block text-sm">
                Calculation Model
              </label>
              <select
                className="text-dark form-select"
                value={formData.power_model_id || ''}
                onChange={(e) => {
                  const value = e.target.value;
                  handleChange('power_model_id', value ? parseInt(value, 10) : null);
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
              <small className="form-text text-muted">Select which calculation method to use for this device</small>
            </div>
          </div>

          {/* Weather Device Configuration */}
          <div className="mb-6 rounded-lg border border-gray-200 p-4">
            <h4 className="fw-semibold text-dark mb-4 text-lg">🌤️ Weather Device Configuration</h4>
            <p className="text-muted small mb-4">
              Configure weather sensors for loss calculations. Select multiple devices for automatic fallback if primary sensor data is unavailable.
            </p>
            
            {device?.parent_code ? (
              <>
                <WeatherDeviceSelector
                  label="☀️ Irradiance Sensors"
                  selectedDevices={formData.weather_device_config?.irradiance_devices || []}
                  onChange={(deviceMetrics) => {
                    setFormData(prev => ({
                      ...prev,
                      weather_device_config: {
                        ...prev.weather_device_config,
                        irradiance_devices: deviceMetrics,
                        temperature_devices: prev.weather_device_config?.temperature_devices || [],
                        wind_devices: prev.weather_device_config?.wind_devices || [],
                      }
                    }));
                  }}
                  assetCode={device.parent_code}
                />

                <WeatherDeviceSelector
                  label="🌡️ Temperature Sensors"
                  selectedDevices={formData.weather_device_config?.temperature_devices || []}
                  onChange={(deviceMetrics) => {
                    setFormData(prev => ({
                      ...prev,
                      weather_device_config: {
                        ...prev.weather_device_config,
                        irradiance_devices: prev.weather_device_config?.irradiance_devices || [],
                        temperature_devices: deviceMetrics,
                        wind_devices: prev.weather_device_config?.wind_devices || [],
                      }
                    }));
                  }}
                  assetCode={device.parent_code}
                />

                <WeatherDeviceSelector
                  label="💨 Wind Speed Sensors (Optional)"
                  selectedDevices={formData.weather_device_config?.wind_devices || []}
                  onChange={(deviceMetrics) => {
                    setFormData(prev => ({
                      ...prev,
                      weather_device_config: {
                        ...prev.weather_device_config,
                        irradiance_devices: prev.weather_device_config?.irradiance_devices || [],
                        temperature_devices: prev.weather_device_config?.temperature_devices || [],
                        wind_devices: deviceMetrics,
                      }
                    }));
                  }}
                  assetCode={device.parent_code}
                />
              </>
            ) : (
              <div className="alert alert-warning">
                <small>Device must have a parent_code (asset) to configure weather devices.</small>
              </div>
            )}
          </div>

          {/* Operational Notes */}
          <div className="mb-6">
            <label className="fw-medium text-dark mb-1 block text-sm">
              Operational Notes
            </label>
            <textarea
              className="form-control text-dark"
              rows={3}
              value={formData.operational_notes || ''}
              onChange={(e) => handleChange('operational_notes', e.target.value || null)}
              placeholder="Any special notes about this device's PV configuration..."
            />
          </div>

          {/* Action Buttons */}
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
              {saving ? 'Saving...' : '💾 Save Configuration'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

