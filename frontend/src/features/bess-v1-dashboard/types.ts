export interface BessV1Record {
  id: number;
  month: string;
  country: string;
  portfolio: string;
  asset_no: string;
  battery_capacity_mwh?: number | string | null;
  actual_pv_energy_kwh?: number | string | null;
  actual_export_energy_kwh?: number | string | null;
  actual_charge_energy_kwh?: number | string | null;
  actual_discharge_energy?: number | string | null;
  actual_pv_grid_kwh?: number | string | null;
  actual_system_losses?: number | string | null;
  min_soc?: number | string | null;
  max_soc?: number | string | null;
  min_ess_temp?: number | string | null;
  max_ess_temp?: number | string | null;
  actual_avg_rte?: number | string | null;
  actual_cuf?: number | string | null;
  actual_no_of_cycles?: number | string | null;
  budget_pv_energy_kwh?: number | string | null;
  budget_export_energy_kwh?: number | string | null;
  budget_charge_energy_kwh?: number | string | null;
  budget_discharge_energy?: number | string | null;
  budget_pv_grid_kwh?: number | string | null;
  budget_system_losses?: number | string | null;
  budget_cuf?: number | string | null;
  budget_no_of_cycles?: number | string | null;
  budget_grid_import_kwh?: number | string | null;
  actual_grid_import_kwh?: number | string | null;
  budget_avg_rte?: number | string | null;
  [key: string]: unknown;
}

export interface BessV1Filters {
  countries: string[];
  portfolios: string[];
  assets: string[];
  month: string | null;
  year: string | null;
  range: { start: string; end: string } | null;
  startMonth?: string;
  endMonth?: string;
  [key: string]: unknown;
}

export interface BessV1FilterOptions {
  countries: string[];
  portfolios: string[];
  assets: string[];
  months: string[];
}

export interface EnergyFlowData {
  labels: string[];
  budget: number[];
  actual: number[];
}

export interface WaterfallData {
  pvGeneration: number;
  gridImport: number;
  systemLosses: number;
  bessToGrid: number;
  pvToGrid: number;
  totalExport: number;
}

export interface TrendPoint {
  month: string;
  cufActual?: number | null;
  cufBudget?: number | null;
  cyclesActual?: number | null;
  cyclesBudget?: number | null;
}

export interface DailyCUFDataPoint {
  date: string;
  cufActual: number | null;
  cufBudget: number | null;
}

export interface DailyCycleDataPoint {
  date: string;
  cyclesActual: number | null;
  cyclesBudget: number | null;
}

export interface DailyBessRecord {
  id: number;
  date: string | null;
  month: string | null;
  country: string | null;
  portfolio: string | null;
  asset_no: string | null;
  actual_no_of_cycles: number | null;
  cuf: number | null;
  charge_energy_kwh?: number | null;
  discharge_energy_kwh?: number | null;
  battery_capacity_mw?: number | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface BessV1Aggregates {
  avgCapMWh: number;
  totalCapMWh: number;
  minSOC: number | null;
  maxSOC: number | null;
  minTemp: number | null;
  maxTemp: number | null;
  avgRTEpct: number | null;
  budgetRTEpct: number | null;
  actualCycles: number | null;
  budgetCycles: number | null;
  cufPctOverall: number | null;
  budgetCUF: number | null;
  energyFlow: EnergyFlowData;
  waterfall: WaterfallData;
  monthCUFData: Array<Pick<TrendPoint, 'month' | 'cufActual' | 'cufBudget'>>;
  monthCycleData: Array<Pick<TrendPoint, 'month' | 'cyclesActual' | 'cyclesBudget'>>;
  dailyCUFData?: DailyCUFDataPoint[];
  dailyCycleData?: DailyCycleDataPoint[];
}

export interface UseBessV1DataReturn {
  data: BessV1Record[];
  filterOptions: BessV1FilterOptions;
  filteredData: BessV1Record[];
  aggregates: BessV1Aggregates | null;
  loading: boolean;
  error: Error | null;
}

