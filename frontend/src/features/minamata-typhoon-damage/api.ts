import type { MinamataData } from './types';

const MINAMATA_DATA_ENDPOINT = '/api/minamata-string-loss-data/';

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

function normalizeMinamataData(data: unknown[]): MinamataData[] {
  if (!Array.isArray(data) || data.length === 0) {
    return [];
  }
  
  return data.map((row) => {
    if (!row || typeof row !== 'object') {
      return null;
    }
    
    const rowObj = row as Record<string, unknown>;
    const cleaned: Record<string, unknown> = {};
    for (const key in rowObj) {
      const normalizedKey = normalizeKey(key);
      const value = rowObj[key];
      // Preserve null/undefined, trim strings, keep numbers as-is
      if (value === null || value === undefined) {
        cleaned[normalizedKey] = value;
      } else if (typeof value === 'string') {
        cleaned[normalizedKey] = value.trim();
      } else {
        cleaned[normalizedKey] = value;
      }
    }
    return cleaned as unknown as MinamataData;
  }).filter((row): row is MinamataData => row !== null);
}

export async function fetchMinamataData(signal?: AbortSignal): Promise<MinamataData[]> {
  try {
    const response = await fetchJson<unknown>(MINAMATA_DATA_ENDPOINT, { signal });
    
    // Handle error response
    if (response && typeof response === 'object' && 'error' in response) {
      console.error('Minamata API error:', (response as { error: string }).error);
      return [];
    }
    
    // Handle both array response and wrapped response
    let dataArray: unknown[] = [];
    if (Array.isArray(response)) {
      dataArray = response;
    } else if (response && typeof response === 'object' && 'data' in response) {
      dataArray = Array.isArray((response as { data: unknown }).data) 
        ? (response as { data: unknown[] }).data 
        : [];
    }
    
    const normalized = normalizeMinamataData(dataArray);
    return normalized;
  } catch (error) {
    console.error('Error fetching Minamata data:', error);
    return [];
  }
}

