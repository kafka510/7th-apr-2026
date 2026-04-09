/**
 * TypeScript types for PV Module management
 */

export type ModuleTechnology = 
  | 'mono_perc'
  | 'mono_standard'
  | 'poly'
  | 'thin_film'
  | 'bifacial'
  | 'heterojunction'
  | 'topcon';

export type MountingType = 
  | 'fixed'
  | 'single_axis'
  | 'dual_axis'
  | 'rooftop'
  | 'ground';

export interface PVModuleDatasheet {
  id: number;
  module_model: string;
  manufacturer: string;
  technology: ModuleTechnology;
  
  // STC electrical specs
  pmax_stc: number;
  isc_stc: number;
  imp_stc: number;
  voc_stc: number;
  vmp_stc: number;
  module_efficiency_stc: number;
  
  // NOCT
  noct: number;
  
  // Temperature coefficients
  temp_coeff_pmax: number;
  temp_coeff_voc: number;
  temp_coeff_isc: number;
  temp_coeff_type_voc: 'absolute' | 'percentage';
  temp_coeff_type_isc: 'absolute' | 'percentage';
  
  // Physical
  cells_per_module: number;
  length: number;
  width: number;
  area: number;
  
  // Low irradiance performance (optional)
  low_irr_200?: number;
  low_irr_400?: number;
  low_irr_600?: number;
  low_irr_800?: number;
  
  // Warranty (optional)
  warranty_year_1?: number;
  warranty_year_25?: number;
  linear_degradation_rate?: number;
  
  // Calculated properties
  fill_factor?: number;
  estimated_annual_degradation?: number;
  
  // Metadata
  created_at: string;
  updated_at: string;
  created_by?: string;
}

export interface InverterTiltConfig {
  tilt_deg: number;
  azimuth_deg: number;
  orientation?: string;
  string_count: number;
  modules_in_series: number;
  panel_count: number;
  // future: irradiance_mode?: 'transposition' | 'direct_gii';
  // future: irradiance_channel?: string;
}

export interface DevicePVConfig {
  device_id: string;
  device_name: string;
  device_type: string;
  parent_code: string;
  
  // Module configuration
  module_datasheet_id?: number;
  module_model?: string;
  manufacturer?: string;
  pmax_stc?: number;
  
  // Installation configuration
  modules_in_series?: number;
  installation_date?: string;
  tilt_angle?: number;
  azimuth_angle?: number;
  mounting_type?: MountingType;
  
  // Loss factors
  expected_soiling_loss?: number;
  shading_factor?: number;
  
  // Measured performance
  measured_degradation_rate?: number;
  last_performance_test_date?: string;
  operational_notes?: string;
  
  // Power model selection (plugin architecture)
  power_model_id?: number;
  power_model_name?: string;
  model_fallback_enabled?: boolean;
  
  // Weather device configuration (with fallback support)
  // Each entry contains device_id and metric to use
  weather_device_config?: {
    irradiance_devices?: WeatherDeviceMetric[];
    temperature_devices?: WeatherDeviceMetric[];
    wind_devices?: WeatherDeviceMetric[];
  };
  
  // Inverter-level configuration (when device_type is inverter)
  tilt_configs?: InverterTiltConfig[];
  dc_cap?: number;
  ac_capacity?: number;
  
  // Calculated values
  string_rated_power?: number;
  string_voc?: number;
  string_vmp?: number;
  string_age_years?: number;
  current_degradation_factor?: number;
}

export interface WeatherDevice {
  device_id: string;
  device_name: string;
  device_type: string;
}

export interface WeatherDeviceMetric {
  device_id: string;
  metric: string; // The metric name (e.g., 'gii', 'temperature')
}

export interface WeatherMetric {
  metric: string;
  oem_tag: string;
  units: string;
  description: string;
}

export interface BulkAssignConfig {
  module_datasheet_id: number;
  modules_in_series: number;
  string_rated_power: number;
  installation_date: string;
  tilt_angle: number;
  azimuth_angle: number;
  tracking_type: string;
  mounting_type: MountingType;
  soiling_loss: number;
  shading_loss: number;
  mismatch_loss: number;
  wiring_loss: number;
  availability_loss: number;
  expected_soiling_loss: number;
  shading_factor: number;
}

export interface ImportResult {
  success: boolean;
  created?: number;
  updated?: number;
  skipped?: number;
  failed?: number;
  errors?: ImportError[];
  total_processed?: number;
}

export interface ImportError {
  row?: number;
  field?: string;
  message: string;
}

export interface PowerModel {
  id: number;
  code: string;
  name: string;
  version: string;
  type: 'physics_based' | 'ml' | 'hybrid' | 'empirical';
  is_default: boolean;
  requires_weather_data: boolean;
  requires_module_datasheet: boolean;
  requires_historical_data: boolean;
  supports_degradation: boolean;
  supports_soiling: boolean;
  supports_bifacial: boolean;
  supports_shading: boolean;
}

