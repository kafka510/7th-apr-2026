 
import { useState } from 'react';
import { createFlag, updateFlag, deleteFlag, exportFlagsCSV, importFlagsCSV, assignFlagsToUser } from '../api';
import type { WaffleFlag, CreateFlagPayload, UpdateFlagPayload } from '../types';

interface FeatureFlagManagementProps {
  flags: WaffleFlag[];
  onFlagsChange: () => void;
  users: Array<{ user: { id: number; username: string; email: string } }>;
}

export function FeatureFlagManagement({ flags: initialFlags, onFlagsChange, users }: FeatureFlagManagementProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingFlag, setEditingFlag] = useState<WaffleFlag | null>(null);
  const [showImportModal, setShowImportModal] = useState(false);
  const [showAssignFlagsModal, setShowAssignFlagsModal] = useState(false);

  const flags = initialFlags || [];

  const handleCreateFlag = async (payload: CreateFlagPayload) => {
    try {
      await createFlag(payload);
      onFlagsChange();
      setShowCreateModal(false);
      alert('Flag created successfully');
    } catch (error) {
      console.error('Error creating flag:', error);
      alert('Failed to create flag');
    }
  };

  const handleUpdateFlag = async (flagId: number, payload: UpdateFlagPayload) => {
    try {
      await updateFlag(flagId, payload);
      onFlagsChange();
      setEditingFlag(null);
      alert('Flag updated successfully');
    } catch (error) {
      console.error('Error updating flag:', error);
      alert('Failed to update flag');
    }
  };

  const handleDeleteFlag = async (flagId: number) => {
    if (!confirm('Are you sure you want to delete this flag?')) return;
    try {
      await deleteFlag(flagId);
      onFlagsChange();
      alert('Flag deleted successfully');
    } catch (error) {
      console.error('Error deleting flag:', error);
      alert('Failed to delete flag');
    }
  };

  const handleExportCSV = async () => {
    try {
      await exportFlagsCSV();
    } catch (error) {
      console.error('Error exporting flags:', error);
      alert('Failed to export flags');
    }
  };

  const handleImportCSV = async (file: File, updateExisting: boolean = true) => {
    try {
      await importFlagsCSV(file, updateExisting);
      onFlagsChange();
      setShowImportModal(false);
      alert('Flags imported successfully');
    } catch (error) {
      console.error('Error importing flags:', error);
      alert('Failed to import flags');
    }
  };

  const filteredFlags = (Array.isArray(flags) ? flags : []).filter((flag) => {
    if (searchQuery) {
      return flag.name.toLowerCase().includes(searchQuery.toLowerCase());
    }
    return true;
  });

  return (
    <div className="row mt-4">
      <div className="col-12">
        <div className="card dark:border-slate-700 dark:bg-slate-800">
          <div className="bg-info card-header text-white dark:bg-sky-700 dark:text-slate-100">
            <div className="d-flex justify-content-between align-items-center">
              <h4 className="text-white dark:text-slate-100">
                <i className="fas fa-flag"></i> Feature Flag Management (Super User Only)
              </h4>
              <div>
                <button className="btn btn-light btn-sm me-2" onClick={handleExportCSV}>
                  <i className="fas fa-download"></i> Export CSV
                </button>
                <button
                  className="btn btn-light btn-sm me-2"
                  onClick={() => setShowImportModal(true)}
                >
                  <i className="fas fa-upload"></i> Import CSV
                </button>
                <button className="btn btn-light btn-sm me-2" onClick={() => setShowCreateModal(true)}>
                  <i className="fas fa-plus"></i> Create Flag
                </button>
                <button className="btn btn-light btn-sm" onClick={() => setShowAssignFlagsModal(true)}>
                  <i className="fas fa-user-check"></i> Assign Flags to User
                </button>
              </div>
            </div>
          </div>
          <div className="card-body dark:bg-slate-800">
            <div className="mb-3">
              <input
                type="text"
                className="form-control dark:border-slate-600 dark:bg-slate-700 dark:text-slate-100"
                placeholder="Search flags..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>

            <div className="table-responsive rounded border border-slate-300 dark:border-slate-600" style={{ maxHeight: '600px', overflowY: 'auto' }}>
                <table className="table-bordered table-striped table-hover mb-0 table">
                  <thead className="table-dark dark:bg-slate-800" style={{ position: 'sticky', top: 0, zIndex: 10 }}>
                    <tr>
                      <th className="border-slate-600 bg-slate-800 text-slate-100 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-200">Name</th>
                      <th className="border-slate-600 bg-slate-800 text-slate-100 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-200">Everyone</th>
                      <th className="border-slate-600 bg-slate-800 text-slate-100 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-200">Percent</th>
                      <th className="border-slate-600 bg-slate-800 text-slate-100 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-200">Superusers</th>
                      <th className="border-slate-600 bg-slate-800 text-slate-100 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-200">Staff</th>
                      <th className="border-slate-600 bg-slate-800 text-slate-100 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-200">Authenticated</th>
                      <th className="border-slate-600 bg-slate-800 text-slate-100 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-200">Testing</th>
                      <th className="border-slate-600 bg-slate-800 text-slate-100 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-200">Rollout</th>
                      <th className="border-slate-600 bg-slate-800 text-slate-100 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-200">Users</th>
                      <th className="border-slate-600 bg-slate-800 text-slate-100 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-200">Note</th>
                      <th className="border-slate-600 bg-slate-800 text-slate-100 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-200">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white dark:bg-slate-900">
                    {filteredFlags.length === 0 ? (
                      <tr>
                        <td colSpan={11} className="text-center text-slate-500 dark:text-slate-400">
                          No flags found
                        </td>
                      </tr>
                    ) : (
                      filteredFlags.map((flag) => (
                        <tr key={flag.id} className="border-slate-300 text-slate-700 dark:border-slate-700 dark:text-slate-200">
                          <td className="border-slate-300 dark:border-slate-700">
                            <strong className="text-slate-900 dark:text-slate-100">{flag.name}</strong>
                          </td>
                          <td className="border-slate-300 text-slate-700 dark:border-slate-700 dark:text-slate-200">
                            {flag.everyone === true ? 'Yes' : flag.everyone === false ? 'No' : 'Unknown'}
                          </td>
                          <td className="border-slate-300 text-slate-700 dark:border-slate-700 dark:text-slate-200">{flag.percent !== null ? `${flag.percent}%` : 'N/A'}</td>
                          <td className="border-slate-300 text-slate-700 dark:border-slate-700 dark:text-slate-200">{flag.superusers ? 'Yes' : 'No'}</td>
                          <td className="border-slate-300 text-slate-700 dark:border-slate-700 dark:text-slate-200">{flag.staff ? 'Yes' : 'No'}</td>
                          <td className="border-slate-300 text-slate-700 dark:border-slate-700 dark:text-slate-200">{flag.authenticated ? 'Yes' : 'No'}</td>
                          <td className="border-slate-300 text-slate-700 dark:border-slate-700 dark:text-slate-200">{flag.testing ? 'Yes' : 'No'}</td>
                          <td className="border-slate-300 text-slate-700 dark:border-slate-700 dark:text-slate-200">{flag.rollout ? 'Yes' : 'No'}</td>
                          <td className="border-slate-300 dark:border-slate-700">
                            {flag.users && flag.users.length > 0 ? (
                              <div>
                                {flag.users.slice(0, 2).map((user) => (
                                  <span key={user.id} className="badge bg-info me-1 text-white dark:bg-sky-600 dark:text-sky-100">
                                    {user.username}
                                  </span>
                                ))}
                                {flag.users.length > 2 && (
                                  <span className="badge bg-secondary text-white dark:bg-slate-600 dark:text-slate-100">+{flag.users.length - 2}</span>
                                )}
                              </div>
                            ) : (
                              <span className="text-slate-500 dark:text-slate-400">-</span>
                            )}
                          </td>
                          <td className="border-slate-300 dark:border-slate-700">
                            <small className="text-slate-500 dark:text-slate-400">{flag.note || '-'}</small>
                          </td>
                          <td className="border-slate-300 dark:border-slate-700">
                            <div className="btn-group">
                              <button
                                className="btn btn-sm btn-warning dark:border-yellow-600 dark:bg-yellow-600 dark:text-yellow-100"
                                onClick={() => setEditingFlag(flag)}
                              >
                                <i className="fas fa-edit"></i>
                              </button>
                              <button
                                className="btn btn-sm btn-danger dark:border-red-600 dark:bg-red-600 dark:text-red-100"
                                onClick={() => handleDeleteFlag(flag.id)}
                              >
                                <i className="fas fa-trash"></i>
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
          </div>
        </div>
      </div>

      {/* Create/Edit Flag Modal - Simplified version */}
      {(showCreateModal || editingFlag) && (
        <FlagFormModal
          key={editingFlag?.id || 'new-flag'}
          flag={editingFlag}
          users={users}
          onClose={() => {
            setShowCreateModal(false);
            setEditingFlag(null);
          }}
          onSave={
            editingFlag
              ? (payload) => handleUpdateFlag(editingFlag.id, payload as UpdateFlagPayload)
              : (payload) => handleCreateFlag(payload as CreateFlagPayload)
          }
        />
      )}

      {/* Import CSV Modal */}
      {showImportModal && (
        <ImportCSVModal
          onClose={() => setShowImportModal(false)}
          onImport={handleImportCSV}
        />
      )}

      {/* Assign Flags to User Modal */}
      {showAssignFlagsModal && (
        <AssignFlagsToUserModal
          users={users}
          flags={flags}
          onClose={() => setShowAssignFlagsModal(false)}
          onSuccess={() => {
            onFlagsChange();
            setShowAssignFlagsModal(false);
          }}
        />
      )}

      {/* Assign Flags to User Modal */}
      {showAssignFlagsModal && (
        <AssignFlagsToUserModal
          users={users}
          flags={flags}
          onClose={() => setShowAssignFlagsModal(false)}
          onSuccess={() => {
            onFlagsChange();
            setShowAssignFlagsModal(false);
          }}
        />
      )}
    </div>
  );
}

interface AssignFlagsToUserModalProps {
  users: Array<{ user: { id: number; username: string; email: string } }>;
  flags: WaffleFlag[];
  onClose: () => void;
  onSuccess: () => void;
}

function AssignFlagsToUserModal({ users, flags, onClose, onSuccess }: AssignFlagsToUserModalProps) {
  const [selectedUserId, setSelectedUserId] = useState<number | null>(null);
  const [selectedFlagIds, setSelectedFlagIds] = useState<number[]>([]);
  const [loading, setLoading] = useState(false);

  const handleUserChange = (userId: number) => {
    setSelectedUserId(userId);
    // Pre-select flags that are already assigned to this user
    const userFlags = flags.filter((flag) => flag.users?.some((u) => u.id === userId));
    setSelectedFlagIds(userFlags.map((f) => f.id));
  };

  const handleSelectAllFlags = () => {
    if (selectedFlagIds.length === flags.length) {
      setSelectedFlagIds([]);
    } else {
      setSelectedFlagIds(flags.map((f) => f.id));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedUserId) {
      alert('Please select a user');
      return;
    }

    setLoading(true);
    try {
      await assignFlagsToUser(selectedUserId, selectedFlagIds);
      alert('Flags assigned successfully');
      onSuccess();
    } catch (error) {
      console.error('Error assigning flags:', error);
      alert('Failed to assign flags');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="modal fade show"
      style={{ display: 'block', backgroundColor: 'rgba(0,0,0,0.5)' }}
      tabIndex={-1}
    >
      <div className="modal-dialog modal-lg">
        <div className="modal-content">
          <div className="modal-header">
            <h5 className="modal-title">Assign Flags to User</h5>
            <button type="button" className="btn-close" onClick={onClose} aria-label="Close"></button>
          </div>
          <form onSubmit={handleSubmit}>
            <div className="modal-body">
              <div className="mb-3">
                <label htmlFor="assign_user" className="form-label">
                  Select User <span className="text-danger">*</span>
                </label>
                <select
                  className="form-select"
                  id="assign_user"
                  value={selectedUserId || ''}
                  onChange={(e) => handleUserChange(parseInt(e.target.value, 10))}
                  required
                >
                  <option value="">-- Select User --</option>
                  {users.map((userProfile) => (
                    <option key={userProfile.user.id} value={userProfile.user.id}>
                      {userProfile.user.username} ({userProfile.user.email})
                    </option>
                  ))}
                </select>
              </div>

              {selectedUserId && (
                <div className="mb-3">
                  <div className="d-flex justify-content-between align-items-center mb-2">
                    <label className="form-label mb-0">Select Flags to Assign</label>
                    <button
                      type="button"
                      className="btn btn-sm btn-outline-primary"
                      onClick={handleSelectAllFlags}
                    >
                      {selectedFlagIds.length === flags.length ? 'Deselect All' : 'Select All'}
                    </button>
                  </div>
                  <div
                    className="rounded border p-2"
                    style={{ maxHeight: '300px', overflowY: 'auto' }}
                  >
                    {flags.map((flag) => {
                      const isSelected = selectedFlagIds.includes(flag.id);
                      return (
                        <div key={flag.id} className="form-check">
                          <input
                            className="form-check-input"
                            type="checkbox"
                            id={`flag-${flag.id}`}
                            checked={isSelected}
                            onChange={(e) => {
                              if (e.target.checked) {
                                setSelectedFlagIds([...selectedFlagIds, flag.id]);
                              } else {
                                setSelectedFlagIds(selectedFlagIds.filter((id) => id !== flag.id));
                              }
                            }}
                          />
                          <label
                            className="form-check-label"
                            htmlFor={`flag-${flag.id}`}
                            style={{ cursor: 'pointer' }}
                          >
                            {flag.name}
                            {flag.note && <small className="text-muted ms-2">({flag.note})</small>}
                          </label>
                        </div>
                      );
                    })}
                  </div>
                  {selectedFlagIds.length > 0 && (
                    <div className="mt-2">
                      <small className="text-muted">
                        Selected: {selectedFlagIds.length} of {flags.length} flag(s)
                      </small>
                    </div>
                  )}
                </div>
              )}
            </div>
            <div className="modal-footer">
              <button type="button" className="btn btn-secondary" onClick={onClose} disabled={loading}>
                Cancel
              </button>
              <button type="submit" className="btn btn-primary" disabled={loading || !selectedUserId}>
                {loading ? 'Assigning...' : 'Assign Flags'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

interface FlagFormModalProps {
  flag: WaffleFlag | null;
  users: Array<{ user: { id: number; username: string; email: string } }>;
  onClose: () => void;
  onSave: (payload: CreateFlagPayload | UpdateFlagPayload) => void;
}

function FlagFormModal({ flag, users, onClose, onSave }: FlagFormModalProps) {
  const [formData, setFormData] = useState<CreateFlagPayload | UpdateFlagPayload>(() => {
    if (flag) {
      return {
        name: flag.name || '',
        everyone: flag.everyone ?? null, // null, true, or false
        percent: flag.percent !== null && flag.percent !== undefined ? flag.percent : undefined,
        superusers: flag.superusers ?? false,
        staff: flag.staff ?? false,
        authenticated: flag.authenticated ?? false,
        testing: flag.testing ?? false,
        rollout: flag.rollout ?? false,
        note: flag.note || '',
        users: flag.users?.map((u) => u.id) || [],
      };
    } else {
      return {
        name: '',
        everyone: null,
        percent: undefined,
        superusers: false,
        staff: false,
        authenticated: false,
        testing: false,
        rollout: false,
        note: '',
        users: [],
      };
    }
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(formData);
  };

  return (
    <div
      className="modal fade show"
      style={{ display: 'block', backgroundColor: 'rgba(0,0,0,0.5)' }}
      tabIndex={-1}
    >
      <div className="modal-dialog">
        <div className="modal-content">
          <div className="modal-header">
            <h5 className="modal-title">{flag ? 'Edit Flag' : 'Create Flag'}</h5>
            <button type="button" className="btn-close" onClick={onClose} aria-label="Close"></button>
          </div>
          <form onSubmit={handleSubmit}>
            <div className="modal-body">
              <div className="mb-3">
                <label htmlFor="flag_name" className="form-label">
                  Flag Name <span className="text-danger">*</span>
                </label>
                <input
                  type="text"
                  className="form-control"
                  id="flag_name"
                  value={formData.name || ''}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  required
                />
              </div>
              <div className="mb-3">
                <label htmlFor="everyone" className="form-label">
                  Everyone
                </label>
                <select
                  className="form-select"
                  id="everyone"
                  value={formData.everyone === true ? 'yes' : formData.everyone === false ? 'no' : 'unknown'}
                  onChange={(e) => {
                    const value = e.target.value;
                    setFormData({
                      ...formData,
                      everyone: value === 'yes' ? true : value === 'no' ? false : null,
                    });
                  }}
                >
                  <option value="unknown">Unknown</option>
                  <option value="yes">Yes</option>
                  <option value="no">No</option>
                </select>
              </div>
              <div className="row mb-3">
                <div className="col-md-6">
                  <div className="form-check">
                    <input
                      className="form-check-input"
                      type="checkbox"
                      id="superusers"
                      checked={formData.superusers || false}
                      onChange={(e) => setFormData({ ...formData, superusers: e.target.checked })}
                    />
                    <label className="form-check-label" htmlFor="superusers">
                      Superusers
                    </label>
                  </div>
                  <div className="form-check">
                    <input
                      className="form-check-input"
                      type="checkbox"
                      id="staff"
                      checked={formData.staff || false}
                      onChange={(e) => setFormData({ ...formData, staff: e.target.checked })}
                    />
                    <label className="form-check-label" htmlFor="staff">
                      Staff
                    </label>
                  </div>
                </div>
                <div className="col-md-6">
                  <div className="form-check">
                    <input
                      className="form-check-input"
                      type="checkbox"
                      id="authenticated"
                      checked={formData.authenticated || false}
                      onChange={(e) => setFormData({ ...formData, authenticated: e.target.checked })}
                    />
                    <label className="form-check-label" htmlFor="authenticated">
                      Authenticated
                    </label>
                  </div>
                  <div className="form-check">
                    <input
                      className="form-check-input"
                      type="checkbox"
                      id="testing"
                      checked={formData.testing || false}
                      onChange={(e) => setFormData({ ...formData, testing: e.target.checked })}
                    />
                    <label className="form-check-label" htmlFor="testing">
                      Testing
                    </label>
                  </div>
                  <div className="form-check">
                    <input
                      className="form-check-input"
                      type="checkbox"
                      id="rollout"
                      checked={formData.rollout || false}
                      onChange={(e) => setFormData({ ...formData, rollout: e.target.checked })}
                    />
                    <label className="form-check-label" htmlFor="rollout">
                      Rollout
                    </label>
                  </div>
                </div>
              </div>
              <div className="mb-3">
                <label htmlFor="percent" className="form-label">
                  Percent (0-100)
                </label>
                <input
                  type="number"
                  className="form-control"
                  id="percent"
                  min="0"
                  max="100"
                  value={formData.percent || ''}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      percent: e.target.value ? parseInt(e.target.value, 10) : undefined,
                    })
                  }
                />
              </div>
              <div className="mb-3">
                <div className="d-flex justify-content-between align-items-center mb-2">
                  <label htmlFor="users" className="form-label mb-0">
                    Assign to Users
                  </label>
                  <button
                    type="button"
                    className="btn btn-sm btn-outline-primary"
                    onClick={() => {
                      const allUserIds = users.map((u) => u.user.id);
                      const currentSelected = formData.users || [];
                      const allSelected = currentSelected.length === allUserIds.length;
                      setFormData({
                        ...formData,
                        users: allSelected ? [] : allUserIds,
                      });
                    }}
                  >
                    {(formData.users || []).length === users.length ? 'Deselect All' : 'Select All'}
                  </button>
                </div>
                <div
                  className="rounded border p-2"
                  style={{ maxHeight: '200px', overflowY: 'auto' }}
                >
                  {users.map((userProfile) => {
                    const isSelected = (formData.users || []).includes(userProfile.user.id);
                    return (
                      <div key={userProfile.user.id} className="form-check">
                        <input
                          className="form-check-input"
                          type="checkbox"
                          id={`user-${userProfile.user.id}`}
                          checked={isSelected}
                          onChange={(e) => {
                            const currentSelected = formData.users || [];
                            if (e.target.checked) {
                              setFormData({
                                ...formData,
                                users: [...currentSelected, userProfile.user.id],
                              });
                            } else {
                              setFormData({
                                ...formData,
                                users: currentSelected.filter((id) => id !== userProfile.user.id),
                              });
                            }
                          }}
                        />
                        <label
                          className="form-check-label"
                          htmlFor={`user-${userProfile.user.id}`}
                          style={{ cursor: 'pointer' }}
                        >
                          {userProfile.user.username} ({userProfile.user.email})
                        </label>
                      </div>
                    );
                  })}
                </div>
                {(formData.users || []).length > 0 && (
                  <div className="mt-2">
                    <small className="text-muted">
                      Selected: {(formData.users || []).length} of {users.length} user(s)
                    </small>
                  </div>
                )}
              </div>
              <div className="mb-3">
                <label htmlFor="note" className="form-label">
                  Note
                </label>
                <textarea
                  className="form-control"
                  id="note"
                  rows={3}
                  value={formData.note || ''}
                  onChange={(e) => setFormData({ ...formData, note: e.target.value })}
                />
              </div>
            </div>
            <div className="modal-footer">
              <button type="button" className="btn btn-secondary" onClick={onClose}>
                Cancel
              </button>
              <button type="submit" className="btn btn-primary">
                {flag ? 'Update' : 'Create'} Flag
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

interface ImportCSVModalProps {
  onClose: () => void;
  onImport: (file: File, updateExisting?: boolean) => void;
}

function ImportCSVModal({ onClose, onImport }: ImportCSVModalProps) {
  const [file, setFile] = useState<File | null>(null);
  const [updateExisting, setUpdateExisting] = useState(true);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (file) {
      onImport(file, updateExisting);
    }
  };

  return (
    <div
      className="modal fade show"
      style={{ display: 'block', backgroundColor: 'rgba(0,0,0,0.5)' }}
      tabIndex={-1}
    >
      <div className="modal-dialog">
        <div className="modal-content">
          <div className="modal-header">
            <h5 className="modal-title">Import Flags from CSV</h5>
            <button type="button" className="btn-close" onClick={onClose} aria-label="Close"></button>
          </div>
          <form onSubmit={handleSubmit}>
            <div className="modal-body">
              <div className="mb-3">
                <label htmlFor="csv_file" className="form-label">
                  Select CSV File
                </label>
                <input
                  type="file"
                  className="form-control"
                  id="csv_file"
                  accept=".csv"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                  required
                />
              </div>
              <div className="mb-3">
                <div className="form-check">
                  <input
                    className="form-check-input"
                    type="checkbox"
                    id="update_existing"
                    checked={updateExisting}
                    onChange={(e) => setUpdateExisting(e.target.checked)}
                  />
                  <label className="form-check-label" htmlFor="update_existing">
                    Update existing flags (if unchecked, existing flags will be skipped)
                  </label>
                </div>
              </div>
            </div>
            <div className="modal-footer">
              <button type="button" className="btn btn-secondary" onClick={onClose}>
                Cancel
              </button>
              <button type="submit" className="btn btn-primary" disabled={!file}>
                Import
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

