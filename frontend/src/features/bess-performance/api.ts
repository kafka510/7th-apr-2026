import type { BESSData } from './types';

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

function normalizeKey(key: string): string {
  return key.trim().toLowerCase().replace(/\s+/g, '_');
}

function normalizeBESSData(data: unknown[]): BESSData[] {
  return data.map((row) => {
    const rowObj = row as Record<string, unknown>;
    const cleaned: Record<string, unknown> = {};
    for (const key in rowObj) {
      const normalizedKey = normalizeKey(key);
      cleaned[normalizedKey] = typeof rowObj[key] === 'string' ? (rowObj[key] as string).trim() : rowObj[key];
    }
    return cleaned as unknown as BESSData;
  });
}

export async function fetchBESSData(signal?: AbortSignal): Promise<BESSData[]> {
  try {
    const response = await fetchJson<unknown[]>(BESS_DATA_ENDPOINT, { signal });
    return normalizeBESSData(response);
  } catch (error) {
    console.error('Error fetching BESS data:', error);
    return [];
  }
}

