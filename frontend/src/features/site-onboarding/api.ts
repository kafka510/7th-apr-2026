// Site Onboarding API Client
import type {
  AssetList,
  DeviceList,
  DeviceMapping,
  BudgetValues,
  ICBudget,
  PaginatedResponse,
  ICBudgetResponse,
  ApiResponse,
  UploadResponse,
  TableName,
  SpareMaster,
  LocationMaster,
  SpareSiteMap,
  StockBalance,
  StockEntry,
  StockIssue,
  AssetAdapterConfig,
  AssetAdapterConfigConfig,
  AdapterAccount,
  DeviceOperatingState,
  AssetContract,
} from './types';

const API_BASE = '/api/site-onboarding';

// CSRF token cache
let csrfTokenCache: string | null = null;
let csrfTokenPromise: Promise<string> | null = null;

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
  csrfTokenPromise = (async () => {
    try {
      const response = await fetch('/api/csrf-token/', {
        method: 'GET',
        credentials: 'include',
        headers: {
          Accept: 'application/json',
        },
      });
      const data = await parseApiResponse<{ success?: boolean; csrfToken?: string }>(response);
      if (data.success && data.csrfToken) {
        csrfTokenCache = data.csrfToken;
        return data.csrfToken;
      }
      throw new Error('Failed to get CSRF token from API');
    } catch (error) {
      csrfTokenPromise = null; // Reset promise on error
      console.error('Error fetching CSRF token:', error);
      throw error;
    }
  })();

  return csrfTokenPromise;
}

// Helper function for GET requests
async function parseApiResponse<T>(response: Response): Promise<T> {
  const contentType = response.headers.get('content-type') || '';
  const isJson = contentType.includes('application/json');

  if (isJson) {
    const payload = (await response.json().catch(() => null)) as
      | { error?: string; message?: string; detail?: string; success?: boolean }
      | null;
    if (!response.ok) {
      const message =
        payload?.error ||
        payload?.message ||
        payload?.detail ||
        (response.status === 401
          ? 'Authentication required. Please log in again.'
          : response.status === 403
            ? 'Access denied or CSRF validation failed. Please refresh and try again.'
            : `HTTP error! status: ${response.status}`);
      throw new Error(message);
    }
    return payload as T;
  }

  const rawText = (await response.text().catch(() => '')).trim();
  const isHtml = rawText.toLowerCase().startsWith('<!doctype') || rawText.toLowerCase().startsWith('<html');
  const message = isHtml
    ? (response.status === 401
        ? 'Authentication required. Please log in again.'
        : response.status === 403
          ? 'Session/CSRF validation failed. Please refresh the page and try again.'
          : 'Server returned an HTML page instead of API JSON. Please refresh and retry.')
    : rawText || `Unexpected non-JSON API response (status ${response.status}).`;
  throw new Error(message);
}

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
  const doPost = (token: string) =>
    fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': token,
      },
      credentials: 'include',
      body: JSON.stringify(data),
    });

  let response = await doPost(csrfToken);
  if (response.status === 403) {
    // One-time token refresh retry for stale CSRF tokens.
    csrfTokenCache = null;
    csrfTokenPromise = null;
    const refreshedToken = await getCSRFToken();
    response = await doPost(refreshedToken);
  }
  return parseApiResponse<T>(response);
}

// Helper function for DELETE requests
async function del<T>(url: string): Promise<T> {
  const csrfToken = await getCSRFToken();
  const doDelete = (token: string) =>
    fetch(url, {
      method: 'DELETE',
      headers: {
        'X-CSRFToken': token,
      },
      credentials: 'include',
    });

  let response = await doDelete(csrfToken);
  if (response.status === 403) {
    csrfTokenCache = null;
    csrfTokenPromise = null;
    const refreshedToken = await getCSRFToken();
    response = await doDelete(refreshedToken);
  }
  return parseApiResponse<T>(response);
}

// Asset List API
export async function fetchAssetList(
  page = 1,
  pageSize = 25,
  search = ''
): Promise<PaginatedResponse<AssetList>> {
  const params = new URLSearchParams({
    page: page.toString(),
    page_size: pageSize.toString(),
    ...(search && { search }),
  });
  return get<PaginatedResponse<AssetList>>(`${API_BASE}/asset-list/?${params}`);
}

export async function createAssetList(data: Partial<AssetList>): Promise<ApiResponse> {
  return post<ApiResponse>(`${API_BASE}/asset-list/create/`, data);
}

export async function updateAssetList(data: Partial<AssetList>): Promise<ApiResponse> {
  return post<ApiResponse>(`${API_BASE}/asset-list/update/`, data);
}

export async function deleteAssetList(assetCode: string): Promise<ApiResponse> {
  return del<ApiResponse>(`${API_BASE}/asset-list/delete/${assetCode}/`);
}

export async function getUniqueApiNames(): Promise<{ success: boolean; api_names: string[] }> {
  return get<{ success: boolean; api_names: string[] }>(`${API_BASE}/api-names/`);
}

export async function getAllAssets(): Promise<AssetList[]> {
  // Fetch all assets (with a large page size to get all)
  const response = await fetchAssetList(1, 10000, '');
  return response.data;
}

// Device List API
export async function fetchDeviceList(
  page = 1,
  pageSize = 25,
  search = '',
  parentCode: string | string[] = ''
): Promise<PaginatedResponse<DeviceList>> {
  const parentCodeParam = Array.isArray(parentCode) ? parentCode.join(',') : parentCode;
  const params = new URLSearchParams({
    page: page.toString(),
    page_size: pageSize.toString(),
    ...(search && { search }),
    ...(parentCodeParam && { parent_code: parentCodeParam }),
  });
  return get<PaginatedResponse<DeviceList>>(`${API_BASE}/device-list/?${params}`);
}

export async function createDeviceList(data: Partial<DeviceList>): Promise<ApiResponse> {
  return post<ApiResponse>(`${API_BASE}/device-list/create/`, data);
}

export async function updateDeviceList(data: Partial<DeviceList>): Promise<ApiResponse> {
  return post<ApiResponse>(`${API_BASE}/device-list/update/`, data);
}

export async function deleteDeviceList(deviceId: string): Promise<ApiResponse> {
  return del<ApiResponse>(`${API_BASE}/device-list/delete/${deviceId}/`);
}

// Device Mapping API
export async function fetchDeviceMapping(
  page = 1,
  pageSize = 25,
  search = '',
  assetCode = ''
): Promise<PaginatedResponse<DeviceMapping>> {
  const params = new URLSearchParams({
    page: page.toString(),
    page_size: pageSize.toString(),
    ...(search && { search }),
    ...(assetCode && { asset_code: assetCode }),
  });
  return get<PaginatedResponse<DeviceMapping>>(`${API_BASE}/device-mapping/?${params}`);
}

export async function createDeviceMapping(data: Partial<DeviceMapping>): Promise<ApiResponse & { id?: number }> {
  return post<ApiResponse & { id?: number }>(`${API_BASE}/device-mapping/create/`, data);
}

export async function updateDeviceMapping(data: Partial<DeviceMapping>): Promise<ApiResponse> {
  return post<ApiResponse>(`${API_BASE}/device-mapping/update/`, data);
}

export async function deleteDeviceMapping(mappingId: number): Promise<ApiResponse> {
  return del<ApiResponse>(`${API_BASE}/device-mapping/delete/${mappingId}/`);
}

// Device Operating State API
export async function fetchDeviceOperatingState(
  page = 1,
  pageSize = 25,
  search = '',
  adapterId = '',
  deviceType = ''
): Promise<PaginatedResponse<DeviceOperatingState>> {
  const params = new URLSearchParams({
    page: page.toString(),
    page_size: pageSize.toString(),
    ...(search && { search }),
    ...(adapterId && { adapter_id: adapterId }),
    ...(deviceType && { device_type: deviceType }),
  });
  return get<PaginatedResponse<DeviceOperatingState>>(`${API_BASE}/device-operating-state/?${params}`);
}

export async function createDeviceOperatingState(
  data: Partial<DeviceOperatingState>
): Promise<ApiResponse & { id?: number }> {
  return post<ApiResponse & { id?: number }>(`${API_BASE}/device-operating-state/create/`, data);
}

export async function updateDeviceOperatingState(
  data: Partial<DeviceOperatingState> & { id: number }
): Promise<ApiResponse> {
  return post<ApiResponse>(`${API_BASE}/device-operating-state/update/`, data);
}

export async function deleteDeviceOperatingState(id: number): Promise<ApiResponse> {
  return del<ApiResponse>(`${API_BASE}/device-operating-state/delete/${id}/`);
}

// Budget Values API
export async function fetchBudgetValues(
  page = 1,
  pageSize = 25,
  search = '',
  assetCode = ''
): Promise<PaginatedResponse<BudgetValues>> {
  const params = new URLSearchParams({
    page: page.toString(),
    page_size: pageSize.toString(),
    ...(search && { search }),
    ...(assetCode && { asset_code: assetCode }),
  });
  return get<PaginatedResponse<BudgetValues>>(`${API_BASE}/budget-values/?${params}`);
}

export async function createBudgetValues(data: Partial<BudgetValues>): Promise<ApiResponse> {
  return post<ApiResponse>(`${API_BASE}/budget-values/create/`, data);
}

export async function updateBudgetValues(data: Partial<BudgetValues>): Promise<ApiResponse> {
  return post<ApiResponse>(`${API_BASE}/budget-values/update/`, data);
}

export async function deleteBudgetValues(budgetId: number): Promise<ApiResponse> {
  return del<ApiResponse>(`${API_BASE}/budget-values/delete/${budgetId}/`);
}

export async function calculateBudgetValues(assetCodes: string[], fromYear: number, toYear: number): Promise<Blob> {
  const csrfToken = await getCSRFToken();
  const response = await fetch(`${API_BASE}/budget-values/calculate/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken,
    },
    credentials: 'include',
    body: JSON.stringify({
      asset_codes: assetCodes,
      from_year: fromYear,
      to_year: toYear,
    }),
  });

  if (!response.ok) {
    const contentType = response.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
      const error = await response.json().catch(() => ({ error: 'Unknown error' }));
      throw new Error(error.error || error.message || `HTTP error! status: ${response.status}`);
    }
    const raw = (await response.text().catch(() => '')).trim();
    const isHtml = raw.toLowerCase().startsWith('<!doctype') || raw.toLowerCase().startsWith('<html');
    if (response.status === 401) throw new Error('Authentication required. Please log in again.');
    if (response.status === 403) throw new Error('Session/CSRF validation failed. Please refresh the page and try again.');
    throw new Error(
      isHtml
        ? 'Server returned an HTML page instead of API JSON. Please refresh and retry.'
        : raw || `HTTP error! status: ${response.status}`
    );
  }

  return response.blob();
}

// IC Budget API
export async function fetchICBudget(
  page = 1,
  pageSize = 25,
  search = '',
  assetCode = ''
): Promise<ICBudgetResponse> {
  const params = new URLSearchParams({
    page: page.toString(),
    page_size: pageSize.toString(),
    ...(search && { search }),
    ...(assetCode && { asset_code: assetCode }),
  });
  return get<ICBudgetResponse>(`${API_BASE}/ic-budget/?${params}`);
}

export async function createICBudget(data: Partial<ICBudget>): Promise<ApiResponse> {
  return post<ApiResponse>(`${API_BASE}/ic-budget/create/`, data);
}

export async function updateICBudget(data: Partial<ICBudget>): Promise<ApiResponse> {
  return post<ApiResponse>(`${API_BASE}/ic-budget/update/`, data);
}

export async function deleteICBudget(icBudgetId: number): Promise<ApiResponse> {
  return del<ApiResponse>(`${API_BASE}/ic-budget/delete/${icBudgetId}/`);
}

// Asset Contracts API
export async function fetchAssetContracts(
  page = 1,
  pageSize = 25,
  search = ''
): Promise<PaginatedResponse<AssetContract> & { can_delete?: boolean }> {
  const params = new URLSearchParams({
    page: page.toString(),
    page_size: pageSize.toString(),
    ...(search && { search }),
  });
  return get<PaginatedResponse<AssetContract> & { can_delete?: boolean }>(`${API_BASE}/asset-contracts/?${params}`);
}

export async function createAssetContract(data: Partial<AssetContract>): Promise<ApiResponse & { id?: number }> {
  return post<ApiResponse & { id?: number }>(`${API_BASE}/asset-contracts/create/`, data);
}

export async function updateAssetContract(data: Partial<AssetContract> & { id: number }): Promise<ApiResponse> {
  return post<ApiResponse>(`${API_BASE}/asset-contracts/update/`, data);
}

export async function deleteAssetContract(contractId: number): Promise<ApiResponse> {
  return del<ApiResponse>(`${API_BASE}/asset-contracts/delete/${contractId}/`);
}

// Data collection adapter IDs (for Data Collection tab dropdown)
export async function getDataCollectionAdapterIds(): Promise<string[]> {
  const res = await get<{ adapter_ids: string[] }>(`${API_BASE}/data-collection-adapters/`);
  return res?.adapter_ids ?? [];
}

// Fusion Solar API-assisted onboarding (getStationList response items)
// Asset form mapping: Latitude <- latitude, Longitude <- longitude, Address <- plantAddress
export type FusionSolarPlant = Record<string, unknown>;
export type FusionSolarDeviceRow = {
  device_id: string;
  device_name: string;
  device_code: string;
  device_type_id: string;
  parent_code: string;
  device_type: string;
  country: string;
  // Optional richer fields mapped from Fusion Solar for onboarding
  latitude?: number | null;
  longitude?: number | null;
  device_model?: string | null;
  device_serial?: string | null;
  optimizer_no?: number | null;
  software_version?: string | null;
  device_make?: string | null;
};

export async function fusionSolarFetchPlants(body: {
  adapter_id: string;
  adapter_account_id: number;
}): Promise<{ success: true; plants: FusionSolarPlant[] } | { success: false; error: string }> {
  const res = await post<{ success: boolean; plants?: FusionSolarPlant[]; error?: string }>(
    `${API_BASE}/fusion-solar-fetch-plants/`,
    body
  );
  if (res.success && Array.isArray(res.plants)) return { success: true, plants: res.plants };
  return { success: false, error: res.error ?? 'Unknown error' };
}

export async function fusionSolarFetchDevices(body: {
  asset_code: string;
  plant_id?: string;
  adapter_account_id?: number;
}): Promise<{ success: true; devices: FusionSolarDeviceRow[] } | { success: false; error: string }> {
  const res = await post<{
    success: boolean;
    devices?: FusionSolarDeviceRow[];
    error?: string;
    message?: string;
    detail?: string;
    [key: string]: unknown;
  }>(`${API_BASE}/fusion-solar-fetch-devices/`, body);
  if (res.success && Array.isArray(res.devices)) return { success: true, devices: res.devices };
  const { devices: _devices, success: _success, ...rest } = res;
  const extra = Object.keys(rest).length > 0 ? ` | response=${JSON.stringify(rest)}` : '';
  const reason = res.error || res.message || res.detail || 'Unknown error';
  return { success: false, error: `Fusion device fetch failed: ${reason}${extra}` };
}

export type LaplaceNodeRow = {
  node_id: string;
  name: string;
  setTime?: string;
  tags?: string[];
};

export type LaplaceInstantMeta = {
  api_version?: string;
  instant_date?: string;
  instant_name?: string;
};

export async function laplaceidTestConnection(body: {
  adapter_account_id: number;
  groupid?: string;
}): Promise<
  { success: true; meta: LaplaceInstantMeta; nodes: LaplaceNodeRow[] } | { success: false; error: string }
> {
  const res = await post<{ success: boolean; meta?: LaplaceInstantMeta; nodes?: LaplaceNodeRow[]; error?: string }>(
    `${API_BASE}/laplaceid-test-connection/`,
    body
  );
  if (res.success && Array.isArray(res.nodes)) return { success: true, meta: res.meta ?? {}, nodes: res.nodes };
  return { success: false, error: res.error ?? 'Unknown error' };
}

export async function laplaceidFetchNodes(body: {
  asset_code: string;
  adapter_account_id: number;
  groupid?: string;
}): Promise<
  { success: true; meta: LaplaceInstantMeta; nodes: LaplaceNodeRow[] } | { success: false; error: string }
> {
  const res = await post<{ success: boolean; meta?: LaplaceInstantMeta; nodes?: LaplaceNodeRow[]; error?: string }>(
    `${API_BASE}/laplaceid-fetch-nodes/`,
    body
  );
  if (res.success && Array.isArray(res.nodes)) return { success: true, meta: res.meta ?? {}, nodes: res.nodes };
  return { success: false, error: res.error ?? 'Unknown error' };
}

export type LaplaceDiscoveredDevice = {
  device_code: string;
  device_name: string;
  device_type: string;
  seen_in_types: string[];
};

export async function laplaceidDiscoverDevices(body: {
  adapter_account_id: number;
  groupid?: string;
  unit?: string;
  time?: string;
  types?: string[];
  csv_api?: string;
  /** If set, default time= uses this asset's asset_list.timezone offset (previous local hour). */
  asset_code?: string;
}): Promise<
  | { success: true; devices: LaplaceDiscoveredDevice[]; errors: { type: string; error: string }[]; sample: Record<string, any> }
  | { success: false; error: string }
> {
  const res = await post<{
    success: boolean;
    devices?: LaplaceDiscoveredDevice[];
    errors?: { type: string; error: string }[];
    sample?: Record<string, any>;
    error?: string;
  }>(`${API_BASE}/laplaceid-discover-devices/`, body);
  if (res.success && Array.isArray(res.devices)) {
    return { success: true, devices: res.devices, errors: res.errors ?? [], sample: res.sample ?? {} };
  }
  return { success: false, error: res.error ?? 'Unknown error' };
}

export async function laplaceidFetchDevicesForAssets(body: {
  adapter_account_id: number;
  asset_codes: string[];
  groupid?: string;
  unit?: string;
  time?: string;
  types?: string[];
  csv_api?: string;
}): Promise<
  | {
      success: true;
      devices: FusionSolarDeviceRow[];
      laplace_csv?: Record<string, unknown>;
    }
  | { success: false; error: string }
> {
  const res = await post<{
    success: boolean;
    devices?: FusionSolarDeviceRow[];
    laplace_csv?: Record<string, unknown>;
    error?: string;
    message?: string;
    detail?: string;
    [key: string]: unknown;
  }>(`${API_BASE}/laplaceid-fetch-devices/`, body);
  if (res.success && Array.isArray(res.devices))
    return { success: true, devices: res.devices, laplace_csv: res.laplace_csv };
  const { devices: _devices, success: _success, ...rest } = res;
  const extra = Object.keys(rest).length > 0 ? ` | response=${JSON.stringify(rest)}` : '';
  const reason = res.error || res.message || res.detail || 'Unknown error';
  return { success: false, error: `Laplace device fetch failed: ${reason}${extra}` };
}

export type AdapterRawSampleFile = {
  asset_code: string;
  filename: string;
  content: string;
  media_type?: string;
  label?: string;
};

export async function fetchAdapterRawSamples(body: {
  adapter_id: string;
  adapter_account_id?: number;
  asset_codes: string[];
  groupid?: string;
  unit?: string;
  time?: string;
  types?: string[];
  csv_api?: string;
}): Promise<
  | { success: true; files: AdapterRawSampleFile[]; errors: { asset_code: string; detail: string }[]; adapter_id: string }
  | { success: false; error: string }
> {
  const res = await post<{
    success: boolean;
    files?: AdapterRawSampleFile[];
    errors?: { asset_code: string; detail: string }[];
    adapter_id?: string;
    error?: string;
  }>(`${API_BASE}/adapter-fetch-raw-samples/`, body);
  if (res.success && Array.isArray(res.files)) {
    return {
      success: true,
      files: res.files,
      errors: res.errors ?? [],
      adapter_id: res.adapter_id ?? body.adapter_id,
    };
  }
  return { success: false, error: res.error ?? 'Unknown error' };
}

// Asset Adapter Config API (Data Collection)
export async function fetchAssetAdapterConfig(
  page = 1,
  pageSize = 25,
  search = '',
  assetCode = '',
  adapterId = ''
): Promise<{ data: AssetAdapterConfig[]; total: number; page: number; page_size: number; total_pages: number }> {
  const params = new URLSearchParams({
    page: page.toString(),
    page_size: pageSize.toString(),
    ...(search && { search }),
    ...(assetCode && { asset_code: assetCode }),
    ...(adapterId && { adapter_id: adapterId }),
  });
  return get<{ data: AssetAdapterConfig[]; total: number; page: number; page_size: number; total_pages: number }>(
    `${API_BASE}/asset-adapter-config/?${params}`
  );
}

export async function createAssetAdapterConfig(data: {
  asset_code: string;
  adapter_id: string;
  adapter_account_id?: number;
  config?: AssetAdapterConfigConfig;
  acquisition_interval_minutes?: number;
  enabled?: boolean;
}): Promise<ApiResponse & { id?: number }> {
  return post<ApiResponse & { id?: number }>(`${API_BASE}/asset-adapter-config/create/`, data);
}

export async function updateAssetAdapterConfig(data: Partial<AssetAdapterConfig> & { id: number }): Promise<ApiResponse> {
  return post<ApiResponse>(`${API_BASE}/asset-adapter-config/update/`, data);
}

export async function deleteAssetAdapterConfig(configId: number): Promise<ApiResponse> {
  return del<ApiResponse>(`${API_BASE}/asset-adapter-config/delete/${configId}/`);
}

// AdapterAccount API
export async function fetchAdapterAccounts(adapterId?: string): Promise<{ data: AdapterAccount[] }> {
  const params = new URLSearchParams({
    ...(adapterId && { adapter_id: adapterId }),
  });
  const url = params.toString()
    ? `${API_BASE}/adapter-accounts/?${params}`
    : `${API_BASE}/adapter-accounts/`;
  return get<{ data: AdapterAccount[] }>(url);
}

export async function createAdapterAccount(data: {
  adapter_id: string;
  name?: string;
  config?: AssetAdapterConfigConfig;
  enabled?: boolean;
}): Promise<ApiResponse & { id?: number }> {
  return post<ApiResponse & { id?: number }>(`${API_BASE}/adapter-accounts/create/`, data);
}

export async function updateAdapterAccount(data: {
  id: number;
  name?: string;
  config?: AssetAdapterConfigConfig;
  enabled?: boolean;
}): Promise<ApiResponse> {
  return post<ApiResponse>(`${API_BASE}/adapter-accounts/update/`, data);
}

export async function deleteAdapterAccount(id: number): Promise<ApiResponse> {
  return del<ApiResponse>(`${API_BASE}/adapter-accounts/delete/${id}/`);
}

// Upload/Download API
export async function uploadCSVFile(tableName: TableName, file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append('csv_file', file);
  formData.append('table_name', tableName);

  const csrfToken = await getCSRFToken();
  const response = await fetch(`${API_BASE}/upload/`, {
    method: 'POST',
    headers: {
      'X-CSRFToken': csrfToken,
    },
    credentials: 'include',
    body: formData,
  });

  if (!response.ok) {
    const contentType = response.headers.get('content-type') || '';
    const errorData = contentType.includes('application/json')
      ? await response.json().catch(() => ({ error: 'Unknown error' }))
      : (() => {
          const fallback = { error: `HTTP error! status: ${response.status}` } as {
            error?: string;
            message?: string;
            validation_errors?: unknown[];
            error_examples?: unknown[];
            error_summary?: Record<string, unknown>;
            total_errors?: number;
            help_text?: string;
            errors?: unknown[];
          };
          return fallback;
        })();
    // If the error response has detailed validation errors, return them instead of throwing
    if (errorData.validation_errors || errorData.error_examples || errorData.message) {
      // Return the error response as-is so UploadModal can display it
      return {
        success: false,
        error: errorData.error || errorData.message || 'Upload failed',
        message: errorData.message || errorData.error || 'Upload failed',
        validation_errors: errorData.validation_errors || [],
        error_examples: errorData.error_examples || [],
        error_summary: errorData.error_summary || {},
        total_errors: errorData.total_errors || 0,
        help_text: errorData.help_text || '',
        errors: errorData.errors || []
      } as UploadResponse;
    }
    throw new Error(errorData.error || errorData.message || `HTTP error! status: ${response.status}`);
  }

  return parseApiResponse<UploadResponse>(response);
}

export function downloadData(
  tableName: TableName,
  filters?: { parent_code?: string | string[]; asset_code?: string; search?: string },
): void {
  const params = new URLSearchParams();
  if (filters?.parent_code) {
    const parentCodeParam = Array.isArray(filters.parent_code)
      ? filters.parent_code.join(',')
      : filters.parent_code;
    params.append('parent_code', parentCodeParam);
  }
  if (filters?.asset_code) {
    params.append('asset_code', filters.asset_code);
  }
  if (filters?.search) {
    params.append('search', filters.search);
  }
  const queryString = params.toString();
  window.location.href = `/site-onboarding/download/${tableName}/${queryString ? '?' + queryString : ''}`;
}

export function downloadTemplate(tableName: TableName): void {
  window.location.href = `/site-onboarding/template/${tableName}/`;
}

// Spare Master API
export async function fetchSpareMaster(
  page = 1,
  pageSize = 25,
  search = ''
): Promise<PaginatedResponse<SpareMaster>> {
  const params = new URLSearchParams({
    page: page.toString(),
    page_size: pageSize.toString(),
    ...(search && { search }),
  });
  return get<PaginatedResponse<SpareMaster>>(`${API_BASE}/spares/?${params}`);
}

export async function createSpareMaster(data: Partial<SpareMaster>): Promise<ApiResponse> {
  return post<ApiResponse>(`${API_BASE}/spares/create/`, data);
}

export async function updateSpareMaster(spareId: number, data: Partial<SpareMaster>): Promise<ApiResponse> {
  return post<ApiResponse>(`${API_BASE}/spares/update/${spareId}/`, data);
}

export async function deleteSpareMaster(spareId: number): Promise<ApiResponse> {
  return del<ApiResponse>(`${API_BASE}/spares/delete/${spareId}/`);
}

// Location Master API
export async function fetchLocationMaster(
  page = 1,
  pageSize = 25,
  search = ''
): Promise<PaginatedResponse<LocationMaster>> {
  const params = new URLSearchParams({
    page: page.toString(),
    page_size: pageSize.toString(),
    ...(search && { search }),
  });
  return get<PaginatedResponse<LocationMaster>>(`${API_BASE}/locations/?${params}`);
}

export async function createLocationMaster(data: Partial<LocationMaster>): Promise<ApiResponse> {
  return post<ApiResponse>(`${API_BASE}/locations/create/`, data);
}

export async function updateLocationMaster(locationId: number, data: Partial<LocationMaster>): Promise<ApiResponse> {
  return post<ApiResponse>(`${API_BASE}/locations/update/${locationId}/`, data);
}

export async function deleteLocationMaster(locationId: number): Promise<ApiResponse> {
  return del<ApiResponse>(`${API_BASE}/locations/delete/${locationId}/`);
}

// Spare Site Map API
export async function fetchSpareSiteMap(
  page = 1,
  pageSize = 25,
  search = '',
  assetCode = '',
  spareCode = '',
  locationCode = ''
): Promise<PaginatedResponse<SpareSiteMap>> {
  const params = new URLSearchParams({
    page: page.toString(),
    page_size: pageSize.toString(),
    ...(search && { search }),
    ...(assetCode && { asset_code: assetCode }),
    ...(spareCode && { spare_code: spareCode }),
    ...(locationCode && { location_code: locationCode }),
  });
  return get<PaginatedResponse<SpareSiteMap>>(`${API_BASE}/spare-site-map/?${params}`);
}

export async function createSpareSiteMap(data: Partial<SpareSiteMap>): Promise<ApiResponse> {
  return post<ApiResponse>(`${API_BASE}/spare-site-map/create/`, data);
}

export async function updateSpareSiteMap(mapId: number, data: Partial<SpareSiteMap>): Promise<ApiResponse> {
  return post<ApiResponse>(`${API_BASE}/spare-site-map/update/${mapId}/`, data);
}

export async function deleteSpareSiteMap(mapId: number): Promise<ApiResponse> {
  return del<ApiResponse>(`${API_BASE}/spare-site-map/delete/${mapId}/`);
}

// Stock Balance API (read-only)
export async function fetchStockBalance(
  page = 1,
  pageSize = 25,
  search = '',
  assetCode = '',
  spareCode = '',
  locationCode = ''
): Promise<PaginatedResponse<StockBalance>> {
  const params = new URLSearchParams({
    page: page.toString(),
    page_size: pageSize.toString(),
    ...(search && { search }),
    ...(assetCode && { asset_code: assetCode }),
    ...(spareCode && { spare_code: spareCode }),
    ...(locationCode && { location_code: locationCode }),
  });
  return get<PaginatedResponse<StockBalance>>(`${API_BASE}/stock-balance/?${params}`);
}

// Stock Entry API
export async function fetchStockEntry(
  page = 1,
  pageSize = 25,
  search = '',
  assetCode = '',
  spareCode = '',
  locationCode = ''
): Promise<PaginatedResponse<StockEntry>> {
  const params = new URLSearchParams({
    page: page.toString(),
    page_size: pageSize.toString(),
    ...(search && { search }),
    ...(assetCode && { asset_code: assetCode }),
    ...(spareCode && { spare_code: spareCode }),
    ...(locationCode && { location_code: locationCode }),
  });
  return get<PaginatedResponse<StockEntry>>(`${API_BASE}/stock-entry/?${params}`);
}

export async function createStockEntry(data: Partial<StockEntry>): Promise<ApiResponse & { balance_after?: number }> {
  return post<ApiResponse & { balance_after?: number }>(`${API_BASE}/stock-entry/create/`, data);
}

// Stock Issue API
export async function fetchStockIssue(
  page = 1,
  pageSize = 25,
  search = '',
  assetCode = '',
  spareCode = '',
  locationCode = '',
  ticketId = ''
): Promise<PaginatedResponse<StockIssue>> {
  const params = new URLSearchParams({
    page: page.toString(),
    page_size: pageSize.toString(),
    ...(search && { search }),
    ...(assetCode && { asset_code: assetCode }),
    ...(spareCode && { spare_code: spareCode }),
    ...(locationCode && { location_code: locationCode }),
    ...(ticketId && { ticket_id: ticketId }),
  });
  return get<PaginatedResponse<StockIssue>>(`${API_BASE}/stock-issue/?${params}`);
}

export async function createStockIssue(data: Partial<StockIssue>): Promise<ApiResponse & { balance_after?: number }> {
  return post<ApiResponse & { balance_after?: number }>(`${API_BASE}/stock-issue/create/`, data);
}
