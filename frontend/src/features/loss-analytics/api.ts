import type { LossEvent, LossEventLog, LossEventFilters, LossEventPage } from './types';

function buildQuery(params: Record<string, string | number | undefined>): string {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== '') {
      searchParams.append(key, String(value));
    }
  });
  const qs = searchParams.toString();
  return qs ? `?${qs}` : '';
}

async function getJSON<T>(url: string): Promise<T> {
  const resp = await fetch(url, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
  });
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    throw new Error(data.error || `HTTP ${resp.status}`);
  }
  return data as T;
}

async function postJSON<T>(url: string, body: unknown): Promise<T> {
  const resp = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(body),
  });
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    throw new Error(data.error || `HTTP ${resp.status}`);
  }
  return data as T;
}

export async function fetchLossEvents(
  filters: LossEventFilters,
  page: number,
  pageSize = 50,
): Promise<LossEventPage> {
  const qs = buildQuery({
    asset_code: filters.assetCode || undefined,
    device_id: filters.deviceId || undefined,
    start_time: filters.startTime || undefined,
    end_time: filters.endTime || undefined,
    page,
    page_size: pageSize,
  });
  const res = await getJSON<{
    success: boolean;
    data: LossEvent[];
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
  }>(`/api/loss/events/${qs}`);

  if (!res.success) {
    throw new Error('Failed to load loss events');
  }

  return {
    events: res.data,
    total: res.total,
    page: res.page,
    pageSize: res.page_size,
    totalPages: res.total_pages,
  };
}

export async function updateLossEventLegitimacy(
  id: number,
  isLegitimate: boolean | null,
): Promise<void> {
  await postJSON('/api/loss/events/update-legitimacy/', {
    id,
    is_legitimate: isLegitimate,
  });
}

export async function fetchLossEventLogs(eventId: number): Promise<LossEventLog[]> {
  const res = await getJSON<{ success: boolean; data: LossEventLog[] }>(
    `/api/loss/events/${eventId}/logs/`,
  );
  if (!res.success) {
    throw new Error('Failed to load event logs');
  }
  return res.data;
}

