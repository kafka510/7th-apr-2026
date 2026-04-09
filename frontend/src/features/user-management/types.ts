// User Management TypeScript Types

export interface UserProfile {
  id: number;
  user: {
    id: number;
    username: string;
    email: string;
    first_name: string;
    last_name: string;
    is_active: boolean;
    date_joined: string;
    last_login: string | null;
  };
  role: string;
  accessible_countries: string;
  accessible_portfolios: string;
  accessible_sites: string;
  app_access: string;
  ticketing_access: boolean;
  created_by: number | null;
  created_at: string;
  // Usage statistics
  usage_score?: number;
  successful_logins_30d?: number;
  successful_logins_all_time?: number;
  failed_attempts_all_time?: number;
  failed_attempts_recent?: number;
}

export interface Asset {
  asset_code: string;
  asset_name: string;
  country: string;
  portfolio: string;
  asset_number: string;
}

export interface ActivityDataPoint {
  hour: string;
  hour_full: string;
  timestamp: string;
  count: number;
  timezone: string;
}

export interface SuspiciousActivity {
  id: number;
  user: {
    id: number;
    username: string;
  } | null;
  ip_address: string;
  action: string;
  resource: string;
  timestamp: string;
  is_suspicious: boolean;
  risk_level: string;
}

export interface ActiveUser {
  id: number;
  user: {
    id: number;
    username: string;
    email: string;
  };
  ip_address: string;
  last_activity: string;
  country: string;
  city: string;
}

export interface BlockedIP {
  id: number;
  ip_address: string;
  status: 'active' | 'inactive' | 'whitelisted';
  priority: 'low' | 'medium' | 'high' | 'critical';
  reason: string;
  description: string;
  blocked_by: number | null;
  created_at: string;
  expires_at: string | null;
  block_count: number;
  last_seen: string | null;
}

export interface BlockedUser {
  id: number;
  user: {
    id: number;
    username: string;
    email: string;
  };
  status: 'active' | 'inactive' | 'whitelisted';
  priority: 'low' | 'medium' | 'high' | 'critical';
  reason: string;
  description: string;
  blocked_by: number | null;
  created_at: string;
  expires_at: string | null;
  block_count: number;
  last_seen: string | null;
}

export interface WaffleFlag {
  id: number;
  name: string;
  everyone: boolean | null;
  percent: number | null;
  testing: boolean;
  superusers: boolean;
  staff: boolean;
  authenticated: boolean;
  rollout: boolean;
  note: string;
  created: string;
  modified: string;
  users?: Array<{
    id: number;
    username: string;
    email: string;
  }>;
}

export interface UserStats {
  active_users_count: number;
  security_alerts_count: number;
  total_users: number;
  suspicious_activities_count: number;
  active_users: number;
  inactive_users: number;
  blocked_users_count: number;
  blocked_ips_count: number;
}

export interface CreateUserPayload {
  username: string;
  email: string;
  password: string;
  role: string;
  access_control: string[];
  countries?: string[];
  portfolios?: string[];
  sites?: string[];
}

export interface UpdateUserPayload {
  email?: string;
  first_name?: string;
  last_name?: string;
  role?: string;
  is_active?: boolean;
  access_control?: string[];
  countries?: string[];
  portfolios?: string[];
  sites?: string[];
}

export interface DownloadActivityFilters {
  start_date?: string;
  end_date?: string;
  user?: string;
  action?: string;
  ip?: string;
  include_suspicious?: boolean;
}

export interface CreateFlagPayload {
  name: string;
  everyone?: boolean | null;
  percent?: number;
  testing?: boolean;
  superusers?: boolean;
  staff?: boolean;
  authenticated?: boolean;
  rollout?: boolean;
  note?: string;
  users?: number[]; // Array of user IDs
}

export interface UpdateFlagPayload {
  name?: string;
  everyone?: boolean | null;
  percent?: number;
  testing?: boolean;
  superusers?: boolean;
  staff?: boolean;
  authenticated?: boolean;
  rollout?: boolean;
  note?: string;
  users?: number[]; // Array of user IDs
}


