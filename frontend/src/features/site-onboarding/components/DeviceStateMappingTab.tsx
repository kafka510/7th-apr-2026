import { useCallback, useEffect, useState } from 'react';
import type { DeviceOperatingState } from '../types';
import {
  fetchDeviceOperatingState,
  createDeviceOperatingState,
  updateDeviceOperatingState,
  deleteDeviceOperatingState,
  downloadData,
  downloadTemplate,
} from '../api';
import { Pagination } from './Pagination';
import { UploadModal } from './UploadModal';
import { ConfirmDeleteModal } from './ConfirmDeleteModal';
import { useTheme } from '../../../contexts/ThemeContext';

export function DeviceStateMappingTab() {
  const { theme } = useTheme();
  const [rows, setRows] = useState<DeviceOperatingState[]>([]);
  const [loading, setLoading] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [totalPages, setTotalPages] = useState(0);
  const [search, setSearch] = useState('');
  const [adapterFilter, setAdapterFilter] = useState('');
  const [deviceTypeFilter, setDeviceTypeFilter] = useState('');
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [rowToDelete, setRowToDelete] = useState<number | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [editingRow, setEditingRow] = useState<DeviceOperatingState | null>(null);

  const loadRows = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetchDeviceOperatingState(
        currentPage,
        pageSize,
        search,
        adapterFilter,
        deviceTypeFilter
      );
      setRows(response.data);
      setTotalPages(response.total_pages);
    } catch (error) {
      window.alert(
        error instanceof Error ? error.message : 'Failed to load device operating state mappings'
      );
    } finally {
      setLoading(false);
    }
  }, [currentPage, pageSize, search, adapterFilter, deviceTypeFilter]);

  useEffect(() => {
    loadRows();
  }, [loadRows]);

  const handleSave = async (data: Partial<DeviceOperatingState>) => {
    try {
      if (editingRow) {
        await updateDeviceOperatingState({
          id: editingRow.id,
          adapter_id: data.adapter_id ?? editingRow.adapter_id,
          device_type: data.device_type ?? editingRow.device_type,
          state_value: data.state_value ?? editingRow.state_value,
          oem_state_label: data.oem_state_label ?? editingRow.oem_state_label,
          internal_state: data.internal_state ?? editingRow.internal_state,
          is_normal:
            typeof data.is_normal === 'boolean' ? data.is_normal : editingRow.is_normal,
          fault_code: data.fault_code ?? editingRow.fault_code,
        });
        window.alert('Device state mapping updated successfully');
      } else {
        await createDeviceOperatingState({
          adapter_id: data.adapter_id,
          device_type: data.device_type,
          state_value: data.state_value,
          oem_state_label: data.oem_state_label,
          internal_state: data.internal_state,
          is_normal: !!data.is_normal,
          fault_code: data.fault_code ?? null,
        });
        window.alert('Device state mapping created successfully');
      }
      setFormOpen(false);
      setEditingRow(null);
      loadRows();
    } catch (error) {
      window.alert(
        error instanceof Error ? error.message : 'Failed to save device state mapping'
      );
    }
  };

  const confirmDelete = async () => {
    if (rowToDelete == null) return;
    try {
      await deleteDeviceOperatingState(rowToDelete);
      window.alert('Device state mapping deleted successfully');
      loadRows();
    } catch (error) {
      window.alert(
        error instanceof Error ? error.message : 'Failed to delete device state mapping'
      );
    } finally {
      setDeleteModalOpen(false);
      setRowToDelete(null);
    }
  };

  const cardBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.5)' : '#ffffff';
  const cardBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : '#dee2e6';
  const headerBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.8)' : '#f8f9fa';
  const headerText = theme === 'dark' ? '#f1f5f9' : '#1a1a1a';
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
    <div className="card mt-3" style={{ backgroundColor: cardBg, borderColor: cardBorder }}>
      <div
        className="card-header d-flex justify-content-between align-items-center"
        style={{ backgroundColor: headerBg, borderColor: cardBorder }}
      >
        <h5 className="mb-0 font-bold" style={{ color: headerText }}>
          ⚙️ Device State Mapping
        </h5>
        <div>
          <button
            className="btn btn-outline-info btn-sm"
            onClick={() => downloadTemplate('device_operating_state')}
            title="Download CSV template"
          >
            📋 Download Template
          </button>
          <button
            className="btn btn-success btn-sm ms-2"
            onClick={() =>
              downloadData('device_operating_state', {
                // downloadData currently only supports asset_code/parent_code/search
                search,
              })
            }
          >
            📥 Download CSV
          </button>
          <button
            className="btn btn-primary btn-sm ms-2"
            onClick={() => setUploadModalOpen(true)}
          >
            📤 Upload CSV
          </button>
        </div>
      </div>
      <div
        className="card-body"
        style={{ backgroundColor: theme === 'dark' ? 'rgba(30, 41, 59, 0.3)' : '#ffffff' }}
      >
        <p className="text-muted small mb-3" style={{ color: tableRowTextSecondary }}>
          Map OEM inverter state codes per adapter/device type to normalized internal states (e.g.
          NORMAL, SHUTDOWN, FAULT). Delete is restricted to superusers at the API level.
        </p>
        <div className="row mb-3">
          <div className="col-md-4">
            <input
              type="text"
              className="form-control"
              placeholder="Search adapter / device type / state value..."
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
          <div className="col-md-3">
            <input
              type="text"
              className="form-control"
              placeholder="Filter by adapter_id (e.g. fusion_solar)"
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
            />
          </div>
          <div className="col-md-3">
            <input
              type="text"
              className="form-control"
              placeholder="Filter by device_type"
              value={deviceTypeFilter}
              onChange={(e) => {
                setDeviceTypeFilter(e.target.value);
                setCurrentPage(1);
              }}
              style={{
                backgroundColor: theme === 'dark' ? 'rgba(15, 23, 42, 0.8)' : '#ffffff',
                color: theme === 'dark' ? '#f1f5f9' : '#1a1a1a',
                borderColor: theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : '#dee2e6',
              }}
            />
          </div>
          <div className="col-md-2 text-end">
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
        </div>

        <div className="mb-3 text-end">
          <button
            className="btn btn-success btn-sm"
            onClick={() => {
              setEditingRow(null);
              setFormOpen(true);
            }}
          >
            ➕ Add Mapping
          </button>
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
              #device-state-table-container {
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
              #device-state-table thead th {
                background: ${tableHeaderBg} !important;
                color: ${tableHeaderText} !important;
                border-color: ${tableBorder} !important;
              }
              #device-state-table tbody td {
                background: ${tableRowBg} !important;
                color: ${tableRowText} !important;
                border-color: ${tableBorder} !important;
              }
              #device-state-table tbody tr:hover td {
                background: ${tableRowHoverBg} !important;
              }
              #device-state-table.table-striped tbody tr:nth-of-type(odd) td {
                background: ${tableRowBg} !important;
              }
              #device-state-table.table-striped tbody tr:nth-of-type(even) td {
                background: ${tableStripeBg} !important;
              }
              #device-state-table.table-striped tbody tr:nth-of-type(even):hover td {
                background: ${tableRowHoverBg} !important;
              }
            `}</style>
            <div id="device-state-table-container">
              <table className="table-striped table-hover table" id="device-state-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Adapter ID</th>
                    <th>Device Type</th>
                    <th>State Value</th>
                    <th>OEM Label</th>
                    <th>Internal State</th>
                    <th>Normal?</th>
                    <th>Fault Code</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.length === 0 ? (
                    <tr>
                      <td colSpan={9} className="text-center font-medium" style={{ color: tableRowTextSecondary }}>
                        No device state mappings found
                      </td>
                    </tr>
                  ) : (
                    rows.map((row) => (
                      <tr key={row.id}>
                        <td>{row.id}</td>
                        <td>{row.adapter_id}</td>
                        <td>{row.device_type}</td>
                        <td>{row.state_value}</td>
                        <td>{row.oem_state_label}</td>
                        <td>{row.internal_state}</td>
                        <td>
                          {row.is_normal ? (
                            <span className="badge bg-success">Yes</span>
                          ) : (
                            <span className="badge bg-secondary">No</span>
                          )}
                        </td>
                        <td>{row.fault_code ?? ''}</td>
                        <td>
                          <button
                            className="btn btn-sm btn-outline-primary me-1"
                            onClick={() => {
                              setEditingRow(row);
                              setFormOpen(true);
                            }}
                          >
                            ✏️
                          </button>
                          <button
                            className="btn btn-sm btn-outline-danger"
                            onClick={() => {
                              setRowToDelete(row.id);
                              setDeleteModalOpen(true);
                            }}
                            title="Delete (superuser only)"
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
            <div className="mt-3">
              <Pagination
                currentPage={currentPage}
                totalPages={totalPages}
                onPageChange={setCurrentPage}
              />
            </div>
          </>
        )}
      </div>

      {/* CSV Upload Modal */}
      <UploadModal
        isOpen={uploadModalOpen}
        onClose={() => setUploadModalOpen(false)}
        tableName="device_operating_state"
        onUploadSuccess={loadRows}
        onError={(message) => window.alert(message)}
      />

      {/* Confirm Delete Modal */}
      <ConfirmDeleteModal
        isOpen={deleteModalOpen}
        onClose={() => setDeleteModalOpen(false)}
        onConfirm={confirmDelete}
        title="Confirm Delete Device State Mapping"
        message="Are you sure you want to delete this device state mapping? This requires superuser permissions and cannot be undone."
      />

      {/* Simple inline form modal for add/edit */}
      {formOpen && (
        <div className="modal fade show" style={{ display: 'block' }}>
          <div className="modal-dialog modal-lg">
            <div className="modal-content">
              <div className="modal-header">
                <h5 className="modal-title">
                  {editingRow ? 'Edit Device State Mapping' : 'Add Device State Mapping'}
                </h5>
                <button
                  type="button"
                  className="btn-close"
                  onClick={() => {
                    setFormOpen(false);
                    setEditingRow(null);
                  }}
                />
              </div>
              <DeviceStateForm
                initial={editingRow ?? undefined}
                onCancel={() => {
                  setFormOpen(false);
                  setEditingRow(null);
                }}
                onSave={handleSave}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

interface DeviceStateFormProps {
  initial?: DeviceOperatingState;
  onSave: (data: Partial<DeviceOperatingState>) => void;
  onCancel: () => void;
}

function DeviceStateForm({ initial, onSave, onCancel }: DeviceStateFormProps) {
  const [adapterId, setAdapterId] = useState(initial?.adapter_id ?? '');
  const [deviceType, setDeviceType] = useState(initial?.device_type ?? '');
  const [stateValue, setStateValue] = useState(initial?.state_value ?? '');
  const [oemLabel, setOemLabel] = useState(initial?.oem_state_label ?? '');
  const [internalState, setInternalState] = useState(initial?.internal_state ?? '');
  const [isNormal, setIsNormal] = useState<boolean>(initial?.is_normal ?? false);
  const [faultCode, setFaultCode] = useState(initial?.fault_code ?? '');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!adapterId || !deviceType || !stateValue || !internalState) {
      window.alert('Adapter ID, device type, state value and internal state are required');
      return;
    }
    onSave({
      adapter_id: adapterId,
      device_type: deviceType,
      state_value: stateValue,
      oem_state_label: oemLabel,
      internal_state: internalState,
      is_normal: isNormal,
      fault_code: faultCode || null,
    });
  };

  return (
    <form onSubmit={handleSubmit}>
      <div className="modal-body">
        <div className="row">
          <div className="col-md-4 mb-2">
            <label className="form-label">Adapter ID *</label>
            <input
              type="text"
              className="form-control"
              value={adapterId}
              onChange={(e) => setAdapterId(e.target.value)}
              required
            />
          </div>
          <div className="col-md-4 mb-2">
            <label className="form-label">Device Type *</label>
            <input
              type="text"
              className="form-control"
              value={deviceType}
              onChange={(e) => setDeviceType(e.target.value)}
              required
            />
          </div>
          <div className="col-md-4 mb-2">
            <label className="form-label">State Value *</label>
            <input
              type="text"
              className="form-control"
              value={stateValue}
              onChange={(e) => setStateValue(e.target.value)}
              required
            />
          </div>
        </div>
        <div className="mb-2">
          <label className="form-label">OEM State Label</label>
          <input
            type="text"
            className="form-control"
            value={oemLabel}
            onChange={(e) => setOemLabel(e.target.value)}
          />
        </div>
        <div className="row mb-2">
          <div className="col-md-6">
            <label className="form-label">Internal State *</label>
            <input
              type="text"
              className="form-control"
              value={internalState}
              onChange={(e) => setInternalState(e.target.value)}
              required
            />
          </div>
          <div className="col-md-3">
            <label className="form-label d-block">Is Normal?</label>
            <div className="form-check mt-2">
              <input
                className="form-check-input"
                type="checkbox"
                checked={isNormal}
                onChange={(e) => setIsNormal(e.target.checked)}
                id="deviceStateIsNormalReact"
              />
              <label className="form-check-label" htmlFor="deviceStateIsNormalReact">
                Normal operation (no loss)
              </label>
            </div>
          </div>
          <div className="col-md-3">
            <label className="form-label">Fault Code (optional)</label>
            <input
              type="text"
              className="form-control"
              value={faultCode}
              onChange={(e) => setFaultCode(e.target.value)}
            />
          </div>
        </div>
      </div>
      <div className="modal-footer">
        <button type="button" className="btn btn-secondary" onClick={onCancel}>
          Cancel
        </button>
        <button type="submit" className="btn btn-primary">
          Save
        </button>
      </div>
    </form>
  );
}

