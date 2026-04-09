import type { YieldDataEntry } from './types';

const YIELD_DATA_ENDPOINT = '/api/yield-data/';

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

export async function fetchYieldData(signal?: AbortSignal): Promise<YieldDataEntry[]> {
  const data = await fetchJson<YieldDataEntry[]>(YIELD_DATA_ENDPOINT, { signal });
  return Array.isArray(data) ? data : [];
}

