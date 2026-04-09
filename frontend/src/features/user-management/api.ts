// User Management API Client
import type {
  UserProfile,
  Asset,
  ActivityDataPoint,
  SuspiciousActivity,
  ActiveUser,
  BlockedIP,
  BlockedUser,
  WaffleFlag,
  UserStats,
  CreateUserPayload,
  UpdateUserPayload,
  DownloadActivityFilters,
  CreateFlagPayload,
  UpdateFlagPayload,
} from './types';

// CSRF token cache
let csrfTokenCache: string | null = null;
let csrfTokenPromise: Promise<string> | null = null;

async function parseApiResponse<T>(response: Response): Promise<T> {
  const contentType = response.headers.get('content-type') || '';
  const isJson = contentType.includes('application/json');

  if (!isJson) {
    const raw = (await response.text().catch(() => '')).trim();
    const isHtml = raw.toLowerCase().startsWith('<!doctype') || raw.toLowerCase().startsWith('<html');
    if (response.status === 401) throw new Error('Session expired. Please log in again.');
    if (response.status === 403) throw new Error('Access denied or CSRF validation failed. Please refresh and try again.');
    throw new Error(
      isHtml ? 'Server returned an HTML page instead of API JSON. Please refresh and retry.' : raw || `HTTP error! status: ${response.status}`
    );
  }

  const payload = (await response.json().catch(() => null)) as { error?: string; message?: string; success?: boolean } | null;
  if (!response.ok) {
    throw new Error(payload?.error || payload?.message || `HTTP error! status: ${response.status}`);
  }
  return payload as T;
}

// Helper function to get CSRF token from API endpoint
async function getCSRFToken(): Promise<string> {
  // Return cached token if available
  if (csrfTokenCache) {
    return csrfTokenCache;
  }

  // Return existing promise if token fetch is in progress
  if (csrfTokenPromise) {
    return csrfTokenPromise;
  }

  // Fetch token from API endpoint
  csrfTokenPromise = fetch('/api/csrf-token/', {
    method: 'GET',
    credentials: 'include',
  })
    .then((response) => parseApiResponse<{ success?: boolean; csrfToken?: string }>(response))
    .then((data) => {
      if (data.success && data.csrfToken) {
        csrfTokenCache = data.csrfToken;
        return data.csrfToken;
      }
      throw new Error('Failed to get CSRF token from API');
    })
    .catch((error) => {
      csrfTokenPromise = null; // Reset promise on error
      console.error('Error fetching CSRF token:', error);
      throw error;
    });

  return csrfTokenPromise;
}

// Helper function for GET requests
async function get<T>(url: string): Promise<T> {
  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
  });

  return parseApiResponse<T>(response);
}

// Helper function for POST requests
async function post<T>(url: string, data: unknown): Promise<T> {
  const csrfToken = await getCSRFToken();
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken,
    },
    credentials: 'include',
    body: JSON.stringify(data),
  });

  return parseApiResponse<T>(response);
}

// Helper function for form POST requests (multipart/form-data)
async function postForm<T>(url: string, formData: FormData): Promise<T> {
  const csrfToken = await getCSRFToken();
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'X-CSRFToken': csrfToken,
    },
    credentials: 'include',
    body: formData,
  });

  return parseApiResponse<T>(response);
}

// Helper function for DELETE requests
async function del<T>(url: string): Promise<T> {
  const csrfToken = await getCSRFToken();
  const response = await fetch(url, {
    method: 'DELETE',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken,
    },
    credentials: 'include',
  });

  return parseApiResponse<T>(response);
}

// ============================================================================
// User Management Data
// ============================================================================

export async function fetchUserManagementData(params?: {
  search?: string;
  role?: string;
  status?: string;
}): Promise<{
  users: UserProfile[];
  assets: Asset[];
  countries: string[];
  portfolios: string[];
  stats: UserStats;
  activity_data: ActivityDataPoint[];
  suspicious_activities: SuspiciousActivity[];
  flags?: WaffleFlag[];
  flag_search_query?: string;
  is_superuser?: boolean;
}> {
  const queryParams = new URLSearchParams();
  if (params?.search) queryParams.append('search', params.search);
  if (params?.role) queryParams.append('role', params.role);
  if (params?.status) queryParams.append('status', params.status);

  const url = `/api/user-management/data/${queryParams.toString() ? `?${queryParams.toString()}` : ''}`;
  return get(url);
}

// ============================================================================
// User CRUD Operations
// ============================================================================

export async function createUser(payload: CreateUserPayload): Promise<{ success: boolean; message: string }> {
  const formData = new FormData();
  formData.append('username', payload.username);
  formData.append('email', payload.email);
  formData.append('password', payload.password);
  formData.append('role', payload.role);
  
  payload.access_control.forEach((access) => {
    formData.append('access_control', access);
  });
  
  if (payload.countries) {
    payload.countries.forEach((country) => {
      formData.append('countries', country);
    });
  }
  
  if (payload.portfolios) {
    payload.portfolios.forEach((portfolio) => {
      formData.append('portfolios', portfolio);
    });
  }
  
  if (payload.sites) {
    payload.sites.forEach((site) => {
      formData.append('sites', site);
    });
  }

  return postForm('/user-management/', formData);
}

export async function updateUser(userId: number, payload: UpdateUserPayload): Promise<{ success: boolean; message: string }> {
  const formData = new FormData();
  
  if (payload.email) formData.append('email', payload.email);
  if (payload.first_name) formData.append('first_name', payload.first_name);
  if (payload.last_name) formData.append('last_name', payload.last_name);
  if (payload.role) formData.append('role', payload.role);
  if (payload.is_active !== undefined) formData.append('is_active', payload.is_active ? 'true' : 'false');
  
  if (payload.access_control) {
    payload.access_control.forEach((access) => {
      formData.append('access_control', access);
    });
  }
  
  if (payload.countries) {
    payload.countries.forEach((country) => {
      formData.append('countries', country);
    });
  }
  
  if (payload.portfolios) {
    payload.portfolios.forEach((portfolio) => {
      formData.append('portfolios', portfolio);
    });
  }
  
  if (payload.sites) {
    payload.sites.forEach((site) => {
      formData.append('sites', site);
    });
  }

  return postForm(`/edit-user-access/${userId}/`, formData);
}

export async function deleteUser(username: string): Promise<{ success: boolean; message: string }> {
  return post('/security/delete-user/', { username });
}

export async function deactivateUser(username: string): Promise<{ success: boolean; message: string }> {
  return post('/security/deactivate-user/', { username });
}

export async function reactivateUser(username: string): Promise<{ success: boolean; message: string }> {
  return post('/security/reactivate-user/', { username });
}

export async function sendPasswordReset(userId: number): Promise<{ success: boolean; message: string }> {
  return post(`/send-password-reset/${userId}/`, {});
}

// ============================================================================
// Activity & Statistics
// ============================================================================

export async function fetchUserActivity(): Promise<{ activity_data: ActivityDataPoint[] }> {
  return get('/api/user-activity/');
}

export async function downloadUserActivity(filters: DownloadActivityFilters): Promise<void> {
  const queryParams = new URLSearchParams();
  if (filters.start_date) queryParams.append('start_date', filters.start_date);
  if (filters.end_date) queryParams.append('end_date', filters.end_date);
  if (filters.user) queryParams.append('user', filters.user);
  if (filters.action) queryParams.append('action', filters.action);
  if (filters.ip) queryParams.append('ip', filters.ip);
  if (filters.include_suspicious) queryParams.append('include_suspicious', 'true');

  const url = `/download-user-activity/?${queryParams.toString()}`;
  window.location.href = url;
}

export async function fetchActiveUsers(): Promise<ActiveUser[]> {
  // This would need to be implemented as an API endpoint
  // For now, return empty array
  return [];
}

// ============================================================================
// Blocked IPs & Users (Superuser Only)
// ============================================================================

export async function fetchBlockedIPs(params?: {
  status?: string;
  search?: string;
  per_page?: number | 'all';
}): Promise<{ data: BlockedIP[]; totalCount: number }> {
  const queryParams = new URLSearchParams();
  if (params?.status) queryParams.append('status', params.status);
  if (params?.search) queryParams.append('search', params.search);
  if (params?.per_page) {
    queryParams.append('per_page', params.per_page === 'all' ? 'all' : String(params.per_page));
  }

  const url = `/api/blocking/ips/${queryParams.toString() ? `?${queryParams.toString()}` : ''}`;
  const response = await get<{ success: boolean; data: BlockedIP[]; pagination?: { total_count: number } }>(url);
  return {
    data: Array.isArray(response.data) ? response.data : [],
    totalCount: response.pagination?.total_count ?? (Array.isArray(response.data) ? response.data.length : 0)
  };
}

export async function blockIP(ipAddress: string, reason: string, description?: string): Promise<{ success: boolean; message: string }> {
  return post('/api/blocking/block-ip/', {
    ip_address: ipAddress,
    reason,
    description: description || '',
  });
}

export async function unblockIP(ipAddress: string): Promise<{ success: boolean; message: string }> {
  return post('/api/blocking/unblock-ip/', {
    ip_address: ipAddress,
  });
}

export async function fetchBlockedUsers(params?: {
  status?: string;
  search?: string;
}): Promise<BlockedUser[]> {
  const queryParams = new URLSearchParams();
  if (params?.status) queryParams.append('status', params.status);
  if (params?.search) queryParams.append('search', params.search);

  const url = `/api/blocking/users/${queryParams.toString() ? `?${queryParams.toString()}` : ''}`;
  const response = await get<{ success: boolean; data: Array<{
    id: number;
    username: string;
    email: string;
    status: string;
    priority: string;
    reason: string;
    description: string;
    created_at: string;
    expires_at: string | null;
    block_count: number;
    last_seen: string | null;
  }> }>(url);
  
  // Map API response to BlockedUser type
  if (Array.isArray(response.data)) {
    return response.data.map((item) => ({
      id: item.id,
      user: {
        id: 0, // API doesn't return user id
        username: item.username,
        email: item.email,
      },
      status: item.status as 'active' | 'inactive' | 'whitelisted',
      priority: item.priority as 'low' | 'medium' | 'high' | 'critical',
      reason: item.reason,
      description: item.description,
      blocked_by: null, // API doesn't return this
      created_at: item.created_at,
      expires_at: item.expires_at,
      block_count: item.block_count,
      last_seen: item.last_seen,
    }));
  }
  return [];
}

export async function blockUser(username: string, reason: string, description?: string): Promise<{ success: boolean; message: string }> {
  return post('/api/blocking/block-user/', {
    username,
    reason,
    description: description || '',
  });
}

export async function unblockUser(username: string): Promise<{ success: boolean; message: string }> {
  return post('/api/blocking/unblock-user/', {
    username,
  });
}

// ============================================================================
// Waffle Flag Management (Superuser Only)
// ============================================================================

export async function fetchFlags(): Promise<WaffleFlag[]> {
  // Flags are included in the main user management data response
  // For now, we'll need to fetch them separately or include them in the main response
  // This is a placeholder - the actual implementation should call an API endpoint
  const data = await fetchUserManagementData();
  return data.flags || [];
}

export async function createFlag(payload: CreateFlagPayload): Promise<{ success: boolean; message: string; flag?: WaffleFlag }> {
  return post('/user-management/flags/create/', payload);
}

export async function updateFlag(flagId: number, payload: UpdateFlagPayload): Promise<{ success: boolean; message: string; flag?: WaffleFlag }> {
  return post(`/user-management/flags/${flagId}/update/`, payload);
}

export async function deleteFlag(flagId: number): Promise<{ success: boolean; message: string }> {
  return del(`/user-management/flags/${flagId}/delete/`);
}

export async function exportFlagsCSV(): Promise<void> {
  // Check if we're in an iframe
  const isInIframe = window.self !== window.top;
  const downloadUrl = '/user-management/flags/export-csv/';
  
  if (isInIframe) {
    // Try multiple methods for sandboxed iframes
    try {
      // Method 1: Try using postMessage to ask parent to open download
      // This works even if the iframe doesn't have allow-downloads
      if (window.parent && window.parent !== window.self) {
        window.parent.postMessage({
          type: 'download_request',
          url: downloadUrl,
          filename: 'flags.csv',
        }, '*');
        
        // Also try the iframe method as backup
        const iframe = document.createElement('iframe');
        iframe.style.display = 'none';
        iframe.style.width = '0';
        iframe.style.height = '0';
        iframe.src = downloadUrl;
        document.body.appendChild(iframe);
        
        // Remove iframe after a delay to clean up
        setTimeout(() => {
          if (document.body.contains(iframe)) {
            document.body.removeChild(iframe);
          }
        }, 5000);
      }
    } catch (error) {
      console.error('Download failed in iframe context:', error);
      // Fallback: try direct navigation (might fail but worth trying)
      try {
        window.location.href = downloadUrl;
      } catch (e) {
        console.error('All download methods failed:', e);
        throw new Error('Download is not allowed in this sandboxed context. Please open this page in a new tab to download.');
      }
    }
  } else {
    // For non-iframe contexts, use anchor element
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = 'flags.csv';
    link.style.display = 'none';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }
}

export async function importFlagsCSV(file: File, updateExisting: boolean = true): Promise<{ success: boolean; message: string; statistics?: unknown }> {
  const formData = new FormData();
  formData.append('csv_file', file);
  formData.append('update_existing', updateExisting ? 'true' : 'false');
  return postForm('/user-management/flags/import-csv/', formData);
}

export async function assignFlagsToUser(userId: number, flagIds: number[]): Promise<{ success: boolean; message: string }> {
  return post('/user-management/flags/assign-to-user/', {
    user_id: userId,
    flag_ids: flagIds,
  });
}

