// Feedback API Client
import type {
  FeedbackSubmitPayload,
  MarkAttendedPayload,
  FeedbackListParams,
  FeedbackListResponse,
} from './types';
import { createJSONHeadersWithCSRF, createHeadersWithCSRF } from '@/utils/csrf';

// Helper function for GET requests
async function get<T>(url: string): Promise<T> {
  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
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
      isHtml ? 'Server returned an HTML page instead of API JSON. Please refresh and retry.' : raw || `HTTP error! status: ${response.status}`
    );
  }

  const payload = (await response.json().catch(() => null)) as { error?: string; message?: string } | null;
  if (!response.ok) {
    throw new Error(payload?.error || payload?.message || `HTTP error! status: ${response.status}`);
  }
  return payload as T;
}

// Helper function for POST requests
async function post<T>(url: string, data: unknown): Promise<T> {
  const headers = createJSONHeadersWithCSRF();
  const response = await fetch(url, {
    method: 'POST',
    headers,
    credentials: 'include',
    body: JSON.stringify(data),
  });

  const contentType = response.headers.get('content-type') || '';
  const isJson = contentType.includes('application/json');
  if (!isJson) {
    const raw = (await response.text().catch(() => '')).trim();
    throw new Error(raw || `HTTP error! status: ${response.status}`);
  }
  const payload = (await response.json().catch(() => null)) as { error?: string; message?: string } | null;
  if (!response.ok) {
    throw new Error(payload?.error || payload?.message || `HTTP error! status: ${response.status}`);
  }
  return payload as T;
}

// Helper function for form POST requests (multipart/form-data)
async function postForm<T>(url: string, formData: FormData): Promise<T> {
  const headers = createHeadersWithCSRF({
    'X-Requested-With': 'XMLHttpRequest',
  });
  const response = await fetch(url, {
    method: 'POST',
    headers,
    credentials: 'include',
    body: formData,
  });

  const contentType = response.headers.get('content-type') || '';
  const isJson = contentType.includes('application/json');
  if (!isJson) {
    const raw = (await response.text().catch(() => '')).trim();
    throw new Error(raw || `HTTP error! status: ${response.status}`);
  }
  const payload = (await response.json().catch(() => null)) as { error?: string; message?: string } | null;
  if (!response.ok) {
    throw new Error(payload?.error || payload?.message || `HTTP error! status: ${response.status}`);
  }
  return payload as T;
}

// Helper function for DELETE requests (Django uses POST for delete)
async function del<T>(url: string): Promise<T> {
  const headers = createJSONHeadersWithCSRF();
  const response = await fetch(url, {
    method: 'POST',
    headers,
    credentials: 'include',
  });

  const contentType = response.headers.get('content-type') || '';
  const isJson = contentType.includes('application/json');
  if (!isJson) {
    const raw = (await response.text().catch(() => '')).trim();
    throw new Error(raw || `HTTP error! status: ${response.status}`);
  }
  const payload = (await response.json().catch(() => null)) as { error?: string; message?: string } | null;
  if (!response.ok) {
    throw new Error(payload?.error || payload?.message || `HTTP error! status: ${response.status}`);
  }
  return payload as T;
}

export async function fetchFeedbackList(
  params?: FeedbackListParams
): Promise<FeedbackListResponse> {
  const queryParams = new URLSearchParams();
  
  // Handle status array - send as comma-separated or empty for all
  if (params?.status && params.status.length > 0) {
    queryParams.append('status', params.status.join(','));
  }
  
  if (params?.search) queryParams.append('search', params.search);
  if (params?.page) queryParams.append('page', params.page.toString());

  const url = `/api/feedback/list/${queryParams.toString() ? `?${queryParams.toString()}` : ''}`;
  const response = await get<FeedbackListResponse>(url);
  return response;
}

export async function submitFeedback(payload: FeedbackSubmitPayload): Promise<{
  success: boolean;
  message: string;
  close_modal?: boolean;
}> {
  const formData = new FormData();
  formData.append('subject', payload.subject);
  formData.append('message', payload.message);

  if (payload.images && payload.images.length > 0) {
    payload.images.forEach((image) => {
      formData.append('images', image);
    });
  }

  return postForm('/api/feedback/submit/', formData);
}

export async function markFeedbackAttended(
  feedbackId: number,
  payload?: MarkAttendedPayload
): Promise<{
  success: boolean;
  message: string;
  email_sent: boolean;
  attended_at?: string;
  subject?: string;
}> {
  return post(`/api/feedback/${feedbackId}/mark-attended/`, payload || {});
}

export async function deleteFeedback(feedbackId: number): Promise<{
  success: boolean;
  message: string;
}> {
  return del(`/api/feedback/${feedbackId}/delete/`);
}

export async function fetchFeedbackImages(feedbackId: number): Promise<{
  success: boolean;
  images: Array<{
    id: number;
    url: string;
    name: string;
  }>;
  count: number;
}> {
  return get(`/api/feedback/${feedbackId}/images/`);
}
