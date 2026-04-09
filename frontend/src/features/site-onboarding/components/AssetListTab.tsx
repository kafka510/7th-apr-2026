 
import { useState, useEffect, useCallback } from 'react';
import type { AssetList, PaginatedResponse } from '../types';
import {
  fetchAssetList,
  createAssetList,
  updateAssetList,
  deleteAssetList,
  downloadData,
  downloadTemplate,
} from '../api';
import { Pagination } from './Pagination';
import { UploadModal } from './UploadModal';
import { ConfirmDeleteModal } from './ConfirmDeleteModal';
import { AssetFormModal } from './AssetFormModal';
import { useTheme } from '../../../contexts/ThemeContext';

export function AssetListTab() {
  const { theme } = useTheme();
  const [assets, setAssets] = useState<AssetList[]>([]);
  const [loading, setLoading] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [totalPages, setTotalPages] = useState(0);
  const [search, setSearch] = useState('');
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [assetToDelete, setAssetToDelete] = useState<string | null>(null);
  const [formModalOpen, setFormModalOpen] = useState(false);
  const [editingAsset, setEditingAsset] = useState<AssetList | null>(null);

  const loadAssets = useCallback(async () => {
    setLoading(true);
    try {
      const response: PaginatedResponse<AssetList> = await fetchAssetList(currentPage, pageSize, search);
      setAssets(response.data);
      setTotalPages(response.total_pages);
    } catch (error) {
      showAlert(error instanceof Error ? error.message : 'Failed to load assets', 'danger');
    } finally {
      setLoading(false);
    }
  }, [currentPage, pageSize, search]);

  useEffect(() => {
    loadAssets();
  }, [loadAssets]);

  const showAlert = (message: string, type: 'success' | 'danger' | 'warning' | 'info') => {
    // Temporary fallback until a UI alert system is added
    window.alert(`[${type.toUpperCase()}] ${message}`);
  };

  const handleSearch = (value: string) => {
    setSearch(value);
    setCurrentPage(1);
  };

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
  };

  const handlePageSizeChange = (newSize: number) => {
    setPageSize(newSize);
    setCurrentPage(1);
  };

  const handleAdd = () => {
    setEditingAsset(null);
    setFormModalOpen(true);
  };

  const handleEdit = (asset: AssetList) => {
    setEditingAsset(asset);
    setFormModalOpen(true);
  };

  const handleDelete = (assetCode: string) => {
    setAssetToDelete(assetCode);
    setDeleteModalOpen(true);
  };

  const confirmDelete = async () => {
    if (!assetToDelete) return;

    try {
      await deleteAssetList(assetToDelete);
      showAlert('Asset deleted successfully', 'success');
      loadAssets();
    } catch (error) {
      showAlert(error instanceof Error ? error.message : 'Failed to delete asset', 'danger');
    } finally {
      setDeleteModalOpen(false);
      setAssetToDelete(null);
    }
  };

  const handleSave = async (data: Partial<AssetList>) => {
    try {
      if (editingAsset) {
        await updateAssetList({ ...data, asset_code: editingAsset.asset_code });
        showAlert('Asset updated successfully', 'success');
      } else {
        await createAssetList(data);
        showAlert('Asset created successfully', 'success');
      }
      setFormModalOpen(false);
      setEditingAsset(null);
      loadAssets();
    } catch (error) {
      showAlert(error instanceof Error ? error.message : 'Failed to save asset', 'danger');
    }
  };

  const handleUploadSuccess = () => {
    showAlert('CSV uploaded successfully', 'success');
    loadAssets();
  };

  const formatDate = (dateString: string) => {
    if (!dateString) return '';
    try {
      return new Date(dateString).toLocaleDateString();
    } catch {
      return dateString;
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
  const stickyHeaderBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.95)' : '#212529';
  const stickyCellBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.8)' : '#fff';
  const stickyCellHoverBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.9)' : '#f8f9fa';
  const stickyCellStripeBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.3)' : 'rgba(0, 0, 0, 0.05)';
  const stickyCellStripeHoverBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.5)' : '#f8f9fa';
  const stickyBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : '#495057';
  const containerBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : '#dee2e6';

  return (
    <div className="card mt-3" style={{ backgroundColor: theme === 'dark' ? 'rgba(30, 41, 59, 0.5)' : '#ffffff', borderColor: theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : '#dee2e6' }}>
      <div className="card-header d-flex justify-content-between align-items-center" style={{ backgroundColor: theme === 'dark' ? 'rgba(15, 23, 42, 0.8)' : '#f8f9fa', borderColor: theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : '#dee2e6' }}>
        <h5 className="mb-0 font-bold" style={{ color: theme === 'dark' ? '#f1f5f9' : '#1a1a1a' }}>🏢 Asset List</h5>
        <div>
          <button
            className="btn btn-outline-info btn-sm"
            onClick={() => downloadTemplate('asset_list')}
            title="Download CSV template with sample data"
          >
            📋 Download Template
          </button>
          <button className="btn btn-success btn-sm ms-2" onClick={() => downloadData('asset_list')}>
            📥 Download CSV
          </button>
          <button className="btn btn-primary btn-sm ms-2" onClick={() => setUploadModalOpen(true)}>
            📤 Upload CSV
          </button>
        </div>
      </div>
      <div className="card-body" style={{ backgroundColor: theme === 'dark' ? 'rgba(30, 41, 59, 0.3)' : '#ffffff' }}>
        {/* Search and Controls */}
        <div className="row mb-3">
          <div className="col-md-6">
            <input
              type="text"
              className="form-control"
              placeholder="Search assets..."
              value={search}
              onChange={(e) => handleSearch(e.target.value)}
              style={{
                backgroundColor: theme === 'dark' ? 'rgba(15, 23, 42, 0.8)' : '#ffffff',
                color: theme === 'dark' ? '#f1f5f9' : '#1a1a1a',
                borderColor: theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : '#dee2e6'
              }}
            />
          </div>
          <div className="col-md-6 text-end">
            <select
              className="form-select"
              style={{ 
                width: 'auto', 
                display: 'inline-block',
                backgroundColor: theme === 'dark' ? 'rgba(15, 23, 42, 0.8)' : '#ffffff',
                color: theme === 'dark' ? '#f1f5f9' : '#1a1a1a',
                borderColor: theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : '#dee2e6'
              }}
              value={pageSize}
              onChange={(e) => handlePageSizeChange(Number(e.target.value))}
            >
              <option value={25}>25 per page</option>
              <option value={50}>50 per page</option>
              <option value={100}>100 per page</option>
            </select>
          </div>
        </div>

        {/* Loading Spinner */}
        {loading && (
          <div className="text-center">
            <div className="spinner-border" role="status">
              <span className="visually-hidden">Loading...</span>
            </div>
          </div>
        )}

        {/* Add New Asset Button */}
        <div className="mb-3">
          <button className="btn btn-success btn-sm" onClick={handleAdd}>
            ➕ Add New Asset
          </button>
        </div>

        {/* Asset Table */}
        {!loading && (
          <>
            <style>{`
              #asset-table-container {
                position: relative;
                overflow-x: scroll;
                overflow-y: auto;
                max-height: 600px;
                width: 100%;
                border: 1px solid ${containerBorder};
                border-radius: 0.375rem;
                -webkit-overflow-scrolling: touch;
                background: ${tableBg};
              }
              #asset-table {
                width: max-content;
                min-width: 100%;
                margin-bottom: 0;
                border-collapse: separate;
                border-spacing: 0;
                background: ${tableBg};
              }
              #asset-table thead th {
                background: ${tableHeaderBg} !important;
                color: ${tableHeaderText} !important;
                border-color: ${tableBorder} !important;
              }
              #asset-table tbody td {
                background: ${tableRowBg} !important;
                color: ${tableRowText} !important;
                border-color: ${tableBorder} !important;
              }
              #asset-table tbody tr:hover td {
                background: ${tableRowHoverBg} !important;
              }
              #asset-table.table-striped tbody tr:nth-of-type(odd) td {
                background: ${tableRowBg} !important;
              }
              #asset-table.table-striped tbody tr:nth-of-type(even) td {
                background: ${tableStripeBg} !important;
              }
              #asset-table.table-striped tbody tr:nth-of-type(even):hover td {
                background: ${tableRowHoverBg} !important;
              }
              #asset-table th.sticky-actions-header {
                position: sticky !important;
                right: 0 !important;
                z-index: 102 !important;
                background: ${stickyHeaderBg} !important;
                min-width: 150px !important;
                width: 150px !important;
                box-shadow: -3px 0 6px rgba(0,0,0,0.2) !important;
                border-left: 2px solid ${stickyBorder} !important;
                color: ${tableHeaderText} !important;
              }
              #asset-table td.sticky-actions-cell {
                position: sticky !important;
                right: 0 !important;
                z-index: 101 !important;
                background: ${stickyCellBg} !important;
                min-width: 150px !important;
                width: 150px !important;
                white-space: nowrap !important;
                box-shadow: -3px 0 6px rgba(0,0,0,0.2) !important;
                text-align: center !important;
                border-left: 2px solid ${tableBorder} !important;
              }
              #asset-table tbody tr:hover td.sticky-actions-cell {
                background: ${stickyCellHoverBg} !important;
              }
              #asset-table tbody tr:nth-child(even) td.sticky-actions-cell {
                background: ${stickyCellStripeBg} !important;
              }
              #asset-table tbody tr:nth-child(even):hover td.sticky-actions-cell {
                background: ${stickyCellStripeHoverBg} !important;
              }
              #asset-table.table-striped tbody tr:nth-of-type(odd) td.sticky-actions-cell {
                background: ${stickyCellBg} !important;
              }
              #asset-table.table-striped tbody tr:nth-of-type(even) td.sticky-actions-cell {
                background: ${stickyCellStripeBg} !important;
              }
              #asset-table.table-striped tbody tr:nth-of-type(even):hover td.sticky-actions-cell {
                background: ${stickyCellStripeHoverBg} !important;
              }
            `}</style>
            <div id="asset-table-container">
              <table className="table-striped table-hover table" id="asset-table">
              <thead>
                <tr>
                  <th>Asset Code</th>
                  <th>Asset Name</th>
                  <th>Provider Asset ID</th>
                  <th>Capacity (kWh)</th>
                  <th>Address</th>
                  <th>Country</th>
                  <th>Portfolio</th>
                  <th>Latitude</th>
                  <th>Longitude</th>
                  <th>Contact Person</th>
                  <th>Contact Method</th>
                  <th>Grid Connection</th>
                  <th>Asset Number</th>
                  <th>Customer Name</th>
                  <th>Timezone</th>
                  <th>Asset Name OEM</th>
                  <th>COD</th>
                  <th>Operational COD</th>
                  <th>Y1 Degradation (%)</th>
                  <th>Annual Degradation (%)</th>
                  <th>API Name</th>
                  <th>API Key</th>
                  <th 
                    className="sticky-actions-header"
                    style={{
                      position: 'sticky',
                      right: 0,
                      zIndex: 102,
                      background: stickyHeaderBg,
                      minWidth: '150px',
                      width: '150px',
                      boxShadow: '-3px 0 6px rgba(0,0,0,0.2)',
                      borderLeft: `2px solid ${stickyBorder}`,
                      color: tableHeaderText
                    }}
                  >
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {assets.length === 0 ? (
                  <tr>
                    <td colSpan={23} className="text-center font-medium" style={{ color: tableRowTextSecondary }}>
                      No assets found
                    </td>
                  </tr>
                ) : (
                  assets.map((asset) => (
                    <tr key={asset.asset_code}>
                      <td className="font-medium" style={{ color: tableRowText }}>{asset.asset_code}</td>
                      <td className="font-medium" style={{ color: tableRowText }}>{asset.asset_name}</td>
                      <td className="font-medium" style={{ color: tableRowTextSecondary }}>{asset.provider_asset_id || ''}</td>
                      <td className="font-medium" style={{ color: tableRowTextSecondary }}>{asset.capacity || 0}</td>
                      <td className="font-medium" style={{ color: tableRowTextSecondary }}>{asset.address || ''}</td>
                      <td className="font-medium" style={{ color: tableRowTextSecondary }}>{asset.country}</td>
                      <td className="font-medium" style={{ color: tableRowTextSecondary }}>{asset.portfolio}</td>
                      <td className="font-medium" style={{ color: tableRowTextSecondary }}>{asset.latitude || 0}</td>
                      <td className="font-medium" style={{ color: tableRowTextSecondary }}>{asset.longitude || 0}</td>
                      <td className="font-medium" style={{ color: tableRowTextSecondary }}>{asset.contact_person || ''}</td>
                      <td className="font-medium" style={{ color: tableRowTextSecondary }}>{asset.contact_method || ''}</td>
                      <td className="font-medium" style={{ color: tableRowTextSecondary }}>{formatDate(asset.grid_connection_date)}</td>
                      <td className="font-medium" style={{ color: tableRowTextSecondary }}>{asset.asset_number || ''}</td>
                      <td className="font-medium" style={{ color: tableRowTextSecondary }}>{asset.customer_name || ''}</td>
                      <td className="font-medium" style={{ color: tableRowTextSecondary }}>{asset.timezone || ''}</td>
                      <td className="font-medium" style={{ color: tableRowTextSecondary }}>{asset.asset_name_oem || ''}</td>
                      <td className="font-medium" style={{ color: tableRowTextSecondary }}>{formatDate(asset.cod)}</td>
                      <td className="font-medium" style={{ color: tableRowTextSecondary }}>{formatDate(asset.operational_cod)}</td>
                      <td className="font-medium" style={{ color: tableRowTextSecondary }}>{asset.y1_degradation ?? ''}</td>
                      <td className="font-medium" style={{ color: tableRowTextSecondary }}>{asset.anual_degradation ?? ''}</td>
                      <td className="font-medium" style={{ color: tableRowTextSecondary }}>{asset.api_name || ''}</td>
                      <td className="font-medium" style={{ color: tableRowTextSecondary }}>{asset.api_key || ''}</td>
                      <td 
                        className="sticky-actions-cell"
                        style={{
                          position: 'sticky',
                          right: 0,
                          zIndex: 101,
                          background: stickyCellBg,
                          minWidth: '150px',
                          width: '150px',
                          whiteSpace: 'nowrap',
                          boxShadow: '-3px 0 6px rgba(0,0,0,0.2)',
                          textAlign: 'center',
                          borderLeft: `2px solid ${tableBorder}`
                        }}
                      >
                        <button
                          className="btn btn-outline-primary btn-sm me-2"
                          onClick={() => handleEdit(asset)}
                          title="Edit"
                        >
                          ✏️
                        </button>
                        <button
                          className="btn btn-outline-danger btn-sm"
                          onClick={() => handleDelete(asset.asset_code)}
                          title="Delete"
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

        {/* Pagination */}
        {!loading && totalPages > 1 && (
          <Pagination currentPage={currentPage} totalPages={totalPages} onPageChange={handlePageChange} />
        )}
      </div>

      {/* Modals */}
      <UploadModal
        isOpen={uploadModalOpen}
        onClose={() => setUploadModalOpen(false)}
        tableName="asset_list"
        onUploadSuccess={handleUploadSuccess}
        onError={(msg) => showAlert(msg, 'danger')}
      />

      <ConfirmDeleteModal
        isOpen={deleteModalOpen}
        onClose={() => {
          setDeleteModalOpen(false);
          setAssetToDelete(null);
        }}
        onConfirm={confirmDelete}
        title="Confirm Delete"
        message={`Are you sure you want to delete asset "${assetToDelete}"?`}
        itemName={assetToDelete || undefined}
      />

        <AssetFormModal
        isOpen={formModalOpen}
        onClose={() => {
          setFormModalOpen(false);
          setEditingAsset(null);
        }}
        onSave={handleSave}
        asset={editingAsset}
      />
    </div>
  );
}

