/**
 * Calculation utilities for sales dashboard
 */
import type { YieldDataEntry, MapDataEntry, SalesFilters, KPIMetrics, ChartDataPoint } from '../types';
import { parseNumeric, normalizeValue, normalizeMonth } from './dataUtils';

// Country-specific grid emission factors (kg CO2/kWh)
const countryGridFactors: Record<string, number> = {
  Japan: 0.46,
  Korea: 0.411,
  'S. Korea': 0.411,
  'South Korea': 0.411,
  Singapore: 0.412,
  Taiwan: 0.509,
  'Taiwan ': 0.509,
};

export function getGridFactor(country: string | null | undefined): number {
  if (!country) return 0.7; // default factor

  const normalizedCountry = String(country).trim();
  
  // Direct match first
  if (countryGridFactors[normalizedCountry]) {
    return countryGridFactors[normalizedCountry];
  }
  
  // Case-insensitive match
  for (const [key, value] of Object.entries(countryGridFactors)) {
    if (key.toLowerCase() === normalizedCountry.toLowerCase()) {
      return value;
    }
  }
  
  // Handle common variations
  if (normalizedCountry.toLowerCase() === 'korea' || 
      normalizedCountry.toLowerCase() === 'south korea' || 
      normalizedCountry.toLowerCase() === 's. korea') {
    return 0.411;
  }
  
  return 0.7; // default factor for unknown countries
}

export function filterYieldData(
  yieldData: YieldDataEntry[],
  filters: SalesFilters
): YieldDataEntry[] {
  return yieldData.filter((row) => {
    // Country filter
    if (filters.country && filters.country.length > 0) {
      if (!filters.country.includes(normalizeValue(row.country))) {
        return false;
      }
    }

    // Portfolio filter
    if (filters.portfolio && filters.portfolio.length > 0) {
      if (!filters.portfolio.includes(normalizeValue(row.portfolio))) {
        return false;
      }
    }

    // Month filter
    if (filters.selectedMonth) {
      const recordMonth = normalizeMonth(row.month);
      if (recordMonth !== filters.selectedMonth) {
        return false;
      }
    }

    // Year filter
    if (filters.selectedYear) {
      const recordMonth = normalizeMonth(row.month);
      if (recordMonth) {
        const year = recordMonth.split('-')[0];
        if (year !== filters.selectedYear) {
          return false;
        }
      }
    }

    // Range filter
    if (filters.selectedRange && filters.selectedRange.start && filters.selectedRange.end) {
      const recordMonth = normalizeMonth(row.month);
      if (recordMonth && (recordMonth < filters.selectedRange.start || recordMonth > filters.selectedRange.end)) {
        return false;
      }
    }

    return true;
  });
}

export function filterMapData(
  mapData: MapDataEntry[],
  filters: SalesFilters
): MapDataEntry[] {
  return mapData.filter((row) => {
    // Country filter
    if (filters.country && filters.country.length > 0) {
      if (!filters.country.includes(normalizeValue(row.country))) {
        return false;
      }
    }

    // Portfolio filter
    if (filters.portfolio && filters.portfolio.length > 0) {
      if (!filters.portfolio.includes(normalizeValue(row.portfolio))) {
        return false;
      }
    }

    // Installation filter
    if (filters.installation && filters.installation.length > 0) {
      if (!filters.installation.includes(normalizeValue(row.installation_type))) {
        return false;
      }
    }

    return true;
  });
}

export function calculateKPIs(
  filteredYieldData: YieldDataEntry[]
): KPIMetrics {
  // Solar Energy: sum of actual_generation (using || 0 pattern like original)
  const solarEnergy = filteredYieldData.reduce(
    (sum, row) => {
      const val = parseNumeric(row.actual_generation);
      return sum + (Number.isFinite(val) ? val : 0);
    },
    0
  );

  // BESS Energy: sum of bess_generation_mwh (using || 0 pattern like original)
  const bessEnergy = filteredYieldData.reduce(
    (sum, row) => {
      const val = parseNumeric(row.bess_generation_mwh);
      return sum + (Number.isFinite(val) ? val : 0);
    },
    0
  );

  // Get unique assets
  const uniqueAssets = new Set(
    filteredYieldData.map((row) => normalizeValue(row.assetno)).filter(Boolean)
  );
  const solarAssetsCount = uniqueAssets.size;

  // Get latest month for capacity calculations
  const months = [...new Set(filteredYieldData.map((row) => row.month).filter(Boolean))].sort();
  const latestMonth = months[months.length - 1] || null;

  // Filter to latest month for capacity
  const latestMonthData = latestMonth
    ? filteredYieldData.filter((row) => row.month === latestMonth)
    : filteredYieldData;

  // Get unique asset capacities from latest month
  const assetCapacityMap = new Map<string, { dc: number; bess: number }>();
  latestMonthData.forEach((row) => {
    const assetId = normalizeValue(row.assetno);
    if (assetId && !assetCapacityMap.has(assetId)) {
      const dcVal = parseNumeric(row.dc_capacity_mw);
      const bessVal = parseNumeric(row.bess_capacity_mwh);
      assetCapacityMap.set(assetId, {
        dc: Number.isFinite(dcVal) ? dcVal : 0,
        bess: Number.isFinite(bessVal) ? bessVal : 0,
      });
    }
  });

  // Sum capacities
  let solarDcCapacity = 0;
  let bessCapacity = 0;
  assetCapacityMap.forEach((asset) => {
    solarDcCapacity += asset.dc;
    bessCapacity += asset.bess;
  });

  // Calculate CO2 saved
  let totalCO2 = 0;

  // Group by country for CO2 calculation
  const energyByCountry: Record<string, number> = {};
  filteredYieldData.forEach((row) => {
    const country = normalizeValue(row.country) || 'Unknown';
    const solarGen = parseNumeric(row.actual_generation);
    const bessGen = parseNumeric(row.bess_generation_mwh);
    if (!energyByCountry[country]) {
      energyByCountry[country] = 0;
    }
    const solarVal = Number.isFinite(solarGen) ? solarGen : 0;
    const bessVal = Number.isFinite(bessGen) ? bessGen : 0;
    energyByCountry[country] += solarVal + bessVal;
  });

  // Calculate CO2 for each country
  Object.entries(energyByCountry).forEach(([country, energy]) => {
    const gridFactor = getGridFactor(country) / 1000; // Convert kg/kWh to tons/MWh
    totalCO2 += energy * gridFactor;
  });

  // Trees saved: CO2 / 0.021 (tons per tree)
  const treesSaved = totalCO2 / 0.021;

  return {
    solarEnergy: Math.round(solarEnergy * 100) / 100,
    bessEnergy: Math.round(bessEnergy * 100) / 100,
    totalCO2: Math.round(totalCO2 * 100) / 100,
    treesSaved: Math.round(treesSaved),
    solarAssetsCount,
    solarDcCapacity: Math.round(solarDcCapacity * 100) / 100,
    bessCapacity: Math.round(bessCapacity * 100) / 100,
  };
}

export function calculateChartData(
  filteredYieldData: YieldDataEntry[]
): {
  solarGen: ChartDataPoint[];
  bessGen: ChartDataPoint[];
  co2: ChartDataPoint[];
  trees: ChartDataPoint[];
} {
  // Group by month
  const monthMap = new Map<string, { solar: number; bess: number; co2: number; trees: number }>();

  filteredYieldData.forEach((row) => {
    const month = normalizeMonth(row.month) || 'Unknown';
    if (!monthMap.has(month)) {
      monthMap.set(month, { solar: 0, bess: 0, co2: 0, trees: 0 });
    }
    const data = monthMap.get(month)!;
    const solarGen = parseNumeric(row.actual_generation);
    const bessGen = parseNumeric(row.bess_generation_mwh);
    const solarVal = Number.isFinite(solarGen) ? solarGen : 0;
    const bessVal = Number.isFinite(bessGen) ? bessGen : 0;
    const country = normalizeValue(row.country) || 'Unknown';
    const gridFactor = getGridFactor(country) / 1000; // Convert to tons/MWh
    const co2 = (solarVal + bessVal) * gridFactor;
    const trees = Number.isFinite(co2) ? co2 / 0.021 : 0;

    data.solar += solarVal;
    data.bess += bessVal;
    data.co2 += Number.isFinite(co2) ? co2 : 0;
    data.trees += trees;
  });

  // Convert to arrays and sort by month
  const months = Array.from(monthMap.keys()).sort();
  const solarGen: ChartDataPoint[] = months.map((month) => ({
    month,
    value: Math.round(monthMap.get(month)!.solar * 100) / 100,
  }));
  const bessGen: ChartDataPoint[] = months.map((month) => ({
    month,
    value: Math.round(monthMap.get(month)!.bess * 100) / 100,
  }));
  const co2: ChartDataPoint[] = months.map((month) => ({
    month,
    value: Math.round(monthMap.get(month)!.co2 * 100) / 100,
  }));
  const trees: ChartDataPoint[] = months.map((month) => ({
    month,
    value: Math.round(monthMap.get(month)!.trees),
  }));

  return { solarGen, bessGen, co2, trees };
}

