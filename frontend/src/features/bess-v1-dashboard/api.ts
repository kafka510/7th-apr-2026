import type { BessV1Record, DailyBessRecord } from './types';

const BESS_V1_ENDPOINT = '/api/bess-v1-data/';
const BESS_DATA_ENDPOINT = '/api/bess-data/';

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

export async function fetchBessV1Data(signal?: AbortSignal): Promise<BessV1Record[]> {
  try {
    return await fetchJson<BessV1Record[]>(BESS_V1_ENDPOINT, { signal });
  } catch (error) {
    console.error('Error fetching BESS V1 data:', error);
    return [];
  }
}

export async function fetchBessDailyData(month: string, signal?: AbortSignal): Promise<DailyBessRecord[]> {
  try {
    const url = `${BESS_DATA_ENDPOINT}?month=${encodeURIComponent(month)}`;
    return await fetchJson<DailyBessRecord[]>(url, { signal });
  } catch (error) {
    console.error('Error fetching BESS daily data:', error);
    return [];
  }
}

