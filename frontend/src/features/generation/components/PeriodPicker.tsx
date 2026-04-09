/**
 * Period Picker Component - Month/Year Range Selector
 * Replicates BestCalendar functionality for React
 */
import { useState, useRef, useEffect } from 'react';
import { useTheme } from '../../../contexts/ThemeContext';
import { useResponsiveFontSize } from '../../../utils/fontScaling';

export interface Period {
  month?: string; // YYYY-MM format
  range?: {
    start: string; // YYYY-MM format
    end: string; // YYYY-MM format
  };
}

interface PeriodPickerProps {
  defaultPeriod?: Period;
  onPeriodChange: (period: Period) => void;
  onReset?: () => void;
}

export function PeriodPicker({
  defaultPeriod,
  onPeriodChange,
  onReset,
}: PeriodPickerProps) {
  const { theme } = useTheme();
  const [isOpen, setIsOpen] = useState(false);
  
  // Responsive font sizes (increased by 1.5x for filter pane)
  const buttonFontSize = useResponsiveFontSize(15, 21, 13.5); // For main button
  const smallFontSize = useResponsiveFontSize(8, 12, 7); // For small text like dropdown arrow
  const monthButtonFontSize = useResponsiveFontSize(9, 13, 8); // For month buttons
  const actionButtonFontSize = useResponsiveFontSize(9, 13, 8); // For action buttons
  
  // Theme-aware colors
  const buttonBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.8)' : '#ffffff';
  const buttonBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : 'rgba(203, 213, 225, 0.8)';
  const buttonText = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';
  const buttonHoverBorder = theme === 'dark' ? '#38bdf8' : '#0072ce';
  const dropdownBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.95)' : '#ffffff';
  const dropdownBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(203, 213, 225, 0.8)';
  const dropdownShadow = theme === 'dark' 
    ? '0 20px 25px -5px rgba(0, 0, 0, 0.5)' 
    : '0 10px 15px -3px rgba(0, 0, 0, 0.1)';
  const yearText = theme === 'dark' ? '#38bdf8' : '#0072ce';
  const navButtonText = theme === 'dark' ? '#cbd5e1' : '#475569';
  const navButtonHoverBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.7)' : 'rgba(241, 245, 249, 0.9)';
  const monthButtonBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.8)' : 'rgba(241, 245, 249, 0.9)';
  const monthButtonText = theme === 'dark' ? '#cbd5e1' : '#475569';
  const monthButtonHoverBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.9)' : 'rgba(226, 232, 240, 0.9)';
  const monthSelectedBg = theme === 'dark' ? 'rgba(56, 189, 248, 0.2)' : 'rgba(0, 114, 206, 0.1)';
  const monthSelectedText = theme === 'dark' ? '#7dd3fc' : '#0072ce';
  const monthSelectedHoverBg = theme === 'dark' ? 'rgba(56, 189, 248, 0.3)' : 'rgba(0, 114, 206, 0.15)';
  const dividerBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(226, 232, 240, 0.8)';
  const resetButtonText = theme === 'dark' ? '#cbd5e1' : '#64748b';
  const resetButtonHoverBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.7)' : 'rgba(241, 245, 249, 0.9)';
  const applyButtonBg = theme === 'dark' ? '#3b82f6' : '#0072ce';
  const applyButtonHoverBg = theme === 'dark' ? '#2563eb' : '#0056a3';
  const [selectedYear, setSelectedYear] = useState(() => {
    const yearStr = defaultPeriod?.range?.start?.split('-')[0] || 
                    defaultPeriod?.month?.split('-')[0] || 
                    String(new Date().getFullYear());
    return parseInt(String(yearStr), 10);
  });
  const [selectedRange, setSelectedRange] = useState<{ start: number; end: number } | null>(() => {
    if (defaultPeriod?.range) {
      const startMonth = parseInt(defaultPeriod.range.start.split('-')[1], 10);
      const endMonth = parseInt(defaultPeriod.range.end.split('-')[1], 10);
      return { start: startMonth, end: endMonth };
    } else if (defaultPeriod?.month) {
      const month = parseInt(defaultPeriod.month.split('-')[1], 10);
      return { start: month, end: month };
    }
    // Default: full year
    return { start: 1, end: 12 };
  });
  const [selectedMonth, setSelectedMonth] = useState<number | null>(null);
  const pickerRef = useRef<HTMLDivElement>(null);

  // Close picker when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (pickerRef.current && !pickerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [isOpen]);

  const months = [
    'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
  ];

  const handleMonthClick = (monthNum: number) => {
    if (selectedRange) {
      // Range mode: update range
      if (selectedRange.start === null || monthNum < selectedRange.start) {
        setSelectedRange({ start: monthNum, end: selectedRange.end });
      } else if (monthNum > selectedRange.end) {
        setSelectedRange({ start: selectedRange.start, end: monthNum });
      } else {
        // Clicked within range, start new range
        setSelectedRange({ start: monthNum, end: monthNum });
      }
    } else {
      // Single month mode
      setSelectedMonth(monthNum);
    }
  };

  const handleApply = () => {
    if (selectedRange) {
      const startMonth = `${selectedYear}-${String(selectedRange.start).padStart(2, '0')}`;
      const endMonth = `${selectedYear}-${String(selectedRange.end).padStart(2, '0')}`;
      onPeriodChange({ range: { start: startMonth, end: endMonth } });
    } else if (selectedMonth !== null) {
      const month = `${selectedYear}-${String(selectedMonth).padStart(2, '0')}`;
      onPeriodChange({ month });
    }
    setIsOpen(false);
  };

  const handleReset = () => {
    const currentYear = new Date().getFullYear();
    setSelectedYear(currentYear);
    setSelectedRange({ start: 1, end: 12 });
    setSelectedMonth(null);
    onPeriodChange({ range: { start: `${currentYear}-01`, end: `${currentYear}-12` } });
    if (onReset) onReset();
  };

  const getLabel = (): string => {
    if (selectedRange) {
      if (selectedRange.start === selectedRange.end) {
        return `${months[selectedRange.start - 1]} ${selectedYear}`;
      }
      return `${months[selectedRange.start - 1]} - ${months[selectedRange.end - 1]} ${selectedYear}`;
    } else if (selectedMonth !== null) {
      return `${months[selectedMonth - 1]} ${selectedYear}`;
    }
    return 'Select Period';
  };

  return (
    <div className="relative inline-block" ref={pickerRef}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center justify-between gap-2 rounded-lg border px-2 py-1 font-medium transition focus:outline-none focus:ring-1"
        style={{ 
          minWidth: '160px',
          backgroundColor: buttonBg,
          borderColor: buttonBorder,
          color: buttonText,
          fontSize: `${buttonFontSize}px`,
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.borderColor = buttonHoverBorder;
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.borderColor = buttonBorder;
        }}
        onFocus={(e) => {
          e.currentTarget.style.borderColor = buttonHoverBorder;
          e.currentTarget.style.outline = 'none';
          e.currentTarget.style.boxShadow = `0 0 0 1px ${buttonHoverBorder}`;
        }}
        onBlur={(e) => {
          e.currentTarget.style.borderColor = buttonBorder;
          e.currentTarget.style.boxShadow = 'none';
        }}
      >
        <span>{getLabel()}</span>
        <span style={{ fontSize: `${smallFontSize}px` }}>▼</span>
      </button>

      {isOpen && (
        <div 
          className="absolute left-0 top-full z-50 mt-1 flex flex-col gap-3 rounded-xl border p-4 shadow-2xl backdrop-blur-md"
          style={{
            backgroundColor: dropdownBg,
            borderColor: dropdownBorder,
            boxShadow: dropdownShadow,
          }}
        >
          {/* Year Selector */}
          <div className="flex items-center justify-center gap-2">
            <button
              type="button"
              onClick={() => setSelectedYear(selectedYear - 1)}
              className="rounded px-2 py-1 text-sm transition-colors"
              style={{
                color: navButtonText,
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = navButtonHoverBg;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = 'transparent';
              }}
            >
              ‹
            </button>
            <span className="min-w-[80px] text-center font-semibold" style={{ color: yearText, fontSize: `${buttonFontSize + 2}px` }}>{selectedYear}</span>
            <button
              type="button"
              onClick={() => setSelectedYear(selectedYear + 1)}
              className="rounded px-2 py-1 text-sm transition-colors"
              style={{
                color: navButtonText,
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = navButtonHoverBg;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = 'transparent';
              }}
            >
              ›
            </button>
          </div>

          {/* Month Grid */}
          <div className="grid grid-cols-3 gap-2">
            {months.map((month, index) => {
              const monthNum = index + 1;
              const isInRange =
                selectedRange &&
                monthNum >= selectedRange.start &&
                monthNum <= selectedRange.end;
              const isSelected = selectedMonth === monthNum || isInRange;

              return (
                <button
                  key={month}
                  type="button"
                  onClick={() => handleMonthClick(monthNum)}
                  className="rounded px-3 py-1.5 transition-colors"
                  style={{
                    backgroundColor: isSelected ? monthSelectedBg : monthButtonBg,
                    color: isSelected ? monthSelectedText : monthButtonText,
                    fontSize: `${monthButtonFontSize}px`,
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.backgroundColor = isSelected ? monthSelectedHoverBg : monthButtonHoverBg;
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = isSelected ? monthSelectedBg : monthButtonBg;
                  }}
                >
                  {month}
                </button>
              );
            })}
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-2 border-t pt-3" style={{ borderColor: dividerBorder }}>
            <button
              type="button"
              onClick={handleReset}
              className="rounded px-3 py-1.5 font-semibold uppercase tracking-wide transition-colors"
              style={{
                color: resetButtonText,
                fontSize: `${actionButtonFontSize}px`,
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = resetButtonHoverBg;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = 'transparent';
              }}
            >
              Reset
            </button>
            <button
              type="button"
              onClick={handleApply}
              className="rounded px-4 py-1.5 font-semibold uppercase tracking-wide text-white transition-colors"
              style={{
                backgroundColor: applyButtonBg,
                fontSize: `${actionButtonFontSize}px`,
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = applyButtonHoverBg;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = applyButtonBg;
              }}
            >
              Apply
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

