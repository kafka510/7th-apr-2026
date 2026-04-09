import type { BackgroundJob, CrontabSpec } from './types';

// CSRF token cache (same pattern as other features)
let csrfTokenCache: string | null = null;
let csrfTokenPromise: Promise<string> | null = null;

async function getCSRFToken(): Promise<string> {
  if (csrfTokenCache) return csrfTokenCache;
  if (csrfTokenPromise) return csrfTokenPromise;

  csrfTokenPromise = fetch('/api/csrf-token/', {
    method: 'GET',
    credentials: 'include',
  })
    .then((r) => r.json())
    .then((data) => {
      if (data.success && data.csrfToken) {
        csrfTokenCache = data.csrfToken as string;
        return csrfTokenCache;
      }
      throw new Error('Failed to get CSRF token');
    })
    .finally(() => {
      // allow refresh on next request if needed
      csrfTokenPromise = null;
    });

  return csrfTokenPromise;
}

async function get<T>(url: string): Promise<T> {
  const res = await fetch(url, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: 'Unknown error' }));
    throw new Error(err.error || `HTTP ${res.status}`);
  }
  return res.json();
}

async function post<T>(url: string, body: unknown): Promise<T> {
  const csrf = await getCSRFToken();
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
    credentials: 'include',
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: 'Unknown error' }));
    throw new Error(err.error || `HTTP ${res.status}`);
  }
  return res.json();
}

async function del<T>(url: string): Promise<T> {
  const csrf = await getCSRFToken();
  const res = await fetch(url, {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
    credentials: 'include',
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: 'Unknown error' }));
    throw new Error(err.error || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function listBackgroundJobs(): Promise<BackgroundJob[]> {
  const data = await get<{ data: BackgroundJob[] }>('/api/background-jobs/');
  return data.data || [];
}

/** Trigger download of all schedules and tasks as JSON (uses export endpoint with attachment). */
export async function downloadAllSchedulesAndTasks(): Promise<void> {
  const res = await fetch('/api/background-jobs/export/', {
    method: 'GET',
    credentials: 'include',
  });
  if (!res.ok) throw new Error(res.statusText || 'Export failed');
  const blob = await res.blob();
  const disposition = res.headers.get('Content-Disposition');
  let filename = 'background-jobs-export.json';
  const match = disposition?.match(/filename="?([^";]+)"?/);
  if (match) filename = match[1].trim();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export interface ImportBackgroundJobsResponse {
  success: boolean;
  created: number;
  updated: number;
  skipped: Array<{ item: string; reason: string }>;
  errors: Array<{ item: string; reason: string }>;
  replace_existing: boolean;
}

export async function importSchedulesFile(
  file: File,
  replaceExisting = false,
): Promise<ImportBackgroundJobsResponse> {
  const csrf = await getCSRFToken();
  const formData = new FormData();
  formData.append('file', file);
  formData.append('replace_existing', replaceExisting ? '1' : '0');

  const res = await fetch('/api/background-jobs/import/', {
    method: 'POST',
    credentials: 'include',
    headers: { 'X-CSRFToken': csrf },
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: 'Unknown error' }));
    throw new Error(err.error || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function listAvailableCeleryTasks(): Promise<string[]> {
  const data = await get<{ data: string[] }>('/api/background-jobs/tasks/');
  return data.data || [];
}

export interface CreateBackgroundJobPayload {
  name: string;
  task: string;
  enabled: boolean;
  queue?: string | null;
  schedule_type: 'interval' | 'crontab';
  interval_seconds?: number;
  crontab?: Partial<CrontabSpec>;
  args?: string;
  kwargs?: string;
  description?: string | null;
}

export async function createBackgroundJob(payload: CreateBackgroundJobPayload): Promise<{ success: boolean; id?: number }> {
  return post('/api/background-jobs/create/', payload);
}

export interface UpdateBackgroundJobPayload extends Partial<CreateBackgroundJobPayload> {
  id: number;
}

export async function updateBackgroundJob(payload: UpdateBackgroundJobPayload): Promise<{ success: boolean }> {
  return post('/api/background-jobs/update/', payload);
}

export async function deleteBackgroundJob(id: number): Promise<{ success: boolean }> {
  return del(`/api/background-jobs/delete/${id}/`);
}

export async function runBackgroundJobNow(
  id: number,
  opts?: { send_completion_email?: boolean; completion_email?: string },
): Promise<{ success: boolean; task_id?: string }> {
  const body: Record<string, unknown> = {};
  if (opts?.send_completion_email) body.send_completion_email = true;
  if (opts?.completion_email?.trim()) body.completion_email = opts.completion_email.trim();
  return post(`/api/background-jobs/run-now/${id}/`, body);
}

export interface RunTaskOnDemandPayload {
  task: string;
  args?: string;
  kwargs?: string;
  queue?: string | null;
  /** For run_solargis_daily_ingest: start date (YYYY-MM-DD). Sent top-level so backend always receives it. */
  date_from?: string;
  /** For run_solargis_daily_ingest: end date (YYYY-MM-DD). Sent top-level so backend always receives it. */
  date_to?: string;
  /** For run_solargis_daily_ingest / compute_daily_kpis_previous_day: restrict to these asset codes. Omit = all. */
  asset_codes?: string[];
  /** Email current user when the task finishes (success / partial / failure). */
  send_completion_email?: boolean;
  /** Optional override recipient instead of request.user.email. */
  completion_email?: string;
}

export async function getSolargisDailyApiCalls(): Promise<{ date: string; total_api_calls: number }> {
  return get('/api/background-jobs/solargis-daily-api-calls/');
}

export async function getSolargisSourceAssets(): Promise<{
  asset_codes: string[];
  all_configured_count?: number;
}> {
  return get('/api/background-jobs/solargis-source-assets/');
}

export async function runTaskOnDemand(payload: RunTaskOnDemandPayload): Promise<{ success: boolean; task_id?: string }> {
  const body: Record<string, unknown> = { task: payload.task };
  if (payload.args !== undefined) body.args = payload.args;
  if (payload.kwargs !== undefined) body.kwargs = payload.kwargs;
  if (payload.queue !== undefined) body.queue = payload.queue || null;
  if (payload.date_from?.trim()) body.date_from = payload.date_from.trim();
  if (payload.date_to?.trim()) body.date_to = payload.date_to.trim();
  if (payload.asset_codes !== undefined && Array.isArray(payload.asset_codes)) {
    body.asset_codes = payload.asset_codes;
  }
  if (payload.send_completion_email) body.send_completion_email = true;
  if (payload.completion_email?.trim()) body.completion_email = payload.completion_email.trim();
  return post('/api/background-jobs/run-task/', body);
}

/** Fusion Solar backfill: list assets for given adapter/account (superuser only). */
export async function getFusionSolarBackfillAssets(params?: {
  adapter_id?: string;
  adapter_account_id?: number | null;
}): Promise<{ asset_codes: string[] }> {
  const search = new URLSearchParams();
  if (params?.adapter_id) search.set('adapter_id', params.adapter_id);
  if (params?.adapter_account_id != null) search.set('adapter_account_id', String(params.adapter_account_id));
  const qs = search.toString();
  const url = `/api/background-jobs/fusion-solar-backfill-assets/${qs ? `?${qs}` : ''}`;
  return get(url);
}

/** Laplace span backfill: list enabled assets (superuser only). */
export async function getLaplaceBackfillAssets(params?: {
  adapter_id?: string;
  adapter_account_id?: number | null;
}): Promise<{ asset_codes: string[] }> {
  const search = new URLSearchParams();
  if (params?.adapter_id) search.set('adapter_id', params.adapter_id);
  if (params?.adapter_account_id != null) search.set('adapter_account_id', String(params.adapter_account_id));
  const qs = search.toString();
  const url = `/api/background-jobs/laplace-backfill-assets/${qs ? `?${qs}` : ''}`;
  return get(url);
}

/** Fusion Solar backfill: start backfill task (superuser only). */
export async function runFusionSolarBackfill(payload: {
  asset_codes: string[];
  date_from: string;
  date_to: string;
  adapter_id?: string;
  adapter_account_id?: number | null;
  send_completion_email?: boolean;
  completion_email?: string;
}): Promise<{ success: boolean; task_id?: string }> {
  return post('/api/background-jobs/fusion-solar-backfill-run/', payload);
}

/** Fusion Solar OEM daily KPI for devTypeId 1 inverters (getDevKpiDay → upsert kpis.oem_daily_product_kwh); no 5-min backfill. */
export async function runFusionSolarOemDailyKpiRun(payload: {
  asset_codes: string[];
  /** Inclusive month range: YYYY-MM (from UI) or YYYY-MM-DD (API accepts both). */
  date_from: string;
  date_to: string;
  adapter_id?: string;
  adapter_account_id?: number | null;
  send_completion_email?: boolean;
  completion_email?: string;
}): Promise<{ success: boolean; task_id?: string }> {
  return post('/api/background-jobs/fusion-solar-oem-daily-kpi-run/', payload);
}

/** Queue ERH invoice PDF parse (async Celery). Requires Energy Revenue Hub feature + same auth as ERH. */
export async function queueErhParseInvoicePdf(files: File[], sessionId?: string): Promise<{ task_id: string }> {
  const csrf = await getCSRFToken();
  const form = new FormData();
  form.append('async', 'true');
  if (sessionId?.trim()) form.append('session_id', sessionId.trim());
  for (const f of files) {
    form.append('files', f);
  }
  const res = await fetch('/energy-revenue-hub/api/parse-invoice-pdf/', {
    method: 'POST',
    credentials: 'include',
    headers: { 'X-CSRFToken': csrf },
    body: form,
  });
  const data = (await res.json().catch(() => ({}))) as { success?: boolean; task_id?: string; message?: string };
  if (!res.ok || !data.success || !data.task_id) {
    throw new Error(data.message || `HTTP ${res.status}`);
  }
  return { task_id: data.task_id };
}

export type ErhTaskStatusPayload = {
  task_id: string;
  state: string;
  ready: boolean;
  successful: boolean;
  result?: Record<string, unknown>;
};

export async function getErhTaskStatus(taskId: string): Promise<ErhTaskStatusPayload> {
  const res = await fetch(`/energy-revenue-hub/api/tasks/${taskId}/status/`, {
    credentials: 'include',
  });
  const data = (await res.json().catch(() => ({}))) as { success?: boolean; message?: string } & ErhTaskStatusPayload;
  if (!res.ok || data.success === false) {
    throw new Error(data.message || `HTTP ${res.status}`);
  }
  return data as ErhTaskStatusPayload;
}

