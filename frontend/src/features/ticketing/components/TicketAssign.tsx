import { useState, useEffect } from 'react';

import { assignTicket, fetchTicketFormOptions } from '../api';
import type { TicketDetail, TicketFormOptions } from '../types';

type TicketAssignProps = {
  ticketId: string;
  detail: TicketDetail | null;
  onAssigned?: () => void;
};

export const TicketAssign = ({ ticketId, detail, onAssigned }: TicketAssignProps) => {
  const [formOptions, setFormOptions] = useState<TicketFormOptions | null>(null);
  const [assignedTo, setAssignedTo] = useState<string>('');
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const canAssign = detail?.permissions?.canAssign ?? false;

  useEffect(() => {
    const loadOptions = async () => {
      try {
        const options = await fetchTicketFormOptions();
        setFormOptions(options);
      } catch (err) {
        console.error('Failed to load form options', err);
      } finally {
        setLoading(false);
      }
    };
    loadOptions();
  }, []);

  useEffect(() => {
    if (detail?.assigned_to) {
      setAssignedTo(detail.assigned_to.id.toString());
    } else {
      setAssignedTo('');
    }
  }, [detail?.assigned_to]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canAssign) {
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      await assignTicket(ticketId, assignedTo || null, notes);
      setNotes('');
      if (onAssigned) {
        onAssigned();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to assign ticket');
    } finally {
      setSubmitting(false);
    }
  };

  if (!canAssign) {
    return null;
  }

  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
      <h2 className="text-lg font-semibold text-slate-900">Assign Ticket</h2>
      <form onSubmit={handleSubmit} className="mt-4 space-y-4">
        {error && (
          <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
            {error}
          </div>
        )}
        <div>
          <label htmlFor="assigned_to" className="block text-sm font-semibold text-slate-700">
            Assign To
          </label>
          <select
            id="assigned_to"
            value={assignedTo}
            onChange={(e) => setAssignedTo(e.target.value)}
            disabled={submitting || loading}
            className="mt-1 w-full rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm text-slate-900 transition focus:border-sky-400 focus:outline-none focus:ring-2 focus:ring-sky-200 disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-500"
          >
            {detail?.assigned_to && !detail?.permissions?.canRemoveAssignee ? null : (
              <option value="">Unassigned</option>
            )}
            {formOptions?.users.map((user) => (
              <option key={user.value} value={user.value}>
                {user.label}
              </option>
            ))}
          </select>
          {detail?.assigned_to && !detail?.permissions?.canRemoveAssignee && (
            <p className="mt-1 text-xs text-slate-500">
              Cannot unassign. You need the &quot;remove_assignee&quot; capability to unassign tickets.
            </p>
          )}
        </div>
        <div>
          <label htmlFor="assign_notes" className="block text-sm font-semibold text-slate-700">
            Notes (Optional)
          </label>
          <textarea
            id="assign_notes"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={3}
            disabled={submitting}
            className="mt-1 w-full rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm text-slate-900 transition focus:border-sky-400 focus:outline-none focus:ring-2 focus:ring-sky-200 disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-500"
            placeholder="Optional notes about the assignment..."
          />
        </div>
        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-xl bg-sky-600 px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-sky-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {submitting ? 'Assigning...' : 'Assign Ticket'}
        </button>
      </form>
    </div>
  );
};


