import type { CSSProperties, ReactNode } from 'react';
import { useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Check } from 'lucide-react';
import { useTheme } from '../../../contexts/ThemeContext';

type MultiSelectDropdownProps = {
  label: string;
  options: string[];
  selected: string[];
  placeholder?: string;
  onChange: (values: string[]) => void;
  icon?: ReactNode;
  disabled?: boolean;
  optionFormatter?: (value: string) => string;
};

export const MultiSelectDropdown = ({
  label,
  options,
  selected,
  placeholder = 'All',
  onChange,
  icon,
  disabled = false,
  optionFormatter,
}: MultiSelectDropdownProps) => {
  const { theme } = useTheme();

  // Fixed enterprise font sizes
  const labelFontSize = 11;  // px — field label
  const bodyFontSize = 13;   // px — trigger text
  const buttonFontSize = 12; // px — dropdown action buttons
  
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [dropdownPos, setDropdownPos] = useState<CSSProperties>({});
  const containerRef = useRef<HTMLDivElement | null>(null);
  const triggerRef = useRef<HTMLButtonElement | null>(null);
  const dropdownRef = useRef<HTMLDivElement | null>(null);
  const searchInputRef = useRef<HTMLInputElement | null>(null);

  const labelColor = theme === 'dark' ? '#94a3b8' : '#64748b';
  const buttonBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.8)' : '#ffffff';
  const buttonBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : 'rgba(203, 213, 225, 0.7)';
  const buttonText = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';
  const dropdownBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.95)' : 'rgba(255, 255, 255, 0.98)';
  const dropdownBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(203, 213, 225, 0.8)';
  const headerBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.8)' : 'rgba(248, 250, 252, 0.9)';
  const headerBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(226, 232, 240, 0.8)';
  const headerText = theme === 'dark' ? '#cbd5e1' : '#475569';
  const searchInputBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.6)' : 'rgba(241, 245, 249, 0.8)';
  const searchInputText = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';
  const selectAllButtonBg = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(241, 245, 249, 0.8)';
  const selectAllButtonBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : 'rgba(203, 213, 225, 0.7)';
  const selectAllButtonText = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';
  const optionText = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';
  const optionHoverBg = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : 'rgba(241, 245, 249, 0.8)';
  const selectedOptionBg = theme === 'dark' ? 'rgba(59, 130, 246, 0.2)' : 'rgba(59, 130, 246, 0.1)';
  const selectedOptionText = theme === 'dark' ? '#93c5fd' : '#1e40af';
  const noMatchesText = theme === 'dark' ? '#64748b' : '#94a3b8';
  const checkboxBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.8)' : '#ffffff';
  const checkboxBorder = theme === 'dark' ? 'rgba(71, 85, 105, 0.6)' : 'rgba(203, 213, 225, 0.7)';

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
        !containerRef.current.contains(event.target as Node) &&
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };
    window.addEventListener('mousedown', handleClickOutside);
    return () => window.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Recompute portal position whenever the dropdown opens or the page scrolls/resizes
  useEffect(() => {
    if (!isOpen || !triggerRef.current) return;
    const compute = () => {
      if (!triggerRef.current) return;
      const r = triggerRef.current.getBoundingClientRect();
      setDropdownPos({
        position: 'fixed',
        top: r.bottom + 6,
        left: r.left,
        minWidth: Math.max(r.width, 400),
        maxWidth: 600,
        zIndex: 9999,
      });
    };
    compute();
    window.addEventListener('scroll', compute, true);
    window.addEventListener('resize', compute);
    return () => {
      window.removeEventListener('scroll', compute, true);
      window.removeEventListener('resize', compute);
    };
  }, [isOpen]);

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

  return (
    <div ref={containerRef} className="relative space-y-1">
      <div
        className="flex items-center gap-1 font-semibold uppercase tracking-wide"
        style={{ color: labelColor, fontSize: `${labelFontSize}px` }}
      >
        {icon ? <span className="text-xs">{icon}</span> : null}
        <span>{label}</span>
      </div>

      <button
        ref={triggerRef}
        type="button"
        disabled={disabled}
        onClick={() => setIsOpen((prev) => !prev)}
        className="flex w-full items-center justify-between rounded-lg border px-2 py-1 text-left font-medium shadow-inner transition hover:border-[var(--accent-primary)] disabled:cursor-not-allowed disabled:opacity-50"
        style={{
          fontSize: `${bodyFontSize}px`,
          borderColor: buttonBorder,
          backgroundColor: buttonBg,
          color: buttonText,
          boxShadow: theme === 'dark' ? 'inset 0 2px 4px rgba(0, 0, 0, 0.4)' : 'inset 0 2px 4px rgba(0, 0, 0, 0.1)',
        }}
      >
        <span className="truncate break-words">{summary}</span>
        <span className="ml-2" style={{ color: labelColor, fontSize: `${bodyFontSize}px` }}>{isOpen ? '▲' : '▼'}</span>
      </button>

      {isOpen && !disabled ? createPortal(
        <div
          ref={dropdownRef}
          className="flex flex-col rounded-xl border shadow-2xl"
          style={{
            ...dropdownPos,
            maxHeight: '500px',
            minHeight: '300px',
            borderColor: dropdownBorder,
            backgroundColor: dropdownBg,
            boxShadow: theme === 'dark' ? '0 20px 25px -5px rgba(0, 0, 0, 0.7)' : '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
          }}
        >
          <div 
            className="flex shrink-0 items-center gap-1 border-b px-2 py-1"
            style={{
              borderColor: headerBorder,
              fontSize: `${labelFontSize}px`,
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
              className="w-full rounded-md px-1.5 py-0.5 text-xs focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
              style={{
                backgroundColor: searchInputBg,
                color: searchInputText,
              }}
            />
            <button
              type="button"
              onClick={handleSelectAll}
              className="whitespace-nowrap rounded-md border px-1.5 py-0.5 font-semibold uppercase tracking-wide transition hover:border-sky-500"
              style={{
                borderColor: selectAllButtonBorder,
                fontSize: `${buttonFontSize}px`,
                backgroundColor: selectAllButtonBg,
                color: selectAllButtonText,
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.color = theme === 'dark' ? '#ffffff' : '#1a1a1a';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.color = selectAllButtonText;
              }}
            >
              {selected.length === options.length ? 'Clear All' : 'Select All'}
            </button>
            {selected.length > 0 ? (
              <button
                type="button"
                onClick={handleClear}
                className="whitespace-nowrap rounded-md border border-transparent px-1.5 py-0.5 font-semibold uppercase tracking-wide transition"
                style={{
                  color: labelColor,
                  fontSize: `${buttonFontSize}px`,
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.color = theme === 'dark' ? '#ffffff' : '#1a1a1a';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.color = labelColor;
                }}
              >
                Reset
              </button>
            ) : null}
          </div>

          <div className="min-h-0 flex-1 overflow-y-auto px-0.5 py-1" style={{ maxHeight: 'calc(100vh - 280px)' }}>
            {filteredOptions.length === 0 ? (
              <div className="px-2 py-1" style={{ color: noMatchesText, fontSize: `${buttonFontSize}px` }}>No matches</div>
            ) : (
              filteredOptions.map((option) => {
                const isSelected = selected.includes(option);
                return (
                  <label
                    key={option}
                    className="flex cursor-pointer items-center gap-2 rounded-lg px-2 py-1 text-xs transition"
                    style={{
                      backgroundColor: isSelected ? selectedOptionBg : 'transparent',
                      color: isSelected ? selectedOptionText : optionText,
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
                    onClick={() => toggleOption(option)}
                  >
                    <span
                      role="checkbox"
                      aria-checked={isSelected}
                      className="flex size-4 shrink-0 items-center justify-center rounded border"
                      style={{
                        borderColor: isSelected ? (theme === 'dark' ? '#3b82f6' : '#0072ce') : checkboxBorder,
                        backgroundColor: isSelected ? (theme === 'dark' ? '#3b82f6' : '#0072ce') : checkboxBg,
                      }}
                    >
                      {isSelected ? <Check className="size-3 text-white" strokeWidth={2.5} /> : null}
                    </span>
                    <span className="flex-1 whitespace-normal break-words">{optionFormatter ? optionFormatter(option) : option}</span>
                  </label>
                );
              })
            )}
          </div>
        </div>,
        document.body
      ) : null}
    </div>
  );
};

