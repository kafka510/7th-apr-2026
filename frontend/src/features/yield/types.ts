export interface YieldDataEntry {
  month: string;
  country: string;
  portfolio: string;
  assetno: string;
  dc_capacity_mw: number | string;
  ic_approved_budget: number | string;
  expected_budget: number | string;
  weather_loss_or_gain: number | string;
  grid_curtailment: number | string;
  grid_outage: number | string;
  operation_budget: number | string;
  breakdown_loss: number | string;
  scheduled_outage_loss?: number | string;
  unclassified_loss: number | string;
  actual_generation: number | string;
  'string failure'?: number | string;
  'inverter failure'?: number | string;
  // Some datasets may use slightly different column names; include aliases for robustness
  'ac failure'?: number | string;
  schduled_outage_loss?: number | string;
  mv_failure?: number | string;
  hv_failure?: number | string;
  ac_failure?: number | string;
  expected_pr: number | string;
  actual_pr: number | string;
  pr_gap: number | string;
  pr_gap_observation?: string;
  pr_gap_action_need_to_taken?: string;
  revenue_loss: number | string;
  revenue_loss_observation?: string;
  revenue_loss_action_need_to_taken?: string;
  actual_irradiation?: number | string;
  ac_capacity_mw?: number | string;
  bess_capacity_mwh?: number | string;
  bess_generation_mwh?: number | string;
  ppa_rate?: number | string;
  ic_approved_budget_dollar?: number | string;
  expected_budget_dollar?: number | string;
  actual_generation_dollar?: number | string;
  created_at?: string;
  updated_at?: string;
  remarks?: string;
}

export interface YieldFilters {
  countries: string[];
  portfolios: string[];
  assets: string[];
  month: string | null;
  year: string | null;
  range: { start: string; end: string } | null;
}

export interface YieldOptions {
  countries: string[];
  portfolios: string[];
  assets: string[];
  months: string[];
  years: string[];
}

// Extended options type used by filter components
export type YieldFilterOptions = YieldOptions;

// Shared data and chart types
export type YieldData = YieldDataEntry;

export interface WaterfallStep {
  name: string;
  value: number;
  type: 'absolute' | 'relative';
}

export interface YieldSummary {
  totalIcApprovedBudget: number;
  totalExpectedBudget: number;
  totalActualGeneration: number;
  totalWeatherLossOrGain: number;
  totalGridCurtailment: number;
  totalGridOutage: number;
  totalOperationBudget: number;
  totalBreakdownLoss: number;
  totalUnclassifiedLoss: number;
}

