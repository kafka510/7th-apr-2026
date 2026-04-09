 
import { useState } from 'react';
import { useTheme } from '../../../contexts/ThemeContext';
import type { FeedbackListParams } from '../types';
import { CompactMultiSelectDropdown } from '../../yield/components/CompactMultiSelectDropdown';

interface FeedbackFiltersProps {
  filters: FeedbackListParams;
  onFilterChange: (filters: FeedbackListParams) => void;
}

const STATUS_OPTIONS = ['pending', 'attended'];

const formatStatus = (status: string): string => {
  return status.charAt(0).toUpperCase() + status.slice(1);
};

export function FeedbackFilters({ filters, onFilterChange }: FeedbackFiltersProps) {
  const { theme } = useTheme();
  
  const labelColor = theme === 'dark' ? '#94a3b8' : '#64748b';
  const inputBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.8)' : '#ffffff';
  const inputBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : 'rgba(203, 213, 225, 0.8)';
  const inputText = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';
  const inputPlaceholder = theme === 'dark' ? '#64748b' : '#94a3b8';
  const inputFocusBorder = theme === 'dark' ? '#3b82f6' : '#0072ce';
  const searchButtonBg = theme === 'dark' ? 'rgba(59, 130, 246, 0.2)' : 'rgba(59, 130, 246, 0.1)';
  const searchButtonBorder = theme === 'dark' ? 'rgba(59, 130, 246, 0.5)' : 'rgba(0, 114, 206, 0.7)';
  const searchButtonText = theme === 'dark' ? '#93c5fd' : '#1e40af';
  const searchButtonHoverBg = theme === 'dark' ? 'rgba(59, 130, 246, 0.3)' : 'rgba(59, 130, 246, 0.15)';
  const badgeBg = theme === 'dark' ? 'rgba(59, 130, 246, 0.2)' : 'rgba(59, 130, 246, 0.1)';
  const badgeBorder = theme === 'dark' ? 'rgba(59, 130, 246, 0.5)' : 'rgba(0, 114, 206, 0.7)';
  const badgeText = theme === 'dark' ? '#93c5fd' : '#1e40af';
  const clearButtonBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.6)' : 'rgba(248, 250, 252, 0.9)';
  const clearButtonBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : 'rgba(203, 213, 225, 0.8)';
  const clearButtonText = theme === 'dark' ? '#cbd5e1' : '#475569';
  const clearButtonHoverBorder = theme === 'dark' ? 'rgba(71, 85, 105, 0.8)' : '#94a3b8';
  const clearButtonHoverText = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';
  
  // Local state for search input (only submitted on form submit)
  const [localSearch, setLocalSearch] = useState(filters.search || '');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onFilterChange({
      ...filters,
      search: localSearch.trim() || undefined,
    });
  };

  const handleStatusChange = (selectedStatus: string[]) => {
    onFilterChange({
      ...filters,
      status: selectedStatus,
    });
  };

  const handleClear = () => {
    setLocalSearch('');
    onFilterChange({
      status: [],
      search: undefined,
    });
  };

  const hasFilters = filters.status.length > 0 || localSearch;

  return (
    <div className="space-y-2">
      <div className="grid grid-cols-12 gap-2">
        {/* Status Filter */}
        <div className="col-span-12 md:col-span-3">
          <CompactMultiSelectDropdown
            label="Status"
            options={STATUS_OPTIONS}
            selected={filters.status}
            onChange={handleStatusChange}
            placeholder="All Status"
            icon="🔖"
            optionFormatter={formatStatus}
          />
        </div>

        {/* Search Input */}
        <div className="col-span-12 md:col-span-7">
          <div className="flex flex-col gap-0.5">
            <label 
              className="flex items-center gap-0.5 text-[8px] font-semibold uppercase tracking-wide"
              style={{ color: labelColor }}
            >
              <span className="text-[10px]">🔍</span>
              <span>Search</span>
            </label>
            <input
              type="text"
              value={localSearch}
              onChange={(e) => setLocalSearch(e.target.value)}
              onKeyPress={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  handleSubmit(e);
                }
              }}
              placeholder="Search by subject, message, username, or email..."
              className="w-full rounded-lg border px-2 py-1 text-[10px] font-medium shadow-inner transition-all duration-200 focus:outline-none focus:ring-1"
              style={{
                borderColor: inputBorder,
                backgroundColor: inputBg,
                color: inputText,
                boxShadow: theme === 'dark' ? 'inset 0 2px 4px rgba(0, 0, 0, 0.3)' : 'inset 0 1px 2px rgba(0, 0, 0, 0.05)',
              }}
              onFocus={(e) => {
                e.currentTarget.style.borderColor = inputFocusBorder;
              }}
              onBlur={(e) => {
                e.currentTarget.style.borderColor = inputBorder;
              }}
              onMouseEnter={(e) => {
                if (document.activeElement !== e.currentTarget) {
                  e.currentTarget.style.borderColor = inputFocusBorder;
                }
              }}
              onMouseLeave={(e) => {
                if (document.activeElement !== e.currentTarget) {
                  e.currentTarget.style.borderColor = inputBorder;
                }
              }}
            />
            <style>{`
              input::placeholder {
                color: ${inputPlaceholder};
              }
              input:focus {
                border-color: ${inputFocusBorder};
                box-shadow: 0 0 0 1px ${theme === 'dark' ? 'rgba(59, 130, 246, 0.3)' : 'rgba(0, 114, 206, 0.2)'};
              }
            `}</style>
          </div>
        </div>

        {/* Search Button */}
        <div className="col-span-12 md:col-span-2">
          <div className="flex flex-col gap-0.5">
            <label className="text-[8px] font-semibold uppercase tracking-wide text-transparent">
              Action
            </label>
            <button
              type="button"
              onClick={handleSubmit}
              className="rounded-lg border px-3 py-1 text-[10px] font-semibold uppercase tracking-wide shadow-md transition-all duration-200 focus:outline-none focus:ring-2"
              style={{
                borderColor: searchButtonBorder,
                backgroundColor: searchButtonBg,
                color: searchButtonText,
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = searchButtonHoverBg;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = searchButtonBg;
              }}
            >
              🔍 Search
            </button>
          </div>
        </div>
      </div>

      {/* Active Filters Display */}
      {hasFilters && (
        <div className="flex flex-wrap items-center gap-2 pt-1">
          <span 
            className="text-[9px] font-semibold uppercase tracking-wide"
            style={{ color: labelColor }}
          >
            Active Filters:
          </span>
          {filters.status.length > 0 &&
            filters.status.map((status) => (
              <span
                key={status}
                className="inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-[9px] font-medium"
                style={{
                  borderColor: badgeBorder,
                  backgroundColor: badgeBg,
                  color: badgeText,
                }}
              >
                Status: {formatStatus(status)}
                <button
                  type="button"
                  onClick={() => {
                    handleStatusChange(filters.status.filter((s) => s !== status));
                  }}
                  className="ml-1 transition-colors"
                  style={{ color: badgeText }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.color = theme === 'dark' ? '#bfdbfe' : '#0056a3';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.color = badgeText;
                  }}
                  aria-label={`Remove ${status} filter`}
                >
                  ✕
                </button>
              </span>
            ))}
          {filters.search && (
            <span 
              className="inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-[9px] font-medium"
              style={{
                borderColor: badgeBorder,
                backgroundColor: badgeBg,
                color: badgeText,
              }}
            >
              Search: &quot;{filters.search}&quot;
              <button
                type="button"
                onClick={() => {
                  setLocalSearch('');
                  onFilterChange({
                    ...filters,
                    search: undefined,
                  });
                }}
                className="ml-1 transition-colors"
                style={{ color: badgeText }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.color = theme === 'dark' ? '#bfdbfe' : '#0056a3';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.color = badgeText;
                }}
                aria-label="Remove search filter"
              >
                ✕
              </button>
            </span>
          )}
          <button
            type="button"
            onClick={handleClear}
            className="rounded-md border px-2 py-0.5 text-[9px] font-semibold uppercase tracking-wide transition-all duration-200"
            style={{
              borderColor: clearButtonBorder,
              backgroundColor: clearButtonBg,
              color: clearButtonText,
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = clearButtonHoverBorder;
              e.currentTarget.style.color = clearButtonHoverText;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = clearButtonBorder;
              e.currentTarget.style.color = clearButtonText;
            }}
          >
            Clear All
          </button>
        </div>
      )}
    </div>
  );
}
