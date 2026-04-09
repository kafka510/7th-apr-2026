import { useEffect, useMemo, useState } from 'react';

import { fetchKpiMetrics } from '../api';
import type {
  KpiFilterOptions,
  KpiFilterState,
  KpiGaugeValues,
  KpiMetric,
  KpiSummary,
} from '../types';

type UseKpiDataResult = {
  loading: boolean;
  error: string | null;
  rawMetrics: KpiMetric[];
  filteredMetrics: KpiMetric[];
  summary: KpiSummary;
  options: KpiFilterOptions;
  gaugeValues: KpiGaugeValues;
};

// Assets that should be excluded from the frontend (not owned by us)
const EXCLUDED_ASSET_NUMBERS = ['KR_BW_01'];

// Sites without API connection - these should be shown separately as "Communication Not Available"
const SITES_WITHOUT_API_CONNECTION = [
  'KR_BW_15',
  'KR_BW_19',
  'KR_BW_26',
  'KR_BW_27',
  'KR_BW_28',
  'KR_BW_31',
  'KR_BW_44',
  'TW1',
  'TW2',
  'TW3',
  'KR_BW_09',
  'KR_BW_24',
  'KR_BW_25',
];

const isSiteWithoutApiConnection = (assetNumber: string | undefined | null): boolean => {
  if (!assetNumber) {
    return false;
  }
  const normalized = assetNumber.trim();
  return SITES_WITHOUT_API_CONNECTION.includes(normalized);
};

const isExcludedAsset = (assetNumber: string | undefined | null): boolean => {
  if (!assetNumber) {
    return false;
  }
  const normalized = assetNumber.trim();
  return EXCLUDED_ASSET_NUMBERS.includes(normalized);
};

const normalise = (value: string | null | undefined) =>
  (value ?? '').trim().toLowerCase();

const matchesSelection = (value: string | undefined, selections: string[]) => {
  if (selections.length === 0) {
    return true;
  }
  return selections.map(normalise).includes(normalise(value));
};

const matchesDate = (
  value: string | undefined,
  targetDate: string | null,
  startDate: string | null,
  endDate: string | null,
) => {
  if (!value) {
    return false;
  }

  const metricDate = value.slice(0, 10); // Extract YYYY-MM-DD from ISO string

  // Use date range if available (preferred)
  if (startDate || endDate) {
    if (startDate && metricDate < startDate) {
      return false;
    }
    if (endDate && metricDate > endDate) {
      return false;
    }
    return true;
  }

  // Fallback to single date for backward compatibility
  if (!targetDate) {
    return true;
  }

  // The API returns ISO strings; compare by YYYY-MM-DD
  return metricDate === targetDate;
};

const computeSummary = (
  metrics: KpiMetric[],
  rawMetrics: KpiMetric[],
  filters?: { assets?: string[]; countries?: string[]; portfolios?: string[] },
): KpiSummary => {
  // Get the latest record for each asset based on last_updated timestamp
  const latestRecordsByAsset: Record<string, KpiMetric> = {};
  let latestTimestamp: number | null = null;

  metrics.forEach((metric) => {
    // Use asset_number if available, otherwise fall back to asset_code
    const assetKey = metric.asset_number || metric.asset_code;
    if (!assetKey) {
      return;
    }

    // Exclude restricted assets
    if (isExcludedAsset(assetKey)) {
      return;
    }

    const lastUpdated = metric.last_updated ?? metric.date;
    if (!lastUpdated) {
      return;
    }

    const timestamp = Date.parse(lastUpdated);
    if (Number.isNaN(timestamp)) {
      return;
    }

    // Track the most recent timestamp across all metrics
    if (latestTimestamp === null || timestamp > latestTimestamp) {
      latestTimestamp = timestamp;
    }

    // Keep only the latest record for each asset
    const existing = latestRecordsByAsset[assetKey];
    if (!existing || timestamp > Date.parse(existing.last_updated ?? existing.date)) {
      latestRecordsByAsset[assetKey] = metric;
    }
  });

  // Build a map of asset to country/portfolio from raw metrics
  // This helps us filter SITES_WITHOUT_API_CONNECTION by country/portfolio
  const assetToCountryPortfolio: Record<string, { country?: string; portfolio?: string }> = {};
  rawMetrics.forEach((metric) => {
    const assetKey = metric.asset_number || metric.asset_code;
    if (assetKey && (metric.country || metric.portfolio)) {
      assetToCountryPortfolio[assetKey] = {
        country: metric.country,
        portfolio: metric.portfolio,
      };
    }
  });

  // Count sites WITH API connection by state
  let activeSites = 0;
  let inactiveSites = 0;

  Object.values(latestRecordsByAsset).forEach((record) => {
    // Use asset_number if available, otherwise fall back to asset_code
    const assetKey = record.asset_number || record.asset_code;
    
    // Skip sites without API connection - they will be counted separately
    if (isSiteWithoutApiConnection(assetKey)) {
      return;
    }

    // Normalize site_state: handle null, undefined, empty string, and trim whitespace
    const siteState = record.site_state?.trim().toLowerCase() || null;
    const generation = Number(record.daily_generation_mwh) || 0;

    // Determine if site is active:
    // 1. If site_state is explicitly 'active', count as active
    // 2. If site_state is 'inactive' BUT has generation > 0, count as active (generation takes priority)
    // 3. If site_state is 'inactive' AND generation = 0, count as inactive
    // 4. If site_state is unknown/null/empty, use generation data as fallback
    if (siteState === 'active') {
      activeSites++;
    } else if (siteState === 'inactive') {
      // Even if marked inactive, if there's generation happening, consider it active
      if (generation > 0) {
        activeSites++;
      } else {
        inactiveSites++;
      }
    } else {
      // Fallback for unknown/null/empty site_state: Use generation data to determine active/inactive
      if (generation > 0) {
        activeSites++;
      } else {
        inactiveSites++;
      }
    }
  });

  // Count sites without API connection
  // Always include all sites from SITES_WITHOUT_API_CONNECTION, even if they don't have data,
  // but respect country/portfolio/asset filters if specified
  const sitesWithoutApiInData = Object.keys(latestRecordsByAsset).filter(
    (assetKey) => isSiteWithoutApiConnection(assetKey),
  );
  
  // Get all sites without API connection that should be counted
  // (respecting country/portfolio/asset filters if specified)
  const allSitesWithoutApi = SITES_WITHOUT_API_CONNECTION.filter((site) => {
    // Check country filter
    if (filters?.countries && filters.countries.length > 0) {
      const siteInfo = assetToCountryPortfolio[site];
      if (!siteInfo?.country || !matchesSelection(siteInfo.country, filters.countries)) {
        return false;
      }
    }
    
    // Check portfolio filter
    if (filters?.portfolios && filters.portfolios.length > 0) {
      const siteInfo = assetToCountryPortfolio[site];
      if (!siteInfo?.portfolio || !matchesSelection(siteInfo.portfolio, filters.portfolios)) {
        return false;
      }
    }
    
    // Check asset filter
    if (filters?.assets && filters.assets.length > 0) {
      if (!matchesSelection(site, filters.assets)) {
        return false;
      }
    }
    
    return true;
  });
  
  // Combine: sites from data + sites without data (that aren't already counted)
  const sitesWithoutApiSet = new Set([...sitesWithoutApiInData, ...allSitesWithoutApi]);
  const communicationNotAvailable = sitesWithoutApiSet.size;

  // Total assets = Active Sites + Inactive Sites + Communication Not Available
  const totalAssets = activeSites + inactiveSites + communicationNotAvailable;

  return {
    totalAssets,
    activeSites,
    inactiveSites,
    communicationNotAvailable,
    lastUpdated: latestTimestamp ? new Date(latestTimestamp).toISOString() : null,
  };
};

const isTaiwanSite = (metric: KpiMetric): boolean => {
  const country = (metric.country ?? '').toString().trim().toLowerCase();
  if (country === 'tw' || country === 'taiwan' || country === 'tiwan') {
    return true;
  }

  const assetCode = (metric.asset_code ?? '').toString().trim().toUpperCase();
  if (assetCode.startsWith('TW')) {
    return true;
  }

  return false;
};

const safeNumber = (value: unknown): number => {
  if (typeof value === 'number') {
    return Number.isFinite(value) ? value : 0;
  }
  if (typeof value === 'string' && value.trim() !== '') {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : 0;
  }
  return 0;
};

const computeGaugeValues = (metrics: KpiMetric[]): KpiGaugeValues => {
  if (metrics.length === 0) {
    return {
      icBudget: 0,
      expectedBudget: 0,
      actualGeneration: 0,
      budgetIrr: 0,
      actualIrr: 0,
      expectedPR: 0,
      actualPR: 0,
    };
  }

  const relevantMetrics = metrics.filter((metric) => !isTaiwanSite(metric));

  if (relevantMetrics.length === 0) {
    return {
      icBudget: 0,
      expectedBudget: 0,
      actualGeneration: 0,
      budgetIrr: 0,
      actualIrr: 0,
      expectedPR: 0,
      actualPR: 0,
    };
  }

  const withActualGeneration = relevantMetrics.filter(
    (metric) => safeNumber(metric.daily_generation_mwh) > 0,
  );

  const icBudget = withActualGeneration.reduce(
    (sum, metric) => sum + safeNumber(metric.daily_ic_mwh),
    0,
  );
  const expectedBudget = withActualGeneration.reduce(
    (sum, metric) => sum + safeNumber(metric.daily_expected_mwh),
    0,
  );
  const actualGeneration = withActualGeneration.reduce(
    (sum, metric) => sum + safeNumber(metric.daily_generation_mwh),
    0,
  );

  const withIrradiation = relevantMetrics.filter((metric) => {
    return (
      safeNumber(metric.daily_irradiation_mwh) > 0 ||
      safeNumber(metric.daily_budget_irradiation_mwh) > 0
    );
  });

  let budgetIrr = 0;
  let actualIrr = 0;
  if (withIrradiation.length > 0) {
    let weightedBudget = 0;
    let budgetWeight = 0;
    let weightedActual = 0;
    let actualWeight = 0;

    withIrradiation.forEach((metric) => {
      const weight = safeNumber(metric.capacity) || 1;
      const budgetValue = safeNumber(metric.daily_budget_irradiation_mwh);
      const actualValue = safeNumber(metric.daily_irradiation_mwh);

      if (budgetValue > 0) {
        weightedBudget += budgetValue * weight;
        budgetWeight += weight;
      }

      if (actualValue > 0) {
        weightedActual += actualValue * weight;
        actualWeight += weight;
      }
    });

    budgetIrr = budgetWeight > 0 ? weightedBudget / budgetWeight : 0;
    actualIrr = actualWeight > 0 ? weightedActual / actualWeight : 0;
  }

  // Calculate PR values using data from real_time_kpi table
  // Match the logic from old KPI.html: include all metrics with generation data
  // Use weighted average by capacity (as described: "weighted by capacity")
  const withPR = relevantMetrics.filter((metric) => {
    const dailyGen = safeNumber(metric.daily_generation_mwh);
    // Include all metrics that have generation data (like old code does)
    return dailyGen > 0;
  });

  let expectedPR = 0;
  let actualPR = 0;
  if (withPR.length > 0) {
    let weightedExpected = 0;
    let expectedWeight = 0;
    let weightedActualPR = 0;
    let actualWeight = 0;

    withPR.forEach((metric) => {
      // Use capacity as weight (from AssetList or dc_capacity_mw from RealTimeKPI)
      const weight = safeNumber(metric.capacity) || safeNumber(metric.dc_capacity_mw) || 1;
      
      // Get expected PR: use expect_pr from database
      const expectedValue = safeNumber(metric.expect_pr);
      
      // Get actual PR: use actual_pr from database
      const actualValue = safeNumber(metric.actual_pr);

      // Only include in weighted average if we have valid PR values (> 0)
      // This matches the pattern used for irradiation calculation and ensures we don't dilute
      // the average with zero/null values
      if (expectedValue > 0) {
        weightedExpected += expectedValue * weight;
        expectedWeight += weight;
      }

      if (actualValue > 0) {
        weightedActualPR += actualValue * weight;
        actualWeight += weight;
      }
    });

    // Calculate weighted averages (divide by total weight, not by count)
    expectedPR = expectedWeight > 0 ? weightedExpected / expectedWeight : 0;
    actualPR = actualWeight > 0 ? weightedActualPR / actualWeight : 0;
  }

  return {
    icBudget,
    expectedBudget,
    actualGeneration,
    budgetIrr,
    actualIrr,
    expectedPR,
    actualPR,
  };
};

export const useKpiData = (filters: KpiFilterState): UseKpiDataResult => {
  const [rawMetrics, setRawMetrics] = useState<KpiMetric[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    let currentController: AbortController | null = null;

    // Use async function to avoid synchronous setState in effect
    const loadData = async () => {
      if (!isMounted) return;
      
      // Abort any ongoing request
      if (currentController) {
        currentController.abort();
      }
      
      // Create a new controller for this request
      currentController = new AbortController();
      const controller = currentController;
      
      setLoading(true);
      setError(null);

      try {
        const metrics = await fetchKpiMetrics(controller.signal);
        if (isMounted && controller === currentController) {
          setRawMetrics(metrics);
        }
      } catch (err: unknown) {
        if (isMounted && controller === currentController && (err as { name?: string })?.name !== 'AbortError') {
          setError(err instanceof Error ? err.message : 'Unknown error');
        }
      } finally {
        if (isMounted && controller === currentController) {
          setLoading(false);
        }
      }
    };

    // Load data immediately
    loadData();

    // Set up auto-refresh every 10 minutes (600,000 milliseconds)
    const refreshInterval = setInterval(() => {
      if (isMounted) {
        loadData();
      }
    }, 10 * 60 * 1000);

    return () => {
      isMounted = false;
      if (currentController) {
        currentController.abort();
      }
      clearInterval(refreshInterval);
    };
  }, []);

  const filteredMetrics = useMemo(() => {
    if (rawMetrics.length === 0) {
      return [];
    }

    return rawMetrics.filter((metric) => {
      // Exclude restricted assets
      if (isExcludedAsset(metric.asset_number)) {
        return false;
      }

      const countryMatch = matchesSelection(metric.country, filters.countries);
      const portfolioMatch = matchesSelection(
        metric.portfolio,
        filters.portfolios,
      );
      const assetMatch = matchesSelection(metric.asset_number, filters.assets);
      const dateMatch = matchesDate(
        metric.date,
        filters.date, // Deprecated: for backward compatibility
        filters.startDate,
        filters.endDate,
      );

      return countryMatch && portfolioMatch && assetMatch && dateMatch;
    });
  }, [rawMetrics, filters]);

  const summary = useMemo(
    () =>
      computeSummary(filteredMetrics, rawMetrics, {
        assets: filters.assets,
        countries: filters.countries,
        portfolios: filters.portfolios,
      }),
    [filteredMetrics, rawMetrics, filters.assets, filters.countries, filters.portfolios],
  );

  const gaugeValues = useMemo(
    () => computeGaugeValues(filteredMetrics),
    [filteredMetrics],
  );

  const options: KpiFilterOptions = useMemo(() => {
    const countries = new Set<string>();
    const portfolios = new Set<string>();
    const assets = new Set<string>();

    rawMetrics.forEach((metric) => {
      // Exclude restricted assets from options
      if (isExcludedAsset(metric.asset_number)) {
        return;
      }

      if (metric.country) {
        countries.add(metric.country);
      }

      if (
        metric.portfolio &&
        matchesSelection(metric.country, filters.countries)
      ) {
        portfolios.add(metric.portfolio);
      }

      if (
        metric.asset_number &&
        matchesSelection(metric.country, filters.countries) &&
        matchesSelection(metric.portfolio, filters.portfolios)
      ) {
        assets.add(metric.asset_number);
      }
    });

    return {
      countries: Array.from(countries).sort(),
      portfolios: Array.from(portfolios).sort(),
      assets: Array.from(assets).sort(),
    };
  }, [rawMetrics, filters.countries, filters.portfolios]);

  return {
    loading,
    error,
    rawMetrics,
    filteredMetrics,
    summary,
    options,
    gaugeValues,
  };
};

