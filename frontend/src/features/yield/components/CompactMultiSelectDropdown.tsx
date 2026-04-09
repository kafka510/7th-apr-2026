import type { ReactNode } from 'react';
import { useEffect, useMemo, useRef, useState } from 'react';
import { useTheme } from '../../../contexts/ThemeContext';
import { useResponsiveFontSize } from '../../../utils/fontScaling';

type CompactMultiSelectDropdownProps = {
  label: string;
  options: string[];
  selected: string[];
  placeholder?: string;
  onChange: (values: string[]) => void;
  icon?: ReactNode;
  disabled?: boolean;
  optionFormatter?: (value: string) => string;
};

export const CompactMultiSelectDropdown = ({
  label,
  options,
  selected,
  placeholder = 'All',
  onChange,
  icon,
  disabled = false,
  optionFormatter,
}: CompactMultiSelectDropdownProps) => {
  const { theme } = useTheme();
  
  // Responsive font sizes (scaled up by 1.25x)
  const FONT_SCALE = 1.25;
  const labelFontSize = useResponsiveFontSize(8, 12, 7) * FONT_SCALE;
  const bodyFontSize = useResponsiveFontSize(10, 14, 9) * FONT_SCALE;
  const buttonFontSize = useResponsiveFontSize(11, 15, 10) * FONT_SCALE;
  
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState('');
  const containerRef = useRef<HTMLDivElement | null>(null);
  const searchInputRef = useRef<HTMLInputElement | null>(null);

  const toggleOption = (value: string) => {
    if (selected.includes(value)) {
      onChange(selected.filter((item) => item !== value));
    } else {
      onChange([...selected, value]);
    }
  };

  const handleSelectAll = () => {
    if (selected.length === options.length) {
      onChange([]);
    } else {
      onChange(options);
    }
  };

  const handleClear = () => {
    onChange([]);
    setSearch('');
  };

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    window.addEventListener('mousedown', handleClickOutside);
    return () => {
      window.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  useEffect(() => {
    if (isOpen && searchInputRef.current) {
      searchInputRef.current.focus();
    }
  }, [isOpen]);

  const filteredOptions = useMemo(() => {
    if (!search) {
      return options;
    }
    const lowerSearch = search.toLowerCase();
    return options.filter((option) =>
      option.toLowerCase().includes(lowerSearch),
    );
  }, [options, search]);

  const summary = useMemo(() => {
    if (selected.length === 0) {
      return placeholder;
    }
    if (selected.length <= 2) {
      return selected.map((val) => optionFormatter ? optionFormatter(val) : val).join(', ');
    }
    return `${selected.length} selected`;
  }, [placeholder, selected, optionFormatter]);

  // Theme-aware colors
  const isDark = theme === 'dark';
  const labelColor = isDark ? '#94a3b8' : '#718096';
  const triggerBg = isDark ? 'rgba(15, 23, 42, 0.8)' : '#ffffff';
  const triggerBorder = isDark ? 'rgba(51, 65, 85, 0.7)' : 'rgba(203, 213, 225, 0.7)';
  const triggerText = isDark ? '#e2e8f0' : '#1a1a1a';
  const triggerArrowColor = isDark ? '#94a3b8' : '#718096';
  const dropdownBg = isDark ? 'rgba(2, 6, 23, 0.95)' : '#ffffff';
  const dropdownBorder = isDark ? 'rgba(30, 41, 59, 1)' : 'rgba(226, 232, 240, 1)';
  const headerBg = isDark ? 'rgba(15, 23, 42, 0.8)' : '#f8fafc';
  const headerBorder = isDark ? 'rgba(30, 41, 59, 1)' : 'rgba(226, 232, 240, 1)';
  const headerText = isDark ? '#cbd5e0' : '#1a1a1a';
  const inputBg = isDark ? 'rgba(15, 23, 42, 0.6)' : '#ffffff';
  const inputText = isDark ? '#e2e8f0' : '#1a1a1a';
  const buttonBg = isDark ? 'rgba(30, 41, 59, 1)' : '#ffffff';
  const buttonBorder = isDark ? 'rgba(51, 65, 85, 1)' : 'rgba(203, 213, 225, 1)';
  const buttonText = isDark ? '#e2e8f0' : '#1a1a1a';
  const optionBg = isDark ? 'rgba(0, 114, 206, 0.2)' : 'rgba(0, 114, 206, 0.1)';
  const optionText = isDark ? '#93c5fd' : '#0072ce';
  const optionHoverBg = isDark ? 'rgba(30, 41, 59, 0.7)' : '#f1f5f9';
  const optionNormalText = isDark ? '#e2e8f0' : '#1a1a1a';
  const noMatchesText = isDark ? '#64748b' : '#94a3b8';
  const checkboxBorder = isDark ? '#475569' : '#cbd5e0';
  const checkboxBg = isDark ? 'rgba(15, 23, 42, 1)' : '#ffffff';

  return (
    <div ref={containerRef} className="relative space-y-0.5" style={{ position: 'relative', overflow: 'visible' }}>
      <div 
        className="flex items-center gap-0.5 font-semibold uppercase tracking-wide"
        style={{ color: labelColor, fontSize: `${labelFontSize}px` }}
      >
        {icon ? <span style={{ fontSize: `${bodyFontSize}px` }}>{icon}</span> : null}
        <span>{label}</span>
      </div>

      <button
        type="button"
        disabled={disabled}
        onClick={() => setIsOpen((prev) => !prev)}
        className="flex w-full items-center justify-between rounded-lg px-1.5 py-0.5 text-left font-medium shadow-inner transition disabled:cursor-not-allowed disabled:opacity-50"
        style={{
          fontSize: `${bodyFontSize}px`,
          border: `1px solid ${triggerBorder}`,
          backgroundColor: triggerBg,
          color: triggerText,
          boxShadow: isDark ? 'inset 0 2px 4px rgba(0, 0, 0, 0.4)' : 'inset 0 2px 4px rgba(0, 0, 0, 0.1)',
        }}
        onMouseEnter={(e) => {
          if (!disabled) {
            e.currentTarget.style.borderColor = '#0072ce';
          }
        }}
        onMouseLeave={(e) => {
          if (!disabled) {
            e.currentTarget.style.borderColor = triggerBorder;
          }
        }}
      >
        <span className="truncate break-words">{summary}</span>
        <span className="ml-2" style={{ color: triggerArrowColor, fontSize: `${labelFontSize}px` }}>{isOpen ? '▲' : '▼'}</span>
      </button>

      {isOpen && !disabled ? (
        <div 
          className="absolute z-[9999] mt-1 flex flex-col rounded-xl backdrop-blur-md" 
          style={{ 
            width: 'max(100%, 400px)', 
            maxWidth: '600px', 
            maxHeight: '500px', 
            minHeight: '300px',
            border: `1px solid ${dropdownBorder}`,
            backgroundColor: dropdownBg,
            boxShadow: isDark 
              ? '0 20px 25px -5px rgba(0, 0, 0, 0.7), 0 10px 10px -5px rgba(0, 0, 0, 0.4)'
              : '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
          }}
        >
          <div 
            className="flex shrink-0 items-center gap-2 px-3 py-2 text-xs"
            style={{
              borderBottom: `1px solid ${headerBorder}`,
              backgroundColor: headerBg,
              color: headerText,
            }}
          >
            <input
              ref={searchInputRef}
              type="text"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search…"
              className="w-full rounded-md px-2 py-1 text-sm focus:outline-none focus:ring-1"
              style={{
                backgroundColor: inputBg,
                color: inputText,
                border: `1px solid ${isDark ? 'rgba(51, 65, 85, 0.5)' : 'rgba(203, 213, 225, 0.5)'}`,
              }}
              onFocus={(e) => {
                e.currentTarget.style.borderColor = '#0072ce';
                e.currentTarget.style.boxShadow = '0 0 0 1px rgba(0, 114, 206, 0.3)';
              }}
              onBlur={(e) => {
                e.currentTarget.style.borderColor = isDark ? 'rgba(51, 65, 85, 0.5)' : 'rgba(203, 213, 225, 0.5)';
                e.currentTarget.style.boxShadow = 'none';
              }}
            />
            <button
              type="button"
              onClick={handleSelectAll}
              className="whitespace-nowrap rounded-md border px-2 py-1 font-semibold uppercase tracking-wide transition"
              style={{
                fontSize: `${buttonFontSize}px`,
                border: `1px solid ${buttonBorder}`,
                backgroundColor: buttonBg,
                color: buttonText,
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = '#0072ce';
                e.currentTarget.style.color = '#0072ce';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = buttonBorder;
                e.currentTarget.style.color = buttonText;
              }}
            >
              {selected.length === options.length ? 'Clear All' : 'Select All'}
            </button>
            {selected.length > 0 ? (
              <button
                type="button"
                onClick={handleClear}
                className="whitespace-nowrap rounded-md border border-transparent px-2 py-1 font-semibold uppercase tracking-wide transition"
                style={{
                  fontSize: `${buttonFontSize}px`,
                  color: isDark ? '#94a3b8' : '#718096',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.color = buttonText;
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.color = isDark ? '#94a3b8' : '#718096';
                }}
              >
                Reset
              </button>
            ) : null}
          </div>

          <div className="min-h-0 flex-1 overflow-y-auto px-1 py-2" style={{ maxHeight: 'calc(100vh - 280px)' }}>
            {filteredOptions.length === 0 ? (
              <div className="px-3 py-2 text-xs" style={{ color: noMatchesText }}>No matches</div>
            ) : (
              filteredOptions.map((option) => {
                const isSelected = selected.includes(option);
                return (
                  <label
                    key={option}
                    className="flex cursor-pointer items-center gap-2 rounded-lg px-3 py-2 text-sm transition"
                    style={{
                      backgroundColor: isSelected ? optionBg : 'transparent',
                      color: isSelected ? optionText : optionNormalText,
                    }}
                    onMouseEnter={(e) => {
                      if (!isSelected) {
                        e.currentTarget.style.backgroundColor = optionHoverBg;
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (!isSelected) {
                        e.currentTarget.style.backgroundColor = 'transparent';
                      }
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => toggleOption(option)}
                      className="size-3.5 rounded focus:ring-1"
                      style={{
                        border: `1px solid ${checkboxBorder}`,
                        backgroundColor: checkboxBg,
                        accentColor: '#0072ce',
                      }}
                    />
                    <span className="flex-1 whitespace-normal break-words">{optionFormatter ? optionFormatter(option) : option}</span>
                  </label>
                );
              })
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
};

