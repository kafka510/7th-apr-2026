/**
 * Generation Report calculation utilities
 * These match the logic from the old JavaScript implementation
 */

import type { GenerationDailyData, YieldDataRow, MapDataRow } from '../types';

/**
 * Parse date string to Date object (handles multiple formats)
 */
export function parseCsvDate(str: string | number | null | undefined): Date | null {
  if (str === null || str === undefined || str === '') return null;
  if (typeof str === 'number') {
    const d = new Date(str);
    if (!isNaN(d.getTime())) {
      return new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
    }
    return null;
  }
  const dateStr = String(str).trim();

  // DD-MM-YYYY
  if (/^\d{1,2}-\d{1,2}-\d{4}$/.test(dateStr)) {
    const [d, mo, y] = dateStr.split('-').map(Number);
    return new Date(Date.UTC(y, mo - 1, d));
  }
  // YYYY-MM-DD
  if (/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) {
    const [y, mo, d] = dateStr.split('-').map(Number);
    return new Date(Date.UTC(y, mo - 1, d));
  }
  // M/D/YYYY or MM/DD/YYYY
  if (/^\d{1,2}\/\d{1,2}\/\d{4}$/.test(dateStr)) {
    const [mo, d, y] = dateStr.split('/').map(Number);
    return new Date(Date.UTC(y, mo - 1, d));
  }
  // ISO / fallback
  const parsed = Date.parse(dateStr);
  if (!isNaN(parsed)) {
    const d = new Date(parsed);
    return new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
  }
  return null;
}

/**
 * Convert date string to YYYY-MM format
 */
export function toYYYYMM(dateStr: string | null | undefined): string {
  const d = parseCsvDate(dateStr);
  if (!d || isNaN(d.getTime())) return '';
  const y = d.getUTCFullYear();
  const m = d.getUTCMonth() + 1;
  return `${y}-${m < 10 ? '0' + m : m}`;
}

/**
 * Get DC capacity for an asset and month
 */
export function getDcCapacityForMonth(
  asset: string,
  selectedMonth: string | null | undefined,
  yieldData: YieldDataRow[],
  mapData: MapDataRow[]
): number {
  if (!asset) return 0;

  const monthKey = (selectedMonth || '').trim();
  
  // 1) Try yieldData index (fastest)
  if (monthKey) {
    const row = yieldData.find(
      (r) => r.assetno?.trim() === asset.trim() && r.month?.trim() === monthKey
    );
    if (row && row.dc_capacity_mw) {
      return Number(row.dc_capacity_mw) || 0;
    }
  }

  // 2) Find most recent dc_capacity in yieldData for asset
  const candidates = yieldData.filter(
    (r) =>
      r.assetno?.trim() === asset.trim() &&
      r.dc_capacity_mw
  );
  if (candidates.length) {
    candidates.sort((a, b) => (b.month || '').localeCompare(a.month || ''));
    return Number(candidates[0].dc_capacity_mw) || 0;
  }

  // 3) mapData fallback
  const mapRow = mapData.find(
    (r) =>
      r.asset_no === asset ||
      r.asset_no === asset.trim()
  );
  if (mapRow && mapRow.dc_capacity_mwp) {
    return Number(mapRow.dc_capacity_mwp) || 0;
  }

  return 0;
}

/**
 * Sum daily data over a date range for specific assets
 */
export function sumDaily(
  df: GenerationDailyData[],
  assets: string[],
  startDate: Date,
  endDate: Date
): number {
  if (!df.length) return 0;

  const assetCols = assets.filter((a) => df.some((row) => row[a] !== undefined));
  let sum = 0;

  df.forEach((row) => {
    const rowDate = parseCsvDate(row.Date || row.date);
    if (!rowDate) return;
    if (rowDate >= startDate && rowDate <= endDate) {
      assetCols.forEach((a) => {
        const val = row[a];
        if (val !== undefined && val !== null && val !== '') {
          sum += parseFloat(String(val)) || 0;
        }
      });
    }
  });

  return sum;
}

/**
 * Sum GII data over a date range
 */
export function sumGii(
  df: GenerationDailyData[],
  assets: string[],
  startDate: Date,
  endDate: Date
): number {
  if (!df.length) return 0;

  const assetCols = assets.filter((a) => df.some((row) => row[a] !== undefined));
  let sum = 0;

  df.forEach((row) => {
    const rowDate = parseCsvDate(row.Date || row.date);
    if (!rowDate) return;
    if (rowDate >= startDate && rowDate <= endDate) {
      assetCols.forEach((a) => {
        const val = row[a];
        if (val !== undefined && val !== null && val !== '') {
          sum += parseFloat(String(val)) || 0;
        }
      });
    }
  });

  return sum;
}

/**
 * Safe PR calculation
 */
export function safePR(ic: number, dc: number, gii: number): number | null {
  if (!dc || dc <= 0) return null;
  if (!gii || gii <= 0) return null;
  const pr = (ic / (dc * gii)) * 100;
  return Number.isFinite(pr) ? pr : null;
}

/**
 * Format number with commas
 */
export function formatNumber(val: number | string): string {
  const num = typeof val === 'number' ? val : parseFloat(String(val));
  if (isNaN(num)) return '';
  return Math.round(num).toLocaleString('en-US');
}

/**
 * Format number in millions
 */
export function formatMillion(val: number): string {
  if (!Number.isFinite(val)) return '';
  const absVal = Math.abs(val);
  if (absVal < 1e6) return (val / 1e6).toFixed(2) + 'M';
  return (val / 1e6).toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }) + 'M';
}

/**
 * Get the appropriate month for DC capacity lookup
 */
export function getDcCapacityMonth(
  period: { range?: { start?: string; end?: string }; month?: string } | null,
  _startMonth: string,
  endMonth: string
): string {
  if (period?.range?.start && period.range.end) {
    return endMonth; // Range selection: use latest month
  } else if (period?.month) {
    return period.month; // Single month selection
  }
  return endMonth; // Fallback
}

