/**
 * Generation Budget Insights - Filters Component
 * Filters for IC Budget vs Expected Generation analysis
 * React Style V1 - Dark theme design system with MonthPicker integration
 */
 
import { useMemo } from 'react';
import { useTheme } from '../../../contexts/ThemeContext';
import { useResponsiveFontSize } from '../../../utils/fontScaling';
import { PeriodPicker, type Period } from '../../generation/components/PeriodPicker';
import type { ICBudgetDataEntry, ICBudgetFilters } from '../types';

interface ICBudgetFiltersProps {
  data: ICBudgetDataEntry[];
  filters: ICBudgetFilters;
  onFiltersChange: (filters: ICBudgetFilters) => void;
  onReset: () => void;
}

export function ICBudgetFilters({
  data,
  filters,
  onFiltersChange,
  onReset,
}: ICBudgetFiltersProps) {
  const { theme } = useTheme();
  
  // Responsive font sizes
  const selectFontSize = useResponsiveFontSize(10, 14, 9);
  const buttonFontSize = useResponsiveFontSize(9, 13, 8);
  
  const containerBg = theme === 'dark'
    ? 'linear-gradient(to bottom right, rgba(15, 23, 42, 0.5), rgba(30, 41, 59, 0.3), rgba(15, 23, 42, 0.5))'
    : 'linear-gradient(to bottom right, rgba(248, 250, 252, 0.9), rgba(241, 245, 249, 0.8), rgba(248, 250, 252, 0.9))';
  const selectBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.8)' : '#ffffff';
  const selectBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : 'rgba(203, 213, 225, 0.8)';
  const selectText = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';
  const selectHoverBorder = theme === 'dark' ? 'rgba(59, 130, 246, 0.5)' : 'rgba(59, 130, 246, 0.7)';
  const selectHoverBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.8)' : 'rgba(241, 245, 249, 0.9)';
  const resetButtonBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.8)' : 'rgba(241, 245, 249, 0.9)';
  const resetButtonText = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';
  const resetButtonHoverBg = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(226, 232, 240, 0.9)';
  const resetButtonHoverText = theme === 'dark' ? '#93c5fd' : '#0072ce';
  const resetButtonShadow = theme === 'dark' 
    ? 'inset 0 2px 4px rgba(0, 0, 0, 0.4)' 
    : 'inset 0 2px 4px rgba(0, 0, 0, 0.1)';
  
  // Extract unique values for filters
  const { countries, portfolios } = useMemo(() => {
    const uniqueCountries = [...new Set(data.map((row) => row.country).filter(Boolean))].sort();
    const uniquePortfolios = [...new Set(data.map((row) => row.portfolio).filter(Boolean))].sort();
    
    // Extract months and convert to YYYY-MM format for MonthPicker
    const monthSet = new Set<string>();
    data.forEach((row) => {
      if (row.month_sort) {
        // month_sort is in format "2025-04-01", we need "2025-04"
        const yearMonth = row.month_sort.substring(0, 7);
        monthSet.add(yearMonth);
      }
    });
    return {
      countries: uniqueCountries,
      portfolios: uniquePortfolios,
    };
  }, [data]);

  // Map IC Budget filters to PeriodPicker Period
  const defaultPeriod: Period = useMemo(() => {
    if (filters.selectedRange) {
      return {
        range: {
          start: filters.selectedRange.start,
          end: filters.selectedRange.end,
        },
      };
    }
    if (filters.selectedMonth) {
      return { month: filters.selectedMonth };
    }
    if (filters.selectedYear) {
      return {
        range: {
          start: `${filters.selectedYear}-01`,
          end: `${filters.selectedYear}-12`,
        },
      };
    }
    return {};
  }, [filters.selectedMonth, filters.selectedYear, filters.selectedRange]);

  const handlePeriodChange = (period: Period) => {
    if (period.range) {
      const { start, end } = period.range;
      const year = start.split('-')[0];

      if (start === `${year}-01` && end === `${year}-12`) {
        onFiltersChange({
          ...filters,
          selectedMonth: null,
          selectedRange: null,
          selectedYear: year,
        });
      } else {
        onFiltersChange({
          ...filters,
          selectedMonth: null,
          selectedYear: null,
          selectedRange: { start, end },
        });
      }
    } else if (period.month) {
      const year = period.month.split('-')[0];
      onFiltersChange({
        ...filters,
        selectedMonth: period.month,
        selectedYear: year,
        selectedRange: null,
      });
    } else {
      onFiltersChange({
        ...filters,
        selectedMonth: null,
        selectedYear: null,
        selectedRange: null,
      });
    }
  };

  const handleCountryChange = (value: string) => {
    onFiltersChange({
      ...filters,
      country: value === 'All' ? undefined : value,
    });
  };

  const handlePortfolioChange = (value: string) => {
    onFiltersChange({
      ...filters,
      portfolio: value === 'All' ? undefined : value,
    });
  };

  return (
    <div 
      className="px-2 py-1"
      style={{
        background: containerBg,
      }}
    >
      <div className="grid grid-cols-1 items-center gap-2 md:grid-cols-5">
        {/* Month Picker */}
        <div className="md:col-span-2">
          <PeriodPicker
            defaultPeriod={defaultPeriod}
            onPeriodChange={handlePeriodChange}
            onReset={onReset}
          />
        </div>

        {/* Country Filter */}
        <div>
          <select
            className="w-full cursor-pointer rounded-lg border px-2 py-1 font-medium shadow-inner transition-all duration-200 focus:outline-none focus:ring-1"
            style={{
              fontSize: `${selectFontSize}px`,
              backgroundColor: selectBg,
              borderColor: selectBorder,
              color: selectText,
              boxShadow: resetButtonShadow,
            }}
            value={filters.country || 'All'}
            onChange={(e) => handleCountryChange(e.target.value)}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = selectHoverBorder;
              e.currentTarget.style.backgroundColor = selectHoverBg;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = selectBorder;
              e.currentTarget.style.backgroundColor = selectBg;
            }}
            onFocus={(e) => {
              e.currentTarget.style.borderColor = theme === 'dark' ? '#3b82f6' : '#0072ce';
              e.currentTarget.style.boxShadow = theme === 'dark' 
                ? '0 0 0 1px rgba(59, 130, 246, 0.3)' 
                : '0 0 0 1px rgba(59, 130, 246, 0.2)';
            }}
            onBlur={(e) => {
              e.currentTarget.style.borderColor = selectBorder;
              e.currentTarget.style.boxShadow = resetButtonShadow;
            }}
          >
            <option value="All">🌏 All Countries</option>
            {countries.map((country) => (
              <option key={country || 'unknown'} value={country || ''}>
                {country}
              </option>
            ))}
          </select>
        </div>

        {/* Portfolio Filter */}
        <div>
          <select
            className="w-full cursor-pointer rounded-lg border px-2 py-1 font-medium shadow-inner transition-all duration-200 focus:outline-none focus:ring-1"
            style={{
              fontSize: `${selectFontSize}px`,
              backgroundColor: selectBg,
              borderColor: selectBorder,
              color: selectText,
              boxShadow: resetButtonShadow,
            }}
            value={filters.portfolio || 'All'}
            onChange={(e) => handlePortfolioChange(e.target.value)}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = selectHoverBorder;
              e.currentTarget.style.backgroundColor = selectHoverBg;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = selectBorder;
              e.currentTarget.style.backgroundColor = selectBg;
            }}
            onFocus={(e) => {
              e.currentTarget.style.borderColor = theme === 'dark' ? '#3b82f6' : '#0072ce';
              e.currentTarget.style.boxShadow = theme === 'dark' 
                ? '0 0 0 1px rgba(59, 130, 246, 0.3)' 
                : '0 0 0 1px rgba(59, 130, 246, 0.2)';
            }}
            onBlur={(e) => {
              e.currentTarget.style.borderColor = selectBorder;
              e.currentTarget.style.boxShadow = resetButtonShadow;
            }}
          >
            <option value="All">📂 All Portfolios</option>
            {portfolios.map((portfolio) => (
              <option key={portfolio || 'unknown'} value={portfolio || ''}>
                {portfolio}
              </option>
            ))}
          </select>
        </div>

        {/* Reset Button */}
        <div>
          <button
            type="button"
            onClick={onReset}
            className="w-full rounded-lg px-3 py-1 font-semibold uppercase tracking-wide shadow-inner transition-all duration-200 focus:outline-none focus:ring-1"
            style={{
              fontSize: `${buttonFontSize}px`,
              backgroundColor: resetButtonBg,
              color: resetButtonText,
              boxShadow: resetButtonShadow,
              border: 'none',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = resetButtonHoverBg;
              e.currentTarget.style.color = resetButtonHoverText;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = resetButtonBg;
              e.currentTarget.style.color = resetButtonText;
            }}
            onFocus={(e) => {
              e.currentTarget.style.boxShadow = theme === 'dark' 
                ? '0 0 0 1px rgba(59, 130, 246, 0.3)' 
                : '0 0 0 1px rgba(59, 130, 246, 0.2)';
            }}
            onBlur={(e) => {
              e.currentTarget.style.boxShadow = resetButtonShadow;
            }}
          >
            🔄 Reset
          </button>
        </div>
      </div>
    </div>
  );
}

