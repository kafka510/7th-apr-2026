/**
 * Generation Budget Insights - Filter Utilities
 * Utility functions for filtering IC Budget data
 * Updated to work with MonthPicker format (YYYY-MM)
 */
import type { ICBudgetDataEntry, ICBudgetFilters } from '../types';

export function filterICBudgetData(
  data: ICBudgetDataEntry[],
  filters: ICBudgetFilters
): ICBudgetDataEntry[] {
  return data.filter((row) => {
    // Month filter - MonthPicker uses YYYY-MM format
    let monthMatch = true;
    if (filters.selectedMonth) {
      // Exact month match - compare YYYY-MM part of month_sort
      if (row.month_sort) {
        const rowYearMonth = row.month_sort.substring(0, 7); // Extract YYYY-MM from YYYY-MM-DD
        monthMatch = rowYearMonth === filters.selectedMonth;
      } else {
        monthMatch = false;
      }
    } else if (filters.selectedRange) {
      // Range selection - compare YYYY-MM part
      if (row.month_sort) {
        const rowYearMonth = row.month_sort.substring(0, 7); // Extract YYYY-MM from YYYY-MM-DD
        monthMatch = rowYearMonth >= filters.selectedRange.start && rowYearMonth <= filters.selectedRange.end;
      } else {
        monthMatch = false;
      }
    } else if (filters.selectedYear) {
      // Year selection - extract year from month_sort
      if (row.month_sort) {
        const rowYear = row.month_sort.substring(0, 4); // Extract YYYY from YYYY-MM-DD
        monthMatch = rowYear === filters.selectedYear;
      } else {
        monthMatch = false;
      }
    }
    // If no month filter, monthMatch remains true (show all months)

    // Country filter
    let countryMatch = true;
    if (filters.country && filters.country !== 'All') {
      // Filter is set and not 'All', so check for match
      countryMatch = row.country === filters.country;
    }
    // If no country filter or filter is 'All', countryMatch remains true

    // Portfolio filter
    let portfolioMatch = true;
    if (filters.portfolio && filters.portfolio !== 'All') {
      // Filter is set and not 'All', so check for match
      portfolioMatch = row.portfolio === filters.portfolio;
    }
    // If no portfolio filter or filter is 'All', portfolioMatch remains true

    return monthMatch && countryMatch && portfolioMatch;
  });
}

