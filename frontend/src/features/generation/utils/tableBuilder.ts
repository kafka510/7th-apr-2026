/**
 * Table building utilities for Generation Report
 * Implements the hierarchical table logic from the old JavaScript
 */

import type {
  GenerationDailyData,
  YieldDataRow,
  MapDataRow,
  HierarchicalRow,
} from '../types';
import {
  parseCsvDate,
  getDcCapacityForMonth,
  sumDaily,
  sumGii,
  safePR,
  getDcCapacityMonth,
} from './calculations';

export interface TableBuildOptions {
  icBudget: GenerationDailyData[];
  expBudget: GenerationDailyData[];
  actualGen: GenerationDailyData[];
  budgetGii: GenerationDailyData[];
  actualGii: GenerationDailyData[];
  yieldData: YieldDataRow[];
  mapData: MapDataRow[];
  startMonth: string; // YYYY-MM
  endMonth: string; // YYYY-MM
  latestReportDate?: string;
}

/**
 * Get country for an asset from yield data
 */
function getAssetCountry(assetNo: string, yieldData: YieldDataRow[]): string {
  if (!assetNo || !yieldData.length) return '';
  const row = yieldData.find(
    (r) => r.assetno?.trim() === assetNo.trim() && r.country?.trim()
  );
  if (row?.country) return row.country.trim();
  const fallback = yieldData.find((r) => r.assetno?.trim() === assetNo.trim());
  return fallback?.country?.trim() || '';
}

/**
 * Sum a field from yield data rows
 */
function sumField(rows: YieldDataRow[], field: keyof YieldDataRow): number {
  return rows.reduce((sum, r) => sum + (parseFloat(String(r[field] || 0)) || 0), 0);
}

/**
 * Count valid assets
 */
function countValidAssets(assetList: string[]): number {
  return assetList.length;
}

/**
 * Build hierarchical rows for Generation Table (KPI Table)
 */
export function buildGenerationTableRows(options: TableBuildOptions): HierarchicalRow[] {
  const {
    icBudget,
    expBudget,
    actualGen,
    budgetGii,
    actualGii,
    yieldData,
    mapData,
    startMonth,
    endMonth,
    latestReportDate,
  } = options;

  const startDate = startMonth ? new Date(startMonth + '-01T00:00:00Z') : new Date('2025-01-01T00:00:00Z');
  const reportEnd = endMonth
    ? (() => {
        const [y, m] = endMonth.split('-').map(Number);
        const lastDay = new Date(Date.UTC(y, m, 0)).getUTCDate();
        return new Date(Date.UTC(y, m - 1, lastDay));
      })()
    : (latestReportDate ? new Date(latestReportDate + 'T00:00:00Z') : new Date());

  const period = { range: { start: startMonth, end: endMonth } };
  const dcCapacityMonth = getDcCapacityMonth(period, startMonth, endMonth);

  // Filter yieldData for selected months
  function parseMonth(monthStr: string | null | undefined): Date | null {
    if (!monthStr) return null;
    const [y, m] = monthStr.split('-').map(Number);
    return new Date(Date.UTC(y, m - 1, 1));
  }

  const filtered = yieldData.filter((row) => {
    const m = parseMonth(row.month);
    return m && m >= startDate && m <= reportEnd;
  });

  // Build portfolio mapping
  const portfolioMapRaw: Record<string, Set<string>> = {};
  const portfolioNameMap: Record<string, string> = {};

  filtered.forEach((row) => {
    if (row.portfolio && row.assetno) {
      const normalizedPortfolio = row.portfolio.trim();
      const originalPortfolio = row.portfolio;

      if (!portfolioNameMap[normalizedPortfolio]) {
        portfolioNameMap[normalizedPortfolio] = originalPortfolio;
      }

      if (!portfolioMapRaw[normalizedPortfolio]) {
        portfolioMapRaw[normalizedPortfolio] = new Set();
      }
      portfolioMapRaw[normalizedPortfolio].add(row.assetno.trim());
    }
  });

  // Sort assets within each portfolio
  const portfolioMap: Record<string, Set<string>> = {};
  Object.keys(portfolioMapRaw).forEach((normalizedPortfolio) => {
    const assets = Array.from(portfolioMapRaw[normalizedPortfolio]);
    const sortedAssets = assets.sort((a, b) => {
      const getNumericPart = (assetName: string) => {
        const match = assetName.match(/(\d+)$/);
        return match ? parseInt(match[1], 10) : 0;
      };
      return getNumericPart(a) - getNumericPart(b);
    });
    portfolioMap[portfolioNameMap[normalizedPortfolio]] = new Set(sortedAssets);
  });

  // Build country structure
  const countries: Record<string, Record<string, Array<{ asset_no: string; dc: number }>>> = {};
  const portfolios = Array.from(new Set(Object.keys(portfolioMap)));

  portfolios.forEach((p) => {
    const pAssets = Array.from(portfolioMap[p] || new Set());

    pAssets.forEach((a) => {
      const country = getAssetCountry(a, yieldData);
      if (!countries[country]) countries[country] = {};
      if (!countries[country][p]) countries[country][p] = [];
      countries[country][p].push({
        asset_no: a,
        dc: getDcCapacityForMonth(a, dcCapacityMonth, yieldData, mapData),
      });
    });
  });

  // Build countryMap
  const countryMap: Record<string, Record<string, Record<string, YieldDataRow[]>>> = {};
  Object.entries(countries).forEach(([country, portfolios]) => {
    countryMap[country] = {};
    Object.entries(portfolios).forEach(([portfolio, assets]) => {
      countryMap[country][portfolio] = {};
      assets.forEach((asset) => {
        const assetRows = filtered.filter(
          (row) => row.assetno?.trim() === asset.asset_no.trim()
        );
        countryMap[country][portfolio][asset.asset_no] = assetRows;
      });
    });
  });

  // Calculate country DC capacities
  const countryDcCapacities: Record<string, number> = {};
  Object.entries(countryMap).forEach(([country, portfolios]) => {
    const countryAssets = new Set<string>();
    Object.values(portfolios).forEach((assets) => {
      Object.keys(assets).forEach((asset) => countryAssets.add(asset));
    });
    countryDcCapacities[country] = Array.from(countryAssets).reduce(
      (sum, assetNo) => sum + getDcCapacityForMonth(assetNo, dcCapacityMonth, yieldData, mapData),
      0
    );
  });

  /**
   * Calculate weighted average PR from asset-level PRs
   * Weighted by DC capacity
   */
  function calculateWeightedAveragePR(
    assetPRs: Array<{ pr: number | null; dc: number }>
  ): number | null {
    let totalWeightedPR = 0;
    let totalDC = 0;

    assetPRs.forEach(({ pr, dc }) => {
      if (pr !== null && pr !== undefined && Number.isFinite(pr) && dc > 0) {
        totalWeightedPR += pr * dc;
        totalDC += dc;
      }
    });

    if (totalDC > 0) {
      return totalWeightedPR / totalDC;
    }
    return null;
  }

  // Build rows
  const rows: HierarchicalRow[] = [];
  let rowId = 0;

  // Store asset-level PRs for weighted average calculation
  const assetPRData: Map<string, { expPR: number | null; actPR: number | null; dc: number }> = new Map();

  // Calculate grand total
  const allAssets = new Set<string>();
  Object.values(countryMap).forEach((portfolios) => {
    Object.values(portfolios).forEach((assets) => {
      Object.keys(assets).forEach((asset) => allAssets.add(asset));
    });
  });

  // Calculate asset-level PRs for grand total
  const allAssetPRs: Array<{ expPR: number | null; actPR: number | null; dc: number }> = [];
  Array.from(allAssets).forEach((assetNo) => {
    const assetList = [assetNo];
    const aDc = getDcCapacityForMonth(assetNo, dcCapacityMonth, yieldData, mapData);
    const aExp = sumDaily(expBudget, assetList, startDate, reportEnd);
    const aAg = sumDaily(actualGen, assetList, startDate, reportEnd) / 1000; // Convert kWh to MWh
    const aBgiiGii = sumGii(budgetGii, assetList, startDate, reportEnd);
    const aAgiiGii = sumGii(actualGii, assetList, startDate, reportEnd);
    const aExpPR = safePR(aExp, aDc, aBgiiGii);
    const aActPR = safePR(aAg, aDc, aAgiiGii);
    allAssetPRs.push({ expPR: aExpPR, actPR: aActPR, dc: aDc });
  });

  const totalDc = Array.from(allAssets).reduce(
    (sum, assetNo) => sum + getDcCapacityForMonth(assetNo, dcCapacityMonth, yieldData, mapData),
    0
  );
  const totalIc = sumDaily(icBudget, Array.from(allAssets), startDate, reportEnd);
  const totalExp = sumDaily(expBudget, Array.from(allAssets), startDate, reportEnd);
  const totalAg = sumDaily(actualGen, Array.from(allAssets), startDate, reportEnd) / 1000; // Convert kWh to MWh

  const totalYield = totalDc ? totalAg / totalDc : 0;
  // Use weighted average PR instead of direct calculation
  const totalExpPR = calculateWeightedAveragePR(allAssetPRs.map(a => ({ pr: a.expPR, dc: a.dc })));
  const totalActPR = calculateWeightedAveragePR(allAssetPRs.map(a => ({ pr: a.actPR, dc: a.dc })));

  // Calculate forecasted generation for grand total
  let totalForecastedGen = '';
  const isSingleMonth = startMonth === endMonth;
  if (Number.isFinite(totalAg) && totalAg > 0 && startDate && reportEnd) {
    if (isSingleMonth) {
      totalForecastedGen = totalAg.toLocaleString();
    } else {
      // Projection logic for range
      const datesWithData: number[] = [];
      actualGen.forEach((row) => {
        const dateValue = row.Date || row.date;
        const rowDate = parseCsvDate(dateValue ? String(dateValue) : null);
        if (!rowDate) return;
        let hasData = false;
        Array.from(allAssets).forEach((asset) => {
          const val = row[asset];
          if (val !== undefined && val !== null && val !== '' && parseFloat(String(val)) > 0) {
            hasData = true;
          }
        });
        if (hasData && rowDate >= startDate && rowDate <= reportEnd) {
          datesWithData.push(rowDate.getTime());
        }
      });

      if (datesWithData.length) {
        datesWithData.sort((a, b) => a - b);
        const firstDate = new Date(startDate);
        const lastDataDate = new Date(datesWithData[datesWithData.length - 1]);
        const msPerDay = 24 * 60 * 60 * 1000;
        const denomDays = Math.floor((lastDataDate.getTime() - firstDate.getTime()) / msPerDay) + 1;
        const [endY, endM] = [reportEnd.getUTCFullYear(), reportEnd.getUTCMonth() + 1];
        const lastDayOfEndMonth = new Date(Date.UTC(endY, endM, 0));
        const multDays = Math.floor((lastDayOfEndMonth.getTime() - firstDate.getTime()) / msPerDay) + 1;
        if (denomDays > 0 && multDays > 0) {
          totalForecastedGen = Math.round((totalAg / denomDays) * multDays).toLocaleString();
        }
      }
    }
  }

  const grandTotalRow: HierarchicalRow = {
    id: 'grandTotal',
    parentId: null,
    level: -1,
    country: '<b>All</b>',
    portfolio: '<b>All</b>',
    asset: `<b>${allAssets.size}</b>`,
    dc: totalDc,
    ic: totalIc,
    exp: totalExp,
    ag: totalAg,
    yieldVal: totalYield,
    fYield: totalForecastedGen || '0',
    expPR: totalExpPR || undefined,
    actPR: totalActPR || undefined,
    isTotal: true,
    isExpandable: Object.keys(countryMap).length > 0,
    isHidden: false,
  };

  rows.push(grandTotalRow);

  // Build country/portfolio/asset rows
  Object.entries(countryMap)
    .sort(([a], [b]) => a.localeCompare(b))
    .forEach(([country, portfolios]) => {
      const cId = `rc${rowId++}`;
      const countryRows: HierarchicalRow[] = [];
      let countryIc = 0,
        countryExp = 0,
        countryAg = 0;

      Object.entries(portfolios).forEach(([portfolio, assets]) => {
        const pId = `rp${rowId++}`;
        const portfolioRows: HierarchicalRow[] = [];
        let pIc = 0,
          pExp = 0,
          pAg = 0;

        // Store portfolio asset PRs for weighted average
        const portfolioAssetPRs: Array<{ expPR: number | null; actPR: number | null; dc: number }> = [];

        Object.entries(assets).forEach(([asset]) => {
          const aId = `ra${rowId++}`;

          // Get values from daily data
          const assetList = [asset];
          const aIc = sumDaily(icBudget, assetList, startDate, reportEnd);
          const aExp = sumDaily(expBudget, assetList, startDate, reportEnd);
          const aAg = sumDaily(actualGen, assetList, startDate, reportEnd) / 1000; // Convert kWh to MWh
          const aBgiiGii = sumGii(budgetGii, assetList, startDate, reportEnd);
          const aAgiiGii = sumGii(actualGii, assetList, startDate, reportEnd);

          const aDc = getDcCapacityForMonth(asset, dcCapacityMonth, yieldData, mapData);
          const aYield = aDc ? aAg / aDc : 0;
          const aExpPR = safePR(aExp, aDc, aBgiiGii);
          const aActPR = safePR(aAg, aDc, aAgiiGii);

          // Store asset PR data for portfolio weighted average
          portfolioAssetPRs.push({ expPR: aExpPR, actPR: aActPR, dc: aDc });
          assetPRData.set(asset, { expPR: aExpPR, actPR: aActPR, dc: aDc });

          // Calculate forecasted generation
          let assetForecastedGen = '';
          if (Number.isFinite(aAg) && aAg > 0 && startDate && reportEnd) {
            if (isSingleMonth) {
              assetForecastedGen = aAg.toLocaleString();
            } else {
              const datesWithData: number[] = [];
              actualGen.forEach((row) => {
                const dateValue = row.Date || row.date;
        const rowDate = parseCsvDate(dateValue ? String(dateValue) : null);
                if (!rowDate) return;
                const val = row[asset];
                if (
                  val !== undefined &&
                  val !== null &&
                  val !== '' &&
                  parseFloat(String(val)) > 0 &&
                  rowDate >= startDate &&
                  rowDate <= reportEnd
                ) {
                  datesWithData.push(rowDate.getTime());
                }
              });

              if (datesWithData.length) {
                datesWithData.sort((a, b) => a - b);
                const firstDate = new Date(startDate);
                const lastDataDate = new Date(datesWithData[datesWithData.length - 1]);
                const msPerDay = 24 * 60 * 60 * 1000;
                const denomDays =
                  Math.floor((lastDataDate.getTime() - firstDate.getTime()) / msPerDay) + 1;
                const [endY, endM] = [reportEnd.getUTCFullYear(), reportEnd.getUTCMonth() + 1];
                const lastDayOfEndMonth = new Date(Date.UTC(endY, endM, 0));
                const multDays =
                  Math.floor((lastDayOfEndMonth.getTime() - firstDate.getTime()) / msPerDay) + 1;
                if (denomDays > 0 && multDays > 0) {
                  assetForecastedGen = Math.round((aAg / denomDays) * multDays).toLocaleString();
                }
              }
            }
          }

          portfolioRows.push({
            id: aId,
            parentId: pId,
            level: 2,
            country,
            portfolio,
            asset,
            dc: aDc,
            ic: aIc,
            exp: aExp,
            ag: aAg,
            yieldVal: aYield,
            fYield: assetForecastedGen,
            expPR: aExpPR || undefined,
            actPR: aActPR || undefined,
            isTotal: false,
            isExpandable: false,
            isHidden: true,
          });

          pIc += aIc;
          pExp += aExp;
          pAg += aAg;
        });

        // Portfolio row
        const pAssets = Object.keys(assets);
        const pDc = pAssets.reduce(
          (sum, asset) => sum + getDcCapacityForMonth(asset, dcCapacityMonth, yieldData, mapData),
          0
        );
        const pYield = pDc ? pAg / pDc : 0;
        // Use weighted average PR instead of direct calculation
        const pExpPR = calculateWeightedAveragePR(portfolioAssetPRs.map(a => ({ pr: a.expPR, dc: a.dc })));
        const pActPR = calculateWeightedAveragePR(portfolioAssetPRs.map(a => ({ pr: a.actPR, dc: a.dc })));

        // Calculate portfolio forecasted generation
        let portfolioForecastedGen = '';
        if (Number.isFinite(pAg) && pAg > 0 && startDate && reportEnd) {
          if (isSingleMonth) {
            portfolioForecastedGen = pAg.toLocaleString();
          } else {
            const datesWithData: number[] = [];
            actualGen.forEach((row) => {
              const dateValue = row.Date || row.date;
        const rowDate = parseCsvDate(dateValue ? String(dateValue) : null);
              if (!rowDate) return;
              let hasAnyData = false;
              pAssets.forEach((asset) => {
                const val = row[asset];
                if (val !== undefined && val !== null && val !== '' && parseFloat(String(val)) > 0) {
                  hasAnyData = true;
                }
              });
              if (hasAnyData && rowDate >= startDate && rowDate <= reportEnd) {
                datesWithData.push(rowDate.getTime());
              }
            });

            if (datesWithData.length) {
              datesWithData.sort((a, b) => a - b);
              const firstDate = new Date(startDate);
              const lastDataDate = new Date(datesWithData[datesWithData.length - 1]);
              const msPerDay = 24 * 60 * 60 * 1000;
              const denomDays =
                Math.floor((lastDataDate.getTime() - firstDate.getTime()) / msPerDay) + 1;
              const [endY, endM] = [reportEnd.getUTCFullYear(), reportEnd.getUTCMonth() + 1];
              const lastDayOfEndMonth = new Date(Date.UTC(endY, endM, 0));
              const multDays =
                Math.floor((lastDayOfEndMonth.getTime() - firstDate.getTime()) / msPerDay) + 1;
              if (denomDays > 0 && multDays > 0) {
                portfolioForecastedGen = Math.round((pAg / denomDays) * multDays).toLocaleString();
              }
            }
          }
        }

        portfolioRows.unshift({
          id: pId,
          parentId: cId,
          level: 1,
          country,
          portfolio,
          asset: countValidAssets(pAssets),
          dc: pDc,
          ic: pIc,
          exp: pExp,
          ag: pAg,
          yieldVal: pYield,
          fYield: portfolioForecastedGen,
          expPR: pExpPR || undefined,
          actPR: pActPR || undefined,
          isTotal: false,
          isExpandable: pAssets.length > 0,
          isHidden: true,
        });

        countryRows.push(...portfolioRows);
        countryIc += pIc;
        countryExp += pExp;
        countryAg += pAg;
      });

      // Country row
      const countryAssets: string[] = [];
      Object.values(portfolios).forEach((assets) => {
        Object.keys(assets).forEach((asset) => countryAssets.push(asset));
      });
      const cDc = countryDcCapacities[country] || 0;
      const cYield = cDc ? countryAg / cDc : 0;
      // Collect country asset PRs for weighted average
      const countryAssetPRs: Array<{ expPR: number | null; actPR: number | null; dc: number }> = [];
      countryAssets.forEach((asset) => {
        const assetPR = assetPRData.get(asset);
        if (assetPR) {
          countryAssetPRs.push(assetPR);
        }
      });
      // Use weighted average PR instead of direct calculation
      const cExpPR = calculateWeightedAveragePR(countryAssetPRs.map(a => ({ pr: a.expPR, dc: a.dc })));
      const cActPR = calculateWeightedAveragePR(countryAssetPRs.map(a => ({ pr: a.actPR, dc: a.dc })));

      // Calculate country forecasted generation
      let countryForecastedGen = '';
      if (Number.isFinite(countryAg) && countryAg > 0 && startDate && reportEnd) {
        if (isSingleMonth) {
          countryForecastedGen = countryAg.toLocaleString();
        } else {
          const datesWithData: number[] = [];
          actualGen.forEach((row) => {
            const dateValue = row.Date || row.date;
        const rowDate = parseCsvDate(dateValue ? String(dateValue) : null);
            if (!rowDate) return;
            let hasAnyData = false;
            countryAssets.forEach((asset) => {
              const val = row[asset];
              if (val !== undefined && val !== null && val !== '' && parseFloat(String(val)) > 0) {
                hasAnyData = true;
              }
            });
            if (hasAnyData && rowDate >= startDate && rowDate <= reportEnd) {
              datesWithData.push(rowDate.getTime());
            }
          });

          if (datesWithData.length) {
            datesWithData.sort((a, b) => a - b);
            const firstDate = new Date(startDate);
            const lastDataDate = new Date(datesWithData[datesWithData.length - 1]);
            const msPerDay = 24 * 60 * 60 * 1000;
            const denomDays =
              Math.floor((lastDataDate.getTime() - firstDate.getTime()) / msPerDay) + 1;
            const [endY, endM] = [reportEnd.getUTCFullYear(), reportEnd.getUTCMonth() + 1];
            const lastDayOfEndMonth = new Date(Date.UTC(endY, endM, 0));
            const multDays =
              Math.floor((lastDayOfEndMonth.getTime() - firstDate.getTime()) / msPerDay) + 1;
            if (denomDays > 0 && multDays > 0) {
              countryForecastedGen = Math.round((countryAg / denomDays) * multDays).toLocaleString();
            }
          }
        }
      }

      rows.push({
        id: cId,
        parentId: null,
        level: 0,
        country,
        portfolio: 'Total',
        asset: countValidAssets(countryAssets),
        dc: cDc,
        ic: countryIc,
        exp: countryExp,
        ag: countryAg,
        yieldVal: cYield,
        fYield: countryForecastedGen,
        expPR: cExpPR || undefined,
        actPR: cActPR || undefined,
        isTotal: true,
        isExpandable: Object.keys(portfolios).length > 0,
        isHidden: false,
      });

      rows.push(...countryRows);
    });

  return rows;
}

/**
 * Build hierarchical rows for Revenue Table
 */
export function buildRevenueTableRows(options: TableBuildOptions): HierarchicalRow[] {
  const {
    yieldData,
    mapData,
    startMonth,
    endMonth,
  } = options;

  const startDate = startMonth ? new Date(startMonth + '-01T00:00:00Z') : new Date('2025-01-01T00:00:00Z');
  const reportEnd = endMonth
    ? (() => {
        const [y, m] = endMonth.split('-').map(Number);
        const lastDay = new Date(Date.UTC(y, m, 0)).getUTCDate();
        return new Date(Date.UTC(y, m - 1, lastDay));
      })()
    : new Date();

  const period = { range: { start: startMonth, end: endMonth } };
  const dcCapacityMonth = getDcCapacityMonth(period, startMonth, endMonth);

  // Filter yieldData for selected months
  function parseMonth(monthStr: string | null | undefined): Date | null {
    if (!monthStr) return null;
    const [y, m] = monthStr.split('-').map(Number);
    return new Date(Date.UTC(y, m - 1, 1));
  }

  const filtered = yieldData.filter((row) => {
    const m = parseMonth(row.month);
    return m && m >= startDate && m <= reportEnd;
  });

  // Build portfolio mapping (same as generation table)
  const portfolioMapRaw: Record<string, Set<string>> = {};
  const portfolioNameMap: Record<string, string> = {};

  filtered.forEach((row) => {
    if (row.portfolio && row.assetno) {
      const normalizedPortfolio = row.portfolio.trim();
      const originalPortfolio = row.portfolio;

      if (!portfolioNameMap[normalizedPortfolio]) {
        portfolioNameMap[normalizedPortfolio] = originalPortfolio;
      }

      if (!portfolioMapRaw[normalizedPortfolio]) {
        portfolioMapRaw[normalizedPortfolio] = new Set();
      }
      portfolioMapRaw[normalizedPortfolio].add(row.assetno.trim());
    }
  });

  const portfolioMap: Record<string, Set<string>> = {};
  Object.keys(portfolioMapRaw).forEach((normalizedPortfolio) => {
    const assets = Array.from(portfolioMapRaw[normalizedPortfolio]);
    const sortedAssets = assets.sort((a, b) => {
      const getNumericPart = (assetName: string) => {
        const match = assetName.match(/(\d+)$/);
        return match ? parseInt(match[1], 10) : 0;
      };
      return getNumericPart(a) - getNumericPart(b);
    });
    portfolioMap[portfolioNameMap[normalizedPortfolio]] = new Set(sortedAssets);
  });

  // Build country structure
  const countries: Record<string, Record<string, Array<{ asset_no: string; dc: number }>>> = {};
  const portfolios = Array.from(new Set(Object.keys(portfolioMap)));

  portfolios.forEach((p) => {
    const pAssets = Array.from(portfolioMap[p] || new Set());

    pAssets.forEach((a) => {
      const country = getAssetCountry(a, yieldData);
      if (!countries[country]) countries[country] = {};
      if (!countries[country][p]) countries[country][p] = [];
      countries[country][p].push({
        asset_no: a,
        dc: getDcCapacityForMonth(a, dcCapacityMonth, yieldData, mapData),
      });
    });
  });

  // Build countryMap
  const countryMap: Record<string, Record<string, Record<string, YieldDataRow[]>>> = {};
  Object.entries(countries).forEach(([country, portfolios]) => {
    countryMap[country] = {};
    Object.entries(portfolios).forEach(([portfolio, assets]) => {
      countryMap[country][portfolio] = {};
      assets.forEach((asset) => {
        const assetRows = filtered.filter(
          (row) => row.assetno?.trim() === asset.asset_no.trim()
        );
        countryMap[country][portfolio][asset.asset_no] = assetRows;
      });
    });
  });

  // Forecasted revenue calculation
  function forecastedRevenue(assetRows: YieldDataRow[], latestReportDate?: string): number {
    if (!assetRows.length) return 0;

    const reportDateStr = latestReportDate || new Date().toISOString().split('T')[0];
    const reportDate = parseCsvDate(reportDateStr);
    if (!reportDate) return 0;

    // Only include rows up to and including the reporting date
    const actualsUpToReport = assetRows.filter((r) => {
      const m = parseMonth(r.month + '-01');
      return m && m <= new Date(Date.UTC(reportDate.getUTCFullYear(), reportDate.getUTCMonth(), 1));
    });

    const totalActual = sumField(actualsUpToReport, 'actual_generation_dollar');

    const year = reportDate.getUTCFullYear();
    const jan1 = new Date(Date.UTC(year, 0, 1));
    const days = Math.floor((reportDate.getTime() - jan1.getTime()) / (1000 * 60 * 60 * 24)) + 1;
    if (days <= 0) return 0;

    const perDay = totalActual / days;
    const isDecember = endMonth?.endsWith('-12');
    const isLeap = (year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0));
    const yearDays = isLeap ? 366 : 365;
    const forecastDays = isDecember ? yearDays : days;

    return Math.round(perDay * forecastDays);
  }

  // Build rows
  const rows: HierarchicalRow[] = [];
  let rowId = 0;

  Object.entries(countryMap)
    .sort(([a], [b]) => a.localeCompare(b))
    .forEach(([country, portfolios]) => {
      const cId = `rc${rowId++}`;
      const countryRows: HierarchicalRow[] = [];
      let countryIc = 0,
        countryExp = 0,
        countryAct = 0,
        countryForecast = 0;

      Object.entries(portfolios).forEach(([portfolio, assets]) => {
        const pId = `rp${rowId++}`;
        const portfolioRows: HierarchicalRow[] = [];
        let pIc = 0,
          pExp = 0,
          pAct = 0,
          pForecast = 0;

        Object.entries(assets).forEach(([asset, assetRows]) => {
          const aId = `ra${rowId++}`;

          const ic = sumField(assetRows, 'ic_approved_budget_dollar');
          const exp = sumField(assetRows, 'expected_budget_dollar');
          const act = sumField(assetRows, 'actual_generation_dollar');
          const forecast = forecastedRevenue(assetRows, options.latestReportDate);
          const dc = getDcCapacityForMonth(asset, dcCapacityMonth, yieldData, mapData);

          portfolioRows.push({
            id: aId,
            parentId: pId,
            level: 2,
            country,
            portfolio,
            asset,
            dc,
            ic,
            exp,
            ag: 0, // Not used in revenue table
            act,
            forecast,
            isTotal: false,
            isExpandable: false,
            isHidden: true,
          });

          pIc += ic;
          pExp += exp;
          pAct += act;
          pForecast += forecast;
        });

        // Portfolio row
        const pAssets = Object.keys(assets);
        const pDc = pAssets.reduce(
          (sum, asset) => sum + getDcCapacityForMonth(asset, dcCapacityMonth, yieldData, mapData),
          0
        );

        portfolioRows.unshift({
          id: pId,
          parentId: cId,
          level: 1,
          country,
          portfolio,
          asset: countValidAssets(pAssets),
          dc: pDc,
          ic: pIc,
          exp: pExp,
          ag: 0,
          act: pAct,
          forecast: pForecast,
          isTotal: false,
          isExpandable: pAssets.length > 0,
          isHidden: true,
        });

        countryRows.push(...portfolioRows);
        countryIc += pIc;
        countryExp += pExp;
        countryAct += pAct;
        countryForecast += pForecast;
      });

      // Country row
      const countryAssets: string[] = [];
      Object.values(portfolios).forEach((assets) => {
        Object.keys(assets).forEach((asset) => countryAssets.push(asset));
      });
      const cDc = countryAssets.reduce(
        (sum, asset) => sum + getDcCapacityForMonth(asset, dcCapacityMonth, yieldData, mapData),
        0
      );

      rows.push({
        id: cId,
        parentId: null,
        level: 0,
        country,
        portfolio: 'Total',
        asset: countValidAssets(countryAssets),
        dc: cDc,
        ic: countryIc,
        exp: countryExp,
        ag: 0,
        act: countryAct,
        forecast: countryForecast,
        isTotal: true,
        isExpandable: Object.keys(portfolios).length > 0,
        isHidden: false,
      });

      rows.push(...countryRows);
    });

  // Grand total row
  const allAssets: string[] = [];
  Object.values(countryMap).forEach((portfolios) => {
    Object.values(portfolios).forEach((assets) => {
      Object.keys(assets).forEach((asset) => allAssets.push(asset));
    });
  });

  const totalDc = allAssets.reduce(
    (sum, asset) => sum + getDcCapacityForMonth(asset, dcCapacityMonth, yieldData, mapData),
    0
  );
  const totalIc = rows.filter((r) => r.level === 0).reduce((sum, r) => sum + r.ic, 0);
  const totalExp = rows.filter((r) => r.level === 0).reduce((sum, r) => sum + r.exp, 0);
  const totalAct = rows.filter((r) => r.level === 0).reduce((sum, r) => sum + (r.act || 0), 0);
  const totalForecast = rows.filter((r) => r.level === 0).reduce((sum, r) => sum + (r.forecast || 0), 0);

  rows.unshift({
    id: 'rgrandTotal',
    parentId: null,
    level: -1,
    country: '<b>All</b>',
    portfolio: '<b>All</b>',
    asset: `<b>${allAssets.length}</b>`,
    dc: totalDc,
    ic: totalIc,
    exp: totalExp,
    ag: 0,
    act: totalAct,
    forecast: totalForecast,
    isExpandable: Object.keys(countryMap).length > 0,
    isHidden: false,
  });

  return rows;
}

