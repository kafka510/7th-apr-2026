import { useMemo } from 'react';
import { useTheme } from '../../../contexts/ThemeContext';
import { useResponsiveFontSize } from '../../../utils/fontScaling';
import type { YieldDataEntry } from '../types';

type CapacityCardsProps = {
  data: YieldDataEntry[]; // Filtered data (already has all filters applied)
  loading?: boolean;
};

function toNumber(val: number | string | undefined | null): number {
  if (val === null || val === undefined || val === '') return 0;
  if (typeof val === 'number') return isNaN(val) ? 0 : val;
  const parsed = parseFloat(String(val));
  return isNaN(parsed) ? 0 : parsed;
}

export const CapacityCards = ({ data, loading = false }: CapacityCardsProps) => {
  const { theme } = useTheme();
  
  // Responsive font sizes
  const titleFontSize = useResponsiveFontSize(9, 13, 8);
  
  const cardBg = theme === 'dark'
    ? 'linear-gradient(to bottom right, rgba(15, 23, 42, 0.9), rgba(30, 41, 59, 0.7), rgba(15, 23, 42, 0.9))'
    : 'linear-gradient(to bottom right, rgba(255, 255, 255, 0.95), rgba(248, 250, 252, 0.9), rgba(255, 255, 255, 0.95))';
  const cardBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(203, 213, 225, 0.8)';
  const titleColor = theme === 'dark' ? '#94a3b8' : '#64748b';
  const valueColor = theme === 'dark' ? '#ffffff' : '#1a1a1a';
  
  const capacities = useMemo(() => {
    if (loading || data.length === 0) {
      return { dc: 0, ac: 0, bess: 0 };
    }

    // Use the filtered data directly - it already has all filters (month/year/range/country/portfolio/asset) applied
    // For capacity calculations, we want unique assets (to avoid double counting)
    // Use the latest month from the filtered data for capacity calculation
    const filteredMonths = [...new Set(data.map((row) => row.month).filter(Boolean))].sort();
    const latestMonth = filteredMonths.length > 0 ? filteredMonths[filteredMonths.length - 1] : null;
    
    let kpiRows: YieldDataEntry[];
    
    if (latestMonth) {
      // Use the latest month from filtered data
      kpiRows = data.filter((r) => r.month === latestMonth);
    } else {
      // If no data, use empty array
      kpiRows = [];
    }

    // Sum up capacities from unique assets (avoid double counting same asset in same month)
    const assetCapacities = new Map<string, { dc: number; ac: number; bess: number }>();
    
    kpiRows.forEach((row) => {
      const assetKey = `${row.assetno}-${row.month}`;
      if (!assetCapacities.has(assetKey)) {
        assetCapacities.set(assetKey, {
          dc: toNumber(row.dc_capacity_mw),
          ac: toNumber(row.ac_capacity_mw),
          bess: toNumber(row.bess_capacity_mwh),
        });
      }
    });

    let dc = 0;
    let ac = 0;
    let bess = 0;

    assetCapacities.forEach((cap) => {
      dc += cap.dc;
      ac += cap.ac;
      bess += cap.bess;
    });

    return { dc, ac, bess };
  }, [data, loading]);

  const formatValue = (value: number): string => {
    return value.toFixed(2);
  };

  return (
    <div className="grid h-full grid-cols-3 gap-2">
      {/* DC Capacity Card */}
      <div 
        className="kpi-card dc group flex flex-col rounded-xl border p-2 shadow-lg transition-all duration-300"
        style={{
          borderColor: cardBorder,
          background: cardBg,
          boxShadow: theme === 'dark' 
            ? '0 10px 15px -3px rgba(250, 204, 21, 0.05)' 
            : '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.borderColor = 'rgba(250, 204, 21, 0.5)';
          e.currentTarget.style.boxShadow = theme === 'dark'
            ? '0 20px 25px -5px rgba(250, 204, 21, 0.1)'
            : '0 10px 15px -3px rgba(250, 204, 21, 0.2)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.borderColor = cardBorder;
          e.currentTarget.style.boxShadow = theme === 'dark' 
            ? '0 10px 15px -3px rgba(250, 204, 21, 0.05)' 
            : '0 4px 6px -1px rgba(0, 0, 0, 0.1)';
        }}
      >
        <div 
          className="kpi-title mb-1 truncate font-semibold uppercase tracking-wide"
          style={{ color: titleColor, fontSize: `${titleFontSize}px` }}
        >
          PV Capacity (MWp)
        </div>
        <div className="flex flex-1 items-center gap-2">
          <div className="kpi-icon-block flex min-w-[24px] shrink-0 items-center justify-center rounded-lg bg-yellow-500/10 p-1.5 transition-all duration-300 group-hover:bg-yellow-500/20">
            <span className="kpi-icon text-yellow-400 transition-transform duration-300 group-hover:scale-110">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={1.5}
                stroke="currentColor"
                className="size-5"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M12 3v2.25m6.364 0l-1.5 1.5M21 12h-2.25m-2.25 0h-2.25M18.364 18.364l-1.5-1.5M12 18.75V21m-4.773-4.227l-1.5 1.5M5.25 12H3m2.25 0h2.25M12 5.25V3m-4.773 4.773l-1.5-1.5M5.25 12H3m2.25 0h2.25"
                />
              </svg>
            </span>
          </div>
          <div 
            className="kpi-value flex-1 truncate text-base font-bold"
            style={{ color: valueColor }}
          >
            {loading ? '—' : formatValue(capacities.dc)}
          </div>
        </div>
      </div>

      {/* AC Capacity Card */}
      <div 
        className="kpi-card ac group flex flex-col rounded-xl border p-2 shadow-lg transition-all duration-300"
        style={{
          borderColor: cardBorder,
          background: cardBg,
          boxShadow: theme === 'dark' 
            ? '0 10px 15px -3px rgba(59, 130, 246, 0.05)' 
            : '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.borderColor = 'rgba(59, 130, 246, 0.5)';
          e.currentTarget.style.boxShadow = theme === 'dark'
            ? '0 20px 25px -5px rgba(59, 130, 246, 0.1)'
            : '0 10px 15px -3px rgba(59, 130, 246, 0.2)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.borderColor = cardBorder;
          e.currentTarget.style.boxShadow = theme === 'dark' 
            ? '0 10px 15px -3px rgba(59, 130, 246, 0.05)' 
            : '0 4px 6px -1px rgba(0, 0, 0, 0.1)';
        }}
      >
        <div 
          className="kpi-title mb-1 truncate font-semibold uppercase tracking-wide"
          style={{ color: titleColor, fontSize: `${titleFontSize}px` }}
        >
          AC Capacity (MW)
        </div>
        <div className="flex flex-1 items-center gap-2">
          <div className="kpi-icon-block flex min-w-[24px] shrink-0 items-center justify-center rounded-lg bg-blue-500/10 p-1.5 transition-all duration-300 group-hover:bg-blue-500/20">
            <span className="kpi-icon text-blue-400 transition-transform duration-300 group-hover:scale-110">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={1.5}
                stroke="currentColor"
                className="size-5"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M13.5 10.5V6.75a4.5 4.5 0 1 1 9 0v3.75M3.75 21.75h10.5a2.25 2.25 0 0 0 2.25-2.25v-6.75a2.25 2.25 0 0 0-2.25-2.25H3.75a2.25 2.25 0 0 0-2.25 2.25v6.75a2.25 2.25 0 0 0 2.25 2.25Z"
                />
              </svg>
            </span>
          </div>
          <div 
            className="kpi-value flex-1 truncate text-base font-bold"
            style={{ color: valueColor }}
          >
            {loading ? '—' : formatValue(capacities.ac)}
          </div>
        </div>
      </div>

      {/* BESS Capacity Card */}
      <div 
        className="kpi-card bess group flex flex-col rounded-xl border p-2 shadow-lg transition-all duration-300"
        style={{
          borderColor: cardBorder,
          background: cardBg,
          boxShadow: theme === 'dark' 
            ? '0 10px 15px -3px rgba(34, 197, 94, 0.05)' 
            : '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.borderColor = 'rgba(34, 197, 94, 0.5)';
          e.currentTarget.style.boxShadow = theme === 'dark'
            ? '0 20px 25px -5px rgba(34, 197, 94, 0.1)'
            : '0 10px 15px -3px rgba(34, 197, 94, 0.2)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.borderColor = cardBorder;
          e.currentTarget.style.boxShadow = theme === 'dark' 
            ? '0 10px 15px -3px rgba(34, 197, 94, 0.05)' 
            : '0 4px 6px -1px rgba(0, 0, 0, 0.1)';
        }}
      >
        <div 
          className="kpi-title mb-1 truncate font-semibold uppercase tracking-wide"
          style={{ color: titleColor, fontSize: `${titleFontSize}px` }}
        >
          BESS Capacity (MWh)
        </div>
        <div className="flex flex-1 items-center gap-2">
          <div className="kpi-icon-block flex min-w-[24px] shrink-0 items-center justify-center rounded-lg bg-green-500/10 p-1.5 transition-all duration-300 group-hover:bg-green-500/20">
            <span className="kpi-icon text-green-400 transition-transform duration-300 group-hover:scale-110">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={1.5}
                stroke="currentColor"
                className="size-5"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M20.25 7.5l-.625 10.632a2.25 2.25 0 01-2.247 2.118H6.622a2.25 2.25 0 01-2.247-2.118L3.75 7.5M10 11.25h4M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125z"
                />
              </svg>
            </span>
          </div>
          <div 
            className="kpi-value flex-1 truncate text-base font-bold"
            style={{ color: valueColor }}
          >
            {loading ? '—' : formatValue(capacities.bess)}
          </div>
        </div>
      </div>
    </div>
  );
};

