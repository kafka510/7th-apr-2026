export interface PrGapData {
  asset_no: string;
  assetno?: string;
  asset?: string;
  pr_gap: number | string;
  dc_capacity_mw: number | string;
  month: string;
  country: string;
  portfolio: string;
  pr_gap_observation?: string;
  pr_gap_action_need_to_taken?: string;
}

export interface LossCalculationData {
  asset_no: string;
  asset?: string;
  month: string;
  l?: string;
  breakdown_dc_capacity_kw?: number | string;
  breakdown_dc_capacity?: number | string;
  dc_capacity?: number | string;
  bd_description?: string;
  action_to_be_taken?: string;
  status_of_bd?: string;
  generation_loss_kwh?: number | string;
  'generation_loss_(kwh)'?: number | string;
}

export interface PrGapFilters {
  month?: string | null;
  year?: string | null;
  range?: { start: string; end: string } | null;
  countries: string[];
  portfolios: string[];
}

export interface PrGapFilterOptions {
  months: string[];
  years: string[];
  countries: string[];
  portfolios: string[];
}

export interface PrGapDataPoint {
  asset: string;
  gap: number;
  dc: number;
  gapDc: number;
  gapDcDisplay: string;
  displayGap: string;
  color: string;
}

