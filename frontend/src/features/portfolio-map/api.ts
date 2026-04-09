/**
 * API client for Portfolio Map feature
 */
import type { PortfolioMapData } from './types';

const API_BASE = '/api/v1/portfolio-map';

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

export async function fetchPortfolioMapData(): Promise<PortfolioMapData> {
  const url = `${API_BASE}/map-data/`;
  console.log('[fetchPortfolioMapData] Calling portfolio map endpoint:', url);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const response = await fetchJson<any>(url);
  const responseKeys = Object.keys(response || {});
  console.log('[fetchPortfolioMapData] Response keys:', responseKeys);
  
  // Check if we got the wrong endpoint response (has generation report keys)
  const generationReportKeys = ['icApprovedBudgetDaily', 'expectedBudgetDaily', 'actualGenerationDaily', 'budgetGIIDaily', 'actualGIIDaily', 'dateRange', 'latestReportDate'];
  const hasGenerationKeys = generationReportKeys.some(key => key in response);
  
  if (hasGenerationKeys) {
    console.error('[fetchPortfolioMapData] ERROR: Response contains generation report keys!');
    console.error('[fetchPortfolioMapData] This means the wrong endpoint was called.');
    console.error('[fetchPortfolioMapData] Expected URL: /api/v1/portfolio-map/map-data/');
    console.error('[fetchPortfolioMapData] Response contains:', generationReportKeys.filter(key => key in response));
    throw new Error('Wrong API endpoint called - response contains generation report data. The portfolio map endpoint should ONLY return mapData and yieldData.');
  }
  
  // Validate response structure
  if (!response || (!('mapData' in response) && !('yieldData' in response))) {
    console.error('[fetchPortfolioMapData] Invalid response structure!');
    console.error('[fetchPortfolioMapData] Expected: mapData and yieldData');
    console.error('[fetchPortfolioMapData] Got:', responseKeys);
    throw new Error('Invalid portfolio map API response structure');
  }
  
  // Extract only mapData and yieldData (ignore any other unexpected keys)
  const portfolioMapData: PortfolioMapData = {
    mapData: response.mapData || [],
    yieldData: response.yieldData || [],
  };
  
  // Validate mapData entries have all required fields
  if (portfolioMapData.mapData.length > 0) {
    const firstEntry = portfolioMapData.mapData[0];
    const requiredFields = ['site_name', 'installation_type', 'plant_type', 'offtaker', 'cod', 'battery_capacity_mw', 'latitude', 'longitude'];
    const missingFields = requiredFields.filter(field => !(field in firstEntry));
    if (missingFields.length > 0) {
      console.error('[fetchPortfolioMapData] Map data entries are missing required fields:', missingFields);
      console.error('[fetchPortfolioMapData] First entry keys:', Object.keys(firstEntry));
      console.error('[fetchPortfolioMapData] First entry:', firstEntry);
      console.error('[fetchPortfolioMapData] This suggests the API is returning incomplete data structure!');
    }
  }
  
  return portfolioMapData;
}

