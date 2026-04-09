export type KpiSummary = {
  totalAssets: number;
  activeSites: number;
  inactiveSites: number;
  communicationNotAvailable: number;
  lastUpdated: string | null;
};

export type KpiMetric = {
  asset_code: string;
  asset_number: string;
  asset_name: string;
  country: string;
  portfolio: string;
  date: string;
  daily_generation_mwh: number;
  daily_expected_mwh: number;
  daily_budget_irradiation_mwh?: number;
  daily_ic_mwh?: number;
  daily_irradiation_mwh?: number;
  capacity?: number;
  dc_capacity_mw?: number;
  expect_pr?: number;
  actual_pr?: number;
  daily_irr?: number;
  last_updated?: string;
  site_state?: string | null;
};

export type KpiFilterState = {
  countries: string[];
  portfolios: string[];
  assets: string[];
  date: string | null; // Deprecated: use startDate/endDate instead
  startDate: string | null;
  endDate: string | null;
  // Persist which sub-tab is active ('gauges' | 'monthly')
  view?: 'gauges' | 'monthly';
  [key: string]: unknown;
};

export type KpiFilterOptions = {
  countries: string[];
  portfolios: string[];
  assets: string[];
};

export type KpiGaugeValues = {
  icBudget: number;
  expectedBudget: number;
  actualGeneration: number;
  budgetIrr: number;
  actualIrr: number;
  expectedPR: number;
  actualPR: number;
};

