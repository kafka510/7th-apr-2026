/**
 * Type definitions for Portfolio Map feature
 */

export interface MapDataEntry {
  id: number;
  asset_no: string;
  country: string;
  site_name: string;
  portfolio: string;
  installation_type: string;
  dc_capacity_mwp: string | number;
  pcs_capacity: string;
  battery_capacity_mw: string;
  plant_type: string;
  offtaker: string;
  cod: string;
  latitude: string | number;
  longitude: string | number;
  created_at: string | null;
  updated_at: string | null;
}

export interface YieldDataEntry {
  month: string;
  country: string;
  portfolio: string;
  assetno: string;
  dc_capacity_mw: string | number;
  ic_approved_budget: string | number;
  expected_budget: string | number;
  actual_generation: string | number;
  created_at: string;
  updated_at: string;
}

export interface PortfolioMapData {
  mapData: MapDataEntry[];
  yieldData: YieldDataEntry[];
}

export interface PortfolioMapFilters {
  country?: string[];
  plantType?: string[];
  installationType?: string[];
  portfolio?: string[];
  assetNo?: string[];
  offtaker?: string[];
  cod?: string[];
  [key: string]: unknown; // For FilterState compatibility
}

export type PerformanceFilter = 'all' | 'excellent' | 'good' | 'poor';

export interface KPIMetrics {
  siteCount: number;
  pvCapacity: number;
  bessCapacity: number;
}

export interface MarkerInfo {
  data: MapDataEntry;
  performancePercentage: number | null;
  performanceCategory: 'excellent' | 'good' | 'poor' | 'default';
}

