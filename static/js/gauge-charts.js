/**
 * Gauge Charts Module - Handles all gauge chart operations
 */
class GaugeChartsManager {
  constructor(dataManager) {
    this.dataManager = dataManager;
    this.charts = {};
    this.currentFilters = {
      countries: [],
      portfolios: [],
      assets: [],
      date: ''
    };
    
    // Chart configuration
    this.chartConfig = {
      icActualGauge: {
        title: 'IC Approved Vs Actual (MWh)',
        color: '#0072CE',
        bgColor: '#e0e0e0'
      },
      expActualGauge: {
        title: 'Expected Vs Actual (MWh)',
        color: '#0072CE',
        bgColor: '#e0e0e0'
      },
      prGauge: {
        title: 'PR(%)',
        color: '#0072CE',
        bgColor: '#e0e0e0'
      },
      irrGauge: {
        title: 'Irradiation (kWh/M2)',
        color: '#0072CE',
        bgColor: '#e0e0e0'
      }
    };
  }

  /**
   * Initialize gauge charts
   */
  init() {
    this.setupEventListeners();
    
    // Set default date to the most recent available date in the data
    this.setDefaultDate();
    
    this.updateCharts();
    
    // Add visibility change handler to handle tab switching
    this.setupVisibilityHandlers();
    
    // Show available dates for debugging
    if (this.dataManager) {
      this.dataManager.getAvailableDates();
    }
    
    // Add a delayed initialization check for page navigation scenarios
    setTimeout(() => {
      this.checkAndInitializeCharts();
    }, 1000);
    
    // Chrome-specific: Force immediate visibility check on init
    setTimeout(() => {
      const gaugesSection = document.getElementById('gaugesSection');
      if (gaugesSection && !gaugesSection.classList.contains('hidden')) {
        this.forceRefreshCharts();
        this.updateCharts();
      }
    }, 500);
  }

  /**
   * Check and initialize charts if they're not properly rendered
   */
  checkAndInitializeCharts() {
    const gaugesSection = document.getElementById('gaugesSection');
    if (gaugesSection && !gaugesSection.classList.contains('hidden')) {
      const gaugeIds = ['icActualGauge', 'expActualGauge', 'prGauge', 'irrGauge'];
      let needsInitialization = false;
      
      gaugeIds.forEach(gaugeId => {
        const canvas = document.getElementById(gaugeId);
        if (canvas) {
          const chart = this.charts[gaugeId];
          const isVisible = canvas.offsetWidth > 0 && canvas.offsetHeight > 0;
          
          // If container is visible but chart is not properly initialized
          if (isVisible && (!chart || !chart.canvas || chart.canvas.width === 0)) {
            needsInitialization = true;
          }
        }
      });
      
      if (needsInitialization) {
        // Force a complete reinitialization
        this.reinitialize();
      }
    }
  }

  /**
   * Setup visibility change handlers to handle tab switching
   */
  setupVisibilityHandlers() {
    // Handle visibility change events (tab switching)
    document.addEventListener('visibilitychange', () => {
      if (!document.hidden) {
        // Tab became visible, refresh charts after a short delay
        setTimeout(() => {
          this.refreshChartsOnVisibilityChange();
        }, 100);
      }
    });

    // Handle window focus events
    window.addEventListener('focus', () => {
      setTimeout(() => {
        this.refreshChartsOnVisibilityChange();
      }, 100);
    });

    // Handle resize events
    window.addEventListener('resize', () => {
      setTimeout(() => {
        this.refreshChartsOnVisibilityChange();
      }, 100);
    });

    // Handle custom tab switching events (if your app uses them)
    document.addEventListener('tabChanged', () => {
      setTimeout(() => {
        this.refreshChartsOnVisibilityChange();
      }, 100);
    });

    // Setup Intersection Observer to detect when gauge containers become visible
    this.setupIntersectionObserver();
    
    // Setup Mutation Observer to watch for CSS class changes on gauge section
    this.setupMutationObserver();
    
    // Periodic visibility check disabled - causes issues with destroyed charts
    // this.setupPeriodicVisibilityCheck();
  }

  /**
   * Setup Intersection Observer to detect when gauge containers become visible
   */
  setupIntersectionObserver() {
    if (!('IntersectionObserver' in window)) {
      return; // Fallback for older browsers
    }

    const gaugeIds = ['icActualGauge', 'expActualGauge', 'prGauge', 'irrGauge'];
    
    gaugeIds.forEach(gaugeId => {
      const canvas = document.getElementById(gaugeId);
      if (canvas) {
        const observer = new IntersectionObserver((entries) => {
          entries.forEach(entry => {
            if (entry.isIntersecting) {
              // Container became visible, refresh the chart
              setTimeout(() => {
                this.refreshSingleChart(gaugeId);
              }, 100);
            }
          });
        }, {
          threshold: 0.1, // Trigger when 10% of the container is visible
          rootMargin: '0px'
        });
        
        observer.observe(canvas.parentElement);
      }
    });
  }

  /**
   * Setup Mutation Observer to watch for CSS class changes on gauge section
   */
  setupMutationObserver() {
    const gaugesSection = document.getElementById('gaugesSection');
    if (gaugesSection && 'MutationObserver' in window) {
      const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
          if (mutation.type === 'attributes' && mutation.attributeName === 'class') {
            const target = mutation.target;
            const isHidden = target.classList.contains('hidden');
            
            if (!isHidden) {
              // Gauge section became visible, force immediate refresh
              setTimeout(() => {
                this.forceRefreshCharts();
                // Also trigger a full update to ensure charts are rendered
                if (typeof this.updateCharts === 'function') {
                  this.updateCharts();
                }
              }, 100);
            }
          }
        });
      });
      
      observer.observe(gaugesSection, {
        attributes: true,
        attributeFilter: ['class']
      });
    }
  }

  /**
   * Setup periodic visibility check as a fallback
   */
  setupPeriodicVisibilityCheck() {
    // Check every 2 seconds if gauge section is visible but charts are not rendered
    setInterval(() => {
      const gaugesSection = document.getElementById('gaugesSection');
      if (gaugesSection && !gaugesSection.classList.contains('hidden')) {
        const gaugeIds = ['icActualGauge', 'expActualGauge', 'prGauge', 'irrGauge'];
        let needsRefresh = false;
        
        gaugeIds.forEach(gaugeId => {
          const canvas = document.getElementById(gaugeId);
          if (canvas) {
            const chart = this.charts[gaugeId];
            const isVisible = canvas.offsetWidth > 0 && canvas.offsetHeight > 0;
            
            // If container is visible but chart is not properly rendered
            if (isVisible && (!chart || !chart.canvas || chart.canvas.width === 0)) {
              needsRefresh = true;
            }
          }
        });
        
        if (needsRefresh) {
          this.forceRefreshCharts();
          // Also trigger a full update
          if (typeof this.updateCharts === 'function') {
            this.updateCharts();
          }
        }
      }
    }, 2000);
    
    // More aggressive check for the first 10 seconds after page load (for navigation scenarios)
    let aggressiveCheckCount = 0;
    const aggressiveInterval = setInterval(() => {
      const gaugesSection = document.getElementById('gaugesSection');
      if (gaugesSection && !gaugesSection.classList.contains('hidden')) {
        const gaugeIds = ['icActualGauge', 'expActualGauge', 'prGauge', 'irrGauge'];
        let needsRefresh = false;
        
        gaugeIds.forEach(gaugeId => {
          const canvas = document.getElementById(gaugeId);
          if (canvas) {
            const chart = this.charts[gaugeId];
            const isVisible = canvas.offsetWidth > 0 && canvas.offsetHeight > 0;
            
            if (isVisible && (!chart || !chart.canvas || chart.canvas.width === 0)) {
              needsRefresh = true;
            }
          }
        });
        
        if (needsRefresh) {
          this.forceRefreshCharts();
          if (typeof this.updateCharts === 'function') {
            this.updateCharts();
          }
        }
      }
      
      aggressiveCheckCount++;
      if (aggressiveCheckCount >= 20) { // Stop after 10 seconds (20 * 500ms)
        clearInterval(aggressiveInterval);
      }
    }, 500);
  }

  /**
   * Refresh a single chart by ID
   */
  refreshSingleChart(gaugeId) {
    const canvas = document.getElementById(gaugeId);
    if (canvas && canvas.parentElement) {
      const parent = canvas.parentElement;
      const isVisible = parent.offsetWidth > 0 && parent.offsetHeight > 0;
      
      if (isVisible) {
        // Recalculate canvas size
        const containerRect = parent.getBoundingClientRect();
        const containerStyle = window.getComputedStyle(parent);
        const paddingLeft = parseFloat(containerStyle.paddingLeft) || 0;
        const paddingRight = parseFloat(containerStyle.paddingRight) || 0;
        const paddingTop = parseFloat(containerStyle.paddingTop) || 0;
        const paddingBottom = parseFloat(containerStyle.paddingBottom) || 0;
        
        canvas.width = containerRect.width - paddingLeft - paddingRight;
        canvas.height = containerRect.height - paddingTop - paddingBottom;
        
        // Force chart resize if it exists
        const chart = this.charts[gaugeId];
        if (chart && typeof chart.resize === 'function') {
          chart.resize();
        } else {
          // If chart doesn't exist, trigger a full update
          if (typeof this.updateCharts === 'function') {
            this.updateCharts();
          }
        }
      }
    }
  }

  /**
   * Refresh charts when visibility changes
   */
  refreshChartsOnVisibilityChange() {
    const gaugeIds = ['icActualGauge', 'expActualGauge', 'prGauge', 'irrGauge'];
    
    gaugeIds.forEach(gaugeId => {
      const canvas = document.getElementById(gaugeId);
      if (canvas && canvas.parentElement) {
        const parent = canvas.parentElement;
        const isVisible = parent.offsetWidth > 0 && parent.offsetHeight > 0;
        
        if (isVisible) {
          // Recalculate canvas size
          const containerRect = parent.getBoundingClientRect();
          const containerStyle = window.getComputedStyle(parent);
          const paddingLeft = parseFloat(containerStyle.paddingLeft) || 0;
          const paddingRight = parseFloat(containerStyle.paddingRight) || 0;
          const paddingTop = parseFloat(containerStyle.paddingTop) || 0;
          const paddingBottom = parseFloat(containerStyle.paddingBottom) || 0;
          
          canvas.width = containerRect.width - paddingLeft - paddingRight;
          canvas.height = containerRect.height - paddingTop - paddingBottom;
          
          // Force chart resize if it exists
          const chart = this.charts[gaugeId];
          if (chart && typeof chart.resize === 'function') {
            chart.resize();
          }
        }
      }
    });
  }

  /**
   * Set default date to today's date, or most recent available date if today has no data
   * Ensures the default date is not before July 1st, 2025 (data cutoff date)
   */
  setDefaultDate() {
    if (this.dataManager && this.dataManager.realtimeData && this.dataManager.realtimeData.length > 0) {
      // Define the cutoff date - data is only available from July 1st, 2025
      const cutoffDate = new Date('2025-07-01');
      
      // Get all available dates
      const availableDates = [...new Set(this.dataManager.realtimeData.map(row => {
        const date = typeof row.date === 'string' ? row.date.split('T')[0] : row.date.toISOString().split('T')[0];
        return date;
      }))].sort();
      
      if (availableDates.length > 0) {
        // Get today's date in YYYY-MM-DD format
        const today = new Date().toISOString().split('T')[0];
        const todayDate = new Date(today);
        
        // Check if today's date is available in the data and not before cutoff
        let defaultDate = today;
        if (!availableDates.includes(today) || todayDate < cutoffDate) {
          // If today's date is not available or before cutoff, use the most recent available date
          // Filter out dates before cutoff
          const validDates = availableDates.filter(date => new Date(date) >= cutoffDate);
          if (validDates.length > 0) {
            defaultDate = validDates[validDates.length - 1];
          } else {
            // If no valid dates after cutoff, use the cutoff date itself
            defaultDate = '2025-07-01';
          }
        }
        
        // Update the date input
        const dateFilter = document.getElementById('gaugeDateFilter');
        if (dateFilter) {
          dateFilter.value = defaultDate;
          this.currentFilters.date = defaultDate;
        }
      }
    }
  }

  /**
   * Setup event listeners for gauge controls
   */
  setupEventListeners() {
    // Date navigation buttons
    const prevBtn = document.getElementById('prevDateBtn');
    const nextBtn = document.getElementById('nextDateBtn');
    const dateInput = document.getElementById('gaugeDateFilter');
    
    if (prevBtn) {
      prevBtn.addEventListener('click', () => this.navigateDate(-1));
    }
    
    if (nextBtn) {
      nextBtn.addEventListener('click', () => this.navigateDate(1));
    }
    
    if (dateInput) {
      dateInput.addEventListener('change', () => this.onDateChange());
    }

    // Action buttons
    const updateBtn = document.getElementById('gaugeUpdateBtn');
    const resetBtn = document.getElementById('gaugeResetBtn');
    
    if (updateBtn) {
      updateBtn.addEventListener('click', () => this.updateCharts());
    }
    
    if (resetBtn) {
      resetBtn.addEventListener('click', () => this.resetFilters());
    }
  }

  /**
   * Navigate to previous/next date
   */
  navigateDate(direction) {
    const dateInput = document.getElementById('gaugeDateFilter');
    if (dateInput) {
      const currentDate = new Date(dateInput.value || new Date());
      currentDate.setDate(currentDate.getDate() + direction);
      
      const newDateStr = currentDate.toISOString().split('T')[0];
      dateInput.value = newDateStr;
      
      this.currentFilters.date = newDateStr;
      this.updateCharts();
    }
  }

  /**
   * Handle date change
   */
  onDateChange() {
    const dateInput = document.getElementById('gaugeDateFilter');
    if (dateInput) {
      this.currentFilters.date = dateInput.value;
      this.updateCharts();
    }
  }

  /**
   * Update all gauge charts
   */
    updateCharts() {
    
    try {
      // Get current filter values
      this.updateCurrentFilters();
      
      // Check if selected date is before July 1st, 2025 (data cutoff date)
      if (this.currentFilters.date) {
        const selectedDate = new Date(this.currentFilters.date);
        const cutoffDate = new Date('2025-07-01');
        
        if (selectedDate < cutoffDate) {
          // Show "No Data Available" message for dates before July 1st, 2025
          this.showNoDataMessage();
          return;
        }
      }
      
      // Get filtered data
      const filteredData = this.dataManager.getFilteredRealtimeData(this.currentFilters);
      

      
      // Check if we have data for the selected date
      if (filteredData.length === 0) {
        // Show "No Data" message on all gauges
        this.showNoDataMessage();
        return;
      }
      
      // Calculate gauge values
      const gaugeValues = this.dataManager.calculateGaugeValues(filteredData);
      
      // Store gauge values for later use
      this.lastGaugeValues = gaugeValues;
      
      // Render all gauge charts with proper labels and units
      // Render immediately without delay to prevent disappearing
      this.renderGaugeChart('icActualGauge', gaugeValues.actualGeneration, gaugeValues.icBudget, 'IC Approved vs Actual', '#0072CE', '');
      this.renderGaugeChart('expActualGauge', gaugeValues.actualGeneration, gaugeValues.expectedBudget, 'Expected vs Actual', '#0072CE', '');
      this.renderGaugeChart('prGauge', gaugeValues.actualPR, gaugeValues.expectedPR, 'PR', '#0072CE', '%');
      this.renderGaugeChart('irrGauge', gaugeValues.actualIrr, gaugeValues.budgetIrr, 'Irradiation', '#0072CE', '');
      
      // Force a refresh after rendering to ensure proper sizing
      setTimeout(() => {
        this.forceRefreshCharts();
      }, 100);
      
      // Update KPI summary cards using site_state from latest data
      this.updateKPISummaryCardsFromSiteState(filteredData);
      
    } catch (error) {
      this.showNoDataMessage();
    }
  }

  /**
   * Show "No Data" message on all gauges
   */
  showNoDataMessage() {
    const gaugeIds = ['icActualGauge', 'expActualGauge', 'prGauge', 'irrGauge'];
    
    gaugeIds.forEach(gaugeId => {
      this.showNoDataMessageForGauge(gaugeId);
    });
    
    // Reset KPI summary cards to zero
    this.updateKPICardDisplay({
      totalSites: 0,
      activeSites: 0,
      inactiveSites: 0
    });
  }

  /**
   * Show "No Data" message for a specific gauge
   */
  showNoDataMessageForGauge(gaugeId) {
    const canvas = document.getElementById(gaugeId);
    if (canvas) {
      // Destroy any existing chart instance
      if (this.charts[gaugeId]) {
        try {
          this.charts[gaugeId].destroy();
          this.charts[gaugeId] = null;
        } catch (error) {
          // Error destroying chart
        }
      }
      
      // Also check Chart.js registry and destroy any remaining instances
      const existingChart = Chart.getChart(canvas);
      if (existingChart) {
        try {
          existingChart.destroy();
        } catch (error) {
          // Error destroying chart from registry
        }
      }
      
      // Clear the canvas completely
      const ctx = canvas.getContext('2d');
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      
      // Remove all existing overlays (values, percentages, etc.)
      const parent = canvas.parentNode;
      if (parent) {
        // Remove existing no-data message
        let existing = parent.querySelector('.no-data-message');
        if (existing) {
          existing.remove();
        }
        
        // Remove gauge value overlays
        let existingValue = parent.querySelector('.gauge-value');
        if (existingValue) {
          existingValue.remove();
        }
        
        // Remove gauge percentage overlays
        let existingPercentage = parent.querySelector('.gauge-percentage');
        if (existingPercentage) {
          existingPercentage.remove();
        }
        
        // Add "No Data" text
        const noDataDiv = document.createElement('div');
        noDataDiv.className = 'no-data-message text-lg font-bold text-gray-500 absolute left-1/2 top-1/2 transform -translate-x-1/2 -translate-y-1/2';
        noDataDiv.innerText = 'No Data Available';
        
        parent.style.position = 'relative';
        parent.appendChild(noDataDiv);
      }
    }
  }

  /**
   * Update current filters from UI
   */
  updateCurrentFilters() {
    // Get multi-select values (assuming they exist)
    if (window.gaugeCountryMultiSelect) {
      this.currentFilters.countries = window.gaugeCountryMultiSelect.getSelectedValues();
    }
    
    if (window.gaugePortfolioMultiSelect) {
      this.currentFilters.portfolios = window.gaugePortfolioMultiSelect.getSelectedValues();
    }
    
    // Get asset filter from multi-select
    if (window.gaugeAssetMultiSelect) {
      this.currentFilters.assets = window.gaugeAssetMultiSelect.getSelectedValues();
    } else {
      this.currentFilters.assets = [];
    }
    
    // Get date filter
    const dateFilter = document.getElementById('gaugeDateFilter');
    if (dateFilter) {
      this.currentFilters.date = dateFilter.value;
    }
  }

  /**
   * Reset all filters
   */
  resetFilters() {
    // Clear multi-select dropdowns
    if (window.gaugeCountryMultiSelect) {
      window.gaugeCountryMultiSelect.clearSelection();
    }
    if (window.gaugePortfolioMultiSelect) {
      window.gaugePortfolioMultiSelect.clearSelection();
    }
    
    // Reset asset filter
    if (window.gaugeAssetMultiSelect) {
      window.gaugeAssetMultiSelect.clearSelection();
    }
    
    // Reset date to today's date, or most recent available date if today has no data
    // Ensures the default date is not before July 1st, 2025 (data cutoff date)
    const dateFilter = document.getElementById('gaugeDateFilter');
    if (dateFilter && this.dataManager && this.dataManager.realtimeData && this.dataManager.realtimeData.length > 0) {
      // Define the cutoff date - data is only available from July 1st, 2025
      const cutoffDate = new Date('2025-07-01');
      
      const availableDates = [...new Set(this.dataManager.realtimeData.map(row => {
        const date = typeof row.date === 'string' ? row.date.split('T')[0] : row.date.toISOString().split('T')[0];
        return date;
      }))].sort();
      
      if (availableDates.length > 0) {
        // Get today's date in YYYY-MM-DD format
        const today = new Date().toISOString().split('T')[0];
        const todayDate = new Date(today);
        
        // Check if today's date is available in the data and not before cutoff
        let defaultDate = today;
        if (!availableDates.includes(today) || todayDate < cutoffDate) {
          // If today's date is not available or before cutoff, use the most recent available date
          // Filter out dates before cutoff
          const validDates = availableDates.filter(date => new Date(date) >= cutoffDate);
          if (validDates.length > 0) {
            defaultDate = validDates[validDates.length - 1];
          } else {
            // If no valid dates after cutoff, use the cutoff date itself
            defaultDate = '2025-07-01';
          }
        }
        
        dateFilter.value = defaultDate;
        this.currentFilters.date = defaultDate;
      }
    }
    
    // Reset cascading filters to show all options
    if (window.kpiDashboard) {
      window.kpiDashboard.updatePortfolioOptions([], false);
      window.kpiDashboard.updateAssetOptions([], [], false);
    }
    
    // Clear current filters and set date
    this.currentFilters = {
      countries: [],
      portfolios: [],
      assets: [],
      date: ''
    };
    
    // Set date to today's date, or most recent available date if today has no data
    // Ensures the default date is not before July 1st, 2025 (data cutoff date)
    if (this.dataManager && this.dataManager.realtimeData && this.dataManager.realtimeData.length > 0) {
      // Define the cutoff date - data is only available from July 1st, 2025
      const cutoffDate = new Date('2025-07-01');
      
      const availableDates = [...new Set(this.dataManager.realtimeData.map(row => {
        const date = typeof row.date === 'string' ? row.date.split('T')[0] : row.date.toISOString().split('T')[0];
        return date;
      }))].sort();
      
      if (availableDates.length > 0) {
        // Get today's date in YYYY-MM-DD format
        const today = new Date().toISOString().split('T')[0];
        const todayDate = new Date(today);
        
        // Check if today's date is available in the data and not before cutoff
        let defaultDate = today;
        if (!availableDates.includes(today) || todayDate < cutoffDate) {
          // If today's date is not available or before cutoff, use the most recent available date
          // Filter out dates before cutoff
          const validDates = availableDates.filter(date => new Date(date) >= cutoffDate);
          if (validDates.length > 0) {
            defaultDate = validDates[validDates.length - 1];
          } else {
            // If no valid dates after cutoff, use the cutoff date itself
            defaultDate = '2025-07-01';
          }
        }
        
        this.currentFilters.date = defaultDate;
      }
    }
    
    // Update charts after resetting filters
    this.updateCharts();
  }

  /**
   * Render a single gauge chart
   */
  renderGaugeChart(canvasId, value, max, label = null, color = null, unit = '', bgColor = null) {
    const config = this.chartConfig[canvasId];
    if (!config) {
      // Still try to render with provided/default values
    }

    // Use config values if not provided, or use defaults if config doesn't exist
    label = label || (config ? config.title : null);
    color = color || (config ? config.color : '#0072CE');
    bgColor = bgColor || (config ? config.bgColor : '#e6f1fc');

    // Destroy previous instance if exists
    if (this.charts[canvasId]) {
      try {
        this.charts[canvasId].destroy();
        this.charts[canvasId] = null;
      } catch (error) {
        // Error destroying chart, force clear the canvas
        const canvas = document.getElementById(canvasId);
        if (canvas) {
          const ctx = canvas.getContext('2d');
          if (ctx) {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
          }
        }
      }
    }

    const canvas = document.getElementById(canvasId);
    if (!canvas) {
      return;
    }

    // Force container to be visible before rendering (Chrome fix)
    const canvasContainer = canvas.parentElement;
    if (canvasContainer) {
      // Force a reflow to ensure container is properly sized
      canvasContainer.style.display = 'none';
      canvasContainer.offsetHeight; // Force reflow
      canvasContainer.style.display = '';
      
      // Wait for next frame to ensure visibility
      requestAnimationFrame(() => {
        this.renderGaugeChartImmediate(canvasId, value, max, label, color, unit, bgColor);
      });
      return;
    }
    
    this.renderGaugeChartImmediate(canvasId, value, max, label, color, unit, bgColor);
  }

  /**
   * Immediate gauge chart rendering (internal method)
   */
  renderGaugeChartImmediate(canvasId, value, max, label = null, color = null, unit = '', bgColor = null) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) {
      return;
    }

    // Clear any existing overlays and messages
    const parent = canvas.parentNode;
    if (parent) {
      // Remove existing no-data message
      const existingNoDataMessage = parent.querySelector('.no-data-message');
      if (existingNoDataMessage) {
        existingNoDataMessage.remove();
      }
      
      // Remove existing gauge value overlays
      const existingValue = parent.querySelector('.gauge-value');
      if (existingValue) {
        existingValue.remove();
      }
      
      // Remove existing gauge percentage overlays
      const existingPercentage = parent.querySelector('.gauge-percentage');
      if (existingPercentage) {
        existingPercentage.remove();
      }
    }
    
    // Ensure canvas uses full container size
    const sizingContainer = canvas.parentElement;
    if (sizingContainer) {
      // Use the full container dimensions minus any padding
      const containerRect = sizingContainer.getBoundingClientRect();
      const containerStyle = window.getComputedStyle(sizingContainer);
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

    const ctx = canvas.getContext('2d');
    
    // Double-check that no chart exists on this canvas
    const existingChart = Chart.getChart(canvas);
    if (existingChart) {
      try {
        existingChart.destroy();
      } catch (error) {
        // Error force destroying chart
      }
    }
    
    try {
      this.charts[canvasId] = new Chart(ctx, {
        type: 'doughnut',
        data: {
          datasets: [{
            data: [value, Math.max(0, max - value)],
            backgroundColor: [color, bgColor],
            borderWidth: 0,
            circumference: 180,
            rotation: 270,
            cutout: '75%',
          }]
        },
        options: {
          plugins: {
            legend: { display: false },
            tooltip: { enabled: false },
            title: { display: false }
          },
          responsive: true,
          maintainAspectRatio: false,
          animation: { animateRotate: false, duration: 0 }, // Disable animation for immediate rendering
          circumference: 180,
          rotation: 270,
        }
      });
      
      // Force immediate update and resize
      requestAnimationFrame(() => {
        if (this.charts[canvasId]) {
          this.charts[canvasId].update('none'); // Update without animation
          this.charts[canvasId].resize();
        }
      });
      
    } catch (error) {
      // If chart creation fails, show "No Data Available" message
      this.showNoDataMessageForGauge(canvasId);
      return;
    }

    // Show the numeric value in the center (overlay)
    // Add a small delay to ensure chart is fully rendered
    setTimeout(() => {
      try {
        this.updateGaugeValue(canvasId, value, max, unit);
      } catch (error) {
      }
    }, 100);
  }

  /**
   * Update gauge value overlay
   */
  updateGaugeValue(canvasId, value, max, unit = '') {
    const canvas = document.getElementById(canvasId);
    if (!canvas) {
      return;
    }



    // Remove existing elements immediately
    const parent = canvas.parentNode;
    if (parent) {
      // Remove existing gauge value overlays
      let existingValue = parent.querySelector('.gauge-value');
      if (existingValue) {
        existingValue.remove();
      }
      
      // Remove existing gauge percentage overlays
      let existingPercentage = parent.querySelector('.gauge-percentage');
      if (existingPercentage) {
        existingPercentage.remove();
      }
      
      // Remove any existing no-data messages
      let existingNoData = parent.querySelector('.no-data-message');
      if (existingNoData) {
        existingNoData.remove();
      }
    }

    // Create main value display
    const valueDiv = document.createElement('div');
    valueDiv.className = 'gauge-value text-lg md:text-xl lg:text-2xl font-bold text-[#0072CE] absolute left-1/2 top-[60%] transform -translate-x-1/2 -translate-y-1/2 drop-shadow-lg';
    
    // Add inline styles to ensure visibility even if Tailwind doesn't load
    valueDiv.style.position = 'absolute';
    valueDiv.style.left = '50%';
    valueDiv.style.top = '60%';
    valueDiv.style.transform = 'translate(-50%, -50%)';
    valueDiv.style.color = '#0072CE';
    valueDiv.style.fontWeight = 'bold';
    valueDiv.style.fontSize = '1.25rem';
    valueDiv.style.zIndex = '20';
    valueDiv.style.pointerEvents = 'none';
    valueDiv.style.textShadow = '0 1px 3px rgba(0,0,0,0.1)';
    
    // Format values with appropriate units and K suffix for large numbers
    const formatValue = (val) => {
      if (isNaN(val) || val === null || val === undefined) {
        return '0.0';
      }
      if (val >= 1000) {
        return (val / 1000).toFixed(1) + 'K';
      }
      return val.toFixed(1);
    };
    
    // Special formatting for PR gauge - show as percentages
    if (canvasId === 'prGauge') {
      // Convert decimal values to percentages (e.g., 0.70 -> 70%)
      const actualPercent = (value * 100).toFixed(1);
      const expectedPercent = (max * 100).toFixed(1);
      valueDiv.innerText = `${actualPercent}% / ${expectedPercent}%`;
    } else {
      valueDiv.innerText = `${formatValue(value)} / ${formatValue(max)}`;
    }
    
    // Ensure parent has relative positioning
    if (!parent) {
      return;
    }
    
    try {
      parent.style.position = 'relative';
      parent.appendChild(valueDiv);
    } catch (error) {
      // Error appending gauge value div
    }
    

    
    // Add percentage label at the end of the gauge arc
    if (max > 0) {
      let percentage;
      // For PR gauge, calculate percentage based on converted values
      if (canvasId === 'prGauge') {
        const actualPercent = value * 100;
        const expectedPercent = max * 100;
        percentage = (actualPercent / expectedPercent * 100).toFixed(1);
      } else {
        percentage = (value / max * 100).toFixed(1);
      }
      
      let percentageDiv = document.createElement('div');
      percentageDiv.className = 'gauge-percentage text-sm font-bold text-[#0072CE] absolute bg-white px-2 py-1 rounded shadow-lg border border-[#0072CE]';
      // Add inline styles to ensure visibility
      percentageDiv.style.backgroundColor = 'white';
      percentageDiv.style.color = '#0072CE';
      percentageDiv.style.fontWeight = 'bold';
      percentageDiv.style.fontSize = '12px';
      percentageDiv.style.padding = '4px 8px';
      percentageDiv.style.borderRadius = '4px';
      percentageDiv.style.boxShadow = '0 2px 4px rgba(0,0,0,0.2)';
      percentageDiv.style.border = '2px solid #0072CE';
      
      // Position the percentage label in a visible location
      // Try positioning it in the top-right area of the gauge
      percentageDiv.style.left = '80%';
      percentageDiv.style.top = '20%';
      percentageDiv.style.transform = 'translate(-50%, -50%)';
      percentageDiv.style.zIndex = '30';
      percentageDiv.style.position = 'absolute';
      
      percentageDiv.innerText = `${percentage}%`;
      parent.appendChild(percentageDiv);
      

    }
  }

  /**
   * Format value for display
   */
  formatValue(value, unit = '') {
    // Handle PR values (convert decimal to percentage)
    if (unit === '%' || unit === 'PR') {
      return (value * 100).toFixed(1) + '%';
    }
    
    if (value >= 1000) {
      return (value / 1000).toFixed(1) + 'K' + unit;
    }
    return value.toFixed(1) + unit;
  }



  /**
   * Populate asset dropdown
   * This method is now handled by updateAssetOptions() which uses multi-select components
   */

  /**
   * Destroy all charts
   */
  destroy() {
    const gaugeIds = ['icActualGauge', 'expActualGauge', 'prGauge', 'irrGauge'];
    
    gaugeIds.forEach(canvasId => {
      try {
        // First, try to destroy using our internal reference
        const chart = this.charts[canvasId];
        if (chart && typeof chart.destroy === 'function') {
          chart.destroy();

        }
        
        // Then, check Chart.js registry and destroy any remaining instances
        const canvas = document.getElementById(canvasId);
        if (canvas) {
          const chartFromRegistry = Chart.getChart(canvas);
          if (chartFromRegistry) {
            chartFromRegistry.destroy();

          }
        }
      } catch (error) {
        // Error destroying chart
      }
    });
    
    // Clear our internal references
    this.charts = {};
    
    // Force Chart.js to clear its registry for these canvases
    setTimeout(() => {
      gaugeIds.forEach(canvasId => {
        const canvas = document.getElementById(canvasId);
        if (canvas) {
          // Clear the canvas context
          const ctx = canvas.getContext('2d');
          ctx.clearRect(0, 0, canvas.width, canvas.height);
        }
      });
    }, 50);
  }

  /**
   * Update KPI summary cards using site_state from latest data
   */
  updateKPISummaryCardsFromSiteState(filteredData) {
    try {
      // Check if we have data
      if (!filteredData || filteredData.length === 0) {
        return;
      }

      // Calculate KPI values using site_state column
      const kpiValues = this.calculateKPISummaryValuesFromSiteState(filteredData);
      
      // Update the UI elements
      this.updateKPICardDisplay(kpiValues);
      
    } catch (error) {
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
    
    filteredData.forEach(row => {
      const assetCode = row.asset_code || row.assetno || row.asset_number || row.asset;
      if (!assetCode) return;
      
      const lastUpdated = row.last_updated || row.updated_at || row.created_at || row.date;
      if (!lastUpdated) return;
      
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

    return {
      totalSites,
      activeSites,
      inactiveSites,
    };
  }

  /**
   * Update KPI card display elements
   */
  updateKPICardDisplay(kpiValues) {
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
   * Handle filter changes from multi-select components
   */
  onFilterChange() {
    this.updateCharts();
  }

  /**
   * Force clear Chart.js registry for our canvases
   */
  forceClearChartRegistry() {
    const gaugeIds = ['icActualGauge', 'expActualGauge', 'prGauge', 'irrGauge'];
    
    gaugeIds.forEach(canvasId => {
      const canvas = document.getElementById(canvasId);
      if (canvas) {
        try {
          // Get any chart from registry
          const chart = Chart.getChart(canvas);
          if (chart) {
            chart.destroy();

          }
          
          // Clear canvas
          const ctx = canvas.getContext('2d');
          ctx.clearRect(0, 0, canvas.width, canvas.height);
        } catch (error) {
          // Error clearing chart registry
        }
      }
    });
  }

  /**
   * Force refresh all charts (useful when switching tabs)
   */
  forceRefreshCharts() {
    const gaugeIds = ['icActualGauge', 'expActualGauge', 'prGauge', 'irrGauge'];
    
    gaugeIds.forEach(gaugeId => {
      try {
        const canvas = document.getElementById(gaugeId);
        if (!canvas || !canvas.parentElement) {
          return; // Skip if canvas doesn't exist
        }
        
        const parent = canvas.parentElement;
        const isVisible = parent.offsetWidth > 0 && parent.offsetHeight > 0;
        
        if (!isVisible) {
          return; // Skip if not visible
        }
        
        // Recalculate canvas size
        const containerRect = parent.getBoundingClientRect();
        const containerStyle = window.getComputedStyle(parent);
        const paddingLeft = parseFloat(containerStyle.paddingLeft) || 0;
        const paddingRight = parseFloat(containerStyle.paddingRight) || 0;
        const paddingTop = parseFloat(containerStyle.paddingTop) || 0;
        const paddingBottom = parseFloat(containerStyle.paddingBottom) || 0;
        
        const newWidth = containerRect.width - paddingLeft - paddingRight;
        const newHeight = containerRect.height - paddingTop - paddingBottom;
        
        // Only update if size changed
        if (canvas.width !== newWidth || canvas.height !== newHeight) {
          canvas.width = newWidth;
          canvas.height = newHeight;
        }
        
        // Force chart resize if it exists and has valid canvas
        const chart = this.charts[gaugeId];
        if (chart && chart.canvas && chart.canvas.parentNode && typeof chart.resize === 'function') {
          try {
            chart.resize();
            // Force immediate update
            if (typeof chart.update === 'function') {
              chart.update('none');
            }
          } catch (resizeError) {
            // Chart resize failed, might be destroyed
          }
        }
      } catch (error) {
        // Silently skip this gauge if any error occurs
      }
    });
  }

  /**
   * Check if gauges need initial visibility fix (Chrome-specific)
   */
  checkInitialVisibility() {
    const gaugeIds = ['icActualGauge', 'expActualGauge', 'prGauge', 'irrGauge'];
    let needsFix = false;
    
    gaugeIds.forEach(gaugeId => {
      const canvas = document.getElementById(gaugeId);
      if (canvas && canvas.parentElement) {
        const parent = canvas.parentElement;
        const isVisible = parent.offsetWidth > 0 && parent.offsetHeight > 0;
        const chart = this.charts[gaugeId];
        
        // Check if container is visible but chart is not properly rendered
        if (isVisible && (!chart || !chart.canvas || chart.canvas.width === 0)) {
          needsFix = true;
        }
      }
    });
    
    if (needsFix) {
      this.reinitialize();
    }
  }

  /**
   * Reinitialize gauge charts (for auto-refresh scenarios)
   */
  reinitialize() {
    try {

      
      // Destroy existing charts
      this.destroy();
      
      // Clear any existing overlays and messages
      const gaugeIds = ['icActualGauge', 'expActualGauge', 'prGauge', 'irrGauge'];
      gaugeIds.forEach(gaugeId => {
        const canvas = document.getElementById(gaugeId);
        if (canvas && canvas.parentNode) {
          const parent = canvas.parentNode;
          
          // Remove existing no-data messages
          const existingNoDataMessage = parent.querySelector('.no-data-message');
          if (existingNoDataMessage) {
            existingNoDataMessage.remove();
          }
          
          // Remove existing gauge value overlays
          const existingValue = parent.querySelector('.gauge-value');
          if (existingValue) {
            existingValue.remove();
          }
          
          // Remove existing gauge percentage overlays
          const existingPercentage = parent.querySelector('.gauge-percentage');
          if (existingPercentage) {
            existingPercentage.remove();
          }
        }
      });
      
      // Add a longer delay to ensure proper cleanup and Chart.js registry clearing
      setTimeout(() => {
        // Force clear Chart.js registry one more time
        this.forceClearChartRegistry();
        
        // Set default date
        this.setDefaultDate();
        
        // Update charts
        this.updateCharts();
        

      }, 200);
      
    } catch (error) {
      // Error reinitializing gauge charts
    }
  }
}

// Export for use in other modules
window.GaugeChartsManager = GaugeChartsManager;

// Global function to force refresh gauge charts (can be called from other modules)
window.refreshGaugeCharts = function() {
  if (window.gaugeChartsManager && typeof window.gaugeChartsManager.forceRefreshCharts === 'function') {
    window.gaugeChartsManager.forceRefreshCharts();
  }
};

// Global function to handle page navigation scenarios
window.handlePageNavigation = function() {
  // Check if we're on the KPI page
  if (document.getElementById('gaugesSection')) {
    setTimeout(() => {
      // Use the more targeted visibility check instead of aggressive refresh
      if (window.gaugeChartsManager) {
        if (typeof window.gaugeChartsManager.checkInitialVisibility === 'function') {
          window.gaugeChartsManager.checkInitialVisibility();
        }
      }
    }, 500);
  }
};

// Listen for page navigation events
document.addEventListener('DOMContentLoaded', function() {
  // Handle initial page load
  setTimeout(() => {
    window.handlePageNavigation();
  }, 1000);
});

// Listen for browser back/forward navigation
window.addEventListener('popstate', function() {
  setTimeout(() => {
    window.handlePageNavigation();
  }, 500);
});

// Chrome-specific: Force gauge visibility when page becomes visible
document.addEventListener('visibilitychange', function() {
  if (!document.hidden) {
    const gaugesSection = document.getElementById('gaugesSection');
    if (gaugesSection && !gaugesSection.classList.contains('hidden')) {
      setTimeout(() => {
        if (window.gaugeChartsManager) {
          window.gaugeChartsManager.forceRefreshCharts();
          if (typeof window.gaugeChartsManager.updateCharts === 'function') {
            window.gaugeChartsManager.updateCharts();
          }
        }
      }, 200);
    }
  }
});

// Chrome-specific fix: Check gauge visibility on page focus (less aggressive)
window.addEventListener('focus', function() {
  if (document.getElementById('gaugesSection') && !document.getElementById('gaugesSection').classList.contains('hidden')) {
    setTimeout(() => {
      if (window.gaugeChartsManager && typeof window.gaugeChartsManager.checkInitialVisibility === 'function') {
        window.gaugeChartsManager.checkInitialVisibility();
      }
    }, 300);
  }
});

// Chrome-specific fix: Check gauge visibility on window resize
window.addEventListener('resize', function() {
  if (document.getElementById('gaugesSection') && !document.getElementById('gaugesSection').classList.contains('hidden')) {
    setTimeout(() => {
      if (window.gaugeChartsManager && typeof window.gaugeChartsManager.checkInitialVisibility === 'function') {
        window.gaugeChartsManager.checkInitialVisibility();
      }
    }, 300);
  }
});

// Chrome-specific fix: Force gauge visibility on any click (but only if gauges are not visible)
document.addEventListener('click', function(event) {
  const gaugesSection = document.getElementById('gaugesSection');
  if (gaugesSection && !gaugesSection.classList.contains('hidden')) {
    // Check if any gauge is not properly rendered
    const gaugeIds = ['icActualGauge', 'expActualGauge', 'prGauge', 'irrGauge'];
    let needsRefresh = false;
    
    gaugeIds.forEach(gaugeId => {
      const canvas = document.getElementById(gaugeId);
      if (canvas && canvas.parentElement) {
        const parent = canvas.parentElement;
        const isVisible = parent.offsetWidth > 0 && parent.offsetHeight > 0;
        const chart = window.gaugeChartsManager ? window.gaugeChartsManager.charts[gaugeId] : null;
        
        if (isVisible && (!chart || !chart.canvas || chart.canvas.width === 0)) {
          needsRefresh = true;
        }
      }
    });
    
    if (needsRefresh && window.gaugeChartsManager) {
      window.gaugeChartsManager.forceRefreshCharts();
      if (typeof window.gaugeChartsManager.updateCharts === 'function') {
        window.gaugeChartsManager.updateCharts();
      }
    }
  }
});
