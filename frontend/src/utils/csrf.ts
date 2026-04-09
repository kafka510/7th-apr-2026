/**
 * CSRF Token Utilities for React Applications
 * 
 * This module provides secure CSRF token retrieval that works with
 * production HTTPS settings (CSRF_COOKIE_HTTPONLY = True)
 * 
 * Usage:
 *   import { getCSRFToken } from '@/utils/csrf';
 *   const token = getCSRFToken();
 */

/**
 * Get CSRF token from multiple sources (in priority order)
 * 
 * Priority:
 * 1. Meta tag (secure, works with HTTPONLY = True) ✅ RECOMMENDED
 * 2. Form input (for traditional forms)
 * 3. Cookie (only if HTTPONLY = False)
 * 
 * @returns CSRF token string or null if not found
 */
export function getCSRFToken(): string | null {
  if (typeof document === 'undefined') {
    return null;
  }
  
  // Method 1: Read from meta tag (SECURE - works with HTTPONLY = True)
  const metaTag = document.querySelector<HTMLMetaElement>('meta[name="csrf-token"]');
  if (metaTag?.content) {
    return metaTag.content;
  }
  
  // Method 2: Read from form input (for non-React pages)
  const formInput = document.querySelector<HTMLInputElement>('[name="csrfmiddlewaretoken"]');
  if (formInput?.value) {
    return formInput.value;
  }
  
  // Method 3: Read from cookie (FALLBACK - only works if HTTPONLY = False)
  const cookies = document.cookie.split(';');
  for (const cookie of cookies) {
    const [name, value] = cookie.trim().split('=');
    if (name === 'csrftoken') {
      return value;
    }
  }
  
  // No token found
  console.warn('CSRF token not found. Ensure template includes: <meta name="csrf-token" content="{{ csrf_token }}">');
  return null;
}

/**
 * Create headers object with CSRF token included
 * 
 * @param additionalHeaders - Optional additional headers to include
 * @returns Headers object with CSRF token
 */
export function createHeadersWithCSRF(additionalHeaders: Record<string, string> = {}): HeadersInit {
  const headers: HeadersInit = { ...additionalHeaders };
  
  const csrfToken = getCSRFToken();
  if (csrfToken) {
    headers['X-CSRFToken'] = csrfToken;
  }
  
  return headers;
}

/**
 * Create headers for JSON requests with CSRF token
 * 
 * @returns Headers object with Content-Type: application/json and CSRF token
 */
export function createJSONHeadersWithCSRF(): HeadersInit {
  return createHeadersWithCSRF({
    'Content-Type': 'application/json',
  });
}

/**
 * Check if CSRF token is available
 * 
 * @returns true if token is available, false otherwise
 */
export function hasCSRFToken(): boolean {
  return getCSRFToken() !== null;
}

/**
 * Get CSRF cookie value (only works if HTTPONLY = False)
 * 
 * @param name - Cookie name (default: 'csrftoken')
 * @returns Cookie value or null
 */
export function getCookie(name: string = 'csrftoken'): string | null {
  if (typeof document === 'undefined') {
    return null;
  }
  
  const cookies = document.cookie.split(';');
  for (const cookie of cookies) {
    const [cookieName, cookieValue] = cookie.trim().split('=');
    if (cookieName === name) {
      return cookieValue;
    }
  }
  
  return null;
}


