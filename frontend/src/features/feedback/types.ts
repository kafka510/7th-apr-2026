export interface FeedbackImage {
  id: number;
  url: string;
  name: string;
}

export interface Feedback {
  id: number;
  user: {
    id: number;
    username: string;
    first_name: string;
    last_name: string;
    email: string;
  };
  user_email: string;
  subject: string;
  message: string;
  attended_status: 'pending' | 'attended';
  attended_at: string | null;
  created_at: string;
  images?: FeedbackImage[];
  image_count?: number;
}

export interface FeedbackSubmitPayload {
  subject: string;
  message: string;
  images?: File[];
}

export interface MarkAttendedPayload {
  admin_response?: string;
}

export interface FeedbackListParams {
  status: string[];
  search?: string;
  page?: number;
}

export interface FeedbackListResponse {
  results: Feedback[];
  count: number;
  next: string | null;
  previous: string | null;
  page: number;
  total_pages: number;
}

