/**
 * Generation Budget Insights - Type Definitions
 * Type definitions for IC Budget vs Expected feature
 */

export interface ICBudgetDataEntry {
  id: number;
  country: string | null;
  portfolio: string | null;
  dc_capacity_mwp: number | null;
  month: string | null; // Format: "Apr 2025"
  month_sort: string | null; // ISO format: "2025-04-01"
  ic_approved_budget_mwh: number | null;
  expected_budget_mwh: number | null;
  actual_generation_mwh: number | null;
  grid_curtailment_budget_mwh: number | null;
  actual_curtailment_mwh: number | null;
  budget_irradiation_kwh_m2: number | null;
  actual_irradiation_kwh_m2: number | null;
  expected_pr_percent: number | null;
  actual_pr_percent: number | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface ICBudgetData {
  data: ICBudgetDataEntry[];
  count: number;
}

export interface ICBudgetFilters {
  selectedMonth?: string | null;
  selectedYear?: string | null;
  selectedRange?: {
    start: string;
    end: string;
  } | null;
  country?: string;
  portfolio?: string;
}

export interface AggregatedRow {
  Month: string;
  'IC Approved Budget (MWh)': number;
  'Expected Budget (MWh)': number;
  'Actual Generation (MWh)': number;
  'Grid Curtailment Budget (MWh)': number;
  'Actual Curtailment (MWh)': number;
  'Budget Irradiation (kWh/M2)': number;
  'Actual Irradiation (kWh/M2)': number;
  'Expected PR (%)': number;
  'Actual PR (%)': number;
}

export interface PortfolioSummary {
  portfolio: string;
  icApprovedBudget: number;
  expectedBudget: number;
  actualGeneration: number;
  difference: number;
  reason: string;
}

