import { useMemo } from 'react';
import { useResponsiveFontSize } from '../../../utils/fontScaling';

import type { KpiGaugeValues } from '../types';
import { buildGaugeInsights, type GaugeInsightTone } from '../utils/gaugeInsights';

const toneStyles: Record<
  GaugeInsightTone,
  {
    badge: string;
    card: string;
    dot: string;
  }
> = {
  positive: {
    badge: 'bg-emerald-500/20 border-emerald-400/50 text-emerald-200',
    card: 'border-emerald-500/40 bg-emerald-500/10',
    dot: 'bg-emerald-400/80',
  },
  neutral: {
    badge: 'bg-slate-500/20 border-slate-400/40 text-slate-200',
    card: 'border-slate-500/30 bg-slate-800/40',
    dot: 'bg-slate-400/70',
  },
  negative: {
    badge: 'bg-rose-500/20 border-rose-400/50 text-rose-200',
    card: 'border-rose-500/40 bg-rose-500/10',
    dot: 'bg-rose-400/80',
  },
};

type GaugeInsightsProps = {
  values: KpiGaugeValues;
  loading?: boolean;
};

export const GaugeInsights = ({ values, loading = false }: GaugeInsightsProps) => {
  // Responsive font sizes
  const badgeFontSize = useResponsiveFontSize(11, 15, 10);
  
  const insightsResult = useMemo(() => buildGaugeInsights(values), [values]);

  const summaryTone = toneStyles[insightsResult.summary.tone];

  return (
    <section className="rounded-3xl border border-slate-800/80 bg-slate-950/70 p-6 shadow-2xl shadow-slate-950/40">
      <header className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
            Executive Summary
          </p>
          <h2 className="text-lg font-semibold text-white md:text-xl">
            Automated insights from the gauge performance snapshot
          </h2>
        </div>
        <span
          className={`inline-flex items-center gap-2 rounded-full border px-4 py-1.5 text-xs font-semibold uppercase tracking-wide ${summaryTone.badge}`}
        >
          <span className={`size-2 rounded-full ${summaryTone.dot}`} />
          {insightsResult.summary.headline}
        </span>
      </header>

      <div className="mt-6 space-y-4">
        {loading ? (
          <div className="grid gap-4 lg:grid-cols-2">
            {Array.from({ length: 4 }).map((_, index) => (
              <div
                key={index}
                className="animate-pulse rounded-2xl border border-slate-800/60 bg-slate-900/60 p-5"
              >
                <div className="h-4 w-28 rounded bg-slate-800/70" />
                <div className="mt-3 h-6 w-40 rounded bg-slate-800/70" />
                <div className="mt-3 h-10 w-full rounded bg-slate-800/70" />
              </div>
            ))}
          </div>
        ) : insightsResult.insights.length === 0 ? (
          <div className="rounded-2xl border border-slate-800/70 bg-slate-900/50 p-6 text-sm text-slate-300">
            Gauge data is unavailable for the current filter selection. Adjust the filters to view
            automated commentary.
          </div>
        ) : (
          <>
            <p className="text-sm text-slate-300 md:max-w-2xl">
              {insightsResult.summary.detail}
            </p>
            <div className="grid gap-4 lg:grid-cols-2">
              {insightsResult.insights.map((insight) => {
                const tone = toneStyles[insight.tone];
                return (
                  <article
                    key={insight.id}
                    className={`rounded-2xl border px-5 py-4 shadow-lg shadow-slate-950/30 transition hover:-translate-y-0.5 hover:shadow-xl ${tone.card}`}
                  >
                    <header className="flex items-center justify-between gap-3">
                      <span className="text-xs font-semibold uppercase tracking-[0.25em] text-slate-300/80">
                        {insight.label}
                      </span>
                      <span className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 font-semibold uppercase tracking-wide ${tone.badge}`} style={{ fontSize: `${badgeFontSize}px` }}>
                        <span className={`size-2 rounded-full ${tone.dot}`} />
                        {insight.tone === 'positive'
                          ? 'Above Target'
                          : insight.tone === 'negative'
                          ? 'Below Target'
                          : 'On Target'}
                      </span>
                    </header>
                    <p className="mt-3 text-base font-semibold text-white">{insight.headline}</p>
                    <p className="mt-2 text-sm text-slate-300">{insight.detail}</p>
                  </article>
                );
              })}
            </div>
          </>
        )}
      </div>
    </section>
  );
};


