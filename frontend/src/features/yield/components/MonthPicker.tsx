import { useState, useRef, useEffect } from 'react';
import { useTheme } from '../../../contexts/ThemeContext';
import { useResponsiveFontSize } from '../../../utils/fontScaling';

type MonthPickerProps = {
  months: string[];
  selectedMonth: string | null;
  selectedYear: string | null;
  selectedRange: { start: string; end: string } | null;
  disabled?: boolean;
  hideLabel?: boolean;
  onMonthChange: (month: string | null) => void;
  onYearChange: (year: string | null) => void;
  onRangeChange: (range: { start: string; end: string } | null) => void;
};

const formatMonthLabel = (ym: string | null): string => {
  if (!ym) return 'All Months';
  const [y, m] = ym.split('-');
  const date = new Date(Number(y), Number(m) - 1, 1);
  return date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
};

const formatMonthShort = (ym: string): string => {
  const [y, m] = ym.split('-');
  const date = new Date(Number(y), Number(m) - 1, 1);
  return date.toLocaleDateString('en-US', { month: 'short' });
};

// Standard month abbreviations for grid display
const MONTH_ABBREVIATIONS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

export const MonthPicker = ({
  months,
  selectedMonth,
  selectedYear,
  selectedRange,
  disabled = false,
  hideLabel = false,
  onMonthChange,
  onYearChange,
  onRangeChange,
}: MonthPickerProps) => {
  const { theme } = useTheme();
  
  // Responsive font sizes (scaled up by 1.25x)
  const FONT_SCALE = 1.25;
  const labelFontSize = useResponsiveFontSize(8, 12, 7) * FONT_SCALE;
  const bodyFontSize = useResponsiveFontSize(10, 14, 9) * FONT_SCALE;
  
  const [isOpen, setIsOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<'month' | 'year' | 'range'>('month');
  const [tempRangeStart, setTempRangeStart] = useState<string>('');
  const [tempRangeEnd, setTempRangeEnd] = useState<string>('');
  const containerRef = useRef<HTMLDivElement>(null);

  // When switching to range tab, preserve year context
  useEffect(() => {
    if (activeTab === 'range') {
      // If we have an existing range, initialize temp range with it
      if (selectedRange && selectedRange.start && selectedRange.end && !tempRangeStart && !tempRangeEnd) {
        setTempRangeStart(selectedRange.start);
        setTempRangeEnd(selectedRange.end);
      }
    } else {
      // Clear temp range when switching away from range tab (but only if not applying)
      // Don't clear if we're in the process of applying
      if (!tempRangeStart || !tempRangeEnd) {
        setTempRangeStart('');
        setTempRangeEnd('');
      }
    }
  }, [activeTab, selectedRange, tempRangeStart, tempRangeEnd]);

  // Extract unique years from months
  const years = [...new Set(months.map((m) => m.split('-')[0]))].sort((a, b) => Number(b) - Number(a));

  // Get all unique months (grouped by month number, showing latest year available)
  // BUT: When a year is selected, only show months from that year
  // Also consider year from existing range when selecting a new range
  const getAvailableMonths = () => {
    // If a year is selected, use it
    if (selectedYear) {
      // ✅ Show ONLY months from selected year
      return months
        .filter((m) => m.startsWith(selectedYear))
        .sort((a, b) => Number(a.split('-')[1]) - Number(b.split('-')[1]));
    }

    // If a range is already selected, extract year from the range to maintain context
    if (selectedRange && selectedRange.start) {
      const yearFromRange = selectedRange.start.split('-')[0];
      const monthsFromRangeYear = months
        .filter((m) => m.startsWith(yearFromRange))
        .sort((a, b) => Number(a.split('-')[1]) - Number(b.split('-')[1]));
      // Only use this if we have months from that year
      if (monthsFromRangeYear.length > 0) {
        return monthsFromRangeYear;
      }
    }

    // Default behavior (no year selected): show latest year per month
    const monthMap = new Map<number, string>();
    months.forEach((month) => {
      const [, m] = month.split('-');
      const monthNum = Number(m);
      if (!monthMap.has(monthNum) || month > monthMap.get(monthNum)!) {
        monthMap.set(monthNum, month);
      }
    });
    // Return months sorted by month number (1-12)
    return Array.from({ length: 12 }, (_, i) => {
      const monthNum = i + 1;
      return monthMap.get(monthNum) || null;
    }).filter(Boolean) as string[];
  };

  const availableMonths = getAvailableMonths();

  // Allow both year and month to be set: user can select a year then pick a single month.
  // Parent (e.g. BessV1Filters) clears month when year is selected via handleYearChange;
  // we do not clear month here when both are set, so single-month selection works.

  // Same for range - if range is selected, ensure month is null
  // BUT: Keep year if it matches the range year (to maintain context for future range selections)
  useEffect(() => {
    if (selectedRange) {
      // Always clear month when range is selected
      if (selectedMonth) onMonthChange(null);
      
      // Only clear year if it doesn't match the range year
      // This preserves the year context for future range selections
      if (selectedYear && selectedRange.start) {
        const rangeYear = selectedRange.start.split('-')[0];
        if (selectedYear !== rangeYear) {
          onYearChange(null);
        }
        // If years match, keep the year selected for context
      } else if (selectedYear && !selectedRange.start) {
        // If range is cleared but year exists, keep year
        // Don't clear it
      }
    }
  }, [selectedRange, selectedMonth, selectedYear, onMonthChange, onYearChange]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Node;
      if (containerRef.current && !containerRef.current.contains(target)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [isOpen]);

  const handleMonthSelect = (month: string) => {
    onMonthChange(month);
    setIsOpen(false);
  };

  const handleYearSelect = (year: string) => {
    onYearChange(year);
    setIsOpen(false);
  };

  const handleRangeMonthClick = (month: string) => {
    if (!tempRangeStart || (tempRangeStart && tempRangeEnd)) {
      // Start new selection
      setTempRangeStart(month);
      setTempRangeEnd('');
    } else if (month >= tempRangeStart) {
      // Complete the range
      setTempRangeEnd(month);
    } else {
      // If clicked before start, swap them
      setTempRangeEnd(tempRangeStart);
      setTempRangeStart(month);
    }
  };

  const handleRangeApply = () => {
    if (tempRangeStart && tempRangeEnd && tempRangeStart <= tempRangeEnd) {
      // Ensure both range start and end have the same year
      // Priority: 1) selectedYear, 2) year from existing range, 3) year from tempRangeStart
      let rangeStart = tempRangeStart;
      let rangeEnd = tempRangeEnd;
      
      // Determine which year to use
      let targetYear: string | null = null;
      
      if (selectedYear) {
        // Use selected year if available
        targetYear = selectedYear;
      } else if (selectedRange && selectedRange.start) {
        // Use year from existing range to maintain context
        targetYear = selectedRange.start.split('-')[0];
      } else if (tempRangeStart.includes('-')) {
        // Use year from the temp range start
        targetYear = tempRangeStart.split('-')[0];
      }
      
      // If we have a target year, ensure both range months use that year
      if (targetYear) {
        const startMonthNum = tempRangeStart.split('-')[1];
        const endMonthNum = tempRangeEnd.split('-')[1];
        rangeStart = `${targetYear}-${startMonthNum}`;
        rangeEnd = `${targetYear}-${endMonthNum}`;
      }
      
      onRangeChange({ start: rangeStart, end: rangeEnd });
      setIsOpen(false);
      setTempRangeStart('');
      setTempRangeEnd('');
    }
  };

  const handleClear = () => {
    onMonthChange(null);
    onYearChange(null);
    onRangeChange(null);
    setTempRangeStart('');
    setTempRangeEnd('');
    setIsOpen(false);
  };

  const handleClose = () => {
    setIsOpen(false);
    setTempRangeStart('');
    setTempRangeEnd('');
  };

  const getDisplayLabel = (): string => {
    if (selectedRange && selectedRange.start && selectedRange.end) {
      return `${formatMonthLabel(selectedRange.start)} – ${formatMonthLabel(selectedRange.end)}`;
    }
    if (selectedMonth) {
      return formatMonthLabel(selectedMonth);
    }
    if (selectedYear) {
      return `${selectedYear} (Full Year)`;
    }
    return 'All Months';
  };

  const isMonthSelected = (month: string) => selectedMonth === month;
  const isYearSelected = (year: string) => selectedYear === year;
  
  const isRangeStart = (month: string) => tempRangeStart === month;
  const isRangeEnd = (month: string) => tempRangeEnd === month;
  const isInRange = (month: string) => {
    if (!tempRangeStart || !tempRangeEnd) return false;
    return month >= tempRangeStart && month <= tempRangeEnd;
  };
  const isRangeDisabled = (month: string): boolean => {
    return !!(tempRangeStart && !tempRangeEnd && month < tempRangeStart);
  };

  // Theme-aware colors
  const isDark = theme === 'dark';
  const triggerBg = isDark ? 'rgba(15, 23, 42, 0.8)' : '#ffffff';
  const triggerBorder = isDark ? 'rgba(51, 65, 85, 0.7)' : 'rgba(203, 213, 225, 0.7)';
  const triggerText = isDark ? '#e2e8f0' : '#1a1a1a';
  const triggerHoverBg = isDark ? 'rgba(30, 41, 59, 0.8)' : '#f8fafc';
  const dropdownBg = isDark ? 'rgba(2, 6, 23, 0.95)' : '#ffffff';
  const dropdownBorder = isDark ? 'rgba(30, 41, 59, 1)' : 'rgba(226, 232, 240, 1)';
  const tabText = isDark ? '#94a3b8' : '#4a5568';
  const tabActiveText = isDark ? '#60a5fa' : '#0072ce';
  const tabActiveBg = isDark ? 'rgba(15, 23, 42, 0.8)' : '#e6f2ff';
  const monthButtonBg = isDark ? 'rgba(30, 41, 59, 0.5)' : '#f8fafc';
  const monthButtonBorder = isDark ? 'rgba(51, 65, 85, 1)' : 'rgba(203, 213, 225, 1)';
  const monthButtonText = isDark ? '#cbd5e0' : '#1a1a1a';
  const monthButtonSelectedBg = isDark ? 'rgba(56, 189, 248, 0.3)' : 'rgba(0, 114, 206, 0.15)';
  const monthButtonSelectedText = isDark ? '#93c5fd' : '#0072ce';
  const footerBg = isDark ? 'rgba(15, 23, 42, 0.8)' : '#f8fafc';
  const footerBorder = isDark ? 'rgba(30, 41, 59, 1)' : 'rgba(226, 232, 240, 1)';
  const footerButtonBg = isDark ? 'rgba(30, 41, 59, 0.5)' : '#ffffff';
  const footerButtonText = isDark ? '#cbd5e0' : '#4a5568';
  const labelText = isDark ? '#94a3b8' : '#718096';

  return (
    <div ref={containerRef} className="relative">
      {/* Trigger Button */}
      {!hideLabel && (
        <div 
          className="mb-0.5 flex items-center gap-0.5 font-semibold uppercase tracking-wide"
          style={{ color: labelText, fontSize: `${labelFontSize}px` }}
        >
          <span style={{ fontSize: `${bodyFontSize}px` }}>📅</span>
          <span>Month</span>
        </div>
      )}
      <button
        type="button"
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          if (!disabled) {
            setIsOpen(!isOpen);
          }
        }}
        disabled={disabled || months.length === 0}
        className="w-full cursor-pointer rounded-lg px-2 py-1 text-left font-medium shadow-inner transition-all duration-200 focus:outline-none focus:ring-1 disabled:cursor-not-allowed disabled:opacity-50"
        style={{
          fontSize: `${bodyFontSize}px`,
          border: `1px solid ${triggerBorder}`,
          backgroundColor: triggerBg,
          color: triggerText,
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.borderColor = '#0072ce';
          e.currentTarget.style.backgroundColor = triggerHoverBg;
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.borderColor = triggerBorder;
          e.currentTarget.style.backgroundColor = triggerBg;
        }}
        onFocus={(e) => {
          e.currentTarget.style.borderColor = '#0072ce';
          e.currentTarget.style.boxShadow = '0 0 0 1px rgba(0, 114, 206, 0.3)';
        }}
        onBlur={(e) => {
          e.currentTarget.style.borderColor = triggerBorder;
          e.currentTarget.style.boxShadow = 'none';
        }}
      >
        <span className="truncate">📅 {getDisplayLabel()}</span>
      </button>

      {/* Dropdown */}
      {isOpen && !disabled && (
        <div
          className="absolute z-[9999] mt-1 w-full min-w-[280px] max-w-[320px] overflow-hidden rounded-xl shadow-2xl backdrop-blur-md"
          style={{
            border: `1px solid ${dropdownBorder}`,
            backgroundColor: dropdownBg,
            boxShadow: isDark 
              ? '0 20px 25px -5px rgba(0, 0, 0, 0.7), 0 10px 10px -5px rgba(0, 0, 0, 0.4)'
              : '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
          }}
          onMouseDown={(e) => e.stopPropagation()}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Tabs */}
          <div 
            className="flex"
            style={{ borderBottom: `1px solid ${isDark ? 'rgba(30, 41, 59, 1)' : 'rgba(226, 232, 240, 1)'}` }}
          >
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setActiveTab('month');
              }}
              className="flex-1 px-3 py-2.5 text-xs font-semibold uppercase tracking-wide transition-all duration-200"
              style={{
                borderBottom: activeTab === 'month' ? '2px solid #0072ce' : 'none',
                backgroundColor: activeTab === 'month' ? tabActiveBg : 'transparent',
                color: activeTab === 'month' ? tabActiveText : tabText,
              }}
              onMouseEnter={(e) => {
                if (activeTab !== 'month') {
                  e.currentTarget.style.backgroundColor = isDark ? 'rgba(15, 23, 42, 0.4)' : '#f1f5f9';
                  e.currentTarget.style.color = isDark ? '#e2e8f0' : '#1a1a1a';
                }
              }}
              onMouseLeave={(e) => {
                if (activeTab !== 'month') {
                  e.currentTarget.style.backgroundColor = 'transparent';
                  e.currentTarget.style.color = tabText;
                }
              }}
            >
              Month
            </button>
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setActiveTab('year');
              }}
              className="flex-1 px-3 py-2.5 text-xs font-semibold uppercase tracking-wide transition-all duration-200"
              style={{
                borderBottom: activeTab === 'year' ? '2px solid #0072ce' : 'none',
                backgroundColor: activeTab === 'year' ? tabActiveBg : 'transparent',
                color: activeTab === 'year' ? tabActiveText : tabText,
              }}
              onMouseEnter={(e) => {
                if (activeTab !== 'year') {
                  e.currentTarget.style.backgroundColor = isDark ? 'rgba(15, 23, 42, 0.4)' : '#f1f5f9';
                  e.currentTarget.style.color = isDark ? '#e2e8f0' : '#1a1a1a';
                }
              }}
              onMouseLeave={(e) => {
                if (activeTab !== 'year') {
                  e.currentTarget.style.backgroundColor = 'transparent';
                  e.currentTarget.style.color = tabText;
                }
              }}
            >
              Year
            </button>
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setActiveTab('range');
              }}
              className="flex-1 px-3 py-2.5 text-xs font-semibold uppercase tracking-wide transition-all duration-200"
              style={{
                borderBottom: activeTab === 'range' ? '2px solid #0072ce' : 'none',
                backgroundColor: activeTab === 'range' ? tabActiveBg : 'transparent',
                color: activeTab === 'range' ? tabActiveText : tabText,
              }}
              onMouseEnter={(e) => {
                if (activeTab !== 'range') {
                  e.currentTarget.style.backgroundColor = isDark ? 'rgba(15, 23, 42, 0.4)' : '#f1f5f9';
                  e.currentTarget.style.color = isDark ? '#e2e8f0' : '#1a1a1a';
                }
              }}
              onMouseLeave={(e) => {
                if (activeTab !== 'range') {
                  e.currentTarget.style.backgroundColor = 'transparent';
                  e.currentTarget.style.color = tabText;
                }
              }}
            >
              Range
            </button>
          </div>

          {/* Content */}
          <div className="p-4">
            {/* Month Tab */}
            {activeTab === 'month' && (
              <div className="space-y-3">
                <div className="grid grid-cols-3 gap-2">
                  {availableMonths.length === 0 ? (
                    <div 
                      className="col-span-3 py-4 text-center text-xs"
                      style={{ color: tabText }}
                    >
                      No months available
                    </div>
                  ) : (
                    availableMonths.map((month) => {
                      const monthNum = Number(month.split('-')[1]);
                      const monthAbbr = MONTH_ABBREVIATIONS[monthNum - 1] || `M${monthNum}`;
                      const selected = isMonthSelected(month);
                      
                      return (
                        <button
                          key={month}
                          type="button"
                          onClick={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            handleMonthSelect(month);
                          }}
                          className="rounded-lg border p-2 text-xs font-medium transition-all duration-200"
                          style={{
                            border: `1px solid ${selected ? '#0072ce' : monthButtonBorder}`,
                            backgroundColor: selected ? monthButtonSelectedBg : monthButtonBg,
                            color: selected ? monthButtonSelectedText : monthButtonText,
                            boxShadow: selected 
                              ? (isDark ? '0 4px 6px rgba(0, 114, 206, 0.2)' : '0 2px 4px rgba(0, 114, 206, 0.1)')
                              : 'none',
                          }}
                          onMouseEnter={(e) => {
                            if (!selected) {
                              e.currentTarget.style.borderColor = '#0072ce';
                              e.currentTarget.style.backgroundColor = isDark ? 'rgba(30, 41, 59, 0.8)' : '#f1f5f9';
                              e.currentTarget.style.boxShadow = '0 1px 2px rgba(0, 0, 0, 0.1)';
                            }
                          }}
                          onMouseLeave={(e) => {
                            if (!selected) {
                              e.currentTarget.style.borderColor = monthButtonBorder;
                              e.currentTarget.style.backgroundColor = monthButtonBg;
                              e.currentTarget.style.boxShadow = 'none';
                            }
                          }}
                        >
                          {monthAbbr}
                        </button>
                      );
                    })
                  )}
                </div>
              </div>
            )}

            {/* Year Tab */}
            {activeTab === 'year' && (
              <div className="space-y-3">
                <div className="grid grid-cols-3 gap-2">
                  {years.map((year) => {
                    const selected = isYearSelected(year);
                    return (
                      <button
                        key={year}
                        type="button"
                        onClick={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          handleYearSelect(year);
                        }}
                        className="rounded-lg border px-3 py-2 text-sm font-medium transition-all duration-200"
                        style={{
                          border: `1px solid ${selected ? '#0072ce' : monthButtonBorder}`,
                          backgroundColor: selected ? monthButtonSelectedBg : monthButtonBg,
                          color: selected ? monthButtonSelectedText : monthButtonText,
                          boxShadow: selected 
                            ? (isDark ? '0 4px 6px rgba(0, 114, 206, 0.2)' : '0 2px 4px rgba(0, 114, 206, 0.1)')
                            : 'none',
                        }}
                        onMouseEnter={(e) => {
                          if (!selected) {
                            e.currentTarget.style.borderColor = '#0072ce';
                            e.currentTarget.style.backgroundColor = isDark ? 'rgba(30, 41, 59, 0.8)' : '#f1f5f9';
                            e.currentTarget.style.boxShadow = '0 1px 2px rgba(0, 0, 0, 0.1)';
                          }
                        }}
                        onMouseLeave={(e) => {
                          if (!selected) {
                            e.currentTarget.style.borderColor = monthButtonBorder;
                            e.currentTarget.style.backgroundColor = monthButtonBg;
                            e.currentTarget.style.boxShadow = 'none';
                          }
                        }}
                      >
                        {year}
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Range Tab */}
            {activeTab === 'range' && (
              <div className="space-y-3">
                {/* Instruction Text */}
                <div 
                  className="py-1 text-center text-xs"
                  style={{ color: tabText }}
                >
                  {!tempRangeStart
                    ? 'Select start month'
                    : !tempRangeEnd
                    ? 'Select end month'
                    : `${formatMonthShort(tempRangeStart)} – ${formatMonthShort(tempRangeEnd)}`}
                </div>

                {/* Month Grid */}
                <div className="grid grid-cols-3 gap-2">
                  {availableMonths.map((month) => {
                    const monthNum = Number(month.split('-')[1]);
                    const monthAbbr = MONTH_ABBREVIATIONS[monthNum - 1] || `M${monthNum}`;
                    const isStart = isRangeStart(month);
                    const isEnd = isRangeEnd(month);
                    const inRange = isInRange(month);
                    const isDisabled = isRangeDisabled(month);

                    let buttonStyle: React.CSSProperties = {};
                    if (isStart || isEnd) {
                      buttonStyle = {
                        border: '1px solid #0072ce',
                        backgroundColor: monthButtonSelectedBg,
                        color: monthButtonSelectedText,
                        boxShadow: isDark ? '0 4px 6px rgba(0, 114, 206, 0.2)' : '0 2px 4px rgba(0, 114, 206, 0.1)',
                      };
                    } else if (inRange) {
                      buttonStyle = {
                        border: '1px solid rgba(0, 114, 206, 0.5)',
                        backgroundColor: isDark ? 'rgba(0, 114, 206, 0.15)' : 'rgba(0, 114, 206, 0.08)',
                        color: monthButtonSelectedText,
                      };
                    } else if (isDisabled) {
                      buttonStyle = {
                        border: `1px solid ${monthButtonBorder}`,
                        backgroundColor: isDark ? 'rgba(30, 41, 59, 0.3)' : '#f8fafc',
                        color: isDark ? '#64748b' : '#94a3b8',
                        opacity: 0.5,
                        cursor: 'not-allowed',
                      };
                    } else {
                      buttonStyle = {
                        border: `1px solid ${monthButtonBorder}`,
                        backgroundColor: monthButtonBg,
                        color: monthButtonText,
                      };
                    }

                    return (
                      <button
                        key={month}
                        type="button"
                        onClick={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          if (!isDisabled) {
                            handleRangeMonthClick(month);
                          }
                        }}
                        disabled={isDisabled}
                        className="rounded-lg border p-2 text-xs font-medium transition-all duration-200"
                        style={buttonStyle}
                        onMouseEnter={(e) => {
                          if (!isDisabled && !isStart && !isEnd && !inRange) {
                            e.currentTarget.style.borderColor = '#0072ce';
                            e.currentTarget.style.backgroundColor = isDark ? 'rgba(30, 41, 59, 0.8)' : '#f1f5f9';
                            e.currentTarget.style.boxShadow = '0 1px 2px rgba(0, 0, 0, 0.1)';
                          }
                        }}
                        onMouseLeave={(e) => {
                          if (!isDisabled && !isStart && !isEnd && !inRange) {
                            e.currentTarget.style.borderColor = monthButtonBorder;
                            e.currentTarget.style.backgroundColor = monthButtonBg;
                            e.currentTarget.style.boxShadow = 'none';
                          }
                        }}
                      >
                        {monthAbbr}
                      </button>
                    );
                  })}
                </div>

                {/* Apply Button */}
                {tempRangeStart && tempRangeEnd && (
                  <button
                    type="button"
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      handleRangeApply();
                    }}
                    className="w-full rounded-lg border px-4 py-2 text-xs font-semibold transition-all duration-200"
                    style={{
                      border: '1px solid #0072ce',
                      backgroundColor: isDark ? 'rgba(0, 114, 206, 0.2)' : 'rgba(0, 114, 206, 0.1)',
                      color: monthButtonSelectedText,
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.backgroundColor = isDark ? 'rgba(0, 114, 206, 0.3)' : 'rgba(0, 114, 206, 0.15)';
                      e.currentTarget.style.boxShadow = isDark 
                        ? '0 4px 6px rgba(0, 114, 206, 0.2)' 
                        : '0 2px 4px rgba(0, 114, 206, 0.1)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.backgroundColor = isDark ? 'rgba(0, 114, 206, 0.2)' : 'rgba(0, 114, 206, 0.1)';
                      e.currentTarget.style.boxShadow = 'none';
                    }}
                  >
                    Apply Range
                  </button>
                )}
              </div>
            )}
          </div>

          {/* Footer Buttons */}
          <div 
            className="flex gap-2 p-3"
            style={{
              borderTop: `1px solid ${footerBorder}`,
              backgroundColor: footerBg,
            }}
          >
            <button
              type="button"
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                handleClear();
              }}
              className="flex-1 rounded-lg border px-3 py-2 text-xs font-semibold transition-all duration-200"
              style={{
                border: `1px solid ${monthButtonBorder}`,
                backgroundColor: footerButtonBg,
                color: footerButtonText,
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = isDark ? '#475569' : '#cbd5e0';
                e.currentTarget.style.backgroundColor = isDark ? 'rgba(30, 41, 59, 0.8)' : '#f1f5f9';
                e.currentTarget.style.color = isDark ? '#e2e8f0' : '#1a1a1a';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = monthButtonBorder;
                e.currentTarget.style.backgroundColor = footerButtonBg;
                e.currentTarget.style.color = footerButtonText;
              }}
            >
              Clear
            </button>
            <button
              type="button"
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                handleClose();
              }}
              className="flex-1 rounded-lg border px-3 py-2 text-xs font-semibold transition-all duration-200"
              style={{
                border: `1px solid ${monthButtonBorder}`,
                backgroundColor: footerButtonBg,
                color: footerButtonText,
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = isDark ? '#475569' : '#cbd5e0';
                e.currentTarget.style.backgroundColor = isDark ? 'rgba(30, 41, 59, 0.8)' : '#f1f5f9';
                e.currentTarget.style.color = isDark ? '#e2e8f0' : '#1a1a1a';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = monthButtonBorder;
                e.currentTarget.style.backgroundColor = footerButtonBg;
                e.currentTarget.style.color = footerButtonText;
              }}
            >
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
