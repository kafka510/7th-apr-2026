export interface AOCData {
  id?: number;
  s_no?: number | string;
  month: string;
  asset_no: string;
  country: string;
  portfolio: string;
  remarks: string;
  created_at?: string;
  updated_at?: string;
}

export interface AOCFilters {
  month?: string;
  year?: string;
  country?: string;
  portfolio?: string;
}

export interface AOCFilterOptions {
  months: string[];
  years: string[];
  countries: string[];
  portfolios: string[];
}

