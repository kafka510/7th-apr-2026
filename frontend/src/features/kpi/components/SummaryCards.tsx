import { useMemo, useState } from 'react';
import { useTheme } from '../../../contexts/ThemeContext';
import { useResponsiveFontSize } from '../../../utils/fontScaling';

import type { KpiMetric, KpiSummary } from '../types';

import { AssetListModal } from './AssetListModal';

type SummaryCardsProps = {
  summary: KpiSummary;
  filteredMetrics: KpiMetric[];
  loading?: boolean;
};

const numberFormatter = new Intl.NumberFormat(undefined, {
  maximumFractionDigits: 0,
});

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
  'KR_BW_25'
];

const isExcludedAsset = (assetNumber: string | undefined | null): boolean => {
  if (!assetNumber) {
    return false;
  }
  const normalized = assetNumber.trim();
  return EXCLUDED_ASSET_NUMBERS.includes(normalized);
};

const isSiteWithoutApiConnection = (assetNumber: string | undefined | null): boolean => {
  if (!assetNumber) {
    return false;
  }
  const normalized = assetNumber.trim();
  return SITES_WITHOUT_API_CONNECTION.includes(normalized);
};

// Helper function to get latest record per asset (same logic as computeSummary)
const getLatestRecordsByAsset = (metrics: KpiMetric[]): Record<string, KpiMetric> => {
  const latestRecordsByAsset: Record<string, KpiMetric> = {};

  metrics.forEach((metric) => {
    // Use asset_number if available, otherwise fall back to asset_code (matching computeSummary)
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

    // Keep only the latest record for each asset
    const existing = latestRecordsByAsset[assetKey];
    if (!existing || timestamp > Date.parse(existing.last_updated ?? existing.date)) {
      latestRecordsByAsset[assetKey] = metric;
    }
  });

  return latestRecordsByAsset;
};

// Helper function to determine if asset is active
const isAssetActive = (record: KpiMetric): boolean => {
  // Normalize site_state: handle null, undefined, empty string, and trim whitespace
  const siteState = record.site_state?.trim().toLowerCase() || null;
  const generation = Number(record.daily_generation_mwh) || 0;
  
  if (siteState === 'active') {
    return true;
  }
  if (siteState === 'inactive') {
    // Even if marked inactive, if there's generation happening, consider it active
    return generation > 0;
  }
  // Fallback: Use generation data
  return generation > 0;
};

export const SummaryCards = ({
  summary,
  filteredMetrics,
  loading = false,
}: SummaryCardsProps) => {
  const { theme } = useTheme();
  
  // Responsive font sizes
  const labelFontSize = useResponsiveFontSize(12, 18, 10.5); // Increased by 1.5x (was 8, 12, 7)
  const iconFontSize = useResponsiveFontSize(9, 13, 8);
  const hintFontSize = useResponsiveFontSize(12, 18, 10.5); // Increased by 1.5x (was 8, 12, 7)
  const [modalOpen, setModalOpen] = useState(false);
  const [modalTitle, setModalTitle] = useState('');
  const [modalAssetNumbers, setModalAssetNumbers] = useState<string[]>([]);

  const cardsBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.7)' : 'rgba(255, 255, 255, 0.95)';
  const cardsShadow = theme === 'dark' 
    ? '0 20px 25px -5px rgba(0, 0, 0, 0.5)' 
    : '0 10px 15px -3px rgba(0, 0, 0, 0.1)';
  const labelColor = theme === 'dark' ? 'rgba(226, 232, 240, 0.8)' : '#64748b';
  const hintColor = theme === 'dark' ? 'rgba(203, 213, 225, 0.8)' : '#94a3b8';
  const valueColor = theme === 'dark' ? '#ffffff' : '#1a1a1a';

  const latestRecordsByAsset = useMemo(
    () => getLatestRecordsByAsset(filteredMetrics),
    [filteredMetrics],
  );

  const handleCardClick = (cardType: 'total' | 'active' | 'inactive' | 'communication') => {
    if (loading) {
      return;
    }

    let assetNumbers: string[] = [];
    let title = '';

    if (cardType === 'total') {
      // Total Assets = all sites in filtered data + all sites without API connection
      // (even if they don't have data, since they're defined as having no API connection)
      const sitesInData = Object.keys(latestRecordsByAsset);
      const allSites = new Set(sitesInData);
      
      // Add all sites from SITES_WITHOUT_API_CONNECTION that aren't already in the data
      SITES_WITHOUT_API_CONNECTION.forEach((site) => {
        allSites.add(site);
      });
      
      assetNumbers = Array.from(allSites).sort();
      title = 'Total Assets';
    } else if (cardType === 'active') {
      // Only sites WITH API connection that are active
      assetNumbers = Object.keys(latestRecordsByAsset)
        .filter((assetKey) => {
          const record = latestRecordsByAsset[assetKey];
          return !isSiteWithoutApiConnection(record.asset_number || record.asset_code) && isAssetActive(record);
        })
        .sort();
      title = 'Active Sites';
    } else if (cardType === 'inactive') {
      // Only sites WITH API connection that are inactive
      assetNumbers = Object.keys(latestRecordsByAsset)
        .filter((assetKey) => {
          const record = latestRecordsByAsset[assetKey];
          return !isSiteWithoutApiConnection(record.asset_number || record.asset_code) && !isAssetActive(record);
        })
        .sort();
      title = 'Inactive Sites';
    } else if (cardType === 'communication') {
      // Sites without API connection - include all from SITES_WITHOUT_API_CONNECTION
      // even if they don't have data (since they're defined as having no API connection)
      const sitesWithoutApiInData = Object.keys(latestRecordsByAsset)
        .filter((assetKey) => {
          const record = latestRecordsByAsset[assetKey];
          return isSiteWithoutApiConnection(record.asset_number || record.asset_code);
        });
      
      // Add all sites from SITES_WITHOUT_API_CONNECTION that aren't already in the data
      const allSitesWithoutApi = new Set(sitesWithoutApiInData);
      SITES_WITHOUT_API_CONNECTION.forEach((site) => {
        allSitesWithoutApi.add(site);
      });
      
      assetNumbers = Array.from(allSitesWithoutApi).sort();
      title = 'Communication Not Available';
    }

    setModalTitle(title);
    setModalAssetNumbers(assetNumbers);
    setModalOpen(true);
  };
  const cards = [
    {
      label: 'Total Assets',
      value: loading ? '—' : numberFormatter.format(summary.totalAssets),
      hint: 'All sites',
      icon: '🏢',
      gradient: 'from-cyan-500/20 via-cyan-500/10 to-slate-900/60',
      shadow: 'shadow-cyan-500/20',
      cardType: 'total' as const,
    },
    {
      label: 'Active Sites',
      value: loading ? '—' : numberFormatter.format(summary.activeSites),
      hint: 'Sites currently generating',
      icon: '✅',
      gradient: 'from-emerald-500/20 via-emerald-500/10 to-slate-900/60',
      shadow: 'shadow-emerald-500/20',
      cardType: 'active' as const,
    },
    {
      label: 'Inactive Sites',
      value: loading ? '—' : numberFormatter.format(summary.inactiveSites),
      hint: 'Sites not generating',
      icon: '⚠️',
      gradient: 'from-amber-400/20 via-amber-400/10 to-slate-900/60',
      shadow: 'shadow-amber-500/20',
      cardType: 'inactive' as const,
    },
    {
      label: 'Communication Not Available',
      value: loading ? '—' : numberFormatter.format(summary.communicationNotAvailable),
      hint: 'Sites without API connection',
      icon: '📡',
      gradient: 'from-orange-500/20 via-orange-500/10 to-slate-900/60',
      shadow: 'shadow-orange-500/20',
      cardType: 'communication' as const,
    },
    {
      label: 'Last Updated',
      value: loading
        ? '—'
        : summary.lastUpdated
        ? new Date(summary.lastUpdated).toLocaleString()
        : 'No data',
      hint: 'Most recent KPI snapshot',
      icon: '⏱️',
      gradient: 'from-violet-500/20 via-violet-500/10 to-slate-900/60',
      shadow: 'shadow-violet-500/20',
      cardType: null,
    },
  ];

  return (
    <>
      <section 
        className="grid gap-1 rounded-xl p-1 sm:grid-cols-2 lg:grid-cols-5"
        style={{
          backgroundColor: cardsBg,
          boxShadow: cardsShadow,
        }}
      >
        {cards.map((card, index) => {
          const isLastCard = index === cards.length - 1; // Last Updated card
          const isClickable = card.cardType !== null && !loading; // First 4 cards are clickable

          return (
            <div
              key={card.label}
              onClick={isClickable && card.cardType ? () => handleCardClick(card.cardType) : undefined}
              className={`relative overflow-hidden rounded-lg bg-gradient-to-br ${card.gradient} p-1.5 text-left shadow-md ${card.shadow} ${
                isClickable ? 'cursor-pointer transition hover:scale-[1.01]' : ''
              }`}
            >
              <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_right,_rgba(255,255,255,0.12),_transparent_55%)]" />
              <div className="relative z-10 space-y-0.5">
                <div 
                  className="flex items-center gap-0.5 font-semibold uppercase tracking-wide"
                  style={{ color: labelColor, fontSize: `${labelFontSize}px` }}
                >
                  <span style={{ fontSize: `${iconFontSize}px` }}>{card.icon}</span>
                  <span className="truncate">{card.label}</span>
                </div>
                <p 
                  className={`${isLastCard ? 'text-xs' : 'text-sm'} font-semibold leading-tight`}
                  style={{ color: valueColor }}
                >
                  {card.value}
                </p>
                <p 
                  className="line-clamp-1"
                  style={{ color: hintColor, fontSize: `${hintFontSize}px` }}
                >
                  {card.hint}
                </p>
              </div>
            </div>
          );
        })}
      </section>

      <AssetListModal
        isOpen={modalOpen}
        title={modalTitle}
        assetNumbers={modalAssetNumbers}
        onClose={() => setModalOpen(false)}
      />
    </>
  );
};

