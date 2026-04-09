/**
 * Type definitions for Sales Dashboard feature
 */

export interface YieldDataEntry {
  month: string;
  country: string;
  portfolio: string;
  assetno: string;
  dc_capacity_mw: string | number;
  ic_approved_budget: string | number;
  expected_budget: string | number;
  weather_loss_or_gain: string | number;
  grid_curtailment: string | number;
  grid_outage: string | number;
  operation_budget: string | number;
  breakdown_loss: string | number;
  unclassified_loss: string | number;
  actual_generation: string | number;
  string_failure: string | number;
  inverter_failure: string | number;
  mv_failure: string | number;
  hv_failure: string | number;
  expected_pr: string | number;
  actual_pr: string | number;
  pr_gap: string | number;
  pr_gap_observation: string;
  pr_gap_action_need_to_taken: string;
  revenue_loss: string | number;
  revenue_loss_observation: string;
  revenue_loss_action_need_to_taken: string;
  actual_irradiation: string | number;
  ac_capacity_mw: string | number;
  bess_capacity_mwh: string | number;
  bess_generation_mwh: string | number;
  ppa_rate: string | number;
  ic_approved_budget_dollar: string | number;
  expected_budget_dollar: string | number;
  actual_generation_dollar: string | number;
  operational_budget_dollar: string | number;
  revenue_loss_op: string | number;
  created_at: string;
  updated_at: string;
}

export interface MapDataEntry {
  asset_no: string;
  country: string;
  portfolio: string;
  site_name: string;
  dc_capacity_mwp: string | number;
  battery_capacity_mw: string | number;
  plant_type: string;
  installation_type: string;
  latitude: string | number;
  longitude: string | number;
}

export interface SalesData {
  yieldData: YieldDataEntry[];
  mapData: MapDataEntry[];
}

export interface SalesFilters {
  country?: string[];
  portfolio?: string[];
  installation?: string[];
  selectedMonth?: string | null;
  selectedYear?: string | null;
  selectedRange?: {
    start: string;
    end: string;
  } | null;
}

export interface KPIMetrics {
  solarEnergy: number; // MWh
  bessEnergy: number; // MWh
  totalCO2: number; // Tons
  treesSaved: number; // Trees
  solarAssetsCount: number; // Count
  solarDcCapacity: number; // MWp
  bessCapacity: number; // MW
}

export interface ChartDataPoint {
  month: string;
  value: number;
}

