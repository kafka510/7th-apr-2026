// Generation Report Types

export interface GenerationDailyData {
  Date: string;
  [assetCode: string]: string | number | undefined; // Wide format: date rows, asset columns
}

export interface YieldDataRow {
  assetno: string;
  dc_capacity_mw?: string | number;
  month: string;
  country: string;
  portfolio: string;
  ic_approved_budget_dollar?: string | number;
  expected_budget_dollar?: string | number;
  actual_generation_dollar?: string | number;
  operational_budget_dollar?: string | number;
  revenue_loss_op?: string | number;
  ppa_rate?: string | number;
}

export interface MapDataRow {
  asset_no: string;
  dc_capacity_mwp?: string | number;
  country: string;
  portfolio: string;
}

export interface GenerationFilters {
  startMonth?: string; // YYYY-MM format
  endMonth?: string; // YYYY-MM format
  [key: string]: unknown; // For FilterState compatibility
}

export interface GenerationData {
  icApprovedBudgetDaily: GenerationDailyData[];
  expectedBudgetDaily: GenerationDailyData[];
  actualGenerationDaily: GenerationDailyData[];
  budgetGIIDaily: GenerationDailyData[];
  actualGIIDaily: GenerationDailyData[];
  yieldData: YieldDataRow[];
  mapData: MapDataRow[];
}

export interface HierarchicalRow {
  id: string;
  parentId: string | null;
  level: number; // -1: grand total, 0: country, 1: portfolio, 2: asset
  country: string;
  portfolio: string;
  asset: string | number;
  dc: number;
  ic: number; // IC Approved Budget
  exp: number; // Expected Budget
  ag: number; // Actual Generation
  yieldVal?: number; // Yield (MWh/MW)
  fYield?: string | number; // Forecasted Generation
  expPR?: number; // Expected PR (%)
  actPR?: number; // Actual PR (%)
  isTotal?: boolean;
  isExpandable: boolean;
  isHidden: boolean;
  // For revenue table
  act?: number; // Actual Revenue ($)
  forecast?: number; // Forecasted Revenue ($)
}

export interface GenerationReportData extends GenerationData {
  latestReportDate?: string;
  dateRange?: {
    min: string;
    max: string;
  };
}

