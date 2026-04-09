/**
 * Generation Budget Insights - API Client
 * API client for IC Budget vs Expected data
 */

import type { ICBudgetData, ICBudgetDataEntry } from './types';

const API_BASE_URL = '/api/v1/ic-budget/ic-budget-data/';

async function parseJsonResponse<T>(response: Response): Promise<T> {
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

export async function fetchICBudgetData(): Promise<ICBudgetData> {
  try {
    const response = await fetch(API_BASE_URL, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      credentials: 'include',
    });
    const result = await parseJsonResponse<{
      success: boolean;
      data: ICBudgetDataEntry[];
      count?: number;
      error?: string;
    }>(response);

    // Validate response structure
    if (!result.success) {
      throw new Error(result.error || 'Failed to fetch IC Budget data');
    }

    if (!Array.isArray(result.data)) {
      throw new Error('Invalid response format: data is not an array');
    }

    return {
      data: result.data,
      count: result.count || result.data.length,
    };
  } catch (error) {
    console.error('Error fetching IC Budget data:', error);
    throw error;
  }
}

