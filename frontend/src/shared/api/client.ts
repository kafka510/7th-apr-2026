/**
 * Standardized API client for React apps
 * All React apps should use this for consistency
 */

import { createJSONHeadersWithCSRF } from '@/utils/csrf';

const API_BASE = '/api/v2';

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
  body?: unknown;
  headers?: Record<string, string>;
  signal?: AbortSignal;
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Unknown error' }));
    throw new Error(error.error || error.detail || `HTTP error! status: ${response.status}`);
  }
  return response.json();
}

export async function apiGet<T>(
  endpoint: string,
  params?: Record<string, string | string[] | number | boolean | undefined>,
  options?: RequestOptions
): Promise<T> {
  const url = new URL(`${API_BASE}${endpoint}`, window.location.origin);
  
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        if (Array.isArray(value)) {
          // Handle arrays as comma-separated
          url.searchParams.append(key, value.join(','));
        } else {
          url.searchParams.append(key, String(value));
        }
      }
    });
  }
  
  const response = await fetch(url.toString(), {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    credentials: 'include',
    signal: options?.signal,
  });
  
  return handleResponse<T>(response);
}

export async function apiPost<T>(
  endpoint: string,
  data?: unknown,
  options?: RequestOptions
): Promise<T> {
  const headers = createJSONHeadersWithCSRF();
  const response = await fetch(`${API_BASE}${endpoint}`, {
    method: 'POST',
    headers: {
      ...headers,
      ...options?.headers,
    },
    credentials: 'include',
    body: data ? JSON.stringify(data) : undefined,
    signal: options?.signal,
  });
  
  return handleResponse<T>(response);
}

export async function apiPut<T>(
  endpoint: string,
  data?: unknown,
  options?: RequestOptions
): Promise<T> {
  const headers = createJSONHeadersWithCSRF();
  const response = await fetch(`${API_BASE}${endpoint}`, {
    method: 'PUT',
    headers: {
      ...headers,
      ...options?.headers,
    },
    credentials: 'include',
    body: data ? JSON.stringify(data) : undefined,
    signal: options?.signal,
  });
  
  return handleResponse<T>(response);
}

export async function apiDelete<T>(
  endpoint: string,
  options?: RequestOptions
): Promise<T> {
  const headers = createJSONHeadersWithCSRF();
  const response = await fetch(`${API_BASE}${endpoint}`, {
    method: 'DELETE',
    headers: {
      ...headers,
      ...options?.headers,
    },
    credentials: 'include',
    signal: options?.signal,
  });
  
  return handleResponse<T>(response);
}

export async function apiPatch<T>(
  endpoint: string,
  data?: unknown,
  options?: RequestOptions
): Promise<T> {
  const headers = createJSONHeadersWithCSRF();
  const response = await fetch(`${API_BASE}${endpoint}`, {
    method: 'PATCH',
    headers: {
      ...headers,
      ...options?.headers,
    },
    credentials: 'include',
    body: data ? JSON.stringify(data) : undefined,
    signal: options?.signal,
  });
  
  return handleResponse<T>(response);
}

