import { useMemo } from 'react';
import type { YieldData } from '../types';

interface YieldSummaryCardsProps {
  data: YieldData[];
  loading?: boolean;
}

function toNum(val: number | string | undefined): number {
  if (val === undefined) return 0;
  if (typeof val === 'number') return isNaN(val) ? 0 : val;
  if (typeof val === 'string') {
    const num = parseFloat(val);
    return isNaN(num) ? 0 : num;
  }
  return 0;
}

export function YieldSummaryCards({ data, loading = false }: YieldSummaryCardsProps) {
  const summary = useMemo(() => {
    if (!data.length) {
      return { dcCapacity: 0, acCapacity: 0, bessCapacity: 0 };
    }

    // Sum up capacities from filtered data (use latest record per asset if duplicates)
    const assetMap = new Map<string, YieldData>();
    data.forEach((row) => {
      const asset = String(row.assetno || '');
      if (!asset) return;
      
      const existing = assetMap.get(asset);
      if (!existing) {
        assetMap.set(asset, row);
      } else {
        // Use the one with the latest month if available
        if (row.month && existing.month) {
          if (row.month > existing.month) {
            assetMap.set(asset, row);
          }
        }
      }
    });

    let dcCapacity = 0;
    let acCapacity = 0;
    let bessCapacity = 0;

    assetMap.forEach((row) => {
      dcCapacity += toNum(row.dc_capacity_mw);
      acCapacity += toNum(row.ac_capacity_mw);
      bessCapacity += toNum(row.bess_capacity_mwh);
    });

    return { dcCapacity, acCapacity, bessCapacity };
  }, [data]);

  const cards = [
    {
      icon: '🔋',
      title: 'DC Capacity (MW)',
      value: loading ? '—' : summary.dcCapacity.toFixed(2),
      gradient: 'from-blue-500/20 via-blue-500/10 to-slate-900/60',
      shadow: 'shadow-blue-500/20',
    },
    {
      icon: '⚡',
      title: 'AC Capacity (MW)',
      value: loading ? '—' : summary.acCapacity.toFixed(2),
      gradient: 'from-green-500/20 via-green-500/10 to-slate-900/60',
      shadow: 'shadow-green-500/20',
    },
    {
      icon: '🔋',
      title: 'BESS Capacity (MWh)',
      value: loading ? '—' : summary.bessCapacity.toFixed(2),
      gradient: 'from-yellow-500/20 via-yellow-500/10 to-slate-900/60',
      shadow: 'shadow-yellow-500/20',
    },
  ];

  return (
    <section className="grid gap-2 rounded-xl border border-slate-800/80 bg-slate-950/70 p-4 shadow-2xl shadow-slate-950/50 sm:grid-cols-2 lg:grid-cols-3">
      {cards.map((card) => (
        <div
          key={card.title}
          className={`relative overflow-hidden rounded-xl border border-slate-800/80 bg-gradient-to-br ${card.gradient} p-4 text-left shadow-lg ${card.shadow} transition hover:scale-[1.02] hover:border-sky-500/50`}
        >
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_right,_rgba(255,255,255,0.12),_transparent_55%)]" />
          <div className="relative z-10 flex items-center gap-3">
            <div className="text-3xl">{card.icon}</div>
            <div className="flex-1">
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-200/80">
                {card.title}
              </div>
              <div className="text-xl font-bold leading-tight text-white">{card.value}</div>
            </div>
          </div>
        </div>
      ))}
    </section>
  );
}

