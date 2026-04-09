import { useState, useEffect, useMemo } from 'react';
import { fetchMinamataData } from '../api';
import type { MinamataData, MinamataTableRow } from '../types';

interface UseMinamataDataReturn {
  minamataData: MinamataData[];
  tableRows: MinamataTableRow[];
  loading: boolean;
  error: Error | null;
}

// Helper to parse month string (e.g., "25-Jan" or "Jan-25")
function parseMonth(monthStr: string): { year: number; month: number } | null {
  if (!monthStr) return null;
  
  const monthNames = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'];
  
  // Handle "25-Jan" or "Jan-25" format
  const parts = monthStr.split('-');
  if (parts.length === 2) {
    const [part1, part2] = parts;
    let year: number | null = null;
    let monthIndex: number | null = null;
    
    // Check if first part is year
    if (/^\d+$/.test(part1)) {
      year = parseInt(part1, 10);
      if (year < 100) year += 2000;
      monthIndex = monthNames.indexOf(part2.toLowerCase());
    } else if (/^\d+$/.test(part2)) {
      year = parseInt(part2, 10);
      if (year < 100) year += 2000;
      monthIndex = monthNames.indexOf(part1.toLowerCase());
    }
    
    if (year !== null && monthIndex !== null && monthIndex >= 0) {
      return { year, month: monthIndex };
    }
  }
  
  return null;
}

// Sort months chronologically
function sortMonths(data: MinamataData[]): MinamataData[] {
  return [...data].sort((a, b) => {
    const aMonth = parseMonth(a.month);
    const bMonth = parseMonth(b.month);
    
    if (!aMonth && !bMonth) return 0;
    if (!aMonth) return 1;
    if (!bMonth) return -1;
    
    if (aMonth.year !== bMonth.year) {
      return aMonth.year - bMonth.year;
    }
    
    return aMonth.month - bMonth.month;
  });
}

export function useMinamataData(): UseMinamataDataReturn {
  const [minamataData, setMinamataData] = useState<MinamataData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetchMinamataData(controller.signal)
      .then((data) => {
        setMinamataData(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err);
        setMinamataData([]);
        setLoading(false);
      });
    return () => { controller.abort(); };
  }, []);

  const tableRows = useMemo<MinamataTableRow[]>(() => {
    // Separate total rows from data rows
    const totalRows = minamataData.filter((row) => 
      (row.month || '').toLowerCase().includes('total')
    );
    
    const dataRows = minamataData.filter((row) => {
      const monthVal = String(row.month || '').trim();
      // Filter out total rows and invalid months
      if (!monthVal || monthVal.toLowerCase().includes('total') || monthVal.toLowerCase() === 'nan') {
        return false;
      }
      // Allow pure numeric months (they might be valid in some formats)
      // Just ensure it's not empty
      return monthVal.length > 0;
    });
    
    // Sort data rows chronologically
    const sortedDataRows = sortMonths(dataRows);
    
    // Process data rows
    const processedRows: MinamataTableRow[] = sortedDataRows.map((row) => ({
      month: row.month,
      no_of_strings_breakdown: row.no_of_strings_breakdown || '',
      budgeted_gen_mwh: parseFloat(String(row.budgeted_gen_mwh || 0)) || 0,
      loss_due_to_string_failure_mwh: parseFloat(String(row.loss_due_to_string_failure_mwh || 0)) || 0,
      loss_in_usd: parseFloat(String(row.loss_in_usd || 0)) || 0,
      isTotal: false,
    }));
    
    // Process total rows or create one
    let finalTotalRows: MinamataTableRow[] = [];
    
    if (totalRows.length === 0 && processedRows.length > 0) {
      // Calculate totals from data rows
      const latestRow = processedRows[processedRows.length - 1];
      const totalBudgeted = processedRows.reduce((sum, r) => sum + r.budgeted_gen_mwh, 0);
      const totalLossMWh = processedRows.reduce((sum, r) => sum + r.loss_due_to_string_failure_mwh, 0);
      const totalLossUSD = processedRows.reduce((sum, r) => sum + r.loss_in_usd, 0);
      
      finalTotalRows = [{
        month: 'Total',
        no_of_strings_breakdown: latestRow.no_of_strings_breakdown,
        budgeted_gen_mwh: Math.round(totalBudgeted),
        loss_due_to_string_failure_mwh: Math.round(totalLossMWh),
        loss_in_usd: Math.round(totalLossUSD),
        isTotal: true,
      }];
    } else if (totalRows.length > 0) {
      // Use existing total row(s)
      const latestRow = processedRows.length > 0 ? processedRows[processedRows.length - 1] : null;
      finalTotalRows = totalRows.map((row) => {
        // Recalculate totals if needed
        const totalLossMWh = processedRows.reduce((sum, r) => sum + r.loss_due_to_string_failure_mwh, 0);
        
        return {
          month: row.month,
          no_of_strings_breakdown: latestRow ? latestRow.no_of_strings_breakdown : (row.no_of_strings_breakdown || ''),
          budgeted_gen_mwh: parseFloat(String(row.budgeted_gen_mwh || 0)) || 0,
          loss_due_to_string_failure_mwh: Math.round(totalLossMWh),
          loss_in_usd: parseFloat(String(row.loss_in_usd || 0)) || 0,
          isTotal: true,
        };
      });
    }
    
    return [...processedRows, ...finalTotalRows];
  }, [minamataData]);

  return { minamataData, tableRows, loading, error };
}

