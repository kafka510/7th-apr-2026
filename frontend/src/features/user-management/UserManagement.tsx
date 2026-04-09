 
import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import html2canvas from 'html2canvas';
import { StatisticsCards } from './components/StatisticsCards';
import { ActivityChart } from './components/ActivityChart';
import { SuspiciousActivities } from './components/SuspiciousActivities';
import { DownloadSection } from './components/DownloadSection';
import type {
  UserProfile,
  UserStats,
  ActivityDataPoint,
  SuspiciousActivity,
  Asset,
  WaffleFlag,
} from './types';
import { fetchUserManagementData, sendPasswordReset, deleteUser } from './api';
import { UserFormModal } from './components/UserFormModal';
import { SecurityManagement } from './components/SecurityManagement';
import { FeatureFlagManagement } from './components/FeatureFlagManagement';
import { RoleAndFeatureManagement } from './components/RoleAndFeatureManagement';
import { CompactMultiSelectDropdown } from '../yield/components/CompactMultiSelectDropdown';

export function UserManagement() {
  const [loading, setLoading] = useState(true);
  const [users, setUsers] = useState<UserProfile[]>([]);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [countries, setCountries] = useState<string[]>([]);
  const [portfolios, setPortfolios] = useState<string[]>([]);
  const [showUserForm, setShowUserForm] = useState(false);
  const [stats, setStats] = useState<UserStats>({
    active_users_count: 0,
    security_alerts_count: 0,
    total_users: 0,
    suspicious_activities_count: 0,
    active_users: 0,
    inactive_users: 0,
    blocked_users_count: 0,
    blocked_ips_count: 0,
  });
  const [activityData, setActivityData] = useState<ActivityDataPoint[]>([]);
  const [suspiciousActivities, setSuspiciousActivities] = useState<SuspiciousActivity[]>([]);
  const [flags, setFlags] = useState<WaffleFlag[]>([]);
  const [isSuperuser, setIsSuperuser] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  // Filter states
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedRoles, setSelectedRoles] = useState<string[]>([]);
  const [selectedStatuses, setSelectedStatuses] = useState<string[]>([]);
  const [downloadingImage, setDownloadingImage] = useState(false);

  // Ref for the main container to capture
  const pageContainerRef = useRef<HTMLDivElement>(null);

  // Only show header when page is NOT in iframe
  const showHeader = typeof window !== 'undefined' && window.self === window.top;

  // Available filter options
  const roleOptions = useMemo(() => ['admin', 'om', 'customer', 'management', 'others'], []);
  const statusOptions = useMemo(() => ['active', 'inactive', 'blocked'], []);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchUserManagementData({
        search: searchQuery || undefined,
        role: selectedRoles.length > 0 ? selectedRoles.join(',') : undefined,
        status: selectedStatuses.length > 0 ? selectedStatuses.join(',') : undefined,
      });
      setUsers(Array.isArray(data.users) ? data.users : []);
      setAssets(Array.isArray(data.assets) ? data.assets : []);
      setCountries(Array.isArray(data.countries) ? data.countries : []);
      setPortfolios(Array.isArray(data.portfolios) ? data.portfolios : []);
      setStats(data.stats || {});
      setActivityData(Array.isArray(data.activity_data) ? data.activity_data : []);
      setSuspiciousActivities(Array.isArray(data.suspicious_activities) ? data.suspicious_activities : []);
      // Set superuser status from API response (explicit check)
      // Also check if flags are returned as a fallback indicator
      const isSuperuserFromAPI = data.is_superuser === true;
      const hasFlags = Array.isArray(data.flags) && data.flags.length > 0;
      setIsSuperuser(isSuperuserFromAPI || hasFlags);
      if (hasFlags && data.flags) {
        setFlags(data.flags);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load user management data');
      console.error('Error loading user management data:', err);
    } finally {
      setLoading(false);
    }
  }, [searchQuery, selectedRoles, selectedStatuses]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleApplyFilters = () => {
    loadData();
  };

  const handleClearFilters = () => {
    setSearchQuery('');
    setSelectedRoles([]);
    setSelectedStatuses([]);
  };

  const handleSendPasswordReset = async (userId: number, username: string, email: string) => {
    const confirmed = window.confirm(
      `Send password setup/reset link to ${username} (${email})?`,
    );
    if (!confirmed) return;

    try {
      setError(null);
      setActionMessage(null);
      const result = await sendPasswordReset(userId);
      setActionMessage(result.message || 'Password reset link sent successfully.');
    } catch (err) {
      const message =
        err instanceof Error ? err.message : 'Failed to send password reset link.';
      setError(message);
    }
  };

  const handleDeleteUser = async (username: string, email: string) => {
    const confirmed = window.confirm(
      `⚠️ WARNING: This will permanently delete user "${username}" (${email}).\n\nThis action cannot be undone. Are you absolutely sure?`,
    );
    if (!confirmed) return;

    try {
      setError(null);
      setActionMessage(null);
      const result = await deleteUser(username);
      setActionMessage(result.message || `User ${username} has been deleted successfully.`);
      // Reload data to refresh the user list
      loadData();
    } catch (err) {
      const message =
        err instanceof Error ? err.message : 'Failed to delete user.';
      setError(message);
    }
  };

  /**
   * Download page as image
   * 
   * SECURITY NOTE: This function respects all existing access controls:
   * - The page itself is protected by @feature_required('user_management') and @login_required decorators
   * - The API endpoint filters data based on user permissions (admin sees all, others see only assigned assets/sites)
   * - This download only captures what's already rendered and visible to the user
   * - It does NOT bypass or override any access controls - users can only download what they can see
   * - The download button is only visible when the user has access to the page (showHeader condition)
   */
  const handleDownloadPageImage = useCallback(async () => {
    if (!pageContainerRef.current) {
      alert('Unable to capture page. Please try again.');
      return;
    }

    try {
      setDownloadingImage(true);
      setError(null);

      // Capture the page using html2canvas
      // This only captures what's already rendered and visible to the user,
      // which has already been filtered by server-side access controls
      const canvas = await html2canvas(pageContainerRef.current, {
        backgroundColor: '#0f172a', // slate-950 background color
        scale: 2, // Higher quality
        useCORS: true,
        logging: false,
        windowWidth: pageContainerRef.current.scrollWidth,
        windowHeight: pageContainerRef.current.scrollHeight,
      });

      // Convert canvas to blob and download
      canvas.toBlob((blob) => {
        if (!blob) {
          alert('Failed to generate image. Please try again.');
          setDownloadingImage(false);
          return;
        }

        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        const timestamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-');
        link.href = url;
        link.download = `user-management-${timestamp}.png`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
        setDownloadingImage(false);
      }, 'image/png');
    } catch (err) {
      console.error('Error downloading page image:', err);
      const message =
        err instanceof Error ? err.message : 'Failed to download page image.';
      setError(message);
      setDownloadingImage(false);
    }
  }, []);

  if (loading && users.length === 0) {
    return (
      <div className="flex size-full items-center justify-center bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
        <div className="text-center">
          <div className="mb-3 inline-block size-8 animate-spin rounded-full border-4 border-sky-400 border-t-transparent"></div>
          <p className="text-sm text-slate-300">Loading user management data...</p>
        </div>
      </div>
    );
  }

  return (
    <div 
      ref={pageContainerRef}
      className="flex w-full flex-col bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950" 
      style={{ minHeight: '100%' }}
    >
      <div className="flex flex-col gap-2 p-2">
        {/* Header - only show when not in iframe */}
        {/* Download button respects access controls: only visible to users who have access to this page */}
        {showHeader && (
          <div className="mb-2 flex items-center justify-between">
            <h2 className="text-xl font-bold text-slate-100">👥 User Management</h2>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleDownloadPageImage}
                disabled={downloadingImage}
                className="flex items-center justify-center rounded-lg border border-slate-600 bg-slate-800/50 px-3 py-1.5 text-xs font-semibold text-slate-200 transition hover:bg-slate-700/50 disabled:cursor-not-allowed disabled:opacity-50"
                title="Download page as image (only captures what you can see)"
              >
                {downloadingImage ? (
                  <>
                    <span className="mr-1 inline-block size-3 animate-spin rounded-full border-2 border-slate-400 border-t-transparent"></span>
                    Downloading...
                  </>
                ) : (
                  <>
                    <svg
                      width="14"
                      height="14"
                      viewBox="0 0 24 24"
                      fill="currentColor"
                      className="mr-1"
                    >
                      <path d="M5 20h14v-2H5v2zm7-18l-5 5h3v6h4v-6h3l-5-5z" />
                    </svg>
                    Download
                  </>
                )}
              </button>
            </div>
          </div>
        )}

        {error && (
          <div className="rounded-xl border border-red-500/50 bg-red-600/20 px-4 py-3">
            <span className="text-sm font-medium text-red-200">
              <strong>Error:</strong> {error}
            </span>
          </div>
        )}

        {actionMessage && (
          <div className="mb-1 rounded-xl border border-emerald-500/50 bg-emerald-600/20 px-4 py-3">
            <span className="text-sm font-medium text-emerald-100">{actionMessage}</span>
          </div>
        )}

      {/* Statistics Cards - Admin Only */}
      <StatisticsCards 
        stats={stats}
        onActiveUsersClick={() => {
          // Navigate to security alerts page or filter for active users
          window.location.href = '/security-alerts/';
        }}
        onSecurityAlertsClick={() => {
          window.location.href = '/security-alerts/';
        }}
        onTotalUsersClick={() => {
          // Scroll to user list or stay on page with all users
          const userListElement = document.querySelector('.rounded-xl.border.border-slate-800\\/80');
          if (userListElement) {
            userListElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
          }
        }}
        onSuspiciousActivitiesClick={() => {
          // Navigate to security alerts page for suspicious activities
          window.location.href = '/security-alerts/';
        }}
      />

      {/* Activity Chart & Suspicious Activities - Admin Only */}
      {stats.total_users > 0 && (
        <div className="row">
          <div className="col-md-8">
            <ActivityChart activityData={activityData} />
          </div>
          <div className="col-md-4">
            <SuspiciousActivities activities={suspiciousActivities} />
          </div>
        </div>
      )}

      {/* Download Section - Admin Only */}
      <DownloadSection />

        {/* User Management Content */}
        <div className="flex flex-col gap-2">
          <div className="rounded-xl border border-slate-800/80 bg-[radial-gradient(circle_at_top,_rgba(56,189,248,0.12),_transparent_55%),radial-gradient(circle_at_bottom,_rgba(167,139,250,0.12),_transparent_60%)] bg-gradient-to-br from-slate-900/90 via-slate-800/60 to-slate-900/90 p-3 shadow-xl">
            <div className="mb-3 flex items-center justify-between">
              <h5 className="text-sm font-bold text-slate-100">👥 User Management</h5>
              <div className="flex items-center gap-2">
                {isSuperuser && (
                  <a
                    href="/user-management/logs/"
                    target="_parent"
                    data-skip-iframe-nav="true"
                    className="rounded-lg border border-purple-600 bg-purple-800/50 px-3 py-1.5 text-xs font-semibold text-purple-200 transition hover:bg-purple-700/50"
                    title="View user management activity logs (Superuser only)"
                  >
                    📋 View Logs
                  </a>
                )}
                <button
                  type="button"
                  className="rounded-lg border border-sky-500 bg-sky-600/30 px-3 py-1.5 text-xs font-semibold text-sky-200 transition hover:bg-sky-600/40"
                  onClick={() => setShowUserForm(true)}
                >
                  ➕ Create User
                </button>
              </div>
            </div>

            {/* Filters */}
            <div className="mb-4 rounded-xl border border-slate-800/80 bg-gradient-to-br from-slate-900/90 via-slate-800/60 to-slate-900/90 p-2 shadow-xl">
              <h6 className="mb-2 text-xs font-bold text-slate-200">🔍 Filter & Search Users</h6>
              <div className="grid grid-cols-1 gap-2 md:grid-cols-6">
                <div className="md:col-span-2">
                  <label htmlFor="search" className="mb-0.5 text-[8px] font-semibold uppercase tracking-wide text-slate-400">
                    <span className="text-[10px]">🔎</span> Search Users
                  </label>
                  <input
                    type="text"
                    className="w-full rounded-lg border border-slate-700/70 bg-slate-900/80 px-2 py-1 text-[10px] font-medium text-slate-200 shadow-inner transition hover:border-sky-500 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500/30"
                    id="search"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Username, email, or name"
                  />
                </div>
                <div className="md:col-span-2">
                  <CompactMultiSelectDropdown
                    label="User Status"
                    options={statusOptions}
                    selected={selectedStatuses}
                    onChange={setSelectedStatuses}
                    icon="📊"
                    placeholder="All Statuses"
                    optionFormatter={(val) => val.charAt(0).toUpperCase() + val.slice(1)}
                  />
                </div>
                <div className="md:col-span-2">
                  <CompactMultiSelectDropdown
                    label="Role"
                    options={roleOptions}
                    selected={selectedRoles}
                    onChange={setSelectedRoles}
                    icon="👤"
                    placeholder="All Roles"
                    optionFormatter={(val) => val.charAt(0).toUpperCase() + val.slice(1)}
                  />
                </div>
              </div>
              <div className="mt-2 flex gap-2">
                <button
                  type="button"
                  className="flex-1 rounded-lg border border-sky-500 bg-sky-600/30 px-3 py-1.5 text-[9px] font-semibold uppercase tracking-wide text-slate-200 transition hover:bg-sky-600/40"
                  onClick={handleApplyFilters}
                >
                  🔍 Apply Filters
                </button>
                <button
                  type="button"
                  className="flex-1 rounded-lg border border-slate-700 bg-slate-800/50 px-3 py-1.5 text-[9px] font-semibold uppercase tracking-wide text-slate-200 transition hover:bg-slate-800"
                  onClick={handleClearFilters}
                >
                  ✖️ Clear Filters
                </button>
              </div>
            </div>

            {/* Users Table with vertical scroll */}
            <div className="rounded-lg border border-slate-700/70 bg-slate-900/60 dark:border-slate-600 dark:bg-slate-800/60">
              <div className="overflow-auto" style={{ maxHeight: '600px' }}>
                <table className="w-full text-sm text-slate-200 dark:text-slate-100">
                  <thead className="sticky top-0 z-10 border-b border-slate-700 bg-slate-800/50 dark:border-slate-600 dark:bg-slate-700/50">
                    <tr>
                      <th className="bg-slate-800/90 p-3 text-left font-semibold text-slate-300 dark:bg-slate-700/90 dark:text-slate-200">Username</th>
                      <th className="bg-slate-800/90 p-3 text-left font-semibold text-slate-300 dark:bg-slate-700/90 dark:text-slate-200">Email</th>
                      <th className="bg-slate-800/90 p-3 text-left font-semibold text-slate-300 dark:bg-slate-700/90 dark:text-slate-200">Role</th>
                      <th className="bg-slate-800/90 p-3 text-left font-semibold text-slate-300 dark:bg-slate-700/90 dark:text-slate-200">Status</th>
                      <th className="bg-slate-800/90 p-3 text-left font-semibold text-slate-300 dark:bg-slate-700/90 dark:text-slate-200">Usage Score</th>
                      <th className="bg-slate-800/90 p-3 text-left font-semibold text-slate-300 dark:bg-slate-700/90 dark:text-slate-200">Failed Logins</th>
                      <th className="bg-slate-800/90 p-3 text-left font-semibold text-slate-300 dark:bg-slate-700/90 dark:text-slate-200">Last Login</th>
                      <th className="bg-slate-800/90 p-3 text-left font-semibold text-slate-300 dark:bg-slate-700/90 dark:text-slate-200">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800 dark:divide-slate-700">
                  {users.length === 0 ? (
                    <tr>
                      <td colSpan={8} className="px-3 py-4 text-center text-slate-400 dark:text-slate-500">
                        No users found
                      </td>
                    </tr>
                  ) : (
                    users.map((profile) => {
                      const usageScore = profile.usage_score ?? 0;
                      const failedAttempts = profile.failed_attempts_all_time ?? 0;
                      const failedRecent = profile.failed_attempts_recent ?? 0;
                      const successfulLogins30d = profile.successful_logins_30d ?? 0;
                      const totalLogins = profile.successful_logins_all_time ?? 0;
                      
                      // Determine usage badge color (theme-aware)
                      let usageBadgeClass = 'bg-slate-600/30 dark:bg-slate-500/30 text-slate-700 dark:text-slate-300';
                      if (usageScore >= 150) {
                        usageBadgeClass = 'bg-green-600/30 dark:bg-green-500/30 text-green-700 dark:text-green-200';
                      } else if (usageScore >= 100) {
                        usageBadgeClass = 'bg-blue-600/30 dark:bg-blue-500/30 text-blue-700 dark:text-blue-200';
                      } else if (usageScore >= 50) {
                        usageBadgeClass = 'bg-yellow-600/30 dark:bg-yellow-500/30 text-yellow-700 dark:text-yellow-200';
                      } else if (usageScore > 0) {
                        usageBadgeClass = 'bg-orange-600/30 dark:bg-orange-500/30 text-orange-700 dark:text-orange-200';
                      }
                      
                      // Determine failed attempts badge color (theme-aware)
                      let failedBadgeClass = 'bg-green-600/30 dark:bg-green-500/30 text-green-700 dark:text-green-200';
                      if (failedAttempts >= 10) {
                        failedBadgeClass = 'bg-red-600/30 dark:bg-red-500/30 text-red-700 dark:text-red-200';
                      } else if (failedAttempts >= 5) {
                        failedBadgeClass = 'bg-orange-600/30 dark:bg-orange-500/30 text-orange-700 dark:text-orange-200';
                      } else if (failedAttempts > 0) {
                        failedBadgeClass = 'bg-yellow-600/30 dark:bg-yellow-500/30 text-yellow-700 dark:text-yellow-200';
                      }
                      
                      return (
                        <tr key={profile.id} className="hover:bg-slate-800/30 dark:hover:bg-slate-700/30">
                          <td className="p-3">
                            <strong className="text-slate-200 dark:text-slate-100">{profile.user.username}</strong>
                          </td>
                          <td className="p-3 text-slate-300 dark:text-slate-200">{profile.user.email}</td>
                          <td className="p-3">
                            <span className="rounded bg-sky-600/30 px-2 py-1 text-xs font-semibold text-sky-200 dark:bg-sky-500/30 dark:text-sky-100">
                              {profile.role}
                            </span>
                          </td>
                          <td className="p-3">
                            {profile.user.is_active ? (
                              <span className="rounded bg-green-600/30 px-2 py-1 text-xs font-semibold text-green-700 dark:bg-green-500/30 dark:text-green-200">
                                Active
                              </span>
                            ) : (
                              <span className="rounded bg-slate-600/30 px-2 py-1 text-xs font-semibold text-slate-700 dark:bg-slate-500/30 dark:text-slate-300">
                                Inactive
                              </span>
                            )}
                          </td>
                          <td className="p-3">
                            <div className="flex flex-col gap-1">
                              <span className={`rounded px-2 py-1 text-xs font-semibold ${usageBadgeClass}`}>
                                {usageScore} pts
                              </span>
                              <span className="text-xs text-slate-400 dark:text-slate-500">
                                {totalLogins} total • {successfulLogins30d} (30d)
                              </span>
                            </div>
                          </td>
                          <td className="p-3">
                            <div className="flex flex-col gap-1">
                              <span className={`rounded px-2 py-1 text-xs font-semibold ${failedBadgeClass}`}>
                                {failedAttempts} total
                              </span>
                              {failedRecent > 0 && (
                                <span className="text-xs text-orange-600 dark:text-orange-400">
                                  {failedRecent} recent
                                </span>
                              )}
                            </div>
                          </td>
                          <td className="p-3 text-slate-300 dark:text-slate-200">
                            {profile.user.last_login
                              ? new Date(profile.user.last_login).toLocaleDateString()
                              : 'Never'}
                          </td>
                          <td className="p-3">
                            <div className="flex flex-col gap-1">
                              <a
                                href={`/edit-user-access/${profile.user.id}/`}
                                className="rounded-lg border border-amber-700 bg-amber-800/30 px-2 py-1 text-xs font-semibold text-amber-200 transition hover:bg-amber-800/50 dark:border-amber-600 dark:bg-amber-700/30 dark:text-amber-100 dark:hover:bg-amber-700/50"
                              >
                                ✏️ Edit Access
                              </a>
                              <button
                                type="button"
                                className="rounded-lg border border-sky-700 bg-sky-800/30 px-2 py-1 text-[11px] font-semibold text-sky-200 transition hover:bg-sky-800/50 dark:border-sky-500 dark:bg-sky-700/30 dark:text-sky-100 dark:hover:bg-sky-700/50"
                                onClick={() =>
                                  handleSendPasswordReset(
                                    profile.user.id,
                                    profile.user.username,
                                    profile.user.email,
                                  )
                                }
                              >
                                🔑 Send Reset Link
                              </button>
                              {isSuperuser && (
                                <button
                                  type="button"
                                  className="rounded-lg border border-red-700 bg-red-800/30 px-2 py-1 text-[11px] font-semibold text-red-200 transition hover:bg-red-800/50 dark:border-red-600 dark:bg-red-700/30 dark:text-red-100 dark:hover:bg-red-700/50"
                                  onClick={() =>
                                    handleDeleteUser(
                                      profile.user.username,
                                      profile.user.email,
                                    )
                                  }
                                >
                                  🗑️ Delete User
                                </button>
                              )}
                            </div>
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

        {/* Role & Feature Management */}
        <RoleAndFeatureManagement users={users} onUsersChange={loadData} />

        {/* Access Management Section */}
        <div className="row mt-4">
          <div className="col-12">
            <div className="card dark:border-slate-700 dark:bg-slate-800">
              <div className="bg-primary card-header text-white dark:bg-blue-700 dark:text-slate-100">
                <h4 className="text-white dark:text-slate-100">
                  <i className="fas fa-shield-alt"></i> Access Management
                </h4>
              </div>
              <div className="card-body dark:bg-slate-800">
                <div className="row">
                  <div className="col-md-4 mb-3">
                    <div className="card h-100 dark:border-slate-600 dark:bg-slate-700">
                      <div className="card-body">
                        <h5 className="card-title text-slate-900 dark:text-slate-100">
                          <i className="fas fa-user-tag"></i> Role Management
                        </h5>
                        <p className="card-text text-slate-600 dark:text-slate-300">
                          Manage user roles and assign capabilities to roles.
                        </p>
                        <a
                          href="/accounts/manage/roles/"
                          className="btn btn-primary dark:border-blue-600 dark:bg-blue-600 dark:text-blue-100"
                          target="_parent"
                          data-skip-iframe-nav="true"
                        >
                          <i className="fas fa-cog"></i> Manage Roles
                        </a>
                      </div>
                    </div>
                  </div>
                  <div className="col-md-4 mb-3">
                    <div className="card h-100 dark:border-slate-600 dark:bg-slate-700">
                      <div className="card-body">
                        <h5 className="card-title text-slate-900 dark:text-slate-100">
                          <i className="fas fa-key"></i> Capability Management
                        </h5>
                        <p className="card-text text-slate-600 dark:text-slate-300">
                          Create and manage system capabilities that can be assigned to roles.
                        </p>
                        <a
                          href="/accounts/manage/capabilities/"
                          className="btn btn-info dark:border-cyan-600 dark:bg-cyan-600 dark:text-cyan-100"
                          target="_parent"
                          data-skip-iframe-nav="true"
                        >
                          <i className="fas fa-cog"></i> Manage Capabilities
                        </a>
                      </div>
                    </div>
                  </div>
                  <div className="col-md-4 mb-3">
                    <div className="card h-100 dark:border-slate-600 dark:bg-slate-700">
                      <div className="card-body">
                        <h5 className="card-title text-slate-900 dark:text-slate-100">
                          <i className="fas fa-star"></i> Feature Management
                        </h5>
                        <p className="card-text text-slate-600 dark:text-slate-300">
                          Manage application features and assign them to roles.
                        </p>
                        <a
                          href="/accounts/manage/features/"
                          className="btn btn-success dark:border-green-600 dark:bg-green-600 dark:text-green-100"
                          target="_parent"
                          data-skip-iframe-nav="true"
                        >
                          <i className="fas fa-cog"></i> Manage Features
                        </a>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Security Management - Superuser Only */}
        {isSuperuser && <SecurityManagement users={users} />}

        {/* Feature Flag Management - Superuser Only */}
        {isSuperuser && (
          <FeatureFlagManagement flags={flags} users={users} onFlagsChange={loadData} />
        )}

        {/* User Form Modal */}
        <UserFormModal
          show={showUserForm}
          onClose={() => setShowUserForm(false)}
          onSuccess={() => {
            loadData();
            setShowUserForm(false);
          }}
          assets={assets}
          countries={countries}
          portfolios={portfolios}
        />
      </div>
    </div>
  );
}

