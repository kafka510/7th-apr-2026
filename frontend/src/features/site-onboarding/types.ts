// Site Onboarding TypeScript Types

/** One tilt/azimuth/panel config for GHI→GII transposition */
export interface TiltConfigItem {
  tilt_deg: number;
  azimuth_deg: number;
  panel_count: number;
}

/**
 * Inverter SDM group row — same shape as PV Modules tab → inverter configuration
 * (`device_list.tilt_configs` / `InverterTiltConfig` in pvModules types).
 */
export interface DeviceInverterTiltConfig {
  tilt_deg: number;
  azimuth_deg: number;
  orientation?: string;
  string_count: number;
  modules_in_series: number;
  panel_count: number;
}

export interface AssetList {
  asset_code: string;
  asset_name: string;
  /** Provider asset ID from OEM (e.g. Fusion Solar plant ID NE=...) */
  provider_asset_id?: string;
  capacity: number;
  address: string;
  country: string;
  latitude: number;
  longitude: number;
  contact_person: string;
  contact_method: string;
  grid_connection_date: string;
  asset_number: string;
  customer_name: string;
  portfolio: string;
  timezone: string;
  asset_name_oem: string;
  cod: string;
  operational_cod: string;
  y1_degradation: number | null;
  anual_degradation: number | null;
  api_name: string;
  api_key: string;
  /** Tilt configs for transposition: [{ tilt_deg, azimuth_deg, panel_count }] */
  tilt_configs: TiltConfigItem[] | null;
  /** Site altitude (m) */
  altitude_m: number | null;
  /** Ground albedo 0–1 */
  albedo: number | null;
  /** PVsyst Performance Ratio (0–1) for PR-based expected power model */
  pv_syst_pr: number | null;
  /** Asset code used as satellite irradiance source for this site */
  satellite_irradiance_source_asset_code: string | null;
}

export interface DeviceList {
  device_id: string;
  device_name: string;
  device_code: string;
  device_type_id: string;
  device_serial: string;
  device_model: string;
  device_make: string;
  latitude: number;
  longitude: number;
  optimizer_no: number;
  parent_code: string;
  device_type: string;
  software_version: string;
  country: string;
  string_no: string;
  connected_strings: string;
  device_sub_group: string;
  dc_cap: number;
  device_source: string;
  ac_capacity: number | null;
  equipment_warranty_start_date: string | null;
  equipment_warranty_expire_date: string | null;
  epc_warranty_start_date: string | null;
  epc_warranty_expire_date: string | null;
  calibration_frequency: string;
  pm_frequency: string;
  visual_inspection_frequency: string;
  bess_capacity: number | null;
  yom: string;
  nomenclature: string;
  location: string;
  // PV module configuration and advanced fields
  module_datasheet_id: number | null;
  modules_in_series: number | null;
  installation_date: string | null;
  tilt_angle: number | null;
  azimuth_angle: number | null;
  mounting_type: string | null;
  expected_soiling_loss: number | null;
  shading_factor: number | null;
  measured_degradation_rate: number | null;
  last_performance_test_date: string | null;
  operational_notes: string | null;
  power_model_id: number | null;
  power_model_config: unknown | null;
  model_fallback_enabled: boolean | null;
  weather_device_config: unknown | null;
  /** Inverter SDM groups (same structure as PV Modules inverter tilt_configs) */
  tilt_configs: DeviceInverterTiltConfig[] | null;
}

export interface DeviceMapping {
  id: number;
  asset_code: string;
  device_type: string;
  oem_tag: string;
  description: string;
  data_type: string;
  units: string;
  metric: string;
  fault_code: string;
  module_no: string;
  default_value: string;
  // Optional asset details (populated when filtering by asset_code)
  asset_name?: string;
  asset_number?: string;
  country?: string;
  portfolio?: string;
}

export interface BudgetValues {
  id: number;
  asset_number: string;
  asset_code: string;
  month_str: string;
  month_date: string;
  bd_production: number;
  bd_ghi: number;
  bd_gti: number;
}

export interface ICBudget {
  id: number;
  asset_code: string;
  asset_number: string;
  month_str: string;
  month_date: string;
  ic_bd_production: number;
}

export interface AssetContract {
  id: number;
  asset_number: string;
  asset_code: string;
  asset_name: string;
  customer_asset_name: string;
  customer_tax_number: string;
  asset_address: string;
  asset_cod: string;
  contractor_name: string;
  spv_name: string;
  contract_start_date: string;
  contract_end_date: string;
  contract_billing_cycle: string;
  contract_billing_cycle_start_day: number | null;
  contract_billing_cycle_end_day: number | null;
  currency_code: string;
  sp_account_no: string;
  escalation_condition: string;
  escalation_type: string;
  escalation_grace_years: number | null;
  escalation_rate: number | null;
  escalation_period: number | null;
  due_days: number | null;
  gst_rate: number | null;
  spv_address: string;
  spv_gst_number: string;
  contractor_id: string;
  contract_type: string;
  requires_utility_invoice: boolean;
  bank_name: string;
  bank_account_no: string;
  bank_swift: string;
  bank_branch_code: string;
  contractor_address: string;
  contact_person_1: string;
  contact_person_2: string;
  contact_person_3: string;
  contact_person_4: string;
  contact_person_5: string;
  contact_person_6: string;
  contact_email_id_1: string;
  contact_email_id_2: string;
  contact_email_id_3: string;
  contact_email_id_4: string;
  contact_email_id_5: string;
  contact_email_id_6: string;
  contact_email_id_7: string;
  contact_number_1: string;
  contact_number_2: string;
  contact_number_3: string;
  grid_export_rate: number | null;
  grid_export_tax: number | null;
  grid_excess_export: number | null;
  grid_excess_export_tax: number | null;
  rooftop_self_consumption_rate: number | null;
  rooftop_self_consumption_tax: number | null;
  solar_lease_rate: number | null;
  solar_lease_rate_tax: number | null;
  bess_dispatch_rate: number | null;
  bess_dispatch_tax: number | null;
  hybrid_solar_bess_rate: number | null;
  hybrid_solar_bess_tax: number | null;
  generation_based_ppa_rate: number | null;
  generation_based_ppa_tax: number | null;
  capacity_payment_rate: number | null;
  capacity_payment_tax: number | null;
  curtailment_compensation: number | null;
  peak_tariff_rate: number | null;
  off_peak_rate: number | null;
  shoulder_tariff: string;
  shoulder_rate: number | null;
  super_off_break_tariff: string;
  super_off_break_rate: number | null;
  seasonal_tou_tariff: string;
  seasonal_tou_rate: number | null;
  real_time_tou_tariff: string;
  real_time_tou_rate: number | null;
  critical_peak_tariff: string;
  critical_peak_rate: number | null;
  merchant_market_rate: number | null;
  ancillary_services_charges: number | null;
  ancillary_services_tax: number | null;
  virtual_ppa_rate: number | null;
  virtual_ppa_tax: number | null;
  green_tariff_rate: number | null;
  green_tariff_tax: number | null;
  tariff_matrix_json: Record<string, unknown> | null;
  created_at?: string;
  updated_at?: string;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ICBudgetResponse {
  ic_budgets: ICBudget[];
  pagination: {
    current_page: number;
    total_pages: number;
    total_count: number;
    page_size: number;
  };
}

export interface ApiResponse {
  success: boolean;
  message?: string;
  error?: string;
}

export interface UploadResponse {
  success: boolean;
  message?: string;
  error?: string;
  statistics?: {
    records_imported: number;
    records_skipped: number;
    total_rows_processed: number;
    empty_rows_skipped: number;
  };
  errors?: string[];
  validation_errors?: Array<{
    type?: string;
    row?: number;
    message?: string;
    asset_code?: string;
    year?: number;
    month_str?: string;
    expected_month?: number;
    actual_month?: number;
    date?: string;
    rows?: number[];
    total_rows?: number;
    expected?: number;
    found?: number;
  }>;
  error_examples?: string[];
  error_summary?: {
    format_errors?: number;
    day_errors?: number;
    month_mismatch_errors?: number;
    missing_months_errors?: number;
    other_errors?: number;
  };
  total_errors?: number;
  help_text?: string;
  validation_feedback?: {
    warnings: string[];
    file_statistics: {
      total_rows: number;
      total_columns: number;
      empty_rows: number;
      missing_data_count: number;
    };
  };
}

/** Solargis region: when daily data is available (UTC). Affects Celery Beat daily ingest time. */
export type SolargisRegion =
  | 'GOES_WEST'           // 09:00 UTC
  | 'GOES_EAST'           // 05:00 UTC
  | 'GOES_EAST_PATAGONIA' // 05:00 UTC
  | 'METEOSAT_PRIME'      // 00:30 UTC
  | 'METEOSAT_PRIME_SCANDINAVIA' // 00:30 UTC
  | 'METEOSAT_IODC'       // 19:00 UTC
  | 'HIMAWARI'            // 16:00 UTC
  | 'IODC_HIMAWARI'       // 16:00 UTC
  | '';                   // default 02:00 UTC

/** Solargis/adapter config fields (inside config JSON) */
export interface AssetAdapterConfigConfig {
  api_url?: string;
  api_key?: string;
  summarization?: string;
  processing_keys?: string;
  terrain_shading?: boolean;
  time_stamp_type?: string;
  tilt?: number;
  azimuth?: number;
  linked_asset_codes?: string[];
  /** Optional explicit Solargis site id to use in requests (must start with a letter). */
  asset_id?: string;
  /** Solargis satellite region: sets when daily ingest runs (UTC). Empty = 02:00 UTC. */
  solargis_region?: SolargisRegion | string;
  /** Override: daily run hour (0-23) UTC. If set with daily_run_utc_minute, overrides solargis_region. */
  daily_run_utc_hour?: number;
  /** Override: daily run minute (0-59) UTC. */
  daily_run_utc_minute?: number;
  /** Daily run time in local time (HH:MM 24h). Used with daily_run_timezone to compute UTC. */
  daily_run_local_time?: string;
  /** Timezone for daily run, e.g. UTC, +05:30, -05:00, +8. Used with daily_run_local_time. */
  daily_run_timezone?: string;
  // Fusion Solar adapter config
  api_base_url?: string;
  username?: string;
  password?: string;
  plant_id?: string;
  rate_limit_calls_per_minute?: number;
  // LaplaceID adapter account/config
  groupid?: string;
}

export interface AssetAdapterConfig {
  id: number;
  asset_code: string;
  adapter_id: string;
  adapter_account_id?: number | null;
  adapter_account_name?: string | null;
  /** Per-asset row JSON (often overrides only when linked to an adapter account). */
  config: AssetAdapterConfigConfig;
  /** Merged adapter account + per-asset config, secrets masked (for list display). */
  effective_config?: AssetAdapterConfigConfig | null;
  acquisition_interval_minutes: number;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface AdapterAccount {
  id: number;
  adapter_id: string;
  name: string;
  config: AssetAdapterConfigConfig;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export type TableName =
  | 'asset_list'
  | 'device_list'
  | 'device_mapping'
  | 'budget_values'
  | 'ic_budget'
  | 'asset_adapter_config'
  | 'assets_contracts'
  | 'device_operating_state'
  | 'spare_master'
  | 'location_master'
  | 'spare_site_map'
  | 'stock_balance'
  | 'stock_entry'
  | 'stock_issue';

export interface DeviceOperatingState {
  id: number;
  adapter_id: string;
  device_type: string;
  state_value: string;
  oem_state_label: string;
  internal_state: string;
  is_normal: boolean;
  fault_code: string | null;
  created_at?: string;
  updated_at?: string;
}

// Spare Management Types
export interface SpareMaster {
  spare_id: number;
  spare_code: string;
  spare_name: string;
  description: string;
  category: string;
  unit: string;
  min_stock: number | null;
  max_stock: number | null;
  is_critical: boolean;
}

export interface LocationMaster {
  location_id: number;
  location_code: string;
  location_name: string;
  location_type: string;
}

export interface SpareSiteMap {
  map_id: number;
  spare_id: number;
  spare_code: string;
  spare_name: string;
  asset_code: string;
  asset_name: string;
  location_id: number;
  location_code: string;
  location_name: string;
  is_active: boolean;
  created_at: string;
}

export interface StockBalance {
  stock_balance_id: number;
  spare_id: number;
  spare_code: string;
  spare_name: string;
  location_id: number;
  location_code: string;
  location_name: string;
  quantity: number;
  unit: string;
  last_updated: string;
}

export interface StockEntry {
  entry_id: number;
  spare_id: number;
  spare_code: string;
  spare_name: string;
  location_id: number;
  location_code: string;
  location_name: string;
  quantity: number;
  unit: string;
  entry_type: string;
  reference_number: string;
  remarks: string;
  entry_date: string;
  performed_by: string;
}

export interface StockIssue {
  issue_id: number;
  spare_id: number;
  spare_code: string;
  spare_name: string;
  location_id: number;
  location_code: string;
  location_name: string;
  quantity: number;
  unit: string;
  issue_type: string;
  ticket_id: string;
  ticket_number: string;
  issued_to: string;
  remarks: string;
  issue_date: string;
  performed_by: string;
}

