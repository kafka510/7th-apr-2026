import { useTheme } from '../../../contexts/ThemeContext';
import type { ChartDataset, TicketDashboardKpis } from '../types';

type DashboardSummaryCardsProps = {
  kpis: TicketDashboardKpis | null;
  statusData?: ChartDataset | null;
  loading?: boolean;
};

const numberFormatter = new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 });

const METRIC_DEFINITIONS: Array<{
  key: keyof TicketDashboardKpis;
  label: string;
  accent: string;
}> = [
  {
    key: 'total_tickets',
    label: 'Total Tickets',
    accent: 'border-sky-500/30 bg-gradient-to-br from-sky-900/40 to-sky-800/30 text-sky-200',
  },
  {
    key: 'open_tickets',
    label: 'Open Tickets',
    accent: 'border-emerald-500/30 bg-gradient-to-br from-emerald-900/40 to-emerald-800/30 text-emerald-200',
  },
  {
    key: 'unassigned_tickets',
    label: 'Unassigned',
    accent: 'border-slate-700/50 bg-gradient-to-br from-slate-800/60 to-slate-900/40 text-slate-200',
  },
  {
    key: 'overdue_tickets',
    label: 'Overdue',
    accent: 'border-rose-500/30 bg-gradient-to-br from-rose-900/40 to-rose-800/30 text-rose-200',
  },
];

export const DashboardSummaryCards = ({ kpis, statusData, loading = false }: DashboardSummaryCardsProps) => {
  const { theme } = useTheme();
  
  const containerBg = theme === 'dark'
    ? 'linear-gradient(to bottom right, rgba(15, 23, 42, 0.9), rgba(30, 41, 59, 0.6))'
    : 'linear-gradient(to bottom right, rgba(255, 255, 255, 0.95), rgba(248, 250, 252, 0.9))';
  const containerBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(203, 213, 225, 0.8)';
  const containerShadow = theme === 'dark' 
    ? '0 20px 25px -5px rgba(0, 0, 0, 0.4)' 
    : '0 10px 15px -3px rgba(0, 0, 0, 0.1)';
  const skeletonBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.5)' : 'rgba(241, 245, 249, 0.8)';
  const skeletonBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(203, 213, 225, 0.8)';
  const skeletonPulse = theme === 'dark' ? 'rgba(71, 85, 105, 0.7)' : 'rgba(203, 213, 225, 0.7)';
  
  // Helper function to get metric card styles
  const getMetricStyles = (key: string) => {
    const styles: Record<string, { border: string; bg: string; text: string }> = {
      total_tickets: {
        border: theme === 'dark' ? 'rgba(59, 130, 246, 0.3)' : 'rgba(59, 130, 246, 0.5)',
        bg: theme === 'dark' 
          ? 'linear-gradient(to bottom right, rgba(30, 58, 138, 0.4), rgba(30, 64, 175, 0.3))' 
          : 'linear-gradient(to bottom right, rgba(59, 130, 246, 0.15), rgba(59, 130, 246, 0.1))',
        text: theme === 'dark' ? '#93c5fd' : '#1e40af',
      },
      open_tickets: {
        border: theme === 'dark' ? 'rgba(16, 185, 129, 0.3)' : 'rgba(16, 185, 129, 0.5)',
        bg: theme === 'dark' 
          ? 'linear-gradient(to bottom right, rgba(5, 150, 105, 0.4), rgba(6, 95, 70, 0.3))' 
          : 'linear-gradient(to bottom right, rgba(16, 185, 129, 0.15), rgba(16, 185, 129, 0.1))',
        text: theme === 'dark' ? '#6ee7b7' : '#059669',
      },
      unassigned_tickets: {
        border: theme === 'dark' ? 'rgba(51, 65, 85, 0.5)' : 'rgba(148, 163, 184, 0.5)',
        bg: theme === 'dark' 
          ? 'linear-gradient(to bottom right, rgba(30, 41, 59, 0.6), rgba(15, 23, 42, 0.4))' 
          : 'linear-gradient(to bottom right, rgba(241, 245, 249, 0.9), rgba(226, 232, 240, 0.8))',
        text: theme === 'dark' ? '#e2e8f0' : '#475569',
      },
      overdue_tickets: {
        border: theme === 'dark' ? 'rgba(244, 63, 94, 0.3)' : 'rgba(244, 63, 94, 0.5)',
        bg: theme === 'dark' 
          ? 'linear-gradient(to bottom right, rgba(190, 18, 60, 0.4), rgba(136, 19, 55, 0.3))' 
          : 'linear-gradient(to bottom right, rgba(244, 63, 94, 0.15), rgba(244, 63, 94, 0.1))',
        text: theme === 'dark' ? '#fca5a5' : '#dc2626',
      },
    };
    return styles[key] || styles.total_tickets;
  };

  // Helper function to get status card styles
  const getStatusCardStyles = (label: string) => {
    const normalized = label.toLowerCase().replace(/\s+/g, '_');
    const styles: Record<string, { border: string; bg: string; text: string }> = {
      raised: {
        border: theme === 'dark' ? 'rgba(59, 130, 246, 0.3)' : 'rgba(59, 130, 246, 0.5)',
        bg: theme === 'dark' 
          ? 'linear-gradient(to bottom right, rgba(30, 58, 138, 0.4), rgba(30, 64, 175, 0.3))' 
          : 'linear-gradient(to bottom right, rgba(59, 130, 246, 0.15), rgba(59, 130, 246, 0.1))',
        text: theme === 'dark' ? '#93c5fd' : '#1e40af',
      },
      in_progress: {
        border: theme === 'dark' ? 'rgba(16, 185, 129, 0.3)' : 'rgba(16, 185, 129, 0.5)',
        bg: theme === 'dark' 
          ? 'linear-gradient(to bottom right, rgba(5, 150, 105, 0.4), rgba(6, 95, 70, 0.3))' 
          : 'linear-gradient(to bottom right, rgba(16, 185, 129, 0.15), rgba(16, 185, 129, 0.1))',
        text: theme === 'dark' ? '#6ee7b7' : '#059669',
      },
      on_hold: {
        border: theme === 'dark' ? 'rgba(245, 158, 11, 0.3)' : 'rgba(245, 158, 11, 0.5)',
        bg: theme === 'dark' 
          ? 'linear-gradient(to bottom right, rgba(217, 119, 6, 0.4), rgba(154, 52, 18, 0.3))' 
          : 'linear-gradient(to bottom right, rgba(245, 158, 11, 0.15), rgba(245, 158, 11, 0.1))',
        text: theme === 'dark' ? '#fcd34d' : '#d97706',
      },
      awaiting_approval: {
        border: theme === 'dark' ? 'rgba(168, 85, 247, 0.3)' : 'rgba(168, 85, 247, 0.5)',
        bg: theme === 'dark' 
          ? 'linear-gradient(to bottom right, rgba(126, 34, 206, 0.4), rgba(88, 28, 135, 0.3))' 
          : 'linear-gradient(to bottom right, rgba(168, 85, 247, 0.15), rgba(168, 85, 247, 0.1))',
        text: theme === 'dark' ? '#c084fc' : '#7c3aed',
      },
      closed: {
        border: theme === 'dark' ? 'rgba(51, 65, 85, 0.5)' : 'rgba(148, 163, 184, 0.5)',
        bg: theme === 'dark' 
          ? 'linear-gradient(to bottom right, rgba(30, 41, 59, 0.6), rgba(15, 23, 42, 0.4))' 
          : 'linear-gradient(to bottom right, rgba(241, 245, 249, 0.9), rgba(226, 232, 240, 0.8))',
        text: theme === 'dark' ? '#e2e8f0' : '#475569',
      },
      cancelled: {
        border: theme === 'dark' ? 'rgba(51, 65, 85, 0.5)' : 'rgba(148, 163, 184, 0.5)',
        bg: theme === 'dark' 
          ? 'linear-gradient(to bottom right, rgba(30, 41, 59, 0.6), rgba(15, 23, 42, 0.4))' 
          : 'linear-gradient(to bottom right, rgba(241, 245, 249, 0.9), rgba(226, 232, 240, 0.8))',
        text: theme === 'dark' ? '#e2e8f0' : '#475569',
      },
      reopened: {
        border: theme === 'dark' ? 'rgba(249, 115, 22, 0.3)' : 'rgba(249, 115, 22, 0.5)',
        bg: theme === 'dark' 
          ? 'linear-gradient(to bottom right, rgba(234, 88, 12, 0.4), rgba(154, 52, 18, 0.3))' 
          : 'linear-gradient(to bottom right, rgba(249, 115, 22, 0.15), rgba(249, 115, 22, 0.1))',
        text: theme === 'dark' ? '#fb923c' : '#ea580c',
      },
    };
    return styles[normalized] || {
      border: theme === 'dark' ? 'rgba(51, 65, 85, 0.5)' : 'rgba(148, 163, 184, 0.5)',
      bg: theme === 'dark' 
        ? 'linear-gradient(to bottom right, rgba(30, 41, 59, 0.6), rgba(15, 23, 42, 0.4))' 
        : 'linear-gradient(to bottom right, rgba(241, 245, 249, 0.9), rgba(226, 232, 240, 0.8))',
      text: theme === 'dark' ? '#e2e8f0' : '#475569',
    };
  };
  
  // Create status cards from status chart data
  const statusCards = statusData
    ? statusData.labels.map((label, index) => ({
        label,
        value: statusData.values[index] || 0,
        styles: getStatusCardStyles(label),
      }))
    : [];

  // Combine KPI cards and status cards
  const allCards = [
    ...METRIC_DEFINITIONS.map((metric) => ({
      type: 'kpi' as const,
      key: metric.key,
      label: metric.label,
      value: kpis ? kpis[metric.key] : 0,
      styles: getMetricStyles(metric.key),
    })),
    ...statusCards.map((status, index) => ({
      type: 'status' as const,
      key: `status-${index}`,
      label: status.label,
      value: status.value,
      styles: status.styles,
    })),
  ];

  return (
    <section 
      className="rounded-xl border p-4 shadow-xl"
      style={{
        borderColor: containerBorder,
        background: containerBg,
        boxShadow: containerShadow,
      }}
    >
      <div className="flex flex-nowrap gap-3 overflow-x-auto">
        {loading
          ? allCards.map((card) => (
              <div
                key={`loading-${card.key}`}
                className="flex min-w-[140px] shrink-0 flex-col gap-1 rounded-lg border p-3 shadow-inner"
                style={{
                  borderColor: skeletonBorder,
                  backgroundColor: skeletonBg,
                }}
              >
                <div 
                  className="h-4 w-20 animate-pulse rounded"
                  style={{ backgroundColor: skeletonPulse }}
                />
                <div 
                  className="h-6 w-16 animate-pulse rounded"
                  style={{ backgroundColor: skeletonPulse }}
                />
              </div>
            ))
          : allCards.map((card) => {
              return (
                <article
                  key={card.key}
                  className="flex min-w-[140px] shrink-0 flex-col gap-1 rounded-lg border p-3 shadow-lg transition hover:-translate-y-0.5 hover:shadow-xl"
                  style={{
                    borderColor: card.styles.border,
                    background: card.styles.bg,
                    color: card.styles.text,
                  }}
                >
                  <div className="text-xs font-semibold uppercase tracking-wide">{card.label}</div>
                  <div className="text-2xl font-bold">
                    {numberFormatter.format(card.value)}
                  </div>
                </article>
              );
            })}
      </div>
    </section>
  );
};

