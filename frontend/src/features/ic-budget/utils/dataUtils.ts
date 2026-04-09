/**
 * Generation Budget Insights - Data Utilities
 * Utility functions for IC Budget data processing
 */

import type { ICBudgetDataEntry, AggregatedRow } from '../types';

/**
 * Parse numeric value, handling null, undefined, NaN, and empty strings
 */
export function parseNumeric(value: unknown): number {
  if (value === null || value === undefined) {
    return 0;
  }
  
  if (typeof value === 'number') {
    return Number.isFinite(value) ? value : 0;
  }
  
  if (typeof value === 'string') {
    const trimmed = value.trim();
    if (trimmed === '' || trimmed === 'null' || trimmed === 'undefined' || trimmed === 'None' || trimmed === 'NaN') {
      return 0;
    }
    // Remove commas and parse
    const num = parseFloat(trimmed.replace(/,/g, ''));
    return Number.isFinite(num) ? num : 0;
  }
  
  return 0;
}

/**
 * Check if a month is up to the cutoff (N-1, previous month)
 */
export function isUpToCutoff(monthSort: string | null, cutoffDate: Date): boolean {
  if (!monthSort) {
    return false;
  }
  
  const cutoffISOString = cutoffDate.toISOString().split('T')[0]; // YYYY-MM-DD format
  return monthSort <= cutoffISOString;
}

/**
 * Convert month string to Date object
 */
export function convertMonthToDate(monthStr: string | null): Date | null {
  if (!monthStr) {
    return null;
  }
  
  const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const parts = monthStr.split(' ');
  
  if (parts.length >= 2) {
    const monthPart = parts[0];
    const yearPart = parts[1];
    
    const monthIndex = monthNames.indexOf(monthPart);
    if (monthIndex !== -1 && yearPart) {
      const year = parseInt(yearPart);
      const month = monthIndex + 1;
      return new Date(year, month - 1, 1);
    }
  }
  
  return null;
}

/**
 * Format number with Indian locale
 */
export function formatNumber(value: number): string {
  if (!Number.isFinite(value)) {
    return '';
  }
  return Math.round(value).toLocaleString('en-IN');
}

/**
 * Format percentage value
 */
export function formatPercentage(value: number): string {
  if (!Number.isFinite(value) || value === 0) {
    return '';
  }
  return value.toFixed(2) + '%';
}

/**
 * Aggregate data by month
 */
export function aggregateByMonth(
  data: ICBudgetDataEntry[],
  cutoffDate: Date
): { aggregatedRows: AggregatedRow[]; totalSums: Record<string, number>; totalCounts: Record<string, number> } {
  // Group by month
  const monthMap: Record<string, ICBudgetDataEntry[]> = {};
  data.forEach((row) => {
    const month = row.month;
    if (month) {
      if (!monthMap[month]) {
        monthMap[month] = [];
      }
      monthMap[month].push(row);
    }
  });

  // Sort months chronologically
  const monthsInData = Object.keys(monthMap);
  monthsInData.sort((a, b) => {
    const aRow = data.find((row) => row.month === a);
    const bRow = data.find((row) => row.month === b);
    
    const aSort = aRow?.month_sort || a;
    const bSort = bRow?.month_sort || b;
    
    return aSort.localeCompare(bSort);
  });

  const displayHeaders = [
    'IC Approved Budget (MWh)',
    'Expected Budget (MWh)',
    'Actual Generation (MWh)',
    'Grid Curtailment Budget (MWh)',
    'Actual Curtailment (MWh)',
    'Budget Irradiation (kWh/M2)',
    'Actual Irradiation (kWh/M2)',
  ];

  const totalSums: Record<string, number> = {};
  const totalCounts: Record<string, number> = {};
  displayHeaders.forEach((h) => {
    totalSums[h] = 0;
    totalCounts[h] = 0;
  });
  totalSums['Expected PR (%)'] = 0;
  totalCounts['Expected PR (%)'] = 0;
  totalSums['Actual PR (%)'] = 0;
  totalCounts['Actual PR (%)'] = 0;

  const aggregatedRows: AggregatedRow[] = [];

  monthsInData.forEach((month) => {
    const rows = monthMap[month];
    const agg: AggregatedRow = {
      Month: month,
      'IC Approved Budget (MWh)': 0,
      'Expected Budget (MWh)': 0,
      'Actual Generation (MWh)': 0,
      'Grid Curtailment Budget (MWh)': 0,
      'Actual Curtailment (MWh)': 0,
      'Budget Irradiation (kWh/M2)': 0,
      'Actual Irradiation (kWh/M2)': 0,
      'Expected PR (%)': 0,
      'Actual PR (%)': 0,
    };

    // Sum numeric columns
    displayHeaders.forEach((header) => {
      // Map display header to data field name
      const fieldMap: Record<string, keyof ICBudgetDataEntry> = {
        'IC Approved Budget (MWh)': 'ic_approved_budget_mwh',
        'Expected Budget (MWh)': 'expected_budget_mwh',
        'Actual Generation (MWh)': 'actual_generation_mwh',
        'Grid Curtailment Budget (MWh)': 'grid_curtailment_budget_mwh',
        'Actual Curtailment (MWh)': 'actual_curtailment_mwh',
        'Budget Irradiation (kWh/M2)': 'budget_irradiation_kwh_m2',
        'Actual Irradiation (kWh/M2)': 'actual_irradiation_kwh_m2',
      };
      
      const fieldName = fieldMap[header];
      const sum = rows.reduce((acc, r) => {
        const value = fieldName ? r[fieldName] : null;
        return acc + parseNumeric(value);
      }, 0);
      (agg as unknown as Record<string, number>)[header] = sum;
      
      // Only sum for totals if up to cutoff
      const firstRow = rows[0];
      if (firstRow && isUpToCutoff(firstRow.month_sort, cutoffDate)) {
        totalSums[header] += sum;
      }
    });

    // Average for PR%
    ['Expected PR (%)', 'Actual PR (%)'].forEach((header) => {
      const fieldName = header === 'Expected PR (%)' ? 'expected_pr_percent' : 'actual_pr_percent';
      const vals = rows
        .map((r) => {
          const value = r[fieldName];
          const numValue = parseNumeric(value);
          return numValue > 0 ? numValue : null;
        })
        .filter((v): v is number => v !== null);

      const avg = vals.length > 0 ? vals.reduce((a, b) => a + b, 0) / vals.length : 0;
      (agg as unknown as Record<string, number>)[header] = avg;

      // Only count for totals if up to cutoff
      const firstRow = rows[0];
      if (firstRow && isUpToCutoff(firstRow.month_sort, cutoffDate)) {
        totalSums[header] += avg;
        totalCounts[header] += vals.length;
      }
    });

    aggregatedRows.push(agg);
  });

  return { aggregatedRows, totalSums, totalCounts };
}

