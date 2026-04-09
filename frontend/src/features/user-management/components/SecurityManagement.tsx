 
import { useState, useEffect, useCallback } from 'react';
import { fetchBlockedIPs, fetchBlockedUsers, blockIP, unblockIP, blockUser, unblockUser } from '../api';
import type { BlockedIP, BlockedUser } from '../types';

interface SecurityManagementProps {
  users: Array<{ user: { id: number; username: string; email: string } }>;
}

export function SecurityManagement({ users }: SecurityManagementProps) {
  const [blockedIPs, setBlockedIPs] = useState<BlockedIP[]>([]);
  const [blockedIPsTotalCount, setBlockedIPsTotalCount] = useState<number>(0);
  const [blockedUsers, setBlockedUsers] = useState<BlockedUser[]>([]);
  const [ipStatusFilter, setIpStatusFilter] = useState<string>('active');
  const [userStatusFilter, setUserStatusFilter] = useState<string>('active');
  const [ipSearch, setIpSearch] = useState<string>('');
  const [userSearch, setUserSearch] = useState<string>('');
  const [loadingIPs, setLoadingIPs] = useState(false);
  const [loadingUsers, setLoadingUsers] = useState(false);
  const [newIP, setNewIP] = useState<string>('');
  const [newIPReason, setNewIPReason] = useState<string>('');
  const [newUser, setNewUser] = useState<string>('');
  const [newUserReason, setNewUserReason] = useState<string>('');

  const loadBlockedIPs = useCallback(async () => {
    try {
      setLoadingIPs(true);
      const result = await fetchBlockedIPs({
        status: ipStatusFilter === 'all' ? undefined : ipStatusFilter,
        search: ipSearch || undefined,
        per_page: 'all', // Get all IPs to get accurate total count
      });
      setBlockedIPs(result.data);
      setBlockedIPsTotalCount(result.totalCount);
    } catch (error) {
      console.error('Error loading blocked IPs:', error);
      setBlockedIPs([]);
      setBlockedIPsTotalCount(0);
    } finally {
      setLoadingIPs(false);
    }
  }, [ipStatusFilter, ipSearch]);

  const loadBlockedUsers = useCallback(async () => {
    try {
      setLoadingUsers(true);
      const data = await fetchBlockedUsers({
        status: userStatusFilter === 'all' ? undefined : userStatusFilter,
        search: userSearch || undefined,
      });
      setBlockedUsers(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error('Error loading blocked users:', error);
      setBlockedUsers([]);
    } finally {
      setLoadingUsers(false);
    }
  }, [userStatusFilter, userSearch]);

  useEffect(() => {
    loadBlockedIPs();
  }, [loadBlockedIPs]);

  useEffect(() => {
    loadBlockedUsers();
  }, [loadBlockedUsers]);

  const validateIPAddress = (ip: string): boolean => {
    // Basic IPv4 validation
    const ipv4Regex = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;
    // Basic IPv6 validation (simplified)
    const ipv6Regex = /^(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$|^::1$|^::$/;
    
    return ipv4Regex.test(ip) || ipv6Regex.test(ip);
  };

  const handleBlockIP = async () => {
    if (!newIP || !newIPReason) {
      alert('Please enter IP address and reason');
      return;
    }
    
    // Validate IP address format
    const trimmedIP = newIP.trim();
    if (!validateIPAddress(trimmedIP)) {
      alert('Please enter a valid IP address (e.g., 192.168.1.1)');
      return;
    }
    
    try {
      const result = await blockIP(trimmedIP, newIPReason);
      if (result.success) {
        setNewIP('');
        setNewIPReason('');
        // Reload the list after a short delay to ensure the backend has processed it
        setTimeout(() => {
          loadBlockedIPs();
        }, 500);
        alert(result.message || 'IP blocked successfully');
      } else {
        alert(result.message || 'Failed to block IP');
      }
    } catch (error) {
      console.error('Error blocking IP:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to block IP';
      alert(errorMessage);
    }
  };

  const handleUnblockIP = async (ipAddress: string) => {
    if (!confirm(`Are you sure you want to unblock ${ipAddress}?`)) return;
    try {
      await unblockIP(ipAddress);
      loadBlockedIPs();
      alert('IP unblocked successfully');
    } catch (error) {
      console.error('Error unblocking IP:', error);
      alert('Failed to unblock IP');
    }
  };

  const handleBlockUser = async () => {
    if (!newUser || !newUserReason) {
      alert('Please select user and enter reason');
      return;
    }
    try {
      await blockUser(newUser, newUserReason);
      setNewUser('');
      setNewUserReason('');
      loadBlockedUsers();
      alert('User blocked successfully');
    } catch (error) {
      console.error('Error blocking user:', error);
      alert('Failed to block user');
    }
  };

  const handleUnblockUser = async (username: string) => {
    if (!confirm(`Are you sure you want to unblock ${username}?`)) return;
    try {
      await unblockUser(username);
      loadBlockedUsers();
      alert('User unblocked successfully');
    } catch (error) {
      console.error('Error unblocking user:', error);
      alert('Failed to unblock user');
    }
  };

  const filteredIPs = (Array.isArray(blockedIPs) ? blockedIPs : []).filter((ip) => {
    if (ipSearch) {
      return ip.ip_address.toLowerCase().includes(ipSearch.toLowerCase());
    }
    return true;
  });

  const filteredUsers = (Array.isArray(blockedUsers) ? blockedUsers : []).filter((blocked) => {
    if (userSearch) {
      const searchLower = userSearch.toLowerCase();
      return (
        blocked.user.username.toLowerCase().includes(searchLower) ||
        blocked.user.email.toLowerCase().includes(searchLower)
      );
    }
    return true;
  });

  return (
    <div className="row mt-4">
      <div className="col-12">
        <div className="card">
          <div className="bg-danger card-header text-white">
            <h4>
              <i className="fas fa-shield-alt"></i> Security Management (Super User Only)
            </h4>
          </div>
          <div className="card-body">
            <div className="row">
              {/* Blocked IPs Management */}
              <div className="col-md-6">
                <h5>
                  <i className="fas fa-ban text-danger"></i> Blocked IP Addresses
                </h5>
                <div className="card mb-3">
                  <div className="card-body p-2">
                    <div className="row g-2">
                      <div className="col-md-6">
                        <select
                          className="form-select-sm form-select"
                          value={ipStatusFilter}
                          onChange={(e) => setIpStatusFilter(e.target.value)}
                        >
                          <option value="active">Active Blocks</option>
                          <option value="inactive">Inactive</option>
                          <option value="all">All</option>
                        </select>
                      </div>
                      <div className="col-md-6">
                        <input
                          type="text"
                          className="form-control-sm form-control"
                          placeholder="Search IP..."
                          value={ipSearch}
                          onChange={(e) => setIpSearch(e.target.value)}
                        />
                      </div>
                    </div>
                  </div>
                </div>

                <div className="d-flex justify-content-between align-items-center mb-2">
                  <span className="badge bg-danger">
                    {ipSearch || ipStatusFilter !== 'active' 
                      ? `${filteredIPs.length} of ${blockedIPsTotalCount}` 
                      : blockedIPsTotalCount} Blocked IP{blockedIPsTotalCount !== 1 ? 's' : ''}
                    {ipSearch || ipStatusFilter !== 'active' ? ' (filtered)' : ''}
                  </span>
                  <button className="btn btn-sm btn-outline-primary" onClick={loadBlockedIPs}>
                    <i className="fas fa-sync-alt"></i> Refresh
                  </button>
                </div>
                <div className="list-group mb-3" style={{ maxHeight: '300px', overflowY: 'auto' }}>
                  {loadingIPs ? (
                    <div className="p-3 text-center">
                      <div className="spinner-border-sm spinner-border" role="status">
                        <span className="visually-hidden">Loading...</span>
                      </div>
                    </div>
                  ) : filteredIPs.length === 0 ? (
                    <div className="text-muted p-3 text-center">No blocked IPs found</div>
                  ) : (
                    filteredIPs.map((ip) => (
                      <div key={ip.id} className="list-group-item">
                        <div className="d-flex justify-content-between align-items-center">
                          <div>
                            <strong>{ip.ip_address}</strong>
                            <br />
                            <small className="text-muted">
                              Status: <span className={`badge bg-${ip.status === 'active' ? 'danger' : 'secondary'}`}>{ip.status}</span>
                              {' | '}
                              Reason: {ip.reason}
                            </small>
                            {ip.description && (
                              <>
                                <br />
                                <small className="text-muted">{ip.description}</small>
                              </>
                            )}
                          </div>
                          {ip.status === 'active' && (
                            <button
                              className="btn btn-sm btn-outline-success"
                              onClick={() => handleUnblockIP(ip.ip_address)}
                            >
                              <i className="fas fa-unlock"></i> Unblock
                            </button>
                          )}
                        </div>
                      </div>
                    ))
                  )}
                </div>
                <div className="mt-3">
                  <div className="input-group mb-2">
                    <input
                      type="text"
                      className="form-control"
                      placeholder="Enter IP address to block"
                      value={newIP}
                      onChange={(e) => setNewIP(e.target.value)}
                    />
                    <button className="btn btn-danger" onClick={handleBlockIP}>
                      <i className="fas fa-ban"></i> Block IP
                    </button>
                  </div>
                  <input
                    type="text"
                    className="form-control"
                    placeholder="Reason for blocking"
                    value={newIPReason}
                    onChange={(e) => setNewIPReason(e.target.value)}
                  />
                </div>
              </div>

              {/* Blocked Users Management */}
              <div className="col-md-6">
                <h5>
                  <i className="fas fa-user-slash text-warning"></i> Blocked Users
                </h5>
                <div className="card mb-3">
                  <div className="card-body p-2">
                    <div className="row g-2">
                      <div className="col-md-6">
                        <select
                          className="form-select-sm form-select"
                          value={userStatusFilter}
                          onChange={(e) => setUserStatusFilter(e.target.value)}
                        >
                          <option value="active">Active Blocks</option>
                          <option value="inactive">Inactive</option>
                          <option value="all">All</option>
                        </select>
                      </div>
                      <div className="col-md-6">
                        <input
                          type="text"
                          className="form-control-sm form-control"
                          placeholder="Search user..."
                          value={userSearch}
                          onChange={(e) => setUserSearch(e.target.value)}
                        />
                      </div>
                    </div>
                  </div>
                </div>

                <div className="d-flex justify-content-between align-items-center mb-2">
                  <span className="badge bg-warning text-dark">
                    {filteredUsers.length} Blocked User{filteredUsers.length !== 1 ? 's' : ''}
                  </span>
                  <button className="btn btn-sm btn-outline-primary" onClick={loadBlockedUsers}>
                    <i className="fas fa-sync-alt"></i> Refresh
                  </button>
                </div>
                <div className="list-group mb-3" style={{ maxHeight: '300px', overflowY: 'auto' }}>
                  {loadingUsers ? (
                    <div className="p-3 text-center">
                      <div className="spinner-border-sm spinner-border" role="status">
                        <span className="visually-hidden">Loading...</span>
                      </div>
                    </div>
                  ) : filteredUsers.length === 0 ? (
                    <div className="text-muted p-3 text-center">No blocked users found</div>
                  ) : (
                    filteredUsers.map((blocked) => (
                      <div key={blocked.id} className="list-group-item">
                        <div className="d-flex justify-content-between align-items-center">
                          <div>
                            <strong>{blocked.user.username}</strong>
                            <br />
                            <small className="text-muted">
                              {blocked.user.email}
                              {' | '}
                              Status: <span className={`badge bg-${blocked.status === 'active' ? 'warning' : 'secondary'}`}>{blocked.status}</span>
                              {' | '}
                              Reason: {blocked.reason}
                            </small>
                            {blocked.description && (
                              <>
                                <br />
                                <small className="text-muted">{blocked.description}</small>
                              </>
                            )}
                          </div>
                          {blocked.status === 'active' && (
                            <button
                              className="btn btn-sm btn-outline-success"
                              onClick={() => handleUnblockUser(blocked.user.username)}
                            >
                              <i className="fas fa-unlock"></i> Unblock
                            </button>
                          )}
                        </div>
                      </div>
                    ))
                  )}
                </div>
                <div className="mt-3">
                  <div className="input-group mb-2">
                    <select
                      className="form-select"
                      value={newUser}
                      onChange={(e) => setNewUser(e.target.value)}
                    >
                      <option value="">Select user to block</option>
                      {users.map((profile) => (
                        <option key={profile.user.id} value={profile.user.username}>
                          {profile.user.username} ({profile.user.email})
                        </option>
                      ))}
                    </select>
                    <button className="btn btn-warning" onClick={handleBlockUser}>
                      <i className="fas fa-user-slash"></i> Block User
                    </button>
                  </div>
                  <input
                    type="text"
                    className="form-control"
                    placeholder="Reason for blocking"
                    value={newUserReason}
                    onChange={(e) => setNewUserReason(e.target.value)}
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

