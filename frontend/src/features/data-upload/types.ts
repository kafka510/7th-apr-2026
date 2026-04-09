/**
 * Type definitions for Data Upload feature
 */

export type DataType =
  | 'yield'
  | 'bess'
  | 'bess_v1'
  | 'aoc'
  | 'ice'
  | 'icvsexvscur'
  | 'map'
  | 'minamata'
  | 'loss_calculation'
  | 'actual_generation_daily'
  | 'expected_budget_daily'
  | 'budget_gii_daily'
  | 'actual_gii_daily'
  | 'ic_approved_budget_daily';

export type UploadMode = 'append' | 'replace';

export interface DataCounts {
  yield_count: number;
  bess_count: number;
  bess_v1_count: number;
  aoc_count: number;
  ice_count: number;
  icvsexvscur_count: number;
  map_count: number;
  minamata_count: number;
  actual_generation_daily_count: number;
  expected_budget_daily_count: number;
  budget_gii_daily_count: number;
  actual_gii_daily_count: number;
  ic_approved_budget_daily_count: number;
}

export interface UploadHistoryItem {
  file_name: string;
  data_type: string;
  upload_mode: string;
  import_date: string | null;
  records_imported: number;
  records_skipped: number;
  status: 'success' | 'failed' | 'pending';
  imported_by: string;
  file_size_mb?: number;
  processing_time?: number;
  success_rate?: number;
}

export interface UploadResponse {
  success: boolean;
  records_imported?: number;
  records_skipped?: number;
  records_updated?: number;
  error?: string;
  warnings?: string[];
  validation_details?: {
    statistics?: {
      total_rows: number;
      total_columns: number;
      empty_rows: number;
      missing_data_count: number;
    };
  };
}

export interface DataPreviewResponse {
  data?: Record<string, unknown>[];
  preview?: Record<string, unknown>[];  // API v2 format
  status?: string;
  total_records?: number;
  data_type?: string;
  message?: string;
}

export interface DeleteDataRequest {
  data_type: DataType;
  delete_option: 'all' | 'date_range';
  start_date?: string;
  end_date?: string;
}

export interface DeleteDataResponse {
  success: boolean;
  deleted_count?: number;
  message?: string;
  error?: string;
}

