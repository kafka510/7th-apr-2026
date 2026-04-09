/**
 * Generation Report API client
 */
import type { GenerationFilters, GenerationReportData } from './types';

const API_BASE = '/api/v1/generation';

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      ...options?.headers,
    },
    credentials: 'include',
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

  const payload = (await response.json().catch(() => null)) as { error?: string; message?: string } | null;
  if (!response.ok) {
    throw new Error(payload?.error || payload?.message || `Request failed (${response.status}): ${response.statusText}`);
  }

  return payload as T;
}

/**
 * Fetch generation report data
 */
export async function fetchGenerationData(filters?: GenerationFilters): Promise<GenerationReportData> {
  const params = new URLSearchParams();
  // Add no_pagination parameter to disable DRF pagination
  params.append('no_pagination', 'true');
  if (filters?.startMonth) {
    params.append('start_month', filters.startMonth);
  }
  if (filters?.endMonth) {
    params.append('end_month', filters.endMonth);
  }

  const queryString = params.toString();
  const url = `${API_BASE}/data?${queryString}`;
  return fetchJson<GenerationReportData>(url);
}

