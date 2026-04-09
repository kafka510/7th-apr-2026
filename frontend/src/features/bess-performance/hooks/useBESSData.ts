import { useState, useEffect, useMemo } from 'react';
import { fetchBESSData } from '../api';
import type { BESSData, BESSFilters, BESSFilterOptions, BESSKPIData, BESSChartData } from '../types';

interface UseBESSDataReturn {
  bessData: BESSData[];
  filterOptions: BESSFilterOptions;
  filteredData: BESSData[];
  kpiData: BESSKPIData[];
  chartData: BESSChartData;
  loading: boolean;
  error: Error | null;
}

// Convert BESS month format (YY-MMM) to YYYY-MM for comparison
function normalizeMonthFormat(month: string | null | undefined): string | null {
  if (!month) return null;
  const parts = month.split('-');
  if (parts.length !== 2) return null;
  
  const [yearPart, monthName] = parts;
  const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const monthIndex = monthNames.indexOf(monthName);
  if (monthIndex === -1) return null;
  
  const fullYear = '20' + yearPart; // "25" -> "2025"
  const monthNum = String(monthIndex + 1).padStart(2, '0');
  return `${fullYear}-${monthNum}`;
}

// Check if a row's month matches the selected month/year/range
function isInSelectedMonth(
  rowMonth: string | null | undefined, 
  selectedMonth: string | null, 
  selectedYear: string | null,
  selectedRange: { start: string; end: string } | null
): boolean {
  if (!rowMonth) return false;

  const normalizedRow = normalizeMonthFormat(rowMonth);
  if (!normalizedRow) return false;

  if (selectedMonth) {
    return normalizedRow === selectedMonth;
  } else if (selectedYear) {
    return normalizedRow.startsWith(selectedYear);
  } else if (selectedRange) {
    return normalizedRow >= selectedRange.start && normalizedRow <= selectedRange.end;
  }

  return true; // No month/year/range filter means show all
}

function getAvailableMonths(data: BESSData[]): string[] {
  const months = Array.from(new Set(data.map((r) => r.month).filter(Boolean)));
  // Convert to YYYY-MM format for MonthPicker
  const normalizedMonths = months
    .map(m => normalizeMonthFormat(m))
    .filter((m): m is string => m !== null)
    .sort();
  return normalizedMonths;
}

export function useBESSData(filters: BESSFilters): UseBESSDataReturn {
  const [bessData, setBessData] = useState<BESSData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetchBESSData(controller.signal)
      .then((data) => {
        setBessData(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err);
        setBessData([]);
        setLoading(false);
      });
    return () => {
      controller.abort();
    };
  }, []);

  const filterOptions = useMemo<BESSFilterOptions>(() => {
    const months = getAvailableMonths(bessData);
    const years = Array.from(new Set(months.map((m) => {
      const normalized = normalizeMonthFormat(m);
      return normalized ? normalized.slice(0, 4) : null;
    }).filter(Boolean))).sort();
    const countries = Array.from(new Set(bessData.map((r) => r.country).filter(Boolean))).sort();
    const portfolios = Array.from(new Set(bessData.map((r) => r.portfolio).filter(Boolean))).sort();
    const assets = Array.from(new Set(bessData.map((r) => r.asset_no).filter(Boolean))).sort();
    return { months, years: years as string[], countries, portfolios, assets };
  }, [bessData]);

  const filteredData = useMemo<BESSData[]>(() => {
    let filtered = bessData.slice();

    // Filter by month/year/range
    if (filters.month || filters.year || filters.range) {
      filtered = filtered.filter((r) => 
        isInSelectedMonth(r.month, filters.month || null, filters.year || null, filters.range || null)
      );
    }

    // Filter by country
    if (filters.country && filters.country.length > 0) {
      filtered = filtered.filter((r) => filters.country!.includes(r.country));
    }

    // Filter by portfolio
    if (filters.portfolio && filters.portfolio.length > 0) {
      filtered = filtered.filter((r) => filters.portfolio!.includes(r.portfolio));
    }

    // Filter by asset
    if (filters.asset && filters.asset.length > 0) {
      filtered = filtered.filter((r) => {
        const rowAssetString = String(r.asset_no).trim();
        return filters.asset!.some((selectedAsset) => {
          const selectedAssetString = String(selectedAsset).trim();
          return (
            rowAssetString === selectedAssetString ||
            rowAssetString.endsWith(selectedAssetString) ||
            selectedAssetString.endsWith(rowAssetString)
          );
        });
      });
    }

    return filtered;
  }, [bessData, filters]);

  const kpiData = useMemo<BESSKPIData[]>(() => {
    if (filteredData.length === 0) return [];

    const getMinMax = (data: BESSData[], field: keyof BESSData, isMin = true): string => {
      const values = data
        .map((r) => {
          const val = r[field];
          if (val === null || val === undefined) return null;
          const num = typeof val === 'string' ? parseFloat(val) : val;
          return typeof num === 'number' && !isNaN(num) ? num : null;
        })
        .filter((v): v is number => v !== null);
      if (values.length === 0) return '-';
      return isMin ? Math.min(...values).toFixed(2) : Math.max(...values).toFixed(2);
    };

    // Calculate average RTE
    const rteValues: number[] = [];
    const assetSet = new Set<string>();
    filteredData.forEach((r) => {
      if (r.asset_no && !assetSet.has(r.asset_no)) {
        const rteValue = typeof r.rte === 'string' ? parseFloat(r.rte) : r.rte;
        if (typeof rteValue === 'number' && !isNaN(rteValue) && rteValue > 0) {
          rteValues.push(rteValue);
          assetSet.add(r.asset_no);
        }
      }
    });
    const avgRTE = rteValues.length > 0 ? (rteValues.reduce((sum, v) => sum + v, 0) / rteValues.length).toFixed(2) + '%' : '-';

    // Calculate battery capacity
    // Use the latest month from filtered data for capacity calculation (similar to CapacityCards)
    const filteredMonths = [...new Set(filteredData.map((r) => r.month).filter((m): m is string => Boolean(m)))].sort();
    const latestMonth = filteredMonths.length > 0 ? filteredMonths[filteredMonths.length - 1] : null;
    
    // Filter to latest month only for capacity calculations
    const latestMonthData = latestMonth
      ? filteredData.filter((r) => r.month === latestMonth)
      : filteredData;
    
    let batteryCap = '-';
    const capacitySet = new Set<string>();
    let sum = 0;
    latestMonthData.forEach((r) => {
      if (r.asset_no && !capacitySet.has(r.asset_no)) {
        const cap = typeof r.battery_capacity_mw === 'string' ? parseFloat(r.battery_capacity_mw) : r.battery_capacity_mw;
        if (typeof cap === 'number' && !isNaN(cap)) {
          sum += cap;
          capacitySet.add(r.asset_no);
        }
      }
    });
    batteryCap = sum > 0 ? sum.toFixed(2) : '-';

    return [
      { label: 'Min SOC', value: getMinMax(filteredData, 'min_soc', true), unit: '%', icon: '📊', color: '#fbbf24', bgGradient: 'linear-gradient(135deg, #fffbeb, #fef3c7)' },
      { label: 'Max SOC', value: getMinMax(filteredData, 'max_soc', false), unit: '%', icon: '📈', color: '#8b5cf6', bgGradient: 'linear-gradient(135deg, #f5f3ff, #e0e7ff)' },
      { label: 'Min ESS Temperature', value: getMinMax(filteredData, 'min_ess_temperature', true), unit: '°C', icon: '❄️', color: '#06b6d4', bgGradient: 'linear-gradient(135deg, #ecfeff, #cffafe)' },
      { label: 'Max ESS Temperature', value: getMinMax(filteredData, 'max_ess_temperature', false), unit: '°C', icon: '🔥', color: '#22c55e', bgGradient: 'linear-gradient(135deg, #f0fdf4, #dcfce7)' },
      { label: 'Min ESS Humidity', value: getMinMax(filteredData, 'min_ess_humidity', true), unit: '%', icon: '💧', color: '#d946ef', bgGradient: 'linear-gradient(135deg, #fef7ff, #fae8ff)' },
      { label: 'Max ESS Humidity', value: getMinMax(filteredData, 'max_ess_humidity', false), unit: '%', icon: '🌧️', color: '#f97316', bgGradient: 'linear-gradient(135deg, #fffbeb, #fed7aa)' },
      { label: 'Battery Capacity', value: batteryCap, unit: 'MWh', icon: '🔋', color: '#3b82f6', bgGradient: 'linear-gradient(135deg, #f0f9ff, #dbeafe)' },
      { label: 'Average RTE', value: avgRTE, unit: '', icon: '⚡', color: '#10b981', bgGradient: 'linear-gradient(135deg, #ecfdf5, #d1fae5)' },
    ];
  }, [filteredData]);

  const chartData = useMemo<BESSChartData>(() => {
    // Group data by month
    const monthGroups: Record<string, BESSData[]> = {};
    filteredData.forEach((row) => {
      const month = row.month;
      if (!month) return;
      if (!monthGroups[month]) monthGroups[month] = [];
      monthGroups[month].push(row);
    });

    // Sort months chronologically using normalized format
    const months = Object.keys(monthGroups).sort((a, b) => {
      const normalizedA = normalizeMonthFormat(a);
      const normalizedB = normalizeMonthFormat(b);
      if (!normalizedA || !normalizedB) return 0;
      return normalizedA.localeCompare(normalizedB);
    });
    const pvEnergy = months.map((m) => {
      return monthGroups[m].reduce((sum, r) => {
        const val = typeof r.pv_energy_kwh === 'string' ? parseFloat(r.pv_energy_kwh) : r.pv_energy_kwh;
        return sum + (typeof val === 'number' && !isNaN(val) ? val : 0);
      }, 0);
    });
    const exportEnergy = months.map((m) => {
      return monthGroups[m].reduce((sum, r) => {
        const val = typeof r.export_energy_kwh === 'string' ? parseFloat(r.export_energy_kwh) : r.export_energy_kwh;
        return sum + (typeof val === 'number' && !isNaN(val) ? val : 0);
      }, 0);
    });
    const chargeEnergy = months.map((m) => {
      return monthGroups[m].reduce((sum, r) => {
        const val = typeof r.charge_energy_kwh === 'string' ? parseFloat(r.charge_energy_kwh) : r.charge_energy_kwh;
        return sum + (typeof val === 'number' && !isNaN(val) ? val : 0);
      }, 0);
    });
    const dischargeEnergy = months.map((m) => {
      return monthGroups[m].reduce((sum, r) => {
        const val = typeof r.discharge_energy_kwh === 'string' ? parseFloat(r.discharge_energy_kwh) : r.discharge_energy_kwh;
        return sum + (typeof val === 'number' && !isNaN(val) ? val : 0);
      }, 0);
    });

    return { months, pvEnergy, exportEnergy, chargeEnergy, dischargeEnergy };
  }, [filteredData]);

  return { bessData, filterOptions, filteredData, kpiData, chartData, loading, error };
}

