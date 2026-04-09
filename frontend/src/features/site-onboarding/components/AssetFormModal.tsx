 
import { useState, useEffect } from 'react';
import type { AssetList } from '../types';
import { getUniqueApiNames } from '../api';

interface AssetFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (data: Partial<AssetList>) => void;
  asset: AssetList | null;
}

type TiltConfigRow = { tilt_deg: string; azimuth_deg: string; panel_count: string };

export function AssetFormModal({ isOpen, onClose, onSave, asset }: AssetFormModalProps) {
  const [formData, setFormData] = useState<Partial<AssetList>>({
    asset_code: '',
    asset_name: '',
    provider_asset_id: '',
    capacity: 0,
    address: '',
    country: '',
    latitude: 0,
    longitude: 0,
    contact_person: '',
    contact_method: '',
    grid_connection_date: '',
    asset_number: '',
    customer_name: '',
    portfolio: '',
    timezone: '',
    asset_name_oem: '',
    cod: '',
    operational_cod: '',
    y1_degradation: null,
    anual_degradation: null,
    api_name: '',
    api_key: '',
    tilt_configs: null,
    altitude_m: null,
    albedo: null,
    pv_syst_pr: null,
    satellite_irradiance_source_asset_code: null,
  });
  const [tiltConfigRows, setTiltConfigRows] = useState<TiltConfigRow[]>([
    { tilt_deg: '', azimuth_deg: '', panel_count: '' },
  ]);
  const [numericInputs, setNumericInputs] = useState<Record<string, string>>({});
  const [tiltConfigsError, setTiltConfigsError] = useState<string | null>(null);
  const [apiNames, setApiNames] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setTiltConfigsError(null);
      if (asset) {
        // Edit mode - populate form with asset data
        setFormData({
          asset_code: asset.asset_code,
          asset_name: asset.asset_name,
          provider_asset_id: asset.provider_asset_id ?? '',
          capacity: asset.capacity,
          address: asset.address,
          country: asset.country,
          latitude: asset.latitude,
          longitude: asset.longitude,
          contact_person: asset.contact_person,
          contact_method: asset.contact_method,
          grid_connection_date: asset.grid_connection_date ? (asset.grid_connection_date.includes('T') ? asset.grid_connection_date.slice(0, 16) : asset.grid_connection_date + 'T00:00') : '',
          asset_number: asset.asset_number,
          customer_name: asset.customer_name,
          portfolio: asset.portfolio,
          timezone: asset.timezone,
          asset_name_oem: asset.asset_name_oem,
          cod: asset.cod && asset.cod.trim() !== '' ? asset.cod.slice(0, 10) : '',
          operational_cod: asset.operational_cod && asset.operational_cod.trim() !== '' ? asset.operational_cod.slice(0, 10) : '',
          y1_degradation: asset.y1_degradation,
          anual_degradation: asset.anual_degradation,
          api_name: asset.api_name,
          api_key: asset.api_key,
          tilt_configs: asset.tilt_configs ?? null,
          altitude_m: asset.altitude_m ?? null,
          albedo: asset.albedo ?? null,
          pv_syst_pr: asset.pv_syst_pr ?? null,
          satellite_irradiance_source_asset_code: asset.satellite_irradiance_source_asset_code ?? null,
        });
        const parsedTiltConfigs = (() => {
          const t = asset.tilt_configs;
          if (t == null) return [];
          if (typeof t === 'string') {
            try {
              const parsed = JSON.parse(t);
              return Array.isArray(parsed) ? parsed : [];
            } catch {
              return [];
            }
          }
          return Array.isArray(t) ? t : [];
        })();
        setTiltConfigRows(
          parsedTiltConfigs.length
            ? parsedTiltConfigs.map((row) => ({
                tilt_deg: row?.tilt_deg != null ? String(row.tilt_deg) : '',
                azimuth_deg: row?.azimuth_deg != null ? String(row.azimuth_deg) : '',
                panel_count: row?.panel_count != null ? String(row.panel_count) : '',
              }))
            : [{ tilt_deg: '', azimuth_deg: '', panel_count: '' }],
        );
        setNumericInputs({
          capacity: asset.capacity != null ? String(asset.capacity) : '',
          latitude: asset.latitude != null ? String(asset.latitude) : '',
          longitude: asset.longitude != null ? String(asset.longitude) : '',
          y1_degradation: asset.y1_degradation != null ? String(asset.y1_degradation) : '',
          anual_degradation: asset.anual_degradation != null ? String(asset.anual_degradation) : '',
          altitude_m: asset.altitude_m != null ? String(asset.altitude_m) : '',
          albedo: asset.albedo != null ? String(asset.albedo) : '',
          pv_syst_pr: asset.pv_syst_pr != null ? String(asset.pv_syst_pr) : '',
        });
      } else {
        // Add mode - reset form
        setFormData({
          asset_code: '',
          asset_name: '',
          provider_asset_id: '',
          capacity: 0,
          address: '',
          country: '',
          latitude: 0,
          longitude: 0,
          contact_person: '',
          contact_method: '',
          grid_connection_date: '',
          asset_number: '',
          customer_name: '',
          portfolio: '',
          timezone: '',
          asset_name_oem: '',
          cod: '',
          operational_cod: '',
          y1_degradation: null,
          anual_degradation: null,
          api_name: '',
          api_key: '',
          tilt_configs: null,
          altitude_m: null,
          albedo: null,
          pv_syst_pr: null,
          satellite_irradiance_source_asset_code: null,
        });
        setTiltConfigRows([{ tilt_deg: '', azimuth_deg: '', panel_count: '' }]);
        setNumericInputs({
          capacity: '',
          latitude: '',
          longitude: '',
          y1_degradation: '',
          anual_degradation: '',
          altitude_m: '',
          albedo: '',
          pv_syst_pr: '',
        });
      }

      // Load API name suggestions
      loadApiNames();
    }
  }, [isOpen, asset]);

  const loadApiNames = async () => {
    try {
      const response = await getUniqueApiNames();
      if (response.success) {
        setApiNames(response.api_names);
      }
    } catch (error) {
      console.error('Failed to load API names:', error);
    }
  };

  useEffect(() => {
    if (isOpen) {
      const modalElement = document.getElementById('assetModal');
      if (modalElement) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const modal = new (window as any).bootstrap.Modal(modalElement);
        modal.show();

        const handleHidden = () => {
          onClose();
        };
        modalElement.addEventListener('hidden.bs.modal', handleHidden);

        return () => {
          modalElement.removeEventListener('hidden.bs.modal', handleHidden);
          modal.dispose();
        };
      }
    }
  }, [isOpen, onClose]);

  const handleChange = (field: keyof AssetList, value: string | number | null) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleNumericInputChange = (field: keyof AssetList, value: string) => {
    setNumericInputs((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setTiltConfigsError(null);
    setSaving(true);

    try {
      const parsedTiltConfigs = tiltConfigRows.reduce<NonNullable<AssetList['tilt_configs']>>((acc, row) => {
        const tilt = row.tilt_deg.trim();
        const azimuth = row.azimuth_deg.trim();
        const panel = row.panel_count.trim();
        if (!tilt && !azimuth && !panel) return acc;
        const tiltNum = Number(tilt);
        const azimuthNum = Number(azimuth);
        const panelNum = Number(panel);
        if (Number.isNaN(tiltNum) || Number.isNaN(azimuthNum) || Number.isNaN(panelNum)) {
          throw new Error('Tilt configs must contain valid numeric values.');
        }
        acc.push({ tilt_deg: tiltNum, azimuth_deg: azimuthNum, panel_count: panelNum });
        return acc;
      }, []);

      const parseOptionalNumber = (rawVal: string): number | null => {
        const trimmed = rawVal.trim();
        if (!trimmed) return null;
        const num = Number(trimmed);
        return Number.isNaN(num) ? null : num;
      };

      const parseRequiredNumber = (rawVal: string, fallback: number): number => {
        const parsed = parseOptionalNumber(rawVal);
        return parsed == null ? fallback : parsed;
      };
      // Convert date strings to ISO format
      const data: Partial<AssetList> = {
        ...formData,
        capacity: parseRequiredNumber(numericInputs.capacity ?? '', 0),
        latitude: parseRequiredNumber(numericInputs.latitude ?? '', 0),
        longitude: parseRequiredNumber(numericInputs.longitude ?? '', 0),
        y1_degradation: parseOptionalNumber(numericInputs.y1_degradation ?? ''),
        anual_degradation: parseOptionalNumber(numericInputs.anual_degradation ?? ''),
        altitude_m: parseOptionalNumber(numericInputs.altitude_m ?? ''),
        albedo: parseOptionalNumber(numericInputs.albedo ?? ''),
        pv_syst_pr: parseOptionalNumber(numericInputs.pv_syst_pr ?? ''),
        provider_asset_id: (formData.provider_asset_id || '').trim() || undefined,
        grid_connection_date: formData.grid_connection_date
          ? new Date(formData.grid_connection_date).toISOString()
          : '',
        // Date-only fields: backend stores with time as 00:00:00
        cod: formData.cod ? `${formData.cod}T00:00:00` : '',
        operational_cod: formData.operational_cod ? `${formData.operational_cod}T00:00:00` : '',
        tilt_configs: parsedTiltConfigs.length ? parsedTiltConfigs : null,
        satellite_irradiance_source_asset_code: formData.satellite_irradiance_source_asset_code ?? null,
      };

      await onSave(data);
    } catch (error) {
      console.error('Save error:', error);
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div
      className="modal fade"
      id="assetModal"
      tabIndex={-1}
      aria-labelledby="assetModalLabel"
      aria-hidden="true"
    >
      <div className="modal-dialog modal-xl">
        <div className="modal-content">
          <div className="modal-header">
            <h5 className="modal-title font-bold text-slate-900" id="assetModalLabel">
              {asset ? 'Edit Asset' : 'Add New Asset'}
            </h5>
            <button
              type="button"
              className="btn-close"
              data-bs-dismiss="modal"
              aria-label="Close"
              onClick={onClose}
            />
          </div>
          <form onSubmit={handleSubmit}>
            <div className="modal-body">
              <div className="row">
                <div className="col-md-6 mb-3">
                  <label htmlFor="assetCode" className="form-label font-bold text-slate-900">
                    Asset Code <span className="text-danger">*</span>
                  </label>
                  <input
                    type="text"
                    className="form-control"
                    id="assetCode"
                    value={formData.asset_code || ''}
                    onChange={(e) => handleChange('asset_code', e.target.value)}
                    required
                    disabled={!!asset}
                  />
                </div>
                <div className="col-md-6 mb-3">
                  <label htmlFor="assetName" className="form-label font-bold text-slate-900">
                    Asset Name <span className="text-danger">*</span>
                  </label>
                  <input
                    type="text"
                    className="form-control"
                    id="assetName"
                    value={formData.asset_name || ''}
                    onChange={(e) => handleChange('asset_name', e.target.value)}
                    required
                  />
                </div>
                <div className="col-md-6 mb-3">
                  <label htmlFor="providerAssetId" className="form-label font-bold text-slate-900">
                    Provider asset ID (plant ID)
                  </label>
                  <input
                    type="text"
                    className="form-control"
                    id="providerAssetId"
                    value={formData.provider_asset_id || ''}
                    onChange={(e) => handleChange('provider_asset_id', e.target.value)}
                  />
                </div>
                <div className="col-md-6 mb-3">
                  <label htmlFor="assetCapacity" className="form-label font-bold text-slate-900">
                    Capacity (kWh)
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    className="form-control"
                    id="assetCapacity"
                    value={numericInputs.capacity ?? ''}
                    onChange={(e) => handleNumericInputChange('capacity', e.target.value)}
                  />
                </div>
                <div className="col-md-6 mb-3">
                  <label htmlFor="assetCountry" className="form-label font-bold text-slate-900">
                    Country <span className="text-danger">*</span>
                  </label>
                  <input
                    type="text"
                    className="form-control"
                    id="assetCountry"
                    value={formData.country || ''}
                    onChange={(e) => handleChange('country', e.target.value)}
                    required
                  />
                </div>
                <div className="col-md-6 mb-3">
                  <label htmlFor="assetPortfolio" className="form-label font-bold text-slate-900">
                    Portfolio <span className="text-danger">*</span>
                  </label>
                  <input
                    type="text"
                    className="form-control"
                    id="assetPortfolio"
                    value={formData.portfolio || ''}
                    onChange={(e) => handleChange('portfolio', e.target.value)}
                    required
                  />
                </div>
                <div className="col-md-6 mb-3">
                  <label htmlFor="assetAddress" className="form-label font-bold text-slate-900">
                    Address
                  </label>
                  <input
                    type="text"
                    className="form-control"
                    id="assetAddress"
                    value={formData.address || ''}
                    onChange={(e) => handleChange('address', e.target.value)}
                  />
                </div>
                <div className="col-md-6 mb-3">
                  <label htmlFor="assetLatitude" className="form-label font-bold text-slate-900">
                    Latitude
                  </label>
                  <input
                    type="number"
                    step="0.000001"
                    className="form-control"
                    id="assetLatitude"
                    value={numericInputs.latitude ?? ''}
                    onChange={(e) => handleNumericInputChange('latitude', e.target.value)}
                  />
                </div>
                <div className="col-md-6 mb-3">
                  <label htmlFor="assetLongitude" className="form-label font-bold text-slate-900">
                    Longitude
                  </label>
                  <input
                    type="number"
                    step="0.000001"
                    className="form-control"
                    id="assetLongitude"
                    value={numericInputs.longitude ?? ''}
                    onChange={(e) => handleNumericInputChange('longitude', e.target.value)}
                  />
                </div>
                <div className="col-md-6 mb-3">
                  <label htmlFor="assetContactPerson" className="form-label font-bold text-slate-900">
                    Contact Person
                  </label>
                  <input
                    type="text"
                    className="form-control"
                    id="assetContactPerson"
                    value={formData.contact_person || ''}
                    onChange={(e) => handleChange('contact_person', e.target.value)}
                  />
                </div>
                <div className="col-md-6 mb-3">
                  <label htmlFor="assetContactMethod" className="form-label font-bold text-slate-900">
                    Contact Method
                  </label>
                  <input
                    type="text"
                    className="form-control"
                    id="assetContactMethod"
                    value={formData.contact_method || ''}
                    onChange={(e) => handleChange('contact_method', e.target.value)}
                  />
                </div>
                <div className="col-md-6 mb-3">
                  <label htmlFor="assetGridConnection" className="form-label font-bold text-slate-900">
                    Grid Connection Date
                  </label>
                  <input
                    type="datetime-local"
                    className="form-control"
                    id="assetGridConnection"
                    value={formData.grid_connection_date || ''}
                    onChange={(e) => handleChange('grid_connection_date', e.target.value)}
                  />
                </div>
                <div className="col-md-6 mb-3">
                  <label htmlFor="assetNumber" className="form-label font-bold text-slate-900">
                    Asset Number
                  </label>
                  <input
                    type="text"
                    className="form-control"
                    id="assetNumber"
                    value={formData.asset_number || ''}
                    onChange={(e) => handleChange('asset_number', e.target.value)}
                  />
                </div>
                <div className="col-md-6 mb-3">
                  <label htmlFor="assetTimezone" className="form-label font-bold text-slate-900">
                    Timezone <span className="text-danger">*</span>
                  </label>
                  <input
                    type="text"
                    className="form-control"
                    id="assetTimezone"
                    value={formData.timezone || ''}
                    onChange={(e) => handleChange('timezone', e.target.value)}
                    required
                  />
                </div>
                <div className="col-md-6 mb-3">
                  <label htmlFor="assetCustomerName" className="form-label font-bold text-slate-900">
                    Customer Name
                  </label>
                  <input
                    type="text"
                    className="form-control"
                    id="assetCustomerName"
                    value={formData.customer_name || ''}
                    onChange={(e) => handleChange('customer_name', e.target.value)}
                  />
                </div>
                <div className="col-md-6 mb-3">
                  <label htmlFor="assetNameOem" className="form-label font-bold text-slate-900">
                    Asset Name OEM
                  </label>
                  <input
                    type="text"
                    className="form-control"
                    id="assetNameOem"
                    value={formData.asset_name_oem || ''}
                    onChange={(e) => handleChange('asset_name_oem', e.target.value)}
                  />
                </div>
                <div className="col-md-6 mb-3">
                  <label htmlFor="assetCod" className="form-label font-bold text-slate-900">
                    COD
                  </label>
                  <input
                    type="date"
                    className="form-control"
                    id="assetCod"
                    value={formData.cod || ''}
                    onChange={(e) => handleChange('cod', e.target.value)}
                  />
                </div>
                <div className="col-md-6 mb-3">
                  <label htmlFor="assetOperationalCod" className="form-label font-bold text-slate-900">
                    Operational COD
                  </label>
                  <input
                    type="date"
                    className="form-control"
                    id="assetOperationalCod"
                    value={formData.operational_cod || ''}
                    onChange={(e) => handleChange('operational_cod', e.target.value)}
                  />
                </div>
                <div className="col-md-6 mb-3">
                  <label htmlFor="assetY1Degradation" className="form-label font-bold text-slate-900">
                    Y1 Degradation (%)
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    className="form-control"
                    id="assetY1Degradation"
                    value={numericInputs.y1_degradation ?? ''}
                    onChange={(e) => handleNumericInputChange('y1_degradation', e.target.value)}
                  />
                </div>
                <div className="col-md-6 mb-3">
                  <label htmlFor="assetAnualDegradation" className="form-label font-bold text-slate-900">
                    Annual Degradation (%)
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    className="form-control"
                    id="assetAnualDegradation"
                    value={numericInputs.anual_degradation ?? ''}
                    onChange={(e) => handleNumericInputChange('anual_degradation', e.target.value)}
                  />
                </div>
                <div className="col-md-6 mb-3">
                  <label htmlFor="assetApiName" className="form-label font-bold text-slate-900">
                    API Name
                  </label>
                  <input
                    type="text"
                    className="form-control"
                    id="assetApiName"
                    list="apiNamesList"
                    value={formData.api_name || ''}
                    onChange={(e) => handleChange('api_name', e.target.value)}
                  />
                  <datalist id="apiNamesList">
                    {apiNames.map((name) => (
                      <option key={name} value={name} />
                    ))}
                  </datalist>
                </div>
                <div className="col-md-6 mb-3">
                  <label htmlFor="assetApiKey" className="form-label font-bold text-slate-900">
                    API Key
                  </label>
                  <input
                    type="text"
                    className="form-control"
                    id="assetApiKey"
                    value={formData.api_key || ''}
                    onChange={(e) => handleChange('api_key', e.target.value)}
                  />
                </div>
                <div className="col-md-4 mb-3">
                  <label htmlFor="assetAltitudeM" className="form-label font-bold text-slate-900">
                    Altitude (m)
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    className="form-control"
                    id="assetAltitudeM"
                    value={numericInputs.altitude_m ?? ''}
                    onChange={(e) => handleNumericInputChange('altitude_m', e.target.value)}
                  />
                </div>
                <div className="col-md-4 mb-3">
                  <label htmlFor="assetAlbedo" className="form-label font-bold text-slate-900">
                    Albedo (0–1)
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    className="form-control"
                    id="assetAlbedo"
                    value={numericInputs.albedo ?? ''}
                    onChange={(e) => handleNumericInputChange('albedo', e.target.value)}
                  />
                </div>
                <div className="col-md-4 mb-3">
                  <label htmlFor="assetPvSystPr" className="form-label font-bold text-slate-900">
                    PVsyst PR (0–1)
                  </label>
                  <input
                    type="number"
                    step="0.001"
                    className="form-control"
                    id="assetPvSystPr"
                    value={numericInputs.pv_syst_pr ?? ''}
                    onChange={(e) => handleNumericInputChange('pv_syst_pr', e.target.value)}
                    placeholder="e.g. 0.82"
                  />
                  <small className="text-muted">Performance Ratio for PR-based expected power model.</small>
                </div>
                <div className="col-md-6 mb-3">
                  <label htmlFor="assetSatelliteIrradianceSource" className="form-label font-bold text-slate-900">
                    Satellite Irradiance Source Asset Code
                  </label>
                  <input
                    type="text"
                    className="form-control"
                    id="assetSatelliteIrradianceSource"
                    value={formData.satellite_irradiance_source_asset_code || ''}
                    onChange={(e) =>
                      handleChange('satellite_irradiance_source_asset_code', e.target.value.trim() || null)
                    }
                    placeholder="Asset code used as satellite irradiance source"
                  />
                  <small className="text-muted">Asset code for satellite irradiance data (Data Collection).</small>
                </div>
                <div className="col-12 mb-3">
                  <label className="form-label font-bold text-slate-900">Tilt configs</label>
                  <div className={`table-responsive border rounded p-2 ${tiltConfigsError ? 'border-danger' : ''}`}>
                    <table className="table table-sm mb-2">
                      <thead>
                        <tr>
                          <th>tilt_deg</th>
                          <th>azimuth_deg</th>
                          <th>panel_count</th>
                        </tr>
                      </thead>
                      <tbody>
                        {tiltConfigRows.map((row, idx) => (
                          <tr key={`asset-tilt-${idx}`}>
                            <td>
                              <input
                                type="number"
                                step="0.1"
                                className="form-control form-control-sm"
                                placeholder="e.g. 25"
                                value={row.tilt_deg}
                                onChange={(e) => {
                                  const value = e.target.value;
                                  setTiltConfigRows((prev) =>
                                    prev.map((item, i) => (i === idx ? { ...item, tilt_deg: value } : item)),
                                  );
                                  if (tiltConfigsError) setTiltConfigsError(null);
                                }}
                              />
                            </td>
                            <td>
                              <input
                                type="number"
                                step="0.1"
                                className="form-control form-control-sm"
                                placeholder="e.g. -10"
                                value={row.azimuth_deg}
                                onChange={(e) => {
                                  const value = e.target.value;
                                  setTiltConfigRows((prev) =>
                                    prev.map((item, i) => (i === idx ? { ...item, azimuth_deg: value } : item)),
                                  );
                                  if (tiltConfigsError) setTiltConfigsError(null);
                                }}
                              />
                            </td>
                            <td>
                              <input
                                type="number"
                                className="form-control form-control-sm"
                                placeholder="e.g. 100"
                                value={row.panel_count}
                                onChange={(e) => {
                                  const value = e.target.value;
                                  setTiltConfigRows((prev) =>
                                    prev.map((item, i) => (i === idx ? { ...item, panel_count: value } : item)),
                                  );
                                  if (tiltConfigsError) setTiltConfigsError(null);
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
                        setTiltConfigRows((prev) => [...prev, { tilt_deg: '', azimuth_deg: '', panel_count: '' }])
                      }
                    >
                      + Add Row
                    </button>
                  </div>
                  {tiltConfigsError && (
                    <div className="invalid-feedback d-block">{tiltConfigsError}</div>
                  )}
                  <small className="text-muted">
                    Values are stored as JSON and shown again in this table when you reopen edit.
                  </small>
                </div>
              </div>
            </div>
            <div className="modal-footer">
              <button
                type="button"
                className="btn btn-secondary"
                data-bs-dismiss="modal"
                onClick={onClose}
                disabled={saving}
              >
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

