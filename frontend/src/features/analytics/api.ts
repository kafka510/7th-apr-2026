/**
 * API client for Analytics Dashboard
 */

import type {
  Asset,
  Device,
  MeasurementPointsByDeviceType,
  MeasurementPointsDiagnostics,
  AnalyticsDataResponse,
} from './types';

const API_BASE = '/api/analytics';

async function parseJsonResponse<T>(response: Response): Promise<T> {
  const contentType = response.headers.get('content-type') || '';
  const isJson = contentType.includes('application/json');

  if (!isJson) {
    const raw = (await response.text().catch(() => '')).trim();
    const isHtml = raw.toLowerCase().startsWith('<!doctype') || raw.toLowerCase().startsWith('<html');
    if (response.status === 401) {
      throw new Error('Session expired. Please log in again.');
    }
    if (response.status === 403) {
      throw new Error('Access denied or CSRF validation failed. Please refresh and try again.');
    }
    throw new Error(
      isHtml
        ? 'Server returned an HTML page instead of API JSON. Please refresh and retry.'
        : raw || `Unexpected non-JSON response (status ${response.status}).`
    );
  }

  const payload = (await response.json().catch(() => null)) as
    | { success?: boolean; error?: string; message?: string }
    | null;

  if (!response.ok) {
    throw new Error(
      payload?.error ||
        payload?.message ||
        (response.status === 401
          ? 'Session expired. Please log in again.'
          : response.status === 403
            ? 'Access denied or CSRF validation failed. Please refresh and try again.'
            : `HTTP error! status: ${response.status}`)
    );
  }

  return payload as T;
}

export async function fetchAssets(): Promise<Asset[]> {
  // Assets are passed from Django template, but we can also fetch them
  // For now, we'll get them from the initial page load
  return [];
}

export async function fetchDevices(assetCode: string): Promise<Device[]> {
  try {
    const response = await fetch(`${API_BASE}/devices/?asset_code=${encodeURIComponent(assetCode)}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      credentials: 'include',
    });
    const result = await parseJsonResponse<{ success: boolean; data?: Device[]; error?: string }>(response);

    if (!result.success) {
      throw new Error(result.error || 'Failed to fetch devices');
    }

    return result.data || [];
  } catch (error) {
    console.error('Error fetching devices:', error);
    throw error;
  }
}

export async function fetchMeasurementPoints(
  assetCode: string,
  deviceTypes: string[]
): Promise<{ data: MeasurementPointsByDeviceType; diagnostics: MeasurementPointsDiagnostics | null }> {
  try {
    const deviceTypesParam = deviceTypes.join(',');
    const response = await fetch(
      `${API_BASE}/measurement-points/?asset_code=${encodeURIComponent(assetCode)}&device_types=${encodeURIComponent(deviceTypesParam)}`,
      {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
        },
        credentials: 'include',
      }
    );

    const result = await parseJsonResponse<{
      success: boolean;
      data?: MeasurementPointsByDeviceType;
      diagnostics?: MeasurementPointsDiagnostics;
      error?: string;
    }>(response);

    if (!response.ok || !result.success) {
      throw new Error(result.error || `HTTP error! status: ${response.status}`);
    }

    return {
      data: result.data || {},
      diagnostics: (result.diagnostics as MeasurementPointsDiagnostics) || null,
    };
  } catch (error) {
    console.error('Error fetching measurement points:', error);
    throw error;
  }
}

export async function fetchTimeSeriesData(
  assetCode: string,
  deviceIds: string[],
  metrics: string[],
  startDate: string,
  endDate: string
): Promise<AnalyticsDataResponse> {
  try {
    const params = new URLSearchParams({
      asset_code: assetCode,
      device_ids: deviceIds.join(','),
      metrics: metrics.join(','),
      start_date: startDate,
      end_date: endDate,
    });

    const response = await fetch(`${API_BASE}/timeseries-data/?${params}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      credentials: 'include',
    });
    const result = await parseJsonResponse<AnalyticsDataResponse & { success?: boolean; error?: string }>(response);

    if (!result.success) {
      throw new Error(result.error || 'Failed to fetch time series data');
    }

    return result;
  } catch (error) {
    console.error('Error fetching time series data:', error);
    throw error;
  }
}

export function getCSVDownloadUrl(
  assetCode: string,
  deviceIds: string[],
  metrics: string[],
  startDate: string,
  endDate: string
): string {
  const params = new URLSearchParams({
    asset_code: assetCode,
    device_ids: deviceIds.join(','),
    metrics: metrics.join(','),
    start_date: startDate,
    end_date: endDate,
  });

  return `${API_BASE}/download-csv/?${params}`;
}


