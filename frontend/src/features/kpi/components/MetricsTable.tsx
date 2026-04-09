import type { KpiMetric } from '../types';

type MetricsTableProps = {
  metrics: KpiMetric[];
  loading?: boolean;
};

const numberFormatter = new Intl.NumberFormat(undefined, {
  maximumFractionDigits: 2,
});

const percentFormatter = new Intl.NumberFormat(undefined, {
  style: 'percent',
  maximumFractionDigits: 2,
});

export const MetricsTable = ({ metrics, loading = false }: MetricsTableProps) => {
  if (loading) {
    return (
      <section className="rounded-3xl border border-slate-800/80 bg-slate-950/70 p-6 shadow-2xl shadow-slate-950/40">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-white">Realtime Metrics (loading)</h2>
          <span className="text-xs uppercase tracking-wide text-slate-500">Fetching latest data…</span>
        </div>
        <div className="mt-4 space-y-2">
          {Array.from({ length: 5 }).map((_, index) => (
            <div
               
              key={index}
              className="h-12 animate-pulse rounded-xl bg-slate-800/60"
            />
          ))}
        </div>
      </section>
    );
  }

  if (metrics.length === 0) {
    return (
      <section className="rounded-3xl border border-slate-800/80 bg-slate-950/70 p-6 text-sm text-slate-200 shadow-2xl shadow-slate-950/40">
        <div className="flex items-center gap-3 text-slate-300">
          <span className="text-lg">ℹ️</span>
          <div>
            <p className="text-sm font-semibold text-white">No realtime KPI records match the filters</p>
            <p className="text-xs text-slate-400">
              Try widening the selection or resetting the filters to view a broader dataset.
            </p>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="relative overflow-hidden rounded-3xl border border-slate-800/80 bg-slate-950/75 p-6 shadow-2xl shadow-slate-950/40">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(59,130,246,0.08),_transparent_55%),radial-gradient(circle_at_bottom_right,_rgba(129,140,248,0.08),_transparent_60%)]" />
      <div className="relative flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-white md:text-xl">Realtime Metrics Overview</h2>
          <p className="text-xs text-slate-400">
            Snapshot of the most recent {Math.min(metrics.length, 50)} records pulled from the DRF API.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="rounded-full border border-slate-700 bg-slate-900/70 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-300">
            {metrics.length} rows
          </span>
          <button
            type="button"
            className="rounded-full bg-gradient-to-r from-sky-500 to-indigo-500 px-4 py-1.5 text-xs font-semibold uppercase tracking-wide text-white shadow shadow-sky-500/40 transition hover:from-sky-400 hover:to-indigo-400"
            onClick={() => {
              window.dispatchEvent(new CustomEvent('kpi:download-requested'));
            }}
          >
            Export CSV
          </button>
        </div>
      </div>

      <div className="relative mt-5 overflow-hidden overflow-x-auto rounded-2xl border border-slate-800/60">
        <table className="min-w-full divide-y divide-slate-800/80 text-sm text-slate-200">
          <thead className="bg-slate-900/90">
            <tr>
              <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-300">
                Asset
              </th>
              <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-300">
                Country
              </th>
              <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-300">
                Portfolio
              </th>
              <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-300">
                Date
              </th>
              <th className="px-5 py-3 text-right text-xs font-semibold uppercase tracking-wide text-slate-300">
                Actual (MWh)
              </th>
              <th className="px-5 py-3 text-right text-xs font-semibold uppercase tracking-wide text-slate-300">
                Expected (MWh)
              </th>
              <th className="px-5 py-3 text-right text-xs font-semibold uppercase tracking-wide text-slate-300">
                Actual PR
              </th>
              <th className="px-5 py-3 text-right text-xs font-semibold uppercase tracking-wide text-slate-300">
                Expected PR
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/70">
            {metrics.slice(0, 50).map((row) => (
              <tr
                key={`${row.asset_code}-${row.date}`}
                className="bg-slate-950/40 transition hover:bg-slate-800/60"
              >
                <td className="px-5 py-3 text-slate-100">
                  <div className="font-semibold text-white">{row.asset_code}</div>
                  <div className="text-xs text-slate-400">{row.asset_name}</div>
                </td>
                <td className="px-5 py-3 text-slate-300">{row.country || '—'}</td>
                <td className="px-5 py-3 text-slate-300">{row.portfolio || '—'}</td>
                <td className="px-5 py-3 text-slate-300">
                  {row.date ? new Date(row.date).toLocaleDateString() : '—'}
                </td>
                <td className="px-5 py-3 text-right text-slate-200">
                  {numberFormatter.format(Number(row.daily_generation_mwh ?? 0))}
                </td>
                <td className="px-5 py-3 text-right text-slate-200">
                  {numberFormatter.format(Number(row.daily_expected_mwh ?? 0))}
                </td>
                <td className="px-5 py-3 text-right text-slate-200">
                  {row.actual_pr !== undefined && row.actual_pr !== null
                    ? percentFormatter.format(Number(row.actual_pr))
                    : '—'}
                </td>
                <td className="px-5 py-3 text-right text-slate-200">
                  {row.expect_pr !== undefined && row.expect_pr !== null
                    ? percentFormatter.format(Number(row.expect_pr))
                    : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
};

