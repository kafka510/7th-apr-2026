 
import { useCallback, useEffect, useState } from 'react';
import type { DeviceMapping } from '../types';
import {
  fetchDeviceMapping,
  createDeviceMapping,
  updateDeviceMapping,
  deleteDeviceMapping,
  downloadData,
  downloadTemplate,
} from '../api';
import { Pagination } from './Pagination';
import { UploadModal } from './UploadModal';
import { ConfirmDeleteModal } from './ConfirmDeleteModal';
import { DeviceMappingFormModal } from './DeviceMappingFormModal';
import { useTheme } from '../../../contexts/ThemeContext';

export function DeviceMappingTab() {
  const { theme } = useTheme();
  const [mappings, setMappings] = useState<DeviceMapping[]>([]);
  const [loading, setLoading] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [totalPages, setTotalPages] = useState(0);
  const [search, setSearch] = useState('');
  const [assetFilter, setAssetFilter] = useState('');
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [mappingToDelete, setMappingToDelete] = useState<number | null>(null);
  const [formModalOpen, setFormModalOpen] = useState(false);
  const [editingMapping, setEditingMapping] = useState<DeviceMapping | null>(null);
  
  // Check if asset details are available (when filtering by asset_code)
  const showAssetDetails = assetFilter && mappings.length > 0 && mappings.some(m => m.asset_name);

  const loadMappings = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetchDeviceMapping(currentPage, pageSize, search, assetFilter);
      setMappings(response.data);
      setTotalPages(response.total_pages);
    } catch (error) {
      window.alert(error instanceof Error ? error.message : 'Failed to load device mappings');
    } finally {
      setLoading(false);
    }
  }, [currentPage, pageSize, search, assetFilter]);

  useEffect(() => {
    loadMappings();
  }, [loadMappings]);

  const handleSave = async (data: Partial<DeviceMapping>) => {
    try {
      if (editingMapping) {
        await updateDeviceMapping({ ...data, id: editingMapping.id });
        window.alert('Device mapping updated successfully');
      } else {
        await createDeviceMapping(data);
        window.alert('Device mapping created successfully');
      }
      setFormModalOpen(false);
      setEditingMapping(null);
      loadMappings();
    } catch (error) {
      window.alert(error instanceof Error ? error.message : 'Failed to save device mapping');
    }
  };

  const confirmDelete = async () => {
    if (mappingToDelete == null) return;
    try {
      await deleteDeviceMapping(mappingToDelete);
      window.alert('Device mapping deleted successfully');
      loadMappings();
    } catch (error) {
      window.alert(error instanceof Error ? error.message : 'Failed to delete device mapping');
    } finally {
      setDeleteModalOpen(false);
      setMappingToDelete(null);
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

  return (
    <div className="card mt-3" style={{ backgroundColor: theme === 'dark' ? 'rgba(30, 41, 59, 0.5)' : '#ffffff', borderColor: theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : '#dee2e6' }}>
      <div className="card-header d-flex justify-content-between align-items-center" style={{ backgroundColor: theme === 'dark' ? 'rgba(15, 23, 42, 0.8)' : '#f8f9fa', borderColor: theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : '#dee2e6' }}>
        <h5 className="mb-0 font-bold" style={{ color: theme === 'dark' ? '#f1f5f9' : '#1a1a1a' }}>🔗 Device Mapping</h5>
        <div>
          <button
            className="btn btn-outline-info btn-sm"
            onClick={() => downloadTemplate('device_mapping')}
            title="Download CSV template"
          >
            📋 Download Template
          </button>
          <button className="btn btn-success btn-sm ms-2" onClick={() => downloadData('device_mapping')}>
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
              placeholder="Search mappings..."
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
                borderColor: theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : '#dee2e6'
              }}
            />
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
              ➕ Add Mapping
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
              #device-mapping-table-container {
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
              #device-mapping-table {
                width: max-content;
                min-width: 100%;
                margin-bottom: 0;
                border-collapse: separate;
                border-spacing: 0;
                background: ${tableBg};
              }
              #device-mapping-table thead th {
                background: ${tableHeaderBg} !important;
                color: ${tableHeaderText} !important;
                border-color: ${tableBorder} !important;
              }
              #device-mapping-table tbody td {
                background: ${tableRowBg} !important;
                color: ${tableRowText} !important;
                border-color: ${tableBorder} !important;
              }
              #device-mapping-table tbody tr:hover td {
                background: ${tableRowHoverBg} !important;
              }
              #device-mapping-table.table-striped tbody tr:nth-of-type(odd) td {
                background: ${tableRowBg} !important;
              }
              #device-mapping-table.table-striped tbody tr:nth-of-type(even) td {
                background: ${tableStripeBg} !important;
              }
              #device-mapping-table.table-striped tbody tr:nth-of-type(even):hover td {
                background: ${tableRowHoverBg} !important;
              }
            `}</style>
            <div id="device-mapping-table-container">
              <table className="table-striped table-hover table" id="device-mapping-table">
                <thead>
                  <tr>
                    <th>Asset Code</th>
                    {showAssetDetails && (
                      <>
                        <th>Asset Name</th>
                        <th>Country</th>
                        <th>Portfolio</th>
                      </>
                    )}
                    <th>Device Type</th>
                    <th>Metric</th>
                    <th>OEM Tag</th>
                    <th>Units</th>
                    <th>Data Type</th>
                    <th>Description</th>
                    <th>Fault Code</th>
                    <th>Module No</th>
                    <th>Default Value</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {mappings.length === 0 ? (
                    <tr>
                      <td colSpan={showAssetDetails ? 14 : 11} className="text-center font-medium" style={{ color: tableRowTextSecondary }}>
                        No device mappings found
                      </td>
                    </tr>
                  ) : (
                    mappings.map((mapping) => (
                      <tr key={mapping.id}>
                        <td className="font-medium" style={{ color: tableRowText }}>{mapping.asset_code}</td>
                        {showAssetDetails && (
                          <>
                            <td className="font-medium" style={{ color: tableRowText }}>{mapping.asset_name || '-'}</td>
                            <td className="font-medium" style={{ color: tableRowTextSecondary }}>{mapping.country || '-'}</td>
                            <td className="font-medium" style={{ color: tableRowTextSecondary }}>{mapping.portfolio || '-'}</td>
                          </>
                        )}
                        <td className="font-medium" style={{ color: tableRowTextSecondary }}>{mapping.device_type}</td>
                        <td className="font-medium" style={{ color: tableRowTextSecondary }}>{mapping.metric}</td>
                        <td className="font-medium" style={{ color: tableRowTextSecondary }}>{mapping.oem_tag}</td>
                        <td className="font-medium" style={{ color: tableRowTextSecondary }}>{mapping.units || '-'}</td>
                        <td className="font-medium" style={{ color: tableRowTextSecondary }}>{mapping.data_type || '-'}</td>
                        <td className="font-medium" style={{ color: tableRowTextSecondary }}>{mapping.description || '-'}</td>
                        <td className="font-medium" style={{ color: tableRowTextSecondary }}>{mapping.fault_code || '-'}</td>
                        <td className="font-medium" style={{ color: tableRowTextSecondary }}>{mapping.module_no || '-'}</td>
                        <td className="font-medium" style={{ color: tableRowTextSecondary }}>{mapping.default_value || '-'}</td>
                        <td>
                        <button
                          className="btn btn-outline-primary btn-sm me-2"
                          onClick={() => {
                            setEditingMapping(mapping);
                            setFormModalOpen(true);
                          }}
                        >
                          ✏️
                        </button>
                        <button
                          className="btn btn-outline-danger btn-sm"
                          onClick={() => {
                            setMappingToDelete(mapping.id);
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
        tableName="device_mapping"
        onUploadSuccess={() => {
          setUploadModalOpen(false);
          loadMappings();
        }}
        onError={(msg) => window.alert(msg)}
      />

      <ConfirmDeleteModal
        isOpen={deleteModalOpen}
        onClose={() => {
          setDeleteModalOpen(false);
          setMappingToDelete(null);
        }}
        onConfirm={confirmDelete}
        title="Delete Device Mapping"
        message="Are you sure you want to delete this mapping?"
      />

      <DeviceMappingFormModal
        isOpen={formModalOpen}
        onClose={() => {
          setFormModalOpen(false);
          setEditingMapping(null);
        }}
        onSave={handleSave}
        mapping={editingMapping}
      />
    </div>
  );
}
