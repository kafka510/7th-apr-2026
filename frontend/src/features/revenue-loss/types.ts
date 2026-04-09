export interface RevenueLossData {
  month: string;
  country: string;
  portfolio: string;
  asset_no?: string;
  assetno?: string;
  asset?: string;
  dc_capacity_mw?: number | string;
  ic_approved_budget?: number | string;
  expected_budget?: number | string;
  weather_loss_or_gain?: number | string;
  grid_curtailment?: number | string;
  grid_outage?: number | string;
  operation_budget?: number | string;
  breakdown_loss?: number | string;
  unclassified_loss?: number | string;
  actual_generation?: number | string;
  'string failure'?: number | string;
  'inverter failure'?: number | string;
  ac_failure?: number | string;
  expected_pr?: number | string;
  actual_pr?: number | string;
  pr_gap?: number | string;
  pr_gap_observation?: string;
  pr_gap_action_need_to_taken?: string;
  revenue_loss?: number | string;
  revenue_loss_observation?: string;
  revenue_loss_action_need_to_taken?: string;
  revenue_loss_op?: number | string;
  actual_irradiation?: number | string;
  ac_capacity_mw?: number | string;
  bess_capacity_mwh?: number | string;
  bess_generation_mwh?: number | string;
  ppa_rate?: number | string;
  ic_approved_budget_dollar?: number | string;
  expected_budget_dollar?: number | string;
  actual_generation_dollar?: number | string;
  operational_budget_dollar?: number | string;
}

export interface RevenueLossFilters {
  month?: string | null;
  year?: string | null;
  range?: { start: string; end: string } | null;
  countries?: string[];
  portfolios?: string[];
}

export interface RevenueLossFilterOptions {
  months: string[];
  years: string[];
  countries: string[];
  portfolios: string[];
}

export interface RevenueLossDataPoint {
  asset: string;
  loss: number;
  color: string;
  displayValue: string;
}

