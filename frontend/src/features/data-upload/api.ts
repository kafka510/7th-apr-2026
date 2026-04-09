/**
 * API client for Data Upload feature
 */

import type {
  DataCounts,
  UploadHistoryItem,
  UploadResponse,
  DataPreviewResponse,
  DeleteDataRequest,
  DeleteDataResponse,
  DataType,
} from './types';

const API_BASE = '/api';

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
    | { success?: boolean; error?: string; message?: string; csrf_error?: boolean }
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

// Helper to get CSRF token
function getCSRFToken(): string | null {
  if (typeof document === 'undefined') {
    return null;
  }
  // First, try to get from meta tag (set by Django template)
  const metaToken = document.querySelector<HTMLMetaElement>('meta[name="csrf-token"]');
  if (metaToken && metaToken.content) {
    return metaToken.content;
  }
  // Second, try to get from hidden input field
  const token = document.querySelector<HTMLInputElement>('[name=csrfmiddlewaretoken]');
  if (token) {
    return token.value;
  }
  // Fallback: try to get from cookie
  const cookies = document.cookie.split(';');
  for (const cookie of cookies) {
    const [name, value] = cookie.trim().split('=');
    if (name === 'csrftoken') {
      return value;
    }
  }
  return null;
}

// Async helper to fetch CSRF token from API endpoint if not found
async function fetchCSRFToken(): Promise<string | null> {
  try {
    const response = await fetch('/api/csrf-token/', {
      method: 'GET',
      credentials: 'include',
    });
    
    if (!response.ok) {
      console.warn('Failed to fetch CSRF token from API');
      return null;
    }
    
    const data = await parseJsonResponse<{ csrfToken?: string }>(response);
    return data.csrfToken || null;
  } catch (error) {
    console.error('Error fetching CSRF token:', error);
    return null;
  }
}

// Helper to create headers with CSRF token (synchronous version - for GET requests)
function createHeaders(): HeadersInit {
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };
  const csrfToken = getCSRFToken();
  if (csrfToken) {
    headers['X-CSRFToken'] = csrfToken;
  }
  return headers;
}

export async function fetchDataCounts(): Promise<DataCounts> {
  try {
    const response = await fetch(`${API_BASE}/data-counts/`, {
      method: 'GET',
      headers: createHeaders(),
      credentials: 'include',
    });
    return await parseJsonResponse<DataCounts>(response);
  } catch (error) {
    console.error('Error fetching data counts:', error);
    throw error;
  }
}

export async function fetchUploadHistory(): Promise<{ uploads: UploadHistoryItem[]; message?: string }> {
  try {
    const response = await fetch(`${API_BASE}/upload-history/`, {
      method: 'GET',
      headers: createHeaders(),
      credentials: 'include',
    });
    return await parseJsonResponse<{ uploads: UploadHistoryItem[]; message?: string }>(response);
  } catch (error) {
    console.error('Error fetching upload history:', error);
    throw error;
  }
}

export async function uploadCSVFile(
  file: File,
  dataType: DataType,
  uploadMode: 'append' | 'replace',
  options?: {
    startDate?: string;
    endDate?: string;
    skipDuplicates?: boolean;
    validateData?: boolean;
    batchSize?: number;
  }
): Promise<UploadResponse> {
  try {
    const formData = new FormData();
    formData.append('csv_file', file);
    formData.append('data_type', dataType);
    formData.append('upload_mode', uploadMode);

    if (options?.startDate) {
      formData.append('start_date', options.startDate);
    }
    if (options?.endDate) {
      formData.append('end_date', options.endDate);
    }
    if (options?.skipDuplicates !== undefined) {
      formData.append('skip_duplicates', options.skipDuplicates.toString());
    }
    if (options?.validateData !== undefined) {
      formData.append('validate_data', options.validateData.toString());
    }
    if (options?.batchSize) {
      formData.append('batch_size', options.batchSize.toString());
    }

    // Always fetch CSRF token from API endpoint for POST requests
    // This ensures we get the full 64-character token that Django expects
    // (meta tag/cookie tokens might be truncated to 32 characters)
    let csrfToken = await fetchCSRFToken();
    
    if (!csrfToken) {
      throw new Error('CSRF token missing. Please refresh the page and try again.');
    }
    
    // Validate token length (Django CSRF tokens are 64 characters)
    if (csrfToken.length !== 64) {
      console.warn(`CSRF token has incorrect length: ${csrfToken.length} (expected 64). Fetching fresh token...`);
      // Try fetching again - might be a stale token
      const freshToken = await fetchCSRFToken();
      if (!freshToken || freshToken.length !== 64) {
        throw new Error('CSRF token validation failed. Please refresh the page and try again.');
      }
      csrfToken = freshToken;
    }
    
    const headers: HeadersInit = {
      'X-CSRFToken': csrfToken,
    };

    const response = await fetch('/api/upload-csv/', {
      method: 'POST',
      headers,
      body: formData,
      credentials: 'include',
    });

    if (!response.ok) {
      // If we get a 403, it might be a CSRF error - try fetching token and retrying once
      if (response.status === 403) {
        // Clone the response to read it without consuming it
        const responseClone = response.clone();
        const errorText = await responseClone.text().catch(() => '');
        if (errorText.includes('CSRF') || errorText.includes('csrf')) {
          // Fetch fresh token and retry
          const freshToken = await fetchCSRFToken();
          if (freshToken) {
            const retryHeaders: HeadersInit = { ...headers };
            retryHeaders['X-CSRFToken'] = freshToken;
            const retryResponse = await fetch('/api/upload-csv/', {
              method: 'POST',
              headers: retryHeaders,
              body: formData,
              credentials: 'include',
            });
            const retryData = await parseJsonResponse<UploadResponse>(retryResponse);
            return retryData;
          }
        }
      }
      
      // Try to parse as JSON, fallback to text if that fails
      let errorMessage = `Upload failed with status ${response.status}`;
      try {
        const errorData = await parseJsonResponse<{ error?: string }>(response);
        errorMessage = errorData.error || errorMessage;
      } catch {
        // If JSON parsing fails, try to get text
        try {
          const errorText = await response.text();
          if (errorText) {
            errorMessage = errorText.includes('CSRF') 
              ? 'CSRF verification failed: CSRF token missing. Please refresh the page and try again.'
              : errorText;
          }
        } catch {
          // If all else fails, use the status message
        }
      }
      throw new Error(errorMessage);
    }

    return await parseJsonResponse<UploadResponse>(response);
  } catch (error) {
    console.error('Error uploading CSV file:', error);
    throw error;
  }
}

export async function fetchDataPreview(dataType: DataType): Promise<DataPreviewResponse> {
  try {
    const response = await fetch(`${API_BASE}/data-preview/${dataType}/`, {
      method: 'GET',
      headers: createHeaders(),
      credentials: 'include',
    });
    return await parseJsonResponse<DataPreviewResponse>(response);
  } catch (error) {
    console.error('Error fetching data preview:', error);
    throw error;
  }
}

export async function deleteData(request: DeleteDataRequest): Promise<DeleteDataResponse> {
  try {
    // Get CSRF token - try local first, then fetch from API if needed
    let csrfToken = getCSRFToken();
    if (!csrfToken) {
      csrfToken = await fetchCSRFToken();
    }
    
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    };
    if (csrfToken) {
      headers['X-CSRFToken'] = csrfToken;
    }
    
    const response = await fetch(`${API_BASE}/delete-data/`, {
      method: 'POST',
      headers,
      body: JSON.stringify(request),
      credentials: 'include',
    });
    return await parseJsonResponse<DeleteDataResponse>(response);
  } catch (error) {
    console.error('Error deleting data:', error);
    throw error;
  }
}

export async function downloadData(dataType: DataType, format: 'csv' | 'excel' = 'csv'): Promise<void> {
  try {
    // Don't send JSON headers for file downloads - we need to accept blob/octet-stream
    const csrfToken = getCSRFToken();
    const headers: HeadersInit = {
      'Accept': format === 'excel' 
        ? 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' 
        : 'text/csv, application/octet-stream',
    };
    if (csrfToken) {
      headers['X-CSRFToken'] = csrfToken;
    }

    const response = await fetch(`${API_BASE}/download-data/?data_type=${dataType}&format=${format}`, {
      method: 'GET',
      headers,
      credentials: 'include',
    });

    if (!response.ok) {
      // Check if it's an HTML error page (like 403 access denied)
      const contentType = response.headers.get('Content-Type') || '';
      if (contentType.includes('text/html')) {
        // For HTML error pages, consume the response but use status for error message
        await response.text(); // Consume the response body
        throw new Error(`Access denied or error: ${response.status} ${response.statusText}`);
      } else if (contentType.includes('application/json')) {
        // Try to get JSON error message
        try {
          const errorJson = await response.json();
          const errorMessage = errorJson.error || `HTTP error! status: ${response.status}`;
          const suggestion = errorJson.suggestion ? ` ${errorJson.suggestion}` : '';
          throw new Error(`${errorMessage}${suggestion}`);
        } catch (jsonError) {
          // If JSON parsing fails, use status
          throw new Error(`Download failed: ${response.status} ${response.statusText}`);
        }
      } else {
        // If not JSON or HTML, use status
        throw new Error(`Download failed: ${response.status} ${response.statusText}`);
      }
    }

    // Get filename from Content-Disposition header or use default
    const contentDisposition = response.headers.get('Content-Disposition');
    let filename = `${dataType}_data.${format === 'excel' ? 'xlsx' : 'csv'}`;
    
    if (contentDisposition) {
      // Try multiple patterns to extract filename
      const patterns = [
        /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/,
        /filename\*?=['"]?([^'";\n]+)['"]?/i,
        /filename=([^;\n]+)/i,
      ];
      
      for (const pattern of patterns) {
        const match = contentDisposition.match(pattern);
        if (match && match[1]) {
          filename = match[1].replace(/['"]/g, '').trim();
          // Handle UTF-8 encoded filenames (filename*=UTF-8''...)
          if (filename.startsWith("UTF-8''")) {
            filename = decodeURIComponent(filename.replace("UTF-8''", ''));
          }
          break;
        }
      }
    }

    // Create blob and download
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  } catch (error) {
    console.error('Error downloading data:', error);
    throw error;
  }
}

