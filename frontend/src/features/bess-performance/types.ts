export interface BESSData {
  id: number;
  asset_no: string;
  date?: string | null;
  month: string;
  country: string;
  portfolio: string;
  battery_capacity_mw?: number | string | null;
  export_energy_kwh?: number | string | null;
  pv_energy_kwh?: number | string | null;
  charge_energy_kwh?: number | string | null;
  discharge_energy_kwh?: number | string | null;
  min_soc?: number | string | null;
  max_soc?: number | string | null;
  min_ess_temperature?: number | string | null;
  max_ess_temperature?: number | string | null;
  min_ess_humidity?: number | string | null;
  max_ess_humidity?: number | string | null;
  rte?: number | string | null;
  created_at?: string | null;
  updated_at?: string | null;
  [key: string]: unknown; // Allow for other properties
}

export interface BESSFilters {
  month?: string | null;
  year?: string | null;
  range?: { start: string; end: string } | null;
  country?: string[];
  portfolio?: string[];
  asset?: string[];
  [key: string]: unknown; // For FilterState compatibility
}

export interface BESSFilterOptions {
  months: string[];
  years: string[];
  countries: string[];
  portfolios: string[];
  assets: string[];
}

export interface BESSKPIData {
  label: string;
  value: string;
  unit: string;
  icon: string;
  color: string;
  bgGradient: string;
}

export interface BESSChartData {
  months: string[];
  pvEnergy: number[];
  exportEnergy: number[];
  chargeEnergy: number[];
  dischargeEnergy: number[];
}

