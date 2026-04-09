/**
 * Date Range Picker Component
 */
 
interface DateRangePickerProps {
  startDate: string | null;
  endDate: string | null;
  onStartDateChange: (date: string) => void;
  onEndDateChange: (date: string) => void;
  disabled?: boolean;
}

export function DateRangePicker({
  startDate,
  endDate,
  onStartDateChange,
  onEndDateChange,
  disabled = false,
}: DateRangePickerProps) {
  // Set default dates (today and 7 days ago)
  const today = new Date().toISOString().split('T')[0];
  const weekAgo = new Date();
  weekAgo.setDate(weekAgo.getDate() - 7);
  const defaultStartDate = weekAgo.toISOString().split('T')[0];

  return (
    <div className="mb-4">
      <label className="mb-2 block text-sm font-bold text-slate-900">Date Range</label>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <input
            type="date"
            className="w-full rounded-lg border-2 border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-900 focus:border-purple-500 focus:outline-none focus:ring-2 focus:ring-purple-200"
            value={startDate || defaultStartDate}
            onChange={(e) => onStartDateChange(e.target.value)}
            disabled={disabled}
          />
          <small className="mt-1 block font-medium text-slate-700">Start Date</small>
        </div>
        <div>
          <input
            type="date"
            className="w-full rounded-lg border-2 border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-900 focus:border-purple-500 focus:outline-none focus:ring-2 focus:ring-purple-200"
            value={endDate || today}
            onChange={(e) => onEndDateChange(e.target.value)}
            disabled={disabled}
          />
          <small className="mt-1 block font-medium text-slate-700">End Date</small>
        </div>
      </div>
    </div>
  );
}

