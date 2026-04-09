/**
 * API client for API Management feature
 */

import type { APIUserInfo, APIKey } from './types';

const API_BASE = '/api/web';

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

export async function fetchAPIUserInfo(): Promise<APIUserInfo> {
  try {
    const response = await fetch(`${API_BASE}/user-info/`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      credentials: 'include',
    });
    const result = await parseJsonResponse<{ success: boolean; data: APIUserInfo; error?: string }>(response);

    if (!result.success) {
      throw new Error(result.error || 'Failed to fetch API user info');
    }

    return result.data;
  } catch (error) {
    console.error('Error fetching API user info:', error);
    throw error;
  }
}

export async function fetchAPIKeys(): Promise<APIKey[]> {
  try {
    const response = await fetch(`${API_BASE}/keys/`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      credentials: 'include',
    });
    const result = await parseJsonResponse<{ success: boolean; data?: APIKey[]; error?: string }>(response);

    if (!result.success) {
      throw new Error(result.error || 'Failed to fetch API keys');
    }

    return result.data || [];
  } catch (error) {
    console.error('Error fetching API keys:', error);
    throw error;
  }
}

export async function generateAPIKey(name: string, description?: string, expiresAt?: string): Promise<{ key: string; key_id: string }> {
  try {
    const formData = new FormData();
    formData.append('name', name);
    if (description) formData.append('description', description);
    if (expiresAt) formData.append('expires_at', expiresAt);

    const response = await fetch('/api/keys/generate/', {
      method: 'POST',
      body: formData,
      credentials: 'include',
    });
    const result = await parseJsonResponse<{ key: string; key_id: string; message?: string; error?: string }>(response);
    return {
      key: result.key,
      key_id: result.key_id,
    };
  } catch (error) {
    console.error('Error generating API key:', error);
    throw error;
  }
}

