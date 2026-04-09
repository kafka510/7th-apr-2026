/**
 * Type definitions for API Management feature
 */

export interface APIUser {
  id: number;
  name: string;
  access_level: 'web_only' | 'api_only' | 'both';
  access_level_display: string;
  status: 'active' | 'suspended' | 'revoked';
  rate_limit_per_minute: number;
  rate_limit_per_hour: number;
  rate_limit_per_day: number;
  total_requests?: number;
  last_request_at?: string;
}

export interface APIKey {
  id: string;
  name: string;
  description?: string;
  key_prefix: string;
  status: 'active' | 'suspended' | 'revoked' | 'expired';
  created_at: string | null;
  expires_at: string | null;
  last_used_at?: string | null;
  total_requests?: number;
}

export interface TablePermission {
  id: number;
  table_name: string;
  can_read: boolean;
  can_filter: boolean;
  can_aggregate: boolean;
  max_records_per_request: number;
}

export interface APIUserInfo {
  api_user: APIUser;
  accessible_sites_count: number;
  accessible_countries: string[];
  accessible_portfolios: string[];
  base_url: string;
}

