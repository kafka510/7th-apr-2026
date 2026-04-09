import { useEffect, useRef, useState } from 'react';

import type { TicketDetail } from '../types';

type TicketBreakdownAnalyticsProps = {
  ticketId: string;
  detail: TicketDetail | null;
  onUpdate?: () => void;
};

export const TicketBreakdownAnalytics = ({ onUpdate }: TicketBreakdownAnalyticsProps) => {
  const [expanded, setExpanded] = useState(true);
  const [saving, setSaving] = useState(false);
  const eventStartTimeRef = useRef<HTMLInputElement>(null);
  const eventEndTimeRef = useRef<HTMLInputElement>(null);
  
  // Form state - these would typically come from ticket metadata or a separate API
  const [eventStartTime, setEventStartTime] = useState('');
  const [eventEndTime, setEventEndTime] = useState('');
  const [downtimeHours, setDowntimeHours] = useState('');
  const [rootCauseCategory, setRootCauseCategory] = useState('');
  const [subCause, setSubCause] = useState('');
  const [severityLevel, setSeverityLevel] = useState('');
  const [estimatedMwhLoss, setEstimatedMwhLoss] = useState('');
  const [revenueLoss, setRevenueLoss] = useState('');
  const [materialCost, setMaterialCost] = useState('');
  const [labourCost, setLabourCost] = useState('');
  const [warrantyStatus, setWarrantyStatus] = useState('');

  // These would typically come from API/options
  const rootCauseOptions = [
    { value: '', label: 'Select' },
    { value: 'equipment_failure', label: 'Equipment Failure' },
    { value: 'human_error', label: 'Human Error' },
    { value: 'environmental', label: 'Environmental' },
    { value: 'maintenance', label: 'Maintenance Related' },
    { value: 'other', label: 'Other' },
  ];

  const severityOptions = [
    { value: '', label: 'Select' },
    { value: 'low', label: 'Low' },
    { value: 'medium', label: 'Medium' },
    { value: 'high', label: 'High' },
    { value: 'critical', label: 'Critical' },
  ];

  const warrantyStatusOptions = [
    { value: '', label: 'Select' },
    { value: 'under_warranty', label: 'Under Warranty' },
    { value: 'out_of_warranty', label: 'Out of Warranty' },
    { value: 'extended_warranty', label: 'Extended Warranty' },
    { value: 'unknown', label: 'Unknown' },
  ];

  // Sub-cause options based on root cause category
  const getSubCauseOptions = (rootCause: string) => {
    const subCauseMap: Record<string, Array<{ value: string; label: string }>> = {
      equipment_failure: [
        { value: '', label: 'Select' },
        { value: 'mechanical_failure', label: 'Mechanical Failure' },
        { value: 'electrical_failure', label: 'Electrical Failure' },
        { value: 'sensor_failure', label: 'Sensor Failure' },
        { value: 'component_wear', label: 'Component Wear' },
        { value: 'overheating', label: 'Overheating' },
        { value: 'corrosion', label: 'Corrosion' },
      ],
      human_error: [
        { value: '', label: 'Select' },
        { value: 'incorrect_operation', label: 'Incorrect Operation' },
        { value: 'improper_maintenance', label: 'Improper Maintenance' },
        { value: 'installation_error', label: 'Installation Error' },
        { value: 'configuration_error', label: 'Configuration Error' },
      ],
      environmental: [
        { value: '', label: 'Select' },
        { value: 'weather_conditions', label: 'Weather Conditions' },
        { value: 'natural_disaster', label: 'Natural Disaster' },
        { value: 'pollution', label: 'Pollution' },
        { value: 'temperature_extreme', label: 'Temperature Extreme' },
      ],
      maintenance: [
        { value: '', label: 'Select' },
        { value: 'scheduled_maintenance', label: 'Scheduled Maintenance' },
        { value: 'preventive_maintenance', label: 'Preventive Maintenance' },
        { value: 'corrective_maintenance', label: 'Corrective Maintenance' },
        { value: 'maintenance_overdue', label: 'Maintenance Overdue' },
      ],
      other: [
        { value: '', label: 'Select' },
        { value: 'unknown_cause', label: 'Unknown Cause' },
        { value: 'third_party', label: 'Third Party Issue' },
        { value: 'supply_chain', label: 'Supply Chain Issue' },
      ],
    };
    return subCauseMap[rootCause] || [{ value: '', label: 'Select Root Cause First' }];
  };

  // Calculate downtime hours automatically from Event Start Time and Event End Time
  useEffect(() => {
    if (eventStartTime && eventEndTime) {
      const start = new Date(eventStartTime);
      const end = new Date(eventEndTime);
      
      if (end > start) {
        const diffMs = end.getTime() - start.getTime();
        const diffHours = diffMs / (1000 * 60 * 60); // Convert milliseconds to hours
        setDowntimeHours(diffHours.toFixed(2));
      } else if (end < start) {
        // Invalid: end time is before start time
        setDowntimeHours('');
      }
    } else {
      // Clear downtime if either time is cleared
      if (!eventStartTime || !eventEndTime) {
        setDowntimeHours('');
      }
    }
  }, [eventStartTime, eventEndTime]);

  // Reset sub-cause when root cause changes
  useEffect(() => {
    if (!rootCauseCategory) {
      setSubCause('');
    }
  }, [rootCauseCategory]);

  const handleSave = async () => {
    setSaving(true);
    try {
      // TODO: Implement API call to save breakdown analytics
      // This would typically update ticket metadata or call a specific endpoint
      await new Promise((resolve) => setTimeout(resolve, 500)); // Simulate API call
      alert('Analytics details saved successfully');
      onUpdate?.();
    } catch {
      alert('Failed to save analytics details');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
      <div
        className="flex cursor-pointer items-center justify-between border-b border-slate-200 bg-slate-50 px-4 py-2"
        onClick={() => setExpanded(!expanded)}
      >
        <h3 className="text-sm font-semibold text-slate-900">Breakdown & Analytics Details</h3>
        <span className="text-slate-500">{expanded ? '▼' : '▶'}</span>
      </div>

      {expanded && (
        <div className="space-y-3 p-4">
          {/* Event Start Time */}
          <div>
            <label className="mb-1 block text-xs font-semibold text-slate-700">
              Event Start Time
            </label>
            <input
              ref={eventStartTimeRef}
              type="datetime-local"
              value={eventStartTime}
              onChange={(e) => {
                const newValue = e.target.value;
                setEventStartTime(newValue);
                
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
                    if (eventStartTimeRef.current) {
                      eventStartTimeRef.current.blur();
                    }
                  }, 500);
                }
              }}
              className="w-full rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-900 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
              placeholder="mm/dd/yyyy --:--"
            />
          </div>

          {/* Event End Time */}
          <div>
            <label className="mb-1 block text-xs font-semibold text-slate-700">
              Event End Time
            </label>
            <input
              ref={eventEndTimeRef}
              type="datetime-local"
              value={eventEndTime}
              onChange={(e) => {
                const newValue = e.target.value;
                setEventEndTime(newValue);
                
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
                    if (eventEndTimeRef.current) {
                      eventEndTimeRef.current.blur();
                    }
                  }, 500);
                }
              }}
              className="w-full rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-900 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
              placeholder="mm/dd/yyyy --:--"
            />
          </div>

          {/* Downtime Hours - Auto-calculated */}
          <div>
            <label className="mb-1 block text-xs font-semibold text-slate-700">
              Downtime (Hours)
            </label>
            <input
              type="number"
              step="0.01"
              value={downtimeHours}
              onChange={(e) => setDowntimeHours(e.target.value)}
              readOnly
              className="w-full rounded-lg border border-slate-300 bg-slate-50 px-3 py-1.5 text-sm text-slate-900 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
              placeholder="Auto-calculated from Event Start/End Time"
            />
            <p className="mt-1 text-xs text-slate-500">Automatically calculated from Event Start Time and Event End Time</p>
          </div>

          {/* Root Cause Category */}
          <div>
            <label className="mb-1 block text-xs font-semibold text-slate-700">
              Root Cause Category
            </label>
            <select
              value={rootCauseCategory}
              onChange={(e) => setRootCauseCategory(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-900 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
            >
              {rootCauseOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          {/* Sub Cause */}
          <div>
            <label className="mb-1 block text-xs font-semibold text-slate-700">
              Sub Cause
            </label>
            <select
              value={subCause}
              onChange={(e) => setSubCause(e.target.value)}
              disabled={!rootCauseCategory}
              className="w-full rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-900 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500 disabled:bg-slate-100 disabled:text-slate-500"
            >
              {getSubCauseOptions(rootCauseCategory).map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          {/* Severity Level */}
          <div>
            <label className="mb-1 block text-xs font-semibold text-slate-700">
              Severity Level
            </label>
            <select
              value={severityLevel}
              onChange={(e) => setSeverityLevel(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-900 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
            >
              {severityOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          {/* Calculated MWh Loss */}
          <div>
            <label className="mb-1 block text-xs font-semibold text-slate-700">
              Calculated MWh Loss
            </label>
            <input
              type="number"
              step="0.01"
              value={estimatedMwhLoss}
              onChange={(e) => setEstimatedMwhLoss(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-900 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
              placeholder="0.00"
            />
          </div>

          {/* Revenue Loss */}
          <div>
            <label className="mb-1 block text-xs font-semibold text-slate-700">
              Revenue Loss ($)
            </label>
            <input
              type="number"
              step="0.01"
              value={revenueLoss}
              onChange={(e) => setRevenueLoss(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-900 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
              placeholder="0.00"
            />
          </div>

          {/* Material Cost */}
          <div>
            <label className="mb-1 block text-xs font-semibold text-slate-700">
              Material Cost ($)
            </label>
            <input
              type="number"
              step="0.01"
              value={materialCost}
              onChange={(e) => setMaterialCost(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-900 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
              placeholder="0.00"
            />
          </div>

          {/* Labour Cost */}
          <div>
            <label className="mb-1 block text-xs font-semibold text-slate-700">
              Labour Cost ($)
            </label>
            <input
              type="number"
              step="0.01"
              value={labourCost}
              onChange={(e) => setLabourCost(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-900 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
              placeholder="0.00"
            />
          </div>

          {/* Warranty Status */}
          <div>
            <label className="mb-1 block text-xs font-semibold text-slate-700">
              Warranty Status
            </label>
            <select
              value={warrantyStatus}
              onChange={(e) => setWarrantyStatus(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-900 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
            >
              {warrantyStatusOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          {/* Save Button */}
          <div className="pt-2">
            <button
              type="button"
              onClick={handleSave}
              disabled={saving}
              className="w-full rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {saving ? 'Saving...' : 'Save Analytics Details'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

