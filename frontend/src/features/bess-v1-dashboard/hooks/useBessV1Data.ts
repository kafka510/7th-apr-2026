import { useEffect, useMemo, useState } from 'react';
import { fetchBessV1Data, fetchBessDailyData } from '../api';
import type {
  BessV1Aggregates,
  BessV1FilterOptions,
  BessV1Filters,
  BessV1Record,
  UseBessV1DataReturn,
  DailyBessRecord,
  DailyCUFDataPoint,
  DailyCycleDataPoint,
} from '../types';

const MONTH_NAMES = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'];

function normalizeMonth(input?: string | null): string | null {
  if (!input) return null;
  const trimmed = input.trim();
  if (!trimmed) return null;

  // Handle formats like YYYY-MM or YYYY/M
  const match = trimmed.match(/^(\d{4})[-/](\d{1,2})$/);
  if (match) {
    const [, year, month] = match;
    return `${year}-${month.padStart(2, '0')}`;
  }

  // Handle formats like Jan-25 or Jan 2025
  const parts = trimmed.replace(/\s+/g, ' ').split(/[-\s/]/);
  if (parts.length === 2) {
    const maybeMonth = parts[0].toLowerCase();
    const monthIndex = MONTH_NAMES.indexOf(maybeMonth.slice(0, 3));
    if (monthIndex >= 0) {
      const yearPart = parts[1].length === 2 ? `20${parts[1]}` : parts[1];
      if (/^\d{4}$/.test(yearPart)) {
        return `${yearPart}-${String(monthIndex + 1).padStart(2, '0')}`;
      }
    }
  }

  const parsed = new Date(trimmed);
  if (!Number.isNaN(parsed.getTime())) {
    return `${parsed.getFullYear()}-${String(parsed.getMonth() + 1).padStart(2, '0')}`;
  }

  return trimmed;
}

function compareMonths(a: string, b: string): number {
  if (a === b) return 0;
  return a < b ? -1 : 1;
}

function toNumber(value: unknown): number {
  if (value === null || value === undefined || value === '') return 0;
  if (typeof value === 'number') return Number.isNaN(value) ? 0 : value;
  if (typeof value === 'string') {
    const cleaned = value.replace(/,/g, '').replace('%', '').trim();
    const num = Number(cleaned);
    return Number.isNaN(num) ? 0 : num;
  }
  const num = Number(value);
  return Number.isNaN(num) ? 0 : num;
}

function toNumberOrNull(value: unknown): number | null {
  if (value === null || value === undefined || value === '') return null;
  const num = toNumber(value);
  return Number.isNaN(num) ? null : num;
}

function getDaysInMonth(month: string): number {
  const [yearStr, monthStr] = month.split('-');
  const year = Number(yearStr);
  const monthIndex = Number(monthStr);
  if (!Number.isFinite(year) || !Number.isFinite(monthIndex)) return 30;
  return new Date(year, monthIndex, 0).getDate();
}

function isMonthInRange(month: string, start?: string, end?: string): boolean {
  if (!start && !end) return true;
  if (start && compareMonths(month, start) < 0) return false;
  if (end && compareMonths(month, end) > 0) return false;
  return true;
}

function matchesAsset(asset: string | undefined | null, selected: string[]): boolean {
  if (!selected.length) return true;
  if (!asset) return false;
  const normalized = asset.trim();
  return selected.some((value) => {
    const target = value.trim();
    return normalized === target || normalized.endsWith(target) || target.endsWith(normalized);
  });
}

function aggregateBessV1Data(rows: BessV1Record[]): BessV1Aggregates {
  let totalPV = 0;
  let totalCharge = 0;
  let totalDischarge = 0;
  let totalExport = 0;
  let totalPVtoGrid = 0;
  let totalSysLoss = 0;
  let totalGridImport = 0;
  let minSOC: number | null = null;
  let maxSOC: number | null = null;
  let minTemp: number | null = null;
  let maxTemp: number | null = null;
  let latestMonth: string | null = null;
  const uniqueMonths = new Set<string>();

  const actualCUFValues: number[] = [];
  const actualCycleValues: number[] = [];
  const budgetCycleValues: number[] = [];
  const actualRteValues: number[] = [];
  const budgetRteValues: number[] = [];
  const budgetCufValues: number[] = [];

  rows.forEach((row) => {
    const pv = toNumber(row.actual_pv_energy_kwh) / 1000;
    const charge = toNumber(row.actual_charge_energy_kwh) / 1000;
    const discharge = toNumber(row.actual_discharge_energy) / 1000;
    const exportEnergy = toNumber(row.actual_export_energy_kwh) / 1000;
    const pvToGrid = toNumber(row.actual_pv_grid_kwh) / 1000;
    const systemLoss = toNumber(row.actual_system_losses) / 1000;
    const gridImport = toNumber(row.actual_grid_import_kwh) / 1000;

    totalPV += pv;
    totalCharge += charge;
    totalDischarge += discharge;
    totalExport += exportEnergy;
    totalPVtoGrid += pvToGrid;
    totalSysLoss += systemLoss;
    totalGridImport += gridImport;

    const socMin = toNumberOrNull(row.min_soc);
    const socMax = toNumberOrNull(row.max_soc);
    const tempMin = toNumberOrNull(row.min_ess_temp);
    const tempMax = toNumberOrNull(row.max_ess_temp);

    if (socMin !== null) {
      minSOC = minSOC === null ? socMin : Math.min(minSOC, socMin);
    }
    if (socMax !== null) {
      maxSOC = maxSOC === null ? socMax : Math.max(maxSOC, socMax);
    }
    if (tempMin !== null) {
      minTemp = minTemp === null ? tempMin : Math.min(minTemp, tempMin);
    }
    if (tempMax !== null) {
      maxTemp = maxTemp === null ? tempMax : Math.max(maxTemp, tempMax);
    }

    const normalizedMonth = normalizeMonth(row.month);
    if (normalizedMonth) {
      uniqueMonths.add(normalizedMonth);
      if (!latestMonth || compareMonths(normalizedMonth, latestMonth) > 0) {
        latestMonth = normalizedMonth;
      }
    }

    const actualCuf = toNumberOrNull(row.actual_cuf);
    // Note: Monthly actual_cuf is already in percentage format (e.g., 42.24, 51.2)
    // Only daily cuf values need conversion from decimal (0.78) to percentage (78)
    if (actualCuf !== null && actualCuf > 0) {
      actualCUFValues.push(actualCuf);
    }

    const actualCycles = toNumberOrNull(row.actual_no_of_cycles);
    if (actualCycles !== null && actualCycles > 0) {
      actualCycleValues.push(actualCycles);
    }

    // Budget calculations work for ALL years (2025, 2026, etc.)
    // These values come directly from database fields and are year-agnostic
    const budgetCycles = toNumberOrNull(row.budget_no_of_cycles);
    if (budgetCycles !== null && budgetCycles > 0) {
      budgetCycleValues.push(budgetCycles);
    }

    const actualRte = toNumberOrNull(row.actual_avg_rte);
    if (actualRte !== null && actualRte > 0) {
      actualRteValues.push(actualRte);
    }

    const budgetRte = toNumberOrNull(row.budget_avg_rte);
    if (budgetRte !== null && budgetRte > 0) {
      budgetRteValues.push(budgetRte);
    }

    const budgetCuf = toNumberOrNull(row.budget_cuf);
    if (budgetCuf !== null && budgetCuf > 0) {
      budgetCufValues.push(budgetCuf);
    }
  });

  // Calculate total capacity: sum unique assets from latest month only
  let totalCapMWh = 0;
  let avgCapMWh = 0;
  if (latestMonth) {
    // Filter to latest month only for capacity calculation
    const latestMonthRows = rows.filter((row) => {
      const normalizedMonth = normalizeMonth(row.month);
      return normalizedMonth === latestMonth;
    });
    
    // Get unique assets from latest month and sum their capacities
    const assetCapacityMap = new Map<string, number>();
    latestMonthRows.forEach((row) => {
      const assetNo = row.asset_no?.trim();
      if (assetNo && !assetCapacityMap.has(assetNo)) {
        const capacityMwh = toNumber(row.battery_capacity_mwh);
        if (capacityMwh > 0) {
          assetCapacityMap.set(assetNo, capacityMwh);
        }
      }
    });
    
    // Sum capacities from unique assets
    totalCapMWh = Array.from(assetCapacityMap.values()).reduce((sum, cap) => sum + cap, 0);
    
    // Calculate average for other calculations (CUF, cycles, etc.)
    const capacityValues = Array.from(assetCapacityMap.values());
    avgCapMWh = capacityValues.length > 0 ? capacityValues.reduce((sum, cap) => sum + cap, 0) / capacityValues.length : 0;
  }
  
  const numDays = Array.from(uniqueMonths).reduce((sum, month) => sum + getDaysInMonth(month), 0);

  const avgRTEpct =
    actualRteValues.length > 0
      ? actualRteValues.reduce((acc, value) => acc + value, 0) / actualRteValues.length
      : totalCharge > 0
        ? (totalDischarge / totalCharge) * 100
        : null;

  const budgetRTEpct =
    budgetRteValues.length > 0
      ? budgetRteValues.reduce((acc, value) => acc + value, 0) / budgetRteValues.length
      : null;

  const actualCycles =
    actualCycleValues.length > 0
      ? actualCycleValues.reduce((acc, value) => acc + value, 0)
      : avgCapMWh > 0
        ? totalCharge / avgCapMWh
        : null;

  // Budget Cycles: Sum of all budget_no_of_cycles from filtered rows
  // Works for ALL years (2025, 2026, etc.) - no year-specific logic
  const budgetCycles =
    budgetCycleValues.length > 0 ? budgetCycleValues.reduce((acc, value) => acc + value, 0) : null;

  const cufPctOverall =
    actualCUFValues.length > 0
      ? actualCUFValues.reduce((acc, value) => acc + value, 0) / actualCUFValues.length
      : avgCapMWh > 0 && numDays > 0
        ? (totalDischarge / (avgCapMWh * 24 * numDays)) * 100
        : null;

  // Budget CUF: Average of all budget_cuf from filtered rows
  // Works for ALL years (2025, 2026, etc.) - no year-specific logic
  const budgetCUF =
    budgetCufValues.length > 0 ? budgetCufValues.reduce((acc, value) => acc + value, 0) / budgetCufValues.length : null;

  // Energy flow budgets
  const energyFlowBudget = rows.reduce(
    (acc, row) => {
      acc.pvGeneration += toNumber(row.budget_pv_energy_kwh) / 1000;
      acc.pvToBess += toNumber(row.budget_charge_energy_kwh) / 1000;
      acc.pvToGrid += toNumber(row.budget_pv_grid_kwh) / 1000;
      acc.systemLoss += toNumber(row.budget_system_losses) / 1000;
      acc.bessToGrid += toNumber(row.budget_discharge_energy) / 1000;
      acc.totalExport += toNumber(row.budget_export_energy_kwh) / 1000;
      return acc;
    },
    { pvGeneration: 0, pvToBess: 0, pvToGrid: 0, systemLoss: 0, bessToGrid: 0, totalExport: 0 },
  );

  const energyFlow: BessV1Aggregates['energyFlow'] = {
    labels: ['PV Generation', 'PV to BESS', 'PV to Grid', 'System Losses', 'BESS to Grid', 'Total Export'],
    budget: [
      energyFlowBudget.pvGeneration,
      energyFlowBudget.pvToBess,
      energyFlowBudget.pvToGrid,
      energyFlowBudget.systemLoss,
      energyFlowBudget.bessToGrid,
      energyFlowBudget.totalExport,
    ],
    actual: [totalPV, totalCharge, totalPVtoGrid, totalSysLoss, totalDischarge, totalExport],
  };

  const waterfall = {
    pvGeneration: totalPV,
    gridImport: totalGridImport,
    systemLosses: totalSysLoss,
    bessToGrid: totalDischarge,
    pvToGrid: totalPVtoGrid,
    totalExport,
  };

  const monthBuckets: Record<string, BessV1Record[]> = {};
  rows.forEach((row) => {
    const normalizedMonth = normalizeMonth(row.month);
    if (!normalizedMonth) {
      return;
    }
    if (!monthBuckets[normalizedMonth]) {
      monthBuckets[normalizedMonth] = [];
    }
    monthBuckets[normalizedMonth].push(row);
  });

  const monthCUFData: BessV1Aggregates['monthCUFData'] = [];
  const monthCycleData: BessV1Aggregates['monthCycleData'] = [];

  Object.keys(monthBuckets)
    .sort(compareMonths)
    .forEach((month) => {
      const bucket = monthBuckets[month];
      const monthCharge = bucket.reduce((sum, row) => sum + toNumber(row.actual_charge_energy_kwh) / 1000, 0);
      const monthDischarge = bucket.reduce((sum, row) => sum + toNumber(row.actual_discharge_energy) / 1000, 0);
      const monthCapAvg =
        bucket.reduce((sum, row) => sum + toNumber(row.battery_capacity_mwh), 0) / Math.max(bucket.length, 1);
      const daysInMonth = getDaysInMonth(month);

      const actualCUFMonthValues = bucket
        .map((row) => toNumberOrNull(row.actual_cuf))
        .filter((value): value is number => value !== null && value > 0);
      // Note: Monthly actual_cuf is already in percentage format (e.g., 42.24, 51.2)
      // Only daily cuf values need conversion from decimal (0.78) to percentage (78)
      const cufActual =
        actualCUFMonthValues.length > 0
          ? actualCUFMonthValues.reduce((sum, value) => sum + value, 0) / actualCUFMonthValues.length
          : monthCapAvg > 0
            ? (monthDischarge / (monthCapAvg * 24 * daysInMonth)) * 100
            : null;

      // Monthly Budget CUF: Average of budget_cuf for all assets in this month
      // Works for ALL years (2025, 2026, etc.) - processes whatever months are in the bucket
      const budgetCufMonthValues = bucket
        .map((row) => toNumberOrNull(row.budget_cuf))
        .filter((value): value is number => value !== null && value > 0);
      const cufBudget =
        budgetCufMonthValues.length > 0
          ? budgetCufMonthValues.reduce((sum, value) => sum + value, 0) / budgetCufMonthValues.length
          : null;

      const actualCycleMonthValues = bucket
        .map((row) => toNumberOrNull(row.actual_no_of_cycles))
        .filter((value): value is number => value !== null && value > 0);
      const cyclesActual =
        actualCycleMonthValues.length > 0
          ? actualCycleMonthValues.reduce((sum, value) => sum + value, 0)
          : monthCapAvg > 0
            ? monthCharge / monthCapAvg
            : null;

      // Monthly Budget Cycles: Sum of budget_no_of_cycles for all assets in this month
      // Works for ALL years (2025, 2026, etc.) - processes whatever months are in the bucket
      const budgetCycleMonthValues = bucket
        .map((row) => toNumberOrNull(row.budget_no_of_cycles))
        .filter((value): value is number => value !== null && value > 0);
      const cyclesBudget =
        budgetCycleMonthValues.length > 0
          ? budgetCycleMonthValues.reduce((sum, value) => sum + value, 0)
          : null;

      monthCUFData.push({ month, cufActual, cufBudget });
      monthCycleData.push({ month, cyclesActual, cyclesBudget });
    });

  return {
    avgCapMWh,
    totalCapMWh,
    minSOC,
    maxSOC,
    minTemp,
    maxTemp,
    avgRTEpct,
    budgetRTEpct,
    actualCycles,
    budgetCycles,
    cufPctOverall,
    budgetCUF,
    energyFlow,
    waterfall,
    monthCUFData,
    monthCycleData,
  };
}

export function useBessV1Data(filters: BessV1Filters): UseBessV1DataReturn {
  const [data, setData] = useState<BessV1Record[]>([]);
  const [dailyData, setDailyData] = useState<DailyBessRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetchBessV1Data(controller.signal)
      .then((response) => {
        setData(response);
        setLoading(false);
      })
      .catch((err) => {
        if (err.name === 'AbortError') return;
        setError(err);
        setData([]);
        setLoading(false);
      });

    return () => {
      controller.abort();
    };
  }, []);

  // Fetch daily data when a single month is selected
  useEffect(() => {
    // Check if a single month is selected (not a range)
    // Single month can be: filters.month set, or startMonth === endMonth
    let selectedMonth: string | null = null;
    
    // Priority 1: Check filters.month (calendar/dropdown selection)
    // IMPORTANT: When a month is selected, range should be null (cleared by handleMonthChange)
    // But we check explicitly to ensure range is null or doesn't exist
    // This allows daily data to be fetched for any month (2025, 2026, etc.)
    if (filters.month) {
      // Check if range is actually set (not just truthy check)
      const hasRange = filters.range && filters.range.start && filters.range.end;
      if (!hasRange) {
        selectedMonth = normalizeMonth(filters.month);
      }
    }
    
    // Priority 2: Check if startMonth and endMonth are the same (quick range button)
    if (!selectedMonth && filters.startMonth && filters.endMonth) {
      const hasRange = filters.range && filters.range.start && filters.range.end;
      if (!hasRange) {
        const normalizedStart = normalizeMonth(filters.startMonth);
        const normalizedEnd = normalizeMonth(filters.endMonth);
        if (normalizedStart && normalizedEnd && normalizedStart === normalizedEnd) {
          selectedMonth = normalizedStart;
        }
      }
    }

    if (selectedMonth) {
      const controller = new AbortController();
      fetchBessDailyData(selectedMonth, controller.signal)
        .then((response) => {
          setDailyData(response);
        })
        .catch((err) => {
          if (err.name === 'AbortError') return;
          setDailyData([]);
        });

      return () => {
        controller.abort();
      };
    } else {
      // Clear daily data when no single month is selected
      setDailyData([]);
    }
  }, [filters.month, filters.range, filters.startMonth, filters.endMonth]);

  const filterOptions = useMemo<BessV1FilterOptions>(() => {
    const countries = Array.from(new Set(data.map((row) => row.country).filter(Boolean))).sort();
    const portfolios = Array.from(new Set(data.map((row) => row.portfolio).filter(Boolean))).sort();
    const assets = Array.from(new Set(data.map((row) => row.asset_no).filter(Boolean))).sort();
    const months = Array.from(
      new Set(
        data
          .map((row) => normalizeMonth(row.month))
          .filter((value): value is string => Boolean(value)),
      ),
    ).sort(compareMonths);

    return { countries, portfolios, assets, months };
  }, [data]);

  const filteredData = useMemo(() => {
    // STEP 2: Apply filters in correct priority order
    // Order: countries → portfolios → assets → YEAR → RANGE → MONTH
    // Month must override range, range must override year
    // 
    // IMPORTANT: Default year logic belongs in state initialization, NOT here
    // This hook respects whatever year is in filters - if user selects 2026, use 2026
    // If year is null, that's a state initialization issue, not a filtering issue
    
    let filtered = data;

    // 1. Filter by countries
    if (filters.countries.length > 0) {
      filtered = filtered.filter((row) => 
        row.country && filters.countries.includes(row.country)
      );
    }

    // 2. Filter by portfolios
    if (filters.portfolios.length > 0) {
      filtered = filtered.filter((row) => 
        row.portfolio && filters.portfolios.includes(row.portfolio)
      );
    }

    // 3. Filter by assets
    if (filters.assets.length > 0) {
      filtered = filtered.filter((row) => 
        matchesAsset(row.asset_no, filters.assets)
      );
    }

    // 4. Filter by YEAR (applies if year is set and no month/range override)
    // Year filtering: row.month must start with "YYYY-"
    // Only apply year filter if:
    // - filters.year is explicitly set (user selected a year)
    // - No month or range is set (they override year)
    if (filters.year && !filters.month && !filters.range) {
      const yearStr = String(filters.year).trim();
      if (yearStr && /^\d{4}$/.test(yearStr)) {
        filtered = filtered.filter((row) => {
          const normalizedMonth = normalizeMonth(row.month);
          return normalizedMonth ? normalizedMonth.startsWith(`${yearStr}-`) : false;
        });
      }
    }

    // 5. Filter by RANGE (overrides year if set)
    // Range filtering: row.month must be between range.start and range.end
    if (filters.range && filters.range.start && filters.range.end) {
      const rangeStart = normalizeMonth(filters.range.start);
      const rangeEnd = normalizeMonth(filters.range.end);
      
      if (rangeStart && rangeEnd) {
        // Ensure start <= end
        const [start, end] = compareMonths(rangeStart, rangeEnd) > 0 
          ? [rangeEnd, rangeStart] 
          : [rangeStart, rangeEnd];
        
        filtered = filtered.filter((row) => {
          const normalizedMonth = normalizeMonth(row.month);
          if (!normalizedMonth) return false;
          return normalizedMonth >= start && normalizedMonth <= end;
        });
      }
    }
    // Also handle startMonth/endMonth if set
    else if (filters.startMonth || filters.endMonth) {
      let rangeStart: string | undefined = undefined;
      let rangeEnd: string | undefined = undefined;
      
      if (filters.startMonth) {
        rangeStart = normalizeMonth(filters.startMonth) ?? undefined;
      }
      if (filters.endMonth) {
        rangeEnd = normalizeMonth(filters.endMonth) ?? undefined;
      }
      
      if (rangeStart || rangeEnd) {
        filtered = filtered.filter((row) => {
          const normalizedMonth = normalizeMonth(row.month);
          if (!normalizedMonth) return false;
          return isMonthInRange(normalizedMonth, rangeStart, rangeEnd);
        });
      }
    }

    // 6. Filter by MONTH (overrides both year and range if set)
    // Month filtering: row.month must exactly match filters.month
    if (filters.month) {
      const normalizedMonth = normalizeMonth(filters.month);
      if (normalizedMonth) {
        filtered = filtered.filter((row) => {
          const rowMonth = normalizeMonth(row.month);
          return rowMonth === normalizedMonth;
        });
      }
    }

    return filtered;
  }, [data, filters]);


  // STEP 3: Ensure aggregates are recalculated from filteredData only
  const aggregates = useMemo(() => {
    if (!filteredData.length && !dailyData.length) {
      return null;
    }
    
    // Determine if single month is selected
    let selectedMonth: string | null = null;
    
    // Priority 1: Check filters.month (calendar/dropdown selection)
    // IMPORTANT: When a month is selected, range should be null (cleared by handleMonthChange)
    // Check explicitly if range is actually set (not just truthy check)
    // This ensures daily data works for any month (2025, 2026, etc.)
    if (filters.month) {
      const hasRange = filters.range && filters.range.start && filters.range.end;
      if (!hasRange) {
        selectedMonth = normalizeMonth(filters.month);
      }
    }
    
    // Priority 2: Check if startMonth and endMonth are the same (quick range button)
    if (!selectedMonth && filters.startMonth && filters.endMonth) {
      const hasRange = filters.range && filters.range.start && filters.range.end;
      if (!hasRange) {
        const normalizedStart = normalizeMonth(filters.startMonth);
        const normalizedEnd = normalizeMonth(filters.endMonth);
        if (normalizedStart && normalizedEnd && normalizedStart === normalizedEnd) {
          selectedMonth = normalizedStart;
        }
      }
    }
    
    const isSingleMonth = selectedMonth !== null;
    
    // If single month selected, create daily entries for charts 3 & 4
    // IMPORTANT: Create daily entries even if dailyData is empty - we still need budget values
    // This ensures daywise view works for 2026 even if actual daily data doesn't exist yet
    if (isSingleMonth && selectedMonth) {
      // Filter daily data by countries, portfolios, and assets (same as monthly data)
      // dailyData might be empty for 2026, but we'll still create daily entries with budget values
      const filteredDailyData = dailyData.filter((record) => {
        if (filters.countries.length && (!record.country || !filters.countries.includes(record.country))) {
          return false;
        }
        if (filters.portfolios.length && (!record.portfolio || !filters.portfolios.includes(record.portfolio))) {
          return false;
        }
        if (!matchesAsset(record.asset_no, filters.assets)) {
          return false;
        }
        return true;
      });
      
      // Helper function to normalize date to YYYY-MM-DD format
      // Handles formats like "10-Jan-25", "1-Apr-25", etc.
      const normalizeDate = (dateStr: string | null): string | null => {
        if (!dateStr) return null;
        
        // If already in YYYY-MM-DD format, return as is
        if (/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) {
          return dateStr;
        }
        
        // Try to parse "DD-MMM-YY" format (e.g., "10-Jan-25", "1-Apr-25")
        const ddmmyyMatch = dateStr.match(/^(\d{1,2})-([A-Za-z]{3})-(\d{2})$/i);
        if (ddmmyyMatch) {
          const [, day, monthName, yearShort] = ddmmyyMatch;
          const monthNames = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'];
          const monthIndex = monthNames.indexOf(monthName.toLowerCase());
          if (monthIndex >= 0) {
            const year = parseInt(yearShort) < 50 ? 2000 + parseInt(yearShort) : 1900 + parseInt(yearShort);
            const month = String(monthIndex + 1).padStart(2, '0');
            const dayPadded = String(day).padStart(2, '0');
            return `${year}-${month}-${dayPadded}`;
          }
        }
        
        // Try to parse as standard date
        const date = new Date(dateStr);
        if (!Number.isNaN(date.getTime())) {
          const year = date.getFullYear();
          const month = String(date.getMonth() + 1).padStart(2, '0');
          const day = String(date.getDate()).padStart(2, '0');
          return `${year}-${month}-${day}`;
        }
        
        return null;
      };
      
      // Get monthly budget values from filteredData for the selected month
      // This works even if dailyData is empty - we get budget from monthly records
      const monthlyRecordsForSelectedMonth = filteredData.filter((record) => {
        const normalizedRecordMonth = normalizeMonth(record.month);
        return normalizedRecordMonth === selectedMonth;
      });
      
      // Calculate monthly budget cycles (sum for cycles)
      // Works for ALL years (2025, 2026, etc.) - processes whatever month is selected
      const monthlyBudgetCycleValues = monthlyRecordsForSelectedMonth
        .map((row) => toNumberOrNull(row.budget_no_of_cycles))
        .filter((value): value is number => value !== null && value > 0);
      const monthlyBudgetCycles = monthlyBudgetCycleValues.length > 0
        ? monthlyBudgetCycleValues.reduce((sum, value) => sum + value, 0)
        : null;
      
      // Process daily data for CUF and Cycles
      const dailyCUFData: DailyCUFDataPoint[] = [];
      const dailyCycleData: DailyCycleDataPoint[] = [];
      
      // Group by date and aggregate values
      const dateMap = new Map<string, { 
        cufValues: number[]; 
        cycleValues: number[];
      }>();
      
      filteredDailyData.forEach((record) => {
        const normalizedDate = normalizeDate(record.date);
        if (!normalizedDate) return;
        
        if (!dateMap.has(normalizedDate)) {
          dateMap.set(normalizedDate, { 
            cufValues: [], 
            cycleValues: [],
          });
        }
        
        const dateData = dateMap.get(normalizedDate)!;
        
        // Use cuf value from database and convert from decimal (0-1) to percentage (0-100)
        // Database stores CUF as decimal (e.g., 0.78, 0.53) but needs to be displayed as percentage (78%, 53%)
        if (record.cuf !== null && record.cuf !== undefined) {
          const cufDecimal = toNumber(record.cuf);
          // Convert decimal to percentage by multiplying by 100
          const cufPercentage = cufDecimal * 100;
          dateData.cufValues.push(cufPercentage);
        }
        
        // Use actual_no_of_cycles value directly from database
        if (record.actual_no_of_cycles !== null && record.actual_no_of_cycles !== undefined) {
          dateData.cycleValues.push(toNumber(record.actual_no_of_cycles));
        }
      });
      
      // Generate all days of the month and fill with data or null
      const [yearStr, monthStr] = selectedMonth.split('-');
      const year = Number(yearStr);
      const month = Number(monthStr);
      const daysInMonth = new Date(year, month, 0).getDate();
      
      // Calculate daywise budget cycles
      // Budget cycles: one day one cycle (monthly budget cycles / days in month)
      // If monthly budget cycles equals days in month, each day gets 1 cycle
      // Works for ALL years (2025, 2026, etc.) - uses daysInMonth which is year-aware
      const dailyBudgetCycles = monthlyBudgetCycles !== null && daysInMonth > 0
        ? monthlyBudgetCycles / daysInMonth
        : null;
      
      // Calculate daywise budget CUF for each asset
      // Formula: daily_budget_discharge_energy (MWh) = (monthly_budget_discharge_energy / daysInMonth) / 1000
      // Then: daily_budget_CUF = (daily_budget_discharge_energy / battery_capacity_mwh) * 100
      // Works for ALL years (2025, 2026, etc.) - processes whatever month is selected
      const dailyBudgetCUFPerAsset: number[] = [];
      monthlyRecordsForSelectedMonth.forEach((record) => {
        const budgetDischargeEnergy = toNumberOrNull(record.budget_discharge_energy);
        const batteryCapacityMWh = toNumberOrNull(record.battery_capacity_mwh);
        
        if (budgetDischargeEnergy !== null && batteryCapacityMWh !== null && batteryCapacityMWh > 0 && daysInMonth > 0) {
          // Calculate daily budget discharge energy in MWh
          const dailyBudgetDischargeEnergyMWh = (budgetDischargeEnergy / daysInMonth) / 1000;
          
          // Calculate daily budget CUF percentage
          const dailyBudgetCUF = (dailyBudgetDischargeEnergyMWh / batteryCapacityMWh) * 100;
          
          dailyBudgetCUFPerAsset.push(dailyBudgetCUF);
        }
      });
      
      // Average the daily budget CUF across all assets
      const dailyBudgetCUF = dailyBudgetCUFPerAsset.length > 0
        ? dailyBudgetCUFPerAsset.reduce((sum, val) => sum + val, 0) / dailyBudgetCUFPerAsset.length
        : null;
      
      // Create entries for all days of the month
      // This ensures daywise view is shown even if dailyData is empty (e.g., for 2026)
      // Budget values will be shown, actual values will be null if no daily data exists
      for (let day = 1; day <= daysInMonth; day++) {
        const dateStr = `${year}-${monthStr.padStart(2, '0')}-${String(day).padStart(2, '0')}`;
        const dateData = dateMap.get(dateStr);
        
        if (dateData && dateData.cufValues.length > 0) {
          // Calculate CUF: average if multiple assets per day
          const avgCUF = dateData.cufValues.reduce((sum, val) => sum + val, 0) / dateData.cufValues.length;
          
          // Calculate Cycles: sum if multiple assets per day
          const totalCycles = dateData.cycleValues.length > 0
            ? dateData.cycleValues.reduce((sum, val) => sum + val, 0)
            : null;
          
          dailyCUFData.push({ date: dateStr, cufActual: avgCUF, cufBudget: dailyBudgetCUF });
          dailyCycleData.push({ date: dateStr, cyclesActual: totalCycles, cyclesBudget: dailyBudgetCycles });
        } else {
          // No actual data for this day, add null values for actual, but still show budget
          // This is important for 2026 where daily actual data might not exist yet
          dailyCUFData.push({ date: dateStr, cufActual: null, cufBudget: dailyBudgetCUF });
          dailyCycleData.push({ date: dateStr, cyclesActual: null, cyclesBudget: dailyBudgetCycles });
        }
      }
      
      // For single month with daily data, we still need monthly aggregates for other charts
      // But we'll override monthCUFData and monthCycleData to only show the selected month
      const aggregated = filteredData.length > 0 ? aggregateBessV1Data(filteredData) : {
        avgCapMWh: 0,
        totalCapMWh: 0,
        minSOC: null,
        maxSOC: null,
        minTemp: null,
        maxTemp: null,
        avgRTEpct: null,
        budgetRTEpct: null,
        actualCycles: null,
        budgetCycles: null,
        cufPctOverall: null,
        budgetCUF: null,
        energyFlow: { labels: [], budget: [], actual: [] },
        waterfall: { pvGeneration: 0, gridImport: 0, systemLosses: 0, bessToGrid: 0, pvToGrid: 0, totalExport: 0 },
        monthCUFData: [],
        monthCycleData: [],
      };
      
      // Override monthly data to only show selected month (for charts 1 & 2)
      const filteredMonthCUFData = aggregated.monthCUFData.filter(item => item.month === selectedMonth);
      const filteredMonthCycleData = aggregated.monthCycleData.filter(item => item.month === selectedMonth);
      
      return {
        ...aggregated,
        monthCUFData: filteredMonthCUFData,
        monthCycleData: filteredMonthCycleData,
        dailyCUFData,
        dailyCycleData,
      };
    }
    
    // For multiple months or no daily data, use regular monthly aggregation
    if (filteredData.length > 0) {
      return aggregateBessV1Data(filteredData);
    }
    
    return null;
  }, [filteredData, dailyData, filters]);

  return {
    data,
    filterOptions,
    filteredData,
    aggregates,
    loading,
    error,
  };
}

