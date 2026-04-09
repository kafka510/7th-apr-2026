
import { useEffect, useState } from 'react';
import type { AdapterAccount, AssetAdapterConfig, AssetAdapterConfigConfig } from '../types';
import { getAllAssets, getDataCollectionAdapterIds, fetchAdapterAccounts } from '../api';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSave: (data: Partial<AssetAdapterConfig> & { asset_code: string; adapter_id: string }) => Promise<void> | void;
  config: AssetAdapterConfig | null;
}

const defaultConfig: AssetAdapterConfigConfig = {
  api_url: 'https://solargis.info/ws/rest/datadelivery/request',
  api_key: '',
  summarization: 'MIN_5',
  processing_keys: 'GHI DNI DIF GTI PVOUT TMOD TEMP WS WD RH CI_FLAG',
  terrain_shading: false,
  time_stamp_type: 'CENTER',
  tilt: 0,
  azimuth: 180,
  linked_asset_codes: [],
  asset_id: '',
};

const defaultFusionSolarConfig: AssetAdapterConfigConfig = {
  api_base_url: 'https://intl.fusionsolar.huawei.com/',
  username: '',
  password: '',
  plant_id: '',
  rate_limit_calls_per_minute: 30,
};

function getInitialFormState(config: AssetAdapterConfig | null) {
  if (config) {
    const adapter = config.adapter_id || 'solargis';
    const base = adapter === 'fusion_solar' ? defaultFusionSolarConfig : defaultConfig;
    const c = { ...base, ...(config.config || {}) };
    return {
      assetCode: config.asset_code,
      adapterId: adapter,
      enabled: config.enabled,
      interval: config.acquisition_interval_minutes ?? 5,
      cfg: c,
      linkedAssetCodesRaw: Array.isArray(c.linked_asset_codes) ? JSON.stringify(c.linked_asset_codes) : '[]',
    };
  }
  return {
    assetCode: '',
    adapterId: 'solargis' as const,
    enabled: true,
    interval: 5,
    cfg: { ...defaultConfig },
    linkedAssetCodesRaw: '[]',
  };
}

export function DataCollectionFormModal({ isOpen, onClose, onSave, config }: Props) {
  const initial = getInitialFormState(config);
  const [assetCode, setAssetCode] = useState(initial.assetCode);
  const [adapterId, setAdapterId] = useState(initial.adapterId);
  const [enabled, setEnabled] = useState(initial.enabled);
  const [interval, setInterval] = useState(initial.interval);
  const [cfg, setCfg] = useState<AssetAdapterConfigConfig>(initial.cfg);
  const [linkedAssetCodesRaw, setLinkedAssetCodesRaw] = useState(initial.linkedAssetCodesRaw);
  const [saving, setSaving] = useState(false);
  const [assets, setAssets] = useState<{ asset_code: string }[]>([]);
  const [adapterIds, setAdapterIds] = useState<string[]>(['solargis', 'fusion_solar']);
  const [accounts, setAccounts] = useState<AdapterAccount[]>([]);
  const [adapterAccountId, setAdapterAccountId] = useState<number | ''>(
    config?.adapter_account_id ?? ''
  );

  // Load assets and adapter IDs once
  useEffect(() => {
    getAllAssets().then((list) => setAssets(list)).catch(() => setAssets([]));
    getDataCollectionAdapterIds()
      .then((ids) => setAdapterIds(ids.length ? ids : ['solargis', 'fusion_solar']))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (isOpen) {
      if (config) {
        setAssetCode(config.asset_code);
        const adapter = config.adapter_id || 'solargis';
        setAdapterId(adapter);
        setEnabled(config.enabled);
        setInterval(config.acquisition_interval_minutes ?? 5);
        const base = adapter === 'fusion_solar' ? defaultFusionSolarConfig : defaultConfig;
        const c = { ...base, ...(config.config || {}) };
        setCfg(c);
        setLinkedAssetCodesRaw(
          Array.isArray(c.linked_asset_codes) ? JSON.stringify(c.linked_asset_codes) : '[]'
        );
        setAdapterAccountId(config.adapter_account_id ?? '');
      } else {
        setAssetCode('');
        setAdapterId('solargis');
        setEnabled(true);
        setInterval(5);
        setCfg({ ...defaultConfig });
        setLinkedAssetCodesRaw('[]');
        setAdapterAccountId('');
      }
      const modalEl = document.getElementById('dataCollectionModal');
      if (modalEl) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const modal = new (window as any).bootstrap.Modal(modalEl);
        modal.show();
        const handleHidden = () => onClose();
        modalEl.addEventListener('hidden.bs.modal', handleHidden);
        return () => {
          modalEl.removeEventListener('hidden.bs.modal', handleHidden);
          modal.dispose();
        };
      }
    }
    return undefined;
  }, [isOpen, config, onClose]);

  // Whenever modal is open, (re)load adapter accounts for selected adapter
  useEffect(() => {
    if (!isOpen) return;
    fetchAdapterAccounts(adapterId)
      .then((res) => setAccounts(res.data || []))
      .catch(() => setAccounts([]));
  }, [isOpen, adapterId]);

  const handleConfigChange = (field: keyof AssetAdapterConfigConfig, value: string | number | boolean | string[]) => {
    setCfg((prev) => ({ ...prev, [field]: value }));
  };

  const handleAdapterChange = (newAdapterId: string) => {
    setAdapterId(newAdapterId);
    setCfg(newAdapterId === 'fusion_solar' ? { ...defaultFusionSolarConfig } : { ...defaultConfig });
    if (newAdapterId === 'fusion_solar') setLinkedAssetCodesRaw('[]');
    // Keep existing accounts list; just reset selected account
    setAdapterAccountId('');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      let linked: string[] = [];
      try {
        const parsed = JSON.parse(linkedAssetCodesRaw || '[]');
        linked = Array.isArray(parsed) ? parsed.filter((x): x is string => typeof x === 'string') : [];
      } catch {
        // ignore
      }
      const finalConfig = adapterId === 'fusion_solar'
        ? { ...cfg, api_base_url: cfg.api_base_url ?? '', username: cfg.username ?? '', password: cfg.password ?? '', plant_id: cfg.plant_id ?? '', rate_limit_calls_per_minute: cfg.rate_limit_calls_per_minute ?? 30 }
        : { ...cfg, linked_asset_codes: linked };
      const payload = {
        id: config?.id,
        asset_code: assetCode.trim(),
        adapter_id: adapterId.trim(),
        adapter_account_id: adapterAccountId || undefined,
        config: finalConfig,
        acquisition_interval_minutes: [5, 30, 60, 1440].includes(interval) ? interval : Math.min(1440, Math.max(5, interval)),
        enabled,
      };
      await onSave(payload as Partial<AssetAdapterConfig> & { asset_code: string; adapter_id: string });
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal fade" id="dataCollectionModal" tabIndex={-1} aria-hidden="true">
      <div className="modal-dialog modal-xl">
        <div className="modal-content">
          <div className="modal-header">
            <h5 className="modal-title font-bold text-slate-900">
              {config ? 'Edit Data Collection Config' : 'Add Data Collection Config'}
            </h5>
            <button type="button" className="btn-close" data-bs-dismiss="modal" aria-label="Close" />
          </div>
          <form onSubmit={handleSubmit}>
            <div className="modal-body">
              <div className="row">
                <div className="col-md-6 mb-3">
                  <label className="form-label font-bold text-slate-900">
                    Asset Code <span className="text-danger">*</span>
                  </label>
                  <select
                    className="form-select"
                    value={assetCode}
                    onChange={(e) => setAssetCode(e.target.value)}
                    required
                    disabled={!!config}
                  >
                    <option value="">-- Select asset --</option>
                    {assets.map((a) => (
                      <option key={a.asset_code} value={a.asset_code}>
                        {a.asset_code}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="col-md-6 mb-3">
                  <label className="form-label font-bold text-slate-900">
                    Adapter <span className="text-danger">*</span>
                  </label>
                  <select
                    className="form-select"
                    value={adapterId}
                    onChange={(e) => handleAdapterChange(e.target.value)}
                    required
                    disabled={!!config}
                  >
                    {adapterIds.map((id) => (
                      <option key={id} value={id}>
                        {id === 'solargis' ? 'SolarGIS' : id === 'fusion_solar' ? 'Fusion Solar' : id}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="col-md-4 mb-3">
                  <label className="form-label font-bold text-slate-900">Enabled</label>
                  <select
                    className="form-select"
                    value={enabled ? 'yes' : 'no'}
                    onChange={(e) => setEnabled(e.target.value === 'yes')}
                  >
                    <option value="yes">Yes</option>
                    <option value="no">No</option>
                  </select>
                </div>
                <div className="col-md-4 mb-3">
                  <label className="form-label font-bold text-slate-900">Acquisition Interval</label>
                  <select
                    className="form-select"
                    value={interval}
                    onChange={(e) => setInterval(Number(e.target.value))}
                  >
                    <option value={5}>5 minutes</option>
                    <option value={30}>30 minutes</option>
                    <option value={60}>Hourly (60 min)</option>
                    <option value={1440}>Daily (24h)</option>
                  </select>
                  {adapterId === 'laplaceid' && (
                    <small className="text-muted">
                      LaplaceID uses fixed dual cadence: WH every 30 min and minute data every hour.
                      This field is kept for compatibility and does not control Laplace scheduler cadence.
                    </small>
                  )}
                </div>
              </div>
              <hr />
              <div className="row mb-3">
                <div className="col-md-6">
                  <label className="form-label font-bold text-slate-900">Adapter account</label>
                  <select
                    className="form-select"
                    value={adapterAccountId === '' ? '' : String(adapterAccountId)}
                    onChange={(e) => {
                      const val = e.target.value;
                      setAdapterAccountId(val ? Number(val) : '');
                    }}
                  >
                    <option value="">— None (inline config) —</option>
                    {accounts.map((a) => (
                      <option key={a.id} value={a.id}>
                        {a.name || `Account #${a.id}`}
                      </option>
                    ))}
                  </select>
                  <small className="text-muted">
                    When set, credentials come from this account; config below is per-asset overrides only.
                  </small>
                </div>
              </div>
              <hr />
              {adapterId === 'solargis' && (
                <>
                  <h6 className="font-bold mb-3">Adapter config (SolarGIS)</h6>
                  <div className="row">
                <div className="col-md-4 mb-3">
                  <label className="form-label font-bold text-slate-900">Daily run time (local)</label>
                  <input
                    type="time"
                    className="form-control"
                    value={cfg.daily_run_local_time ?? ''}
                    onChange={(e) => handleConfigChange('daily_run_local_time', e.target.value ? e.target.value : '')}
                  />
                  <small className="text-muted">Recommendation: source availability time + some expected delays (use with timezone below).</small>
                </div>
                <div className="col-md-4 mb-3">
                  <label className="form-label font-bold text-slate-900">Timezone</label>
                  <select
                    className="form-select"
                    value={cfg.daily_run_timezone ?? ''}
                    onChange={(e) => handleConfigChange('daily_run_timezone', e.target.value ? e.target.value : '')}
                  >
                    <option value="">—</option>
                    <option value="UTC">UTC</option>
                    <option value="+05:30">+05:30 (India)</option>
                    <option value="+08:00">+08:00 (Singapore)</option>
                    <option value="+09:00">+09:00 (Japan)</option>
                    <option value="-05:00">-05:00 (US Eastern)</option>
                    <option value="-08:00">-08:00 (US Pacific)</option>
                    <option value="+01:00">+01:00 (CET)</option>
                    <option value="+00:00">+00:00 (GMT)</option>
                  </select>
                  <small className="text-muted">Timezone for the local time above.</small>
                </div>
                <div className="col-md-4 mb-3">
                  <label className="form-label font-bold text-slate-900">Solargis Site ID (asset_id)</label>
                  <input
                    className="form-control"
                    value={cfg.asset_id || ''}
                    onChange={(e) => handleConfigChange('asset_id', e.target.value)}
                    placeholder="Optional; defaults to asset_code (prefixed if needed)"
                  />
                  <small className="text-muted">
                    Used as &lt;site id=&quot;...&quot;&gt; in Solargis requests. Must start with a letter; leave blank to
                    use asset_code (adapter will prefix if it starts with a digit).
                  </small>
                </div>
                <div className="col-12 mb-3">
                  <label className="form-label font-bold text-slate-900">API URL</label>
                  <input
                    className="form-control"
                    value={cfg.api_url || ''}
                    onChange={(e) => handleConfigChange('api_url', e.target.value)}
                  />
                </div>
                <div className="col-md-6 mb-3">
                  <label className="form-label font-bold text-slate-900">API Key</label>
                  <input
                    type="password"
                    className="form-control"
                    value={cfg.api_key === '****' ? '' : (cfg.api_key || '')}
                    onChange={(e) => handleConfigChange('api_key', e.target.value)}
                    placeholder={config?.config?.api_key === '****' ? '(leave blank to keep existing)' : ''}
                    autoComplete="off"
                  />
                </div>
                <div className="col-md-6 mb-3">
                  <label className="form-label font-bold text-slate-900">Summarization</label>
                  <input
                    className="form-control"
                    value={cfg.summarization || ''}
                    onChange={(e) => handleConfigChange('summarization', e.target.value)}
                  />
                </div>
                <div className="col-12 mb-3">
                  <label className="form-label font-bold text-slate-900">Processing Keys</label>
                  <input
                    className="form-control"
                    value={cfg.processing_keys || ''}
                    onChange={(e) => handleConfigChange('processing_keys', e.target.value)}
                  />
                </div>
                <div className="col-md-4 mb-3">
                  <label className="form-label font-bold text-slate-900">Terrain Shading</label>
                  <select
                    className="form-select"
                    value={cfg.terrain_shading ? 'yes' : 'no'}
                    onChange={(e) => handleConfigChange('terrain_shading', e.target.value === 'yes')}
                  >
                    <option value="no">No</option>
                    <option value="yes">Yes</option>
                  </select>
                </div>
                <div className="col-md-4 mb-3">
                  <label className="form-label font-bold text-slate-900">Time Stamp Type</label>
                  <input
                    className="form-control"
                    value={cfg.time_stamp_type || ''}
                    onChange={(e) => handleConfigChange('time_stamp_type', e.target.value)}
                  />
                </div>
                <div className="col-md-2 mb-3">
                  <label className="form-label font-bold text-slate-900">Tilt</label>
                  <input
                    type="number"
                    step="0.01"
                    className="form-control"
                    value={cfg.tilt ?? ''}
                    onChange={(e) => handleConfigChange('tilt', e.target.value ? parseFloat(e.target.value) : 0)}
                  />
                </div>
                <div className="col-md-2 mb-3">
                  <label className="form-label font-bold text-slate-900">Azimuth</label>
                  <input
                    type="number"
                    step="0.01"
                    className="form-control"
                    value={cfg.azimuth ?? ''}
                    onChange={(e) => handleConfigChange('azimuth', e.target.value ? parseFloat(e.target.value) : 180)}
                  />
                </div>
                <div className="col-12 mb-3">
                  <label className="form-label font-bold text-slate-900">Linked Asset Codes (JSON array, e.g. [&quot;ASSET1&quot;,&quot;ASSET2&quot;])</label>
                  <input
                    className="form-control"
                    value={linkedAssetCodesRaw}
                    onChange={(e) => setLinkedAssetCodesRaw(e.target.value)}
                  />
                </div>
              </div>
                </>
              )}
              {adapterId === 'fusion_solar' && (
                <>
                  <h6 className="font-bold mb-3">Adapter config (Fusion Solar)</h6>
                  <div className="row">
                    {adapterAccountId === '' && (
                      <>
                        <div className="col-12 mb-3">
                          <label className="form-label font-bold text-slate-900">API base URL <span className="text-danger">*</span></label>
                          <input
                            className="form-control"
                            value={cfg.api_base_url ?? ''}
                            onChange={(e) => handleConfigChange('api_base_url', e.target.value)}
                            placeholder="https://intl.fusionsolar.huawei.com/"
                            required
                          />
                          <small className="text-muted">e.g. https://intl.fusionsolar.huawei.com/</small>
                        </div>
                        <div className="col-md-6 mb-3">
                          <label className="form-label font-bold text-slate-900">Username <span className="text-danger">*</span></label>
                          <input
                            className="form-control"
                            value={cfg.username ?? ''}
                            onChange={(e) => handleConfigChange('username', e.target.value)}
                            required
                          />
                        </div>
                        <div className="col-md-6 mb-3">
                          <label className="form-label font-bold text-slate-900">Password <span className="text-danger">*</span></label>
                          <input
                            type="password"
                            className="form-control"
                            value={cfg.password === '****' ? '' : (cfg.password ?? '')}
                            onChange={(e) => handleConfigChange('password', e.target.value)}
                            placeholder={config?.config?.password === '****' ? '(leave blank to keep existing)' : ''}
                            autoComplete="off"
                            required={!config}
                          />
                        </div>
                      </>
                    )}
                    <div className="col-md-6 mb-3">
                      <label className="form-label font-bold text-slate-900">Plant ID (optional)</label>
                      <input
                        className="form-control"
                        value={cfg.plant_id ?? ''}
                        onChange={(e) => handleConfigChange('plant_id', e.target.value)}
                        placeholder="Leave blank to use asset provider_asset_id"
                      />
                      <small className="text-muted">API plant ID; can also be set on the asset.</small>
                    </div>
                    <div className="col-md-6 mb-3">
                      <label className="form-label font-bold text-slate-900">Rate limit (calls/min)</label>
                      <input
                        type="number"
                        min={1}
                        max={120}
                        className="form-control"
                        value={cfg.rate_limit_calls_per_minute ?? 30}
                        onChange={(e) => handleConfigChange('rate_limit_calls_per_minute', e.target.value ? parseInt(e.target.value, 10) : 30)}
                      />
                      <small className="text-muted">Default 30. Min interval between getDevRealKpi calls.</small>
                    </div>
                  </div>
                </>
              )}
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
