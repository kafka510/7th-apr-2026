
import { useCallback, useEffect, useState } from 'react';
import type { AdapterAccount, AssetAdapterConfig, AssetAdapterConfigConfig } from '../types';
import {
  fetchAssetAdapterConfig,
  createAssetAdapterConfig,
  updateAssetAdapterConfig,
  deleteAssetAdapterConfig,
  downloadData,
  downloadTemplate,
  fetchAdapterAccounts,
  deleteAdapterAccount,
  getDataCollectionAdapterIds,
} from '../api';
import { Pagination } from './Pagination';
import { UploadModal } from './UploadModal';
import { ConfirmDeleteModal } from './ConfirmDeleteModal';
import { DataCollectionFormModal } from './DataCollectionFormModal';
import { AdapterAccountsModal } from './AdapterAccountsModal';
import { useTheme } from '../../../contexts/ThemeContext';

export function DataCollectionTab() {
  const { theme } = useTheme();
  const [configs, setConfigs] = useState<AssetAdapterConfig[]>([]);
  const [loading, setLoading] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [totalPages, setTotalPages] = useState(0);
  const [search, setSearch] = useState('');
  const [assetFilter, setAssetFilter] = useState('');
  const [adapterFilter, setAdapterFilter] = useState('');
  const [adapterIdOptions, setAdapterIdOptions] = useState<string[]>([]);
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [configToDelete, setConfigToDelete] = useState<number | null>(null);
  const [formModalOpen, setFormModalOpen] = useState(false);
  const [editingConfig, setEditingConfig] = useState<AssetAdapterConfig | null>(null);
  const [accountsModalOpen, setAccountsModalOpen] = useState(false);
  const [accounts, setAccounts] = useState<AdapterAccount[]>([]);
  const [accountsLoading, setAccountsLoading] = useState(false);
  const [accountToEditId, setAccountToEditId] = useState<number | null>(null);

  const loadConfigs = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetchAssetAdapterConfig(
        currentPage,
        pageSize,
        search,
        assetFilter,
        adapterFilter
      );
      setConfigs(response.data);
      setTotalPages(response.total_pages);
    } catch (error) {
      window.alert(error instanceof Error ? error.message : 'Failed to load data collection configs');
    } finally {
      setLoading(false);
    }
  }, [currentPage, pageSize, search, assetFilter, adapterFilter]);

  const loadAccounts = useCallback(async () => {
    setAccountsLoading(true);
    try {
      const res = await fetchAdapterAccounts();
      setAccounts(res.data || []);
    } catch {
      setAccounts([]);
    } finally {
      setAccountsLoading(false);
    }
  }, []);

  useEffect(() => {
    getDataCollectionAdapterIds()
      .then((ids) => setAdapterIdOptions(ids.length ? ids : []))
      .catch(() => setAdapterIdOptions([]));
  }, []);

  useEffect(() => {
    loadConfigs();
    loadAccounts();
  }, [loadConfigs, loadAccounts]);

  const formatEffectiveConfigSummary = (
    adapterId: string,
    effective: AssetAdapterConfigConfig | null | undefined
  ): { line: string; title: string } => {
    const c = effective || {};
    if (adapterId === 'fusion_solar') {
      const base = (c.api_base_url as string) || '-';
      const user = c.username
        ? String(c.username).length > 14
          ? `${String(c.username).slice(0, 12)}…`
          : String(c.username)
        : '-';
      const plant = c.plant_id ? String(c.plant_id) : '-';
      return {
        line: `${base} | user: ${user} | plant: ${plant}`,
        title: [c.api_base_url, c.username, c.plant_id ? `plant ${c.plant_id}` : ''].filter(Boolean).join(' • '),
      };
    }
    if (adapterId === 'solargis') {
      const url = (c.api_url as string) || '-';
      const sum = (c.summarization as string) || '-';
      const aid = c.asset_id ? `site ${c.asset_id}` : '';
      return {
        line: [url, sum, aid].filter(Boolean).join(' | '),
        title: [c.api_url, c.summarization, c.asset_id].filter(Boolean).join(' • '),
      };
    }
    if (adapterId === 'laplaceid') {
      const base = (c.api_base_url as string) || (c as { api_url?: string }).api_url || '-';
      const group = (c as { groupid?: string }).groupid || '-';
      return {
        line: `${base} | group: ${group}`,
        title: [base !== '-' ? base : '', group !== '-' ? `group ${group}` : ''].filter(Boolean).join(' • '),
      };
    }
    const bits = [
      c.api_url,
      c.api_base_url,
      (c as { plant_id?: string }).plant_id,
      (c as { asset_id?: string }).asset_id,
      (c as { groupid?: string }).groupid,
    ]
      .map((x) => (x != null && String(x).trim() !== '' ? String(x) : ''))
      .filter(Boolean);
    return {
      line: bits.length ? bits.slice(0, 4).join(' | ') : '—',
      title: bits.join(' • '),
    };
  };

  const handleSave = async (data: Partial<AssetAdapterConfig> & { asset_code: string; adapter_id: string }) => {
    try {
      if (editingConfig) {
        await updateAssetAdapterConfig({
          id: editingConfig.id,
          adapter_account_id: data.adapter_account_id,
          config: data.config,
          acquisition_interval_minutes: data.acquisition_interval_minutes,
          enabled: data.enabled,
        });
        window.alert('Config updated successfully');
      } else {
        await createAssetAdapterConfig({
          asset_code: data.asset_code,
          adapter_id: data.adapter_id,
          adapter_account_id: data.adapter_account_id ?? undefined,
          config: data.config,
          acquisition_interval_minutes: data.acquisition_interval_minutes ?? 5,
          enabled: data.enabled ?? true,
        });
        window.alert('Config created successfully');
      }
      setFormModalOpen(false);
      setEditingConfig(null);
      loadConfigs();
    } catch (error) {
      window.alert(error instanceof Error ? error.message : 'Failed to save config');
    }
  };

  const confirmDelete = async () => {
    if (configToDelete == null) return;
    try {
      await deleteAssetAdapterConfig(configToDelete);
      window.alert('Config deleted successfully');
      loadConfigs();
    } catch (error) {
      window.alert(error instanceof Error ? error.message : 'Failed to delete config');
    } finally {
      setDeleteModalOpen(false);
      setConfigToDelete(null);
    }
  };

  const tableBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.5)' : '#ffffff';
  const tableHeaderBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.9)' : '#212529';
  const tableHeaderText = theme === 'dark' ? '#f1f5f9' : '#ffffff';
  const tableRowBg = theme === 'dark' ? 'transparent' : 'transparent';
  const tableRowHoverBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.3)' : 'rgba(248, 250, 252, 0.9)';
  const tableRowText = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';
  const tableRowTextSecondary = theme === 'dark' ? '#cbd5e0' : '#4a5568';
  const tableBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : '#dee2e6';
  const tableStripeBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.1)' : 'rgba(0, 0, 0, 0.05)';

  return (
    <div className="mt-3">
      {/* Adapter accounts section */}
      <div className="card mb-3" style={{ backgroundColor: theme === 'dark' ? 'rgba(30, 41, 59, 0.5)' : '#ffffff', borderColor: theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : '#dee2e6' }}>
        <div className="card-header d-flex justify-content-between align-items-center" style={{ backgroundColor: theme === 'dark' ? 'rgba(15, 23, 42, 0.8)' : '#f8f9fa', borderColor: theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : '#dee2e6' }}>
          <h5 className="mb-0 font-bold" style={{ color: theme === 'dark' ? '#f1f5f9' : '#1a1a1a' }}>
            🔑 Adapter accounts
          </h5>
          <button
            className="btn btn-primary btn-sm"
            onClick={() => setAccountsModalOpen(true)}
            title="Add or edit adapter accounts"
          >
            ➕ Add account
          </button>
        </div>
        <div className="card-body" style={{ backgroundColor: theme === 'dark' ? 'rgba(30, 41, 59, 0.3)' : '#ffffff' }}>
          {accountsLoading ? (
            <div className="py-3 text-muted">Loading accounts…</div>
          ) : accounts.length === 0 ? (
            <div className="text-muted">No adapter accounts configured yet.</div>
          ) : (
            <div className="table-responsive">
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
                            setAccountToEditId(a.id);
                            setAccountsModalOpen(true);
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
                              await loadAccounts();
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
            </div>
          )}
        </div>
      </div>

      {/* Asset adapter config section */}
      <div className="card" style={{ backgroundColor: theme === 'dark' ? 'rgba(30, 41, 59, 0.5)' : '#ffffff', borderColor: theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : '#dee2e6' }}>
      <div className="card-header d-flex justify-content-between align-items-center" style={{ backgroundColor: theme === 'dark' ? 'rgba(15, 23, 42, 0.8)' : '#f8f9fa', borderColor: theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : '#dee2e6' }}>
        <h5 className="mb-0 font-bold" style={{ color: theme === 'dark' ? '#f1f5f9' : '#1a1a1a' }}>
          📡 Data Collection (Asset Adapter Config)
        </h5>
        <div>
          <button
            className="btn btn-outline-info btn-sm"
            onClick={() => downloadTemplate('asset_adapter_config')}
            title="Download CSV template"
          >
            📋 Download Template
          </button>
          <button
            className="btn btn-success btn-sm ms-2"
            onClick={() => downloadData('asset_adapter_config', { asset_code: assetFilter, search })}
          >
            📥 Download CSV
          </button>
          <button className="btn btn-primary btn-sm ms-2" onClick={() => setUploadModalOpen(true)}>
            📤 Upload CSV
          </button>
        </div>
      </div>
      <div className="card-body" style={{ backgroundColor: theme === 'dark' ? 'rgba(30, 41, 59, 0.3)' : '#ffffff' }}>
        <p className="small text-muted mb-2">
          Rows come from <code>data_collection_asset_adapter_config</code>. &quot;Effective settings&quot; merges the linked adapter
          account with per-asset overrides (same as acquisition). Secrets stay masked.
        </p>
        <div className="row mb-3">
          <div className="col-md-4">
            <input
              type="text"
              className="form-control"
              placeholder="Search asset code / adapter..."
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setCurrentPage(1);
              }}
              style={{
                backgroundColor: theme === 'dark' ? 'rgba(15, 23, 42, 0.8)' : '#ffffff',
                color: theme === 'dark' ? '#f1f5f9' : '#1a1a1a',
                borderColor: theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : '#dee2e6',
              }}
            />
          </div>
          <div className="col-md-2">
            <input
              type="text"
              className="form-control"
              placeholder="Filter by asset code"
              value={assetFilter}
              onChange={(e) => {
                setAssetFilter(e.target.value);
                setCurrentPage(1);
              }}
              style={{
                backgroundColor: theme === 'dark' ? 'rgba(15, 23, 42, 0.8)' : '#ffffff',
                color: theme === 'dark' ? '#f1f5f9' : '#1a1a1a',
                borderColor: theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : '#dee2e6',
              }}
            />
          </div>
          <div className="col-md-2">
            <select
              className="form-select"
              value={adapterFilter}
              onChange={(e) => {
                setAdapterFilter(e.target.value);
                setCurrentPage(1);
              }}
              style={{
                backgroundColor: theme === 'dark' ? 'rgba(15, 23, 42, 0.8)' : '#ffffff',
                color: theme === 'dark' ? '#f1f5f9' : '#1a1a1a',
                borderColor: theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : '#dee2e6',
              }}
              aria-label="Filter by adapter"
            >
              <option value="">All adapters</option>
              {adapterIdOptions.map((id) => (
                <option key={id} value={id}>
                  {id}
                </option>
              ))}
            </select>
          </div>
          <div className="col-md-2">
            <select
              className="form-select"
              value={pageSize}
              onChange={(e) => {
                setPageSize(Number(e.target.value));
                setCurrentPage(1);
              }}
              style={{
                backgroundColor: theme === 'dark' ? 'rgba(15, 23, 42, 0.8)' : '#ffffff',
                color: theme === 'dark' ? '#f1f5f9' : '#1a1a1a',
                borderColor: theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : '#dee2e6',
              }}
            >
              <option value={25}>25 per page</option>
              <option value={50}>50 per page</option>
              <option value={100}>100 per page</option>
            </select>
          </div>
          <div className="col-md-2 text-end">
            <button
              className="btn btn-success btn-sm"
              onClick={() => {
                setEditingConfig(null);
                setFormModalOpen(true);
              }}
            >
              ➕ Add Config
            </button>
          </div>
        </div>

        {loading ? (
          <div className="py-5 text-center">
            <div className="spinner-border" role="status">
              <span className="visually-hidden">Loading...</span>
            </div>
          </div>
        ) : (
          <>
            <style>{`
              #data-collection-table-container {
                position: relative;
                overflow-x: scroll;
                overflow-y: auto;
                max-height: 600px;
                width: 100%;
                border: 1px solid ${tableBorder};
                border-radius: 0.375rem;
                -webkit-overflow-scrolling: touch;
                background: ${tableBg};
              }
              #data-collection-table thead th {
                background: ${tableHeaderBg} !important;
                color: ${tableHeaderText} !important;
                border-color: ${tableBorder} !important;
              }
              #data-collection-table tbody td {
                background: ${tableRowBg} !important;
                color: ${tableRowText} !important;
                border-color: ${tableBorder} !important;
              }
              #data-collection-table tbody tr:hover td {
                background: ${tableRowHoverBg} !important;
              }
              #data-collection-table.table-striped tbody tr:nth-of-type(odd) td {
                background: ${tableRowBg} !important;
              }
              #data-collection-table.table-striped tbody tr:nth-of-type(even) td {
                background: ${tableStripeBg} !important;
              }
              #data-collection-table.table-striped tbody tr:nth-of-type(even):hover td {
                background: ${tableRowHoverBg} !important;
              }
            `}</style>
            <div id="data-collection-table-container">
              <table className="table-striped table-hover table" id="data-collection-table">
                <thead>
                  <tr>
                    <th>Asset Code</th>
                    <th>Adapter</th>
                    <th>Linked account</th>
                    <th>Enabled</th>
                    <th>Interval</th>
                    <th>Effective settings (masked)</th>
                    <th>Updated</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {configs.length === 0 ? (
                    <tr>
                      <td colSpan={8} className="text-center font-medium" style={{ color: tableRowTextSecondary }}>
                        No data collection configs found
                      </td>
                    </tr>
                  ) : (
                    configs.map((c) => (
                      <tr key={c.id}>
                        <td className="font-medium" style={{ color: tableRowText }}>{c.asset_code}</td>
                        <td className="font-medium" style={{ color: tableRowTextSecondary }}>{c.adapter_id}</td>
                        <td className="font-medium" style={{ color: tableRowTextSecondary }}>
                          {typeof c.adapter_account_id === 'number' ? (
                            <>
                              #{c.adapter_account_id}
                              {c.adapter_account_name ? (
                                <span className="text-muted"> — {c.adapter_account_name}</span>
                              ) : null}
                            </>
                          ) : (
                            <span className="text-muted">Inline config</span>
                          )}
                        </td>
                        <td className="font-medium" style={{ color: tableRowTextSecondary }}>{c.enabled ? 'Yes' : 'No'}</td>
                        <td className="font-medium" style={{ color: tableRowTextSecondary }}>
                          {c.acquisition_interval_minutes === 1440 ? 'Daily' : `${c.acquisition_interval_minutes} min`}
                        </td>
                        <td
                          className="font-medium small"
                          style={{ color: tableRowTextSecondary, maxWidth: 320 }}
                          title={formatEffectiveConfigSummary(c.adapter_id, c.effective_config ?? c.config).title}
                        >
                          {formatEffectiveConfigSummary(c.adapter_id, c.effective_config ?? c.config).line}
                        </td>
                        <td className="font-medium small" style={{ color: tableRowTextSecondary }}>
                          {c.updated_at
                            ? new Date(c.updated_at).toLocaleString(undefined, {
                                dateStyle: 'short',
                                timeStyle: 'short',
                              })
                            : '—'}
                        </td>
                        <td>
                          <button
                            className="btn btn-outline-primary btn-sm me-2"
                            onClick={() => {
                              setEditingConfig(c);
                              setFormModalOpen(true);
                            }}
                          >
                            ✏️
                          </button>
                          <button
                            className="btn btn-outline-danger btn-sm"
                            onClick={() => {
                              setConfigToDelete(c.id);
                              setDeleteModalOpen(true);
                            }}
                          >
                            🗑️
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </>
        )}

        {!loading && totalPages > 1 && (
          <Pagination currentPage={currentPage} totalPages={totalPages} onPageChange={setCurrentPage} />
        )}
      </div>
      </div>

      <UploadModal
        isOpen={uploadModalOpen}
        onClose={() => setUploadModalOpen(false)}
        tableName="asset_adapter_config"
        onUploadSuccess={() => {
          setUploadModalOpen(false);
          loadConfigs();
        }}
        onError={(msg) => window.alert(msg)}
      />

      <ConfirmDeleteModal
        isOpen={deleteModalOpen}
        onClose={() => {
          setDeleteModalOpen(false);
          setConfigToDelete(null);
        }}
        onConfirm={confirmDelete}
        title="Delete Data Collection Config"
        message="Are you sure you want to delete this config?"
      />

      <DataCollectionFormModal
        key={editingConfig ? `edit-${editingConfig.id}` : 'add'}
        isOpen={formModalOpen}
        onClose={() => {
          setFormModalOpen(false);
          setEditingConfig(null);
        }}
        onSave={handleSave}
        config={editingConfig}
      />

      <AdapterAccountsModal
        isOpen={accountsModalOpen}
        onClose={() => {
          setAccountsModalOpen(false);
          setAccountToEditId(null);
        }}
        onAccountsChanged={loadAccounts}
        initialAccountId={accountToEditId}
      />
    </div>
  );
}
