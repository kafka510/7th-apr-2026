export interface LossEvent {
  id: number;
  asset_code: string;
  device_id: string;
  start_ts: string | null;
  end_ts: string | null;
  internal_state: string | null;
  oem_state_label: string | null;
  loss_kwh: number | null;
  is_legitimate: boolean | null;
  confirmed_at: string | null;
  confirmed_by_id: number | null;
}

export interface LossEventLog {
  id: number;
  created_at: string | null;
  old_value: boolean | null;
  new_value: boolean | null;
  user_id: number | null;
  username: string | null;
}

export interface LossEventFilters {
  assetCode?: string;
  deviceId?: string;
  startTime?: string;
  endTime?: string;
}

export interface LossEventPage {
  events: LossEvent[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

