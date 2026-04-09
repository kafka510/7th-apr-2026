/**
 * KPI Dashboard - Main orchestrator for the KPI dashboard
 */
class KPIDashboard {
  constructor() {
    this.dataManager = null;
    this.gaugeManager = null;
    this.multiSelectInstances = {};
    this.isInitialized = false;
    this.loadingState = {
      isLoading: false,
      message: ''
    };
    this.chartType = 'bar'; // Default to bar chart

  }

  /**
   * Initialize the dashboard
   */
  async init() {
    try {
      // Show loading state
      this.showLoading('Initializing dashboard...');
      
      // Initialize data manager (use singleton instance)
      this.dataManager = window.KPIDataManager;
      
      // Set up data manager event listeners
      this.setupDataManagerListeners();
      
      // Load all data
      await this.dataManager.loadAllData();
      
      // Initialize components
      this.initializeComponents();
      
      // Set up global event listeners
      this.setupGlobalEventListeners();
      
      // Set up chart type selector
      this.setupChartTypeSelector();
      
      this.isInitialized = true;
      this.hideLoading();
      
    } catch (error) {
      this.showError('Failed to initialize dashboard: ' + error.message);
    }
  }

  /**
   * Setup data manager event listeners
   */
  setupDataManagerListeners() {
    this.dataManager.on('dataLoaded', (data) => {
      this.onDataLoaded(data);
    });

    this.dataManager.on('error', (error) => {
      this.showError('Data loading error: ' + error.message);
    });
  }


     /**
    * Handle data loaded event
    */
   onDataLoaded(data) {
     try {
       // Initialize multi-select components first
       this.initializeMultiSelects();
       
       // Setup advanced reset button after multi-selects are initialized
       this.setupAdvancedResetButton();
       
      // Initialize gauge charts
      this.gaugeManager = new GaugeChartsManager(this.dataManager);
      // expose globally so cross-page/tab handlers can refresh
      window.gaugeChartsManager = this.gaugeManager;
      this.gaugeManager.init();
       
       // Set default date
       this.gaugeManager.setDefaultDate();
       
       // Initialize advanced components
       this.initializeAdvancedComponents();
       
       // Update calendar data if available
       if (window.currentBestCalendar && this.dataManager.yieldData && this.dataManager.yieldData.length > 0) {
         try {
           if (typeof window.currentBestCalendar.setData === 'function') {
             window.currentBestCalendar.setData(this.dataManager.yieldData);
           } else {
             // BestCalendar setData method not available
           }
         } catch (error) {
           // Error updating calendar data
         }
       }
       
       // Ensure calendar is properly initialized
       if (!window.currentBestCalendar && typeof BestCalendar !== 'undefined') {
         setTimeout(() => {
           this.initializeAdvancedComponents();
         }, 100);
       }
       
       // Populate dropdowns
       this.populateDropdowns();
       
      // Update charts
      this.gaugeManager.updateCharts();
      
      // Update KPI summary cards using site_state from latest data
      this.updateKPISummaryCardsFromSiteState();
       
       // Validate data
       const validationErrors = this.dataManager.validateData();
       if (validationErrors.length > 0) {
         // Data validation warnings (suppressed for production)
       }
       
     } catch (error) {
       this.showError('Error processing data: ' + error.message);
     }
   }

  /**
   * Initialize all components
   */
  initializeComponents() {
    // Initialize advanced components (if they exist)
    this.initializeAdvancedComponents();
    
    // Setup toggle functionality
    this.setupToggles();
    
    // Setup reset button with a more robust approach
    this.setupResetButtonRobust();
  }

  /**
   * Robust reset button setup that works regardless of timing
   */
  setupResetButtonRobust() {
    // Try to set up the reset button immediately
    this.trySetupResetButton();
    
    // Also try again after a short delay in case the DOM isn't ready
    setTimeout(() => {
      this.trySetupResetButton();
    }, 500);
    
    // And try again after a longer delay
    setTimeout(() => {
      this.trySetupResetButton();
    }, 2000);
  }

  /**
   * Try to set up the reset button
   */
  trySetupResetButton() {
    const advancedResetBtn = document.getElementById('advancedResetBtn');
    
    if (advancedResetBtn) {
      // Remove any existing event listeners
      advancedResetBtn.removeEventListener('click', this.resetAdvancedFilters);
      
      // Add new event listener with proper binding
      advancedResetBtn.addEventListener('click', () => {
        // Test if we can directly access the title element
        const titleElement = document.getElementById('advancedChartTitle');
        if (titleElement) {
          titleElement.textContent = 'All Data';
        }
        
        this.resetAdvancedFilters();
      });
      
      return true;
    } else {
      return false;
    }
  }

  /**
   * Initialize multi-select dropdowns
   */
  initializeMultiSelects() {
    try {
      // Gauge section multi-selects
      this.multiSelectInstances.gaugeCountry = new MultiSelect(
        'gaugeCountryFilterTrigger',
        'gaugeCountryFilterDropdown',
        'gaugeCountryFilterPlaceholder',
        'gaugeCountrySelectedItems',
        () => {
          // Update portfolio options based on selected countries
          const selectedCountries = this.multiSelectInstances.gaugeCountry.getSelectedValues();
          this.updatePortfolioOptions(selectedCountries, false);
          // Update asset options
          const selectedPortfolios = this.multiSelectInstances.gaugePortfolio.getSelectedValues();
          this.updateAssetOptions(selectedCountries, selectedPortfolios, false);
          // Update charts
          this.gaugeManager.onFilterChange();
        }
      );

      this.multiSelectInstances.gaugePortfolio = new MultiSelect(
        'gaugePortfolioFilterTrigger',
        'gaugePortfolioFilterDropdown',
        'gaugePortfolioFilterPlaceholder',
        'gaugePortfolioSelectedItems',
        () => {
          // Update asset options based on selected countries and portfolios
          const selectedCountries = this.multiSelectInstances.gaugeCountry.getSelectedValues();
          const selectedPortfolios = this.multiSelectInstances.gaugePortfolio.getSelectedValues();
          this.updateAssetOptions(selectedCountries, selectedPortfolios, false);
          // Update charts
          this.gaugeManager.onFilterChange();
        }
      );

      // Gauge Asset multi-select
      this.multiSelectInstances.gaugeAsset = new MultiSelect(
        'gaugeAssetNoFilterTrigger',
        'gaugeAssetNoFilterDropdown',
        'gaugeAssetNoFilterPlaceholder',
        'gaugeAssetNoSelectedItems',
        () => {
          // Update charts
          this.gaugeManager.onFilterChange();
        }
      );

      // Set global references for the gauge manager to access
      window.gaugeCountryMultiSelect = this.multiSelectInstances.gaugeCountry;
      window.gaugePortfolioMultiSelect = this.multiSelectInstances.gaugePortfolio;
      window.gaugeAssetMultiSelect = this.multiSelectInstances.gaugeAsset;

      // Chart Type multi-select (single selection - max 1)
      this.multiSelectInstances.advancedChartType = new MultiSelect(
        'advancedChartTypeFilterTrigger',
        'advancedChartTypeFilterDropdown',
        'advancedChartTypeFilterPlaceholder',
        'advancedChartTypeSelectedItems',
        () => {
          // Update chart when type changes
          // Also enforce parameter limit based on chart type
          this.enforceParameterLimitBasedOnChartType();
          setTimeout(() => {
            this.updateAdvancedCharts();
          }, 10);
        }
      );

      // Advanced section multi-selects
       this.multiSelectInstances.advancedParameter = new MultiSelect(
         'advancedParameterFilterTrigger',
         'advancedParameterFilterDropdown',
         'advancedParameterFilterPlaceholder',
         'advancedParameterSelectedItems',
         () => {
           this.updateAdvancedCharts();
         }
       );
       
       // Override toggleOption to enforce dynamic parameter selection based on chart type
       if (this.multiSelectInstances.advancedParameter) {
         const paramInstance = this.multiSelectInstances.advancedParameter;
         const originalToggleOption = paramInstance.toggleOption.bind(paramInstance);
         const dashboardInstance = this; // Capture the dashboard instance
         
         // Helper function to update disabled states
         const updateDisabledStates = () => {
           const currentSelections = paramInstance.getSelectedValues();
           const maxLimit = dashboardInstance.getMaxParameterLimit();
           const shouldDisableOthers = currentSelections.length >= maxLimit;
           
           // Update ALL options in the dropdown
           paramInstance.dropdown.querySelectorAll('.multi-select-option').forEach(div => {
             const optionValue = div.getAttribute('data-value');
             const checkbox = div.querySelector('input[type="checkbox"]');
             const isSelected = currentSelections.includes(optionValue);
             
             if (isSelected) {
               // Selected options should always be enabled (so they can be deselected)
               div.classList.remove('opacity-50', 'cursor-not-allowed');
               div.style.pointerEvents = 'auto';
               if (checkbox) checkbox.disabled = false;
             } else {
               // Unselected options - enable or disable based on count
               if (shouldDisableOthers) {
                 // At limit - disable unselected options
                 div.classList.add('opacity-50', 'cursor-not-allowed');
                 div.style.pointerEvents = 'none';
                 if (checkbox) checkbox.disabled = true;
               } else {
                 // Below limit - enable all unselected options
                 div.classList.remove('opacity-50', 'cursor-not-allowed');
                 div.style.pointerEvents = 'auto';
                 if (checkbox) checkbox.disabled = false;
               }
             }
           });
         };
         
         paramInstance.toggleOption = (value) => {
           const currentSelections = paramInstance.getSelectedValues();
           const isCurrentlySelected = currentSelections.includes(value);
           
           // Get max limit based on current chart type
           const maxLimit = dashboardInstance.getMaxParameterLimit();
           
           // If selecting (not deselecting) and already at max limit, prevent selection
           if (!isCurrentlySelected && currentSelections.length >= maxLimit) {
             // Show alert to user with dynamic message
             const chartType = dashboardInstance.getChartType();
             if (chartType === 'stacked') {
               alert('Stacked Chart allows only 1 parameter selection.');
             } else {
               alert(`Maximum ${maxLimit} parameters can be selected for Bar Chart.`);
             }
             return; // Don't allow more than max limit selections
           }
           
           // Call original toggle to update the selection
           originalToggleOption(value);
           
           // Update disabled states immediately and after a delay to ensure DOM is updated
           updateDisabledStates();
           setTimeout(updateDisabledStates, 50);
           setTimeout(updateDisabledStates, 100);
         };
         
         // Store reference to update function for external use
         paramInstance.updateParameterDisabledStates = updateDisabledStates;
       }
 
      this.multiSelectInstances.advancedCountry = new MultiSelect(
        'advancedCountryFilterTrigger',
        'advancedCountryFilterDropdown',
        'advancedCountryFilterPlaceholder',
        'advancedCountrySelectedItems',
        (selectedValues) => {
          // Use the passed selectedValues if available, otherwise get from instance
          // This ensures we use the latest state even when called synchronously
          const selectedCountries = selectedValues || this.multiSelectInstances.advancedCountry.getSelectedValues();
          this.updatePortfolioOptions(selectedCountries, true);
          // Update asset options
          const selectedPortfolios = this.multiSelectInstances.advancedPortfolio.getSelectedValues();
          this.updateAssetOptions(selectedCountries, selectedPortfolios, true);
          // Update charts - use a small delay to ensure all state updates are complete
          setTimeout(() => {
            this.updateAdvancedCharts();
          }, 10);
        }
      );

      this.multiSelectInstances.advancedPortfolio = new MultiSelect(
        'advancedPortfolioFilterTrigger',
        'advancedPortfolioFilterDropdown',
        'advancedPortfolioFilterPlaceholder',
        'advancedPortfolioSelectedItems',
        (selectedValues) => {
          // Use the passed selectedValues if available, otherwise get from instance
          const selectedPortfolios = selectedValues || this.multiSelectInstances.advancedPortfolio.getSelectedValues();
          const selectedCountries = this.multiSelectInstances.advancedCountry.getSelectedValues();
          this.updateAssetOptions(selectedCountries, selectedPortfolios, true);
          // Update charts - use a small delay to ensure all state updates are complete
          setTimeout(() => {
            this.updateAdvancedCharts();
          }, 10);
        }
      );

      // Advanced Asset multi-select
      this.multiSelectInstances.advancedAsset = new MultiSelect(
        'advancedAssetNoFilterTrigger',
        'advancedAssetNoFilterDropdown',
        'advancedAssetNoFilterPlaceholder',
        'advancedAssetNoSelectedItems',
        (selectedValues) => {
          // Update charts - use a small delay to ensure all state updates are complete
          setTimeout(() => {
            this.updateAdvancedCharts();
          }, 10);
        }
      );
      
  

      // Parameter options will be set dynamically after data is loaded
      this.multiSelectInstances.advancedParameter.setOptions([]);

    } catch (error) {
      // Error initializing multi-select components
    }
  }

  /**
   * Initialize advanced components (calendar, charts)
   */
  initializeAdvancedComponents() {
    if (this.advancedComponentsInitialized) {
      return;
    }
    this.advancedComponentsInitialized = true;
    
    // 1. Make sure BestCalendar is available
    if (typeof window.BestCalendar === 'undefined') {
      // Retry after a short delay in case the script is still loading
      setTimeout(() => {
        this.advancedComponentsInitialized = false;
        this.initializeAdvancedComponents();
      }, 100);
      return;
    }
    
    const triggerEl = document.getElementById("advancedMonthMatrixTrigger");
    const pickerEl = document.getElementById("advancedMonthMatrixPicker");
    const labelEl = document.getElementById("advancedSelectedMonthLabel");

    if (triggerEl && pickerEl && labelEl) {
      try {
        // 2. Destroy existing instance if present
        if (window.currentBestCalendar && typeof window.currentBestCalendar.destroy === 'function') {
          window.currentBestCalendar.destroy();
          window.currentBestCalendar = null;
        }

        // 3. Create new instance
        const calendar = new window.BestCalendar({
          triggerId: "advancedMonthMatrixTrigger",
          pickerId: "advancedMonthMatrixPicker",
          labelId: "advancedSelectedMonthLabel",
          options: {
            range: true, // Always enable range mode to show all tabs (Month, Year, Range)
            onPeriodChange: (period) => {
              // Only log and process if there's an actual selection change
              if (period.range || period.month || period.year) {
                // Advanced Calendar period changed
                if (period.range) {
                  // Range selected - filter data by date range
                                      // Processing range selection
                  this.renderAdvancedChart("range", period.range);
                } else if (period.month) {
                  // Single month selected
                                      // Processing month selection
                  this.renderAdvancedChart("month", period.month);
                } else if (period.year) {
                  // Year selected
                                      // Processing year selection
                  this.renderAdvancedChart("year", period.year);
                }
              }
              // Don't trigger chart update for null selections during initialization
            },
          }
        });

        // Verify calendar instance was created properly
        if (!calendar || typeof calendar.setData !== 'function') {
          return;
        }

        // Store global ref
        window.currentBestCalendar = calendar;

        // Calendar mode toggle removed - all modes (Month, Year, Range) are now available as tabs

        // 4. Load calendar data
        if (this.dataManager && this.dataManager.yieldData && this.dataManager.yieldData.length > 0) {
          try {
            calendar.setData(this.dataManager.yieldData);
          } catch (error) {
            // Error setting calendar data
          }
        }
      } catch (error) {
        // Error initializing BestCalendar
      }
    } else {
      // Advanced calendar DOM elements not found
    }

    // Initialize advanced chart
    this.renderAdvancedChart();
  }



  /**
   * Render advanced chart with optional period filtering
   */
  renderAdvancedChart(periodType = null, periodValue = null) {
    // Initialize ECharts for advanced chart
    const chartDom = document.getElementById('advancedChart2');
    if (chartDom && typeof echarts !== 'undefined') {
      // Destroy existing chart instance if it exists
      if (window.advancedChart2 && typeof window.advancedChart2.dispose === 'function') {
        window.advancedChart2.dispose();
      }
      
      try {
        window.advancedChart2 = echarts.init(chartDom, null, {
          renderer: 'canvas',
          useDirtyRect: false
        });
        
        // Update chart with optional period filtering
        this.updateAdvancedChart2(periodType, periodValue);
        
        // Ensure chart uses full container size
        setTimeout(() => {
          if (window.advancedChart2 && typeof window.advancedChart2.resize === 'function') {
            window.advancedChart2.resize();
          }
        }, 100);
      } catch (error) {
        window.advancedChart2 = null;
      }
    } else {
      window.advancedChart2 = null;
    }
  }

  /**
   * Setup toggle functionality
   */
  setupToggles() {
    // Gauge section toggle
    const toggleGauges = document.getElementById('toggleGauges');
    if (toggleGauges) {
      toggleGauges.addEventListener('click', () => {
        const section = document.getElementById('gaugesSection');
        const arrow = document.getElementById('arrowGauges');
        if (section && arrow) {
          section.classList.toggle('max-h-0');
          section.classList.toggle('max-h-[2000px]');
          arrow.classList.toggle('rotate-180');
        }
      });
    }

    // Advanced bars section toggle
    const toggleAdvancedBars = document.getElementById('toggleAdvancedBars');
    if (toggleAdvancedBars) {
      toggleAdvancedBars.addEventListener('click', () => {
        const section = document.getElementById('advancedBarsContainer');
        const arrow = document.getElementById('arrowAdvancedBars');
        if (section && arrow) {
          section.classList.toggle('max-h-0');
          section.classList.toggle('max-h-[3000px]');
          arrow.classList.toggle('rotate-180');
        }
      });
    }
  }

  /**
   * Populate dropdowns with data
   */
  populateDropdowns() {
    try {
      // Populate gauge dropdowns with cascading logic
      const gaugeCountries = this.dataManager.getUniqueCountries('realtime');
      
      if (this.multiSelectInstances.gaugeCountry) {
        this.multiSelectInstances.gaugeCountry.setOptions(gaugeCountries);
        // Initialize portfolio options based on all countries
        this.updatePortfolioOptions([], false);
        // Initialize asset options based on all countries and portfolios
        this.updateAssetOptions([], [], false);
      }

      // Populate advanced dropdowns with cascading logic
      const advancedCountries = this.dataManager.getUniqueCountries('yield');
      
      if (this.multiSelectInstances.advancedCountry) {
        this.multiSelectInstances.advancedCountry.setOptions(advancedCountries);
        // Initialize portfolio options based on all countries
        this.updatePortfolioOptions([], true);
        // Initialize asset options based on all countries and portfolios
        this.updateAssetOptions([], [], true);
      }

      // Populate chart type options
      this.populateChartTypeOptions();

      // Populate parameter options for advanced charts
      this.populateParameterOptions();

      // Populate asset dropdowns (legacy method for backward compatibility)
      // Note: This might be redundant now since we're using cascading filters
      // this.populateAssetDropdowns();

    } catch (error) {
      // Error populating dropdowns
    }
  }

  /**
   * Get parameter label mapping - shared across functions
   */
  getParameterLabelMap() {
    // Define only the allowed parameters with their display labels
    // Based on CSV column names and user requirements
    return {
      'ic_approved_budget': 'IC Approved Budget',
      'expected_budget': 'Expected Budget',
      'actual_generation': 'Actual Generation',
      'weather_loss_or_gain': 'Weather Loss or Gain',
      'weather_corrected_budget': 'Weather Corrected Budget',
      'budgeted_irradiation': 'Budget Irradiation',
      'actual_irradiation': 'Actual Irradiation',
      'operation_budget': 'Operation Budget',
      'grid_curtailment': 'Actual Grid Curtailment',
      'grid_outage': 'Grid Outage',
      'grid_loss': 'Grid Loss',
      'string_failure': 'String Failure',
      'inverter_failure': 'Inverter Failure',
      'scheduled_outage_loss': 'Scheduled Outage',
      'breakdown_loss': 'Breakdown Loss',
      'unclassified_loss': 'Unclassified Loss or Gain',
      'bess_capacity_mwh': 'BESS Capacity MWh',
      'bess_generation_mwh': 'BESS Generation MWh',
      'dc_capacity_mw': 'DC Capacity MWp',
      'ac_capacity_mw': 'AC Capacity MW'
    };
  }

  /**
   * Populate chart type options
   */
  populateChartTypeOptions() {
    if (!this.multiSelectInstances.advancedChartType) {
      return;
    }

    const chartTypeOptions = [
      { value: 'bar', label: 'Bar Chart' },
      { value: 'stacked', label: 'Stacked Chart' }
    ];

    this.multiSelectInstances.advancedChartType.setOptions(chartTypeOptions);
    
    // Set default selection to "Bar Chart" if nothing is selected
    const currentSelection = this.multiSelectInstances.advancedChartType.getSelectedValues();
    if (currentSelection.length === 0) {
      this.multiSelectInstances.advancedChartType.setSelectedValues(['bar']);
      this.chartType = 'bar';
    }
  }

  /**
   * Populate parameter options for advanced charts
   */
  populateParameterOptions() {
    if (!this.dataManager.yieldData || this.dataManager.yieldData.length === 0) {
      return;
    }

    // Get the allowed parameters mapping
    const allowedParameters = this.getParameterLabelMap();

    // Check which parameters exist in the data
    const sampleRecord = this.dataManager.yieldData[0];
    const availableFields = Object.keys(sampleRecord);
    
    // Filter to only include allowed parameters that exist in the data
    const parameterOptions = Object.keys(allowedParameters)
      .filter(field => availableFields.includes(field)) // Only include if field exists in data
      .map(field => ({
        value: field,
        label: allowedParameters[field]
      }))
      .sort((a, b) => a.label.localeCompare(b.label)); // Sort alphabetically by label

    if (this.multiSelectInstances.advancedParameter) {
      this.multiSelectInstances.advancedParameter.setOptions(parameterOptions);
      
      // Always set default parameter to "Actual Generation" on initialization
      // Check if actual_generation exists in the parameter options
      const hasActualGeneration = parameterOptions.some(opt => opt.value === 'actual_generation');
      if (hasActualGeneration) {
        this.multiSelectInstances.advancedParameter.setSelectedValues(['actual_generation']);
        // Trigger chart update with default parameter
        setTimeout(() => {
          this.updateAdvancedChart2();
        }, 100);
      }
    }
  }

    /**
   * Populate asset dropdowns
   * This method is now handled by updateAssetOptions() which uses multi-select components
   */

  /**
   * Update advanced charts
   */
  updateAdvancedCharts() {
    this.updateAdvancedChart2();
    this.updateDynamicChartTitle();
  }

     /**
    * Update advanced chart 2 (ECharts)
    */
   updateAdvancedChart2(periodType = null, periodValue = null) {
     if (!window.advancedChart2 || typeof window.advancedChart2.setOption !== 'function') {
       // Try to reinitialize the chart
       const chartDom = document.getElementById('advancedChart2');
       if (chartDom && typeof echarts !== 'undefined') {
         try {
           if (window.advancedChart2 && typeof window.advancedChart2.dispose === 'function') {
             window.advancedChart2.dispose();
           }
           window.advancedChart2 = echarts.init(chartDom, null, {
             renderer: 'canvas',
             useDirtyRect: false
           });
         } catch (error) {
           return;
         }
       } else {
         return;
       }
     }
     
           let selectedParameters = this.multiSelectInstances.advancedParameter ? 
        this.multiSelectInstances.advancedParameter.getSelectedValues() : [];
     
           // If no parameters are selected, default to "Actual Generation"
           if (selectedParameters.length === 0) {
             selectedParameters = ['actual_generation'];
           }
      

    
    // Get filtered yield data based on current filters
    const currentFilters = {
      countries: this.multiSelectInstances.advancedCountry ? 
        this.multiSelectInstances.advancedCountry.getSelectedValues() : [],
      portfolios: this.multiSelectInstances.advancedPortfolio ? 
        this.multiSelectInstances.advancedPortfolio.getSelectedValues() : [],
      assets: this.multiSelectInstances.advancedAsset ? 
        this.multiSelectInstances.advancedAsset.getSelectedValues() : [],
      period: null
    };
    

    
    // Get period filter from BestCalendar or passed parameters
    if (periodType && periodValue) {
      // Use passed parameters for filtering
      if (periodType === 'range') {
        // Handle range filtering
        currentFilters.period = { range: periodValue };
        // Setting range filter from parameters
      } else {
        currentFilters.period = { [periodType]: periodValue };
                  // Setting period filter from parameters
      }
    } else if (window.currentBestCalendar) {
      try {
        const selectedPeriod = window.currentBestCalendar.getSelectedPeriod();
        if (selectedPeriod) {
          if (selectedPeriod.range) {
            // Range selected
            currentFilters.period = { range: selectedPeriod.range };
            // Setting range filter from calendar
          } else if (selectedPeriod.month || selectedPeriod.year) {
            // Single month or year selected.
            // To honor the user's preference to see the full dataset by default,
            // we will NOT lock to a single month here; the fallback below will set full range.
          }
        }
      } catch (error) {
        // Error getting period from BestCalendar
      }
    }
    
    // If no explicit period was provided or selected, default to full available range in yieldData
    if (!currentFilters.period && this.dataManager && Array.isArray(this.dataManager.yieldData) && this.dataManager.yieldData.length > 0) {
      const months = this.dataManager.yieldData
        .map(r => r && r.month)
        .filter(Boolean)
        .map(m => m.toString());
      if (months.length > 0) {
        const sorted = months.sort(); // 'YYYY-MM' sorts correctly lexicographically
        const start = sorted[0];
        const end = sorted[sorted.length - 1];
        currentFilters.period = { range: { start, end } };
        // Optional: sync calendar to reflect the full-range default if API exists
        try {
          if (window.currentBestCalendar && typeof window.currentBestCalendar.setRange === 'function') {
            window.currentBestCalendar.setRange(start, end);
          }
        } catch(_){}
      }
    }
    
    // Final currentFilters
    

    // Determine if we should stack by country or by portfolio
    const selectedCountries = currentFilters.countries || [];
    const selectedPortfolios = currentFilters.portfolios || [];
    const selectedAssets = currentFilters.assets || [];
    
    // Determine if we should show simple bar chart (no filters) or stacked chart (filters applied)
    // Important: Empty arrays mean "all" - filters should only be considered when explicitly selected
    // Check if filters are explicitly set (non-empty arrays)
    const hasCountryFilter = Array.isArray(selectedCountries) && selectedCountries.length > 0;
    const hasPortfolioFilter = Array.isArray(selectedPortfolios) && selectedPortfolios.length > 0;
    const hasAssetFilter = Array.isArray(selectedAssets) && selectedAssets.length > 0;
    const hasFilters = hasCountryFilter || hasPortfolioFilter || hasAssetFilter;
    
    // Get chart type - if no filters, force bar chart; if filters exist, use user selection or default to bar
    let effectiveChartType = this.getChartType();
    if (!hasFilters) {
      // No filters = simple bar chart showing totals only
      effectiveChartType = 'bar';
    } else {
      // Filters applied = use user's chart type selection (default to bar if not specified)
      if (effectiveChartType !== 'bar' && effectiveChartType !== 'stacked') {
        effectiveChartType = 'bar';
      }
    }
    
    // Only stack by portfolio if portfolios are explicitly selected
    // Otherwise, always stack by country (even when countries are selected)
    const stackByPortfolio = hasPortfolioFilter && selectedPortfolios.length > 0;
    
    // Get filtered data - respect country filter if countries are selected
    // Important: When filters are empty arrays, getFilteredYieldData returns all data (matchesFilter returns true for empty filters)
    const filteredYieldData = this.dataManager.getFilteredYieldData(currentFilters);
    
    // Helper to parse various month formats -> numeric month (1-12)
    function parseMonthNumber(monthStr) {
      if (!monthStr || typeof monthStr !== 'string') return null;
      const s = monthStr.trim();
      // Format: YYYY-MM
      const iso = s.match(/^\s*(\d{4})-(\d{1,2})\s*$/);
      if (iso) {
        return parseInt(iso[2]);
      }
      // Format: Mon YYYY or Month YYYY
      const monthNames = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
      const fullMonthNames = ['January','February','March','April','May','June','July','August','September','October','November','December'];
      const parts = s.split(/\s+/);
      if (parts.length >= 2) {
        let idx = monthNames.indexOf(parts[0]);
        if (idx === -1) idx = fullMonthNames.indexOf(parts[0]);
        if (idx !== -1) return idx + 1;
      }
      return null;
    }

    // Process yield data for the chart with dual y-axis
     const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
     const series = [];
     
     // Determine which months to process based on period type
     let monthsToProcess = months;
     let monthLabels = months;
     
     if ((periodType === 'range' && periodValue && periodValue.start && periodValue.end) || 
         (currentFilters.period && currentFilters.period.range && currentFilters.period.range.start && currentFilters.period.range.end)) {
       // For range selection, only process months in the range
       // Use periodValue if available, otherwise use currentFilters.period.range
       const rangeStart = periodValue ? periodValue.start : currentFilters.period.range.start;
       const rangeEnd = periodValue ? periodValue.end : currentFilters.period.range.end;
       const startMonth = parseInt(rangeStart.split('-')[1]);
       const endMonth = parseInt(rangeEnd.split('-')[1]);
       const year = rangeStart.split('-')[0];
       
       // Range processing
       
       // Create array of months in range
       monthsToProcess = [];
       monthLabels = [];
       for (let i = startMonth; i <= endMonth; i++) {
         const monthName = months[i - 1];
         monthsToProcess.push(monthName);
         monthLabels.push(`${monthName} ${year}`);
       }
       
       // Generated monthsToProcess and monthLabels
     }
     
     // Chart processing setup
     
    
     
     // Separate parameters by type (MWh vs Percentage)
     const mwhParameters = selectedParameters.filter(param => {
       const paramLower = param.toLowerCase();
       
      
       
       // Hardcoded list of known percentage parameters (exact matches only)
       const knownPercentageParams = [
         'expected_pr', 'actual_pr'
       ];
       
       // Hardcoded list of known MWh parameters
       const knownMwhParams = [
         'ic_approved_budget', 'expected_budget', 'actual_generation',
         'budget', 'generation', 'mwh', 'kwh', 'irradiation', 'capacity',
         'loss', 'gain', 'weather_loss_or_gain'
       ];
       
       // Check if it's a known percentage parameter
       const isKnownPercentage = knownPercentageParams.includes(param);
       
       // Check if it's a known MWh parameter
       const isKnownMwh = knownMwhParams.some(known => 
         paramLower.includes(known.toLowerCase())
       );
       
       // If it's explicitly a known percentage parameter, exclude it
       if (isKnownPercentage) {
         return false;
       }
       
       // If it's explicitly a known MWh parameter, include it
       if (isKnownMwh) {
         return true;
       }
       
       // Default to MWh for unknown parameters (safer assumption)
       return true;
     });
     
     const percentageParameters = selectedParameters.filter(param => {
       const paramLower = param.toLowerCase();
       
       // Hardcoded list of known percentage parameters (exact matches only)
       const knownPercentageParams = [
         'expected_pr', 'actual_pr'
       ];
       
       const isPercentage = knownPercentageParams.includes(param);
       return isPercentage;
     });
     

     
     // Use consistent normalization for matching
     const normalizeCountryName = (country) => {
       if (!country) return '';
       return String(country).trim();
     };
     
     const normalizePortfolioName = (portfolio) => {
       if (!portfolio) return '';
       return String(portfolio).trim();
     };
     
    // Determine what to stack by:
    // STACKED CHART BEHAVIOR:
    // 1. DEFAULT: Stack by COUNTRY (when Stacked Chart is selected without portfolio filter)
    // 2. PORTFOLIO-WISE: Stack by PORTFOLIO (when user selects portfolio filter)
    // 3. If no filters, show simple totals (no stacking)
    let stackItems = [];
    let stackItemType = 'country';
    
    if (!hasFilters) {
      // No filters selected - show simple bar chart with totals only
      // Don't set stackItems, we'll create a single series for totals
      stackItems = [];
    } else if (stackByPortfolio) {
      // Stack by portfolio ONLY when portfolios are explicitly selected by user
      // This shows portfolio-wise breakdown in the stacked chart
      stackItemType = 'portfolio';
      const uniquePortfolios = [...new Set(filteredYieldData
        .map(row => normalizePortfolioName(row.portfolio || row.portfolio_name || row.portfolio_code || ''))
        .filter(portfolio => portfolio !== '' && portfolio !== 'Unknown')
      )].sort();
      stackItems = uniquePortfolios;
    } else {
      // Stack by country (DEFAULT behavior for stacked chart)
      // This applies when:
      // - Stacked Chart is selected WITHOUT portfolio filter (shows country-wise breakdown)
      // - Countries are selected but portfolios are not
      const uniqueCountries = [...new Set(filteredYieldData
        .map(row => normalizeCountryName(row.country || row.rowCountry || ''))
        .filter(country => country !== '' && country !== 'Unknown')
      )].sort();
      stackItems = uniqueCountries;
    }
     
    // Color palette (reused for both countries and portfolios)
    const stackColors = ['#0072CE', '#16a34a', '#dc2626', '#ea580c', '#7c3aed', '#0891b2', '#059669', '#f59e0b', '#ec4899', '#6366f1'];
    
    // If no filters, calculate totals only and skip stackItem processing
    let sortedStackItems = [];
    let colorIndexMap = new Map();
    
    if (!hasFilters) {
      // For simple bar chart, we'll create a single total series - skip stackItem calculations
      sortedStackItems = [];
    } else {
      // Calculate totals for each stackItem to sort by largest first (bottom of stack)
      // This preserves the original index for color mapping
      const stackItemTotals = stackItems.map((stackItem, originalIndex) => {
      let total = 0;
      
      // Calculate total across all months for the first MWh parameter (if any)
      if (mwhParameters.length > 0) {
        const param = mwhParameters[0];
        monthsToProcess.forEach((month, index) => {
          let monthData;
          
          if ((periodType === 'range' && periodValue && periodValue.start && periodValue.end) || 
              (currentFilters.period && currentFilters.period.range && currentFilters.period.range.start && currentFilters.period.range.end)) {
            const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
            const monthNumber = monthNames.indexOf(month) + 1;
            const rangeStart = periodValue ? periodValue.start : currentFilters.period.range.start;
            const rangeEnd = periodValue ? periodValue.end : currentFilters.period.range.end;
            const startMonth = parseInt(rangeStart.split('-')[1]);
            const endMonth = parseInt(rangeEnd.split('-')[1]);
            const targetYear = rangeStart.split('-')[0];
            
            if (monthNumber >= startMonth && monthNumber <= endMonth) {
              monthData = filteredYieldData.filter(row => {
                const rowMonth = row.month;
                if (!rowMonth) return false;
                const rowMonthNum = parseMonthNumber(rowMonth);
                const rowYear = String(rowMonth).slice(0, 4);
                
                if (stackItemType === 'portfolio') {
                  const rowPortfolio = normalizePortfolioName(row.portfolio || row.portfolio_name || row.portfolio_code || '');
                  return rowMonthNum === monthNumber && rowYear === targetYear && rowPortfolio === stackItem;
                } else {
                  const rowCountry = normalizeCountryName(row.country || row.rowCountry || '');
                  return rowMonthNum === monthNumber && rowYear === targetYear && rowCountry === stackItem;
                }
              });
            } else {
              monthData = [];
            }
          } else {
            monthData = filteredYieldData.filter(row => {
              const rowMonth = row.month;
              if (!rowMonth) return false;
              const rowMonthNum = parseMonthNumber(rowMonth);
              const targetMonthNumber = index + 1;
              
              if (stackItemType === 'portfolio') {
                const rowPortfolio = normalizePortfolioName(row.portfolio || row.portfolio_name || row.portfolio_code || '');
                return rowMonthNum === targetMonthNumber && rowPortfolio === stackItem;
              } else {
                const rowCountry = normalizeCountryName(row.country || row.rowCountry || '');
                return rowMonthNum === targetMonthNumber && rowCountry === stackItem;
              }
            });
          }
          
          const sum = monthData.reduce((acc, row) => {
            const value = parseFloat(row[param]) || 0;
            return acc + (isNaN(value) ? 0 : value);
          }, 0);
          total += sum;
        });
      }
      
      return {
        stackItem: stackItem,
        total: total,
        originalIndex: originalIndex
      };
      });
      
      // Sort by total descending (largest first = bottom of stack)
      stackItemTotals.sort((a, b) => b.total - a.total);
      
      // Create sorted stackItems array with color mapping preserved
      sortedStackItems = stackItemTotals.map(item => item.stackItem);
      stackItemTotals.forEach((item, sortedIndex) => {
        colorIndexMap.set(item.stackItem, item.originalIndex);
      });
    }
    
    // Process MWh parameters (left y-axis) - create series based on filter state
    mwhParameters.forEach((param, paramIndex) => {
      // First, calculate monthly totals for this parameter to help with label positioning and totals
      const monthlyTotals = monthsToProcess.map((month, index) => {
         let monthData;
         if ((periodType === 'range' && periodValue && periodValue.start && periodValue.end) || 
             (currentFilters.period && currentFilters.period.range && currentFilters.period.range.start && currentFilters.period.range.end)) {
           const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
           const monthNumber = monthNames.indexOf(month) + 1;
           const rangeStart = periodValue ? periodValue.start : currentFilters.period.range.start;
           const rangeEnd = periodValue ? periodValue.end : currentFilters.period.range.end;
           const startMonth = parseInt(rangeStart.split('-')[1]);
           const endMonth = parseInt(rangeEnd.split('-')[1]);
           const targetYear = rangeStart.split('-')[0];
           
           if (monthNumber >= startMonth && monthNumber <= endMonth) {
             monthData = filteredYieldData.filter(row => {
               const rowMonth = row.month;
               if (!rowMonth) return false;
               const rowMonthNum = parseMonthNumber(rowMonth);
               const rowYear = String(rowMonth).slice(0, 4);
               return rowMonthNum === monthNumber && rowYear === targetYear;
             });
           } else {
             monthData = [];
           }
         } else {
           monthData = filteredYieldData.filter(row => {
             const rowMonth = row.month;
             if (!rowMonth) return false;
             const rowMonthNum = parseMonthNumber(rowMonth);
             const targetMonthNumber = index + 1;
             return rowMonthNum === targetMonthNumber;
           });
         }
         
         return monthData.reduce((total, row) => {
           const value = parseFloat(row[param]) || 0;
           return total + (isNaN(value) ? 0 : value);
         }, 0);
       });
       
       // Determine chart rendering based on filters and chart type
       if (!hasFilters || effectiveChartType === 'bar') {
         // No filters OR filters + bar chart = single cumulative series
         // For bar chart with filters, monthlyTotals already contains cumulative values
         const paramLabel = param.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
         const seriesName = paramLabel;
         
         series.push({
           name: seriesName,
           type: 'bar',
           stack: null, // No stacking for bar chart
           yAxisIndex: 0, // Left y-axis for MWh values
           data: monthlyTotals, // Use totals/cumulative values directly
           itemStyle: {
             color: stackColors[paramIndex % stackColors.length] // Use different color for each parameter
           },
           originalParam: param,
           label: {
             show: true,
             position: 'top', // Labels on top for bar chart
             formatter: function(params) {
               const value = params.value;
               // Handle zero values - don't show label for zero
               if (value === 0) return '';
               
               // Special handling for MWh parameters - show K format for data labels (integers only)
               if (param === 'ic_approved_budget' || param === 'expected_budget' || param === 'actual_generation') {
                 if (Math.abs(value) >= 1000) {
                   const kValue = Math.round(value / 1000);
                   return kValue + 'K';
                 } else {
                   return Math.round(value); // Show only integers
                 }
               }
               
               // Format large numbers with K suffix (both positive and negative)
               if (Math.abs(value) >= 1000) {
                 const kValue = Math.round(value / 1000);
                 return kValue + 'K';
               }
               
               // Return rounded integer value for smaller numbers
               return Math.round(value);
             },
             fontSize: function() {
               // Dynamically calculate font size based on chart width and number of data points
               const chartWidth = window.advancedChart2 ? window.advancedChart2.getWidth() : 800;
               const dataPoints = months.length;
               const barWidth = chartWidth / (dataPoints * 2); // Approximate bar width
               
               // Adjust font size based on bar width
               if (barWidth < 30) return 8;
               if (barWidth < 50) return 9;
               if (barWidth < 80) return 10;
               if (barWidth < 120) return 11;
               return 12;
             },
             fontWeight: 'bold',
             color: '#333'
           }
         });
       } else {
         // Filters applied + stacked chart = multiple stacked series
         // Create a series for each stack item (country or portfolio) - use sorted order
         sortedStackItems.forEach((stackItem, sortedIndex) => {
         // Get original color index from map
         const originalColorIndex = colorIndexMap.get(stackItem);
         const stackIndex = originalColorIndex !== undefined ? originalColorIndex : sortedIndex;
         const monthlyData = monthsToProcess.map((month, index) => {
           // Filter data for this month and stack item
           let monthData;
           
            if ((periodType === 'range' && periodValue && periodValue.start && periodValue.end) || 
                (currentFilters.period && currentFilters.period.range && currentFilters.period.range.start && currentFilters.period.range.end)) {
             // For range, filter by the specific month in the range
             const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
             const monthNumber = monthNames.indexOf(month) + 1; // Get month number from month name
             const rangeStart = periodValue ? periodValue.start : currentFilters.period.range.start;
             const rangeEnd = periodValue ? periodValue.end : currentFilters.period.range.end;
             const startMonth = parseInt(rangeStart.split('-')[1]);
             const endMonth = parseInt(rangeEnd.split('-')[1]);
             const targetYear = rangeStart.split('-')[0];
             
             // Only process if this month is within our range
             if (monthNumber >= startMonth && monthNumber <= endMonth) {
               monthData = filteredYieldData.filter(row => {
                  const rowMonth = row.month;
                  if (!rowMonth) return false;
                  const rowMonthNum = parseMonthNumber(rowMonth);
                  const rowYear = String(rowMonth).slice(0, 4);
                  
                  // Match by stack item type
                  if (stackItemType === 'portfolio') {
                    const rowPortfolio = normalizePortfolioName(row.portfolio || row.portfolio_name || row.portfolio_code || '');
                    return rowMonthNum === monthNumber && rowYear === targetYear && rowPortfolio === stackItem;
                  } else {
                    const rowCountry = normalizeCountryName(row.country || row.rowCountry || '');
                    return rowMonthNum === monthNumber && rowYear === targetYear && rowCountry === stackItem;
                  }
               });
             } else {
               monthData = []; // No data for months outside the range
             }
           } else {
             // For single month/year, use original logic
             monthData = filteredYieldData.filter(row => {
                const rowMonth = row.month;
                if (!rowMonth) return false;
                const rowMonthNum = parseMonthNumber(rowMonth);
                const targetMonthNumber = index + 1;
                
                // Match by stack item type
                if (stackItemType === 'portfolio') {
                  const rowPortfolio = normalizePortfolioName(row.portfolio || row.portfolio_name || row.portfolio_code || '');
                  return rowMonthNum === targetMonthNumber && rowPortfolio === stackItem;
                } else {
                  const rowCountry = normalizeCountryName(row.country || row.rowCountry || '');
                  return rowMonthNum === targetMonthNumber && rowCountry === stackItem;
                }
             });
           }
           
           // Calculate sum for this parameter, month, and stack item
           const sum = monthData.reduce((total, row) => {
             const value = parseFloat(row[param]) || 0;
             if (isNaN(value)) return total; // Skip NaN values
             return total + value;
           }, 0);
           
           const roundedSum = Math.round(sum * 100) / 100; // Round to 2 decimal places
           
           return roundedSum;
         });
       
         const paramLabel = param.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
         const seriesName = stackItemType === 'portfolio' ? `${stackItem} - ${paramLabel}` : `${stackItem} - ${paramLabel}`;
         
         // Determine if this is the last (top) series for this parameter - add total labels
         const isLastSeries = sortedIndex === sortedStackItems.length - 1;
         
         // Use effective chart type (auto-determined based on filters)
         const isStacked = effectiveChartType === 'stacked';
         
         const seriesConfig = {
           name: seriesName,
           type: 'bar',
           stack: isStacked ? param : null, // Only stack if chart type is 'stacked'
           yAxisIndex: 0, // Left y-axis for MWh values
           data: monthlyData,
           itemStyle: {
             color: stackColors[stackIndex % stackColors.length]
           },
           // Store the original parameter name for debugging
           originalParam: param,
           originalStackItem: stackItem,
           stackItemType: stackItemType,
           label: {
             show: true,
             position: isStacked ? 'inside' : 'top', // Inside for stacked, top for bar chart
             formatter: function(params) {
               const value = params.value;
               // Handle zero values - don't show label for zero
               if (value === 0) return '';
               
               // Get total for this month (using pre-calculated monthlyTotals)
               const monthIndex = params.dataIndex;
               const totalValue = monthlyTotals[monthIndex] || 0;
               
               // Hide label for very small segments (< 3% of total) to avoid clutter and overlaps
               if (totalValue > 0 && (value / totalValue) < 0.03) {
                 return ''; // Hide label for segments < 3% of total
               }
               
               // Special handling for MWh parameters - show K format for data labels (integers only)
               if (param === 'ic_approved_budget' || param === 'expected_budget' || param === 'actual_generation') {
                 if (Math.abs(value) >= 1000) {
                   const kValue = Math.round(value / 1000);
                   return kValue + 'K';
                 } else {
                   return Math.round(value); // Show only integers
                 }
               }
               
               // Format large numbers with K suffix (both positive and negative)
               if (Math.abs(value) >= 1000) {
                 const kValue = Math.round(value / 1000);
                 return kValue + 'K';
               }
               
               // Return rounded integer value for smaller numbers
               return Math.round(value);
             },
             fontSize: function() {
               // Dynamically calculate font size based on chart width and number of data points
               const chartWidth = window.advancedChart2 ? window.advancedChart2.getWidth() : 800;
               const dataPoints = months.length;
               const barWidth = chartWidth / (dataPoints * 2); // Approximate bar width
               
               // Adjust font size based on bar width
               if (barWidth < 30) return 8;
               if (barWidth < 50) return 9;
               if (barWidth < 80) return 10;
               if (barWidth < 120) return 11;
               return 12;
             },
             fontWeight: 'bold',
             color: '#333'
           }
         };
         
         // For stacked charts, we'll add total labels using a separate invisible series after all series are added
         // This will be handled after the series.push() call
         
         series.push(seriesConfig);
         }); // End sortedStackItems.forEach
       } // End else (hasFilters)
     }); // End mwhParameters.forEach
     
          // Process percentage parameters (right y-axis) - create series based on filter state
     percentageParameters.forEach((param, paramIndex) => {
        if (!hasFilters || effectiveChartType === 'bar') {
          // No filters OR filters + bar chart = single cumulative average series
          // Calculate averages for all filtered data (cumulative)
          const monthlyAverages = monthsToProcess.map((month, index) => {
            let monthData;
            
            if ((periodType === 'range' && periodValue && periodValue.start && periodValue.end) || 
                (currentFilters.period && currentFilters.period.range && currentFilters.period.range.start && currentFilters.period.range.end)) {
              const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
              const monthNumber = monthNames.indexOf(month) + 1;
              const rangeStart = periodValue ? periodValue.start : currentFilters.period.range.start;
              const rangeEnd = periodValue ? periodValue.end : currentFilters.period.range.end;
              const startMonth = parseInt(rangeStart.split('-')[1]);
              const endMonth = parseInt(rangeEnd.split('-')[1]);
              const targetYear = rangeStart.split('-')[0];
              
              if (monthNumber >= startMonth && monthNumber <= endMonth) {
                monthData = filteredYieldData.filter(row => {
                  const rowMonth = row.month;
                  if (!rowMonth) return false;
                  const rowMonthNum = parseMonthNumber(rowMonth);
                  const rowYear = String(rowMonth).slice(0, 4);
                  return rowMonthNum === monthNumber && rowYear === targetYear;
                });
              } else {
                monthData = [];
              }
            } else {
              monthData = filteredYieldData.filter(row => {
                const rowMonth = row.month;
                if (!rowMonth) return false;
                const rowMonthNum = parseMonthNumber(rowMonth);
                const targetMonthNumber = index + 1;
                return rowMonthNum === targetMonthNumber;
              });
            }
            
            const validValues = monthData
              .map(row => parseFloat(row[param]))
              .filter(value => !isNaN(value) && value !== null);
            
            const average = validValues.length > 0 ? 
              validValues.reduce((sum, val) => sum + val, 0) / validValues.length : 0;
            
            return Math.round(average * 100) / 100;
          });
          
          const paramLabel = param.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
          const seriesName = paramLabel;
          
          series.push({
            name: seriesName,
            type: 'bar',
            stack: null, // No stacking for simple bar chart
            yAxisIndex: 1, // Right y-axis for percentage values
            data: monthlyAverages,
            itemStyle: {
              color: stackColors[(mwhParameters.length + paramIndex) % stackColors.length] // Use different color, offset by MWh params
            },
            originalParam: param,
            label: {
              show: true,
              position: 'top', // Labels on top for simple bar chart
              formatter: function(params) {
                const value = params.value;
                // Handle zero values - don't show label for zero
                if (value === 0) return '';
                
                // For percentage parameters, we still want to hide very small segments
                if (Math.abs(value) < 0.01) {
                  return '';
                }
                
                // Convert decimal to percentage (e.g., 0.80 -> 80%)
                return Math.round(value * 100) + '%';
              },
              fontSize: function() {
                const chartWidth = window.advancedChart2 ? window.advancedChart2.getWidth() : 800;
                const dataPoints = months.length;
                const barWidth = chartWidth / (dataPoints * 2);
                
                if (barWidth < 30) return 8;
                if (barWidth < 50) return 9;
                if (barWidth < 80) return 10;
                if (barWidth < 120) return 11;
                return 12;
              },
              fontWeight: 'bold',
              color: '#333'
            }
          });
        } else {
          // Filters applied + stacked chart = multiple stacked series
          // Create a series for each stack item (country or portfolio) - use sorted order
          sortedStackItems.forEach((stackItem, sortedIndex) => {
          // Get original color index from map
          const originalColorIndex = colorIndexMap.get(stackItem);
          const stackIndex = originalColorIndex !== undefined ? originalColorIndex : sortedIndex;
          // Use the same month processing logic as MWh parameters
          const monthlyData = monthsToProcess.map((month, index) => {
            // Filter data for this month and stack item
            let monthData;
            
            if ((periodType === 'range' && periodValue && periodValue.start && periodValue.end) || 
                (currentFilters.period && currentFilters.period.range && currentFilters.period.range.start && currentFilters.period.range.end)) {
              // For range, filter by the specific month in the range
              const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
              const monthNumber = monthNames.indexOf(month) + 1; // Get month number from month name
              const rangeStart = periodValue ? periodValue.start : currentFilters.period.range.start;
              const rangeEnd = periodValue ? periodValue.end : currentFilters.period.range.end;
              const startMonth = parseInt(rangeStart.split('-')[1]);
              const endMonth = parseInt(rangeEnd.split('-')[1]);
              const targetYear = rangeStart.split('-')[0];
              
              // Only process if this month is within our range
              if (monthNumber >= startMonth && monthNumber <= endMonth) {
                monthData = filteredYieldData.filter(row => {
                  const rowMonth = row.month;
                  if (!rowMonth) return false;
                  const rowMonthNum = parseMonthNumber(rowMonth);
                  const rowYear = String(rowMonth).slice(0, 4);
                  
                  // Match by stack item type
                  if (stackItemType === 'portfolio') {
                    const rowPortfolio = normalizePortfolioName(row.portfolio || row.portfolio_name || row.portfolio_code || '');
                    return rowMonthNum === monthNumber && rowYear === targetYear && rowPortfolio === stackItem;
                  } else {
                    const rowCountry = normalizeCountryName(row.country || row.rowCountry || '');
                    return rowMonthNum === monthNumber && rowYear === targetYear && rowCountry === stackItem;
                  }
                });
              } else {
                monthData = []; // No data for months outside the range
              }
            } else {
              // For single month/year, use original logic
              monthData = filteredYieldData.filter(row => {
                const rowMonth = row.month;
                if (!rowMonth) return false;
                const rowMonthNum = parseMonthNumber(rowMonth);
                const targetMonthNumber = index + 1;
                
                // Match by stack item type
                if (stackItemType === 'portfolio') {
                  const rowPortfolio = normalizePortfolioName(row.portfolio || row.portfolio_name || row.portfolio_code || '');
                  return rowMonthNum === targetMonthNumber && rowPortfolio === stackItem;
                } else {
                  const rowCountry = normalizeCountryName(row.country || row.rowCountry || '');
                  return rowMonthNum === targetMonthNumber && rowCountry === stackItem;
                }
              });
            }
            
            // Calculate weighted average for percentage parameters
            // For PR, we need to calculate properly - sum of (value * weight) / sum of weights
            // For simplicity, using average if weights aren't available
            const validValues = monthData
              .map(row => parseFloat(row[param]))
              .filter(value => !isNaN(value) && value !== null);
            
            const average = validValues.length > 0 ? 
              validValues.reduce((sum, val) => sum + val, 0) / validValues.length : 0;
            
            const roundedAverage = Math.round(average * 100) / 100; // Round to 2 decimal places
            
            return roundedAverage;
          });
        
          const paramLabel = param.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
          const seriesName = `${stackItem} - ${paramLabel}`;
          
          // Use effective chart type (auto-determined based on filters)
          const isStacked = effectiveChartType === 'stacked';
          
          series.push({
            name: seriesName,
            type: 'bar', // Use bar chart for percentage values
            stack: isStacked ? param : null, // Only stack if chart type is 'stacked'
            yAxisIndex: 1, // Right y-axis for percentage values
            data: monthlyData,
            itemStyle: {
              color: stackColors[stackIndex % stackColors.length]
            },
            // Store the original parameter name for debugging
            originalParam: param,
            originalStackItem: stackItem,
            stackItemType: stackItemType,
            label: {
              show: true,
              position: isStacked ? 'inside' : 'top', // Inside for stacked, top for bar chart
              formatter: function(params) {
                const value = params.value;
                // Handle zero values - don't show label for zero
                if (value === 0) return '';
                
                // For percentage parameters, we still want to hide very small segments
                // But since percentages are already normalized, we can use a simple threshold
                // Hide if value is less than 0.01 (1%)
                if (Math.abs(value) < 0.01) {
                  return '';
                }
                
                // Convert decimal to percentage (e.g., 0.80 -> 80%)
                return Math.round(value * 100) + '%';
              },
              fontSize: function() {
                // Dynamically calculate font size based on chart width and number of data points
                const chartWidth = window.advancedChart2 ? window.advancedChart2.getWidth() : 800;
                const dataPoints = months.length;
                const barWidth = chartWidth / (dataPoints * 2); // Approximate bar width
                
                // Adjust font size based on bar width
                if (barWidth < 30) return 8;
                if (barWidth < 50) return 9;
                if (barWidth < 80) return 10;
                if (barWidth < 120) return 11;
                return 12;
              },
              fontWeight: 'bold',
              color: '#333'
            }
          });
          }); // End sortedStackItems.forEach
        } // End else (hasFilters)
      }); // End percentageParameters.forEach
      
      // Total labels will be added after the option is built using a transparent overlay series
    
      // --- Build ECharts option ---
      const option = {
         grid: {
           top: effectiveChartType === 'stacked' ? '12%' : '3%',
           left: '4%',
           right: '4%',
           bottom: '6%',
           containLabel: true
         },
         tooltip: { 
           trigger: 'axis',
           axisPointer: { type: 'shadow' },
           formatter: function(params) {
             // Helper function to format numbers with comma separators (no K/M)
             const formatNumber = (num) => {
               if (isNaN(num) || num === null || num === undefined) return '0';
               // Round to 2 decimal places, then format with commas
               const rounded = Math.round(num * 100) / 100;
               return rounded.toLocaleString('en-US', {
                 minimumFractionDigits: 0,
                 maximumFractionDigits: 2
               });
             };
             
             let result = params[0].axisValue + '<br/>';
             let mwhTotal = 0; // Track total for MWh parameters
             let isStackedChart = false;
             
             params.forEach(param => {
               // Skip "Total Labels" series from display
               if (param.seriesName === 'Total Labels' || param.seriesName.startsWith('Total_')) {
                 return;
               }
               
               let value = param.value;
               let formattedValue = '';
               let shouldAddToTotal = false;
               
               // Check if this is a PR parameter first (but exclude IC APPROVED BUDGET)
               if ((param.seriesName.includes('PR') || param.seriesName.includes('pr') || (param.originalParam && (param.originalParam.includes('pr') || param.originalParam.includes('PR')))) && 
                   !param.seriesName.includes('APPROVED') && 
                   !param.seriesName.includes('approved') &&
                   !param.originalParam?.includes('approved')) {
                 // Convert decimal to percentage (e.g., 0.80 -> 80%)
                 const percentage = Math.round(value * 100);
                 formattedValue = formatNumber(percentage) + '%';
                
               } 
               // Check if this is IC Approved Budget
               else if (param.seriesName.includes('IC APPROVED BUDGET') || param.seriesName.includes('IC_APPROVED_BUDGET') || param.seriesName.includes('ic_approved_budget') || param.seriesName.includes('BUDGET') || (param.originalParam && param.originalParam === 'ic_approved_budget')) {
                 // For IC Approved Budget, show as MWh with comma separators
                 // Check if the value is abnormally large (might be a percentage)
                 if (Math.abs(value) > 1000000) {
                   // If it's a very large number, it might be a percentage, so divide by 100
                   value = value / 100;
                 }
                 formattedValue = formatNumber(value) + ' MWh';
                 // Check if this is a stacked series (series name contains " - " indicating country/portfolio series)
                 if (param.seriesName && param.seriesName.includes(' - ')) {
                   shouldAddToTotal = true;
                 }
                
               } 
               // Check if this is Expected Budget
               else if (param.seriesName.includes('EXPECTED BUDGET') || param.seriesName.includes('EXPECTED_BUDGET') || param.seriesName.includes('expected_budget') || (param.originalParam && param.originalParam === 'expected_budget')) {
                 // For Expected Budget, show as MWh with comma separators
                 formattedValue = formatNumber(value) + ' MWh';
                 // Check if this is a stacked series (series name contains " - " indicating country/portfolio series)
                 if (param.seriesName && param.seriesName.includes(' - ')) {
                   shouldAddToTotal = true;
                 }
               } 
               // Check if this is Actual Generation
               else if (param.seriesName.includes('ACTUAL GENERATION') || param.seriesName.includes('ACTUAL_GENERATION') || param.seriesName.includes('actual_generation') || (param.originalParam && param.originalParam === 'actual_generation')) {
                 // For Actual Generation, show as MWh with comma separators
                 formattedValue = formatNumber(value) + ' MWh';
                 // Check if this is a stacked series (series name contains " - " indicating country/portfolio series)
                 if (param.seriesName && param.seriesName.includes(' - ')) {
                   shouldAddToTotal = true;
                 }
               } 
               // Default formatting for other parameters - use comma separators, no K/M
               else {
                 formattedValue = formatNumber(value);
                 // Check if this is a stacked MWh series (series name contains " - " indicating country/portfolio series)
                 if (param.seriesName && param.seriesName.includes(' - ') && !param.seriesName.includes('PR')) {
                   shouldAddToTotal = true;
                 }
               }
               
               // Add to total if this is a stacked MWh series
               if (shouldAddToTotal) {
                 mwhTotal += parseFloat(value) || 0;
                 isStackedChart = true;
               }
               
               result += param.marker + ' ' + param.seriesName + ': ' + formattedValue + '<br/>';
             });
             
             // Add total value for stacked charts
             if (isStackedChart && mwhTotal > 0) {
               const totalFormatted = formatNumber(mwhTotal) + ' MWh';
               result += '<div style="margin-top: 4px; padding-top: 4px; border-top: 1px solid #ddd;">';
               result += '<strong>Total: ' + totalFormatted + '</strong>';
               result += '</div>';
             }
             
             return result;
           }
         },
         legend: { 
           bottom: 10,
           data: series.map(s => s.name).filter(name => !name.startsWith('Total_') && name !== 'Total Labels'), // Exclude total label series from legend
           textStyle: { 
             fontSize: 12,
             fontWeight: 'bold'
           },
           type: 'scroll', // Use scrollable legend if there are many countries
           pageButtonItemGap: 5,
           pageButtonGap: 10,
           pageIconSize: 12
         },
         xAxis: { 
           type: 'category',
           data: monthLabels, // Use monthLabels instead of months for proper range display
           axisLabel: {
             rotate: 0,
             fontWeight: 'bold'
           },
           nameTextStyle: {
             fontWeight: 'bold'
           }
         },
        yAxis: [
                     {
             // Left y-axis for MWh values
             type: 'value',
             name: 'MWh',
             nameLocation: 'middle',
             nameGap: 50,
             position: 'left',
             axisLabel: {
               fontWeight: 'bold',
               formatter: function(value) {
                 if (Math.abs(value) >= 1000) {
                   const kValue = Math.round(value / 1000);
                   return kValue + 'K';
                 }
                 return Math.round(value);
               }
             },
             nameTextStyle: {
               fontWeight: 'bold'
             }
           },
                     {
             // Right y-axis for percentage values
             type: 'value',
             name: '%',
             nameLocation: 'middle',
             nameGap: 50,
             position: 'right',
             min: function(value) {
               // Ensure negative values are displayed above 0% line
               return Math.min(0, value.min);
             },
             axisLabel: {
               fontWeight: 'bold',
               formatter: function(value) {
                 // Convert decimal to percentage (e.g., 0.80 -> 80%)
                 return Math.round(value * 100) + '%';
               }
             },
             nameTextStyle: {
               fontWeight: 'bold'
             }
           }
        ],
        series: series
      };
    
      // --- ✅ Add centered total labels for stacked bars ---
      if (effectiveChartType === 'stacked' && mwhParameters.length > 0) {
        const totalValues = [];
        const monthKeys = monthLabels || months;
        
        // Calculate totals for each month (sum across all stacked MWh series for that month)
        monthKeys.forEach((month, idx) => {
          let total = 0;
          series.forEach(s => {
            // Only sum stacked MWh series (yAxisIndex === 0 and has stack property)
            if (s.stack && s.yAxisIndex === 0 && Array.isArray(s.data) && !s.name.startsWith('Total_')) {
              const val = parseFloat(s.data[idx]) || 0;
              total += val;
            }
          });
          totalValues.push(total);
        });
        
        // Add transparent overlay bar for total labels
        option.series.push({
          name: 'Total Labels',
          type: 'bar',
          stack: null,
          yAxisIndex: 0,
          data: totalValues,
          barGap: '-100%', // Overlay exactly on top of stacked bars
          itemStyle: { 
            color: 'transparent' 
          },
          label: {
            show: true,
            position: 'top',
            align: 'center',
            verticalAlign: 'bottom',
            fontSize: 12,
            fontWeight: 'bold',
            color: '#333', // Black color
            backgroundColor: '#ffffff',
            borderColor: '#333', // Black border
            borderWidth: 1,
            borderRadius: 4,
            padding: [4, 8],
            formatter: params => {
              const total = params.value;
              if (total === 0 || total === null || total === undefined) return '';
              if (Math.abs(total) >= 1000) {
                const kValue = Math.round(total / 1000);
                return kValue + 'K';
              } else {
                return Math.round(total).toString();
              }
            }
          },
          tooltip: { 
            show: false 
          },
          silent: true,
          z: 10
        });
      }
    
      // --- Apply chart option ---
      window.advancedChart2.setOption(option, true); // Use notMerge = true to ensure clean update
      
      // --- Ensure chart fits container ---
      setTimeout(() => {
        if (window.advancedChart2 && typeof window.advancedChart2.resize === 'function') {
          window.advancedChart2.resize();
        }
      }, 100);
      
      // Add window resize listener for larger screens to ensure chart expands properly
      if (!window.advancedChartResizeHandler) {
        window.advancedChartResizeHandler = () => {
          if (window.advancedChart2 && typeof window.advancedChart2.resize === 'function') {
            window.advancedChart2.resize();
          }
        };
        window.addEventListener('resize', window.advancedChartResizeHandler);
      }
  }

     /**
    * Update dynamic chart title
    */
   updateDynamicChartTitle() {
     const titleElement = document.getElementById('advancedChartTitle');
     if (!titleElement) {
       return;
     }

     const selectedParams = this.multiSelectInstances.advancedParameter ? 
       this.multiSelectInstances.advancedParameter.getSelectedValues() : [];
     const selectedCountries = this.multiSelectInstances.advancedCountry ? 
       this.multiSelectInstances.advancedCountry.getSelectedValues() : [];
     
     // Use the shared parameter label mapping
     const parameterLabelMap = this.getParameterLabelMap();
     
     let title = 'All Data';
     if (selectedParams.length > 0 || selectedCountries.length > 0) {
       title = '';
       if (selectedCountries.length > 0) {
         title += selectedCountries.join(', ');
       }
       if (selectedParams.length > 0) {
         if (title) title += ' - ';
         const paramLabels = selectedParams.map(param => parameterLabelMap[param] || param.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()));
         title += paramLabels.join(', ');
       }
     }
     
     titleElement.textContent = title;
   }

   /**
    * Reset advanced chart filters
    */
   resetAdvancedFilters() {
     try {
       // Reset chart type to default (Bar Chart)
       if (this.multiSelectInstances.advancedChartType) {
         this.multiSelectInstances.advancedChartType.setSelectedValues(['bar']);
         this.chartType = 'bar';
       }
       
       // Reset multi-select filters
       if (this.multiSelectInstances.advancedCountry) {
         this.multiSelectInstances.advancedCountry.clearSelection();
       }
       
       if (this.multiSelectInstances.advancedPortfolio) {
         this.multiSelectInstances.advancedPortfolio.clearSelection();
       }
       
       if (this.multiSelectInstances.advancedParameter) {
         this.multiSelectInstances.advancedParameter.clearSelection();
       }
       
           // Reset asset filter
    if (window.kpiDashboard && window.kpiDashboard.multiSelectInstances && window.kpiDashboard.multiSelectInstances.advancedAsset) {
      window.kpiDashboard.multiSelectInstances.advancedAsset.clearSelection();
    }
       
       // Reset advanced calendar if available
       if (window.currentBestCalendar && typeof window.currentBestCalendar.reset === 'function') {
         window.currentBestCalendar.reset();
       }
       
       // Reset cascading filters to show all options
       this.updatePortfolioOptions([], true);
       this.updateAssetOptions([], [], true);
       
       // Clear the chart completely
       this.clearAdvancedChart();
       
       // Reset the chart title back to "All Data" directly
       const titleElement = document.getElementById('advancedChartTitle');
       if (titleElement) {
         titleElement.textContent = 'All Data';
       }
       
       // Force update the title after a short delay to ensure all instances are cleared
       setTimeout(() => {
         this.updateDynamicChartTitle();
       }, 100);
       
     } catch (error) {
       // Error resetting advanced filters
     }
   }

   /**
    * Clear advanced chart completely
    */
   clearAdvancedChart() {
     if (!window.advancedChart2) return;
     
     const option = {
       title: { 
         text: 'Select parameters to view data', 
         left: 'center',
         top: 'center',
         textStyle: {
           fontSize: 16,
           color: '#666'
         }
       },
       tooltip: {},
       legend: { data: [], bottom: 10 },
       xAxis: { data: [] },
       yAxis: {},
       series: []
     };
     
     // Use notMerge = true to completely clear existing data
     window.advancedChart2.setOption(option, true);
   }

  /**
   * Setup tab switching handlers to refresh gauge charts
   */
  setupTabSwitchingHandlers() {
    // Handle visibility change events (tab switching)
    document.addEventListener('visibilitychange', () => {
      if (!document.hidden) {
        // Tab became visible, refresh gauge charts after a short delay
        setTimeout(() => {
          if (this.gaugeManager && typeof this.gaugeManager.forceRefreshCharts === 'function') {
            this.gaugeManager.forceRefreshCharts();
          }
        }, 200);
      }
    });

    // Handle window focus events
    window.addEventListener('focus', () => {
      setTimeout(() => {
        if (this.gaugeManager && typeof this.gaugeManager.forceRefreshCharts === 'function') {
          this.gaugeManager.forceRefreshCharts();
        }
      }, 200);
    });

    // Handle custom tab switching events (if your app uses them)
    document.addEventListener('tabChanged', () => {
      setTimeout(() => {
        if (this.gaugeManager && typeof this.gaugeManager.forceRefreshCharts === 'function') {
          this.gaugeManager.forceRefreshCharts();
        }
      }, 200);
    });

    // Handle page show events (back/forward navigation)
    window.addEventListener('pageshow', () => {
      setTimeout(() => {
        if (this.gaugeManager && typeof this.gaugeManager.forceRefreshCharts === 'function') {
          this.gaugeManager.forceRefreshCharts();
        }
      }, 200);
    });

    // Handle page load events (when returning to the page)
    window.addEventListener('load', () => {
      setTimeout(() => {
        this.handlePageLoad();
      }, 500);
    });

    // Handle beforeunload to clean up
    window.addEventListener('beforeunload', () => {
      this.cleanup();
    });
  }

  /**
   * Handle page load events (when returning to the page)
   */
  handlePageLoad() {
    // Check if we're on the KPI page and gauge section is visible
    const gaugesSection = document.getElementById('gaugesSection');
    if (gaugesSection && !gaugesSection.classList.contains('hidden')) {
      // Force refresh all gauge charts
      if (this.gaugeManager) {
        if (typeof this.gaugeManager.forceRefreshCharts === 'function') {
          this.gaugeManager.forceRefreshCharts();
        }
        if (typeof this.gaugeManager.updateCharts === 'function') {
          this.gaugeManager.updateCharts();
        }
      }
    }
    
    // Also refresh advanced charts if they exist
    if (window.advancedChart2 && typeof window.advancedChart2.resize === 'function') {
      window.advancedChart2.resize();
    }
  }

  /**
   * Cleanup method for page unload
   */
  cleanup() {
    // Clean up gauge charts
    if (this.gaugeManager && typeof this.gaugeManager.destroy === 'function') {
      this.gaugeManager.destroy();
    }
    
    // Clean up advanced charts
    if (window.advancedChart2 && typeof window.advancedChart2.dispose === 'function') {
      window.advancedChart2.dispose();
    }
  }

  /**
   * Setup chart type selector
   * IMPORTANT: Chart type selection is SINGLE-SELECT only (radio button behavior)
   * User can select ONLY Bar Chart OR Stacked Chart, not both
   */
  setupChartTypeSelector() {
    // Chart type is now handled by multi-select component
    // Override toggleOption to enforce single selection (radio button behavior)
    if (this.multiSelectInstances.advancedChartType) {
      const chartTypeInstance = this.multiSelectInstances.advancedChartType;
      const originalToggleOption = chartTypeInstance.toggleOption.bind(chartTypeInstance);
      
      // Override to enforce single selection - when one is selected, deselect the other
      chartTypeInstance.toggleOption = (value) => {
        const currentSelections = chartTypeInstance.getSelectedValues();
        
        // If clicking an already selected item, don't deselect (keep it selected)
        if (currentSelections.includes(value)) {
          return; // Already selected, do nothing
        }
        
        // Clear all selections first
        chartTypeInstance.selectedValues = [];
        
        // Uncheck all options
        chartTypeInstance.dropdown.querySelectorAll('.multi-select-option').forEach(div => {
          const checkbox = div.querySelector('input[type="checkbox"]');
          if (checkbox) {
            checkbox.checked = false;
            div.classList.remove('selected');
          }
        });
        
        // Add the new selection
        chartTypeInstance.selectedValues.push(value);
        this.chartType = value;
        
        // Update the selected checkbox
        const optionDiv = chartTypeInstance.dropdown.querySelector(`.multi-select-option[data-value="${value}"]`);
        if (optionDiv) {
          const checkbox = optionDiv.querySelector('input[type="checkbox"]');
          if (checkbox) {
            checkbox.checked = true;
            optionDiv.classList.add('selected');
          }
        }
        
        // Update display
        chartTypeInstance.updateDisplay();
        
        // Trigger onChange callback
        if (chartTypeInstance.onChange) {
          if (chartTypeInstance.onChangeTimer) {
            clearTimeout(chartTypeInstance.onChangeTimer);
          }
          chartTypeInstance.onChangeTimer = setTimeout(() => {
            const currentSelection = [...chartTypeInstance.selectedValues];
            chartTypeInstance.onChange(currentSelection);
          }, 0);
        }
      };
      
      // Set initial value
      const currentSelection = chartTypeInstance.getSelectedValues();
      if (currentSelection.length === 0) {
        this.chartType = 'bar';
      } else {
        this.chartType = currentSelection[0];
      }
    }
  }

  /**
   * Get current chart type
   */
  getChartType() {
    if (this.multiSelectInstances.advancedChartType) {
      const selectedValues = this.multiSelectInstances.advancedChartType.getSelectedValues();
      if (selectedValues.length > 0) {
        return selectedValues[0];
      }
    }
    return this.chartType || 'bar';
  }

  /**
   * Get maximum parameter limit based on current chart type
   * Bar Chart: 4 parameters max
   * Stacked Chart: 1 parameter max
   */
  getMaxParameterLimit() {
    const chartType = this.getChartType();
    if (chartType === 'stacked') {
      return 1; // Stacked chart allows only 1 parameter
    }
    return 4; // Bar chart allows up to 4 parameters
  }

  /**
   * Enforce parameter limit when chart type changes
   * If switching to stacked chart, trim parameters to 1
   * Also update the placeholder text dynamically
   */
  enforceParameterLimitBasedOnChartType() {
    if (!this.multiSelectInstances.advancedParameter) {
      return;
    }

    const chartType = this.getChartType();
    const maxLimit = this.getMaxParameterLimit();
    const paramInstance = this.multiSelectInstances.advancedParameter;
    const currentSelections = paramInstance.getSelectedValues();

    // Update placeholder text based on chart type
    const placeholderElement = document.getElementById('advancedParameterFilterPlaceholder');
    if (placeholderElement) {
      if (chartType === 'stacked') {
        placeholderElement.setAttribute('data-default', 'Select Parameter (Max 1)');
        if (currentSelections.length === 0) {
          placeholderElement.textContent = 'Select Parameter (Max 1)';
        }
      } else {
        placeholderElement.setAttribute('data-default', 'Select Parameters (Max 4)');
        if (currentSelections.length === 0) {
          placeholderElement.textContent = 'Select Parameters (Max 4)';
        }
      }
    }

    // If current selections exceed the new limit, trim them
    if (currentSelections.length > maxLimit) {
      // Keep only the first parameter(s) up to maxLimit
      const trimmedSelections = currentSelections.slice(0, maxLimit);
      paramInstance.setSelectedValues(trimmedSelections);
      
      // Show alert to user
      if (chartType === 'stacked') {
        alert('Stacked Chart allows only 1 parameter. Other parameters have been removed.');
      }
      
      // Update chart with new selections
      setTimeout(() => {
        this.updateAdvancedCharts();
      }, 50);
    }

    // Update disabled state of options using the helper function if available
    if (paramInstance.updateParameterDisabledStates) {
      paramInstance.updateParameterDisabledStates();
      setTimeout(() => paramInstance.updateParameterDisabledStates(), 50);
      setTimeout(() => paramInstance.updateParameterDisabledStates(), 100);
    } else {
      // Fallback if helper function not available
      setTimeout(() => {
        const updatedSelections = paramInstance.getSelectedValues();
        const shouldDisableOthers = updatedSelections.length >= maxLimit;
        
        paramInstance.dropdown.querySelectorAll('.multi-select-option').forEach(div => {
          const optionValue = div.getAttribute('data-value');
          const checkbox = div.querySelector('input[type="checkbox"]');
          const isSelected = updatedSelections.includes(optionValue);
          
          if (isSelected) {
            div.classList.remove('opacity-50', 'cursor-not-allowed');
            div.style.pointerEvents = 'auto';
            if (checkbox) checkbox.disabled = false;
          } else {
            if (shouldDisableOthers) {
              div.classList.add('opacity-50', 'cursor-not-allowed');
              div.style.pointerEvents = 'none';
              if (checkbox) checkbox.disabled = true;
            } else {
              div.classList.remove('opacity-50', 'cursor-not-allowed');
              div.style.pointerEvents = 'auto';
              if (checkbox) checkbox.disabled = false;
            }
          }
        });
      }, 50);
    }
  }

  /**
   * Setup global event listeners
   */
  setupGlobalEventListeners() {
    // Handle tab switching and visibility changes
    this.setupTabSwitchingHandlers();
           // Window resize handler
      window.addEventListener('resize', () => {
        if (window.advancedChart2) {
          window.advancedChart2.resize();
          // Update the chart to recalculate font sizes
          setTimeout(() => {
            this.updateAdvancedChart2();
          }, 100);
        }
        
                 // Resize gauge charts
         if (this.gaugeManager && this.gaugeManager.charts) {
           Object.keys(this.gaugeManager.charts).forEach(canvasId => {
             const canvas = document.getElementById(canvasId);
             if (canvas) {
               const container = canvas.parentElement;
               if (container) {
                 // Use the full container dimensions minus any padding
                 const containerRect = container.getBoundingClientRect();
                 const containerStyle = window.getComputedStyle(container);
                 const paddingLeft = parseFloat(containerStyle.paddingLeft) || 0;
                 const paddingRight = parseFloat(containerStyle.paddingRight) || 0;
                 const paddingTop = parseFloat(containerStyle.paddingTop) || 0;
                 const paddingBottom = parseFloat(containerStyle.paddingBottom) || 0;
                 
                 canvas.width = containerRect.width - paddingLeft - paddingRight;
                 canvas.height = containerRect.height - paddingTop - paddingBottom;
                 
                 // Set canvas style to fill the container
                 canvas.style.width = '100%';
                 canvas.style.height = '100%';
               }
             }
           });
         }
      });

     // Asset filter change handlers are now handled by multi-select components
     

   }

   /**
    * Setup advanced reset button handler
    */
   setupAdvancedResetButton() {
     const advancedResetBtn = document.getElementById('advancedResetBtn');
     
     if (advancedResetBtn) {
       // Remove any existing event listeners
       advancedResetBtn.removeEventListener('click', this.resetAdvancedFilters);
       
       // Add new event listener with proper binding
       advancedResetBtn.addEventListener('click', () => {
         // Test if we can directly access the title element
         const titleElement = document.getElementById('advancedChartTitle');
         if (titleElement) {
           titleElement.textContent = 'All Data';
         }
         
         this.resetAdvancedFilters();
       });
     }
   }
   


  /**
   * Show loading state
   */
  showLoading(message = 'Loading...') {
    this.loadingState.isLoading = true;
    this.loadingState.message = message;
    
    // Update UI to show loading
    const gaugeDateDisplay = document.getElementById('gaugeDateDisplay');
    if (gaugeDateDisplay) {
      gaugeDateDisplay.textContent = message;
    }
  }

  /**
   * Hide loading state
   */
  hideLoading() {
    this.loadingState.isLoading = false;
    this.loadingState.message = '';
  }

  /**
   * Show error message
   */
  showError(message) {
    // Update UI to show error
    const gaugeDateDisplay = document.getElementById('gaugeDateDisplay');
    if (gaugeDateDisplay) {
      gaugeDateDisplay.textContent = 'Error loading data';
    }
    
    // Could add a toast notification here
  }

  /**
   * Refresh dashboard data
   */
  async refresh() {
    if (!this.isInitialized) return;
    
    try {
      this.showLoading('Refreshing data...');
      await this.dataManager.loadAllData();
      
      // Re-initialize gauge charts after data refresh
      if (this.gaugeManager) {
        this.gaugeManager.reinitialize();
      }
      
      // Update dropdowns with new data
      this.populateDropdowns();
      
      // Update KPI summary cards using site_state from latest data
      this.updateKPISummaryCardsFromSiteState();
      
      this.hideLoading();
    } catch (error) {
      this.showError('Failed to refresh data: ' + error.message);
    }
  }

  /**
   * Destroy dashboard and cleanup
   */
  destroy() {
    // Destroy gauge manager
    if (this.gaugeManager) {
      this.gaugeManager.destroy();
    }
    // Clear global reference so stale instances aren't used after navigation
    if (window.gaugeChartsManager === this.gaugeManager) {
      window.gaugeChartsManager = null;
    }

    // Destroy multi-select instances
    Object.values(this.multiSelectInstances).forEach(instance => {
      if (instance && typeof instance.destroy === 'function') {
        instance.destroy();
      }
    });

    // Clear references
    this.dataManager = null;
    this.gaugeManager = null;
    this.multiSelectInstances = {};
    this.isInitialized = false;
  }

  /**
   * Update portfolio options based on selected countries (cascading filter)
   */
  updatePortfolioOptions(selectedCountries, isAdvanced = false) {
    // Use appropriate data source based on chart type
    const dataSource = isAdvanced ? this.dataManager.yieldData : this.dataManager.realtimeData;
    
    if (!dataSource || dataSource.length === 0) {
      return;
    }

    // Filter data based on selected countries (normalize values)
    let filteredData = dataSource;
    if (selectedCountries && selectedCountries.length > 0) {
      filteredData = dataSource.filter(row => {
        const countryVal = (row.country || row.rowCountry || '').toString().trim().toLowerCase();
        const selectedNorm = selectedCountries.map(v => (v || '').toString().trim().toLowerCase());
        return selectedNorm.includes(countryVal);
      });
    }

    // Get unique portfolios from filtered data (try multiple field names)
    const availablePortfolios = [...new Set(filteredData.map(row => (row.portfolio || row.portfolio_name || row.portfolio_code || '').toString().trim()))].sort();

    // Create portfolio options
    const portfolioOptions = availablePortfolios.map(portfolio => ({
      value: portfolio,
      label: portfolio
    }));

    // Update the appropriate portfolio multi-select
    const portfolioMultiSelect = isAdvanced ? 
      this.multiSelectInstances.advancedPortfolio : 
      this.multiSelectInstances.gaugePortfolio;

    if (portfolioMultiSelect) {
      // Preserve valid selections like Yield Report_v2
      const currentSelections = portfolioMultiSelect.getSelectedValues ? portfolioMultiSelect.getSelectedValues() : [];
      const validSelections = currentSelections.filter(v => availablePortfolios.includes(v));
      portfolioMultiSelect.setOptions(portfolioOptions);
      if (validSelections.length > 0) {
        portfolioMultiSelect.setSelectedValues(validSelections);
      } else {
        portfolioMultiSelect.clearSelection();
      }
    }
  }

  /**
   * Update KPI summary cards using site_state from latest data
   */
  updateKPISummaryCardsFromSiteState() {
    try {
      // Check if data manager and data are available
      if (!this.dataManager) {
        setTimeout(() => this.updateKPISummaryCardsFromSiteState(), 100);
        return;
      }

      // Get current filter values for gauge section
      const currentFilters = {
        countries: this.multiSelectInstances.gaugeCountry ? 
          this.multiSelectInstances.gaugeCountry.getSelectedValues() : [],
        portfolios: this.multiSelectInstances.gaugePortfolio ? 
          this.multiSelectInstances.gaugePortfolio.getSelectedValues() : [],
        assets: this.multiSelectInstances.gaugeAsset ? 
          this.multiSelectInstances.gaugeAsset.getSelectedValues() : [],
        date: ''
      };
      
      // Get date filter
      const dateFilter = document.getElementById('gaugeDateFilter');
      if (dateFilter) {
        currentFilters.date = dateFilter.value;
      }
      
      // Get filtered data
      const filteredData = this.dataManager.getFilteredRealtimeData(currentFilters);
      
      if (!filteredData || filteredData.length === 0) {
        setTimeout(() => this.updateKPISummaryCardsFromSiteState(), 200);
        return;
      }
      
      // Calculate KPI values using site_state column
      const kpiValues = this.calculateKPISummaryValuesFromSiteState(filteredData);
      
      
      // Update the UI elements
      this.updateKPICardDisplay(kpiValues);
      
    } catch (error) {
      // Error in updateKPISummaryCardsFromSiteState
    }
  }

  /**
   * Calculate KPI summary values from site_state column in latest data
   */
  calculateKPISummaryValuesFromSiteState(filteredData) {
    if (!filteredData || filteredData.length === 0) {
      return {
        totalSites: 0,
        activeSites: 0,
        inactiveSites: 0,
      };
    }

    // Get the latest record for each asset based on last_updated timestamp
    const latestRecordsByAsset = {};
    
    filteredData.forEach((row, index) => {
      const assetCode = row.asset_code || row.assetno || row.asset_number || row.asset;
      if (!assetCode) {
        return;
      }
      
      const lastUpdated = row.last_updated || row.updated_at || row.created_at || row.date;
      if (!lastUpdated) {
        return;
      }
      
      // Parse timestamp to compare
      let timestamp;
      if (typeof lastUpdated === 'string') {
        timestamp = new Date(lastUpdated).getTime();
      } else if (lastUpdated instanceof Date) {
        timestamp = lastUpdated.getTime();
      } else {
        return;
      }
      
      // Keep only the latest record for each asset
      if (!latestRecordsByAsset[assetCode] || timestamp > latestRecordsByAsset[assetCode].timestamp) {
        latestRecordsByAsset[assetCode] = {
          site_state: row.site_state,
          daily_generation_mwh: row.daily_generation_mwh,
          timestamp: timestamp,
          last_updated_string: lastUpdated,
          asset_code: assetCode
        };
      }
    });


    // Count sites by state
    const totalSites = Object.keys(latestRecordsByAsset).length;
    let activeSites = 0;
    let inactiveSites = 0;
    Object.values(latestRecordsByAsset).forEach(record => {
      
      // First try to use site_state column if available
      if (record.site_state === 'active') {
        activeSites++;
      } else if (record.site_state === 'inactive') {
        inactiveSites++;
      } else if (record.site_state === undefined || record.site_state === null) {
        // Fallback: Use generation data to determine active/inactive
        const generation = parseFloat(record.daily_generation_mwh || 0);
        if (!isNaN(generation) && generation > 0) {
          activeSites++;
        } else {
          inactiveSites++;
        }
      } else {
        // Fallback for unknown site_state values
        const generation = parseFloat(record.daily_generation_mwh || 0);
        if (!isNaN(generation) && generation > 0) {
          activeSites++;
        } else {
          inactiveSites++;
        }
      }
    });

    const result = {
      totalSites,
      activeSites,
      inactiveSites
    };

    return result;
  }






  /**
   * Update KPI card display elements
   */
  updateKPICardDisplay(kpiValues) {
    
    // Store KPI values for tooltip use
    this.currentKPIValues = kpiValues;
    
    // Update Total Sites
    const totalSitesElement = document.getElementById('totalSitesCount');
    if (totalSitesElement) {
      totalSitesElement.textContent = kpiValues.totalSites;
    }

    // Update Active Sites
    const activeSitesElement = document.getElementById('activeSitesCount');
    if (activeSitesElement) {
      activeSitesElement.textContent = kpiValues.activeSites;
    }

    // Update Inactive Sites
    const inactiveSitesElement = document.getElementById('inactiveSitesCount');
    if (inactiveSitesElement) {
      inactiveSitesElement.textContent = kpiValues.inactiveSites;
    }

  }

  /**
   * Show KPI tooltip with site list
   */
  showKPITooltip(cardType) {
    try {
      if (!this.currentKPIValues) {
        return;
      }

      // Get current data to populate site lists
      const currentFilters = {
        countries: this.multiSelectInstances.gaugeCountry ? 
          this.multiSelectInstances.gaugeCountry.getSelectedValues() : [],
        portfolios: this.multiSelectInstances.gaugePortfolio ? 
          this.multiSelectInstances.gaugePortfolio.getSelectedValues() : [],
        assets: this.multiSelectInstances.gaugeAsset ? 
          this.multiSelectInstances.gaugeAsset.getSelectedValues() : [],
        date: ''
      };
      
      const dateFilter = document.getElementById('gaugeDateFilter');
      if (dateFilter) {
        currentFilters.date = dateFilter.value;
      }
      
      const filteredData = this.dataManager.getFilteredRealtimeData(currentFilters);
      const siteLists = this.getSiteListsFromData(filteredData);
      
      // Update tooltip content based on card type
      this.populateTooltip(cardType, siteLists);
      
      // Show tooltip
      const overlay = document.getElementById('kpiTooltipOverlay');
      if (overlay) {
        overlay.classList.remove('hidden');
        overlay.style.display = 'block';
      }
      
    } catch (error) {
      // Error showing tooltip
    }
  }

  /**
   * Get site lists from filtered data
   */
  getSiteListsFromData(filteredData) {
    if (!filteredData || filteredData.length === 0) {
      return { total: [], active: [], inactive: [] };
    }

    // Get the latest record for each asset
    const latestRecordsByAsset = {};
    
    filteredData.forEach(row => {
      const assetCode = row.asset_code || row.assetno || row.asset_number || row.asset;
      if (!assetCode) return;
      
      const lastUpdated = row.last_updated || row.updated_at || row.created_at || row.date;
      if (!lastUpdated) return;
      
      let timestamp;
      if (typeof lastUpdated === 'string') {
        timestamp = new Date(lastUpdated).getTime();
      } else if (lastUpdated instanceof Date) {
        timestamp = lastUpdated.getTime();
      } else {
        return;
      }
      
      if (!latestRecordsByAsset[assetCode] || timestamp > latestRecordsByAsset[assetCode].timestamp) {
        latestRecordsByAsset[assetCode] = {
          site_state: row.site_state,
          daily_generation_mwh: row.daily_generation_mwh,
          timestamp: timestamp,
          asset_code: assetCode
        };
      }
    });

    const total = Object.keys(latestRecordsByAsset);
    const active = [];
    const inactive = [];

    Object.values(latestRecordsByAsset).forEach(record => {

      if (record.site_state === 'active') {
        active.push(record.asset_code);
      } else if (record.site_state === 'inactive') {
        inactive.push(record.asset_code);
      } else if (record.site_state === undefined || record.site_state === null) {
        // Fallback: Use generation data
        const generation = parseFloat(record.daily_generation_mwh || 0);
        if (!isNaN(generation) && generation > 0) {
          active.push(record.asset_code);
        } else {
          inactive.push(record.asset_code);
        }
      } else {
        // Fallback for unknown site_state values
        const generation = parseFloat(record.daily_generation_mwh || 0);
        if (!isNaN(generation) && generation > 0) {
          active.push(record.asset_code);
        } else {
          inactive.push(record.asset_code);
        }
      }
    });

    return { total, active, inactive };
  }

  /**
   * Populate tooltip content
   */
  populateTooltip(cardType, siteLists) {
    const tooltipTitle = document.getElementById('tooltipTitle');
    const tooltipSubtitle = document.getElementById('tooltipSubtitle');
    const siteCount = document.getElementById('siteCount');
    const siteList = document.getElementById('siteList');
    const tooltipTotal = document.getElementById('tooltipTotal');
    const tooltipActive = document.getElementById('tooltipActive');
    const tooltipInactive = document.getElementById('tooltipInactive');

    let sites = [];
    let title = '';
    let subtitle = '';

    switch (cardType) {
      case 'total':
        sites = siteLists.total;
        title = 'Total Sites';
        subtitle = 'All sites based on current filters';
        break;
      case 'active':
        sites = siteLists.active;
        title = 'Active Sites';
        subtitle = 'Sites with generation > 0';
        break;
      case 'inactive':
        sites = siteLists.inactive;
        title = 'Inactive Sites';
        subtitle = 'Sites with no generation';
        break;
    }

    // Update header
    if (tooltipTitle) tooltipTitle.textContent = title;
    if (tooltipSubtitle) tooltipSubtitle.textContent = subtitle;
    if (siteCount) siteCount.textContent = `${sites.length} sites`;

    // Update site list
    if (siteList) {
      siteList.innerHTML = '';
      if (sites.length === 0) {
        siteList.innerHTML = '<div class="text-center text-gray-500 py-4">No sites found</div>';
      } else {
        sites.forEach((site, index) => {
          const siteItem = document.createElement('div');
          siteItem.className = 'flex items-center justify-between p-2 border-b border-gray-100 hover:bg-gray-50';
          
          {
            const siteName = typeof site === 'object' ? site.asset_code : site;
            siteItem.innerHTML = `
              <div class="flex items-center">
                <span class="w-6 h-6 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center text-xs font-semibold mr-3">
                  ${index + 1}
                </span>
                <span class="font-medium text-gray-800">${siteName}</span>
              </div>
              <div class="text-xs text-gray-500">
                ${cardType === 'active' ? '✅ Active' : cardType === 'inactive' ? '⚠️ Inactive' : '🏢 Site'}
              </div>
            `;
          }
          siteList.appendChild(siteItem);
        });
      }
    }

    // Update summary stats
    if (tooltipTotal) tooltipTotal.textContent = siteLists.total.length;
    if (tooltipActive) tooltipActive.textContent = siteLists.active.length;
    if (tooltipInactive) tooltipInactive.textContent = siteLists.inactive.length;
    
  }

  /**
   * Hide KPI tooltip
   */
  hideKPITooltip() {
    const overlay = document.getElementById('kpiTooltipOverlay');
    if (overlay) {
      overlay.classList.add('hidden');
      overlay.style.display = 'none';
    }
  }

  /**
   * Update asset options based on selected countries and portfolios (cascading filter)
   */
  updateAssetOptions(selectedCountries, selectedPortfolios, isAdvanced = false) {
    // Use appropriate data source based on chart type
    const dataSource = isAdvanced ? this.dataManager.yieldData : this.dataManager.realtimeData;
    
    if (!dataSource || dataSource.length === 0) {
      return;
    }

    // Normalize helper
    const norm = v => (v || '').toString().trim().toLowerCase();

    // Filter data based on selected countries and portfolios (robust, case-insensitive)
    let filteredData = dataSource;

    let countryFiltered = filteredData;
    if (selectedCountries && selectedCountries.length > 0) {
      const selectedCountriesNorm = selectedCountries.map(norm);
      countryFiltered = filteredData.filter(row => selectedCountriesNorm.includes(norm(row.country || row.rowCountry)));
    }

    // Determine portfolios available within the country filter (for reference only)
    const portfoliosInCountry = [...new Set(countryFiltered.map(row => (row.portfolio || row.portfolio_name || row.portfolio_code || '').toString().trim()))];

    // Decide which subset to use for assets
    // Only filter by selected portfolios - don't auto-scope to single portfolio
    // This allows users to see all assets from all portfolios when no portfolio is selected
    if (selectedPortfolios && selectedPortfolios.length > 0) {
      const selectedPortfoliosNorm = selectedPortfolios.map(norm);
      filteredData = countryFiltered.filter(row => selectedPortfoliosNorm.includes(norm(row.portfolio || row.portfolio_name || row.portfolio_code)));
    } else {
      // Show all assets from all portfolios when no portfolio filter is applied
      filteredData = countryFiltered;
    }

    // Get unique assets from filtered data (try multiple field names)
    const availableAssets = [...new Set(filteredData.map(row => (row.asset_code || row.assetno || row.asset_number || row.asset || '').toString().trim()))].sort();
    


    // Create options array for multi-select
    const assetOptions = availableAssets.map(asset => ({
      value: asset,
      label: asset
    }));

    // Update the appropriate asset multi-select
    const assetMultiSelect = isAdvanced ? 
      this.multiSelectInstances.advancedAsset : 
      this.multiSelectInstances.gaugeAsset;
    

    
    if (assetMultiSelect) {
      // Preserve valid selections - but NEVER auto-select assets
      // Users should explicitly choose assets, even if only one is available
      const currentSelections = assetMultiSelect.getSelectedValues ? assetMultiSelect.getSelectedValues() : [];
      const validSelections = currentSelections.filter(v => availableAssets.includes(v));
      
      // Set new options - this will render with current selections
      assetMultiSelect.setOptions(assetOptions);
      
      // Only preserve valid selections that were already selected by the user
      // Never auto-select assets, even if only one asset exists
      if (validSelections.length > 0) {
        // Valid selections exist - restore them
        assetMultiSelect.setSelectedValues(validSelections);
      } else {
        // No valid selections - clear to ensure no auto-selection happens
        // This is safe because setOptions already rendered, and clearSelection will re-render
        // but it's necessary to clear selectedValues state
        assetMultiSelect.selectedValues = [];
        assetMultiSelect.updateDisplay();
      }
    }
  }
}

// Export for use in other modules
window.KPIDashboard = KPIDashboard;
window.MultiSelect = MultiSelect;
window.MultiSelectFactory = MultiSelectFactory;

// Direct reset button setup that works regardless of dashboard initialization
document.addEventListener('DOMContentLoaded', function() {
  // Flag to prevent automatic title updates after reset
  let resetInProgress = false;
  
  function setupResetButtonDirectly() {
    const advancedResetBtn = document.getElementById('advancedResetBtn');
    
    if (advancedResetBtn) {
      // Remove any existing event listeners
      advancedResetBtn.removeEventListener('click', handleResetClick);
      
      // Add new event listener
      advancedResetBtn.addEventListener('click', handleResetClick);
      
      return true;
    } else {
      return false;
    }
  }
  
  function handleResetClick() {
    resetInProgress = true;
    
    // Reset the chart title first
    const titleElement = document.getElementById('advancedChartTitle');
    if (titleElement) {
      titleElement.textContent = 'All Data';
    }
    
    // Reset multi-select instances if they exist
    
    // Reset advanced parameter multi-select
    if (window.kpiDashboard && window.kpiDashboard.multiSelectInstances && window.kpiDashboard.multiSelectInstances.advancedParameter) {
      window.kpiDashboard.multiSelectInstances.advancedParameter.clearSelection();
    }
    
    // Reset advanced country multi-select
    if (window.kpiDashboard && window.kpiDashboard.multiSelectInstances && window.kpiDashboard.multiSelectInstances.advancedCountry) {
      window.kpiDashboard.multiSelectInstances.advancedCountry.clearSelection();
    }
    
    // Reset advanced portfolio multi-select
    if (window.kpiDashboard && window.kpiDashboard.multiSelectInstances && window.kpiDashboard.multiSelectInstances.advancedPortfolio) {
      window.kpiDashboard.multiSelectInstances.advancedPortfolio.clearSelection();
    }
    
    // Reset asset filter
    if (window.kpiDashboard && window.kpiDashboard.multiSelectInstances && window.kpiDashboard.multiSelectInstances.advancedAsset) {
      window.kpiDashboard.multiSelectInstances.advancedAsset.clearSelection();
    }
    
    // Reset calendar if available
    if (window.currentBestCalendar && typeof window.currentBestCalendar.reset === 'function') {
      window.currentBestCalendar.reset();
    }
    
    // Clear the chart
    if (window.advancedChart2) {
      const option = {
        title: { 
          text: 'Select parameters to view data', 
          left: 'center',
          top: 'center',
          textStyle: {
            fontSize: 16,
            color: '#666'
          }
        },
        tooltip: {},
        legend: { data: [], bottom: 10 },
        xAxis: { data: [] },
        yAxis: {},
        series: []
      };
      window.advancedChart2.setOption(option, true);
    }
    
    // Force update the chart title again after clearing selections
    setTimeout(() => {
      if (titleElement) {
        titleElement.textContent = 'All Data';
      }
    }, 100);
    
    // Try to call the dashboard reset function if available
    if (window.kpiDashboard && typeof window.kpiDashboard.resetAdvancedFilters === 'function') {
      window.kpiDashboard.resetAdvancedFilters();
    }
    
    // Force another title update after a longer delay
    setTimeout(() => {
      if (titleElement) {
        titleElement.textContent = 'All Data';
      }
      resetInProgress = false;
    }, 500);
  }
  
  // Override the updateDynamicChartTitle function to prevent automatic updates during reset
  if (window.kpiDashboard && window.kpiDashboard.updateDynamicChartTitle) {
    const originalUpdateTitle = window.kpiDashboard.updateDynamicChartTitle;
    window.kpiDashboard.updateDynamicChartTitle = function() {
      if (resetInProgress) {
        return;
      }
      return originalUpdateTitle.apply(this, arguments);
    };
  }
  
  // Function to monitor and ensure title stays as "All Data" after reset
  function monitorTitle() {
    const titleElement = document.getElementById('advancedChartTitle');
    if (titleElement && resetInProgress) {
      if (titleElement.textContent !== 'All Data') {
        titleElement.textContent = 'All Data';
      }
    }
  }
  
  // Set up title monitoring after reset
  function startTitleMonitoring() {
    const titleElement = document.getElementById('advancedChartTitle');
    if (titleElement) {
      // Monitor title changes using MutationObserver
      const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
          if (resetInProgress && mutation.type === 'childList') {
            setTimeout(() => {
              if (titleElement.textContent !== 'All Data') {
                titleElement.textContent = 'All Data';
              }
            }, 10);
          }
        });
      });
      
      observer.observe(titleElement, {
        childList: true,
        subtree: true,
        characterData: true
      });
    }
  }
  
  // Start title monitoring after a delay
  setTimeout(startTitleMonitoring, 1000);
  
  // Try to set up the reset button immediately
  if (!setupResetButtonDirectly()) {
    // If not found, try again after a short delay
    setTimeout(() => {
      if (!setupResetButtonDirectly()) {
        // Try again after a longer delay
        setTimeout(() => {
          setupResetButtonDirectly();
        }, 1000);
      }
    }, 500);
  }
});
