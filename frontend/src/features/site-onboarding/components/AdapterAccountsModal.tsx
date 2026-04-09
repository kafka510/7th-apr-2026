import { useEffect, useState } from 'react';
import type { AdapterAccount, AssetAdapterConfigConfig } from '../types';
import {
  fetchAdapterAccounts,
  createAdapterAccount,
  updateAdapterAccount,
  deleteAdapterAccount,
  getDataCollectionAdapterIds,
} from '../api';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onAccountsChanged?: () => void;
  initialAccountId?: number | null;
}

const defaultSolargisConfig: AssetAdapterConfigConfig = {
  api_url: 'https://solargis.info/ws/rest/datadelivery/request',
  api_key: '',
};

const defaultFusionConfig: AssetAdapterConfigConfig = {
  api_base_url: 'https://intl.fusionsolar.huawei.com/',
  username: '',
  password: '',
};

const defaultLaplaceIdConfig: AssetAdapterConfigConfig = {
  api_base_url: 'https://services.energymntr.com/megasolar/',
  username: '',
  password: '',
  groupid: '1',
};

export function AdapterAccountsModal({ isOpen, onClose, onAccountsChanged, initialAccountId }: Props) {
  const [accounts, setAccounts] = useState<AdapterAccount[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [adapterIds, setAdapterIds] = useState<string[]>(['solargis', 'fusion_solar', 'laplaceid']);
  const [adapterId, setAdapterId] = useState<string>('solargis');
  const [name, setName] = useState('');
  const [cfg, setCfg] = useState<AssetAdapterConfigConfig>({ ...defaultSolargisConfig });
  const [editing, setEditing] = useState<AdapterAccount | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    getDataCollectionAdapterIds()
      .then((ids) => {
        const safe = Array.isArray(ids) ? ids.filter(Boolean) : [];
        if (safe.length) setAdapterIds(safe);
      })
      .catch(() => {});
    setLoading(true);
    fetchAdapterAccounts()
      .then((res) => {
        const list = res.data || [];
        setAccounts(list);
        if (initialAccountId) {
          const acc = list.find((a) => a.id === initialAccountId);
          if (acc) {
            setEditing(acc);
            setAdapterId(acc.adapter_id || 'solargis');
            if (acc.adapter_id === 'fusion_solar') {
              setCfg({
                api_base_url: acc.config.api_base_url,
                username: acc.config.username,
                password: '****',
              });
            } else if (acc.adapter_id === 'laplaceid') {
              setCfg({
                api_base_url: acc.config.api_base_url,
                username: acc.config.username,
                password: '****',
                groupid: (acc.config as any).groupid ?? '1',
              });
            } else {
              setCfg({
                api_url: acc.config.api_url,
                api_key: '****',
              });
            }
            setName(acc.name || '');
          }
        }
      })
      .catch(() => setAccounts([]))
      .finally(() => setLoading(false));
  }, [isOpen, initialAccountId]);

  useEffect(() => {
    if (!isOpen) return;
    const modalEl = document.getElementById('adapterAccountsModal');
    if (!modalEl) return;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const modal = new (window as any).bootstrap.Modal(modalEl);
    modal.show();
    const handleHidden = () => onClose();
    modalEl.addEventListener('hidden.bs.modal', handleHidden);
    return () => {
      modalEl.removeEventListener('hidden.bs.modal', handleHidden);
      modal.dispose();
    };
  }, [isOpen, onClose]);

  const handleAdapterChange = (value: string) => {
    setAdapterId(value);
    if (value === 'fusion_solar') {
      setCfg({ ...defaultFusionConfig });
      return;
    }
    if (value === 'laplaceid') {
      setCfg({ ...defaultLaplaceIdConfig });
      return;
    }
    setCfg({ ...defaultSolargisConfig });
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const payload =
        adapterId === 'fusion_solar'
          ? {
              adapter_id: adapterId,
              name: name.trim(),
              config: {
                api_base_url: cfg.api_base_url ?? '',
                username: cfg.username ?? '',
                password: cfg.password ?? '',
              },
              enabled: true,
            }
          : adapterId === 'laplaceid'
            ? {
                adapter_id: adapterId,
                name: name.trim(),
                config: {
                  api_base_url: cfg.api_base_url ?? '',
                  username: cfg.username ?? '',
                  password: cfg.password ?? '',
                  groupid: (cfg as any).groupid ?? '1',
                },
                enabled: true,
              }
            : {
              adapter_id: adapterId,
              name: name.trim(),
              config: {
                api_url: cfg.api_url ?? '',
                api_key: cfg.api_key ?? '',
              },
              enabled: true,
            };
      if (editing) {
        await updateAdapterAccount({
          id: editing.id,
          name: payload.name,
          config: payload.config,
          enabled: payload.enabled,
        });
        window.alert('Adapter account updated.');
      } else {
        await createAdapterAccount(payload);
        window.alert('Adapter account created.');
      }
      setName('');
      setCfg(
        adapterId === 'fusion_solar'
          ? { ...defaultFusionConfig }
          : adapterId === 'laplaceid'
            ? { ...defaultLaplaceIdConfig }
            : { ...defaultSolargisConfig }
      );
      setEditing(null);
      const res = await fetchAdapterAccounts();
      setAccounts(res.data || []);
      if (onAccountsChanged) {
        onAccountsChanged();
      }
    } catch (err) {
      window.alert(err instanceof Error ? err.message : 'Failed to create adapter account');
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal fade" id="adapterAccountsModal" tabIndex={-1} aria-hidden="true">
      <div className="modal-dialog modal-lg">
        <div className="modal-content">
          <div className="modal-header">
            <h5 className="modal-title font-bold text-slate-900">Adapter accounts</h5>
            <button type="button" className="btn-close" data-bs-dismiss="modal" aria-label="Close" />
          </div>
          <div className="modal-body">
            <h6 className="font-bold mb-3">Add account</h6>
            <form onSubmit={handleSave} className="mb-4">
              <div className="row">
                <div className="col-md-4 mb-3">
                  <label className="form-label font-bold text-slate-900">Adapter</label>
                  <select
                    className="form-select"
                    value={adapterId}
                    onChange={(e) => handleAdapterChange(e.target.value)}
                  >
                    {adapterIds.map((id) => (
                      <option key={id} value={id}>
                        {id === 'solargis' ? 'SolarGIS' : id === 'fusion_solar' ? 'Fusion Solar' : id === 'laplaceid' ? 'LaplaceID' : id}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="col-md-8 mb-3">
                  <label className="form-label font-bold text-slate-900">Name</label>
                  <input
                    type="text"
                    className="form-control"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="e.g. Solargis Production, Fusion Solar Account A"
                    required
                  />
                </div>
              </div>
              {adapterId === 'solargis' ? (
                <div className="row">
                  <div className="col-md-6 mb-3">
                    <label className="form-label font-bold text-slate-900">API URL</label>
                    <input
                      type="text"
                      className="form-control"
                      value={cfg.api_url ?? ''}
                      onChange={(e) => setCfg((prev) => ({ ...prev, api_url: e.target.value }))}
                      required
                    />
                  </div>
                  <div className="col-md-6 mb-3">
                    <label className="form-label font-bold text-slate-900">API key</label>
                    <input
                      type="password"
                      className="form-control"
                      value={cfg.api_key ?? ''}
                      onChange={(e) => setCfg((prev) => ({ ...prev, api_key: e.target.value }))}
                      required
                    />
                  </div>
                </div>
              ) : adapterId === 'laplaceid' ? (
                <div className="row">
                  <div className="col-md-3 mb-3">
                    <label className="form-label font-bold text-slate-900">API base URL</label>
                    <input
                      type="text"
                      className="form-control"
                      value={cfg.api_base_url ?? ''}
                      onChange={(e) => setCfg((prev) => ({ ...prev, api_base_url: e.target.value }))}
                      placeholder="https://services.energymntr.com/megasolar/"
                      required
                    />
                  </div>
                  <div className="col-md-3 mb-3">
                    <label className="form-label font-bold text-slate-900">Username</label>
                    <input
                      type="text"
                      className="form-control"
                      value={cfg.username ?? ''}
                      onChange={(e) => setCfg((prev) => ({ ...prev, username: e.target.value }))}
                      required
                    />
                  </div>
                  <div className="col-md-3 mb-3">
                    <label className="form-label font-bold text-slate-900">Password</label>
                    <input
                      type="password"
                      className="form-control"
                      value={cfg.password ?? ''}
                      onChange={(e) => setCfg((prev) => ({ ...prev, password: e.target.value }))}
                      required
                    />
                  </div>
                  <div className="col-md-3 mb-3">
                    <label className="form-label font-bold text-slate-900">Group ID</label>
                    <input
                      type="text"
                      className="form-control"
                      value={(cfg as any).groupid ?? '1'}
                      onChange={(e) => setCfg((prev) => ({ ...(prev || {}), groupid: e.target.value } as any))}
                      placeholder="1"
                    />
                  </div>
                </div>
              ) : (
                <div className="row">
                  <div className="col-md-4 mb-3">
                    <label className="form-label font-bold text-slate-900">API base URL</label>
                    <input
                      type="text"
                      className="form-control"
                      value={cfg.api_base_url ?? ''}
                      onChange={(e) => setCfg((prev) => ({ ...prev, api_base_url: e.target.value }))}
                      required
                    />
                  </div>
                  <div className="col-md-4 mb-3">
                    <label className="form-label font-bold text-slate-900">Username</label>
                    <input
                      type="text"
                      className="form-control"
                      value={cfg.username ?? ''}
                      onChange={(e) => setCfg((prev) => ({ ...prev, username: e.target.value }))}
                      required
                    />
                  </div>
                  <div className="col-md-4 mb-3">
                    <label className="form-label font-bold text-slate-900">Password</label>
                    <input
                      type="password"
                      className="form-control"
                      value={cfg.password ?? ''}
                      onChange={(e) => setCfg((prev) => ({ ...prev, password: e.target.value }))}
                      required
                    />
                  </div>
                </div>
              )}
              <div className="text-end">
                <button type="submit" className="btn btn-primary btn-sm" disabled={saving}>
                  {saving ? 'Saving…' : 'Save account'}
                </button>
              </div>
            </form>

            <h6 className="font-bold mb-2">Existing accounts</h6>
            {loading ? (
              <div>Loading accounts…</div>
            ) : accounts.length === 0 ? (
              <div className="text-muted">No adapter accounts configured yet.</div>
            ) : (
              <table className="table table-sm">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Adapter</th>
                    <th>Name</th>
                    <th>Enabled</th>
                    <th>Updated at</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {accounts.map((a) => (
                    <tr key={a.id}>
                      <td>{a.id}</td>
                      <td>{a.adapter_id}</td>
                      <td>{a.name || '-'}</td>
                      <td>{a.enabled ? 'Yes' : 'No'}</td>
                      <td>{a.updated_at}</td>
                      <td>
                        <button
                          type="button"
                          className="btn btn-outline-primary btn-sm me-2"
                          onClick={() => {
                            setEditing(a);
                            setAdapterId(a.adapter_id || 'solargis');
                            if (a.adapter_id === 'fusion_solar') {
                              setCfg({
                                api_base_url: a.config.api_base_url,
                                username: a.config.username,
                                password: '****',
                              });
                            } else if (a.adapter_id === 'laplaceid') {
                              setCfg({
                                api_base_url: a.config.api_base_url,
                                username: a.config.username,
                                password: '****',
                                groupid: (a.config as any).groupid ?? '1',
                              });
                            } else {
                              setCfg({
                                api_url: a.config.api_url,
                                api_key: '****',
                              });
                            }
                            setName(a.name || '');
                          }}
                        >
                          Edit
                        </button>
                        <button
                          type="button"
                          className="btn btn-outline-danger btn-sm"
                          onClick={async () => {
                            if (!window.confirm('Delete this adapter account? This action cannot be undone.')) {
                              return;
                            }
                            try {
                              await deleteAdapterAccount(a.id);
                              window.alert('Adapter account deleted.');
                              const res = await fetchAdapterAccounts();
                              setAccounts(res.data || []);
                              if (onAccountsChanged) onAccountsChanged();
                            } catch (err) {
                              window.alert(
                                err instanceof Error
                                  ? err.message
                                  : 'Failed to delete adapter account (only superusers can delete).'
                              );
                            }
                          }}
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

