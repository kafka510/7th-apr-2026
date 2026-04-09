import { createHeadersWithCSRF, createJSONHeadersWithCSRF, getCSRFToken } from '@/utils/csrf';

type ApiSuccess<T> = { success: true } & T;
type ApiError = { success: false; error?: string; message?: string };
type ApiResponse<T> = ApiSuccess<T> | ApiError;

export type BillingSession = {
  id: string;
  country: string;
  portfolio: string;
  asset_list: Array<string | { name?: string; asset_name?: string; code?: string; asset_code?: string }>;
  invoice_template_id?: string;
  /** Merged into invoice snapshot on PDF generate (e.g. gst_rate, notes). */
  billing_extras_json?: Record<string, unknown>;
  /** Normalized profile key (e.g. sg_ppa_maiora). */
  billing_contract_type?: string;
  /** First day of month (YYYY-MM-DD) for the intended billing month. */
  billing_month?: string | null;
  session_label?: string;
  start_date: string | null;
  end_date: string | null;
  status: string;
  created_by: string;
  created_at: string;
  updated_at: string;
};

async function parse<T>(res: Response): Promise<ApiResponse<T>> {
  const data = (await res.json().catch(() => ({}))) as ApiResponse<T>;
  if (!res.ok) {
    return {
      success: false,
      error: (data as ApiError).error || `HTTP_${res.status}`,
      message: (data as ApiError).message || `Request failed (${res.status})`,
    };
  }
  return data;
}

export type SessionListFilters = {
  billing_contract_type?: string;
  /** YYYY-MM */
  billing_month?: string;
  country?: string;
  portfolio?: string;
  status?: string;
  q?: string;
  limit?: number;
};

function sessionsQueryString(filters?: SessionListFilters) {
  if (!filters) return '';
  const p = new URLSearchParams();
  if (filters.billing_contract_type) p.set('billing_contract_type', filters.billing_contract_type);
  if (filters.billing_month) p.set('billing_month', filters.billing_month);
  if (filters.country) p.set('country', filters.country);
  if (filters.portfolio) p.set('portfolio', filters.portfolio);
  if (filters.status) p.set('status', filters.status);
  if (filters.q) p.set('q', filters.q);
  if (filters.limit != null) p.set('limit', String(filters.limit));
  const s = p.toString();
  return s ? `?${s}` : '';
}

export async function listSessions(filters?: SessionListFilters) {
  const res = await fetch(`/energy-revenue-hub/api/sessions/${sessionsQueryString(filters)}`, {
    credentials: 'same-origin',
  });
  return parse<{ sessions: BillingSession[] }>(res);
}

export async function fetchContractProfileKeys() {
  const res = await fetch('/energy-revenue-hub/api/contract-profile-keys/', {
    credentials: 'same-origin',
  });
  return parse<{ contract_profile_keys: string[] }>(res);
}

export type EligibleBillingAsset = {
  asset_code: string;
  asset_name: string;
  portfolio: string;
  country: string;
  contract_type: string;
};

export async function fetchEligibleBillingAssets(params: {
  country: string;
  contract_type: string;
  /** YYYY-MM; when set, contracts must overlap this month. */
  billing_month?: string;
}) {
  const p = new URLSearchParams();
  p.set('country', params.country);
  p.set('contract_type', params.contract_type);
  if (params.billing_month) p.set('billing_month', params.billing_month);
  const res = await fetch(`/energy-revenue-hub/api/eligible-billing-assets/?${p.toString()}`, {
    credentials: 'same-origin',
  });
  return parse<{ assets: EligibleBillingAsset[] }>(res);
}

export async function createSession(payload: {
  country: string;
  /** Derived on the server from AssetList when omitted. */
  portfolio?: string;
  assets?: string[];
  /** Optional when billing_month is sent — server defaults period to that calendar month. */
  start_date?: string;
  end_date?: string;
  billing_contract_type?: string;
  /** YYYY-MM or ISO date; first month of period is used. */
  billing_month?: string;
  session_label?: string;
}) {
  const res = await fetch('/energy-revenue-hub/api/sessions/create/', {
    method: 'POST',
    headers: createJSONHeadersWithCSRF(),
    credentials: 'same-origin',
    body: JSON.stringify(payload),
  });
  return parse<{ session: BillingSession }>(res);
}

export async function getSessionDetail(sessionId: string) {
  const res = await fetch(`/energy-revenue-hub/api/sessions/${sessionId}/`, {
    credentials: 'same-origin',
  });
  return parse<{
    session: BillingSession;
    line_items: Array<Record<string, unknown>>;
    parsed_invoices: Array<Record<string, unknown>>;
    generated_invoices: Array<Record<string, unknown>>;
    utility_invoices: Array<Record<string, unknown>>;
    payments: Array<Record<string, unknown>>;
    meter_readings: Array<Record<string, unknown>>;
    asset_generation: Array<Record<string, unknown>>;
    penalties: Array<Record<string, unknown>>;
    adjustments: Array<Record<string, unknown>>;
    billing_audit_logs: Array<Record<string, unknown>>;
    upload_summary?: Array<Record<string, unknown>>;
    conflicts?: Array<Record<string, unknown>>;
    generation_blockers?: Array<Record<string, unknown>>;
    invoice_generation_allowed?: boolean;
    invoice_generation_blockers?: Array<Record<string, unknown>>;
    coverage_summary?: Record<string, unknown>;
    pending_assets?: Array<Record<string, unknown>>;
    can_delete: boolean;
    can_unfreeze_billing_lines?: boolean;
  }>(res);
}

export async function patchBillingSession(
  sessionId: string,
  payload: {
    invoice_template_id?: string;
    billing_extras_json?: Record<string, unknown>;
    billing_contract_type?: string;
    billing_month?: string | null;
    session_label?: string;
  }
) {
  const res = await fetch(`/energy-revenue-hub/api/sessions/${sessionId}/`, {
    method: 'PATCH',
    headers: createJSONHeadersWithCSRF(),
    credentials: 'same-origin',
    body: JSON.stringify(payload),
  });
  return parse<{ session: BillingSession }>(res);
}

export async function addAssetToBillingSession(
  sessionId: string,
  payload: { asset_code: string; asset_name?: string }
) {
  const res = await fetch(`/energy-revenue-hub/api/sessions/${sessionId}/add-asset/`, {
    method: 'POST',
    headers: createJSONHeadersWithCSRF(),
    credentials: 'same-origin',
    body: JSON.stringify(payload),
  });
  return parse<{ session: BillingSession; added: string }>(res);
}

export async function unfreezeBillingLines(
  sessionId: string,
  opts?: { reason?: string; lineItemId?: string }
) {
  if (!getCSRFToken()) {
    return {
      success: false as const,
      error: 'CSRF_MISSING',
      message: 'Security token missing. Reload the page and try again.',
    };
  }
  const body: Record<string, string> = { reason: opts?.reason ?? '' };
  if (opts?.lineItemId) {
    body.line_item_id = opts.lineItemId;
  }
  const res = await fetch(`/energy-revenue-hub/api/sessions/${sessionId}/unfreeze-lines/`, {
    method: 'POST',
    headers: createJSONHeadersWithCSRF(),
    credentials: 'same-origin',
    body: JSON.stringify(body),
  });
  return parse<{ status: string }>(res);
}

export async function generateBillingTable(sessionId: string, exportKwh: number) {
  const body: Record<string, unknown> = { export_kwh: exportKwh };
  const res = await fetch(`/energy-revenue-hub/api/sessions/${sessionId}/generate-table/`, {
    method: 'POST',
    headers: createJSONHeadersWithCSRF(),
    credentials: 'same-origin',
    body: JSON.stringify(body),
  });
  return parse<{
    line_items: Array<Record<string, unknown>>;
    status: string;
  }>(res);
}

export async function generateBillingTableAsync(sessionId: string, exportKwh: number) {
  const body: Record<string, unknown> = { export_kwh: exportKwh, async: true };
  const res = await fetch(`/energy-revenue-hub/api/sessions/${sessionId}/generate-table/`, {
    method: 'POST',
    headers: createJSONHeadersWithCSRF(),
    credentials: 'same-origin',
    body: JSON.stringify(body),
  });
  return parse<{ task_id: string; status: string }>(res);
}

export async function recalculateBillingLines(sessionId: string, exportKwh: number) {
  const body: Record<string, unknown> = { export_kwh: exportKwh };
  const res = await fetch(`/energy-revenue-hub/api/sessions/${sessionId}/recalculate-lines/`, {
    method: 'POST',
    headers: createJSONHeadersWithCSRF(),
    credentials: 'same-origin',
    body: JSON.stringify(body),
  });
  return parse<{
    line_items: Array<Record<string, unknown>>;
    status: string;
  }>(res);
}

export async function recalculateBillingLinesAsync(sessionId: string, exportKwh: number) {
  const body: Record<string, unknown> = { export_kwh: exportKwh, async: true };
  const res = await fetch(`/energy-revenue-hub/api/sessions/${sessionId}/recalculate-lines/`, {
    method: 'POST',
    headers: createJSONHeadersWithCSRF(),
    credentials: 'same-origin',
    body: JSON.stringify(body),
  });
  return parse<{ task_id: string; status: string }>(res);
}

export async function generateInvoice(sessionId: string) {
  const res = await fetch(`/energy-revenue-hub/api/sessions/${sessionId}/generate-invoice/`, {
    method: 'POST',
    headers: createJSONHeadersWithCSRF(),
    credentials: 'same-origin',
    body: JSON.stringify({}),
  });
  return parse<{ generated_invoice: Record<string, unknown>; status: string }>(res);
}

export async function generateInvoiceAsync(sessionId: string) {
  const res = await fetch(`/energy-revenue-hub/api/sessions/${sessionId}/generate-invoice/`, {
    method: 'POST',
    headers: createJSONHeadersWithCSRF(),
    credentials: 'same-origin',
    body: JSON.stringify({ async: true }),
  });
  return parse<{ task_id: string; status: string }>(res);
}

/** Default `async: true` — PDF work runs on Celery; use `async: false` only for debugging or scripts. */
export async function generateLineItemInvoice(
  lineItemId: string,
  options?: { async?: boolean },
) {
  const runAsync = options?.async ?? true;
  const res = await fetch(`/energy-revenue-hub/api/line-items/${lineItemId}/generate-invoice/`, {
    method: 'POST',
    headers: createJSONHeadersWithCSRF(),
    credentials: 'same-origin',
    body: JSON.stringify({ async: runAsync }),
  });
  return parse<
    | { task_id: string; status: 'queued' }
    | {
        line_item_id: string;
        generated_invoices: Array<Record<string, unknown>>;
        failed_invoices: Array<Record<string, unknown>>;
        status: string;
        task_id: string;
      }
  >(res);
}

export async function postInvoice(sessionId: string) {
  const res = await fetch(`/energy-revenue-hub/api/sessions/${sessionId}/post-invoice/`, {
    method: 'POST',
    headers: createJSONHeadersWithCSRF(),
    credentials: 'same-origin',
    body: JSON.stringify({}),
  });
  return parse<{ status: string }>(res);
}

export async function parseInvoicePdf(files: FileList | File[], sessionId?: string) {
  const form = new FormData();
  const list = Array.from(files);
  if (list.length === 1) {
    form.append('file', list[0]);
  } else {
    list.forEach((f) => form.append('files', f));
  }
  if (sessionId) form.append('session_id', sessionId);

  const res = await fetch('/energy-revenue-hub/api/parse-invoice-pdf/', {
    method: 'POST',
    headers: createHeadersWithCSRF(),
    credentials: 'same-origin',
    body: form,
  });
  return parse<{ results: Array<Record<string, unknown>>; created_parsed_invoice_ids: string[] }>(res);
}

export async function parseInvoicePdfAsync(files: FileList | File[], sessionId?: string) {
  const form = new FormData();
  const list = Array.from(files);
  if (list.length === 1) {
    form.append('file', list[0]);
  } else {
    list.forEach((f) => form.append('files', f));
  }
  if (sessionId) form.append('session_id', sessionId);
  form.append('async', 'true');

  const res = await fetch('/energy-revenue-hub/api/parse-invoice-pdf/', {
    method: 'POST',
    headers: createHeadersWithCSRF(),
    credentials: 'same-origin',
    body: form,
  });
  return parse<{
    task_id: string;
    task_ids?: string[];
    status: string;
    estimated_seconds?: number;
    estimated_seconds_min?: number;
    estimated_seconds_max?: number;
    estimated_workers_used?: number;
    estimated_seconds_per_file?: number;
    file_count?: number;
    accepted_file_count?: number;
    rejected_file_count?: number;
    security_rejections?: Array<{
      original_filename?: string;
      security_reason_code?: string;
      security_reason_message?: string;
    }>;
  }>(res);
}

export async function parseInvoicePdfAsyncWithUploadProgress(
  files: FileList | File[],
  sessionId: string | undefined,
  onProgress?: (loaded: number, total: number) => void
) {
  const form = new FormData();
  const list = Array.from(files);
  if (list.length === 1) {
    form.append('file', list[0]);
  } else {
    list.forEach((f) => form.append('files', f));
  }
  if (sessionId) form.append('session_id', sessionId);
  form.append('async', 'true');

  return new Promise<
    ApiResponse<{
      task_id: string;
      task_ids?: string[];
      status: string;
      estimated_seconds?: number;
      estimated_seconds_min?: number;
      estimated_seconds_max?: number;
      estimated_workers_used?: number;
      estimated_seconds_per_file?: number;
      file_count?: number;
      accepted_file_count?: number;
      rejected_file_count?: number;
      security_rejections?: Array<{
        original_filename?: string;
        security_reason_code?: string;
        security_reason_message?: string;
      }>;
    }>
  >((resolve) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/energy-revenue-hub/api/parse-invoice-pdf/', true);
    xhr.withCredentials = true;
    const csrf = getCSRFToken();
    if (csrf) xhr.setRequestHeader('X-CSRFToken', csrf);
    xhr.upload.onprogress = (evt) => {
      if (evt.lengthComputable) onProgress?.(evt.loaded, evt.total);
    };
    xhr.onerror = () => resolve({ success: false, error: 'NETWORK_ERROR', message: 'Upload failed due to network error.' });
    xhr.onload = () => {
      let payload: ApiResponse<{
        task_id: string;
        task_ids?: string[];
        status: string;
        estimated_seconds?: number;
        estimated_seconds_min?: number;
        estimated_seconds_max?: number;
        estimated_workers_used?: number;
        estimated_seconds_per_file?: number;
        file_count?: number;
        accepted_file_count?: number;
        rejected_file_count?: number;
        security_rejections?: Array<{
          original_filename?: string;
          security_reason_code?: string;
          security_reason_message?: string;
        }>;
      }> = {
        success: false,
        error: `HTTP_${xhr.status || 0}`,
        message: `Request failed (${xhr.status || 0})`,
      };
      try {
        payload = JSON.parse(xhr.responseText || '{}') as ApiResponse<{
          task_id: string;
          task_ids?: string[];
          status: string;
          estimated_seconds?: number;
          estimated_seconds_min?: number;
          estimated_seconds_max?: number;
          estimated_workers_used?: number;
          estimated_seconds_per_file?: number;
          file_count?: number;
          accepted_file_count?: number;
          rejected_file_count?: number;
          security_rejections?: Array<{
            original_filename?: string;
            security_reason_code?: string;
            security_reason_message?: string;
          }>;
        }>;
      } catch {
        // keep fallback payload
      }
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(payload);
      } else {
        resolve({
          success: false,
          error: (payload as ApiError).error || `HTTP_${xhr.status}`,
          message: (payload as ApiError).message || `Request failed (${xhr.status})`,
        });
      }
    };
    xhr.send(form);
  });
}

export async function getTaskStatus(taskId: string) {
  const res = await fetch(`/energy-revenue-hub/api/tasks/${taskId}/status/`, {
    credentials: 'same-origin',
  });
  return parse<{
    task_id: string;
    state: string;
    ready: boolean;
    successful: boolean;
    result?: Record<string, unknown>;
  }>(res);
}

export async function getSharepointUploadHealth() {
  const res = await fetch('/energy-revenue-hub/api/sharepoint/health/', {
    credentials: 'same-origin',
  });
  return parse<{
    generated: { total: number; on_sharepoint: number; failed: number };
    utility: { uploaded: number; failed: number };
  }>(res);
}

export async function testSharepointConnection(payload?: {
  country?: string;
  asset_name?: string;
  invoice_number?: string;
}) {
  const res = await fetch('/energy-revenue-hub/api/sharepoint/test/', {
    method: 'POST',
    headers: createJSONHeadersWithCSRF(),
    credentials: 'same-origin',
    body: JSON.stringify(payload || {}),
  });
  return parse<{
    message: string;
    upload_mode: string;
    sharepoint_remote_path: string;
    details: Record<string, unknown>;
  }>(res);
}

export async function createUtilityInvoice(sessionId: string, payload: Record<string, unknown>) {
  const res = await fetch(`/energy-revenue-hub/api/sessions/${sessionId}/utility-invoices/`, {
    method: 'POST',
    headers: createJSONHeadersWithCSRF(),
    credentials: 'same-origin',
    body: JSON.stringify(payload),
  });
  return parse<{ utility_invoice_id: string }>(res);
}

export async function updateUtilityInvoice(invoiceId: string, payload: Record<string, unknown>) {
  const res = await fetch(`/energy-revenue-hub/api/utility-invoices/${invoiceId}/`, {
    method: 'PATCH',
    headers: createJSONHeadersWithCSRF(),
    credentials: 'same-origin',
    body: JSON.stringify(payload),
  });
  return parse<{ utility_invoice_id: string; is_frozen: boolean }>(res);
}

/** Full utility row including raw_text / parse JSON (not included in session list payloads). */
export async function fetchUtilityInvoiceDetail(invoiceId: string) {
  const res = await fetch(`/energy-revenue-hub/api/utility-invoices/${invoiceId}/`, {
    method: 'GET',
    credentials: 'same-origin',
  });
  return parse<{ utility_invoice: Record<string, unknown> }>(res);
}

export async function passUtilityInvoice(invoiceId: string) {
  const res = await fetch(`/energy-revenue-hub/api/utility-invoices/${invoiceId}/parse-pass/`, {
    method: 'POST',
    headers: createJSONHeadersWithCSRF(),
    credentials: 'same-origin',
    body: JSON.stringify({}),
  });
  return parse<{ utility_invoice_id: string; parse_review_status: string }>(res);
}

export async function freezeAllUtilityInvoices(sessionId: string) {
  const res = await fetch(`/energy-revenue-hub/api/sessions/${sessionId}/utility-invoices/freeze-all/`, {
    method: 'POST',
    headers: createJSONHeadersWithCSRF(),
    credentials: 'same-origin',
    body: JSON.stringify({}),
  });
  return parse<{ frozen_rows: number }>(res);
}

export async function resolveBillingInvoicePdfMerge(
  billingInvoicePdfId: string,
  action: 'apply' | 'reject'
) {
  const res = await fetch(`/energy-revenue-hub/api/billing-invoice-pdfs/${billingInvoicePdfId}/resolve-merge/`, {
    method: 'POST',
    headers: createJSONHeadersWithCSRF(),
    credentials: 'same-origin',
    body: JSON.stringify({ action }),
  });
  return parse<{ status: string; action: string; billing_invoice_pdf_id: string; utility_invoice_id: string }>(res);
}

export async function createPayment(sessionId: string, payload: Record<string, unknown>) {
  const res = await fetch(`/energy-revenue-hub/api/sessions/${sessionId}/payments/`, {
    method: 'POST',
    headers: createJSONHeadersWithCSRF(),
    credentials: 'same-origin',
    body: JSON.stringify(payload),
  });
  return parse<{ payment_id: string }>(res);
}

export async function createMeterReading(sessionId: string, payload: Record<string, unknown>) {
  const res = await fetch(`/energy-revenue-hub/api/sessions/${sessionId}/meter-readings/`, {
    method: 'POST',
    headers: createJSONHeadersWithCSRF(),
    credentials: 'same-origin',
    body: JSON.stringify(payload),
  });
  return parse<{ meter_reading_id: string }>(res);
}

export async function createAssetGeneration(sessionId: string, payload: Record<string, unknown>) {
  const res = await fetch(`/energy-revenue-hub/api/sessions/${sessionId}/asset-generation/`, {
    method: 'POST',
    headers: createJSONHeadersWithCSRF(),
    credentials: 'same-origin',
    body: JSON.stringify(payload),
  });
  return parse<{ asset_generation_id: string }>(res);
}

export async function createPenalty(sessionId: string, payload: Record<string, unknown>) {
  const res = await fetch(`/energy-revenue-hub/api/sessions/${sessionId}/penalties/`, {
    method: 'POST',
    headers: createJSONHeadersWithCSRF(),
    credentials: 'same-origin',
    body: JSON.stringify(payload),
  });
  return parse<{ penalty_id: string }>(res);
}

export async function createAdjustment(sessionId: string, payload: Record<string, unknown>) {
  const res = await fetch(`/energy-revenue-hub/api/sessions/${sessionId}/adjustments/`, {
    method: 'POST',
    headers: createJSONHeadersWithCSRF(),
    credentials: 'same-origin',
    body: JSON.stringify(payload),
  });
  return parse<{ adjustment_id: string }>(res);
}

export async function deleteUtilityInvoice(invoiceId: string) {
  const res = await fetch(`/energy-revenue-hub/api/utility-invoices/${invoiceId}/delete/`, {
    method: 'DELETE',
    headers: createHeadersWithCSRF(),
    credentials: 'same-origin',
  });
  return parse<{ deleted: boolean }>(res);
}

export async function deletePayment(paymentId: string) {
  const res = await fetch(`/energy-revenue-hub/api/payments/${paymentId}/delete/`, {
    method: 'DELETE',
    headers: createHeadersWithCSRF(),
    credentials: 'same-origin',
  });
  return parse<{ deleted: boolean }>(res);
}

export async function deleteMeterReading(readingId: string) {
  const res = await fetch(`/energy-revenue-hub/api/meter-readings/${readingId}/delete/`, {
    method: 'DELETE',
    headers: createHeadersWithCSRF(),
    credentials: 'same-origin',
  });
  return parse<{ deleted: boolean }>(res);
}

export async function deleteAssetGeneration(generationId: string) {
  const res = await fetch(`/energy-revenue-hub/api/asset-generation/${generationId}/delete/`, {
    method: 'DELETE',
    headers: createHeadersWithCSRF(),
    credentials: 'same-origin',
  });
  return parse<{ deleted: boolean }>(res);
}

export async function deletePenalty(penaltyId: string) {
  const res = await fetch(`/energy-revenue-hub/api/penalties/${penaltyId}/delete/`, {
    method: 'DELETE',
    headers: createHeadersWithCSRF(),
    credentials: 'same-origin',
  });
  return parse<{ deleted: boolean }>(res);
}

export async function deleteAdjustment(adjustmentId: string) {
  const res = await fetch(`/energy-revenue-hub/api/adjustments/${adjustmentId}/delete/`, {
    method: 'DELETE',
    headers: createHeadersWithCSRF(),
    credentials: 'same-origin',
  });
  return parse<{ deleted: boolean }>(res);
}

export async function deleteParsedInvoice(parsedInvoiceId: string) {
  const res = await fetch(`/energy-revenue-hub/api/parsed-invoices/${parsedInvoiceId}/delete/`, {
    method: 'DELETE',
    headers: createHeadersWithCSRF(),
    credentials: 'same-origin',
  });
  return parse<{ deleted: boolean }>(res);
}

export async function deleteBillingLineItem(lineItemId: string) {
  const res = await fetch(`/energy-revenue-hub/api/line-items/${lineItemId}/delete/`, {
    method: 'DELETE',
    headers: createHeadersWithCSRF(),
    credentials: 'same-origin',
  });
  return parse<{ deleted: boolean }>(res);
}

export async function deleteGeneratedInvoice(generatedInvoiceId: string) {
  const res = await fetch(`/energy-revenue-hub/api/generated-invoices/${generatedInvoiceId}/delete/`, {
    method: 'DELETE',
    headers: createHeadersWithCSRF(),
    credentials: 'same-origin',
  });
  return parse<{ deleted: boolean }>(res);
}
