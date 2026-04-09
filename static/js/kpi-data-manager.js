/**
 * KPI Data Manager - Handles all data operations for the KPI dashboard
 * Version: 2025-11-11 - Taiwan exclusion enabled
 */

class KPIDataManager {
  constructor() {
    this.realtimeData = [];
    this.yieldData = [];
    this.filteredData = [];
    this.assetOptions = [];
    this.isLoading = false;
    this.error = null;
    
    // Event listeners for data changes
    this.listeners = {
      dataLoaded: [],
      dataFiltered: [],
      error: []
    };
  }

  /**
   * Add event listener
   */
  on(event, callback) {
    if (this.listeners[event]) {
      this.listeners[event].push(callback);
    }
  }

  /**
   * Trigger event
   */
  trigger(event, data) {
    if (this.listeners[event]) {
      this.listeners[event].forEach(callback => callback(data));
    }
  }

  /**
   * Load all required data
   */
  async loadAllData() {
    this.isLoading = true;
    this.error = null;

    try {
      await Promise.all([
        this.loadRealtimeKPIData(),
        this.loadYieldData(),
        this.loadAssetOptions()
      ]);

      this.isLoading = false;
      this.trigger('dataLoaded', {
        realtimeData: this.realtimeData,
        yieldData: this.yieldData,
        assetOptions: this.assetOptions
      });

    } catch (error) {
      this.isLoading = false;
      this.error = error;
      this.trigger('error', error);
    }
  }

  /**
   * Load real-time KPI data from API
   */
  async loadRealtimeKPIData() {
    try {
      const response = await fetch('/api/real-time-kpi-data');
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      
      if (data.success) {
        this.realtimeData = data.data || [];
      } else {
        throw new Error(data.error || 'Failed to load real-time KPI data');
      }
    } catch (error) {
      throw error;
    }
  }

  /**
   * Load yield data from Django context
   */
  async loadYieldData() {
    try {
      // This will be populated from Django template context
      if (typeof window.yieldDataJson !== 'undefined') {
        // Use YieldData for historical data (January-September)
        this.yieldData = Array.isArray(window.yieldDataJson) ? window.yieldDataJson.slice() : [];
      } else if (typeof window.kpiDataJson !== 'undefined') {
        // Fallback to RealTimeKPI data if YieldData is not available
        this.yieldData = Array.isArray(window.kpiDataJson) ? window.kpiDataJson.slice() : [];
      } else {
        this.yieldData = [];
      }
    } catch (error) {
      this.yieldData = [];
    }
  }

  /**
   * Load asset options from API
   */
  async loadAssetOptions() {
    try {
      const response = await fetch('/api/asset-options');
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      
      // API returns an array directly, not a wrapper object
      if (Array.isArray(data)) {
        this.assetOptions = data;
      } else {
        throw new Error('Invalid response format from asset-options API');
      }
    } catch (error) {
      this.assetOptions = [];
      // Don't throw error for asset options as it's not critical
    }
  }

  /**
   * Get filtered real-time data based on filters
   */
  getFilteredRealtimeData(filters) {
    if (!this.realtimeData || this.realtimeData.length === 0) {
      return [];
    }

    // Define the cutoff date - data is only available from July 1st, 2025
    const cutoffDate = new Date('2025-07-01');
    
    const filteredData = this.realtimeData.filter(row => {
      // Exclude Taiwan sites from gauge calculations (check both country and asset_code)
      if (this.isTaiwanSite(row)) {
        return false;
      }
      
      const countryMatch = !filters.countries || filters.countries.length === 0 || 
                          filters.countries.includes(row.country);
      const portfolioMatch = !filters.portfolios || filters.portfolios.length === 0 || 
                            filters.portfolios.includes(row.portfolio);
      const assetMatch = !filters.assets || filters.assets.length === 0 || 
                        filters.assets.includes(row.asset_code || row.assetno);
      
      // Fix date matching logic and check cutoff date
      let dateMatch = true;
      if (filters.date) {
        const rowDate = typeof row.date === 'string' ? row.date.split('T')[0] : row.date.toISOString().split('T')[0];
        const selectedDate = new Date(filters.date);
        
        // Check if selected date is before the cutoff date
        if (selectedDate < cutoffDate) {
          return false; // No data available before July 1st, 2025
        }
        
        dateMatch = rowDate === filters.date;
      }

      return countryMatch && portfolioMatch && assetMatch && dateMatch;
    });
    return filteredData;
  }

  /**
   * Helper function to check if a row matches a filter
   */
  matchesFilter(row, filters, field) {
    // Handle special case for field mapping
    let rowValue;
    if (field === 'countries') {
      rowValue = (row.country || row.rowCountry || '').trim(); // Try both field names and trim
    } else if (field === 'portfolios') {
      rowValue = (row.portfolio || row.portfolio_name || row.portfolio_code || '').trim(); // Try multiple field names and trim
    } else if (field === 'assets') {
      rowValue = row.asset_code || row.assetno || row.asset_number || row.asset; // Try multiple field names
    } else {
      rowValue = row[field];
    }

    // Normalize function for country codes and names
    const normalizeCountry = (val) => {
      const v = (val || '').toString().trim();
      const lower = v.toLowerCase();
      const map = {
        'jp': 'jp', 'japan': 'jp',
        'kr': 'kr', 'korea': 'kr',
        'sg': 'sg', 'singapore': 'sg',
        'tw': 'tw', 'taiwan': 'tw'
      };
      return map[lower] || lower;
    };

    if (!filters[field] || filters[field].length === 0) {
      return true;
    }

    if (field === 'countries') {
      const rowCountry = normalizeCountry(rowValue);
      const filterCountries = filters[field].map(normalizeCountry);
      return filterCountries.includes(rowCountry);
    }

    const rowValueNormalized = (rowValue || '').toString().trim().toLowerCase();
    const filterValuesNormalized = filters[field].map(v => (v || '').toString().trim().toLowerCase());
    return filterValuesNormalized.includes(rowValueNormalized);
  }

  /**
   * Get filtered yield data based on filters
   */
  getFilteredYieldData(filters) {
    if (!this.yieldData || this.yieldData.length === 0) {
      return [];
    }



    const result = this.yieldData.filter(row => {
      const countryMatch = this.matchesFilter(row, filters, 'countries');
      const portfolioMatch = this.matchesFilter(row, filters, 'portfolios');
      const assetValue = (row.asset_code || row.assetno || row.asset_number || row.asset || '').trim();
      const assetMatch = !filters.assets || filters.assets.length === 0 || 
                        filters.assets.includes(assetValue);
      
      
      
      let periodMatch = true;
      if (filters.period) {
        if (filters.period.range) {
          const startMonth = filters.period.range.start;
          const endMonth = filters.period.range.end;
          
          const startDate = this.convertMonthToDate(startMonth);
          const endDate = this.convertMonthToDate(endMonth);
          const rowDate = this.convertMonthToDate(row.month);
          
          if (rowDate && startDate && endDate) {
            periodMatch = rowDate >= startDate && rowDate <= endDate;
          } else {
            periodMatch = false;
          }
        } else if (filters.period.month) {
          // Normalize both row.month and filter month to 'YYYY-MM' for robust matching
          const normalizeToYYYYMM = (val) => {
            if (!val) return '';
            const s = String(val).trim();
            // YYYY-MM or YYYY-M or YYYY-MM-DD
            let m = s.match(/^(\d{4})-(\d{1,2})(?:-(\d{1,2}))?$/);
            if (m) {
              return `${m[1]}-${String(parseInt(m[2], 10)).padStart(2, '0')}`;
            }
            // Mon YYYY or Month YYYY
            const monthNames = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
            const fullMonthNames = ['January','February','March','April','May','June','July','August','September','October','November','December'];
            m = s.match(/^(\w+)\s+(\d{4})$/);
            if (m) {
              let idx = monthNames.indexOf(m[1]);
              if (idx === -1) idx = fullMonthNames.indexOf(m[1]);
              if (idx !== -1) {
                return `${m[2]}-${String(idx + 1).padStart(2, '0')}`;
              }
            }
            return s;
          };
          const rowMonthNorm = normalizeToYYYYMM(row.month);
          const filterMonthNorm = normalizeToYYYYMM(filters.period.month);
          periodMatch = rowMonthNorm === filterMonthNorm;
        } else if (filters.period.year) {
          periodMatch = row.month && row.month.startsWith(filters.period.year.toString());
        }
      }

      return countryMatch && portfolioMatch && assetMatch && periodMatch;
    });
    

    
    return result;
  }

  /**
   * Helper function to check if a row is from Taiwan (to exclude from calculations)
   * Checks both country field and asset_code to catch all Taiwan sites
   */
  isTaiwanSite(row) {
    // Check country field (case-insensitive)
    const countryValue = (row.country || row.rowCountry || '').toString().trim().toLowerCase();
    if (countryValue === 'tw' || countryValue === 'taiwan' || countryValue === 'tiwan') {
      return true;
    }
    
    // Check asset_code for Taiwan sites (TW1, TW2, TW3, or any starting with TW)
    const assetCode = (row.asset_code || row.assetno || row.asset_number || row.asset || '').toString().trim().toUpperCase();
    if (assetCode.startsWith('TW') || assetCode === 'TW1' || assetCode === 'TW2' || assetCode === 'TW3') {
      return true;
    }
    
    return false;
  }

  /**
   * Calculate gauge values from filtered real-time data
   * Only considers budgets where their corresponding actual values are available
   * Excludes Taiwan sites to prevent incomplete data from skewing weighted averages
   */
  calculateGaugeValues(filteredData) {
    if (!filteredData || filteredData.length === 0) {
      return {
        icBudget: 0,
        expectedBudget: 0,
        actualGeneration: 0,
        budgetIrr: 0,
        actualIrr: 0,
        expectedPR: 0,
        actualPR: 0
      };
    }

    // First, explicitly exclude Taiwan sites to prevent incomplete data from affecting weighted averages
    const dataExcludingTaiwan = filteredData.filter(row => !this.isTaiwanSite(row));

    // Filter data for each metric separately - only include records where actual values exist
    const dataWithActualGeneration = dataExcludingTaiwan.filter(row => 
      !isNaN(+row.daily_generation_mwh) && +row.daily_generation_mwh > 0
    );
    
    const dataWithActualIrr = dataExcludingTaiwan.filter(row => 
      (!isNaN(+row.daily_irradiation_mwh) && +row.daily_irradiation_mwh > 0) ||
      (!isNaN(+row.daily_budget_irradiation_mwh) && +row.daily_budget_irradiation_mwh > 0)
    );
    
    const dataWithActualPR = dataExcludingTaiwan.filter(row => 
      (!isNaN(+row.actual_pr) && +row.actual_pr > 0) ||
      (!isNaN(+row.expect_pr) && +row.expect_pr > 0)
    );
    


    // Calculate generation metrics - only from records with actual generation
    const icBudget = dataWithActualGeneration.reduce((sum, row) => sum + (+row.daily_ic_mwh || 0), 0);
    const expectedBudget = dataWithActualGeneration.reduce((sum, row) => sum + (+row.daily_expected_mwh || 0), 0);
    const actualGeneration = dataWithActualGeneration.reduce((sum, row) => sum + (+row.daily_generation_mwh || 0), 0);
    
    // Calculate weighted average irradiation metrics
    let budgetIrr, actualIrr;
    
    // Check if we have any irradiation data for weighted calculation
    const hasAnyIrrData = dataWithActualIrr.some(row => 
      (!isNaN(+row.daily_irradiation_mwh) && +row.daily_irradiation_mwh > 0) ||
      (!isNaN(+row.daily_budget_irradiation_mwh) && +row.daily_budget_irradiation_mwh > 0)
    );
    

    
    if (hasAnyIrrData) {
      // Use weighted average based on capacity/area for irradiation
      // FIXED: Separate weight calculations for budget vs actual to avoid skewing results
      let totalWeightIrr = 0;        // Only for actual irradiation (sites with actual > 0)
      let weightedBudgetIrr = 0;     // For budget irradiation (all sites with budget > 0)
      let weightedActualIrr = 0;     // Only for actual irradiation (sites with actual > 0)
      
      dataWithActualIrr.forEach(row => {
        // Use capacity as weight (fallback to 1 if not available)
        const weight = +row.capacity || 1;
        const budgetValue = +row.daily_budget_irradiation_mwh || 0;
        const actualValue = +row.daily_irradiation_mwh || 0;
        
        if (weight > 0) {
          // For budget: include if budget value exists
          if (budgetValue > 0) {
            const weightedBudget = budgetValue * weight;
            weightedBudgetIrr += weightedBudget;
          }
          
          // For actual: ONLY include if actual value exists (not zero)
          if (actualValue > 0) {
            const weightedActual = actualValue * weight;
            weightedActualIrr += weightedActual;
            totalWeightIrr += weight; // Only add to total weight for actual calculations
          }
        }
      });
      
      // Calculate budget irradiation using all sites with budget data
      const totalBudgetWeight = dataWithActualIrr.reduce((sum, row) => {
        const weight = +row.capacity || 1;
        const budgetValue = +row.daily_budget_irradiation_mwh || 0;
        return budgetValue > 0 ? sum + weight : sum;
      }, 0);
      
      budgetIrr = totalBudgetWeight > 0 ? weightedBudgetIrr / totalBudgetWeight : 0;
      
      // Calculate actual irradiation using only sites with actual data
      actualIrr = totalWeightIrr > 0 ? weightedActualIrr / totalWeightIrr : 0;

    } else {
      // Fallback to simple sum if no irradiation data
      budgetIrr = dataWithActualIrr.reduce((sum, row) => {
        const value = +row.daily_budget_irradiation_mwh || 0;
        return sum + value;
      }, 0);
      
      actualIrr = dataWithActualIrr.reduce((sum, row) => {
        const value = +row.daily_irradiation_mwh || 0;
        return sum + value;
      }, 0);
    }

    // Calculate weighted average PR metrics
    let expectedPR, actualPR;
    
    // Check if we have any PR data for weighted calculation
    const hasAnyPRData = dataWithActualPR.some(row => 
      (!isNaN(+row.actual_pr) && +row.actual_pr > 0) ||
      (!isNaN(+row.expect_pr) && +row.expect_pr > 0)
    );
    

    
    if (hasAnyPRData) {
      // Use weighted average based on generation capacity for PR
      // FIXED: Separate weight calculations for expected vs actual PR to avoid skewing results
      let totalWeightExpectedPR = 0;  // Only for expected PR (sites with expect_pr > 0)
      let totalWeightActualPR = 0;    // Only for actual PR (sites with actual_pr > 0)
      let weightedExpectedPR = 0;
      let weightedActualPR = 0;
      
      dataWithActualPR.forEach(row => {
        // Use capacity as weight (fallback to 1 if not available)
        const weight = +row.capacity || 1;
        const expectedValue = +row.expect_pr || 0;
        const actualValue = +row.actual_pr || 0;
        
        if (weight > 0) {
          // Calculate weighted averages separately for expected and actual PR
          if (!isNaN(expectedValue) && expectedValue > 0) {
            const weightedExpected = expectedValue * weight;
            weightedExpectedPR += weightedExpected;
            totalWeightExpectedPR += weight;
          }
          
          if (!isNaN(actualValue) && actualValue > 0) {
            const weightedActual = actualValue * weight;
            weightedActualPR += weightedActual;
            totalWeightActualPR += weight;
          }
        }
      });
      
      expectedPR = totalWeightExpectedPR > 0 ? weightedExpectedPR / totalWeightExpectedPR : 0;
      actualPR = totalWeightActualPR > 0 ? weightedActualPR / totalWeightActualPR : 0;

    } else {
      // Fallback to simple average if no PR data
      const validExpectedPRData = dataWithActualPR.filter(row => {
        const pr = +row.expect_pr;
        return !isNaN(pr) && pr !== null && row.expect_pr !== '' && row.expect_pr !== 'NaN';
      });
      
      const validActualPRData = dataWithActualPR.filter(row => {
        const pr = +row.actual_pr;
        return !isNaN(pr) && pr !== null && row.actual_pr !== '' && row.actual_pr !== 'NaN';
      });
      
      expectedPR = validExpectedPRData.length > 0 ? 
        (validExpectedPRData.reduce((sum, row) => sum + (+row.expect_pr || 0), 0) / validExpectedPRData.length) : 0;
      
      actualPR = validActualPRData.length > 0 ? 
        (validActualPRData.reduce((sum, row) => sum + (+row.actual_pr || 0), 0) / validActualPRData.length) : 0;

    }

    const result = {
      icBudget,
      expectedBudget,
      actualGeneration,
      budgetIrr,
      actualIrr,
      expectedPR,
      actualPR
    };
    
    return result;
  }

  /**
   * Helper function to convert month string to Date object
   */
  convertMonthToDate(monthStr) {
    try {
      // Handle different month formats
      const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
      const fullMonthNames = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
      
      // Try to parse different formats
      let year, month;
      
      // Accepted formats:
      // - YYYY-MM
      // - YYYY-M
      // - YYYY-MM-DD (normalize to first of the month)
      // - Mon YYYY
      // - Month YYYY
      if (typeof monthStr === 'string' && monthStr.includes('-')) {
        const parts = monthStr.split('-');
        if (parts.length >= 2) {
          year = parseInt(parts[0]);
          month = parseInt(parts[1]) - 1; // Month is 0-indexed
        }
      } else {
        // Format: "Jan 2025" or "January 2025"
        const parts = monthStr.split(' ');
        if (parts.length >= 2) {
          const monthPart = parts[0];
          const yearPart = parts[1];
          
          let monthIndex = monthNames.indexOf(monthPart);
          if (monthIndex === -1) {
            monthIndex = fullMonthNames.indexOf(monthPart);
          }
          
          if (monthIndex !== -1 && yearPart) {
            year = parseInt(yearPart);
            month = monthIndex;
          }
        }
      }
      
      if (year && month !== undefined) {
        // Create date in UTC to avoid timezone issues
        return new Date(Date.UTC(year, month, 1));
      }
    } catch (error) {
      // Error converting month to date
    }
    return null;
  }

  /**
   * Get unique countries from data
   */
  getUniqueCountries(dataType = 'realtime') {
    const data = dataType === 'realtime' ? this.realtimeData : this.yieldData;
    const countries = [...new Set(data.map(r => r.country ? r.country.trim() : ''))].filter(c => c).sort();
    
    // Only apply country mapping for yield data (advanced section)
    // Gauge section (realtime data) should show original country codes (JP, KR, SG, TW)
    if (dataType === 'yield') {
      const countryMapping = {
        'JP': 'Japan',
        'KR': 'Korea', 
        'SG': 'Singapore',
        'TW': 'Taiwan'
      };
      
      return countries.map(country => ({
        value: country,
        label: countryMapping[country] || country
      }));
    } else {
      // For realtime data (gauge section), return simple array with country codes
      return countries.map(country => ({
        value: country,
        label: country
      }));
    }
  }

  /**
   * Get unique portfolios from data
   */
  getUniquePortfolios(dataType = 'realtime') {
    const data = dataType === 'realtime' ? this.realtimeData : this.yieldData;
    return [...new Set(data.map(r => r.portfolio ? r.portfolio.trim() : ''))].filter(p => p).sort();
  }

  /**
   * Get date with most data for better UX
   */
  getDefaultDate() {
    if (!this.realtimeData || this.realtimeData.length === 0) {
      return new Date();
    }

    const dateCount = {};
    this.realtimeData.forEach(r => {
      const dateKey = r.date.split('T')[0];
      dateCount[dateKey] = (dateCount[dateKey] || 0) + 1;
    });

    const dateWithMostData = Object.keys(dateCount).reduce((a, b) => 
      dateCount[a] > dateCount[b] ? a : b
    );

    return dateWithMostData ? new Date(dateWithMostData) : new Date();
  }

  /**
   * Get all available dates in the data
   */
  getAvailableDates() {
    if (!this.realtimeData || this.realtimeData.length === 0) {
      return [];
    }

    const availableDates = [...new Set(this.realtimeData.map(row => row.date.split('T')[0]))].sort();
    return availableDates;
  }

  /**
   * Validate data integrity
   */
  validateData() {
    const errors = [];

    if (!this.realtimeData || this.realtimeData.length === 0) {
      errors.push('No real-time data available');
    }

    if (!this.yieldData || this.yieldData.length === 0) {
      errors.push('No yield data available');
    }

    // Check for required fields in real-time data
    if (this.realtimeData.length > 0) {
      const requiredFields = ['country', 'portfolio', 'asset_code', 'date'];
      const sampleRecord = this.realtimeData[0];
      
      requiredFields.forEach(field => {
        if (!(field in sampleRecord)) {
          errors.push(`Missing required field: ${field}`);
        }
      });
    }

    return errors;
  }

  /**
   * Clear all data
   */
  clearData() {
    this.realtimeData = [];
    this.yieldData = [];
    this.filteredData = [];
    this.assetOptions = [];
    this.error = null;
  }
}

// Create singleton instance
const KPIManager = new KPIDataManager();
window.KPIDataManager = KPIManager;
