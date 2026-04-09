 
import { useEffect, useRef, useState } from 'react';
import type { DeviceList } from '../types';
import type { InverterTiltConfig } from '../types/pvModules';

interface DeviceFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (device: Partial<DeviceList>) => Promise<void> | void;
  device: DeviceList | null;
}

const defaultDevice: Partial<DeviceList> = {
  device_id: '',
  device_name: '',
  device_code: '',
  device_type_id: '',
  device_serial: '',
  device_model: '',
  device_make: '',
  latitude: 0,
  longitude: 0,
  optimizer_no: 0,
  parent_code: '',
  device_type: '',
  software_version: '',
  country: '',
  string_no: '',
  connected_strings: '',
  device_sub_group: '',
  dc_cap: 0,
  device_source: '',
  ac_capacity: null,
  equipment_warranty_start_date: '',
  equipment_warranty_expire_date: '',
  epc_warranty_start_date: '',
  epc_warranty_expire_date: '',
  calibration_frequency: '',
  pm_frequency: '',
  visual_inspection_frequency: '',
  bess_capacity: null,
  yom: '',
  nomenclature: '',
  location: '',
  module_datasheet_id: null,
  modules_in_series: null,
  installation_date: null,
  tilt_angle: null,
  azimuth_angle: null,
  mounting_type: null,
  expected_soiling_loss: null,
  shading_factor: null,
  measured_degradation_rate: null,
  last_performance_test_date: null,
  operational_notes: '',
  power_model_id: null,
  power_model_config: null,
  model_fallback_enabled: null,
  weather_device_config: null,
  tilt_configs: null,
};

type PowerModelRow = { param: string; value: string };
type WeatherConfigRow = { irradiance_device: string; temperature_device: string };

const emptyInverterTiltRow = (): InverterTiltConfig => ({
  tilt_deg: 0,
  azimuth_deg: 0,
  orientation: '',
  string_count: 1,
  modules_in_series: 1,
  panel_count: 1,
});

/** Legacy rows only had tilt_deg, azimuth_deg, panel_count — preserve and default the rest. */
function normalizeTiltRowFromApi(raw: Record<string, unknown>): InverterTiltConfig {
  const legacy =
    raw.string_count === undefined &&
    raw.modules_in_series === undefined &&
    raw.orientation === undefined;
  const panel = Number(raw.panel_count ?? 0);
  return {
    tilt_deg: Number(raw.tilt_deg ?? 0),
    azimuth_deg: Number(raw.azimuth_deg ?? 0),
    orientation: typeof raw.orientation === 'string' ? raw.orientation : '',
    string_count: legacy ? 1 : Number(raw.string_count ?? 1),
    modules_in_series: legacy ? 1 : Number(raw.modules_in_series ?? 1),
    panel_count: Number.isFinite(panel) ? panel : 0,
  };
}

const DEVICE_SOURCE_OPTIONS = ['revenue', 'ghi', 'active_power', 'gii', 'others'] as const;

const parseJsonValue = (val: unknown) => {
  if (val == null) return null;
  if (typeof val === 'string') {
    const trimmed = val.trim();
    if (!trimmed) return null;
    try {
      return JSON.parse(trimmed);
    } catch {
      return null;
    }
  }
  return val;
};

export function DeviceFormModal({ isOpen, onClose, onSave, device }: DeviceFormModalProps) {
  const [formData, setFormData] = useState<Partial<DeviceList>>(defaultDevice);
  const [selectedDeviceSources, setSelectedDeviceSources] = useState<string[]>([]);
  const [customDeviceSource, setCustomDeviceSource] = useState('');
  const [deviceSourceDropdownOpen, setDeviceSourceDropdownOpen] = useState(false);
  const [powerModelRows, setPowerModelRows] = useState<PowerModelRow[]>([{ param: '', value: '' }]);
  const [weatherConfigRows, setWeatherConfigRows] = useState<WeatherConfigRow[]>([
    { irradiance_device: '', temperature_device: '' },
  ]);
  const [tiltConfigRows, setTiltConfigRows] = useState<InverterTiltConfig[]>([emptyInverterTiltRow()]);
  const [jsonError, setJsonError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const deviceSourceDropdownRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (isOpen) {
      setFormData(device ? { ...defaultDevice, ...device } : defaultDevice);
      const sourceValues = (() => {
        const raw = device?.device_source;
        if (!raw) return [];
        try {
          const parsed = JSON.parse(raw);
          if (Array.isArray(parsed)) {
            return parsed
              .map((item) => (typeof item === 'string' ? item.trim() : ''))
              .filter(Boolean);
          }
        } catch {
          // keep backward compatibility with legacy plain string values
        }
        return [String(raw).trim()].filter(Boolean);
      })();
      const normalizedOptions = DEVICE_SOURCE_OPTIONS.slice(0, 4);
      const selectedKnown = sourceValues.filter((s) => normalizedOptions.includes(s as (typeof DEVICE_SOURCE_OPTIONS)[number]));
      const customValues = sourceValues.filter((s) => !normalizedOptions.includes(s as (typeof DEVICE_SOURCE_OPTIONS)[number]));
      const hasCustom = customValues.length > 0;
      setSelectedDeviceSources(hasCustom ? [...selectedKnown, 'others'] : selectedKnown);
      setCustomDeviceSource(customValues.join(', '));

      const parsedPowerModel = parseJsonValue(device?.power_model_config ?? null);
      if (parsedPowerModel && typeof parsedPowerModel === 'object' && !Array.isArray(parsedPowerModel)) {
        const entries = Object.entries(parsedPowerModel as Record<string, unknown>);
        setPowerModelRows(
          entries.length
            ? entries.map(([param, value]) => ({ param, value: value == null ? '' : String(value) }))
            : [{ param: '', value: '' }],
        );
      } else {
        setPowerModelRows([{ param: '', value: '' }]);
      }

      const parsedWeatherConfig = parseJsonValue(device?.weather_device_config ?? null);
      if (parsedWeatherConfig && typeof parsedWeatherConfig === 'object' && !Array.isArray(parsedWeatherConfig)) {
        const weatherObj = parsedWeatherConfig as Record<string, unknown>;
        const irradianceDevices = Array.isArray(weatherObj.irradiance_devices)
          ? (weatherObj.irradiance_devices as unknown[]).map((v) => String(v))
          : [];
        const temperatureDevices = Array.isArray(weatherObj.temperature_devices)
          ? (weatherObj.temperature_devices as unknown[]).map((v) => String(v))
          : [];
        const maxLen = Math.max(irradianceDevices.length, temperatureDevices.length, 1);
        const rows: WeatherConfigRow[] = [];
        for (let i = 0; i < maxLen; i += 1) {
          rows.push({
            irradiance_device: irradianceDevices[i] ?? '',
            temperature_device: temperatureDevices[i] ?? '',
          });
        }
        setWeatherConfigRows(rows);
      } else {
        setWeatherConfigRows([{ irradiance_device: '', temperature_device: '' }]);
      }

      const parsedTiltConfigs = parseJsonValue(device?.tilt_configs ?? null);
      if (Array.isArray(parsedTiltConfigs) && parsedTiltConfigs.length > 0) {
        const rows = parsedTiltConfigs
          .filter((item) => item && typeof item === 'object')
          .map((item) => normalizeTiltRowFromApi(item as Record<string, unknown>));
        setTiltConfigRows(rows.length ? rows : [emptyInverterTiltRow()]);
      } else {
        setTiltConfigRows([emptyInverterTiltRow()]);
      }

      setJsonError(null);
      setDeviceSourceDropdownOpen(false);
      const modalEl = document.getElementById('deviceFormModal');
      if (modalEl) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const modal = new (window as any).bootstrap.Modal(modalEl);
        modal.show();

        const handleHidden = () => {
          onClose();
        };
        modalEl.addEventListener('hidden.bs.modal', handleHidden);

        return () => {
          modalEl.removeEventListener('hidden.bs.modal', handleHidden);
          modal.dispose();
        };
      }
    }
    return undefined;
  }, [isOpen, device, onClose]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (!deviceSourceDropdownRef.current) return;
      if (!deviceSourceDropdownRef.current.contains(event.target as Node)) {
        setDeviceSourceDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const handleChange = (field: keyof DeviceList, value: string | number | boolean | null) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleTiltFieldChange = (index: number, field: keyof InverterTiltConfig, value: string | number) => {
    setTiltConfigRows((prev) => {
      const next = [...prev];
      const cfg = { ...(next[index] || emptyInverterTiltRow()) };
      if (field === 'orientation') {
        cfg.orientation = String(value);
      } else {
        const n = value === '' ? 0 : Number(value);
        const num = Number.isFinite(n) ? n : 0;
        if (field === 'tilt_deg') cfg.tilt_deg = num;
        else if (field === 'azimuth_deg') cfg.azimuth_deg = num;
        else if (field === 'string_count') cfg.string_count = num;
        else if (field === 'modules_in_series') cfg.modules_in_series = num;
        else if (field === 'panel_count') cfg.panel_count = num;
      }
      next[index] = cfg;
      return next;
    });
  };

  const addTiltRow = () => setTiltConfigRows((prev) => [...prev, emptyInverterTiltRow()]);
  const removeTiltRow = (index: number) =>
    setTiltConfigRows((prev) => (prev.length <= 1 ? prev : prev.filter((_, i) => i !== index)));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setJsonError(null);
    setSaving(true);
    try {
      const allSources = [
        ...selectedDeviceSources.filter((source) => source !== 'others'),
        ...customDeviceSource
          .split(',')
          .map((value) => value.trim())
          .filter(Boolean),
      ];
      const uniqueSources = Array.from(new Set(allSources));
      const serializedDeviceSource = uniqueSources.length ? JSON.stringify(uniqueSources) : '';

      const powerModelConfig = powerModelRows.reduce<Record<string, string>>((acc, row) => {
        const key = row.param.trim();
        if (!key) return acc;
        acc[key] = row.value.trim();
        return acc;
      }, {});
      const parsedPowerModel = Object.keys(powerModelConfig).length ? powerModelConfig : null;

      const irradianceDevices = weatherConfigRows
        .map((row) => row.irradiance_device.trim())
        .filter(Boolean);
      const temperatureDevices = weatherConfigRows
        .map((row) => row.temperature_device.trim())
        .filter(Boolean);
      const parsedWeatherConfig =
        irradianceDevices.length || temperatureDevices.length
          ? {
              irradiance_devices: irradianceDevices,
              temperature_devices: temperatureDevices,
            }
          : null;

      const parsedTiltConfigs: NonNullable<DeviceList['tilt_configs']> = tiltConfigRows.map((row) => ({
        tilt_deg: Number(row.tilt_deg),
        azimuth_deg: Number(row.azimuth_deg),
        orientation: row.orientation || '',
        string_count: Number(row.string_count) || 1,
        modules_in_series: Number(row.modules_in_series) || 1,
        panel_count: Number(row.panel_count) || 0,
      }));
      const tiltNums = parsedTiltConfigs.flatMap((r) => [
        r.tilt_deg,
        r.azimuth_deg,
        r.string_count,
        r.modules_in_series,
        r.panel_count,
      ]);
      if (tiltNums.some((x) => Number.isNaN(x))) {
        throw new Error('Tilt config values must be valid numbers.');
      }
      const finalTiltConfigs = parsedTiltConfigs.length ? parsedTiltConfigs : null;

      if (selectedDeviceSources.includes('others') && !customDeviceSource.trim()) {
        setJsonError('Please enter at least one custom source when "others" is selected.');
        setSaving(false);
        return;
      }

      const payload: Partial<DeviceList> = {
        ...formData,
        device_source: serializedDeviceSource,
        power_model_config: parsedPowerModel,
        weather_device_config: parsedWeatherConfig,
        tilt_configs: finalTiltConfigs,
      };

      await onSave(payload);
    } catch (err) {
      setJsonError(err instanceof Error ? err.message : 'Invalid input in advanced configuration fields.');
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal fade" id="deviceFormModal" tabIndex={-1} aria-hidden="true">
      <div className="modal-dialog modal-xl">
        <div className="modal-content">
          <div className="modal-header">
            <h5 className="modal-title font-bold text-slate-900">
              {device ? 'Edit Device' : 'Add New Device'}
            </h5>
            <button type="button" className="btn-close" data-bs-dismiss="modal" aria-label="Close" />
          </div>
          <form onSubmit={handleSubmit}>
            <div className="modal-body">
              <div className="row">
                <div className="col-md-6 mb-3">
                  <label htmlFor="deviceId" className="form-label font-bold text-slate-900">
                    Device ID <span className="text-danger">*</span>
                  </label>
                  <input
                    id="deviceId"
                    className="form-control"
                    value={formData.device_id || ''}
                    onChange={(e) => handleChange('device_id', e.target.value)}
                    required
                    disabled={!!device}
                  />
                </div>
                <div className="col-md-6 mb-3">
                  <label htmlFor="deviceName" className="form-label font-bold text-slate-900">
                    Device Name <span className="text-danger">*</span>
                  </label>
                  <input
                    id="deviceName"
                    className="form-control"
                    value={formData.device_name || ''}
                    onChange={(e) => handleChange('device_name', e.target.value)}
                    required
                  />
                </div>
                <div className="col-md-6 mb-3">
                  <label htmlFor="deviceSerial" className="form-label font-bold text-slate-900">
                    Device serial
                  </label>
                  <input
                    id="deviceSerial"
                    className="form-control"
                    value={formData.device_serial || ''}
                    onChange={(e) => handleChange('device_serial', e.target.value)}
                    placeholder="Equipment / meter serial (e.g. for ERH meter reading source)"
                    autoComplete="off"
                  />
                  <small className="text-muted">
                    For meter devices (device type 63), this serial is used as the invoice &quot;Meter reading
                    source&quot; when parent code matches the asset.
                  </small>
                </div>

                <div className="col-md-6 mb-3">
                  <label htmlFor="deviceType" className="form-label font-bold text-slate-900">
                    Device Type <span className="text-danger">*</span>
                  </label>
                  <input
                    id="deviceType"
                    className="form-control"
                    value={formData.device_type || ''}
                    onChange={(e) => handleChange('device_type', e.target.value)}
                    required
                  />
                </div>
                <div className="col-md-6 mb-3">
                  <label htmlFor="country" className="form-label font-bold text-slate-900">
                    Country <span className="text-danger">*</span>
                  </label>
                  <input
                    id="country"
                    className="form-control"
                    value={formData.country || ''}
                    onChange={(e) => handleChange('country', e.target.value)}
                    required
                  />
                </div>

                <div className="col-md-6 mb-3">
                  <label htmlFor="parentCode" className="form-label font-bold text-slate-900">
                    Parent Code
                  </label>
                  <input
                    id="parentCode"
                    className="form-control"
                    value={formData.parent_code || ''}
                    onChange={(e) => handleChange('parent_code', e.target.value)}
                  />
                </div>
                <div className="col-md-6 mb-3">
                  <label htmlFor="deviceSource" className="form-label font-bold text-slate-900">
                    Device Source
                  </label>
                  <div className="position-relative" ref={deviceSourceDropdownRef}>
                    <button
                      id="deviceSource"
                      type="button"
                      className="btn btn-sm w-100 d-flex justify-content-between align-items-center border"
                      onClick={() => setDeviceSourceDropdownOpen((prev) => !prev)}
                    >
                      <span>
                        {selectedDeviceSources.length === 0
                          ? 'Select device source'
                          : `${selectedDeviceSources.length} selected`}
                      </span>
                      <span>{deviceSourceDropdownOpen ? '▲' : '▼'}</span>
                    </button>
                    {deviceSourceDropdownOpen && (
                      <div
                        className="position-absolute mt-1 w-100 p-2 rounded border bg-white shadow-sm"
                        style={{ maxHeight: '220px', overflowY: 'auto', zIndex: 20 }}
                      >
                        {[...DEVICE_SOURCE_OPTIONS]
                          .sort((a, b) => {
                            const aSelected = selectedDeviceSources.includes(a) ? 0 : 1;
                            const bSelected = selectedDeviceSources.includes(b) ? 0 : 1;
                            if (aSelected !== bSelected) return aSelected - bSelected;
                            return a.localeCompare(b);
                          })
                          .map((option) => (
                            <div key={option} className="form-check">
                              <input
                                id={`deviceSource-${option}`}
                                type="checkbox"
                                className="form-check-input"
                                checked={selectedDeviceSources.includes(option)}
                                onChange={(e) => {
                                  setSelectedDeviceSources((prev) => {
                                    if (e.target.checked) return [...prev, option];
                                    return prev.filter((item) => item !== option);
                                  });
                                }}
                              />
                              <label htmlFor={`deviceSource-${option}`} className="form-check-label text-capitalize">
                                {option.replace('_', ' ')}
                              </label>
                            </div>
                          ))}
                      </div>
                    )}
                  </div>
                  <div className="d-flex flex-wrap gap-1 mt-2">
                    {selectedDeviceSources.map((source) => (
                      <span key={`source-chip-${source}`} className="badge text-bg-primary">
                        {source.replace('_', ' ')}
                      </span>
                    ))}
                  </div>
                  {selectedDeviceSources.includes('others') && (
                    <input
                      className="form-control mt-2"
                      placeholder="Enter custom source(s), separated by commas"
                      value={customDeviceSource}
                      onChange={(e) => setCustomDeviceSource(e.target.value)}
                    />
                  )}
                </div>

                <div className="col-md-6 mb-3">
                  <label htmlFor="latitude" className="form-label font-bold text-slate-900">
                    Latitude
                  </label>
                  <input
                    id="latitude"
                    type="number"
                    step="0.000001"
                    className="form-control"
                    value={formData.latitude ?? ''}
                    onChange={(e) => handleChange('latitude', e.target.value ? parseFloat(e.target.value) : 0)}
                  />
                </div>
                <div className="col-md-6 mb-3">
                  <label htmlFor="longitude" className="form-label font-bold text-slate-900">
                    Longitude
                  </label>
                  <input
                    id="longitude"
                    type="number"
                    step="0.000001"
                    className="form-control"
                    value={formData.longitude ?? ''}
                    onChange={(e) => handleChange('longitude', e.target.value ? parseFloat(e.target.value) : 0)}
                  />
                </div>

                <div className="col-md-6 mb-3">
                  <label htmlFor="dcCap" className="form-label font-bold text-slate-900">
                    DC Capacity
                  </label>
                  <input
                    id="dcCap"
                    type="number"
                    step="0.01"
                    className="form-control"
                    value={formData.dc_cap ?? ''}
                    onChange={(e) => handleChange('dc_cap', e.target.value ? parseFloat(e.target.value) : 0)}
                  />
                </div>
                <div className="col-md-6 mb-3">
                  <label htmlFor="acCap" className="form-label font-bold text-slate-900">
                    AC Capacity
                  </label>
                  <input
                    id="acCap"
                    type="number"
                    step="0.01"
                    className="form-control"
                    value={formData.ac_capacity ?? ''}
                    onChange={(e) => handleChange('ac_capacity', e.target.value ? parseFloat(e.target.value) : null)}
                  />
                </div>

                <div className="col-md-6 mb-3">
                  <label htmlFor="optimizerNo" className="form-label font-bold text-slate-900">
                    Optimizer No.
                  </label>
                  <input
                    id="optimizerNo"
                    type="number"
                    className="form-control"
                    value={formData.optimizer_no ?? ''}
                    onChange={(e) => handleChange('optimizer_no', e.target.value ? parseInt(e.target.value, 10) : 0)}
                  />
                </div>
                <div className="col-md-6 mb-3">
                  <label htmlFor="deviceCode" className="form-label font-bold text-slate-900">
                    Device Code
                  </label>
                  <input
                    id="deviceCode"
                    className="form-control"
                    value={formData.device_code || ''}
                    onChange={(e) => handleChange('device_code', e.target.value)}
                  />
                </div>

                <div className="col-md-6 mb-3">
                  <label htmlFor="deviceModel" className="form-label font-bold text-slate-900">
                    Device Model
                  </label>
                  <input
                    id="deviceModel"
                    className="form-control"
                    value={formData.device_model || ''}
                    onChange={(e) => handleChange('device_model', e.target.value)}
                  />
                </div>
                <div className="col-md-6 mb-3">
                  <label htmlFor="deviceMake" className="form-label font-bold text-slate-900">
                    Device Make
                  </label>
                  <input
                    id="deviceMake"
                    className="form-control"
                    value={formData.device_make || ''}
                    onChange={(e) => handleChange('device_make', e.target.value)}
                  />
                </div>

                <div className="col-md-6 mb-3">
                  <label htmlFor="softwareVersion" className="form-label font-bold text-slate-900">
                    Software Version
                  </label>
                  <input
                    id="softwareVersion"
                    className="form-control"
                    value={formData.software_version || ''}
                    onChange={(e) => handleChange('software_version', e.target.value)}
                  />
                </div>
                <div className="col-md-6 mb-3">
                  <label htmlFor="stringNo" className="form-label font-bold text-slate-900">
                    String No.
                  </label>
                  <input
                    id="stringNo"
                    className="form-control"
                    value={formData.string_no || ''}
                    onChange={(e) => handleChange('string_no', e.target.value)}
                  />
                </div>

                <div className="col-md-6 mb-3">
                  <label htmlFor="connectedStrings" className="form-label font-bold text-slate-900">
                    Connected Strings
                  </label>
                  <input
                    id="connectedStrings"
                    className="form-control"
                    value={formData.connected_strings || ''}
                    onChange={(e) => handleChange('connected_strings', e.target.value)}
                  />
                </div>
                <div className="col-md-6 mb-3">
                  <label htmlFor="location" className="form-label font-bold text-slate-900">
                    Location
                  </label>
                  <input
                    id="location"
                    className="form-control"
                    value={formData.location || ''}
                    onChange={(e) => handleChange('location', e.target.value)}
                  />
                </div>
              </div>

              {/* PV module configuration and advanced fields */}
              <hr />
              <h6 className="font-bold text-slate-900 mb-3">PV Module & Advanced Configuration</h6>
              <div className="row">
                <div className="col-md-4 mb-3">
                  <label htmlFor="moduleDatasheetId" className="form-label font-bold text-slate-900">
                    Module Datasheet ID
                  </label>
                  <input
                    id="moduleDatasheetId"
                    type="number"
                    className="form-control"
                    value={formData.module_datasheet_id ?? ''}
                    onChange={(e) =>
                      handleChange('module_datasheet_id', e.target.value ? parseInt(e.target.value, 10) : null)
                    }
                  />
                </div>
                <div className="col-md-4 mb-3">
                  <label htmlFor="modulesInSeries" className="form-label font-bold text-slate-900">
                    Modules in Series
                  </label>
                  <input
                    id="modulesInSeries"
                    type="number"
                    className="form-control"
                    value={formData.modules_in_series ?? ''}
                    onChange={(e) =>
                      handleChange('modules_in_series', e.target.value ? parseInt(e.target.value, 10) : null)
                    }
                  />
                </div>
                <div className="col-md-4 mb-3">
                  <label htmlFor="installationDate" className="form-label font-bold text-slate-900">
                    Installation Date
                  </label>
                  <input
                    id="installationDate"
                    type="date"
                    className="form-control"
                    value={formData.installation_date || ''}
                    onChange={(e) => handleChange('installation_date', e.target.value || null)}
                  />
                </div>

                <div className="col-md-4 mb-3">
                  <label htmlFor="tiltAngle" className="form-label font-bold text-slate-900">
                    Tilt Angle (deg)
                  </label>
                  <input
                    id="tiltAngle"
                    type="number"
                    step="0.1"
                    className="form-control"
                    value={formData.tilt_angle ?? ''}
                    onChange={(e) =>
                      handleChange('tilt_angle', e.target.value ? parseFloat(e.target.value) : null)
                    }
                  />
                </div>
                <div className="col-md-4 mb-3">
                  <label htmlFor="azimuthAngle" className="form-label font-bold text-slate-900">
                    Azimuth Angle (deg)
                  </label>
                  <input
                    id="azimuthAngle"
                    type="number"
                    step="0.1"
                    className="form-control"
                    value={formData.azimuth_angle ?? ''}
                    onChange={(e) =>
                      handleChange('azimuth_angle', e.target.value ? parseFloat(e.target.value) : null)
                    }
                  />
                </div>
                <div className="col-md-4 mb-3">
                  <label htmlFor="mountingType" className="form-label font-bold text-slate-900">
                    Mounting Type
                  </label>
                  <input
                    id="mountingType"
                    className="form-control"
                    value={formData.mounting_type || ''}
                    onChange={(e) => handleChange('mounting_type', e.target.value)}
                  />
                </div>

                <div className="col-md-4 mb-3">
                  <label htmlFor="expectedSoilingLoss" className="form-label font-bold text-slate-900">
                    Expected Soiling Loss (%)
                  </label>
                  <input
                    id="expectedSoilingLoss"
                    type="number"
                    step="0.1"
                    className="form-control"
                    value={formData.expected_soiling_loss ?? ''}
                    onChange={(e) =>
                      handleChange(
                        'expected_soiling_loss',
                        e.target.value !== '' ? parseFloat(e.target.value) : null,
                      )
                    }
                  />
                </div>
                <div className="col-md-4 mb-3">
                  <label htmlFor="shadingFactor" className="form-label font-bold text-slate-900">
                    Shading Factor (%)
                  </label>
                  <input
                    id="shadingFactor"
                    type="number"
                    step="0.1"
                    className="form-control"
                    value={formData.shading_factor ?? ''}
                    onChange={(e) =>
                      handleChange('shading_factor', e.target.value !== '' ? parseFloat(e.target.value) : null)
                    }
                  />
                </div>
                <div className="col-md-4 mb-3">
                  <label htmlFor="measuredDegradationRate" className="form-label font-bold text-slate-900">
                    Measured Degradation (%/year)
                  </label>
                  <input
                    id="measuredDegradationRate"
                    type="number"
                    step="0.01"
                    className="form-control"
                    value={formData.measured_degradation_rate ?? ''}
                    onChange={(e) =>
                      handleChange(
                        'measured_degradation_rate',
                        e.target.value !== '' ? parseFloat(e.target.value) : null,
                      )
                    }
                  />
                </div>

                <div className="col-md-4 mb-3">
                  <label htmlFor="lastPerformanceTestDate" className="form-label font-bold text-slate-900">
                    Last Performance Test Date
                  </label>
                  <input
                    id="lastPerformanceTestDate"
                    type="date"
                    className="form-control"
                    value={formData.last_performance_test_date || ''}
                    onChange={(e) => handleChange('last_performance_test_date', e.target.value || null)}
                  />
                </div>
                <div className="col-md-4 mb-3">
                  <label htmlFor="powerModelId" className="form-label font-bold text-slate-900">
                    Power Model ID
                  </label>
                  <input
                    id="powerModelId"
                    type="number"
                    className="form-control"
                    value={formData.power_model_id ?? ''}
                    onChange={(e) =>
                      handleChange('power_model_id', e.target.value ? parseInt(e.target.value, 10) : null)
                    }
                  />
                </div>
                <div className="col-md-4 mb-3 d-flex align-items-center">
                  <div className="form-check mt-4">
                    <input
                      id="modelFallbackEnabled"
                      type="checkbox"
                      className="form-check-input"
                      checked={formData.model_fallback_enabled ?? true}
                      onChange={(e) => handleChange('model_fallback_enabled', e.target.checked)}
                    />
                    <label htmlFor="modelFallbackEnabled" className="form-check-label ms-2">
                      Model Fallback Enabled
                    </label>
                  </div>
                </div>

                <div className="col-md-12 mb-3">
                  <label htmlFor="operationalNotes" className="form-label font-bold text-slate-900">
                    Operational Notes
                  </label>
                  <textarea
                    id="operationalNotes"
                    className="form-control"
                    rows={2}
                    value={formData.operational_notes || ''}
                    onChange={(e) => handleChange('operational_notes', e.target.value)}
                  />
                </div>

                <div className="col-md-6 mb-3">
                  <label className="form-label font-bold text-slate-900">Power Model Config</label>
                  <div className="table-responsive border rounded p-2">
                    <table className="table table-sm mb-2">
                      <thead>
                        <tr>
                          <th>param</th>
                          <th>value</th>
                        </tr>
                      </thead>
                      <tbody>
                        {powerModelRows.map((row, idx) => (
                          <tr key={`power-${idx}`}>
                            <td>
                              <input
                                className="form-control form-control-sm"
                                placeholder="e.g. model_name"
                                value={row.param}
                                onChange={(e) => {
                                  const value = e.target.value;
                                  setPowerModelRows((prev) =>
                                    prev.map((item, i) => (i === idx ? { ...item, param: value } : item)),
                                  );
                                }}
                              />
                            </td>
                            <td>
                              <input
                                className="form-control form-control-sm"
                                placeholder="e.g. default"
                                value={row.value}
                                onChange={(e) => {
                                  const value = e.target.value;
                                  setPowerModelRows((prev) =>
                                    prev.map((item, i) => (i === idx ? { ...item, value } : item)),
                                  );
                                }}
                              />
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    <button
                      type="button"
                      className="btn btn-outline-secondary btn-sm"
                      onClick={() => setPowerModelRows((prev) => [...prev, { param: '', value: '' }])}
                    >
                      + Add Row
                    </button>
                  </div>
                </div>
                <div className="col-md-6 mb-3">
                  <label className="form-label font-bold text-slate-900">
                    Weather Device Config
                  </label>
                  <div className="table-responsive border rounded p-2">
                    <table className="table table-sm mb-2">
                      <thead>
                        <tr>
                          <th>irradiance_devices</th>
                          <th>temperature_devices</th>
                        </tr>
                      </thead>
                      <tbody>
                        {weatherConfigRows.map((row, idx) => (
                          <tr key={`weather-${idx}`}>
                            <td>
                              <input
                                className="form-control form-control-sm"
                                placeholder="e.g. dev1"
                                value={row.irradiance_device}
                                onChange={(e) => {
                                  const value = e.target.value;
                                  setWeatherConfigRows((prev) =>
                                    prev.map((item, i) => (i === idx ? { ...item, irradiance_device: value } : item)),
                                  );
                                }}
                              />
                            </td>
                            <td>
                              <input
                                className="form-control form-control-sm"
                                placeholder="e.g. dev2"
                                value={row.temperature_device}
                                onChange={(e) => {
                                  const value = e.target.value;
                                  setWeatherConfigRows((prev) =>
                                    prev.map((item, i) => (i === idx ? { ...item, temperature_device: value } : item)),
                                  );
                                }}
                              />
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    <button
                      type="button"
                      className="btn btn-outline-secondary btn-sm"
                      onClick={() =>
                        setWeatherConfigRows((prev) => [...prev, { irradiance_device: '', temperature_device: '' }])
                      }
                    >
                      + Add Row
                    </button>
                  </div>
                </div>

                <div className="col-md-12 mb-3">
                  <h6 className="font-bold text-slate-900 mb-1">Inverter SDM Groups (Tilt Configs)</h6>
                  <p className="small text-muted mb-2">
                    Same structure as Site onboarding → PV Modules → inverter configuration. Stored in{' '}
                    <code>device_list.tilt_configs</code>. Existing rows with only tilt/azimuth/panel are loaded and
                    defaulted for orientation, string count, and modules in series.
                  </p>
                  <div className="table-responsive border rounded p-2">
                    <table className="table table-sm mb-2">
                      <thead>
                        <tr>
                          <th>Tilt (°)</th>
                          <th>Azimuth (°)</th>
                          <th>Orientation</th>
                          <th>String count</th>
                          <th>Modules in series</th>
                          <th>Panel count</th>
                          <th className="text-center">Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {tiltConfigRows.map((row, idx) => (
                          <tr key={`tilt-${idx}`}>
                            <td>
                              <input
                                type="number"
                                step="0.1"
                                className="form-control form-control-sm"
                                value={row.tilt_deg}
                                onChange={(e) => handleTiltFieldChange(idx, 'tilt_deg', e.target.value)}
                              />
                            </td>
                            <td>
                              <input
                                type="number"
                                step="0.1"
                                className="form-control form-control-sm"
                                value={row.azimuth_deg}
                                onChange={(e) => handleTiltFieldChange(idx, 'azimuth_deg', e.target.value)}
                              />
                            </td>
                            <td>
                              <input
                                type="text"
                                className="form-control form-control-sm"
                                placeholder="North / South / East / West"
                                value={row.orientation || ''}
                                onChange={(e) => handleTiltFieldChange(idx, 'orientation', e.target.value)}
                              />
                            </td>
                            <td>
                              <input
                                type="number"
                                className="form-control form-control-sm"
                                value={row.string_count}
                                onChange={(e) => handleTiltFieldChange(idx, 'string_count', e.target.value)}
                              />
                            </td>
                            <td>
                              <input
                                type="number"
                                className="form-control form-control-sm"
                                value={row.modules_in_series}
                                onChange={(e) => handleTiltFieldChange(idx, 'modules_in_series', e.target.value)}
                              />
                            </td>
                            <td>
                              <input
                                type="number"
                                className="form-control form-control-sm"
                                value={row.panel_count}
                                onChange={(e) => handleTiltFieldChange(idx, 'panel_count', e.target.value)}
                              />
                            </td>
                            <td className="text-center">
                              <button
                                type="button"
                                className="btn btn-sm btn-outline-danger"
                                onClick={() => removeTiltRow(idx)}
                                disabled={tiltConfigRows.length <= 1}
                                title="Remove group"
                              >
                                ✕
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    <button type="button" className="btn btn-outline-secondary btn-sm" onClick={addTiltRow}>
                      + Add group
                    </button>
                  </div>
                </div>

                {jsonError && (
                  <div className="col-12">
                    <div className="alert alert-danger mt-2 mb-0">{jsonError}</div>
                  </div>
                )}
              </div>
            </div>
            <div className="modal-footer">
              <button type="button" className="btn btn-secondary" data-bs-dismiss="modal" disabled={saving}>
                Cancel
              </button>
              <button type="submit" className="btn btn-primary" disabled={saving}>
                {saving ? 'Saving...' : 'Save'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}


