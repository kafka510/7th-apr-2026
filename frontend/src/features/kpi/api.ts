import type { KpiMetric } from './types';

type MetricsApiResponse =
  | { results?: KpiMetric[]; data?: KpiMetric[]; count?: number }
  | KpiMetric[];

const METRICS_ENDPOINT = '/api/v1/kpi/metrics/';

async function fetchJson<T>(input: RequestInfo, init?: RequestInit): Promise<T> {
  const response = await fetch(input, {
    credentials: 'same-origin',
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
      isHtml
        ? 'Server returned an HTML page instead of API JSON. Please refresh and retry.'
        : raw || `Request failed (${response.status}): ${response.statusText}`
    );
  }

  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const error = payload as { error?: string; message?: string } | null;
    throw new Error(
      error?.error || error?.message || `Request failed (${response.status}): ${response.statusText}`
    );
  }

  return payload as T;
}

function normaliseMetricsResponse(payload: MetricsApiResponse): KpiMetric[] {
  if (Array.isArray(payload)) {
    return payload;
  }

  if (Array.isArray(payload.results)) {
    return payload.results;
  }

  if (Array.isArray(payload.data)) {
    return payload.data;
  }

  return [];
}

export async function fetchKpiMetrics(signal?: AbortSignal): Promise<KpiMetric[]> {
  const data = await fetchJson<MetricsApiResponse>(METRICS_ENDPOINT, { signal });
  return normaliseMetricsResponse(data);
}

export type YieldDataEntry = {
  month: string;
  country: string;
  portfolio: string;
  assetno: string;
  dc_capacity_mw: number;
  ic_approved_budget: number;
  expected_budget: number;
  weather_loss_or_gain: number;
  grid_curtailment: number;
  grid_outage: number;
  operation_budget: number;
  breakdown_loss: number;
  unclassified_loss: number;
  actual_generation: number;
  string_failure?: number;
  inverter_failure?: number;
  mv_failure?: number;
  hv_failure?: number;
  expected_pr: number;
  actual_pr: number;
  budgeted_irradiation?: number;
  actual_irradiation?: number;
};

const YIELD_DATA_ENDPOINT = '/api/yield-data/';

export async function fetchYieldData(signal?: AbortSignal): Promise<YieldDataEntry[]> {
  const data = await fetchJson<YieldDataEntry[]>(YIELD_DATA_ENDPOINT, { signal });
  return Array.isArray(data) ? data : [];
}

