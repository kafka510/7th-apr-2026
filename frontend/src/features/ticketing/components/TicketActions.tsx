import { useState, useEffect } from 'react';

import { assignTicket, changeTicketStatus, fetchTicketFormOptions, updateTicketWatchers } from '../api';
import type { TicketDetail, TicketFormOptions } from '../types';
import { FormMultiSelect } from './FormMultiSelect';

type TicketActionsProps = {
  ticketId: string;
  detail: TicketDetail | null;
  onUpdate?: () => void;
};

export const TicketActions = ({ ticketId, detail, onUpdate }: TicketActionsProps) => {
  const [expanded, setExpanded] = useState(true);
  const [formOptions, setFormOptions] = useState<TicketFormOptions | null>(null);
  
  // Watchers state
  const [selectedWatchers, setSelectedWatchers] = useState<string[]>([]);
  const [watchersSaving, setWatchersSaving] = useState(false);
  
  // Status state
  const [status, setStatus] = useState('');
  const [statusNotes, setStatusNotes] = useState('');
  const [statusSaving, setStatusSaving] = useState(false);
  
  // Assign state
  const [assignedTo, setAssignedTo] = useState<string>('');
  const [assignNotes, setAssignNotes] = useState('');
  const [assignSaving, setAssignSaving] = useState(false);
  
  // Close ticket state
  const [closeNotes, setCloseNotes] = useState('');
  const [closing, setClosing] = useState(false);

  const canManageWatchers = detail?.permissions?.canManageWatchers ?? false;
  const canAssign = detail?.permissions?.canAssign ?? false;
  const canClose = detail?.status !== 'closed' && detail?.status !== 'cancelled';

  useEffect(() => {
    const loadOptions = async () => {
      try {
        const options = await fetchTicketFormOptions();
        setFormOptions(options);
      } catch (err) {
        console.error('Failed to load form options', err);
      }
    };
    loadOptions();
  }, []);

  useEffect(() => {
    if (detail?.watchers) {
      setSelectedWatchers(detail.watchers.filter((w) => w !== null).map((w) => w!.id.toString()));
    }
    if (detail?.status) {
      setStatus(detail.status);
    }
    if (detail?.assigned_to) {
      setAssignedTo(detail.assigned_to.id.toString());
    }
  }, [detail]);

  const handleUpdateWatchers = async () => {
    if (!canManageWatchers) return;
    setWatchersSaving(true);
    try {
      await updateTicketWatchers(ticketId, selectedWatchers);
      alert('Watchers updated successfully');
      onUpdate?.();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to update watchers');
    } finally {
      setWatchersSaving(false);
    }
  };

  const handleChangeStatus = async () => {
    if (!status) return;
    setStatusSaving(true);
    try {
      await changeTicketStatus(ticketId, status, statusNotes);
      setStatusNotes('');
      alert('Status updated successfully');
      onUpdate?.();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to update status');
    } finally {
      setStatusSaving(false);
    }
  };

  const handleAssign = async () => {
    if (!canAssign) return;
    setAssignSaving(true);
    try {
      await assignTicket(ticketId, assignedTo || null, assignNotes);
      setAssignNotes('');
      alert('Ticket assigned successfully');
      onUpdate?.();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to assign ticket');
    } finally {
      setAssignSaving(false);
    }
  };

  const handleCloseTicket = async () => {
    if (!canClose) return;
    if (!window.confirm('Are you sure you want to close this ticket?')) {
      return;
    }
    setClosing(true);
    try {
      await changeTicketStatus(ticketId, 'closed', closeNotes);
      setCloseNotes('');
      alert('Ticket closed successfully');
      onUpdate?.();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to close ticket');
    } finally {
      setClosing(false);
    }
  };

  const statusOptions = [
    { value: 'raised', label: 'Raised' },
    { value: 'in_progress', label: 'In Progress' },
    { value: 'submitted', label: 'Submitted' },
    { value: 'waiting_for_approval', label: 'Waiting for Approval' },
    { value: 'closed', label: 'Closed' },
    { value: 'reopened', label: 'Reopened' },
    { value: 'cancelled', label: 'Cancelled' },
  ];

  return (
    <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
      <div
        className="flex cursor-pointer items-center justify-between border-b border-slate-200 bg-slate-50 px-4 py-2"
        onClick={() => setExpanded(!expanded)}
      >
        <h3 className="text-sm font-semibold text-slate-900">Actions</h3>
        <span className="text-slate-500">{expanded ? '▼' : '▶'}</span>
      </div>

      {expanded && (
        <div className="space-y-4 p-4">
          {/* Update Watchers */}
          {canManageWatchers && (
            <div className="space-y-2 border-b border-slate-100 pb-4">
              <label className="block text-xs font-semibold text-slate-700">Update Watchers</label>
              {formOptions?.users && (
                <FormMultiSelect
                  label="Watchers"
                  options={formOptions.users}
                  selected={selectedWatchers}
                  onChange={setSelectedWatchers}
                  placeholder="Select watchers"
                  singleSelect={false}
                />
              )}
              <button
                type="button"
                onClick={handleUpdateWatchers}
                disabled={watchersSaving}
                className="w-full rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {watchersSaving ? 'Saving...' : 'Save Watchers'}
              </button>
            </div>
          )}

          {/* Change Status */}
          <div className="space-y-2 border-b border-slate-100 pb-4">
            <label className="block text-xs font-semibold text-slate-700">Change Status</label>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-900 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
            >
              {statusOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            <textarea
              value={statusNotes}
              onChange={(e) => setStatusNotes(e.target.value)}
              placeholder="Optional notes"
              rows={2}
              className="w-full rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-900 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
            />
            <button
              type="button"
              onClick={handleChangeStatus}
              disabled={statusSaving || !status}
              className="w-full rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {statusSaving ? 'Updating...' : 'Update'}
            </button>
          </div>

          {/* Assign To */}
          {canAssign && (
            <div className="space-y-2 border-b border-slate-100 pb-4">
              <label className="block text-xs font-semibold text-slate-700">Assign To</label>
              {formOptions?.users && (
                <FormMultiSelect
                  label="Assign To"
                  options={formOptions.users}
                  selected={assignedTo ? [assignedTo] : []}
                  onChange={(values) => setAssignedTo(values[0] || '')}
                  placeholder="Select user"
                  singleSelect={true}
                />
              )}
              <textarea
                value={assignNotes}
                onChange={(e) => setAssignNotes(e.target.value)}
                placeholder="Optional notes"
                rows={2}
                className="w-full rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-900 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
              />
              <button
                type="button"
                onClick={handleAssign}
                disabled={assignSaving}
                className="w-full rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {assignSaving ? 'Assigning...' : '+ Assign'}
              </button>
            </div>
          )}

          {/* Close Ticket */}
          {canClose && (
            <div className="space-y-2">
              <label className="block text-xs font-semibold text-slate-700">Close Ticket</label>
              <textarea
                value={closeNotes}
                onChange={(e) => setCloseNotes(e.target.value)}
                placeholder="Resolution notes"
                rows={3}
                className="w-full rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-900 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
              />
              <button
                type="button"
                onClick={handleCloseTicket}
                disabled={closing}
                className="w-full rounded-lg bg-green-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-green-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {closing ? 'Closing...' : '✓ Close Ticket'}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

