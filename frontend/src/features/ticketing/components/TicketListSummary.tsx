import { useMemo } from 'react';
import { useTheme } from '../../../contexts/ThemeContext';
import type { TicketListSummary as TicketListSummaryType } from '../types';

type TicketListSummaryProps = {
  summary: TicketListSummaryType | null;
  loading: boolean;
  activeStatuses: string[];
  onStatusFilter?: (statuses: string[] | null) => void;
};

const numberFormatter = new Intl.NumberFormat();

const METRIC_DEFINITIONS: Array<{
  key: 'total' | 'open' | 'awaitingApproval' | 'unassigned' | 'critical';
  label: string;
  description: string;
  accent: string;
}> = [
  {
    key: 'total',
    label: 'Total Tickets',
    description: 'Across all filters',
    accent: 'border-sky-500/30 bg-gradient-to-br from-sky-900/40 to-sky-800/30 text-sky-200',
  },
  {
    key: 'open',
    label: 'Open Work',
    description: 'Raised, in progress, or reopened',
    accent: 'border-emerald-500/30 bg-gradient-to-br from-emerald-900/40 to-emerald-800/30 text-emerald-200',
  },
  {
    key: 'awaitingApproval',
    label: 'Awaiting Approval',
    description: 'Waiting for gate review',
    accent: 'border-amber-500/30 bg-gradient-to-br from-amber-900/40 to-amber-800/30 text-amber-200',
  },
  {
    key: 'unassigned',
    label: 'Unassigned',
    description: 'Needs an owner',
    accent: 'border-slate-700/50 bg-gradient-to-br from-slate-800/60 to-slate-900/40 text-slate-200',
  },
  {
    key: 'critical',
    label: 'Critical Priority',
    description: 'High urgency items',
    accent: 'border-rose-500/30 bg-gradient-to-br from-rose-900/40 to-rose-800/30 text-rose-200',
  },
];

export const TicketListSummary = ({
  summary,
  loading,
  activeStatuses,
  onStatusFilter,
}: TicketListSummaryProps) => {
  const { theme } = useTheme();
  
  const containerBg = theme === 'dark'
    ? 'linear-gradient(to bottom right, rgba(15, 23, 42, 0.5), rgba(30, 41, 59, 0.3))'
    : 'linear-gradient(to bottom right, rgba(248, 250, 252, 0.9), rgba(241, 245, 249, 0.8))';
  const containerBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(203, 213, 225, 0.8)';
  const containerShadow = theme === 'dark' 
    ? '0 10px 15px -3px rgba(0, 0, 0, 0.3)' 
    : '0 4px 6px -1px rgba(0, 0, 0, 0.1)';
  const skeletonBg = theme === 'dark' ? 'rgba(51, 65, 85, 0.5)' : 'rgba(226, 232, 240, 0.5)';
  const skeletonBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(203, 213, 225, 0.8)';
  const labelText = theme === 'dark' ? '#94a3b8' : '#64748b';
  
  const statusBreakdown = useMemo(() => {
    if (!summary) {
      return [];
    }
    return [...summary.statusBreakdown].sort((a, b) => b.count - a.count);
  }, [summary]);

  // Theme-aware metric colors
  const getMetricStyles = (key: string) => {
    const baseStyles = {
      total: {
        border: theme === 'dark' ? 'rgba(59, 130, 246, 0.3)' : 'rgba(59, 130, 246, 0.5)',
        bg: theme === 'dark' 
          ? 'linear-gradient(to bottom right, rgba(30, 58, 138, 0.4), rgba(30, 64, 175, 0.3))' 
          : 'linear-gradient(to bottom right, rgba(59, 130, 246, 0.15), rgba(59, 130, 246, 0.1))',
        text: theme === 'dark' ? '#93c5fd' : '#1e40af',
      },
      open: {
        border: theme === 'dark' ? 'rgba(16, 185, 129, 0.3)' : 'rgba(16, 185, 129, 0.5)',
        bg: theme === 'dark' 
          ? 'linear-gradient(to bottom right, rgba(5, 150, 105, 0.4), rgba(6, 95, 70, 0.3))' 
          : 'linear-gradient(to bottom right, rgba(16, 185, 129, 0.15), rgba(16, 185, 129, 0.1))',
        text: theme === 'dark' ? '#6ee7b7' : '#059669',
      },
      awaitingApproval: {
        border: theme === 'dark' ? 'rgba(245, 158, 11, 0.3)' : 'rgba(245, 158, 11, 0.5)',
        bg: theme === 'dark' 
          ? 'linear-gradient(to bottom right, rgba(217, 119, 6, 0.4), rgba(154, 52, 18, 0.3))' 
          : 'linear-gradient(to bottom right, rgba(245, 158, 11, 0.15), rgba(245, 158, 11, 0.1))',
        text: theme === 'dark' ? '#fcd34d' : '#d97706',
      },
      unassigned: {
        border: theme === 'dark' ? 'rgba(51, 65, 85, 0.5)' : 'rgba(148, 163, 184, 0.5)',
        bg: theme === 'dark' 
          ? 'linear-gradient(to bottom right, rgba(30, 41, 59, 0.6), rgba(15, 23, 42, 0.4))' 
          : 'linear-gradient(to bottom right, rgba(241, 245, 249, 0.9), rgba(226, 232, 240, 0.8))',
        text: theme === 'dark' ? '#e2e8f0' : '#475569',
      },
      critical: {
        border: theme === 'dark' ? 'rgba(244, 63, 94, 0.3)' : 'rgba(244, 63, 94, 0.5)',
        bg: theme === 'dark' 
          ? 'linear-gradient(to bottom right, rgba(190, 18, 60, 0.4), rgba(136, 19, 55, 0.3))' 
          : 'linear-gradient(to bottom right, rgba(244, 63, 94, 0.15), rgba(244, 63, 94, 0.1))',
        text: theme === 'dark' ? '#fca5a5' : '#dc2626',
      },
    };
    return baseStyles[key as keyof typeof baseStyles] || baseStyles.total;
  };

  const statusButtonActiveBg = theme === 'dark' ? 'rgba(59, 130, 246, 0.3)' : 'rgba(59, 130, 246, 0.15)';
  const statusButtonActiveBorder = theme === 'dark' ? 'rgba(59, 130, 246, 0.5)' : 'rgba(59, 130, 246, 0.7)';
  const statusButtonActiveText = theme === 'dark' ? '#93c5fd' : '#1e40af';
  const statusButtonInactiveBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.6)' : 'rgba(248, 250, 252, 0.9)';
  const statusButtonInactiveBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : 'rgba(203, 213, 225, 0.8)';
  const statusButtonInactiveText = theme === 'dark' ? '#cbd5e1' : '#475569';
  const statusButtonHoverBorder = theme === 'dark' ? 'rgba(59, 130, 246, 0.5)' : '#3b82f6';
  const statusButtonHoverText = theme === 'dark' ? '#93c5fd' : '#0072ce';
  const statusBadgeBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.6)' : 'rgba(241, 245, 249, 0.9)';
  const statusBadgeText = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';
  const clearButtonBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.8)' : '#ffffff';
  const clearButtonBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : 'rgba(203, 213, 225, 0.8)';
  const clearButtonText = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';
  const clearButtonHoverBorder = theme === 'dark' ? 'rgba(100, 116, 139, 0.6)' : '#94a3b8';
  const clearButtonHoverText = theme === 'dark' ? '#f1f5f9' : '#0f172a';

  return (
    <section 
      className="rounded-xl border p-2 shadow-lg"
      style={{
        borderColor: containerBorder,
        background: containerBg,
        boxShadow: containerShadow,
      }}
    >
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-5">
        {loading
          ? METRIC_DEFINITIONS.map((metric) => (
              <div
                key={`loading-${metric.key}`}
                className="flex items-center justify-between rounded-lg border p-2 shadow-inner"
                style={{
                  borderColor: skeletonBorder,
                  backgroundColor: skeletonBg,
                }}
              >
                <div 
                  className="h-3 w-16 animate-pulse rounded"
                  style={{ backgroundColor: theme === 'dark' ? 'rgba(71, 85, 105, 0.7)' : 'rgba(203, 213, 225, 0.7)' }}
                />
                <div 
                  className="h-2 w-12 animate-pulse rounded"
                  style={{ backgroundColor: theme === 'dark' ? 'rgba(71, 85, 105, 0.7)' : 'rgba(203, 213, 225, 0.7)' }}
                />
              </div>
            ))
          : METRIC_DEFINITIONS.map((metric) => {
              const value = summary ? summary[metric.key] : 0;
              const styles = getMetricStyles(metric.key);
              return (
                <article
                  key={metric.key}
                  className="flex items-center justify-between rounded-lg border p-2 shadow-lg transition hover:-translate-y-0.5 hover:shadow-xl"
                  style={{
                    borderColor: styles.border,
                    background: styles.bg,
                    color: styles.text,
                  }}
                >
                  <div className="text-lg font-bold">
                    {summary ? numberFormatter.format(value) : '—'}
                  </div>
                  <div className="text-right text-[9px] font-semibold uppercase tracking-wide">{metric.label}</div>
                </article>
              );
            })}
      </div>

      {statusBreakdown.length > 0 ? (
        <div className="mt-2 space-y-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 
              className="text-[9px] font-semibold uppercase tracking-[0.3em]"
              style={{ color: labelText }}
            >
              Status Distribution
            </h3>
            {activeStatuses.length > 0 && onStatusFilter ? (
              <button
                type="button"
                onClick={() => onStatusFilter(null)}
                className="rounded-lg border px-2 py-0.5 text-[9px] font-semibold uppercase tracking-wide shadow-sm transition"
                style={{
                  borderColor: clearButtonBorder,
                  backgroundColor: clearButtonBg,
                  color: clearButtonText,
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = clearButtonHoverBorder;
                  e.currentTarget.style.color = clearButtonHoverText;
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = clearButtonBorder;
                  e.currentTarget.style.color = clearButtonText;
                }}
              >
                Clear status filters
              </button>
            ) : null}
          </div>
          <div className="flex flex-wrap gap-1.5">
            {statusBreakdown.map((bucket) => {
              const isActive = activeStatuses.includes(bucket.status);
              const isZero = bucket.count === 0;
              const label = `${bucket.label}`;

              return (
                <button
                  key={bucket.status}
                  type="button"
                  disabled={!onStatusFilter || isZero}
                  onClick={() => onStatusFilter?.([bucket.status])}
                  className="inline-flex items-center gap-1 rounded-lg border px-2 py-1 text-[9px] font-semibold uppercase tracking-wide shadow-sm transition"
                  style={{
                    borderColor: isActive ? statusButtonActiveBorder : statusButtonInactiveBorder,
                    backgroundColor: isActive ? statusButtonActiveBg : statusButtonInactiveBg,
                    color: isActive ? statusButtonActiveText : statusButtonInactiveText,
                    opacity: isZero ? 0.5 : 1,
                    cursor: (!onStatusFilter || isZero) ? 'not-allowed' : 'pointer',
                  }}
                  onMouseEnter={(e) => {
                    if (!isZero && onStatusFilter) {
                      e.currentTarget.style.borderColor = statusButtonHoverBorder;
                      e.currentTarget.style.color = statusButtonHoverText;
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!isZero && onStatusFilter) {
                      e.currentTarget.style.borderColor = isActive ? statusButtonActiveBorder : statusButtonInactiveBorder;
                      e.currentTarget.style.color = isActive ? statusButtonActiveText : statusButtonInactiveText;
                    }
                  }}
                >
                  <span>{label}</span>
                  <span 
                    className="rounded-full px-1.5 py-0.5 text-[8px] font-bold"
                    style={{
                      backgroundColor: statusBadgeBg,
                      color: statusBadgeText,
                    }}
                  >
                    {numberFormatter.format(bucket.count)}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      ) : null}
    </section>
  );
};


