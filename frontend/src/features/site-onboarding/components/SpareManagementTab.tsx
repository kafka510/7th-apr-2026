import { useCallback, useEffect, useState } from 'react';
import type { 
  SpareMaster, 
  LocationMaster, 
  SpareSiteMap, 
  StockBalance, 
  StockEntry, 
  StockIssue,
  AssetList 
} from '../types';
import {
  fetchSpareMaster,
  createSpareMaster,
  updateSpareMaster,
  deleteSpareMaster,
  fetchLocationMaster,
  createLocationMaster,
  updateLocationMaster,
  deleteLocationMaster,
  fetchSpareSiteMap,
  createSpareSiteMap,
  updateSpareSiteMap,
  deleteSpareSiteMap,
  fetchStockBalance,
  fetchStockEntry,
  createStockEntry,
  fetchStockIssue,
  createStockIssue,
  downloadData,
  downloadTemplate,
  getAllAssets,
} from '../api';
import { Pagination } from './Pagination';
import { UploadModal } from './UploadModal';
import { ConfirmDeleteModal } from './ConfirmDeleteModal';
import { SpareMasterFormModal } from './SpareMasterFormModal';
import { LocationMasterFormModal } from './LocationMasterFormModal';
import { SpareSiteMapFormModal } from './SpareSiteMapFormModal';
import { StockEntryFormModal } from './StockEntryFormModal';
import { StockIssueFormModal } from './StockIssueFormModal';
import { useTheme } from '../../../contexts/ThemeContext';

type SpareSubTab = 'spares' | 'locations' | 'mapping' | 'balance' | 'entry' | 'issue';

export function SpareManagementTab() {
  const { theme } = useTheme();
  const [activeSubTab, setActiveSubTab] = useState<SpareSubTab>('spares');
  
  // Common state
  const [loading, setLoading] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize] = useState(25);
  const [totalPages, setTotalPages] = useState(0);
  const [search, setSearch] = useState('');
  const [assetFilter, setAssetFilter] = useState('');
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [allAssets, setAllAssets] = useState<AssetList[]>([]);
  
  // Spare Master state
  const [spares, setSpares] = useState<SpareMaster[]>([]);
  const [spareToDelete, setSpareToDelete] = useState<number | null>(null);
  const [spareFormOpen, setSpareFormOpen] = useState(false);
  const [editingSpare, setEditingSpare] = useState<SpareMaster | null>(null);
  
  // Location Master state
  const [locations, setLocations] = useState<LocationMaster[]>([]);
  const [locationToDelete, setLocationToDelete] = useState<number | null>(null);
  const [locationFormOpen, setLocationFormOpen] = useState(false);
  const [editingLocation, setEditingLocation] = useState<LocationMaster | null>(null);
  
  // Spare Site Map state
  const [mappings, setMappings] = useState<SpareSiteMap[]>([]);
  const [mappingToDelete, setMappingToDelete] = useState<number | null>(null);
  const [mappingFormOpen, setMappingFormOpen] = useState(false);
  const [editingMapping, setEditingMapping] = useState<SpareSiteMap | null>(null);
  
  // Stock Balance state (read-only)
  const [balances, setBalances] = useState<StockBalance[]>([]);
  
  // Stock Entry state
  const [entries, setEntries] = useState<StockEntry[]>([]);
  const [entryFormOpen, setEntryFormOpen] = useState(false);
  
  // Stock Issue state
  const [issues, setIssues] = useState<StockIssue[]>([]);
  const [issueFormOpen, setIssueFormOpen] = useState(false);

  // Load assets for dropdowns
  useEffect(() => {
    getAllAssets().then(setAllAssets).catch(err => {
      console.error('Failed to load assets:', err);
    });
  }, []);

  // Load data based on active sub-tab
  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      switch (activeSubTab) {
        case 'spares':
          const spareResponse = await fetchSpareMaster(currentPage, pageSize, search);
          setSpares(spareResponse.data);
          setTotalPages(spareResponse.total_pages);
          break;
        case 'locations':
          const locationResponse = await fetchLocationMaster(currentPage, pageSize, search);
          setLocations(locationResponse.data);
          setTotalPages(locationResponse.total_pages);
          break;
        case 'mapping':
          const mappingResponse = await fetchSpareSiteMap(currentPage, pageSize, search, assetFilter);
          setMappings(mappingResponse.data);
          setTotalPages(mappingResponse.total_pages);
          break;
        case 'balance':
          const balanceResponse = await fetchStockBalance(currentPage, pageSize, search, assetFilter);
          setBalances(balanceResponse.data);
          setTotalPages(balanceResponse.total_pages);
          break;
        case 'entry':
          const entryResponse = await fetchStockEntry(currentPage, pageSize, search, assetFilter);
          setEntries(entryResponse.data);
          setTotalPages(entryResponse.total_pages);
          break;
        case 'issue':
          const issueResponse = await fetchStockIssue(currentPage, pageSize, search, assetFilter);
          setIssues(issueResponse.data);
          setTotalPages(issueResponse.total_pages);
          break;
      }
    } catch (error) {
      window.alert(error instanceof Error ? error.message : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  }, [activeSubTab, currentPage, pageSize, search, assetFilter]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Get current table name for upload/download
  const getCurrentTableName = (): 'spare_master' | 'location_master' | 'spare_site_map' | 'stock_entry' | 'stock_issue' => {
    switch (activeSubTab) {
      case 'spares': return 'spare_master';
      case 'locations': return 'location_master';
      case 'mapping': return 'spare_site_map';
      case 'entry': return 'stock_entry';
      case 'issue': return 'stock_issue';
      default: return 'spare_master';
    }
  };

  // Check if user is admin (for edit/create) and superuser (for delete)
  // This should be fetched from user context or API
  const [isAdmin] = useState(true); // TODO: Get from user context
  const [isSuperuser] = useState(false); // TODO: Get from user context

  // Theme-aware colors
  const tabBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.5)' : 'rgba(255, 255, 255, 0.9)';
  const tabActiveBg = theme === 'dark' ? 'rgba(56, 189, 248, 0.3)' : 'rgba(59, 130, 246, 0.15)';
  const tabActiveText = theme === 'dark' ? '#7dd3fc' : '#1e40af';
  const tabInactiveText = theme === 'dark' ? '#94a3b8' : '#64748b';
  const tableBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.5)' : '#ffffff';
  const tableHeaderBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.9)' : '#212529';
  const tableHeaderText = theme === 'dark' ? '#f1f5f9' : '#ffffff';
  const tableRowText = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';
  const tableBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : '#dee2e6';

  return (
    <div className="card mt-3" style={{ backgroundColor: tableBg, borderColor: tableBorder }}>
      <div className="card-header" style={{ backgroundColor: theme === 'dark' ? 'rgba(15, 23, 42, 0.8)' : '#f8f9fa', borderColor: tableBorder }}>
        <h5 className="mb-0 font-bold" style={{ color: theme === 'dark' ? '#f1f5f9' : '#1a1a1a' }}>
          🔧 Spare Management
        </h5>
      </div>

      {/* Sub-tab Navigation */}
      <div className="card-body border-bottom p-2" style={{ backgroundColor: tabBg, borderColor: tableBorder }}>
        <div className="d-flex flex-wrap gap-1">
          {(['spares', 'locations', 'mapping', 'balance', 'entry', 'issue'] as SpareSubTab[]).map((tab) => (
            <button
              key={tab}
              className="btn btn-sm"
              style={{
                backgroundColor: activeSubTab === tab ? tabActiveBg : 'transparent',
                color: activeSubTab === tab ? tabActiveText : tabInactiveText,
                borderColor: tableBorder,
                flex: '1 1 auto',
                minWidth: '100px',
              }}
              onClick={() => {
                setActiveSubTab(tab);
                setCurrentPage(1);
                setSearch('');
                setAssetFilter('');
              }}
            >
              {tab === 'spares' && '📦 Spares'}
              {tab === 'locations' && '📍 Locations'}
              {tab === 'mapping' && '🗺️ Mapping'}
              {tab === 'balance' && '📊 Balance'}
              {tab === 'entry' && '📥 Entry'}
              {tab === 'issue' && '📤 Issue'}
            </button>
          ))}
        </div>
      </div>

      {/* Filters and Actions */}
      <div className="card-body border-bottom" style={{ backgroundColor: theme === 'dark' ? 'rgba(30, 41, 59, 0.3)' : '#f8f9fa', borderColor: tableBorder }}>
        <div className="row mb-2">
          <div className="col-md-4">
            <input
              type="text"
              className="form-control form-control-sm"
              placeholder="Search..."
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setCurrentPage(1);
              }}
              style={{
                backgroundColor: theme === 'dark' ? 'rgba(15, 23, 42, 0.8)' : '#ffffff',
                color: theme === 'dark' ? '#f1f5f9' : '#1a1a1a',
                borderColor: tableBorder
              }}
            />
          </div>
          {(activeSubTab === 'mapping' || activeSubTab === 'balance' || activeSubTab === 'entry' || activeSubTab === 'issue') && (
            <div className="col-md-4">
              <select
                className="form-control form-control-sm"
                value={assetFilter}
                onChange={(e) => {
                  setAssetFilter(e.target.value);
                  setCurrentPage(1);
                }}
                style={{
                  backgroundColor: theme === 'dark' ? 'rgba(15, 23, 42, 0.8)' : '#ffffff',
                  color: theme === 'dark' ? '#f1f5f9' : '#1a1a1a',
                  borderColor: tableBorder
                }}
              >
                <option value="">All Assets</option>
                {allAssets.map(asset => (
                  <option key={asset.asset_code} value={asset.asset_code}>
                    {asset.asset_code} - {asset.asset_name}
                  </option>
                ))}
              </select>
            </div>
          )}
          <div className="col-md-4 text-end">
            <button
              className="btn btn-outline-info btn-sm me-2"
              onClick={() => downloadTemplate(getCurrentTableName())}
            >
              📋 Template
            </button>
            <button
              className="btn btn-success btn-sm me-2"
              onClick={() => downloadData(getCurrentTableName(), { asset_code: assetFilter, search })}
            >
              📥 Download
            </button>
            <button
              className="btn btn-primary btn-sm me-2"
              onClick={() => setUploadModalOpen(true)}
            >
              📤 Upload
            </button>
            {isAdmin && activeSubTab !== 'balance' && (
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => {
                  if (activeSubTab === 'spares') {
                    setEditingSpare(null);
                    setSpareFormOpen(true);
                  } else if (activeSubTab === 'locations') {
                    setEditingLocation(null);
                    setLocationFormOpen(true);
                  } else if (activeSubTab === 'mapping') {
                    setEditingMapping(null);
                    setMappingFormOpen(true);
                  } else if (activeSubTab === 'entry') {
                    setEntryFormOpen(true);
                  } else if (activeSubTab === 'issue') {
                    setIssueFormOpen(true);
                  }
                }}
              >
                ➕ Add
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Data Table */}
      <div className="card-body p-0">
        {loading ? (
          <div className="p-4 text-center" style={{ color: tableRowText }}>
            Loading...
          </div>
        ) : (
          <>
            {/* Spare Master Table */}
            {activeSubTab === 'spares' && (
              <div className="table-responsive">
                <table className="table-hover mb-0 table">
                  <thead style={{ backgroundColor: tableHeaderBg }}>
                    <tr>
                      <th style={{ color: tableHeaderText }}>Spare Code</th>
                      <th style={{ color: tableHeaderText }}>Spare Name</th>
                      <th style={{ color: tableHeaderText }}>Category</th>
                      <th style={{ color: tableHeaderText }}>Unit</th>
                      <th style={{ color: tableHeaderText }}>Min Stock</th>
                      <th style={{ color: tableHeaderText }}>Max Stock</th>
                      <th style={{ color: tableHeaderText }}>Critical</th>
                      {isAdmin && <th style={{ color: tableHeaderText }}>Actions</th>}
                    </tr>
                  </thead>
                  <tbody>
                    {spares.map((spare) => (
                      <tr key={spare.spare_id} style={{ color: tableRowText }}>
                        <td>{spare.spare_code}</td>
                        <td>{spare.spare_name}</td>
                        <td>{spare.category || '-'}</td>
                        <td>{spare.unit}</td>
                        <td>{spare.min_stock ?? '-'}</td>
                        <td>{spare.max_stock ?? '-'}</td>
                        <td>{spare.is_critical ? 'Yes' : 'No'}</td>
                        {isAdmin && (
                          <td>
                            <button
                              className="btn btn-sm btn-outline-primary me-1"
                              onClick={() => {
                                setEditingSpare(spare);
                                setSpareFormOpen(true);
                              }}
                            >
                              ✏️ Edit
                            </button>
                            {isSuperuser && (
                              <button
                                className="btn btn-sm btn-outline-danger"
                                onClick={() => {
                                  setSpareToDelete(spare.spare_id);
                                  setDeleteModalOpen(true);
                                }}
                              >
                                🗑️ Delete
                              </button>
                            )}
                          </td>
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Location Master Table */}
            {activeSubTab === 'locations' && (
              <div className="table-responsive">
                <table className="table-hover mb-0 table">
                  <thead style={{ backgroundColor: tableHeaderBg }}>
                    <tr>
                      <th style={{ color: tableHeaderText }}>Location Code</th>
                      <th style={{ color: tableHeaderText }}>Location Name</th>
                      <th style={{ color: tableHeaderText }}>Type</th>
                      {isAdmin && <th style={{ color: tableHeaderText }}>Actions</th>}
                    </tr>
                  </thead>
                  <tbody>
                    {locations.map((location) => (
                      <tr key={location.location_id} style={{ color: tableRowText }}>
                        <td>{location.location_code}</td>
                        <td>{location.location_name}</td>
                        <td>{location.location_type || '-'}</td>
                        {isAdmin && (
                          <td>
                            <button
                              className="btn btn-sm btn-outline-primary me-1"
                              onClick={() => {
                                setEditingLocation(location);
                                setLocationFormOpen(true);
                              }}
                            >
                              ✏️ Edit
                            </button>
                            {isSuperuser && (
                              <button
                                className="btn btn-sm btn-outline-danger"
                                onClick={() => {
                                  setLocationToDelete(location.location_id);
                                  setDeleteModalOpen(true);
                                }}
                              >
                                🗑️ Delete
                              </button>
                            )}
                          </td>
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Spare Site Map Table */}
            {activeSubTab === 'mapping' && (
              <div className="table-responsive">
                <table className="table-hover mb-0 table">
                  <thead style={{ backgroundColor: tableHeaderBg }}>
                    <tr>
                      <th style={{ color: tableHeaderText }}>Asset Code</th>
                      <th style={{ color: tableHeaderText }}>Spare Code</th>
                      <th style={{ color: tableHeaderText }}>Location Code</th>
                      <th style={{ color: tableHeaderText }}>Active</th>
                      {isAdmin && <th style={{ color: tableHeaderText }}>Actions</th>}
                    </tr>
                  </thead>
                  <tbody>
                    {mappings.map((mapping) => (
                      <tr key={mapping.map_id} style={{ color: tableRowText }}>
                        <td>{mapping.asset_code}</td>
                        <td>{mapping.spare_code}</td>
                        <td>{mapping.location_code}</td>
                        <td>{mapping.is_active ? 'Yes' : 'No'}</td>
                        {isAdmin && (
                          <td>
                            <button
                              className="btn btn-sm btn-outline-primary me-1"
                              onClick={() => {
                                setEditingMapping(mapping);
                                setMappingFormOpen(true);
                              }}
                            >
                              ✏️ Edit
                            </button>
                            {isSuperuser && (
                              <button
                                className="btn btn-sm btn-outline-danger"
                                onClick={() => {
                                  setMappingToDelete(mapping.map_id);
                                  setDeleteModalOpen(true);
                                }}
                              >
                                🗑️ Delete
                              </button>
                            )}
                          </td>
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Stock Balance Table (Read-only) */}
            {activeSubTab === 'balance' && (
              <div className="table-responsive">
                <table className="table-hover mb-0 table">
                  <thead style={{ backgroundColor: tableHeaderBg }}>
                    <tr>
                      <th style={{ color: tableHeaderText }}>Spare Code</th>
                      <th style={{ color: tableHeaderText }}>Location Code</th>
                      <th style={{ color: tableHeaderText }}>Quantity</th>
                      <th style={{ color: tableHeaderText }}>Unit</th>
                      <th style={{ color: tableHeaderText }}>Last Updated</th>
                    </tr>
                  </thead>
                  <tbody>
                    {balances.map((balance) => (
                      <tr key={balance.stock_balance_id} style={{ color: tableRowText }}>
                        <td>{balance.spare_code}</td>
                        <td>{balance.location_code}</td>
                        <td>{balance.quantity}</td>
                        <td>{balance.unit}</td>
                        <td>{new Date(balance.last_updated).toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Stock Entry Table */}
            {activeSubTab === 'entry' && (
              <div className="table-responsive">
                <table className="table-hover mb-0 table">
                  <thead style={{ backgroundColor: tableHeaderBg }}>
                    <tr>
                      <th style={{ color: tableHeaderText }}>Entry Date</th>
                      <th style={{ color: tableHeaderText }}>Spare Code</th>
                      <th style={{ color: tableHeaderText }}>Location</th>
                      <th style={{ color: tableHeaderText }}>Quantity</th>
                      <th style={{ color: tableHeaderText }}>Type</th>
                      <th style={{ color: tableHeaderText }}>Reference</th>
                      <th style={{ color: tableHeaderText }}>Performed By</th>
                    </tr>
                  </thead>
                  <tbody>
                    {entries.map((entry) => (
                      <tr key={entry.entry_id} style={{ color: tableRowText }}>
                        <td>{new Date(entry.entry_date).toLocaleString()}</td>
                        <td>{entry.spare_code}</td>
                        <td>{entry.location_code}</td>
                        <td>{entry.quantity} {entry.unit}</td>
                        <td>{entry.entry_type}</td>
                        <td>{entry.reference_number || '-'}</td>
                        <td>{entry.performed_by}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Stock Issue Table */}
            {activeSubTab === 'issue' && (
              <div className="table-responsive">
                <table className="table-hover mb-0 table">
                  <thead style={{ backgroundColor: tableHeaderBg }}>
                    <tr>
                      <th style={{ color: tableHeaderText }}>Issue Date</th>
                      <th style={{ color: tableHeaderText }}>Spare Code</th>
                      <th style={{ color: tableHeaderText }}>Location</th>
                      <th style={{ color: tableHeaderText }}>Quantity</th>
                      <th style={{ color: tableHeaderText }}>Type</th>
                      <th style={{ color: tableHeaderText }}>Ticket</th>
                      <th style={{ color: tableHeaderText }}>Issued To</th>
                      <th style={{ color: tableHeaderText }}>Performed By</th>
                    </tr>
                  </thead>
                  <tbody>
                    {issues.map((issue) => (
                      <tr key={issue.issue_id} style={{ color: tableRowText }}>
                        <td>{new Date(issue.issue_date).toLocaleString()}</td>
                        <td>{issue.spare_code}</td>
                        <td>{issue.location_code}</td>
                        <td>{issue.quantity} {issue.unit}</td>
                        <td>{issue.issue_type}</td>
                        <td>{issue.ticket_number || '-'}</td>
                        <td>{issue.issued_to || '-'}</td>
                        <td>{issue.performed_by}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {((activeSubTab === 'spares' && spares.length === 0) ||
              (activeSubTab === 'locations' && locations.length === 0) ||
              (activeSubTab === 'mapping' && mappings.length === 0) ||
              (activeSubTab === 'balance' && balances.length === 0) ||
              (activeSubTab === 'entry' && entries.length === 0) ||
              (activeSubTab === 'issue' && issues.length === 0)) && (
              <div className="p-4 text-center" style={{ color: tableRowText }}>
                No data found
              </div>
            )}
          </>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="card-footer" style={{ backgroundColor: theme === 'dark' ? 'rgba(15, 23, 42, 0.8)' : '#f8f9fa', borderColor: tableBorder }}>
          <Pagination
            currentPage={currentPage}
            totalPages={totalPages}
            onPageChange={setCurrentPage}
          />
        </div>
      )}

      {/* Modals */}
      <UploadModal
        isOpen={uploadModalOpen}
        onClose={() => setUploadModalOpen(false)}
        tableName={getCurrentTableName()}
        onUploadSuccess={loadData}
        onError={(message) => window.alert(`Upload error: ${message}`)}
      />

      <SpareMasterFormModal
        isOpen={spareFormOpen}
        onClose={() => {
          setSpareFormOpen(false);
          setEditingSpare(null);
        }}
        onSave={async (data) => {
          try {
            if (editingSpare) {
              await updateSpareMaster(editingSpare.spare_id, data);
              window.alert('Spare updated successfully');
            } else {
              await createSpareMaster(data);
              window.alert('Spare created successfully');
            }
            setSpareFormOpen(false);
            setEditingSpare(null);
            loadData();
          } catch (error) {
            window.alert(error instanceof Error ? error.message : 'Failed to save spare');
          }
        }}
        spare={editingSpare}
      />

      <LocationMasterFormModal
        isOpen={locationFormOpen}
        onClose={() => {
          setLocationFormOpen(false);
          setEditingLocation(null);
        }}
        onSave={async (data) => {
          try {
            if (editingLocation) {
              await updateLocationMaster(editingLocation.location_id, data);
              window.alert('Location updated successfully');
            } else {
              await createLocationMaster(data);
              window.alert('Location created successfully');
            }
            setLocationFormOpen(false);
            setEditingLocation(null);
            loadData();
          } catch (error) {
            window.alert(error instanceof Error ? error.message : 'Failed to save location');
          }
        }}
        location={editingLocation}
      />

      <SpareSiteMapFormModal
        isOpen={mappingFormOpen}
        onClose={() => {
          setMappingFormOpen(false);
          setEditingMapping(null);
        }}
        onSave={async (data) => {
          try {
            if (editingMapping) {
              await updateSpareSiteMap(editingMapping.map_id, data);
              window.alert('Mapping updated successfully');
            } else {
              await createSpareSiteMap(data);
              window.alert('Mapping created successfully');
            }
            setMappingFormOpen(false);
            setEditingMapping(null);
            loadData();
          } catch (error) {
            window.alert(error instanceof Error ? error.message : 'Failed to save mapping');
          }
        }}
        mapping={editingMapping}
      />

      <StockEntryFormModal
        isOpen={entryFormOpen}
        onClose={() => setEntryFormOpen(false)}
        onSave={async (data) => {
          try {
            const result = await createStockEntry(data);
            window.alert(result.message || 'Stock entry created successfully');
            setEntryFormOpen(false);
            loadData();
          } catch (error) {
            window.alert(error instanceof Error ? error.message : 'Failed to create stock entry');
          }
        }}
      />

      <StockIssueFormModal
        isOpen={issueFormOpen}
        onClose={() => setIssueFormOpen(false)}
        onSave={async (data) => {
          try {
            const result = await createStockIssue(data);
            window.alert(result.message || 'Stock issue created successfully');
            setIssueFormOpen(false);
            loadData();
          } catch (error) {
            window.alert(error instanceof Error ? error.message : 'Failed to create stock issue');
          }
        }}
      />

      <ConfirmDeleteModal
        isOpen={deleteModalOpen}
        onClose={() => {
          setDeleteModalOpen(false);
          setSpareToDelete(null);
          setLocationToDelete(null);
          setMappingToDelete(null);
        }}
        onConfirm={async () => {
          try {
            if (activeSubTab === 'spares' && spareToDelete) {
              await deleteSpareMaster(spareToDelete);
              window.alert('Spare deleted successfully');
            } else if (activeSubTab === 'locations' && locationToDelete) {
              await deleteLocationMaster(locationToDelete);
              window.alert('Location deleted successfully');
            } else if (activeSubTab === 'mapping' && mappingToDelete) {
              await deleteSpareSiteMap(mappingToDelete);
              window.alert('Mapping deleted successfully');
            }
            loadData();
          } catch (error) {
            window.alert(error instanceof Error ? error.message : 'Failed to delete');
          } finally {
            setDeleteModalOpen(false);
            setSpareToDelete(null);
            setLocationToDelete(null);
            setMappingToDelete(null);
          }
        }}
        title="Confirm Delete"
        message={
          activeSubTab === 'spares' 
            ? `Are you sure you want to delete this spare? This action cannot be undone.`
            : activeSubTab === 'locations'
            ? `Are you sure you want to delete this location? This action cannot be undone.`
            : `Are you sure you want to delete this mapping? This action cannot be undone.`
        }
        itemName={
          activeSubTab === 'spares' ? 'spare' :
          activeSubTab === 'locations' ? 'location' :
          'mapping'
        }
      />

      {/* TODO: Add form modals for create/edit */}
    </div>
  );
}
