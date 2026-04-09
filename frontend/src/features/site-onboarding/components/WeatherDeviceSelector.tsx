/**
 * Weather Device Selector Component
 * Multi-select component for choosing weather devices with metric selection and fallback support
 */
import React, { useState, useEffect } from 'react';
import { weatherDeviceApi, weatherMetricsApi } from '../api/pvModules';
import type { WeatherDevice, WeatherDeviceMetric, WeatherMetric } from '../types/pvModules';

interface WeatherDeviceSelectorProps {
  label: string;
  selectedDevices: WeatherDeviceMetric[];
  onChange: (devices: WeatherDeviceMetric[]) => void;
  assetCode: string;
  disabled?: boolean;
}

export const WeatherDeviceSelector: React.FC<WeatherDeviceSelectorProps> = ({
  label,
  selectedDevices,
  onChange,
  assetCode,
  disabled = false,
}) => {
  const [devices, setDevices] = useState<WeatherDevice[]>([]);
  const [metrics, setMetrics] = useState<WeatherMetric[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingMetrics, setLoadingMetrics] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [selectedDeviceId, setSelectedDeviceId] = useState<string>('');
  const [selectedMetric, setSelectedMetric] = useState<string>('');

  // Fetch weather devices when asset code changes
  useEffect(() => {
    if (!assetCode) {
      setDevices([]);
      return;
    }

    const fetchDevices = async () => {
      setLoading(true);
      setError(null);
      try {
        const deviceList = await weatherDeviceApi.list(assetCode);
        setDevices(deviceList);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load weather devices');
        console.error('Error fetching weather devices:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchDevices();
  }, [assetCode]);

  // Fetch weather metrics when asset code changes
  useEffect(() => {
    if (!assetCode) {
      setMetrics([]);
      return;
    }

    const fetchMetrics = async () => {
      setLoadingMetrics(true);
      try {
        const metricsList = await weatherMetricsApi.list(assetCode);
        setMetrics(metricsList);
      } catch (err) {
        console.error('Error fetching weather metrics:', err);
      } finally {
        setLoadingMetrics(false);
      }
    };

    fetchMetrics();
  }, [assetCode]);

  const handleAddDevice = () => {
    if (!selectedDeviceId || !selectedMetric) {
      return;
    }

    // Check if this device+metric combination already exists
    const exists = selectedDevices.some(
      d => d.device_id === selectedDeviceId && d.metric === selectedMetric
    );

    if (exists) {
      return;
    }

    const newDevice: WeatherDeviceMetric = {
      device_id: selectedDeviceId,
      metric: selectedMetric,
    };

    onChange([...selectedDevices, newDevice]);
    setSelectedDeviceId('');
    setSelectedMetric('');
    setIsOpen(false);
  };

  const handleRemoveDevice = (index: number) => {
    if (disabled) return;
    const newSelection = selectedDevices.filter((_, i) => i !== index);
    onChange(newSelection);
  };

  const getDeviceName = (deviceId: string) => {
    const device = devices.find(d => d.device_id === deviceId);
    return device ? device.device_name : deviceId;
  };

  const getMetricDisplay = (metricName: string) => {
    const metric = metrics.find(m => m.metric === metricName);
    if (metric) {
      // Display metric name with units and description
      let display = metric.metric;
      if (metric.units) {
        display += ` (${metric.units})`;
      }
      if (metric.description) {
        display += ` - ${metric.description}`;
      }
      return display;
    }
    return metricName;
  };

  return (
    <div className="mb-4">
      <label className="fw-medium text-dark mb-2 block text-sm">
        {label}
        <span className="text-muted ms-2">
          (Select device + metric, multiple for fallback - order matters)
        </span>
      </label>

      {!assetCode && (
        <div className="alert alert-warning mb-2">
          <small>Select an asset first to load weather devices</small>
        </div>
      )}

      {loading && (
        <div className="text-muted">
          <small>Loading weather devices...</small>
        </div>
      )}

      {error && (
        <div className="alert alert-danger mb-2">
          <small>{error}</small>
        </div>
      )}

      {/* Selected Devices (Ordered List) */}
      {selectedDevices.length > 0 && (
        <div className="mb-2">
          <div className="fw-semibold text-dark mb-1 text-xs">Selected (in fallback order):</div>
          <div className="d-flex flex-column gap-1">
            {selectedDevices.map((deviceMetric, index) => (
              <div
                key={`${deviceMetric.device_id}-${deviceMetric.metric}-${index}`}
                className="badge bg-primary d-flex align-items-center justify-content-between gap-2 p-2"
                style={{ fontSize: '0.75rem' }}
              >
                <div className="d-flex align-items-center gap-2">
                  <span className="fw-bold text-white">{index + 1}.</span>
                  <span className="text-white">
                    {getDeviceName(deviceMetric.device_id)} → {getMetricDisplay(deviceMetric.metric)}
                  </span>
                </div>
                {!disabled && (
                  <button
                    type="button"
                    className="btn-close btn-close-white"
                    style={{ fontSize: '0.6rem' }}
                    onClick={() => handleRemoveDevice(index)}
                    aria-label="Remove"
                  />
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Device + Metric Selection */}
      {assetCode && devices.length > 0 && metrics.length > 0 && (
        <div className="position-relative">
          <button
            type="button"
            className="form-select text-start"
            onClick={() => setIsOpen(!isOpen)}
            disabled={disabled}
            style={{ cursor: disabled ? 'not-allowed' : 'pointer' }}
          >
            {selectedDevices.length === 0
              ? '-- Add Device + Metric --'
              : `Add Device + Metric (${devices.length} devices, ${metrics.length} metrics available)`}
          </button>

          {isOpen && !disabled && (
            <>
              <div
                className="position-fixed"
                style={{
                  top: 0,
                  left: 0,
                  right: 0,
                  bottom: 0,
                  zIndex: 1040,
                }}
                onClick={() => {
                  setIsOpen(false);
                  setSelectedDeviceId('');
                  setSelectedMetric('');
                }}
              />
              <div
                className="position-absolute rounded border bg-white p-3 shadow-lg"
                style={{
                  top: '100%',
                  left: 0,
                  right: 0,
                  zIndex: 1050,
                  maxHeight: '400px',
                  overflowY: 'auto',
                  marginTop: '2px',
                }}
              >
                <div className="mb-3">
                  <label className="fw-medium text-dark mb-1 block text-sm">
                    Select Device:
                  </label>
                  <select
                    className="form-select-sm text-dark form-select"
                    value={selectedDeviceId}
                    onChange={(e) => setSelectedDeviceId(e.target.value)}
                  >
                    <option value="">-- Select Device --</option>
                    {devices.map((device) => (
                      <option key={device.device_id} value={device.device_id} className="text-dark">
                        {device.device_name} ({device.device_type})
                      </option>
                    ))}
                  </select>
                </div>

                <div className="mb-3">
                  <label className="fw-medium text-dark mb-1 block text-sm">
                    Select Metric:
                  </label>
                  <select
                    className="form-select-sm text-dark form-select"
                    value={selectedMetric}
                    onChange={(e) => setSelectedMetric(e.target.value)}
                    disabled={!selectedDeviceId}
                  >
                    <option value="">-- Select Metric --</option>
                    {metrics.map((metric) => (
                      <option key={metric.metric} value={metric.metric} className="text-dark">
                        {metric.metric}{metric.units ? ` (${metric.units})` : ''}
                        {metric.description ? ` - ${metric.description}` : ''}
                      </option>
                    ))}
                  </select>
                </div>

                <button
                  type="button"
                  className="btn btn-primary btn-sm w-100"
                  onClick={handleAddDevice}
                  disabled={!selectedDeviceId || !selectedMetric}
                >
                  Add Device + Metric
                </button>
              </div>
            </>
          )}
        </div>
      )}

      {assetCode && !loading && devices.length === 0 && (
        <div className="alert alert-info mb-0">
          <small>No weather devices found for this asset. Add weather devices in Device List first.</small>
        </div>
      )}

      {loadingMetrics && (
        <div className="text-muted">
          <small>Loading metrics...</small>
        </div>
      )}

      <small className="form-text text-muted">
        Devices are tried in order. If the first device has no data for the selected metric, the system automatically tries the next one.
      </small>
    </div>
  );
};
