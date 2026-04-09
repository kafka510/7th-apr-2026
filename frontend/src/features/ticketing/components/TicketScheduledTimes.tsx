import { useRef, useState } from 'react';

import type { TicketDetail } from '../types';

type TicketScheduledTimesProps = {
  ticketId: string;
  detail: TicketDetail | null;
  onUpdate?: () => void;
};

export const TicketScheduledTimes = ({ onUpdate }: TicketScheduledTimesProps) => {
  const [expanded, setExpanded] = useState(true);
  const [saving, setSaving] = useState(false);
  const [scheduledStartTime, setScheduledStartTime] = useState('');
  const [scheduledEndTime, setScheduledEndTime] = useState('');
  const scheduledStartTimeRef = useRef<HTMLInputElement>(null);
  const scheduledEndTimeRef = useRef<HTMLInputElement>(null);

  const handleSave = async () => {
    setSaving(true);
    try {
      // TODO: Implement API call to save scheduled times
      // This would typically update ticket metadata or call a specific endpoint
      await new Promise((resolve) => setTimeout(resolve, 500)); // Simulate API call
      alert('Scheduled times saved successfully');
      onUpdate?.();
    } catch {
      alert('Failed to save scheduled times');
    } finally {
      setSaving(false);
    }
  };

  const handleClear = () => {
    setScheduledStartTime('');
    setScheduledEndTime('');
  };

  return (
    <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
      <div
        className="flex cursor-pointer items-center justify-between border-b border-slate-200 bg-slate-50 px-4 py-2"
        onClick={() => setExpanded(!expanded)}
      >
        <h3 className="text-sm font-semibold text-slate-900">Scheduled Times</h3>
        <span className="text-slate-500">{expanded ? '▼' : '▶'}</span>
      </div>

      {expanded && (
        <div className="space-y-3 p-4">
          {/* Scheduled Start Time */}
          <div>
            <label className="mb-1 block text-xs font-semibold text-slate-700">
              Scheduled Start Time
            </label>
            <input
              ref={scheduledStartTimeRef}
              type="datetime-local"
              value={scheduledStartTime}
              onChange={(e) => {
                const newValue = e.target.value;
                setScheduledStartTime(newValue);
                
                // Check if datetime value is complete (has both date and time)
                // Format: "YYYY-MM-DDTHH:mm" - must have 'T' separator and complete time (HH:mm)
                const parts = newValue.split('T');
                const hasDate = parts[0] && parts[0].length === 10; // YYYY-MM-DD format
                const timePart = parts[1] || '';
                const hasCompleteTime = timePart.includes(':') && timePart.split(':').length === 2;
                const isComplete = hasDate && hasCompleteTime;
                
                // Only close calendar if the datetime selection is complete
                // Use a delay to allow user to finish selecting AM/PM if using 12-hour format picker
                if (isComplete) {
                  setTimeout(() => {
                    if (scheduledStartTimeRef.current) {
                      scheduledStartTimeRef.current.blur();
                    }
                  }, 500);
                }
              }}
              onBlur={(e) => {
                // Ensure input loses focus when user clicks outside
                e.target.blur();
              }}
              className="w-full rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-900 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
              placeholder="Select start date and time"
            />
          </div>

          {/* Scheduled End Time */}
          <div>
            <label className="mb-1 block text-xs font-semibold text-slate-700">
              Scheduled End Time
            </label>
            <input
              ref={scheduledEndTimeRef}
              type="datetime-local"
              value={scheduledEndTime}
              onChange={(e) => {
                const newValue = e.target.value;
                setScheduledEndTime(newValue);
                
                // Check if datetime value is complete (has both date and time)
                // Format: "YYYY-MM-DDTHH:mm" - must have 'T' separator and complete time (HH:mm)
                const parts = newValue.split('T');
                const hasDate = parts[0] && parts[0].length === 10; // YYYY-MM-DD format
                const timePart = parts[1] || '';
                const hasCompleteTime = timePart.includes(':') && timePart.split(':').length === 2;
                const isComplete = hasDate && hasCompleteTime;
                
                // Only close calendar if the datetime selection is complete
                // Use a delay to allow user to finish selecting AM/PM if using 12-hour format picker
                if (isComplete) {
                  setTimeout(() => {
                    if (scheduledEndTimeRef.current) {
                      scheduledEndTimeRef.current.blur();
                    }
                  }, 500);
                }
              }}
              onBlur={(e) => {
                // Ensure input loses focus when user clicks outside
                e.target.blur();
              }}
              className="w-full rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-900 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
              placeholder="Select end date and time"
            />
          </div>

          {/* Action Buttons */}
          <div className="flex gap-2 pt-2">
            <button
              type="button"
              onClick={handleSave}
              disabled={saving}
              className="flex-1 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {saving ? 'Saving...' : 'Save Scheduled Times'}
            </button>
            <button
              type="button"
              onClick={handleClear}
              disabled={saving || (!scheduledStartTime && !scheduledEndTime)}
              className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-red-600 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              × Clear
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

