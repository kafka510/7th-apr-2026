/**
 * Solar Insight / Engineering Tools API base URL.
 * Module and inverter master data: GET /api/pre-feasibility/module-master/, inverter-master/
 * (from engineering_tools/data_master/pv_module_master_v1.csv, inverter_master_v1.csv).
 * In dev, set VITE_ENGINEERING_TOOLS_BASE to backend origin (e.g. http://localhost:8000) if needed.
 */
import { getCSRFToken } from '@/utils/csrf';

const SOLAR_BASE =
  (typeof import.meta !== 'undefined' &&
    import.meta.env &&
    (import.meta.env.VITE_ENGINEERING_TOOLS_BASE as string)) ||
  '/engineering-tools';

export function solarApiUrl(path: string): string {
  const normalized = path.startsWith('/') ? path.slice(1) : path;
  const base = SOLAR_BASE.endsWith('/') ? SOLAR_BASE.slice(0, -1) : SOLAR_BASE;
  return `${base}/${normalized}`.replace(/\/+/g, '/');
}

/** Use for solargis-monthly endpoint (implemented). */
export function solargisApiUrl(path: string): string {
  const p = path.startsWith('/') ? path.slice(1) : path;
  return solarApiUrl(`api/${p}`);
}

/**
 * Same-origin fetch for /engineering-tools APIs: session cookies + CSRF on mutating methods.
 * Do not set Content-Type for FormData bodies (browser sets multipart boundary).
 */
export function engineeringToolsFetch(url: string, init: RequestInit = {}): Promise<Response> {
  const method = (init.method || 'GET').toUpperCase();
  const headers = new Headers(init.headers);
  if (!headers.has('Accept')) {
    headers.set('Accept', 'application/json');
  }
  if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
    const csrf = getCSRFToken();
    if (csrf) {
      headers.set('X-CSRFToken', csrf);
    }
  }
  return fetch(url, {
    ...init,
    credentials: 'include',
    headers,
  });
}
