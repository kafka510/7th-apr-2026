/**
 * Type definitions for Analytics Dashboard feature
 */

export interface Asset {
  asset_code: string;
  asset_name: string;
  timezone: string;
  country: string;
  portfolio: string;
}

export interface Device {
  device_id: string;
  device_name: string;
  device_type: string;
}

export interface MeasurementPoint {
  metric: string;
  units?: string;
  description?: string;
  oem_tag?: string;
}

export interface MeasurementPointsByDeviceType {
  [deviceType: string]: MeasurementPoint[];
}

/** Server-side explanation when metrics list is empty or filtered oddly */
export interface MeasurementPointsDiagnostics {
  lookup_codes: string[];
  device_types_requested: string[] | null;
  expanded_device_types: string[] | null;
  used_device_type_fallback: boolean;
  raw_mapping_row_count: number;
  rows_with_nonempty_metric: number;
  grouped_metric_count: number;
  hints: string[];
}

export interface DataPoint {
  timestamp: string;
  value: string | number;
}

export interface TimeSeriesData {
  device_id: string;
  /** Display name for chart (when available from device_list) */
  device_name?: string;
  metric: string;
  units?: string;
  data_points: DataPoint[];
}

export interface AnalyticsDataResponse {
  success: boolean;
  data?: TimeSeriesData[];
  record_count?: number;
  timezone_offset?: string;
  data_quality?: {
    valid_records: number;
    total_records: number;
    filter_percentage: number;
  };
  warnings?: string[];
  warning?: string;
  error?: string;
}

export interface AnalyticsFilters {
  assetCode: string | null;
  deviceIds: string[];
  metrics: string[];
  startDate: string | null;
  endDate: string | null;
}

export type ZoomMode = 'x' | 'y' | 'xy';
export type PanMode = 'x' | 'y' | 'xy';

