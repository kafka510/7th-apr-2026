import { useEffect, useMemo, useRef, useState } from 'react';
import { useTheme } from '../../../contexts/ThemeContext';

type DateRangePickerProps = {
  startDate: string | null;
  endDate: string | null;
  onStartDateChange: (date: string | null) => void;
  onEndDateChange: (date: string | null) => void;
  disabled?: boolean;
  maxDate?: string; // YYYY-MM-DD
};

const formatDateString = (date: Date): string => {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
};

const parseDate = (dateStr: string) => {
  const [y, m, d] = dateStr.split('-').map(Number);
  return new Date(y, m - 1, d);
};

export const DateRangePicker = ({
  startDate,
  endDate,
  onStartDateChange,
  onEndDateChange,
  disabled = false,
  maxDate,
}: DateRangePickerProps) => {
  const { theme } = useTheme();
  const containerRef = useRef<HTMLDivElement>(null);

  const [open, setOpen] = useState(false);
  const [selectingStart, setSelectingStart] = useState(true);
  const [hoverDate, setHoverDate] = useState<string | null>(null);

  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const maxDateObj = maxDate ? parseDate(maxDate) : today;

  const [currentMonth, setCurrentMonth] = useState(
    new Date(today.getFullYear(), today.getMonth(), 1)
  );

  const nextMonth = useMemo(
    () => new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1, 1),
    [currentMonth]
  );

  // Sync selectingStart state with actual dates
  useEffect(() => {
    if (startDate && !endDate) {
      // If we have start date but no end date, we should be selecting end date
      setSelectingStart(false);
    } else if (!startDate) {
      // If no start date, we should be selecting start date
      setSelectingStart(true);
    }
  }, [startDate, endDate]);

  useEffect(() => {
    const close = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    const esc = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false);

    document.addEventListener('mousedown', close);
    document.addEventListener('keydown', esc);
    return () => {
      document.removeEventListener('mousedown', close);
      document.removeEventListener('keydown', esc);
    };
  }, []);

  const buildMonth = (month: Date) => {
    const y = month.getFullYear();
    const m = month.getMonth();
    const first = new Date(y, m, 1);
    const last = new Date(y, m + 1, 0);

    const days: (Date | null)[] = [];
    for (let i = 0; i < first.getDay(); i++) days.push(null);
    for (let d = 1; d <= last.getDate(); d++) {
      days.push(new Date(y, m, d));
    }
    return days;
  };

  const isInRange = (d: Date) => {
    if (!startDate || !endDate) return false;
    const s = startDate;
    const e = endDate;
    const c = formatDateString(d);
    return c > s && c < e;
  };

  const isPreviewRange = (d: Date) => {
    if (!startDate || selectingStart || !hoverDate) return false;
    const c = formatDateString(d);
    return c > startDate && c < hoverDate;
  };

  // Unlimited month navigation (past and future)
  const goPrevMonth = () => {
    setCurrentMonth((prev) => new Date(prev.getFullYear(), prev.getMonth() - 1, 1));
  };

  const goNextMonth = () => {
    setCurrentMonth((prev) => new Date(prev.getFullYear(), prev.getMonth() + 1, 1));
  };

  const handleDateClick = (date: Date) => {
    if (disabled || date > maxDateObj) return;
    const value = formatDateString(date);

    if (selectingStart || !startDate) {
      // Selecting start date
      onStartDateChange(value);
      onEndDateChange(null);
      setSelectingStart(false);
      // Calendar stays open for end date selection
      return;
    }

    // Selecting end date
    if (value < startDate) {
      // If clicked date is before start, swap them
      onStartDateChange(value);
      onEndDateChange(startDate);
      setSelectingStart(false);
      // After swapping, both dates are set, so close the calendar
      setOpen(false);
    } else if (value === startDate) {
      // If same date is clicked twice, set both start and end to that date
      onEndDateChange(value);
      // Close calendar since both dates are now set (same date)
      setOpen(false);
    } else {
      // Normal end date selection
      onEndDateChange(value);
      // Close calendar since both dates are now set
      setOpen(false);
    }
  };

  const applyPreset = (type: 'today' | 'last7' | 'month') => {
    const end = new Date();
    let start = new Date();

    if (type === 'last7') start.setDate(end.getDate() - 6);
    if (type === 'month') start = new Date(end.getFullYear(), end.getMonth(), 1);

    onStartDateChange(formatDateString(start));
    onEndDateChange(formatDateString(end));
    setSelectingStart(true);
    setOpen(false);
  };

  const renderMonth = (month: Date) => {
    const days = buildMonth(month);

    return (
      <div>
        <div className="mb-2 text-center text-sm font-semibold">
          {month.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}
        </div>

        <div className="grid grid-cols-7 gap-1 text-xs">
          {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((d) => (
            <div key={d} className="text-center opacity-60">{d}</div>
          ))}

          {days.map((d, i) =>
            d ? (
              <button
                key={i}
                onClick={() => handleDateClick(d)}
                onMouseEnter={() => !selectingStart && setHoverDate(formatDateString(d))}
                onMouseLeave={() => setHoverDate(null)}
                disabled={d > maxDateObj}
                className="aspect-square rounded transition"
                style={{
                  background:
                    formatDateString(d) === startDate ||
                    formatDateString(d) === endDate
                      ? 'rgba(59,130,246,.35)'
                      : isInRange(d)
                      ? 'rgba(59,130,246,.15)'
                      : isPreviewRange(d)
                      ? 'rgba(59,130,246,.1)'
                      : 'transparent',
                  fontWeight:
                    formatDateString(d) === startDate ||
                    formatDateString(d) === endDate
                      ? 'bold'
                      : 'normal',
                  opacity: d > maxDateObj ? 0.4 : 1,
                }}
              >
                {d.getDate()}
              </button>
            ) : (
              <div key={i} />
            )
          )}
        </div>
      </div>
    );
  };

  const displayText =
    startDate && endDate
      ? `${parseDate(startDate).toDateString()} – ${parseDate(endDate).toDateString()}`
      : startDate
      ? `${parseDate(startDate).toDateString()} – …`
      : 'Select Date Range';

  const inputBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.8)' : '#ffffff';
  const inputBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : 'rgba(203, 213, 225, 0.7)';
  const inputText = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';
  const calendarBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.95)' : '#ffffff';
  const calendarBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(203, 213, 225, 0.8)';
  const buttonBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.6)' : 'rgba(241, 245, 249, 0.8)';
  const buttonHover = theme === 'dark' ? 'rgba(30, 41, 59, 0.9)' : 'rgba(241, 245, 249, 1)';

  return (
    <div ref={containerRef} className="relative">
      <div
        onClick={() => !disabled && setOpen((o) => !o)}
        className="cursor-pointer rounded-lg border px-2 py-1 text-xs font-medium shadow-inner transition-colors focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500/30 disabled:cursor-not-allowed disabled:opacity-50"
        style={{
          borderColor: inputBorder,
          backgroundColor: inputBg,
          color: inputText,
          boxShadow: theme === 'dark' ? 'inset 0 2px 4px rgba(0, 0, 0, 0.4)' : 'inset 0 2px 4px rgba(0, 0, 0, 0.1)',
        }}
      >
        <div className="flex items-center justify-between">
          <span className="flex items-center gap-1">
            <span>🗓️</span>
            <span>{displayText}</span>
          </span>
          <span className="text-xs opacity-60">▼</span>
        </div>
      </div>

      {open && (
        <div
          className="absolute z-50 mt-2 rounded-lg border p-3 shadow-xl"
          style={{
            backgroundColor: calendarBg,
            borderColor: calendarBorder,
            minWidth: '560px',
          }}
        >
          {/* Navigation Header - unlimited months */}
          <div className="mb-3 flex items-center justify-between">
            <button
              type="button"
              onClick={goPrevMonth}
              className="rounded px-2 py-1 text-xs hover:bg-slate-200/60 dark:hover:bg-slate-700/60"
              style={{ color: inputText }}
            >
              ‹
            </button>
            <span className="text-sm font-semibold" style={{ color: inputText }}>
              {currentMonth.getFullYear()}
            </span>
            <button
              type="button"
              onClick={goNextMonth}
              className="rounded px-2 py-1 text-xs hover:bg-slate-200/60 dark:hover:bg-slate-700/60"
              style={{ color: inputText }}
            >
              ›
            </button>
          </div>

          <div className="mb-3 flex gap-2">
            <button
              onClick={() => applyPreset('today')}
              className="rounded px-3 py-1 text-xs transition-colors"
              style={{
                backgroundColor: buttonBg,
                color: inputText,
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = buttonHover;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = buttonBg;
              }}
            >
              Today
            </button>
            <button
              onClick={() => applyPreset('last7')}
              className="rounded px-3 py-1 text-xs transition-colors"
              style={{
                backgroundColor: buttonBg,
                color: inputText,
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = buttonHover;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = buttonBg;
              }}
            >
              Last 7 Days
            </button>
            <button
              onClick={() => applyPreset('month')}
              className="rounded px-3 py-1 text-xs transition-colors"
              style={{
                backgroundColor: buttonBg,
                color: inputText,
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = buttonHover;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = buttonBg;
              }}
            >
              This Month
            </button>
          </div>

          <div className="grid grid-cols-2 gap-4">
            {renderMonth(currentMonth)}
            {renderMonth(nextMonth)}
          </div>

          <div className="mt-3 flex items-center justify-between border-t pt-2" style={{ borderColor: calendarBorder }}>
            <button
              onClick={() => {
                onStartDateChange(null);
                onEndDateChange(null);
                setSelectingStart(true);
              }}
              className="text-xs transition-colors hover:opacity-80"
              style={{ color: theme === 'dark' ? '#fca5a5' : '#dc2626' }}
            >
              Clear
            </button>
            <div className="text-xs" style={{ color: theme === 'dark' ? 'rgba(148, 163, 184, 0.7)' : '#64748b' }}>
              {selectingStart ? 'Select start date' : 'Select end date'}
            </div>
            <button
              onClick={() => setOpen(false)}
              className="text-xs font-medium transition-colors hover:opacity-80"
              style={{ color: theme === 'dark' ? '#60a5fa' : '#2563eb' }}
            >
              Done
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
