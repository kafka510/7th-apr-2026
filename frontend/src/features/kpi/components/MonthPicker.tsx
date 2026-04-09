import { useState, useRef, useEffect } from 'react';
import { useTheme } from '../../../contexts/ThemeContext';
import { useResponsiveFontSize } from '../../../utils/fontScaling';

type MonthPickerProps = {
  months: string[];
  selectedMonth: string | null;
  selectedYear: number | null;
  selectedRange: { start: string; end: string } | null;
  disabled?: boolean;
  onMonthChange: (month: string | null) => void;
  onYearChange: (year: number | null) => void;
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
  onMonthChange,
  onYearChange,
  onRangeChange,
}: MonthPickerProps) => {
  const { theme } = useTheme();
  
  // Responsive font sizes
  const labelFontSize = useResponsiveFontSize(9, 13, 8);
  const buttonFontSize = useResponsiveFontSize(9, 13, 8);
  
  const [isOpen, setIsOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<'month' | 'year' | 'range'>('month');
  const [tempRangeStart, setTempRangeStart] = useState<string>('');
  const [tempRangeEnd, setTempRangeEnd] = useState<string>('');
  const containerRef = useRef<HTMLDivElement>(null);

  const labelColor = theme === 'dark' ? '#94a3b8' : '#64748b';
  const buttonBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.8)' : '#ffffff';
  const buttonBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : 'rgba(203, 213, 225, 0.7)';
  const buttonText = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';
  const dropdownBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.95)' : 'rgba(255, 255, 255, 0.98)';
  const dropdownBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(203, 213, 225, 0.8)';
  const tabBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(226, 232, 240, 0.8)';
  const activeTabBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.8)' : 'rgba(241, 245, 249, 0.9)';
  const inactiveTabText = theme === 'dark' ? '#94a3b8' : '#64748b';
  const inactiveTabHoverBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.4)' : 'rgba(241, 245, 249, 0.6)';
  const monthButtonBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.5)' : 'rgba(248, 250, 252, 0.8)';
  const monthButtonBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : 'rgba(203, 213, 225, 0.7)';
  const monthButtonText = theme === 'dark' ? '#cbd5e1' : '#475569';
  const selectedButtonBg = theme === 'dark' ? 'rgba(59, 130, 246, 0.3)' : 'rgba(59, 130, 246, 0.15)';
  const selectedButtonText = theme === 'dark' ? '#93c5fd' : '#1e40af';
  const instructionText = theme === 'dark' ? '#94a3b8' : '#64748b';
  const disabledButtonBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.3)' : 'rgba(241, 245, 249, 0.5)';
  const disabledButtonText = theme === 'dark' ? '#64748b' : '#94a3b8';
  const footerBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.8)' : 'rgba(248, 250, 252, 0.9)';
  const footerBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(226, 232, 240, 0.8)';
  const footerButtonBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.5)' : 'rgba(248, 250, 252, 0.8)';
  const footerButtonBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : 'rgba(203, 213, 225, 0.7)';
  const footerButtonText = theme === 'dark' ? '#cbd5e1' : '#475569';
  const noDataText = theme === 'dark' ? '#94a3b8' : '#64748b';

  // Extract unique years from months
  const years = [...new Set(months.map((m) => m.split('-')[0]))].sort((a, b) => Number(b) - Number(a));

  // Get all unique months (grouped by month number, showing latest year available)
  const getAvailableMonths = () => {
    const monthMap = new Map<number, string>(); // month number -> latest year-month string
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

  const handleYearSelect = (year: number) => {
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
      onRangeChange({ start: tempRangeStart, end: tempRangeEnd });
      // Note: onRangeChange handler already clears month and year, so we don't need to call them here
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
  const isYearSelected = (year: number) => selectedYear === year;
  
  const isRangeStart = (month: string) => tempRangeStart === month;
  const isRangeEnd = (month: string) => tempRangeEnd === month;
  const isInRange = (month: string) => {
    if (!tempRangeStart || !tempRangeEnd) return false;
    return month >= tempRangeStart && month <= tempRangeEnd;
  };
  const isRangeDisabled = (month: string): boolean => {
    return !!(tempRangeStart && !tempRangeEnd && month < tempRangeStart);
  };

  return (
    <div ref={containerRef} className="relative space-y-1">
      {/* Trigger Button */}
      <div 
        className="flex items-center gap-1 font-semibold uppercase tracking-wide"
        style={{ color: labelColor, fontSize: `${labelFontSize}px` }}
      >
        <span className="text-xs">📅</span>
        <span>Period</span>
      </div>
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
        className="w-full cursor-pointer rounded-lg border px-2 py-1 text-left text-xs font-medium shadow-inner transition-all duration-200 hover:border-blue-500/50 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500/30 disabled:cursor-not-allowed disabled:opacity-50"
        style={{
          borderColor: buttonBorder,
          backgroundColor: buttonBg,
          color: buttonText,
          boxShadow: theme === 'dark' ? 'inset 0 2px 4px rgba(0, 0, 0, 0.4)' : 'inset 0 2px 4px rgba(0, 0, 0, 0.1)',
        }}
        onMouseEnter={(e) => {
          if (!disabled && months.length > 0) {
            e.currentTarget.style.backgroundColor = theme === 'dark' 
              ? 'rgba(51, 65, 85, 0.8)' 
              : 'rgba(241, 245, 249, 0.9)';
          }
        }}
        onMouseLeave={(e) => {
          if (!disabled && months.length > 0) {
            e.currentTarget.style.backgroundColor = buttonBg;
          }
        }}
      >
        <span className="truncate">{getDisplayLabel()}</span>
      </button>

      {/* Dropdown */}
      {isOpen && !disabled && (
        <div
          className="absolute z-[9999] mt-1 w-full min-w-[280px] max-w-[360px] overflow-hidden rounded-lg border shadow-xl backdrop-blur-md"
          style={{
            borderColor: dropdownBorder,
            backgroundColor: dropdownBg,
            boxShadow: theme === 'dark' ? '0 20px 25px -5px rgba(0, 0, 0, 0.7)' : '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
          }}
          onMouseDown={(e) => e.stopPropagation()}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Tabs */}
          <div 
            className="flex border-b"
            style={{ borderColor: tabBorder }}
          >
            {(['month', 'year', 'range'] as const).map((tab) => (
            <button
                key={tab}
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                  setActiveTab(tab);
              }}
                className="flex-1 px-2 py-1 font-semibold uppercase tracking-wide transition-all duration-200"
                style={{
                  borderBottomWidth: activeTab === tab ? '2px' : '0',
                  borderBottomColor: activeTab === tab ? '#3b82f6' : 'transparent',
                  backgroundColor: activeTab === tab ? activeTabBg : 'transparent',
                  color: activeTab === tab ? '#60a5fa' : inactiveTabText,
                  fontSize: `${buttonFontSize}px`,
                }}
                onMouseEnter={(e) => {
                  if (activeTab !== tab) {
                    e.currentTarget.style.backgroundColor = inactiveTabHoverBg;
                    e.currentTarget.style.color = theme === 'dark' ? '#e2e8f0' : '#334155';
                  }
                }}
                onMouseLeave={(e) => {
                  if (activeTab !== tab) {
                    e.currentTarget.style.backgroundColor = 'transparent';
                    e.currentTarget.style.color = inactiveTabText;
                  }
                }}
              >
                {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
            ))}
          </div>

          {/* Content */}
          <div className="p-2">
            {/* Month Tab */}
            {activeTab === 'month' && (
              <div className="space-y-2">
                <div className="grid grid-cols-3 gap-1">
                  {availableMonths.length === 0 ? (
                    <div className="col-span-3 py-2 text-center" style={{ color: noDataText, fontSize: `${buttonFontSize}px` }}>
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
                          className="rounded-lg border p-1 font-medium transition-all duration-200"
                          style={{
                            borderColor: selected ? '#3b82f6' : monthButtonBorder,
                            fontSize: `${buttonFontSize}px`,
                            backgroundColor: selected ? selectedButtonBg : monthButtonBg,
                            color: selected ? selectedButtonText : monthButtonText,
                            boxShadow: selected 
                              ? theme === 'dark' 
                                ? '0 4px 6px -1px rgba(59, 130, 246, 0.2)' 
                                : '0 2px 4px -1px rgba(59, 130, 246, 0.1)'
                              : 'none',
                          }}
                          onMouseEnter={(e) => {
                            if (!selected) {
                              e.currentTarget.style.borderColor = 'rgba(59, 130, 246, 0.5)';
                              e.currentTarget.style.backgroundColor = theme === 'dark' 
                                ? 'rgba(51, 65, 85, 0.8)' 
                                : 'rgba(241, 245, 249, 0.9)';
                            }
                          }}
                          onMouseLeave={(e) => {
                            if (!selected) {
                              e.currentTarget.style.borderColor = monthButtonBorder;
                              e.currentTarget.style.backgroundColor = monthButtonBg;
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
              <div className="space-y-2">
                <div className="grid grid-cols-3 gap-1">
                  {years.map((year) => {
                    const selected = isYearSelected(Number(year));
                    return (
                      <button
                        key={year}
                        type="button"
                        onClick={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          handleYearSelect(Number(year));
                        }}
                        className="rounded-lg border p-1 font-medium transition-all duration-200"
                        style={{
                          borderColor: selected ? '#3b82f6' : monthButtonBorder,
                          fontSize: `${buttonFontSize}px`,
                          backgroundColor: selected ? selectedButtonBg : monthButtonBg,
                          color: selected ? selectedButtonText : monthButtonText,
                          boxShadow: selected 
                            ? theme === 'dark' 
                              ? '0 4px 6px -1px rgba(59, 130, 246, 0.2)' 
                              : '0 2px 4px -1px rgba(59, 130, 246, 0.1)'
                            : 'none',
                        }}
                        onMouseEnter={(e) => {
                          if (!selected) {
                            e.currentTarget.style.borderColor = 'rgba(59, 130, 246, 0.5)';
                            e.currentTarget.style.backgroundColor = theme === 'dark' 
                              ? 'rgba(51, 65, 85, 0.8)' 
                              : 'rgba(241, 245, 249, 0.9)';
                          }
                        }}
                        onMouseLeave={(e) => {
                          if (!selected) {
                            e.currentTarget.style.borderColor = monthButtonBorder;
                            e.currentTarget.style.backgroundColor = monthButtonBg;
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
              <div className="space-y-2">
                {/* Instruction Text */}
                <div className="py-0.5 text-center" style={{ color: instructionText, fontSize: `${buttonFontSize}px` }}>
                  {!tempRangeStart
                    ? 'Select start month'
                    : !tempRangeEnd
                    ? 'Select end month'
                    : `${formatMonthShort(tempRangeStart)} – ${formatMonthShort(tempRangeEnd)}`}
                </div>

                {/* Month Grid */}
                <div className="grid grid-cols-3 gap-1">
                  {availableMonths.map((month) => {
                    const monthNum = Number(month.split('-')[1]);
                    const monthAbbr = MONTH_ABBREVIATIONS[monthNum - 1] || `M${monthNum}`;
                    const isStart = isRangeStart(month);
                    const isEnd = isRangeEnd(month);
                    const inRange = isInRange(month);
                    const isDisabled = isRangeDisabled(month);

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
                        className="rounded-lg border p-1 font-medium transition-all duration-200"
                        style={{
                          cursor: isDisabled ? 'not-allowed' : 'pointer',
                          fontSize: `${buttonFontSize}px`,
                          opacity: isDisabled ? 0.5 : 1,
                          borderColor: isStart || isEnd 
                            ? '#3b82f6' 
                            : inRange 
                            ? 'rgba(59, 130, 246, 0.5)' 
                            : isDisabled
                            ? monthButtonBorder
                            : monthButtonBorder,
                          backgroundColor: isStart || isEnd 
                            ? theme === 'dark' ? 'rgba(59, 130, 246, 0.4)' : 'rgba(59, 130, 246, 0.2)'
                            : inRange 
                            ? theme === 'dark' ? 'rgba(59, 130, 246, 0.15)' : 'rgba(59, 130, 246, 0.08)'
                            : isDisabled
                            ? disabledButtonBg
                            : monthButtonBg,
                          color: isStart || isEnd 
                            ? selectedButtonText
                            : inRange
                            ? theme === 'dark' ? '#93c5fd' : '#1e40af'
                            : isDisabled
                            ? disabledButtonText
                            : monthButtonText,
                          boxShadow: (isStart || isEnd)
                            ? theme === 'dark' 
                              ? '0 4px 6px -1px rgba(59, 130, 246, 0.2)' 
                              : '0 2px 4px -1px rgba(59, 130, 246, 0.1)'
                            : 'none',
                        }}
                        onMouseEnter={(e) => {
                          if (!isDisabled && !isStart && !isEnd && !inRange) {
                            e.currentTarget.style.borderColor = 'rgba(59, 130, 246, 0.5)';
                            e.currentTarget.style.backgroundColor = theme === 'dark' 
                              ? 'rgba(51, 65, 85, 0.8)' 
                              : 'rgba(241, 245, 249, 0.9)';
                          }
                        }}
                        onMouseLeave={(e) => {
                          if (!isDisabled && !isStart && !isEnd && !inRange) {
                            e.currentTarget.style.borderColor = monthButtonBorder;
                            e.currentTarget.style.backgroundColor = monthButtonBg;
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
                    className="w-full rounded-lg border border-blue-500 bg-blue-600/20 px-2 py-1 font-semibold text-blue-200 transition-all duration-200 hover:bg-blue-600/30 hover:shadow-md hover:shadow-blue-500/20"
                    style={{ fontSize: `${buttonFontSize}px` }}
                  >
                    Apply Range
                  </button>
                )}
              </div>
            )}
          </div>

          {/* Footer Buttons */}
          <div 
            className="flex gap-1 border-t p-2"
            style={{
              borderColor: footerBorder,
              backgroundColor: footerBg,
            }}
          >
            {(['Clear', 'Close'] as const).map((action) => (
            <button
                key={action}
              type="button"
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                  if (action === 'Clear') handleClear();
                  else handleClose();
              }}
                className="flex-1 rounded-lg border px-2 py-1 font-semibold transition-all duration-200"
                style={{
                  borderColor: footerButtonBorder,
                  fontSize: `${buttonFontSize}px`,
                  backgroundColor: footerButtonBg,
                  color: footerButtonText,
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = theme === 'dark' ? 'rgba(71, 85, 105, 0.6)' : 'rgba(203, 213, 225, 0.6)';
                  e.currentTarget.style.backgroundColor = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(241, 245, 249, 0.9)';
                  e.currentTarget.style.color = theme === 'dark' ? '#e2e8f0' : '#334155';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = footerButtonBorder;
                  e.currentTarget.style.backgroundColor = footerButtonBg;
                  e.currentTarget.style.color = footerButtonText;
                }}
              >
                {action}
            </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

