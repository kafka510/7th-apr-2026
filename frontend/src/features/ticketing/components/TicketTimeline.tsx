import { useState } from 'react';

import type { TicketTimelineEntry } from '../types';

type TicketTimelineProps = {
  timeline: TicketTimelineEntry[];
  loading?: boolean;
};

export const TicketTimeline = ({ timeline, loading = false }: TicketTimelineProps) => {
  const [expanded, setExpanded] = useState(true);

  return (
    <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
      <div
        className="flex cursor-pointer items-center justify-between border-b border-slate-200 bg-slate-50 px-4 py-2"
        onClick={() => setExpanded(!expanded)}
      >
        <h3 className="text-sm font-semibold text-slate-900">Activity Timeline</h3>
        <span className="text-slate-500">{expanded ? '▼' : '▶'}</span>
      </div>

      {expanded && (
        <div className="p-4">
          {loading ? (
            <p className="text-sm text-slate-500">Loading timeline…</p>
          ) : timeline.length === 0 ? (
            <p className="text-sm text-slate-500">No recorded activity for this ticket yet.</p>
          ) : (
            <ul className="space-y-3">
              {timeline.map((entry) => (
                <li key={entry.id} className="flex gap-3 text-sm text-slate-700">
                  <div className="shrink-0">
                    <div className="size-2 rounded-full bg-sky-500" />
                  </div>
                  <div className="space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-semibold text-slate-900">{entry.user?.name ?? 'System'}</span>
                      <span className="text-xs text-slate-500">•</span>
                      <span className="text-xs text-slate-500">
                        {new Date(entry.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                    {entry.action && (
                      <p className="text-xs text-slate-500">{entry.action}</p>
                    )}
                    {entry.field ? (
                      <p className="text-xs text-slate-500">
                        <span className="font-semibold text-slate-600">{entry.field}</span> changed from{' '}
                        <span>{entry.old_value ?? '—'}</span> to <span>{entry.new_value ?? '—'}</span>
                      </p>
                    ) : null}
                    {entry.notes ? <p className="text-xs text-slate-500">{entry.notes}</p> : null}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
};


