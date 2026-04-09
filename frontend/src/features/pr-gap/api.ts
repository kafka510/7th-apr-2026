import type { PrGapData, LossCalculationData } from './types';

const YIELD_DATA_ENDPOINT = '/api/yield-data/';
const LOSS_CALCULATION_ENDPOINT = '/api/loss-calculation-data/';

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

function normalizePrGapData(data: unknown[]): PrGapData[] {
  return data.map((row) => {
    const rowObj = row as Record<string, unknown>;
    const cleaned: Record<string, unknown> = {};
    for (const key in rowObj) {
      const normalizedKey = normalizeKey(key);
      cleaned[normalizedKey] = typeof rowObj[key] === 'string' ? (rowObj[key] as string).trim() : rowObj[key];
    }
    return cleaned as unknown as PrGapData;
  });
}

function normalizeLossCalculationData(data: unknown[]): LossCalculationData[] {
  return data.map((row) => {
    const rowObj = row as Record<string, unknown>;
    const cleaned: Record<string, unknown> = {};
    for (const key in rowObj) {
      const normalizedKey = normalizeKey(key);
      cleaned[normalizedKey] = typeof rowObj[key] === 'string' ? (rowObj[key] as string).trim() : rowObj[key];
    }
    return cleaned as unknown as LossCalculationData;
  });
}

export async function fetchPrGapData(signal?: AbortSignal): Promise<PrGapData[]> {
  try {
    const response = await fetchJson<unknown[]>(YIELD_DATA_ENDPOINT, { signal });
    return normalizePrGapData(response);
  } catch (error) {
    console.error('Error fetching PR Gap data:', error);
    // Return sample data on error
    return [
      {
        asset_no: 'SAMPLE-001',
        pr_gap: 0.05,
        dc_capacity_mw: 10,
        month: '2025-01',
        country: 'Sample',
        portfolio: 'Test',
      },
      {
        asset_no: 'SAMPLE-002',
        pr_gap: -0.03,
        dc_capacity_mw: 15,
        month: '2025-01',
        country: 'Sample',
        portfolio: 'Test',
      },
    ];
  }
}

export async function fetchLossCalculationData(signal?: AbortSignal): Promise<LossCalculationData[]> {
  try {
    const response = await fetchJson<unknown[]>(LOSS_CALCULATION_ENDPOINT, { signal });
    return normalizeLossCalculationData(response);
  } catch (error) {
    console.error('Error fetching Loss Calculation data:', error);
    return [];
  }
}

