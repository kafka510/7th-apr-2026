import { useMemo, useState, useRef, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { useTheme } from '../../../contexts/ThemeContext';
import { useResponsiveFontSize } from '../../../utils/fontScaling';
import type { BESSFilters, BESSFilterOptions } from '../types';
import { MonthPicker } from '../../yield/components/MonthPicker';

interface BESSFiltersProps {
  filters: BESSFilters;
  options: BESSFilterOptions;
  loading: boolean;
  onFiltersChange: (filters: BESSFilters) => void;
  onReset: () => void;
}

function MultiSelect({
  label,
  icon,
  options,
  selected,
  placeholder,
  onChange,
  disabled,
  minWidth = '180px',
  maxWidth = '280px',
}: {
  label: string;
  icon: string;
  options: string[];
  selected: string[];
  placeholder: string;
  onChange: (values: string[]) => void;
  disabled: boolean;
  minWidth?: string;
  maxWidth?: string;
}) {
  const { theme } = useTheme();
  
  // Responsive font sizes
  const labelFontSize = useResponsiveFontSize(8, 12, 7);
  const bodyFontSize = useResponsiveFontSize(10, 14, 9);
  
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const [dropdownPosition, setDropdownPosition] = useState({ top: 0, left: 0, width: 0 });

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    window.addEventListener('mousedown', handleClickOutside);
    return () => window.removeEventListener('mousedown', handleClickOutside);
  }, []);

  useEffect(() => {
    if (isOpen && buttonRef.current) {
      const rect = buttonRef.current.getBoundingClientRect();
      setDropdownPosition({
        top: rect.bottom + window.scrollY + 2,
        left: rect.left + window.scrollX,
        width: rect.width,
      });
    }
  }, [isOpen]);

  const toggleOption = (value: string) => {
    if (selected.includes(value)) {
      onChange(selected.filter((v) => v !== value));
    } else {
      onChange([...selected, value]);
    }
  };

  const displayText = useMemo(() => {
    if (selected.length === 0) return placeholder;
    if (selected.length === 1) return selected[0];
    return `${selected.length} selected`;
  }, [selected, placeholder]);

  const labelColor = theme === 'dark' ? '#94a3b8' : '#64748b';
  const buttonBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.8)' : '#ffffff';
  const buttonBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : 'rgba(203, 213, 225, 0.8)';
  const buttonText = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';
  const dropdownBg = theme === 'dark' 
    ? 'rgba(15, 23, 42, 0.95)' 
    : 'rgba(255, 255, 255, 0.98)';
  const dropdownBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(203, 213, 225, 0.8)';
  const optionText = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';
  const optionHoverBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.7)' : 'rgba(241, 245, 249, 0.9)';
  const selectedBg = theme === 'dark' ? 'rgba(59, 130, 246, 0.2)' : 'rgba(59, 130, 246, 0.1)';
  const selectedText = theme === 'dark' ? '#93c5fd' : '#1e40af';
  const checkboxBorder = theme === 'dark' ? 'rgba(71, 85, 105, 0.6)' : 'rgba(203, 213, 225, 0.7)';

  return (
    <div style={{ minWidth, maxWidth, flex: '0 0 auto' }}>
      <label 
        className="font-semibold uppercase tracking-wide" 
        style={{ display: 'block', marginBottom: '4px', color: labelColor, fontSize: `${labelFontSize}px` }}
      >
        <span style={{ fontSize: `${bodyFontSize}px` }}>{icon}</span> {label}
      </label>
      <div ref={containerRef} style={{ position: 'relative' }}>
        <button
          ref={buttonRef}
          type="button"
          onClick={() => setIsOpen(!isOpen)}
          disabled={disabled}
          className="font-medium"
          style={{
            width: '100%',
            padding: '6px 12px',
            border: `1px solid ${buttonBorder}`,
            borderRadius: '8px',
            cursor: disabled ? 'not-allowed' : 'pointer',
            textAlign: 'left',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            transition: 'border-color 0.2s',
            backgroundColor: buttonBg,
            color: buttonText,
            fontSize: `${bodyFontSize}px`,
          }}
          onMouseEnter={(e) => {
            if (!disabled) e.currentTarget.style.borderColor = '#3b82f6';
          }}
          onMouseLeave={(e) => {
            if (!disabled) e.currentTarget.style.borderColor = buttonBorder;
          }}
        >
          <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{displayText}</span>
          <span style={{ marginLeft: '8px', fontSize: `${bodyFontSize}px`, color: theme === 'dark' ? '#38bdf8' : '#0072ce' }}>{isOpen ? '▲' : '▼'}</span>
        </button>
        {isOpen && !disabled && createPortal(
          <div
            className="rounded-xl border shadow-2xl backdrop-blur-md"
            style={{
              position: 'absolute',
              top: dropdownPosition.top,
              left: dropdownPosition.left,
              width: dropdownPosition.width,
              zIndex: 999999,
              maxHeight: '250px',
              overflowY: 'auto',
              backgroundColor: dropdownBg,
              borderColor: dropdownBorder,
              boxShadow: theme === 'dark' 
                ? '0 20px 25px -5px rgba(0, 0, 0, 0.5)' 
                : '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
            }}
          >
            {options.map((option) => {
              const isSelected = selected.includes(option);
              return (
                <div
                  key={option}
                  onClick={() => toggleOption(option)}
                  style={{
                    padding: '8px 12px',
                    cursor: 'pointer',
                    fontSize: '0.85rem',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    backgroundColor: isSelected ? selectedBg : 'transparent',
                    color: isSelected ? selectedText : optionText,
                    transition: 'background-color 0.2s',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.backgroundColor = isSelected 
                      ? (theme === 'dark' ? 'rgba(59, 130, 246, 0.3)' : 'rgba(59, 130, 246, 0.15)')
                      : optionHoverBg;
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = isSelected ? selectedBg : 'transparent';
                  }}
                >
                  <div
                    className="size-3.5 rounded"
                    style={{
                      border: `2px solid ${isSelected ? (theme === 'dark' ? '#38bdf8' : '#0072ce') : checkboxBorder}`,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: `${bodyFontSize}px`,
                      fontWeight: 'bold',
                      background: isSelected ? (theme === 'dark' ? '#38bdf8' : '#0072ce') : 'transparent',
                      color: isSelected ? 'white' : 'transparent',
                    }}
                  >
                    {isSelected ? '✓' : ''}
                  </div>
                  <span>{option}</span>
                </div>
              );
            })}
          </div>,
          document.body
        )}
      </div>
    </div>
  );
}

export function BESSFilters({ filters, options, loading, onFiltersChange, onReset }: BESSFiltersProps) {
  const { theme } = useTheme();
  
  // Responsive font sizes
  const labelFontSize = useResponsiveFontSize(8, 12, 7);
  const buttonFontSize = useResponsiveFontSize(9, 13, 8);
  
  const containerBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(203, 213, 225, 0.8)';
  const containerShadow = theme === 'dark' 
    ? '0 20px 25px -5px rgba(0, 0, 0, 0.4)' 
    : '0 10px 15px -3px rgba(0, 0, 0, 0.1)';
  const labelColor = theme === 'dark' ? '#94a3b8' : '#64748b';
  const resetButtonBg = theme === 'dark' ? '#f87171' : '#ef4444';
  const resetButtonHoverBg = theme === 'dark' ? '#ef4444' : '#dc2626';
  const handleCountryChange = (values: string[]) => {
    onFiltersChange({ ...filters, country: values });
  };

  const handlePortfolioChange = (values: string[]) => {
    onFiltersChange({ ...filters, portfolio: values });
  };

  const handleAssetChange = (values: string[]) => {
    onFiltersChange({ ...filters, asset: values });
  };

  // MonthPicker manages state clearing internally, but React batches updates
  // So handlers need to include all fields that MonthPicker sets
  const handleMonthChange = (month: string | null) => {
    onFiltersChange({ 
      ...filters, 
      month,
      // Extract year from month since MonthPicker calls onYearChange(year) but React batches
      year: month ? month.split('-')[0] : filters.year,
      range: null, // MonthPicker clears range when selecting month
    });
  };

  const handleYearChange = (year: string | null) => {
    onFiltersChange({ 
      ...filters, 
      year,
      // MonthPicker clears month and range when year changes
      month: null,
      range: null,
    });
  };

  const handleRangeChange = (range: { start: string; end: string } | null) => {
    onFiltersChange({ 
      ...filters, 
      range,
      // Extract year from range start since MonthPicker calls onYearChange(year) but React batches
      year: range ? range.start.split('-')[0] : filters.year,
      month: null, // MonthPicker clears month when applying range
    });
  };

  const availablePortfolios = useMemo(() => {
    if (!filters.country || filters.country.length === 0) return options.portfolios;
    // Filter portfolios based on selected countries
    // This would need access to the actual data to filter properly
    // For now, return all portfolios
    return options.portfolios;
  }, [options.portfolios, filters.country]);

  const availableAssets = useMemo(() => {
    if ((!filters.country || filters.country.length === 0) && (!filters.portfolio || filters.portfolio.length === 0)) {
      return options.assets;
    }
    // Filter assets based on selected countries/portfolios
    // This would need access to the actual data to filter properly
    return options.assets;
  }, [options.assets, filters.country, filters.portfolio]);

  const containerBg = theme === 'dark'
    ? 'linear-gradient(to bottom right, rgba(15, 23, 42, 0.9), rgba(30, 41, 59, 0.6), rgba(15, 23, 42, 0.9))'
    : 'linear-gradient(to bottom right, rgba(255, 255, 255, 0.95), rgba(248, 250, 252, 0.9), rgba(255, 255, 255, 0.95))';

  return (
    <div 
      className="relative rounded-xl border shadow-xl"
      style={{
        padding: '8px 16px', 
        margin: '0 16px', 
        marginBottom: '8px', 
        display: 'flex', 
        gap: '8px', 
        alignItems: 'flex-end', 
        flexWrap: 'wrap', 
        width: 'calc(100% - 32px)',
        background: containerBg,
        borderColor: containerBorder,
        boxShadow: containerShadow,
        overflow: 'visible',
      }}
    >
      {theme === 'dark' ? (
        <div className="pointer-events-none absolute inset-0 rounded-xl bg-[radial-gradient(circle_at_top,_rgba(56,189,248,0.12),_transparent_55%),radial-gradient(circle_at_bottom,_rgba(167,139,250,0.12),_transparent_60%)]" />
      ) : (
        <div className="pointer-events-none absolute inset-0 rounded-xl bg-[radial-gradient(circle_at_top,_rgba(59,130,246,0.08),_transparent_55%),radial-gradient(circle_at_bottom,_rgba(167,139,250,0.06),_transparent_60%)]" />
      )}
      <div className="relative flex w-full flex-wrap items-end gap-2">
      {/* Country Filter */}
      <MultiSelect
        label="Country"
        icon="🌍"
        options={options.countries}
        selected={filters.country || []}
        placeholder="All Countries"
        onChange={handleCountryChange}
        disabled={loading}
      />

      {/* Portfolio Filter */}
      <MultiSelect
        label="Portfolio"
        icon="📂"
        options={availablePortfolios}
        selected={filters.portfolio || []}
        placeholder="All Portfolios"
        onChange={handlePortfolioChange}
        disabled={loading}
      />

      {/* Asset Filter */}
      <MultiSelect
        label="Asset"
        icon="🏭"
        options={availableAssets}
        selected={filters.asset || []}
        placeholder="All Assets"
        onChange={handleAssetChange}
        disabled={loading}
        minWidth="225px"
        maxWidth="400px"
      />

      {/* Month Picker */}
      <div style={{ minWidth: '200px', maxWidth: '300px', flex: '0 0 auto' }}>
        <MonthPicker
          months={options.months}
          selectedMonth={filters.month || null}
          selectedYear={filters.year || null}
          selectedRange={filters.range || null}
          disabled={loading}
          hideLabel={true}
          onMonthChange={handleMonthChange}
          onYearChange={handleYearChange}
          onRangeChange={handleRangeChange}
        />
      </div>

      {/* Reset Button */}
      <div style={{ minWidth: '80px', flex: '0 0 auto' }}>
        <label 
          className="font-semibold uppercase tracking-wide" 
          style={{ display: 'block', marginBottom: '4px', color: labelColor, fontSize: `${labelFontSize}px` }}
        >
          &nbsp;
        </label>
        <button
          type="button"
          onClick={onReset}
          disabled={loading}
          className="font-semibold uppercase tracking-wide"
          style={{
            fontSize: `${buttonFontSize}px`,
            width: '100%',
            padding: '6px 14px',
            background: resetButtonBg,
            color: 'white',
            border: 'none',
            borderRadius: '8px',
            cursor: loading ? 'not-allowed' : 'pointer',
            transition: 'background 0.3s ease',
            opacity: loading ? 0.5 : 1,
          }}
          onMouseEnter={(e) => {
            if (!loading) e.currentTarget.style.background = resetButtonHoverBg;
          }}
          onMouseLeave={(e) => {
            if (!loading) e.currentTarget.style.background = resetButtonBg;
          }}
        >
          Reset
        </button>
        </div>
      </div>
    </div>
  );
}

