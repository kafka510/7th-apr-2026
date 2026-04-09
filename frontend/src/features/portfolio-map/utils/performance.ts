/**
 * Utility functions for performance calculations
 */
import type { YieldDataEntry } from '../types';

/**
 * Parse numeric value from string/number, handling commas and whitespace
 */
export function parseNumeric(value: string | number | null | undefined): number {
  if (value === undefined || value === null) return NaN;
  const str = String(value).trim();
  // Handle empty strings explicitly
  if (str === '' || str === 'null' || str === 'undefined' || str === 'None' || str === 'NaN') return NaN;
  const normalized = str.replace(/[\s,]/g, '');
  const match = normalized.match(/-?\d+(?:\.\d+)?/);
  return match ? Number(match[0]) : NaN;
}

/**
 * Convert month string to timestamp
 * Supports 'YYYY-MM', 'YYYY/M', 'Jan-2025', 'July-2025'
 */
export function toTimestamp(monthStr: string | null | undefined): number {
  if (!monthStr) return NaN;
  const s = String(monthStr).trim();
  
  // YYYY-MM or YYYY-M
  let m = s.match(/^(\d{4})-(\d{1,2})$/);
  if (m) return Date.UTC(Number(m[1]), Number(m[2]) - 1, 1);
  
  // YYYY/MM
  m = s.match(/^(\d{4})\/(\d{1,2})$/);
  if (m) return Date.UTC(Number(m[1]), Number(m[2]) - 1, 1);
  
  // MonthName-YYYY (Jan/January etc)
  m = s.match(/^([A-Za-z]+)-(\d{4})$/);
  if (m) {
    const names = [
      'january', 'february', 'march', 'april', 'may', 'june',
      'july', 'august', 'september', 'october', 'november', 'december'
    ];
    const idx = names.indexOf(m[1].toLowerCase());
    if (idx >= 0) return Date.UTC(Number(m[2]), idx, 1);
  }
  
  const ts = Date.parse(s);
  return isNaN(ts) ? NaN : ts;
}

/**
 * Extract year and month from month string
 * Returns { year: number, month: number } or null if invalid
 * Month is 1-12 (not 0-based)
 */
export function parseYearMonth(monthStr: string | null | undefined): { year: number; month: number } | null {
  if (!monthStr) return null;
  const s = String(monthStr).trim();
  
  // YYYY-MM or YYYY-M
  let m = s.match(/^(\d{4})-(\d{1,2})$/);
  if (m) {
    const year = Number(m[1]);
    const month = Number(m[2]);
    if (year > 0 && month >= 1 && month <= 12) {
      return { year, month };
    }
  }
  
  // YYYY/MM
  m = s.match(/^(\d{4})\/(\d{1,2})$/);
  if (m) {
    const year = Number(m[1]);
    const month = Number(m[2]);
    if (year > 0 && month >= 1 && month <= 12) {
      return { year, month };
    }
  }
  
  // MonthName-YYYY (Jan/January etc)
  m = s.match(/^([A-Za-z]+)-(\d{4})$/);
  if (m) {
    const names = [
      'january', 'february', 'march', 'april', 'may', 'june',
      'july', 'august', 'september', 'october', 'november', 'december'
    ];
    const idx = names.indexOf(m[1].toLowerCase());
    const year = Number(m[2]);
    if (idx >= 0 && year > 0) {
      return { year, month: idx + 1 }; // Convert 0-based to 1-based
    }
  }
  
  return null;
}

/**
 * Get the number of days in a given month and year
 */
export function getDaysInMonth(year: number, month: number): number {
  // month is 1-12 (not 0-based)
  return new Date(year, month, 0).getDate();
}

/**
 * Get yesterday's date (n-1)
 */
export function getYesterday(): Date {
  const yesterday = new Date();
  yesterday.setDate(yesterday.getDate() - 1);
  return yesterday;
}

/**
 * Calculate performance achievement percentage for an asset
 * Yearly-based calculation with n-1 date logic (completion till yesterday)
 * 
 * Logic:
 * - Filters data for current year only
 * - For past months: uses full month budget
 * - For current month: pro-rates budget based on days elapsed till yesterday (n-1)
 * - Calculates YTD performance: (actual_YTD_till_yesterday / budget_YTD_till_yesterday) * 100
 */
export function calculatePerformanceAchievement(
  assetNo: string,
  yieldData: YieldDataEntry[],
  cutoffMonth: string | null = null
): number | null {
  if (!yieldData || yieldData.length === 0) {
    return null;
  }

  // Get current date and yesterday (n-1)
  const today = new Date();
  const yesterday = getYesterday();
  const currentYear = today.getFullYear();
  const currentMonth = today.getMonth() + 1; // 1-12 (not 0-based)
  const daysElapsedInCurrentMonth = yesterday.getDate(); // Days up to yesterday

  // Filter by asset number first
  let rows = yieldData.filter((row) => String(row.assetno).trim() === String(assetNo).trim());
  
  if (rows.length === 0) {
    return null;
  }

  // If cutoffMonth is provided, use it for backward compatibility
  // Otherwise, use yearly n-1 logic
  if (cutoffMonth) {
    const cutoffTs = toTimestamp(cutoffMonth);
    rows = rows.filter((row) => {
      const rowTs = toTimestamp(row.month);
      if (!Number.isFinite(rowTs)) return false;
      return rowTs <= cutoffTs;
    });
  } else {
    // Yearly n-1 logic: filter for current year only
    rows = rows.filter((row) => {
      const yearMonth = parseYearMonth(row.month);
      if (!yearMonth) return false;
      
      // Include only current year data
      if (yearMonth.year !== currentYear) return false;
      
      // For current month, only include if it's the current month
      // (data should represent generation till yesterday)
      if (yearMonth.month === currentMonth) {
        return true; // Current month data (already represents data till yesterday)
      }
      
      // Include all past months in current year
      return yearMonth.month < currentMonth;
    });
  }
    
  if (rows.length === 0) {
    return null;
  }

  let totalActual = 0;
  let totalBudget = 0;
  
  for (const r of rows) {
    const actual = parseNumeric(r.actual_generation);
    const budget = parseNumeric(r.ic_approved_budget);
    
    // Add actual generation (already represents data till yesterday for current month)
    if (Number.isFinite(actual)) {
      totalActual += actual;
    }
    
    // Calculate budget with pro-rating for current month
    if (Number.isFinite(budget) && budget > 0) {
      const yearMonth = parseYearMonth(r.month);
      
      if (yearMonth && yearMonth.year === currentYear && yearMonth.month === currentMonth) {
        // Current month: pro-rate budget based on days elapsed till yesterday
        const daysInMonth = getDaysInMonth(currentYear, currentMonth);
        const proRatedBudget = budget * (daysElapsedInCurrentMonth / daysInMonth);
        totalBudget += proRatedBudget;
      } else {
        // Past months: use full month budget
        totalBudget += budget;
      }
    }
  }

  if (!Number.isFinite(totalBudget) || totalBudget <= 0) {
    return null;
  }

  const percentage = (totalActual / totalBudget) * 100;
  return percentage;
}

/**
 * Get performance category based on achievement percentage
 */
export function getPerformanceCategory(achievementPercentage: number | null): 'excellent' | 'good' | 'poor' | 'default' {
  if (achievementPercentage === null) return 'default';
  if (achievementPercentage >= 90) return 'excellent';
  if (achievementPercentage >= 70) return 'good';
  return 'poor';
}

/**
 * Get marker color based on performance category
 */
export function getMarkerColor(category: 'excellent' | 'good' | 'poor' | 'default'): string {
  const colorScheme = {
    excellent: '#2E8B57', // Dark Green 3 for ≥90% achievement
    good: '#FFB800',      // Dark Yellow 3 for 70–90% achievement
    poor: '#B22222',      // Dark Red 3 for <70% achievement
    default: '#6B7280',   // Dark gray for unknown
  };
  return colorScheme[category] || colorScheme.default;
}

/**
 * Format COD date to DD-MMM-YYYY format
 */
export function formatCODDate(dateStr: string | null | undefined): string {
  if (!dateStr || dateStr === 'N/A') return 'N/A';
  
  // Try to parse the date string
  let date = new Date(dateStr);
  
  // If parsing failed, try MM/DD/YYYY format specifically
  if (isNaN(date.getTime())) {
    const parts = dateStr.split('/');
    if (parts.length === 3) {
      // MM/DD/YYYY format
      const month = parseInt(parts[0], 10) - 1; // JavaScript months are 0-based
      const day = parseInt(parts[1], 10);
      const year = parseInt(parts[2], 10);
      date = new Date(year, month, day);
    }
  }
  
  // If still invalid, return original string
  if (isNaN(date.getTime())) {
    return dateStr;
  }
  
  // Format to DD-MMM-YYYY
  const day = date.getDate().toString().padStart(2, '0');
  const monthNames = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 
                     'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'];
  const month = monthNames[date.getMonth()];
  const year = date.getFullYear();
  
  return `${day}-${month}-${year}`;
}

/**
 * Normalize value by trimming whitespace
 */
export function normalizeValue(value: string | number | null | undefined): string {
  return String(value ?? '').trim();
}

