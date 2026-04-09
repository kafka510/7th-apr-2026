import { useState, useEffect } from 'react';

import { updateTicketWatchers, fetchTicketFormOptions } from '../api';
import type { TicketDetail, TicketFormOptions } from '../types';

type TicketWatchersProps = {
  ticketId: string;
  detail: TicketDetail | null;
  onWatchersUpdated?: () => void;
};

export const TicketWatchers = ({ ticketId, detail, onWatchersUpdated }: TicketWatchersProps) => {
  const [formOptions, setFormOptions] = useState<TicketFormOptions | null>(null);
  const [selectedWatchers, setSelectedWatchers] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const canManageWatchers = detail?.permissions?.canManageWatchers ?? false;

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
    if (detail?.watchers) {
      setSelectedWatchers(detail.watchers.filter((w) => w !== null).map((w) => w!.id.toString()));
    } else {
      setSelectedWatchers([]);
    }
  }, [detail?.watchers]);

  const canRemoveWatchers = detail?.permissions?.canRemoveWatchers ?? false;
  
  const handleWatcherToggle = (userId: string) => {
    // If user is trying to remove a watcher, check permission
    if (selectedWatchers.includes(userId) && !canRemoveWatchers) {
      return; // Don't allow removal without permission
    }
    setSelectedWatchers((prev) => (prev.includes(userId) ? prev.filter((id) => id !== userId) : [...prev, userId]));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canManageWatchers) {
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      await updateTicketWatchers(ticketId, selectedWatchers);
      if (onWatchersUpdated) {
        onWatchersUpdated();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update watchers');
    } finally {
      setSubmitting(false);
    }
  };

  const currentWatchers = detail?.watchers ?? [];

  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
      <h2 className="text-lg font-semibold text-slate-900">Watchers</h2>
      {loading ? (
        <p className="mt-4 text-sm text-slate-500">Loading watchers…</p>
      ) : currentWatchers.length === 0 && !canManageWatchers ? (
        <p className="mt-4 text-sm text-slate-500">No watchers added yet.</p>
      ) : (
        <>
          {currentWatchers.length > 0 && (
            <ul className="mt-4 space-y-2 text-sm text-slate-700">
              {currentWatchers.map((user) =>
                user ? (
                  <li key={`watcher-${user.id}`} className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2">
                    {user.name}
                  </li>
                ) : null,
              )}
            </ul>
          )}

          {canManageWatchers && (
            <form onSubmit={handleSubmit} className="mt-6 space-y-4 border-t border-slate-200 pt-6">
              {error && (
                <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
                  {error}
                </div>
              )}
              <div>
                <label className="mb-2 block text-sm font-semibold text-slate-700">Select Watchers</label>
                <div className="max-h-48 space-y-2 overflow-y-auto rounded-xl border border-slate-300 bg-white p-3">
                  {formOptions?.users.map((user) => {
                    const isChecked = selectedWatchers.includes(user.value);
                    const isCurrentWatcher = currentWatchers.some((w) => w?.id.toString() === user.value);
                    const canToggle = !isChecked || canRemoveWatchers;
                    
                    return (
                      <label key={user.value} className={`flex items-center gap-2 rounded p-2 text-sm text-slate-700 ${canToggle ? 'cursor-pointer hover:bg-slate-50' : 'cursor-not-allowed opacity-50'}`}>
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={() => handleWatcherToggle(user.value)}
                          disabled={submitting || !canToggle}
                          className="size-4 rounded border-slate-300 text-sky-600 focus:ring-2 focus:ring-sky-200 disabled:cursor-not-allowed"
                        />
                        <span>{user.label}</span>
                        {isCurrentWatcher && !canRemoveWatchers && (
                          <span className="ml-auto text-xs text-slate-400">(Cannot remove)</span>
                        )}
                      </label>
                    );
                  })}
                </div>
              </div>
              <button
                type="submit"
                disabled={submitting}
                className="w-full rounded-xl bg-sky-600 px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-sky-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {submitting ? 'Updating...' : 'Update Watchers'}
              </button>
            </form>
          )}
        </>
      )}
    </div>
  );
};


