import { useResponsiveFontSize } from '../../../utils/fontScaling';
import type { YieldSummary } from '../types';

type SummaryCardsProps = {
  summary: YieldSummary;
  loading?: boolean;
};

const numberFormatter = new Intl.NumberFormat(undefined, {
  maximumFractionDigits: 0,
});

const formatMWh = (value: number): string => {
  return `${numberFormatter.format(value)} MWh`;
};

export const SummaryCards = ({ summary, loading = false }: SummaryCardsProps) => {
  // Responsive font sizes
  const labelFontSize = useResponsiveFontSize(9, 13, 8);
  const iconFontSize = useResponsiveFontSize(10, 14, 9);
  const hintFontSize = useResponsiveFontSize(9, 13, 8);
  
  const cards = [
    {
      label: 'IC Approved Budget',
      value: loading ? '—' : formatMWh(summary.totalIcApprovedBudget),
      hint: 'Total approved budget',
      icon: '💰',
      gradient: 'from-blue-500/20 via-blue-500/10 to-slate-900/60',
      shadow: 'shadow-blue-500/20',
    },
    {
      label: 'Expected Budget',
      value: loading ? '—' : formatMWh(summary.totalExpectedBudget),
      hint: 'Total expected generation',
      icon: '📈',
      gradient: 'from-emerald-500/20 via-emerald-500/10 to-slate-900/60',
      shadow: 'shadow-emerald-500/20',
    },
    {
      label: 'Actual Generation',
      value: loading ? '—' : formatMWh(summary.totalActualGeneration),
      hint: 'Total actual generation',
      icon: '⚡',
      gradient: 'from-yellow-500/20 via-yellow-500/10 to-slate-900/60',
      shadow: 'shadow-yellow-500/20',
    },
    {
      label: 'Weather Loss/Gain',
      value: loading ? '—' : formatMWh(summary.totalWeatherLossOrGain),
      hint: 'Weather impact',
      icon: '🌤️',
      gradient: 'from-cyan-500/20 via-cyan-500/10 to-slate-900/60',
      shadow: 'shadow-cyan-500/20',
    },
    {
      label: 'Grid Curtailment',
      value: loading ? '—' : formatMWh(summary.totalGridCurtailment),
      hint: 'Grid curtailment losses',
      icon: '🔌',
      gradient: 'from-orange-500/20 via-orange-500/10 to-slate-900/60',
      shadow: 'shadow-orange-500/20',
    },
    {
      label: 'Grid Outage',
      value: loading ? '—' : formatMWh(summary.totalGridOutage),
      hint: 'Grid outage losses',
      icon: '⚠️',
      gradient: 'from-red-500/20 via-red-500/10 to-slate-900/60',
      shadow: 'shadow-red-500/20',
    },
    {
      label: 'Operation Budget',
      value: loading ? '—' : formatMWh(summary.totalOperationBudget),
      hint: 'Operational budget',
      icon: '⚙️',
      gradient: 'from-purple-500/20 via-purple-500/10 to-slate-900/60',
      shadow: 'shadow-purple-500/20',
    },
    {
      label: 'Breakdown Loss',
      value: loading ? '—' : formatMWh(summary.totalBreakdownLoss),
      hint: 'Equipment breakdown losses',
      icon: '🔧',
      gradient: 'from-pink-500/20 via-pink-500/10 to-slate-900/60',
      shadow: 'shadow-pink-500/20',
    },
    {
      label: 'Unclassified Loss',
      value: loading ? '—' : formatMWh(summary.totalUnclassifiedLoss),
      hint: 'Unclassified losses',
      icon: '❓',
      gradient: 'from-gray-500/20 via-gray-500/10 to-slate-900/60',
      shadow: 'shadow-gray-500/20',
    },
  ];

  return (
    <section className="grid gap-1.5 rounded-3xl border border-slate-800/80 bg-slate-950/70 p-2 shadow-2xl shadow-slate-950/50 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {cards.map((card) => (
        <div
          key={card.label}
          className={`relative overflow-hidden rounded-xl border border-slate-800/80 bg-gradient-to-br ${card.gradient} p-2 text-left shadow-lg ${card.shadow}`}
        >
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_right,_rgba(255,255,255,0.12),_transparent_55%)]" />
          <div className="relative z-10 space-y-1">
            <div className="flex items-center gap-1 font-semibold uppercase tracking-wide text-slate-200/80" style={{ fontSize: `${labelFontSize}px` }}>
              <span style={{ fontSize: `${iconFontSize}px` }}>{card.icon}</span>
              <span className="truncate">{card.label}</span>
            </div>
            <p className="text-lg font-semibold leading-tight text-white">{card.value}</p>
            <p className="line-clamp-1 text-slate-300/80" style={{ fontSize: `${hintFontSize}px` }}>{card.hint}</p>
          </div>
        </div>
      ))}
    </section>
  );
};

