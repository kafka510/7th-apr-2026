/**
 * API client for Sales Dashboard feature
 */
import type { SalesData } from './types';

const API_BASE = '/api/v1/sales';

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

export async function fetchSalesData(): Promise<SalesData> {
  const url = `${API_BASE}/sales-data/`;
  console.log('[fetchSalesData] Calling sales endpoint:', url);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const response = await fetchJson<any>(url);
  const responseKeys = Object.keys(response || {});
  console.log('[fetchSalesData] Response keys:', responseKeys);

  // Validate response structure
  if (!response || (!('yieldData' in response) && !('mapData' in response))) {
    console.error('[fetchSalesData] Invalid response structure!');
    console.error('[fetchSalesData] Expected: yieldData and mapData');
    console.error('[fetchSalesData] Got:', responseKeys);
    throw new Error('Invalid sales API response structure');
  }

  const salesData: SalesData = {
    yieldData: response.yieldData || [],
    mapData: response.mapData || [],
  };

  console.log('[fetchSalesData] Loaded data:', {
    yieldDataLength: salesData.yieldData.length,
    mapDataLength: salesData.mapData.length,
  });

  return salesData;
}

