import { useState } from 'react';
import { changeTicketStatus } from '../api';
import type { TicketDetail } from '../types';

type TicketStatusActionsProps = {
  ticketId: string;
  detail: TicketDetail | null;
  onStatusChanged: () => void;
};

export const TicketStatusActions = ({ ticketId, detail, onStatusChanged }: TicketStatusActionsProps) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!detail) {
    return null;
  }

  const currentStatus = detail.status;
  const canStart = currentStatus === 'raised';
  const canComplete = currentStatus === 'in_progress' || currentStatus === 'submitted';

  const handleStart = async () => {
    if (!canStart) {
      return;
    }

    setLoading(true);
    setError(null);

    try {
      await changeTicketStatus(ticketId, 'in_progress');
      onStatusChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start ticket');
    } finally {
      setLoading(false);
    }
  };

  const handleComplete = async () => {
    if (!canComplete) {
      return;
    }

    if (!window.confirm('Are you sure you want to mark this ticket as completed? This will close the ticket.')) {
      return;
    }

    setLoading(true);
    setError(null);

    try {
      await changeTicketStatus(ticketId, 'closed');
      onStatusChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to complete ticket');
    } finally {
      setLoading(false);
    }
  };

  // Don't show buttons if ticket is already closed or cancelled
  if (currentStatus === 'closed' || currentStatus === 'cancelled') {
    return null;
  }

  return (
    <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
      <header className="mb-4">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Quick Actions</p>
        <h2 className="mt-1 text-lg font-semibold text-slate-900">Ticket Status</h2>
      </header>

      {error && (
        <div className="mb-4 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
          {error}
        </div>
      )}

      <div className="flex flex-wrap gap-3">
        {canStart && (
          <button
            type="button"
            onClick={handleStart}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-5 py-2.5 text-sm font-semibold text-emerald-700 transition hover:border-emerald-300 hover:bg-emerald-100 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <svg
              className="size-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            {loading ? 'Starting...' : 'Start Ticket'}
          </button>
        )}

        {canComplete && (
          <button
            type="button"
            onClick={handleComplete}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-lg border border-sky-200 bg-sky-50 px-5 py-2.5 text-sm font-semibold text-sky-700 transition hover:border-sky-300 hover:bg-sky-100 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <svg
              className="size-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            {loading ? 'Completing...' : 'Complete Ticket'}
          </button>
        )}

        {!canStart && !canComplete && currentStatus !== 'closed' && currentStatus !== 'cancelled' && (
          <p className="text-sm text-slate-600">
            Current status: <span className="font-semibold">{detail.status_display}</span>
          </p>
        )}
      </div>
    </section>
  );
};

