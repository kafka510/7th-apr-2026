import { useState } from 'react';
import { updateUser } from '../api';
import type { UserProfile, UpdateUserPayload } from '../types';

interface RoleAndFeatureManagementProps {
  users: UserProfile[];
  onUsersChange: () => void;
}

export function RoleAndFeatureManagement({ users, onUsersChange }: RoleAndFeatureManagementProps) {
  const [editingUser, setEditingUser] = useState<UserProfile | null>(null);
  const [selectedRole, setSelectedRole] = useState<string>('');
  const [selectedFeatures, setSelectedFeatures] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  const roleOptions = ['admin', 'om', 'customer', 'management', 'others'];
  const featureOptions = [
    { value: 'web_access', label: 'Web Access' },
    { value: 'api_access', label: 'API Access' },
    { value: 'ticketing_access', label: 'Ticketing Access' },
  ];

  const handleEditClick = (user: UserProfile) => {
    setEditingUser(user);
    setSelectedRole(user.role);
    
    // Parse app_access to determine selected features
    const appAccess = user.app_access || '';
    const features: string[] = [];
    if (appAccess.includes('web')) features.push('web_access');
    if (appAccess.includes('api')) features.push('api_access');
    if (user.ticketing_access) features.push('ticketing_access');
    setSelectedFeatures(features);
  };

  const handleSave = async () => {
    if (!editingUser) return;

    setLoading(true);
    try {
      const payload: UpdateUserPayload = {
        role: selectedRole,
        access_control: selectedFeatures,
      };

      await updateUser(editingUser.user.id, payload);
      onUsersChange();
      setEditingUser(null);
      alert('User role and features updated successfully');
    } catch (error) {
      console.error('Error updating user:', error);
      alert('Failed to update user role and features');
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    setEditingUser(null);
    setSelectedRole('');
    setSelectedFeatures([]);
  };

  return (
    <div className="row mt-4">
      <div className="col-12">
        <div className="card dark:border-slate-700 dark:bg-slate-800">
          <div className="bg-info card-header text-white dark:bg-sky-700 dark:text-slate-100">
            <h4 className="text-white dark:text-slate-100">
              <i className="fas fa-user-cog"></i> Role & Feature Management
            </h4>
          </div>
          <div className="card-body dark:bg-slate-800">
            <div className="table-responsive rounded border border-slate-300 dark:border-slate-600" style={{ maxHeight: '600px', overflowY: 'auto' }}>
              <table className="table-bordered table-striped table-hover mb-0 table">
                <thead className="table-dark dark:bg-slate-800" style={{ position: 'sticky', top: 0, zIndex: 10 }}>
                  <tr>
                    <th className="border-slate-600 bg-slate-800 text-slate-100 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-200">Username</th>
                    <th className="border-slate-600 bg-slate-800 text-slate-100 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-200">Email</th>
                    <th className="border-slate-600 bg-slate-800 text-slate-100 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-200">Current Role</th>
                    <th className="border-slate-600 bg-slate-800 text-slate-100 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-200">Current Features</th>
                    <th className="border-slate-600 bg-slate-800 text-slate-100 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-200">Actions</th>
                  </tr>
                </thead>
                <tbody className="bg-white dark:bg-slate-900">
                  {users.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="text-center text-slate-500 dark:text-slate-400">
                        No users found
                      </td>
                    </tr>
                  ) : (
                    users.map((user) => {
                      const appAccess = user.app_access || '';
                      const hasWeb = appAccess.includes('web');
                      const hasApi = appAccess.includes('api');
                      const hasTicketing = user.ticketing_access;

                      return (
                        <tr key={user.id} className="border-slate-300 text-slate-700 dark:border-slate-700 dark:text-slate-200">
                          <td className="border-slate-300 dark:border-slate-700">
                            <strong className="text-slate-900 dark:text-slate-100">{user.user.username}</strong>
                          </td>
                          <td className="border-slate-300 dark:border-slate-700">{user.user.email}</td>
                          <td className="border-slate-300 dark:border-slate-700">
                            <span className="badge bg-primary text-white dark:bg-sky-600 dark:text-sky-100">
                              {user.role}
                            </span>
                          </td>
                          <td className="border-slate-300 dark:border-slate-700">
                            <div className="d-flex flex-wrap gap-1">
                              {hasWeb && (
                                <span className="badge bg-success text-white dark:bg-green-600 dark:text-green-100">
                                  Web
                                </span>
                              )}
                              {hasApi && (
                                <span className="badge bg-info text-white dark:bg-cyan-600 dark:text-cyan-100">
                                  API
                                </span>
                              )}
                              {hasTicketing && (
                                <span className="badge bg-warning text-white dark:bg-yellow-600 dark:text-yellow-100">
                                  Ticketing
                                </span>
                              )}
                              {!hasWeb && !hasApi && !hasTicketing && (
                                <span className="text-slate-500 dark:text-slate-400">No features</span>
                              )}
                            </div>
                          </td>
                          <td className="border-slate-300 dark:border-slate-700">
                            <button
                              className="btn btn-sm btn-warning dark:border-yellow-600 dark:bg-yellow-600 dark:text-yellow-100"
                              onClick={() => handleEditClick(user)}
                            >
                              <i className="fas fa-edit"></i> Edit
                            </button>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      {/* Edit Modal */}
      {editingUser && (
        <div
          className="modal fade show"
          style={{ display: 'block', backgroundColor: 'rgba(0,0,0,0.5)' }}
          tabIndex={-1}
        >
          <div className="modal-dialog">
            <div className="modal-content">
              <div className="modal-header">
                <h5 className="modal-title">Edit Role & Features for {editingUser.user.username}</h5>
                <button type="button" className="btn-close" onClick={handleCancel} aria-label="Close"></button>
              </div>
              <div className="modal-body">
                <div className="mb-3">
                  <label htmlFor="edit_role" className="form-label">
                    Role <span className="text-danger">*</span>
                  </label>
                  <select
                    className="form-select"
                    id="edit_role"
                    value={selectedRole}
                    onChange={(e) => setSelectedRole(e.target.value)}
                    required
                  >
                    <option value="">Select Role</option>
                    {roleOptions.map((role) => (
                      <option key={role} value={role}>
                        {role.charAt(0).toUpperCase() + role.slice(1)}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="mb-3">
                  <label className="form-label">Features</label>
                  <div className="rounded border p-2">
                    {featureOptions.map((feature) => (
                      <div key={feature.value} className="form-check">
                        <input
                          className="form-check-input"
                          type="checkbox"
                          id={`feature-${feature.value}`}
                          checked={selectedFeatures.includes(feature.value)}
                          onChange={(e) => {
                            if (e.target.checked) {
                              setSelectedFeatures([...selectedFeatures, feature.value]);
                            } else {
                              setSelectedFeatures(selectedFeatures.filter((f) => f !== feature.value));
                            }
                          }}
                        />
                        <label className="form-check-label" htmlFor={`feature-${feature.value}`}>
                          {feature.label}
                        </label>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={handleCancel} disabled={loading}>
                  Cancel
                </button>
                <button type="button" className="btn btn-primary" onClick={handleSave} disabled={loading || !selectedRole}>
                  {loading ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

