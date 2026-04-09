import { useMemo } from 'react';
import { useTheme } from '../../../contexts/ThemeContext';
import type { YieldDataEntry, YieldFilters, YieldOptions } from '../types';
import { WaterfallChartECharts } from './WaterfallChartECharts';

type BreakdownChartProps = {
  data: YieldDataEntry[];
  filters: YieldFilters;
  options: YieldOptions;
  loading?: boolean;
};

const formatMonthLabel = (ym: string | null | undefined): string => {
  if (!ym) return '';
  const [y, m] = ym.split('-');
  const date = new Date(Number(y), Number(m) - 1, 1);
  return date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
};

const buildChartTitle = (
  prefix: string,
  months: string[],
  countries: string[],
  portfolios: string[],
  assetNos: string[],
  allCountries: string[],
  allPortfolios: string[],
): string => {
  let monthTitle = 'YTD';
  if (months.length === 1) {
    // If the string is just a year (e.g., '2025'), use it directly
    if (/^\d{4}$/.test(months[0])) {
      monthTitle = months[0];
    } else {
      monthTitle = formatMonthLabel(months[0]);
    }
  } else if (months.length > 1) {
    monthTitle = formatMonthLabel(months[0]) + ' – ' + formatMonthLabel(months[months.length - 1]);
  }

  let countryTitle = 'All Countries';
  if (countries.length === 1) {
    countryTitle = countries[0];
  } else if (countries.length > 1 && countries.length < allCountries.length) {
    countryTitle = 'Multiple Countries';
  }

  let portfolioTitle = 'All Portfolios';
  if (portfolios.length === 1) {
    portfolioTitle = portfolios[0];
  } else if (portfolios.length > 1 && portfolios.length < allPortfolios.length) {
    portfolioTitle = 'Multiple Portfolios';
  }

  let assetTitle = 'All Assets';
  if (assetNos.length === 1) {
    assetTitle = 'Asset ' + assetNos[0];
  } else if (assetNos.length > 1 && assetNos.length < allCountries.length) {
    assetTitle = 'Multiple Assets';
  }

  return `${prefix}: ${countryTitle} - ${portfolioTitle} - ${monthTitle} - ${assetTitle}`;
};

function toNumber(val: number | string | undefined | null): number {
  if (val === null || val === undefined || val === '') return 0;
  if (typeof val === 'number') return isNaN(val) ? 0 : val;
  const parsed = parseFloat(String(val));
  return isNaN(parsed) ? 0 : parsed;
}

export const BreakdownChart = ({ data, filters, options, loading = false }: BreakdownChartProps) => {
  const { theme } = useTheme();
  
  const chartTitle = useMemo(() => {
    let monthsForTitle: string[] = [];
    let chartType = 'Yield Analysis';

    // Check filters in priority order: range > month > year > YTD
    if (filters.range && filters.range.start && filters.range.end) {
      // Range selected - pass both start and end as separate items
      chartType = 'Yield Analysis (Range)';
      monthsForTitle = [filters.range.start, filters.range.end];
    } else if (filters.month) {
      // Month selected - pass the month string
      chartType = 'Yield Analysis';
      monthsForTitle = [filters.month];
    } else if (filters.year) {
      // Year selected but no specific month
      chartType = 'Yield Analysis (Full Year)';
      monthsForTitle = [filters.year.toString()];
    } else {
      // YTD - no month/year selected, use months from filtered data
      const allMonths = [...new Set(data.map((r) => r.month).filter(Boolean))].sort();
      if (allMonths.length === 1) {
        monthsForTitle = [allMonths[0]];
      } else if (allMonths.length > 1) {
        monthsForTitle = [allMonths[0], allMonths[allMonths.length - 1]];
      } else {
        monthsForTitle = ['YTD'];
      }
    }

    return buildChartTitle(
      chartType,
      monthsForTitle,
      filters.countries,
      filters.portfolios,
      filters.assets,
      options.countries,
      options.portfolios,
    );
  }, [data, filters.month, filters.year, filters.range, filters.countries, filters.portfolios, filters.assets, options.countries, options.portfolios]);

  const steps = useMemo(() => {
    if (loading || data.length === 0) {
      return [];
    }

    const sumBudget = (key: keyof YieldDataEntry) => {
      return data.reduce((acc, r) => acc + toNumber(r[key]), 0);
    };

    const sum = (key: keyof YieldDataEntry) => {
      return data.reduce((acc, r) => acc + toNumber(r[key]), 0);
    };

    // Helper to handle alternate backend field names for a logical metric
    const sumWithAliases = (primary: keyof YieldDataEntry, aliases: (keyof YieldDataEntry | string)[] = []) => {
      return data.reduce((acc, r) => {
        const allKeys = [primary, ...aliases];
        let raw: number | string | undefined | null = 0;
        for (const k of allKeys) {
          const candidate = (r as unknown as Record<string, number | string | undefined | null>)[k as string];
          if (candidate !== undefined && candidate !== null && candidate !== '') {
            raw = candidate;
            break;
          }
        }
        return acc + toNumber(raw);
      }, 0);
    };

    return [
      { name: 'IC<br>Approved<br>Budget', value: sumBudget('ic_approved_budget'), type: 'absolute' as const },
      { name: 'Expected<br>Budget', value: sumBudget('expected_budget'), type: 'absolute' as const },
      { name: 'Weather<br>Loss or<br>Gain', value: sum('weather_loss_or_gain'), type: 'relative' as const },
      { name: 'Grid<br>Curtailment<br>Loss or Gain', value: sum('grid_curtailment'), type: 'relative' as const },
      { name: 'Grid<br>Outage', value: sum('grid_outage'), type: 'relative' as const },
      { name: 'Operation<br>Budget', value: sumBudget('operation_budget'), type: 'absolute' as const },
      { name: 'Breakdown<br>Loss', value: sum('breakdown_loss'), type: 'relative' as const },
      // Support both correctly spelled and legacy typo column names
      { name: 'Scheduled<br>Outage<br>Loss', value: sumWithAliases('scheduled_outage_loss', ['schduled_outage_loss']) || 0, type: 'relative' as const },
      { name: 'Unclassified<br>Loss or Gain', value: sum('unclassified_loss'), type: 'relative' as const },
      { name: 'Actual<br>Generation', value: sum('actual_generation'), type: 'absolute' as const },
    ];
  }, [data, loading]);

  const containerBg = theme === 'dark'
    ? 'linear-gradient(to bottom right, rgba(15, 23, 42, 0.9), rgba(30, 41, 59, 0.7), rgba(15, 23, 42, 0.9))'
    : 'linear-gradient(to bottom right, rgba(255, 255, 255, 0.95), rgba(248, 250, 252, 0.9), rgba(255, 255, 255, 0.95))';
  const containerBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(203, 213, 225, 0.8)';
  const containerShadow = theme === 'dark' 
    ? '0 20px 25px -5px rgba(0, 0, 0, 0.4)' 
    : '0 10px 15px -3px rgba(0, 0, 0, 0.1)';
  const loadingTextColor = theme === 'dark' ? '#94a3b8' : '#64748b';
  const spinnerBorder = theme === 'dark' ? 'rgba(71, 85, 105, 0.6)' : 'rgba(203, 213, 225, 0.7)';

  if (loading) {
    return (
      <div 
        className="flex h-[500px] items-center justify-center rounded-xl border shadow-xl"
        style={{
          borderColor: containerBorder,
          background: containerBg,
          boxShadow: containerShadow,
        }}
      >
        <div className="flex flex-col items-center gap-2">
          <div 
            className="size-6 animate-spin rounded-full border-2 border-t-sky-500"
            style={{ borderColor: spinnerBorder }}
          />
          <div className="text-sm" style={{ color: loadingTextColor }}>Loading chart...</div>
        </div>
      </div>
    );
  }

  if (!steps.length) {
    return (
      <div 
        className="flex h-[500px] items-center justify-center rounded-xl border shadow-xl"
        style={{
          borderColor: containerBorder,
          background: containerBg,
          boxShadow: containerShadow,
        }}
      >
        <div style={{ color: loadingTextColor }}>No data available</div>
      </div>
    );
  }

  return (
    <div 
      className="flex flex-col rounded-xl border p-2 shadow-xl"
      style={{
        borderColor: containerBorder,
        background: containerBg,
        boxShadow: containerShadow,
      }}
    >
      <WaterfallChartECharts steps={steps} title={chartTitle} theme={theme === 'dark' ? 'dark' : 'light'} />
    </div>
  );
};

