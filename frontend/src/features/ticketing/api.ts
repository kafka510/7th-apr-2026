import type {
  BasicOption,
  DeviceOption,
  RecentTicketsParams,
  RecentTicketsResponse,
  TicketAnalyticsParams,
  TicketAnalyticsResponse,
  TicketDashboardFilterParams,
  TicketDashboardFilters,
  TicketDashboardSummary,
  TicketFormData,
  TicketFormOptions,
  TicketListFilters,
  TicketListQueryState,
  TicketListResponse,
  TicketAttachment,
  TicketComment,
  TicketDetail,
  TicketTimelineEntry,
  TicketCategory,
  TicketSubCategory,
  TicketSubCategoryInput,
  LossCategory,
  PMRule,
  PMRuleInput,
  TicketMaterialEntry,
  TicketMaterialInput,
  TicketManpowerEntry,
  TicketManpowerInput,
} from './types';
import { createJSONHeadersWithCSRF, createHeadersWithCSRF } from '@/utils/csrf';

const DASHBOARD_ENDPOINT = '/api/v1/ticketing/dashboard/';
const FILTERS_ENDPOINT = '/api/v1/ticketing/dashboard/filters/';
const RECENT_ENDPOINT = '/api/v1/ticketing/dashboard/recent/';
const ANALYTICS_ENDPOINT = '/api/v1/ticketing/dashboard/analytics/';
const TICKET_LIST_ENDPOINT = '/api/v1/ticketing/tickets/';
const TICKET_DETAIL_ENDPOINT = '/api/v1/ticketing/tickets/';
const ADMIN_ENDPOINT = '/api/v1/ticketing/admin/';

/**
 * Builds headers for requests, including CSRF token for state-changing methods
 */
function buildHeaders(init?: RequestInit): HeadersInit {
  const method = init?.method?.toUpperCase();
  
  // Include CSRF token for POST, PUT, DELETE, PATCH requests
  if (method && ['POST', 'PUT', 'DELETE', 'PATCH'].includes(method)) {
    return createJSONHeadersWithCSRF();
  }
  
  // For GET requests, just return JSON headers without CSRF
  return {
    'Content-Type': 'application/json',
  };
}

async function fetchJson<T>(input: RequestInfo, init?: RequestInit): Promise<T> {
  const response = await fetch(input, {
    credentials: 'same-origin',
    headers: buildHeaders(init),
    ...init,
  });

  const contentType = response.headers.get('content-type') || '';
  const isJson = contentType.includes('application/json');
  if (!isJson) {
    const raw = (await response.text().catch(() => '')).trim();
    const isHtml = raw.toLowerCase().startsWith('<!doctype') || raw.toLowerCase().startsWith('<html');
    if (response.status === 401) throw new Error('Session expired. Please log in again.');
    if (response.status === 403) throw new Error('Access denied or CSRF validation failed. Please refresh and try again.');
    throw new Error(
      isHtml ? 'Server returned an HTML page instead of API JSON. Please refresh and retry.' : (raw || response.statusText)
    );
  }

  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const error = payload as { error?: string; message?: string; detail?: string } | null;
    throw new Error(error?.error || error?.message || error?.detail || response.statusText);
  }
  return payload as T;
}

function buildQuery(params: Record<string, unknown>): string {
  const search = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') {
      return;
    }

    if (Array.isArray(value)) {
      value.forEach((item) => {
        if (item !== undefined && item !== null && `${item}`.trim() !== '') {
          search.append(key, String(item));
        }
      });
      return;
    }

    search.append(key, String(value));
  });

  const queryString = search.toString();
  return queryString ? `?${queryString}` : '';
}

function normaliseFilterParams(filters?: TicketDashboardFilterParams): Record<string, unknown> {
  if (!filters) {
    return {};
  }

  return {
    status: filters.status,
    priority: filters.priority,
    category: filters.category,
    site: filters.site,
    date_from: filters.dateFrom,
    date_to: filters.dateTo,
  };
}

export async function fetchTicketDashboard(
  filters?: TicketDashboardFilterParams,
  signal?: AbortSignal,
): Promise<TicketDashboardSummary> {
  const query = buildQuery(normaliseFilterParams(filters));
  return fetchJson<TicketDashboardSummary>(`${DASHBOARD_ENDPOINT}${query}`, { signal });
}

export async function fetchTicketFilters(signal?: AbortSignal): Promise<TicketDashboardFilters> {
  return fetchJson<TicketDashboardFilters>(FILTERS_ENDPOINT, { signal });
}

export async function fetchRecentTickets(
  params?: RecentTicketsParams,
  signal?: AbortSignal,
): Promise<RecentTicketsResponse> {
  const query = buildQuery({
    ...normaliseFilterParams(params),
    limit: params?.limit,
    filter_by: params?.filterBy,
    filter_value: params?.filterValue,
  });

  return fetchJson<RecentTicketsResponse>(`${RECENT_ENDPOINT}${query}`, { signal });
}

export async function fetchTicketAnalytics(
  params?: TicketAnalyticsParams,
  signal?: AbortSignal,
): Promise<TicketAnalyticsResponse> {
  const query = buildQuery({
    ...normaliseFilterParams(params),
    view_by: params?.viewBy,
    per_page: params?.perPage,
    page: params?.page,
    trend_days: params?.trendDays,
  });

  return fetchJson<TicketAnalyticsResponse>(`${ANALYTICS_ENDPOINT}${query}`, { signal });
}

export async function fetchTicketList(
  params: Partial<TicketListQueryState>,
  signal?: AbortSignal,
  includeFilters = false,
): Promise<TicketListResponse> {
  const query = buildQuery({
    status: params.statuses,
    priority: params.priorities,
    category: params.categories,
    site: params.sites,
    assigned_to: params.assignees,
    asset_number: params.assetNumbers,
    date_from: params.dateFrom,
    date_to: params.dateTo,
    search: params.search,
    sort: params.sort,
    order: params.order,
    page: params.page,
    page_size: params.pageSize,
    include_filters: includeFilters ? '1' : undefined,
  });

  return fetchJson<TicketListResponse>(`${TICKET_LIST_ENDPOINT}${query}`, { signal });
}

export async function fetchTicketListFilters(signal?: AbortSignal): Promise<TicketListFilters> {
  const response = await fetchTicketList(
    {
      statuses: [],
      priorities: [],
      categories: [],
      sites: [],
      assignees: [],
      page: 1,
      pageSize: 1,
    },
    signal,
    true,
  );

  if (!response.filterOptions) {
    throw new Error('Filter options missing from response');
  }

  return response.filterOptions;
}

export async function fetchTicketDetail(ticketId: string, signal?: AbortSignal): Promise<TicketDetail> {
  return fetchJson<TicketDetail>(`${TICKET_DETAIL_ENDPOINT}${ticketId}/`, { signal });
}

export async function fetchTicketTimeline(ticketId: string, signal?: AbortSignal): Promise<TicketTimelineEntry[]> {
  return fetchJson<TicketTimelineEntry[]>(`${TICKET_DETAIL_ENDPOINT}${ticketId}/timeline/`, { signal });
}

export async function fetchTicketComments(ticketId: string, signal?: AbortSignal): Promise<TicketComment[]> {
  return fetchJson<TicketComment[]>(`${TICKET_DETAIL_ENDPOINT}${ticketId}/comments/`, { signal });
}

export async function fetchTicketAttachments(ticketId: string, signal?: AbortSignal): Promise<TicketAttachment[]> {
  return fetchJson<TicketAttachment[]>(`${TICKET_DETAIL_ENDPOINT}${ticketId}/attachments/`, { signal });
}

export async function uploadTicketAttachment(
  ticketId: string,
  file: File,
  signal?: AbortSignal,
): Promise<TicketAttachment> {
  const formData = new FormData();
  formData.append('file', file);

  const headers = createHeadersWithCSRF();

  const response = await fetch(`${TICKET_DETAIL_ENDPOINT}${ticketId}/attachments/`, {
    method: 'POST',
    credentials: 'same-origin',
    headers,
    body: formData,
    signal,
  });

  if (!response.ok) {
    const contentType = response.headers.get('content-type') || '';
    if (!contentType.includes('application/json')) {
      const body = await response.text().catch(() => '');
      throw new Error(body || response.statusText);
    }
    const error = (await response.json().catch(() => null)) as { error?: string; message?: string } | null;
    throw new Error(error?.error || error?.message || response.statusText);
  }

  const contentType = response.headers.get('content-type') || '';
  if (!contentType.includes('application/json')) {
    const raw = (await response.text().catch(() => '')).trim();
    throw new Error(raw || 'Unexpected non-JSON response while uploading attachment.');
  }
  return (await response.json()) as TicketAttachment;
}

export async function fetchTicketMaterials(ticketId: string, signal?: AbortSignal): Promise<TicketMaterialEntry[]> {
  return fetchJson<TicketMaterialEntry[]>(`${TICKET_DETAIL_ENDPOINT}${ticketId}/materials/`, { signal });
}

export async function createTicketMaterial(
  ticketId: string,
  payload: TicketMaterialInput,
  signal?: AbortSignal,
): Promise<TicketMaterialEntry> {
  return fetchJson<TicketMaterialEntry>(`${TICKET_DETAIL_ENDPOINT}${ticketId}/materials/`, {
    method: 'POST',
    body: JSON.stringify(payload),
    signal,
  });
}

export async function updateTicketMaterial(
  ticketId: string,
  materialId: string,
  payload: TicketMaterialInput,
  signal?: AbortSignal,
): Promise<TicketMaterialEntry> {
  return fetchJson<TicketMaterialEntry>(`${TICKET_DETAIL_ENDPOINT}${ticketId}/materials/${materialId}/`, {
    method: 'PUT',
    body: JSON.stringify(payload),
    signal,
  });
}

export async function deleteTicketMaterial(ticketId: string, materialId: string, signal?: AbortSignal): Promise<void> {
  await fetchJson<void>(`${TICKET_DETAIL_ENDPOINT}${ticketId}/materials/${materialId}/`, {
    method: 'DELETE',
    signal,
  });
}

export async function fetchTicketManpower(ticketId: string, signal?: AbortSignal): Promise<TicketManpowerEntry[]> {
  return fetchJson<TicketManpowerEntry[]>(`${TICKET_DETAIL_ENDPOINT}${ticketId}/manpower/`, { signal });
}

export async function createTicketManpower(
  ticketId: string,
  payload: TicketManpowerInput,
  signal?: AbortSignal,
): Promise<TicketManpowerEntry> {
  return fetchJson<TicketManpowerEntry>(`${TICKET_DETAIL_ENDPOINT}${ticketId}/manpower/`, {
    method: 'POST',
    body: JSON.stringify(payload),
    signal,
  });
}

export async function updateTicketManpower(
  ticketId: string,
  manpowerId: string,
  payload: TicketManpowerInput,
  signal?: AbortSignal,
): Promise<TicketManpowerEntry> {
  return fetchJson<TicketManpowerEntry>(`${TICKET_DETAIL_ENDPOINT}${ticketId}/manpower/${manpowerId}/`, {
    method: 'PUT',
    body: JSON.stringify(payload),
    signal,
  });
}

export async function deleteTicketManpower(ticketId: string, manpowerId: string, signal?: AbortSignal): Promise<void> {
  await fetchJson<void>(`${TICKET_DETAIL_ENDPOINT}${ticketId}/manpower/${manpowerId}/`, {
    method: 'DELETE',
    signal,
  });
}

export async function uploadPastedImage(
  ticketId: string,
  imageData: string,
  signal?: AbortSignal,
): Promise<void> {
  const headers = createHeadersWithCSRF({
    'Content-Type': 'application/x-www-form-urlencoded',
  });

  const formData = new URLSearchParams();
  formData.append('pasted_image', imageData);

  const response = await fetch(`/tickets/${ticketId}/attachment/`, {
    method: 'POST',
    credentials: 'same-origin',
    headers,
    body: formData.toString(),
    signal,
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || response.statusText);
  }

  // For pasted images, the Django view redirects, so we just return
  // The parent component should reload attachments
}

const FORM_ENDPOINT = '/api/v1/ticketing/tickets/form/';

export async function fetchTicketFormOptions(signal?: AbortSignal): Promise<TicketFormOptions> {
  return fetchJson<TicketFormOptions>(`${FORM_ENDPOINT}options/`, { signal });
}

export async function fetchDeviceTypes(siteCode: string, signal?: AbortSignal): Promise<string[]> {
  const query = buildQuery({ site: siteCode });
  const response = await fetchJson<{ device_types: string[] }>(`/tickets/api/device-types${query}`, { signal });
  return response.device_types;
}

export async function fetchDeviceOptions(siteCode: string, deviceType?: string, subgroup?: string, location?: string, signal?: AbortSignal): Promise<DeviceOption[]> {
  const query = buildQuery({ site: siteCode, type: deviceType, subgroup, location });
  const response = await fetchJson<{ devices: DeviceOption[] }>(`${FORM_ENDPOINT}devices${query}`, { signal });
  return response.devices;
}

export async function fetchLocationOptions(siteCode: string, signal?: AbortSignal): Promise<BasicOption[]> {
  const query = buildQuery({ site: siteCode });
  const response = await fetchJson<{ locations: BasicOption[] }>(`${FORM_ENDPOINT}locations${query}`, { signal });
  return response.locations;
}

export async function createTicket(data: TicketFormData, signal?: AbortSignal): Promise<{ id: string; ticket_number: string }> {
  return fetchJson<{ id: string; ticket_number: string }>(`${TICKET_LIST_ENDPOINT}create/`, {
    method: 'POST',
    body: JSON.stringify(data),
    signal,
  });
}

export async function updateTicket(ticketId: string, data: Partial<TicketFormData>, signal?: AbortSignal): Promise<{ id: string; ticket_number: string }> {
  return fetchJson<{ id: string; ticket_number: string }>(`${TICKET_LIST_ENDPOINT}${ticketId}/update/`, {
    method: 'PUT',
    body: JSON.stringify(data),
    signal,
  });
}

export async function addTicketComment(ticketId: string, comment: string, isInternal: boolean = false, signal?: AbortSignal): Promise<TicketComment> {
  return fetchJson<TicketComment>(`${TICKET_DETAIL_ENDPOINT}${ticketId}/comments/`, {
    method: 'POST',
    body: JSON.stringify({ comment, is_internal: isInternal }),
    signal,
  });
}

export async function assignTicket(ticketId: string, assignedToId: string | null, notes?: string, signal?: AbortSignal): Promise<TicketDetail> {
  return fetchJson<TicketDetail>(`${TICKET_DETAIL_ENDPOINT}${ticketId}/assign/`, {
    method: 'POST',
    body: JSON.stringify({ assigned_to: assignedToId, notes }),
    signal,
  });
}

export async function updateTicketWatchers(ticketId: string, watcherIds: string[], signal?: AbortSignal): Promise<TicketDetail> {
  return fetchJson<TicketDetail>(`${TICKET_DETAIL_ENDPOINT}${ticketId}/watchers/`, {
    method: 'POST',
    body: JSON.stringify({ watchers: watcherIds }),
    signal,
  });
}

export async function changeTicketStatus(ticketId: string, status: string, notes?: string, signal?: AbortSignal): Promise<TicketDetail> {
  return fetchJson<TicketDetail>(`${TICKET_DETAIL_ENDPOINT}${ticketId}/status/`, {
    method: 'POST',
    body: JSON.stringify({ status, notes }),
    signal,
  });
}

export async function deleteTicket(ticketId: string, signal?: AbortSignal): Promise<{ success: boolean; message: string }> {
  return fetchJson<{ success: boolean; message: string }>(`${TICKET_DETAIL_ENDPOINT}${ticketId}/delete/`, {
    method: 'DELETE',
    signal,
  });
}

export async function bulkDeleteTickets(ticketIds: string[], signal?: AbortSignal): Promise<{ success: boolean; deleted_count: number; message: string }> {
  return fetchJson<{ success: boolean; deleted_count: number; message: string }>(`${TICKET_LIST_ENDPOINT}`, {
    method: 'DELETE',
    body: JSON.stringify({ ticket_ids: ticketIds }),
    signal,
  });
}

// Admin API functions
export async function fetchTicketCategories(signal?: AbortSignal): Promise<{ categories: TicketCategory[] }> {
  return fetchJson<{ categories: TicketCategory[] }>(`${ADMIN_ENDPOINT}ticket-categories/`, { signal });
}

export async function createTicketCategory(data: Partial<TicketCategory>, signal?: AbortSignal): Promise<TicketCategory> {
  return fetchJson<TicketCategory>(`${ADMIN_ENDPOINT}ticket-categories/create/`, {
    method: 'POST',
    body: JSON.stringify(data),
    signal,
  });
}

export async function updateTicketCategory(id: number, data: Partial<TicketCategory>, signal?: AbortSignal): Promise<TicketCategory> {
  return fetchJson<TicketCategory>(`${ADMIN_ENDPOINT}ticket-categories/${id}/`, {
    method: 'PUT',
    body: JSON.stringify(data),
    signal,
  });
}

export async function deleteTicketCategory(id: number, signal?: AbortSignal): Promise<{ success: boolean; message: string }> {
  return fetchJson<{ success: boolean; message: string }>(`${ADMIN_ENDPOINT}ticket-categories/${id}/delete/`, {
    method: 'DELETE',
    signal,
  });
}

export async function fetchTicketSubCategories(
  signal?: AbortSignal,
  categoryId?: number,
): Promise<{ subCategories: TicketSubCategory[] }> {
  const query = buildQuery({ category: categoryId });
  return fetchJson<{ subCategories: TicketSubCategory[] }>(`${ADMIN_ENDPOINT}ticket-sub-categories/${query}`, { signal });
}

export async function createTicketSubCategory(
  data: TicketSubCategoryInput,
  signal?: AbortSignal,
): Promise<TicketSubCategory> {
  return fetchJson<TicketSubCategory>(`${ADMIN_ENDPOINT}ticket-sub-categories/create/`, {
    method: 'POST',
    body: JSON.stringify(data),
    signal,
  });
}

export async function updateTicketSubCategory(
  id: number,
  data: Partial<TicketSubCategoryInput>,
  signal?: AbortSignal,
): Promise<TicketSubCategory> {
  return fetchJson<TicketSubCategory>(`${ADMIN_ENDPOINT}ticket-sub-categories/${id}/`, {
    method: 'PUT',
    body: JSON.stringify(data),
    signal,
  });
}

export async function deleteTicketSubCategory(id: number, signal?: AbortSignal): Promise<{ success: boolean; message: string }> {
  return fetchJson<{ success: boolean; message: string }>(`${ADMIN_ENDPOINT}ticket-sub-categories/${id}/delete/`, {
    method: 'DELETE',
    signal,
  });
}

export async function fetchLossCategories(signal?: AbortSignal): Promise<{ categories: LossCategory[] }> {
  return fetchJson<{ categories: LossCategory[] }>(`${ADMIN_ENDPOINT}loss-categories/`, { signal });
}

export async function createLossCategory(data: Partial<LossCategory>, signal?: AbortSignal): Promise<LossCategory> {
  return fetchJson<LossCategory>(`${ADMIN_ENDPOINT}loss-categories/create/`, {
    method: 'POST',
    body: JSON.stringify(data),
    signal,
  });
}

export async function updateLossCategory(id: number, data: Partial<LossCategory>, signal?: AbortSignal): Promise<LossCategory> {
  return fetchJson<LossCategory>(`${ADMIN_ENDPOINT}loss-categories/${id}/`, {
    method: 'PUT',
    body: JSON.stringify(data),
    signal,
  });
}

export async function deleteLossCategory(id: number, signal?: AbortSignal): Promise<{ success: boolean; message: string }> {
  return fetchJson<{ success: boolean; message: string }>(`${ADMIN_ENDPOINT}loss-categories/${id}/delete/`, {
    method: 'DELETE',
    signal,
  });
}

export async function fetchPMRules(signal?: AbortSignal): Promise<{ rules: PMRule[] }> {
  return fetchJson<{ rules: PMRule[] }>(`${ADMIN_ENDPOINT}pm-rules/`, { signal });
}

export async function fetchPMRule(id: number, signal?: AbortSignal): Promise<PMRule> {
  return fetchJson<PMRule>(`${ADMIN_ENDPOINT}pm-rules/${id}/`, { signal });
}

export async function createPMRule(data: Partial<PMRuleInput>, signal?: AbortSignal): Promise<PMRule> {
  return fetchJson<PMRule>(`${ADMIN_ENDPOINT}pm-rules/create/`, {
    method: 'POST',
    body: JSON.stringify(data),
    signal,
  });
}

export async function updatePMRule(id: number, data: Partial<PMRuleInput>, signal?: AbortSignal): Promise<PMRule> {
  return fetchJson<PMRule>(`${ADMIN_ENDPOINT}pm-rules/${id}/update/`, {
    method: 'PUT',
    body: JSON.stringify(data),
    signal,
  });
}

export async function deletePMRule(id: number, signal?: AbortSignal): Promise<{ success: boolean; message: string }> {
  return fetchJson<{ success: boolean; message: string }>(`${ADMIN_ENDPOINT}pm-rules/${id}/delete/`, {
    method: 'DELETE',
    signal,
  });
}

export async function togglePMRule(id: number, signal?: AbortSignal): Promise<{ success: boolean; message: string; is_active: boolean }> {
  return fetchJson<{ success: boolean; message: string; is_active: boolean }>(`${ADMIN_ENDPOINT}pm-rules/${id}/toggle/`, {
    method: 'POST',
    signal,
  });
}

export async function triggerPMProcessing(signal?: AbortSignal): Promise<{ success: boolean; message: string; task_id: string }> {
  return fetchJson<{ success: boolean; message: string; task_id: string }>(`${ADMIN_ENDPOINT}pm-rules/trigger/`, {
    method: 'POST',
    signal,
  });
}

