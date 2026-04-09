import { useMemo, useState, useEffect } from 'react';
import type { ChangeEvent } from 'react';
import { useTheme } from '../../../contexts/ThemeContext';
import { CompactMultiSelectDropdown } from '../../yield/components/CompactMultiSelectDropdown';
import { MonthPicker } from '../../yield/components/MonthPicker';
import type { TicketListFilters, TicketListQueryState } from '../types';
import { useResponsiveFontSize } from '../../../utils/fontScaling';

type TicketListControlsProps = {
  filters: TicketListFilters | null;
  query: TicketListQueryState;
  disabled?: boolean;
  loading?: boolean;
  onChange: (updater: (state: TicketListQueryState) => TicketListQueryState) => void;
  onRefresh: () => void;
  onReset: () => void;
  onExportCSV?: () => void;
};

export const TicketListControls = ({
  filters,
  query,
  disabled = false,
  loading = false,
  onChange,
  onRefresh,
  onReset,
  onExportCSV,
}: TicketListControlsProps) => {
  const { theme } = useTheme();
  
  // Responsive font sizes
  const labelFontSize = useResponsiveFontSize(8, 12, 7);
  const inputFontSize = useResponsiveFontSize(10, 14, 9);
  const buttonFontSize = useResponsiveFontSize(9, 13, 8);
  
  const containerBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(203, 213, 225, 0.8)';
  const containerShadow = theme === 'dark' 
    ? '0 20px 25px -5px rgba(0, 0, 0, 0.4)' 
    : '0 10px 15px -3px rgba(0, 0, 0, 0.1)';
  const labelColor = theme === 'dark' ? '#94a3b8' : '#64748b';
  const inputBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.8)' : '#ffffff';
  const inputBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : 'rgba(203, 213, 225, 0.8)';
  const inputText = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';
  const inputHoverBorder = theme === 'dark' ? 'rgba(59, 130, 246, 0.5)' : '#3b82f6';
  const inputFocusBorder = theme === 'dark' ? '#3b82f6' : '#0072ce';
  const badgeBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.6)' : 'rgba(248, 250, 252, 0.9)';
  const badgeBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : 'rgba(203, 213, 225, 0.8)';
  const badgeText = theme === 'dark' ? '#cbd5e1' : '#475569';
  const buttonBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.8)' : '#ffffff';
  const buttonBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : 'rgba(203, 213, 225, 0.8)';
  const buttonText = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';
  const refreshButtonHoverBorder = theme === 'dark' ? 'rgba(59, 130, 246, 0.5)' : '#3b82f6';
  const refreshButtonHoverText = theme === 'dark' ? '#93c5fd' : '#0072ce';
  const exportButtonHoverBorder = theme === 'dark' ? 'rgba(100, 116, 139, 0.6)' : '#94a3b8';
  const exportButtonHoverText = theme === 'dark' ? '#f1f5f9' : '#0f172a';
  const resetButtonHoverBorder = theme === 'dark' ? 'rgba(248, 113, 113, 0.5)' : '#f87171';
  const resetButtonHoverText = theme === 'dark' ? '#fca5a5' : '#dc2626';
  const createButtonBg = theme === 'dark' ? 'rgba(59, 130, 246, 0.8)' : '#0072ce';
  const createButtonBorder = theme === 'dark' ? 'rgba(59, 130, 246, 0.5)' : 'rgba(0, 114, 206, 0.7)';
  const createButtonHoverBg = theme === 'dark' ? 'rgba(37, 99, 235, 0.9)' : '#0056a3';
  const skeletonBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.5)' : 'rgba(241, 245, 249, 0.8)';
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
      onChange((state) => ({
        ...state,
        dateFrom: startDate,
        dateTo: endDate,
        page: 1,
      }));
    } else if (selectedMonth) {
      const [year, month] = selectedMonth.split('-');
      const startDate = `${year}-${month}-01`;
      const endDate = new Date(parseInt(year), parseInt(month), 0).toISOString().split('T')[0];
      onChange((state) => ({
        ...state,
        dateFrom: startDate,
        dateTo: endDate,
        page: 1,
      }));
    } else if (selectedYear) {
      const startDate = `${selectedYear}-01-01`;
      const endDate = `${selectedYear}-12-31`;
      onChange((state) => ({
        ...state,
        dateFrom: startDate,
        dateTo: endDate,
        page: 1,
      }));
    } else if (selectedMonth === null && selectedYear === null && selectedRange === null && (query.dateFrom || query.dateTo)) {
      // Clear dates when month picker is cleared
      onChange((state) => ({
        ...state,
        dateFrom: undefined,
        dateTo: undefined,
        page: 1,
      }));
    }
  }, [selectedMonth, selectedYear, selectedRange]);

  const activeFilters = useMemo(() => {
    let count = 0;
    if (query.search?.trim()) count += 1;
    if (query.statuses.length) count += 1;
    if (query.priorities.length) count += 1;
    if (query.categories.length) count += 1;
    if (query.sites.length) count += 1;
    if (query.assignees.length) count += 1;
    if (query.assetNumbers.length) count += 1;
    if (query.dateFrom) count += 1;
    if (query.dateTo) count += 1;
    return count;
  }, [query]);

  const handleSelectChange = (key: keyof TicketListQueryState) => (values: string[]) => {
    if (disabled) {
      return;
    }
    onChange((state) => ({
      ...state,
      [key]: values,
      page: 1,
    }));
  };

  const handleSearchChange = (event: ChangeEvent<HTMLInputElement>) => {
    const value = event.target.value;
    onChange((state) => ({
      ...state,
      search: value,
      page: 1,
    }));
  };

  return (
    <section 
      className="rounded-xl border p-2 shadow-xl"
      style={{
        borderColor: containerBorder,
        background: theme === 'dark'
          ? 'radial-gradient(circle at top, rgba(56,189,248,0.12), transparent 55%), radial-gradient(circle at bottom, rgba(167,139,250,0.12), transparent 60%), linear-gradient(to bottom right, rgba(15, 23, 42, 0.9), rgba(30, 41, 59, 0.6), rgba(15, 23, 42, 0.9))'
          : 'radial-gradient(circle at top, rgba(59,130,246,0.08), transparent 55%), radial-gradient(circle at bottom, rgba(167,139,250,0.06), transparent 60%), linear-gradient(to bottom right, rgba(255, 255, 255, 0.95), rgba(248, 250, 252, 0.9), rgba(255, 255, 255, 0.95))',
        boxShadow: containerShadow,
      }}
    >
      <div className="flex flex-wrap items-end gap-2">
        <label className="flex min-w-[150px] flex-1 flex-col gap-0.5">
          <span
            className="font-semibold uppercase tracking-wide"
            style={{ color: labelColor, fontSize: `${labelFontSize}px` }}
          >
            🔍 Search
          </span>
          <input
            type="search"
            placeholder="Search by ticket #, title, or description…"
            disabled={disabled}
            value={query.search ?? ''}
            onChange={handleSearchChange}
            className="rounded-lg border px-2 py-1 font-medium shadow-inner transition focus:outline-none focus:ring-1 disabled:cursor-not-allowed disabled:opacity-50"
            style={{
              fontSize: `${inputFontSize}px`,
              borderColor: inputBorder,
              backgroundColor: inputBg,
              color: inputText,
            }}
            onMouseEnter={(e) => {
              if (!disabled) e.currentTarget.style.borderColor = inputHoverBorder;
            }}
            onMouseLeave={(e) => {
              if (!disabled) e.currentTarget.style.borderColor = inputBorder;
            }}
            onFocus={(e) => {
              e.currentTarget.style.borderColor = inputFocusBorder;
              e.currentTarget.style.boxShadow = theme === 'dark' 
                ? '0 0 0 1px rgba(59, 130, 246, 0.3)' 
                : '0 0 0 1px rgba(0, 114, 206, 0.2)';
            }}
            onBlur={(e) => {
              e.currentTarget.style.borderColor = inputBorder;
              e.currentTarget.style.boxShadow = 'none';
            }}
          />
        </label>

        <div className="flex flex-col gap-0.5">
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

        <span 
          className="rounded-lg border px-2.5 py-1 font-semibold uppercase tracking-wide shadow-inner"
          style={{
            borderColor: badgeBorder,
            backgroundColor: badgeBg,
            color: badgeText,
            fontSize: `${buttonFontSize}px`,
          }}
        >
          {activeFilters > 0 ? `${activeFilters} active filters` : 'All tickets'}
        </span>
        <button
          type="button"
          onClick={onRefresh}
          disabled={disabled || loading}
          className="rounded-lg border px-2.5 py-1 font-semibold uppercase tracking-wide shadow-sm transition disabled:cursor-not-allowed disabled:opacity-50"
          style={{
            borderColor: buttonBorder,
            backgroundColor: buttonBg,
            color: buttonText,
            fontSize: `${buttonFontSize}px`,
          }}
          onMouseEnter={(e) => {
            if (!disabled && !loading) {
              e.currentTarget.style.borderColor = refreshButtonHoverBorder;
              e.currentTarget.style.color = refreshButtonHoverText;
            }
          }}
          onMouseLeave={(e) => {
            if (!disabled && !loading) {
              e.currentTarget.style.borderColor = buttonBorder;
              e.currentTarget.style.color = buttonText;
            }
          }}
        >
          {loading ? '↻ Refreshing…' : '↻ Refresh'}
        </button>
        <button
          type="button"
          onClick={onExportCSV}
          disabled={disabled || loading}
          className="rounded-lg border px-2.5 py-1 font-semibold uppercase tracking-wide shadow-sm transition disabled:cursor-not-allowed disabled:opacity-50"
          style={{
            borderColor: buttonBorder,
            backgroundColor: buttonBg,
            color: buttonText,
            fontSize: `${buttonFontSize}px`,
          }}
          onMouseEnter={(e) => {
            if (!disabled && !loading) {
              e.currentTarget.style.borderColor = exportButtonHoverBorder;
              e.currentTarget.style.color = exportButtonHoverText;
            }
          }}
          onMouseLeave={(e) => {
            if (!disabled && !loading) {
              e.currentTarget.style.borderColor = buttonBorder;
              e.currentTarget.style.color = buttonText;
            }
          }}
        >
          📥 Export CSV
        </button>
        <button
          type="button"
          onClick={onReset}
          disabled={disabled || activeFilters === 0}
          className="rounded-lg border px-2.5 py-1 font-semibold uppercase tracking-wide shadow-sm transition disabled:cursor-not-allowed disabled:opacity-50"
          style={{
            borderColor: buttonBorder,
            backgroundColor: buttonBg,
            color: buttonText,
            fontSize: `${buttonFontSize}px`,
          }}
          onMouseEnter={(e) => {
            if (!disabled && activeFilters > 0) {
              e.currentTarget.style.borderColor = resetButtonHoverBorder;
              e.currentTarget.style.color = resetButtonHoverText;
            }
          }}
          onMouseLeave={(e) => {
            if (!disabled && activeFilters > 0) {
              e.currentTarget.style.borderColor = buttonBorder;
              e.currentTarget.style.color = buttonText;
            }
          }}
        >
          🔄 Reset
        </button>
        <a
          href="/tickets/create/"
          className="rounded-lg border px-2.5 py-1 font-semibold uppercase tracking-wide text-white shadow-lg transition"
          style={{
            borderColor: createButtonBorder,
            backgroundColor: createButtonBg,
            fontSize: `${buttonFontSize}px`,
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.backgroundColor = createButtonHoverBg;
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor = createButtonBg;
          }}
        >
          ➕ Create Ticket
        </a>
      </div>

      <div className="mt-2 grid gap-2 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        {filters ? (
          <>
            <CompactMultiSelectDropdown
              label="Status"
              icon="📊"
              options={filters.statusOptions.map((opt) => opt.value)}
              selected={query.statuses}
              onChange={handleSelectChange('statuses')}
              disabled={disabled}
              placeholder="All statuses"
              optionFormatter={(val) => filters.statusOptions.find((opt) => opt.value === val)?.label || val}
            />
            <CompactMultiSelectDropdown
              label="Priority"
              icon="⚡"
              options={filters.priorityOptions.map((opt) => opt.value)}
              selected={query.priorities}
              onChange={handleSelectChange('priorities')}
              disabled={disabled}
              placeholder="All priorities"
              optionFormatter={(val) => filters.priorityOptions.find((opt) => opt.value === val)?.label || val}
            />
            <CompactMultiSelectDropdown
              label="Category"
              icon="📂"
              options={filters.categoryOptions.map((opt) => opt.value)}
              selected={query.categories}
              onChange={handleSelectChange('categories')}
              disabled={disabled}
              placeholder="All categories"
              optionFormatter={(val) => filters.categoryOptions.find((opt) => opt.value === val)?.label || val}
            />
            <CompactMultiSelectDropdown
              label="Site"
              icon="📍"
              options={filters.siteOptions.map((opt) => opt.value)}
              selected={query.sites}
              onChange={handleSelectChange('sites')}
              disabled={disabled}
              placeholder="All sites"
              optionFormatter={(val) => filters.siteOptions.find((opt) => opt.value === val)?.label || val}
            />
            <CompactMultiSelectDropdown
              label="Asset Number"
              icon="🔢"
              options={filters.assetNumberOptions?.map((opt) => opt.value) || []}
              selected={query.assetNumbers}
              onChange={handleSelectChange('assetNumbers')}
              disabled={disabled}
              placeholder="All asset numbers"
              optionFormatter={(val) => filters.assetNumberOptions?.find((opt) => opt.value === val)?.label || val}
            />
            <CompactMultiSelectDropdown
              label="Assigned To"
              icon="👤"
              options={filters.assigneeOptions.map((opt) => opt.value)}
              selected={query.assignees}
              onChange={handleSelectChange('assignees')}
              disabled={disabled}
              placeholder="Anyone"
              optionFormatter={(val) => filters.assigneeOptions.find((opt) => opt.value === val)?.label || val}
            />
          </>
        ) : (
          Array.from({ length: 6 }).map((_, index) => (
            <div
              key={`filter-skeleton-${index}`}
              className="h-20 animate-pulse rounded-xl border"
              style={{
                borderColor: skeletonBorder,
                backgroundColor: skeletonBg,
              }}
            />
          ))
        )}
      </div>
    </section>
  );
};

