 
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { AssetList, DeviceList } from '../types';
import {
  fetchDeviceList,
  createDeviceList,
  updateDeviceList,
  deleteDeviceList,
  downloadData,
  downloadTemplate,
  getAllAssets,
} from '../api';
import { Pagination } from './Pagination';
import { UploadModal } from './UploadModal';
import { ConfirmDeleteModal } from './ConfirmDeleteModal';
import { DeviceFormModal } from './DeviceFormModal';
import { useTheme } from '../../../contexts/ThemeContext';

export function DeviceListTab() {
  const { theme } = useTheme();
  const [devices, setDevices] = useState<DeviceList[]>([]);
  const [loading, setLoading] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [totalPages, setTotalPages] = useState(0);
  const [search, setSearch] = useState('');
  const [parentFilters, setParentFilters] = useState<string[]>([]);
  const [assetFilterSearch, setAssetFilterSearch] = useState('');
  const [assetDropdownOpen, setAssetDropdownOpen] = useState(false);
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [deviceToDelete, setDeviceToDelete] = useState<string | null>(null);
  const [formModalOpen, setFormModalOpen] = useState(false);
  const [editingDevice, setEditingDevice] = useState<DeviceList | null>(null);
  const [allAssets, setAllAssets] = useState<AssetList[]>([]);
  const assetDropdownRef = useRef<HTMLDivElement | null>(null);

  const loadDevices = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetchDeviceList(currentPage, pageSize, search, parentFilters);
      setDevices(response.data);
      setTotalPages(response.total_pages);
    } catch (error) {
      window.alert(error instanceof Error ? error.message : 'Failed to load devices');
    } finally {
      setLoading(false);
    }
  }, [currentPage, pageSize, search, parentFilters]);

  useEffect(() => {
    loadDevices();
  }, [loadDevices]);

  useEffect(() => {
    // Load full asset list once so the Parent Code filter shows all sites
    getAllAssets()
      .then(setAllAssets)
      .catch(() => {
        // Ignore errors here; filter will just fall back to codes from current page
      });
  }, []);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (!assetDropdownRef.current) return;
      if (!assetDropdownRef.current.contains(event.target as Node)) {
        setAssetDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const parentCodeOptions = useMemo(() => {
    if (allAssets.length) {
      return allAssets
        .filter((asset) => asset.asset_code)
        .map((asset) => ({
          code: asset.asset_code,
          name: asset.asset_name || asset.asset_code,
          label: `${asset.asset_name || asset.asset_code} (${asset.asset_code})`,
        }))
        .sort((a, b) => a.label.localeCompare(b.label));
    }
    return Array.from(
      new Set(
        devices
          .map((device) => device.parent_code)
          .filter(Boolean),
      ),
    )
      .sort()
      .map((code) => ({ code, name: code, label: `${code} (${code})` }));
  }, [allAssets, devices]);

  const filteredParentCodeOptions = useMemo(() => {
    const q = assetFilterSearch.trim().toLowerCase();
    if (!q) return parentCodeOptions;
    return parentCodeOptions.filter((opt) => opt.label.toLowerCase().includes(q));
  }, [assetFilterSearch, parentCodeOptions]);

  const selectedParentOptions = useMemo(
    () => parentCodeOptions.filter((opt) => parentFilters.includes(opt.code)),
    [parentCodeOptions, parentFilters],
  );

  const handleSave = async (data: Partial<DeviceList>) => {
    try {
      if (editingDevice) {
        await updateDeviceList({ ...data, device_id: editingDevice.device_id });
        window.alert('Device updated successfully');
      } else {
        await createDeviceList(data);
        window.alert('Device created successfully');
      }
      setFormModalOpen(false);
      setEditingDevice(null);
      loadDevices();
    } catch (error) {
      window.alert(error instanceof Error ? error.message : 'Failed to save device');
    }
  };

  const confirmDelete = async () => {
    if (!deviceToDelete) return;
    try {
      await deleteDeviceList(deviceToDelete);
      window.alert('Device deleted successfully');
      loadDevices();
    } catch (error) {
      window.alert(error instanceof Error ? error.message : 'Failed to delete device');
    } finally {
      setDeleteModalOpen(false);
      setDeviceToDelete(null);
    }
  };

  // Theme-aware colors
  const tableBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.5)' : '#ffffff';
  const tableHeaderBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.9)' : '#212529';
  const tableHeaderText = theme === 'dark' ? '#f1f5f9' : '#ffffff';
  const tableRowBg = theme === 'dark' ? 'transparent' : 'transparent';
  const tableRowHoverBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.3)' : 'rgba(248, 250, 252, 0.9)';
  const tableRowText = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';
  const tableRowTextSecondary = theme === 'dark' ? '#cbd5e0' : '#4a5568';
  const tableBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : '#dee2e6';
  const tableStripeBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.1)' : 'rgba(0, 0, 0, 0.05)';
  const parseDeviceSource = (raw: string | null | undefined): string => {
    if (!raw) return '-';
    try {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) {
        const values = parsed.map((item) => (typeof item === 'string' ? item.trim() : '')).filter(Boolean);
        return values.length ? values.join(', ') : '-';
      }
    } catch {
      // fallback to raw value for backward compatibility
    }
    return raw;
  };

  return (
    <div className="card mt-3" style={{ backgroundColor: theme === 'dark' ? 'rgba(30, 41, 59, 0.5)' : '#ffffff', borderColor: theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : '#dee2e6' }}>
      <div className="card-header d-flex justify-content-between align-items-center" style={{ backgroundColor: theme === 'dark' ? 'rgba(15, 23, 42, 0.8)' : '#f8f9fa', borderColor: theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : '#dee2e6' }}>
        <h5 className="mb-0 font-bold" style={{ color: theme === 'dark' ? '#f1f5f9' : '#1a1a1a' }}>📱 Device List</h5>
        <div>
          <button
            className="btn btn-outline-info btn-sm"
            onClick={() => downloadTemplate('device_list')}
            title="Download CSV template"
          >
            📋 Download Template
          </button>
          <button 
            className="btn btn-success btn-sm ms-2" 
            onClick={() => {
              if (parentFilters.length === 0) {
                window.alert('Please select at least one site filter before downloading.');
                return;
              }
              downloadData('device_list', { parent_code: parentFilters, search });
            }}
            title={parentFilters.length ? 'Download filtered device list' : 'Please select a site filter first'}
          >
            📥 Download CSV
          </button>
          <button className="btn btn-primary btn-sm ms-2" onClick={() => setUploadModalOpen(true)}>
            📤 Upload CSV
          </button>
        </div>
      </div>
      <div className="card-body" style={{ backgroundColor: theme === 'dark' ? 'rgba(30, 41, 59, 0.3)' : '#ffffff' }}>
        <div className="row mb-3">
          <div className="col-md-5">
            <input
              type="text"
              className="form-control"
              placeholder="Search devices..."
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setCurrentPage(1);
              }}
              style={{
                backgroundColor: theme === 'dark' ? 'rgba(15, 23, 42, 0.8)' : '#ffffff',
                color: theme === 'dark' ? '#f1f5f9' : '#1a1a1a',
                borderColor: theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : '#dee2e6'
              }}
            />
          </div>
          <div className="col-md-3">
            <div className="position-relative" ref={assetDropdownRef}>
              <button
                type="button"
                className="btn btn-sm w-100 d-flex justify-content-between align-items-center"
                onClick={() => setAssetDropdownOpen((prev) => !prev)}
                style={{
                  backgroundColor: theme === 'dark' ? 'rgba(15, 23, 42, 0.8)' : '#ffffff',
                  color: theme === 'dark' ? '#f1f5f9' : '#1a1a1a',
                  border: `1px solid ${theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : '#dee2e6'}`,
                }}
              >
                <span>
                  {parentFilters.length === 0
                    ? 'Select Assets'
                    : `${parentFilters.length} site${parentFilters.length > 1 ? 's' : ''} selected`}
                </span>
                <span>{assetDropdownOpen ? '▲' : '▼'}</span>
              </button>

              {assetDropdownOpen && (
                <div
                  className="position-absolute mt-1 w-100 p-2 rounded shadow"
                  style={{
                    zIndex: 50,
                    maxHeight: '320px',
                    overflowY: 'auto',
                    backgroundColor: theme === 'dark' ? 'rgba(15, 23, 42, 0.98)' : '#ffffff',
                    border: `1px solid ${theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : '#dee2e6'}`,
                  }}
                >
                  <input
                    type="text"
                    className="form-control form-control-sm mb-2"
                    placeholder="Search assets..."
                    value={assetFilterSearch}
                    onChange={(e) => setAssetFilterSearch(e.target.value)}
                    style={{
                      backgroundColor: theme === 'dark' ? 'rgba(30, 41, 59, 0.7)' : '#ffffff',
                      color: theme === 'dark' ? '#f1f5f9' : '#1a1a1a',
                      borderColor: theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : '#dee2e6',
                    }}
                  />
                  <div className="d-flex gap-2 mb-2">
                    <button
                      type="button"
                      className="btn btn-outline-secondary btn-sm"
                      onClick={() => {
                        setParentFilters(filteredParentCodeOptions.map((opt) => opt.code));
                        setCurrentPage(1);
                      }}
                    >
                      Select visible
                    </button>
                    <button
                      type="button"
                      className="btn btn-outline-secondary btn-sm"
                      onClick={() => {
                        setParentFilters([]);
                        setCurrentPage(1);
                      }}
                    >
                      Clear
                    </button>
                  </div>
                  {filteredParentCodeOptions.length === 0 ? (
                    <div className="small text-muted px-1 py-2">No assets found</div>
                  ) : (
                    filteredParentCodeOptions.map((opt) => (
                      <div key={opt.code} className="form-check mb-1">
                        <input
                          className="form-check-input"
                          type="checkbox"
                          id={`asset-filter-${opt.code}`}
                          checked={parentFilters.includes(opt.code)}
                          onChange={(e) => {
                            setParentFilters((prev) => {
                              if (e.target.checked) return [...prev, opt.code];
                              return prev.filter((code) => code !== opt.code);
                            });
                            setCurrentPage(1);
                          }}
                        />
                        <label className="form-check-label small" htmlFor={`asset-filter-${opt.code}`}>
                          {opt.label}
                        </label>
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>

            <div className="d-flex flex-wrap gap-1 mt-2">
              {selectedParentOptions.length === 0 ? (
                <small className="text-muted">No assets selected</small>
              ) : (
                selectedParentOptions.map((opt) => (
                  <span
                    key={`chip-${opt.code}`}
                    className="badge d-inline-flex align-items-center"
                    style={{
                      backgroundColor: theme === 'dark' ? 'rgba(59, 130, 246, 0.2)' : '#e7f1ff',
                      color: theme === 'dark' ? '#bfdbfe' : '#0b5ed7',
                      border: `1px solid ${theme === 'dark' ? 'rgba(59, 130, 246, 0.5)' : '#b6d4fe'}`,
                    }}
                  >
                    {opt.name}
                    <button
                      type="button"
                      className="btn btn-link btn-sm p-0 ms-2 text-decoration-none"
                      onClick={() => {
                        setParentFilters((prev) => prev.filter((code) => code !== opt.code));
                        setCurrentPage(1);
                      }}
                      style={{ color: 'inherit', lineHeight: 1 }}
                      aria-label={`Remove ${opt.label}`}
                    >
                      ×
                    </button>
                  </span>
                ))
              )}
            </div>
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
                borderColor: theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : '#dee2e6'
              }}
            >
              <option value={25}>25 per page</option>
              <option value={50}>50 per page</option>
              <option value={100}>100 per page</option>
            </select>
          </div>
          <div className="col-md-2 text-end">
            <button className="btn btn-success btn-sm" onClick={() => setFormModalOpen(true)}>
              ➕ Add Device
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
              #device-table-container {
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
              #device-table {
                width: max-content;
                min-width: 100%;
                margin-bottom: 0;
                border-collapse: separate;
                border-spacing: 0;
                background: ${tableBg};
              }
              #device-table thead th {
                background: ${tableHeaderBg} !important;
                color: ${tableHeaderText} !important;
                border-color: ${tableBorder} !important;
              }
              #device-table tbody td {
                background: ${tableRowBg} !important;
                color: ${tableRowText} !important;
                border-color: ${tableBorder} !important;
              }
              #device-table tbody tr:hover td {
                background: ${tableRowHoverBg} !important;
              }
              #device-table.table-striped tbody tr:nth-of-type(odd) td {
                background: ${tableRowBg} !important;
              }
              #device-table.table-striped tbody tr:nth-of-type(even) td {
                background: ${tableStripeBg} !important;
              }
              #device-table.table-striped tbody tr:nth-of-type(even):hover td {
                background: ${tableRowHoverBg} !important;
              }
              #device-table .sticky-actions {
                position: sticky;
                right: 0;
                z-index: 2;
                min-width: 110px;
              }
            `}</style>
            <div id="device-table-container">
              <table className="table-striped table-hover table" id="device-table">
                <thead>
                  <tr>
                    <th>Device ID</th>
                    <th>Name</th>
                    <th>Serial</th>
                    <th>Type</th>
                    <th>Country</th>
                    <th>Parent</th>
                    <th>Source</th>
                    <th>DC Cap</th>
                    <th>AC Cap</th>
                    <th>Latitude</th>
                    <th>Longitude</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {devices.length === 0 ? (
                    <tr>
                      <td colSpan={12} className="text-center font-medium" style={{ color: tableRowTextSecondary }}>
                        No devices found
                      </td>
                    </tr>
                  ) : (
                    devices.map((device) => (
                      <tr key={device.device_id}>
                        <td className="font-medium" style={{ color: tableRowText }}>{device.device_id}</td>
                        <td className="font-medium" style={{ color: tableRowText }}>{device.device_name}</td>
                        <td className="font-medium" style={{ color: tableRowTextSecondary }}>{device.device_serial || '—'}</td>
                        <td className="font-medium" style={{ color: tableRowTextSecondary }}>{device.device_type}</td>
                        <td className="font-medium" style={{ color: tableRowTextSecondary }}>{device.country}</td>
                        <td className="font-medium" style={{ color: tableRowTextSecondary }}>{device.parent_code || '-'}</td>
                        <td className="font-medium" style={{ color: tableRowTextSecondary }}>{parseDeviceSource(device.device_source)}</td>
                        <td className="font-medium" style={{ color: tableRowTextSecondary }}>{device.dc_cap ?? '-'}</td>
                        <td className="font-medium" style={{ color: tableRowTextSecondary }}>{device.ac_capacity ?? '-'}</td>
                        <td className="font-medium" style={{ color: tableRowTextSecondary }}>{device.latitude ?? '-'}</td>
                        <td className="font-medium" style={{ color: tableRowTextSecondary }}>{device.longitude ?? '-'}</td>
                        <td className="sticky-actions" style={{ background: tableBg }}>
                        <button
                          className="btn btn-outline-primary btn-sm me-2"
                          onClick={() => {
                            setEditingDevice(device);
                            setFormModalOpen(true);
                          }}
                        >
                          ✏️
                        </button>
                        <button
                          className="btn btn-outline-danger btn-sm"
                          onClick={() => {
                            setDeviceToDelete(device.device_id);
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

      <UploadModal
        isOpen={uploadModalOpen}
        onClose={() => setUploadModalOpen(false)}
        tableName="device_list"
        onUploadSuccess={() => {
          setUploadModalOpen(false);
          loadDevices();
        }}
        onError={(msg) => window.alert(msg)}
      />

      <ConfirmDeleteModal
        isOpen={deleteModalOpen}
        onClose={() => {
          setDeleteModalOpen(false);
          setDeviceToDelete(null);
        }}
        onConfirm={confirmDelete}
        title="Delete Device"
        message="Are you sure you want to delete this device?"
        itemName={deviceToDelete || undefined}
      />

      <DeviceFormModal
        isOpen={formModalOpen}
        onClose={() => {
          setFormModalOpen(false);
          setEditingDevice(null);
        }}
        onSave={handleSave}
        device={editingDevice}
      />
    </div>
  );
}
