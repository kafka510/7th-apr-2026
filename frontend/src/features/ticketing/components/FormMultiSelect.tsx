import { useEffect, useMemo, useRef, useState } from 'react';
import { useTheme } from '../../../contexts/ThemeContext';

type FormMultiSelectProps = {
  label: string;
  options: Array<{ value: string; label: string }>;
  selected: string[];
  onChange: (values: string[]) => void;
  placeholder?: string;
  disabled?: boolean;
  required?: boolean;
  error?: string;
  singleSelect?: boolean; // If true, only allows one selection and closes dropdown after selection
};

export const FormMultiSelect = ({
  label,
  options,
  selected,
  onChange,
  placeholder = 'Select options',
  disabled = false,
  required = false,
  error,
  singleSelect = false,
}: FormMultiSelectProps) => {
  const { theme } = useTheme();
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState('');
  const containerRef = useRef<HTMLDivElement | null>(null);
  const searchInputRef = useRef<HTMLInputElement | null>(null);
  
  const labelColor = theme === 'dark' ? '#cbd5e1' : '#475569';
  const buttonBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.8)' : '#ffffff';
  const buttonBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : 'rgba(203, 213, 225, 0.8)';
  const buttonText = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';
  const buttonHoverBorder = theme === 'dark' ? '#3b82f6' : '#0072ce';
  const buttonFocusBorder = theme === 'dark' ? '#3b82f6' : '#0072ce';
  const buttonFocusRing = theme === 'dark' ? 'rgba(59, 130, 246, 0.3)' : 'rgba(0, 114, 206, 0.2)';
  const errorBorder = theme === 'dark' ? 'rgba(239, 68, 68, 0.5)' : '#f87171';
  const errorFocusRing = theme === 'dark' ? 'rgba(239, 68, 68, 0.3)' : 'rgba(248, 113, 113, 0.2)';
  const dropdownBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.95)' : '#ffffff';
  const dropdownBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(203, 213, 225, 0.8)';
  const dropdownShadow = theme === 'dark' 
    ? '0 20px 25px -5px rgba(0, 0, 0, 0.5)' 
    : '0 10px 15px -3px rgba(0, 0, 0, 0.1)';
  const searchBarBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.7)' : 'rgba(241, 245, 249, 0.9)';
  const searchBarBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.5)' : 'rgba(226, 232, 240, 0.8)';
  const searchInputBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.8)' : '#ffffff';
  const searchInputBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : 'rgba(203, 213, 225, 0.8)';
  const searchInputText = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';
  const actionButtonBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.8)' : '#ffffff';
  const actionButtonBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : 'rgba(203, 213, 225, 0.8)';
  const actionButtonText = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';
  const actionButtonHoverBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.9)' : '#f8fafc';
  const actionButtonHoverBorder = theme === 'dark' ? '#3b82f6' : '#0072ce';
  const optionText = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';
  const optionSelectedBg = theme === 'dark' ? 'rgba(59, 130, 246, 0.2)' : 'rgba(59, 130, 246, 0.1)';
  const optionSelectedText = theme === 'dark' ? '#93c5fd' : '#1e40af';
  const optionHoverBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.7)' : 'rgba(241, 245, 249, 0.9)';
  const checkboxBorder = theme === 'dark' ? 'rgba(71, 85, 105, 0.6)' : 'rgba(203, 213, 225, 0.7)';
  const checkboxColor = theme === 'dark' ? '#3b82f6' : '#0072ce';
  const noMatchesText = theme === 'dark' ? '#94a3b8' : '#64748b';
  const errorTextColor = theme === 'dark' ? '#fca5a5' : '#dc2626';
  const arrowColor = theme === 'dark' ? '#94a3b8' : '#64748b';
  const secondaryText = theme === 'dark' ? '#94a3b8' : '#64748b';

  const toggleOption = (value: string) => {
    if (singleSelect) {
      // For single-select, replace the selection and close dropdown
      if (selected.includes(value)) {
        onChange([]);
      } else {
        onChange([value]);
      }
      setIsOpen(false);
    } else {
      // For multi-select, toggle the selection and auto-close after selection
      if (selected.includes(value)) {
        onChange(selected.filter((item) => item !== value));
      } else {
        onChange([...selected, value]);
      }
      // Auto-close dropdown after each selection in multi-select mode
      setIsOpen(false);
    }
  };

  const handleSelectAll = () => {
    if (selected.length === options.length) {
      onChange([]);
    } else {
      onChange(options.map((opt) => opt.value));
    }
    // Auto-close dropdown after select all
    setIsOpen(false);
  };

  const handleClear = () => {
    onChange([]);
    setSearch('');
    // Auto-close dropdown after clear
    setIsOpen(false);
  };

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
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
    return options.filter((option) => option.label.toLowerCase().includes(lowerSearch));
  }, [options, search]);

  const summary = useMemo(() => {
    if (selected.length === 0) {
      return placeholder;
    }
    if (singleSelect) {
      // For single-select, show the selected option label
      const opt = options.find((o) => o.value === selected[0]);
      return opt ? opt.label : selected[0];
    }
    if (selected.length === options.length) {
      return 'All selected';
    }
    if (selected.length <= 2) {
      return selected
        .map((val) => {
          const opt = options.find((o) => o.value === val);
          return opt ? opt.label : val;
        })
        .join(', ');
    }
    return `${selected.length} selected`;
  }, [placeholder, selected, options, singleSelect]);

  const allSelected = selected.length === options.length && options.length > 0;

  return (
    <div ref={containerRef} className="relative" style={{ zIndex: isOpen ? 99999 : 'auto' }}>
      <label 
        className="block text-xs font-semibold"
        style={{ color: labelColor }}
      >
        {label} {required && <span style={{ color: errorTextColor }}>*</span>}
      </label>
      <button
        type="button"
        disabled={disabled}
        onClick={() => setIsOpen((prev) => !prev)}
        className="mt-1 flex w-full items-center justify-between rounded-lg border px-2 py-1.5 text-left text-sm shadow-sm transition disabled:cursor-not-allowed disabled:opacity-50"
        style={{
          backgroundColor: buttonBg,
          borderColor: error ? errorBorder : (isOpen ? buttonFocusBorder : buttonBorder),
          color: buttonText,
          boxShadow: isOpen ? `0 0 0 2px ${error ? errorFocusRing : buttonFocusRing}` : (theme === 'dark' ? 'inset 0 2px 4px rgba(0, 0, 0, 0.3)' : 'inset 0 1px 2px rgba(0, 0, 0, 0.05)'),
        }}
        onMouseEnter={(e) => {
          if (!disabled && !error) {
            e.currentTarget.style.borderColor = buttonHoverBorder;
          }
        }}
        onMouseLeave={(e) => {
          if (!disabled && !error) {
            e.currentTarget.style.borderColor = isOpen ? buttonFocusBorder : buttonBorder;
          }
        }}
        onFocus={(e) => {
          if (!disabled) {
            e.currentTarget.style.borderColor = error ? errorBorder : buttonFocusBorder;
            e.currentTarget.style.boxShadow = `0 0 0 2px ${error ? errorFocusRing : buttonFocusRing}`;
          }
        }}
        onBlur={(e) => {
          if (!disabled) {
            e.currentTarget.style.borderColor = error ? errorBorder : buttonBorder;
            e.currentTarget.style.boxShadow = theme === 'dark' ? 'inset 0 2px 4px rgba(0, 0, 0, 0.3)' : 'inset 0 1px 2px rgba(0, 0, 0, 0.05)';
          }
        }}
      >
        <span className="truncate">{summary}</span>
        <span 
          className="ml-2 text-xs"
          style={{ color: arrowColor }}
        >
          {isOpen ? '▲' : '▼'}
        </span>
      </button>
      {error && (
        <p 
          className="mt-0.5 text-xs"
          style={{ color: errorTextColor }}
        >
          {error}
        </p>
      )}

      {isOpen && !disabled && (
        <div
          className="absolute inset-x-0 top-full z-[99999] mt-1 flex w-full flex-col rounded-lg border shadow-xl"
          style={{ 
            maxHeight: '300px',
            backgroundColor: dropdownBg,
            borderColor: dropdownBorder,
            boxShadow: dropdownShadow,
          }}
        >
          <div 
            className="flex shrink-0 items-center gap-2 border-b px-3 py-2"
            style={{
              borderColor: searchBarBorder,
              backgroundColor: searchBarBg,
            }}
          >
            <input
              ref={searchInputRef}
              type="text"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search…"
              className="w-full rounded border px-2 py-1 text-xs focus:outline-none focus:ring-1"
              style={{
                backgroundColor: searchInputBg,
                borderColor: searchInputBorder,
                color: searchInputText,
                boxShadow: theme === 'dark' ? 'inset 0 2px 4px rgba(0, 0, 0, 0.3)' : 'inset 0 1px 2px rgba(0, 0, 0, 0.05)',
              }}
              onFocus={(e) => {
                e.currentTarget.style.borderColor = buttonFocusBorder;
                e.currentTarget.style.boxShadow = `0 0 0 1px ${buttonFocusRing}`;
              }}
              onBlur={(e) => {
                e.currentTarget.style.borderColor = searchInputBorder;
                e.currentTarget.style.boxShadow = theme === 'dark' ? 'inset 0 2px 4px rgba(0, 0, 0, 0.3)' : 'inset 0 1px 2px rgba(0, 0, 0, 0.05)';
              }}
            />
            <style>{`
              input[type="text"]::placeholder {
                color: ${theme === 'dark' ? '#64748b' : '#94a3b8'};
              }
            `}</style>
            {!singleSelect && (
              <>
                <button
                  type="button"
                  onClick={handleSelectAll}
                  className="whitespace-nowrap rounded border px-2 py-1 text-xs font-semibold transition"
                  style={{
                    backgroundColor: actionButtonBg,
                    borderColor: actionButtonBorder,
                    color: actionButtonText,
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = actionButtonHoverBorder;
                    e.currentTarget.style.backgroundColor = actionButtonHoverBg;
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = actionButtonBorder;
                    e.currentTarget.style.backgroundColor = actionButtonBg;
                  }}
                >
                  {allSelected ? 'Clear All' : 'Select All'}
                </button>
                {selected.length > 0 && (
                  <button
                    type="button"
                    onClick={handleClear}
                    className="whitespace-nowrap rounded border border-transparent px-2 py-1 text-xs font-semibold transition"
                    style={{
                      color: secondaryText,
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.color = optionText;
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.color = secondaryText;
                    }}
                  >
                    Reset
                  </button>
                )}
              </>
            )}
          </div>

          <div className="min-h-0 flex-1 overflow-y-auto px-1 py-2" style={{ maxHeight: '250px' }}>
            {filteredOptions.length === 0 ? (
              <div 
                className="px-3 py-2 text-xs"
                style={{ color: noMatchesText }}
              >
                No matches
              </div>
            ) : (
              filteredOptions.map((option) => {
                const isSelected = selected.includes(option.value);
                return (
                  <label
                    key={option.value}
                    className="flex cursor-pointer items-center gap-2 rounded px-2 py-1.5 text-sm transition"
                    style={{
                      backgroundColor: isSelected ? optionSelectedBg : 'transparent',
                      color: isSelected ? optionSelectedText : optionText,
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
                      onChange={() => toggleOption(option.value)}
                      className="size-4 rounded focus:ring-1"
                      style={{
                        borderColor: checkboxBorder,
                        accentColor: checkboxColor,
                      }}
                    />
                    <span className="flex-1">{option.label}</span>
                  </label>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
};

