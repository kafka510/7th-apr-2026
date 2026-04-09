import { useState, useEffect, useMemo } from 'react';
import { useTheme } from '../../../contexts/ThemeContext';
import { CompactMultiSelectDropdown } from '../../yield/components/CompactMultiSelectDropdown';
import { MonthPicker } from '../../yield/components/MonthPicker';
import type { TicketDashboardFilters, TicketFilterState } from '../types';

type TicketFiltersProps = {
  state: TicketFilterState;
  options: TicketDashboardFilters | null;
  disabled?: boolean;
  onChange: (changes: Partial<TicketFilterState>) => void;
  onReset: () => void;
  onApply?: () => void;
};


export const TicketFilters = ({
  state,
  options,
  disabled = false,
  onChange,
  onReset,
  onApply,
}: TicketFiltersProps) => {
  const { theme } = useTheme();
  
  const containerBg = theme === 'dark'
    ? 'linear-gradient(to bottom right, rgba(15, 23, 42, 0.9), rgba(30, 41, 59, 0.6), rgba(15, 23, 42, 0.9))'
    : 'linear-gradient(to bottom right, rgba(255, 255, 255, 0.95), rgba(248, 250, 252, 0.9), rgba(255, 255, 255, 0.95))';
  const containerBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(203, 213, 225, 0.8)';
  const containerShadow = theme === 'dark' 
    ? '0 20px 25px -5px rgba(0, 0, 0, 0.4)' 
    : '0 10px 15px -3px rgba(0, 0, 0, 0.1)';
  const applyButtonBg = theme === 'dark' ? 'rgba(59, 130, 246, 0.8)' : '#0072ce';
  const applyButtonBorder = theme === 'dark' ? 'rgba(59, 130, 246, 0.5)' : 'rgba(0, 114, 206, 0.7)';
  const applyButtonHoverBg = theme === 'dark' ? 'rgba(37, 99, 235, 0.9)' : '#0056a3';
  const resetButtonBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.8)' : '#ffffff';
  const resetButtonBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : 'rgba(203, 213, 225, 0.8)';
  const resetButtonText = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';
  const resetButtonHoverBorder = theme === 'dark' ? 'rgba(248, 113, 113, 0.5)' : '#f87171';
  const resetButtonHoverText = theme === 'dark' ? '#fca5a5' : '#dc2626';
  const skeletonBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.5)' : 'rgba(241, 245, 249, 0.8)';
  const skeletonBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(203, 213, 225, 0.8)';
  
  // Month picker state
  const [selectedMonth, setSelectedMonth] = useState<string | null>(null);
  const [selectedYear, setSelectedYear] = useState<string | null>(null);
  const [selectedRange, setSelectedRange] = useState<{ start: string; end: string } | null>(null);
  
  // Generate available months from current date backwards
  const availableMonths = useMemo(() => {
    const months: string[] = [];
    const now = new Date();
    for (let i = 0; i < 36; i++) { // Last 3 years
      const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
      const ym = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
      months.push(ym);
    }
    return months;
  }, []);
  
  // Convert month/year/range selections to dateFrom/dateTo
  useEffect(() => {
    if (selectedRange) {
      const [startYear, startMonth] = selectedRange.start.split('-');
      const [endYear, endMonth] = selectedRange.end.split('-');
      const startDate = `${startYear}-${startMonth}-01`;
      const endDate = new Date(parseInt(endYear), parseInt(endMonth), 0).toISOString().split('T')[0];
      onChange({ dateFrom: startDate, dateTo: endDate });
    } else if (selectedMonth) {
      const [year, month] = selectedMonth.split('-');
      const startDate = `${year}-${month}-01`;
      const endDate = new Date(parseInt(year), parseInt(month), 0).toISOString().split('T')[0];
      onChange({ dateFrom: startDate, dateTo: endDate });
    } else if (selectedYear) {
      const startDate = `${selectedYear}-01-01`;
      const endDate = `${selectedYear}-12-31`;
      onChange({ dateFrom: startDate, dateTo: endDate });
    } else if (selectedMonth === null && selectedYear === null && selectedRange === null && (state.dateFrom || state.dateTo)) {
      // Clear dates when month picker is cleared
      onChange({ dateFrom: undefined, dateTo: undefined });
    }
  }, [selectedMonth, selectedYear, selectedRange]);

  const getArrayLength = (value: string | string[] | undefined): number => {
    if (!value) return 0;
    return Array.isArray(value) ? value.length : 1;
  };

  const activeCount =
    getArrayLength(state.status) +
    getArrayLength(state.priority) +
    getArrayLength(state.category) +
    getArrayLength(state.site) +
    Number(Boolean(state.dateFrom || state.dateTo));

  const normalizeToArray = (value: string | string[] | undefined): string[] => {
    if (!value) return [];
    return Array.isArray(value) ? value : [value];
  };

  return (
    <section 
      className="relative rounded-xl border p-3 shadow-xl"
      style={{
        borderColor: containerBorder,
        background: containerBg,
        boxShadow: containerShadow,
      }}
    >
      {theme === 'dark' ? (
        <div className="pointer-events-none absolute inset-0 rounded-xl bg-[radial-gradient(circle_at_top,_rgba(56,189,248,0.12),_transparent_55%),radial-gradient(circle_at_bottom,_rgba(167,139,250,0.12),_transparent_60%)]" />
      ) : (
        <div className="pointer-events-none absolute inset-0 rounded-xl bg-[radial-gradient(circle_at_top,_rgba(59,130,246,0.08),_transparent_55%),radial-gradient(circle_at_bottom,_rgba(167,139,250,0.06),_transparent_60%)]" />
      )}
      <div className="relative">
      {options ? (
        <div className="flex flex-wrap items-end gap-3">
          <div className="min-w-[140px]">
            <CompactMultiSelectDropdown
              label="Status"
              icon="📊"
              options={options.statusOptions.map((opt) => opt.value)}
              selected={normalizeToArray(state.status)}
              onChange={(values) => onChange({ status: values.length > 0 ? values : undefined })}
              placeholder="All statuses"
              disabled={disabled}
              optionFormatter={(val) => options.statusOptions.find((opt) => opt.value === val)?.label || val}
            />
          </div>
          <div className="min-w-[140px]">
            <CompactMultiSelectDropdown
              label="Priority"
              icon="⚡"
              options={options.priorityOptions.map((opt) => opt.value)}
              selected={normalizeToArray(state.priority)}
              onChange={(values) => onChange({ priority: values.length > 0 ? values : undefined })}
              placeholder="All priorities"
              disabled={disabled}
              optionFormatter={(val) => options.priorityOptions.find((opt) => opt.value === val)?.label || val}
            />
          </div>
          <div className="min-w-[140px]">
            <CompactMultiSelectDropdown
              label="Category"
              icon="📂"
              options={options.categoryOptions.map((opt) => String(opt.value))}
              selected={normalizeToArray(state.category)}
              onChange={(values) => onChange({ category: values.length > 0 ? values : undefined })}
              placeholder="All categories"
              disabled={disabled}
              optionFormatter={(val) => options.categoryOptions.find((opt) => String(opt.value) === val)?.label || val}
            />
          </div>
          <div className="min-w-[140px]">
            <CompactMultiSelectDropdown
              label="Site"
              icon="📍"
              options={options.siteOptions.map((opt) => String(opt.value))}
              selected={normalizeToArray(state.site)}
              onChange={(values) => onChange({ site: values.length > 0 ? values : undefined })}
              placeholder="All sites"
              disabled={disabled}
              optionFormatter={(val) => options.siteOptions.find((opt) => String(opt.value) === val)?.label || val}
            />
          </div>
          <div className="min-w-[140px]">
            <MonthPicker
              months={availableMonths}
              selectedMonth={selectedMonth}
              selectedYear={selectedYear}
              selectedRange={selectedRange}
              disabled={disabled}
              onMonthChange={setSelectedMonth}
              onYearChange={setSelectedYear}
              onRangeChange={setSelectedRange}
            />
          </div>
          
          <button
            type="button"
            onClick={onApply}
            disabled={disabled}
            className="rounded-lg border px-4 py-1.5 text-xs font-semibold uppercase tracking-wide text-white shadow-lg transition disabled:cursor-not-allowed disabled:opacity-50"
            style={{
              borderColor: applyButtonBorder,
              backgroundColor: applyButtonBg,
            }}
            onMouseEnter={(e) => {
              if (!disabled) {
                e.currentTarget.style.backgroundColor = applyButtonHoverBg;
              }
            }}
            onMouseLeave={(e) => {
              if (!disabled) {
                e.currentTarget.style.backgroundColor = applyButtonBg;
              }
            }}
          >
            Apply Filters
          </button>
          <button
            type="button"
            onClick={onReset}
            disabled={disabled || activeCount === 0}
            className="rounded-lg border px-4 py-1.5 text-xs font-semibold uppercase tracking-wide shadow-sm transition disabled:cursor-not-allowed disabled:opacity-40"
            style={{
              borderColor: resetButtonBorder,
              backgroundColor: resetButtonBg,
              color: resetButtonText,
            }}
            onMouseEnter={(e) => {
              if (!disabled && activeCount > 0) {
                e.currentTarget.style.borderColor = resetButtonHoverBorder;
                e.currentTarget.style.color = resetButtonHoverText;
              }
            }}
            onMouseLeave={(e) => {
              if (!disabled && activeCount > 0) {
                e.currentTarget.style.borderColor = resetButtonBorder;
                e.currentTarget.style.color = resetButtonText;
              }
            }}
          >
            🔄 Clear
          </button>
        </div>
      ) : (
        <div className="flex flex-wrap items-end gap-3">
          {Array.from({ length: 7 }).map((_, index) => (
            <div
              key={`ticket-filter-skeleton-${index}`}
              className="h-10 w-32 animate-pulse rounded-xl border"
              style={{
                borderColor: skeletonBorder,
                backgroundColor: skeletonBg,
              }}
            />
          ))}
        </div>
      )}
      </div>
    </section>
  );
};

