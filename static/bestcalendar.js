// BestCalendar Component - Reusable Month/Year Picker
// Pure JavaScript version with delegation + fixes

// Prevent duplicate declaration
if (typeof window.BestCalendar !== 'undefined') {
  // BestCalendar already exists, don't redefine
} else {

// Inject CSS styles
const bestCalendarStyles = `
/* BestCalendar Component Styles */
.month-trigger-btn {
  background: #f8fbff;
  border: 1px solid #b3d7f2;
  border-radius: 6px;
  padding: 4px 8px;
  font-size: clamp(0.75rem, 0.8vw, 0.9rem);
  color: #0072CE;
  cursor: pointer;
  text-align: left;
  transition: background 0.2s, border-color 0.2s;
  white-space: nowrap;
  min-width: 100px;
}
.month-trigger-btn:hover { background: #e6f1fc; border-color: #0072CE; }

.month-matrix-picker {
  position: relative;
  z-index: 999999 !important;
  background: #fff;
  box-shadow: 0 4px 16px rgba(0,0,0,0.1);
  border-radius: 10px;
  min-width: 280px;
  max-width: 400px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  padding: 20px;
}
.picker-tabs { display: flex; justify-content: space-around; margin-bottom: 16px; border-bottom: 1px solid #e0e0e0; padding-bottom: 8px; width: 100%; }
.tab-btn { border: none; background: none; padding: 8px 16px; cursor: pointer; font-size: 14px; color: #666; font-weight: 500; transition: color 0.2s; }
.tab-btn.active { color: #0072CE; font-weight: bold; border-bottom: 2px solid #0072CE; }
.tab-btn:hover { color: #0072CE; }
.picker-view { display: none; width: 100%; }
.picker-view.active { display: block; }

/* BestCalendar tab classes */
.bc-tabs { display: flex; justify-content: space-around; margin-bottom: 16px; border-bottom: 1px solid #e0e0e0; padding-bottom: 8px; width: 100%; }
.bc-tab-btn { border: none; background: none; padding: 8px 16px; cursor: pointer; font-size: 14px; color: #666; font-weight: 500; transition: color 0.2s; }
.bc-tab-btn.bc-active { color: #0072CE; font-weight: bold; border-bottom: 2px solid #0072CE; }
.bc-tab-btn:hover { color: #0072CE; }
.bc-content { width: 100%; }
.month-matrix-year-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; width: 100%; }
.month-matrix-year-row button { background: none; border: none; font-size: 18px; cursor: pointer; color: #0072CE; padding: 4px 8px; border-radius: 4px; }
.month-matrix-year-row button:hover { background: #f0f8ff; }
.month-matrix-year-label { font-weight: bold; color: #333; font-size: 16px; }
.month-matrix-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; width: 100%; }
.month-matrix-cell { padding: 8px 4px; text-align: center; border: 1px solid #e0e0e0; border-radius: 4px; cursor: pointer; font-size: 12px; transition: all 0.2s; background: white; color: #333; }
.month-matrix-cell.selected, .month-matrix-cell:hover { background: #0072CE; color: white; border-color: #0072CE; }
.month-matrix-cell.disabled { background: #f5f5f5; color: #ccc; cursor: not-allowed; }

/* BestCalendar specific classes */
.bc-month-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; width: 100%; }
.bc-month-cell { padding: 8px 4px; text-align: center; border: 1px solid #e0e0e0; border-radius: 4px; cursor: pointer; font-size: 12px; transition: all 0.2s; background: white; color: #333; }
.bc-month-cell.bc-selected, .bc-month-cell:hover { background: #0072CE; color: white; border-color: #0072CE; }
.bc-month-cell.bc-disabled { background: #f5f5f5; color: #ccc; cursor: not-allowed; }
.year-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; width: 100%; }
.year-cell { padding: 12px 8px; text-align: center; border: 1px solid #e0e0e0; border-radius: 6px; cursor: pointer; font-size: 14px; font-weight: 500; transition: all 0.2s; background: white; color: #333; }
.year-cell.selected, .year-cell:hover { background: #0072CE; color: white; border-color: #0072CE; }

/* BestCalendar year classes */
.bc-year-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; width: 100%; }
.bc-year-cell { padding: 12px 8px; text-align: center; border: 1px solid #e0e0e0; border-radius: 6px; cursor: pointer; font-size: 14px; font-weight: 500; transition: all 0.2s; background: white; color: #333; }
.bc-year-cell.bc-selected, .bc-year-cell:hover { background: #0072CE; color: white; border-color: #0072CE; }
.filter-pill { position: relative; display: inline-block; }

/* Range selection styles */
.range-instructions {
  text-align: center;
  font-size: 12px;
  color: #666;
  margin-bottom: 8px;
  padding: 4px;
  background: #f8f9fa;
  border-radius: 4px;
}

@keyframes pulse {
  0% { transform: scale(1); }
  50% { transform: scale(1.05); }
  100% { transform: scale(1); }
}

.bc-hidden {
  display: none !important;
}

/* Ensure calendar appears above all other elements */
#calendarContainer {
  z-index: 999999 !important;
  position: absolute !important;
}

#monthMatrixPicker {
  z-index: 999999 !important;
  position: relative !important;
}
.range-selection-info {
  margin-top: 8px;
  padding: 8px;
  background: #f8f9fa;
  border-radius: 4px;
  font-size: 12px;
  text-align: center;
}

/* BestCalendar range classes */
.bc-range-info {
  margin-top: 8px;
  padding: 8px;
  background: #f8f9fa;
  border-radius: 4px;
  font-size: 12px;
  text-align: center;
}
.bc-range-selected {
  color: #0072CE;
  font-weight: bold;
}
.bc-range-selecting {
  color: #666;
}
.bc-range-prompt {
  color: #999;
}
.range-selected {
  color: #0072CE;
  font-weight: bold;
}
.range-selecting {
  color: #666;
}
.range-prompt {
  color: #999;
}
.month-matrix-cell.range-start {
  background: #0072CE !important;
  color: white !important;
  border-color: #0072CE !important;
  font-weight: bold;
}
.month-matrix-cell.range-end {
  background: #0072CE !important;
  color: white !important;
  border-color: #0072CE !important;
  font-weight: bold;
}
.month-matrix-cell.range-middle {
  background: #e3f2fd !important;
  color: #0072CE !important;
  border-color: #0072CE !important;
}
@media (max-width: 768px) {
  .month-matrix-picker { min-width: 260px; padding: 16px; }
  .month-matrix-grid { grid-template-columns: repeat(3, 1fr); gap: 6px; }
  .month-matrix-cell { padding: 6px 2px; font-size: 11px; }
  .year-grid { grid-template-columns: repeat(2, 1fr); }
}
`;

// Inject styles into document
function injectBestCalendarStyles() {
  if (!document.getElementById('bestcalendar-styles')) {
    const styleElement = document.createElement('style');
    styleElement.id = 'bestcalendar-styles';
    styleElement.textContent = bestCalendarStyles;
    document.head.appendChild(styleElement);
  }
}

class BestCalendar {
  constructor({ triggerId, pickerId, labelId, data, options = {} }) {
    // Remove the problematic line that returns existing instance
    // if (typeof window.BestCalendar !== "undefined") return window.BestCalendar;

    this.triggerId = triggerId;
    this.pickerId = pickerId;
    this.labelId = labelId;
    this.data = data || [];
    this.options = Object.assign({
      range: false,
      rangeMode: false, // Compatibility with existing code
      autoCloseDelay: 1000,
      onPeriodChange: null
    }, options);

    // Use rangeMode if provided for compatibility
    if (this.options.rangeMode) {
      this.options.range = true;
    }

    // Default to range view if range mode is enabled, otherwise month view
    this.currentView = this.options.range ? "range" : "month";
    this.selectedMonth = null;
    this.selectedYear = new Date().getFullYear(); // Initialize with current year
    this.rangeStart = null;
    this.rangeEnd = null;
    this.selectedRange = { start: null, end: null }; // Compatibility with existing code
    
    // Ensure selectedRange is always properly initialized
    if (!this.selectedRange || typeof this.selectedRange !== 'object') {
      this.selectedRange = { start: null, end: null };
    }
    if (typeof this.selectedRange.start === 'undefined') {
      this.selectedRange.start = null;
    }
    if (typeof this.selectedRange.end === 'undefined') {
      this.selectedRange.end = null;
    }

    this.trigger = null;
    this.picker = null;
    this.label = null;
    this.isDestroyed = false;

    this.injectStyles();
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", () => this.init());
    } else {
      this.init();
    }

    // Don't overwrite the global BestCalendar class with instance
    // window.BestCalendar = this;
  }

  injectStyles() {
    if (document.getElementById("bestcalendar-styles")) return;
    const style = document.createElement("style");
    style.id = "bestcalendar-styles";
    style.textContent = `
      .bc-hidden { display: none !important; }
      .bc-picker {
        position: absolute;
        z-index: 99999;
        background: #fff;
        box-shadow: 0 4px 16px rgba(0,0,0,0.1);
        margin-top: 4px;
        border-radius: 10px;
        top: 100%;
        left: 0;
        right: 0;
        min-width: 280px;
        max-width: 400px;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 16px;
        padding: 20px;
        border: 1px solid #e0e0e0;
      }
      .bc-tabs { 
        display: flex; 
        justify-content: space-around; 
        margin-bottom: 16px; 
        border-bottom: 1px solid #e0e0e0; 
        padding-bottom: 8px; 
        width: 100%; 
      }
      .bc-tab-btn { 
        cursor: pointer; 
        padding: 8px 16px; 
        border: none; 
        background: none; 
        font-size: 14px; 
        color: #666; 
        font-weight: 500; 
        transition: color 0.2s; 
      }
      .bc-tab-btn.bc-active { 
        color: #0072CE; 
        font-weight: bold; 
        border-bottom: 2px solid #0072CE; 
      }
      .bc-tab-btn:hover { 
        color: #0072CE; 
      }
      .bc-content { 
        width: 100%; 
      }
      .bc-month-grid { 
        display: grid; 
        grid-template-columns: repeat(3, 1fr); 
        gap: 8px; 
        width: 100%; 
      }
      .bc-year-grid { 
        display: grid; 
        grid-template-columns: repeat(3, 1fr); 
        gap: 8px; 
        width: 100%; 
      }
      .bc-month-cell, .bc-year-cell { 
        cursor: pointer; 
        padding: 8px 4px; 
        text-align: center; 
        border: 1px solid #e0e0e0; 
        border-radius: 4px; 
        font-size: 12px; 
        transition: all 0.2s; 
        background: white; 
        color: #333; 
      }
      .bc-month-cell:hover, .bc-year-cell:hover { 
        background: #0072CE; 
        color: white; 
        border-color: #0072CE; 
      }
      .bc-month-cell.bc-selected, .bc-year-cell.bc-selected { 
        background: #0072CE; 
        color: white; 
        border-color: #0072CE; 
      }
      .bc-month-cell.bc-disabled { 
        background: #f5f5f5; 
        color: #ccc; 
        cursor: not-allowed; 
      }
      .bc-range-start { 
        background: #0072CE !important; 
        color: white !important; 
        border-color: #0072CE !important; 
        font-weight: bold; 
      }
      .bc-range-end { 
        background: #0072CE !important; 
        color: white !important; 
        border-color: #0072CE !important; 
        font-weight: bold; 
      }
      .bc-range-middle { 
        background: #e6f1fc !important; 
        color: #0072CE !important; 
        border-color: #0072CE !important; 
      }
      .bc-trigger {
        width: 100%;
        background: #f8fbff;
        border: 1px solid #b3d7f2;
        border-radius: 6px;
        padding: 8px 12px;
        font-size: 14px;
        color: #0072CE;
        cursor: pointer;
        text-align: left;
        transition: background 0.2s, border-color 0.2s;
        display: flex;
        justify-content: space-between;
        align-items: center;
        user-select: none;
      }
      .bc-trigger:hover { 
        background: #e6f1fc; 
        border-color: #0072CE; 
      }
      .bc-range-info {
        margin-top: 8px;
        padding: 8px;
        background: #f8f9fa;
        border-radius: 4px;
        font-size: 12px;
        text-align: center;
      }
      .bc-range-selected {
        color: #0072CE;
        font-weight: bold;
      }
      .bc-range-selecting {
        color: #666;
      }
      .bc-range-prompt {
        color: #999;
      }
      @keyframes bc-pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.05); }
        100% { transform: scale(1); }
      }
    `;
    document.head.appendChild(style);
  }

  init() {
    this.trigger = document.getElementById(this.triggerId);
    this.picker = document.getElementById(this.pickerId);
    this.label = document.getElementById(this.labelId);

    if (!this.trigger || !this.picker || !this.label) {
      console.warn("BestCalendar: Missing DOM elements", {
        trigger: this.trigger,
        picker: this.picker,
        label: this.label
      });
      return;
    }

    // Add classes for styling
    this.trigger.classList.add('bc-trigger');
    this.picker.classList.add('bc-picker');

    // Ensure picker is hidden initially
    this.picker.style.display = 'none';
    
    // If there's pending data, render it now
    if (this.pendingData) {
      this.renderPicker();
      this.hidePicker();
      this.pendingData = null;
    }

    this.trigger.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      this.togglePicker();
    });

    // Close picker when clicking outside
    document.addEventListener("click", (e) => {
      if (!this.picker.contains(e.target) && e.target !== this.trigger) {
        // In range mode, only hide picker if no range selection is in progress
        if (this.options.range && this.rangeStart && !this.rangeEnd) {
          return;
        }
        this.hidePicker();
      }
    });

    // Add keyboard support
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && this.picker.style.display !== 'none') {
        this.hidePicker();
      }
    });

    // Initialize the calendar structure
    this.renderTabs();
    this.renderPicker();
    this.updateLabel();
    
    // Force a re-render of the current view to ensure event listeners are attached
    setTimeout(() => {
      this.renderPicker();
    }, 50);
  }

  togglePicker() {
    const isHidden = this.picker.style.display === 'none';
    if (isHidden) {
      this.showPicker();
    } else {
      this.hidePicker();
    }
  }

  showPicker() {
    this.picker.style.display = 'flex';
    this.picker.classList.remove("bc-hidden");
    
    // Force a complete re-render to ensure everything is properly set up
    this.renderTabs();
    this.renderPicker();
    this.updateLabel();
    
    // Double-check that event listeners are attached
    setTimeout(() => {
      this.renderPicker();
    }, 50);
  }

  hidePicker() {
    this.picker.style.display = 'none';
    this.picker.classList.add("bc-hidden");
  }

  renderTabs() {
    // Check if tabs already exist
    const existingTabs = this.picker.querySelector(".bc-tabs");
    
    if (!existingTabs) {
      // First time rendering - create the full structure
      this.picker.innerHTML = `
        <div class="bc-tabs">
          <span class="bc-tab-btn ${this.currentView === "month" ? "bc-active" : ""}" data-view="month">Month</span>
          <span class="bc-tab-btn ${this.currentView === "year" ? "bc-active" : ""}" data-view="year">Year</span>
          ${this.options.range ? `<span class="bc-tab-btn ${this.currentView === "range" ? "bc-active" : ""}" data-view="range">Range</span>` : ''}
        </div>
        <div class="bc-content"></div>
        ${this.options.range ? '<div class="bc-range-info"></div>' : ''}
      `;
    } else {
      // Update existing tabs with correct active state
      const tabButtons = existingTabs.querySelectorAll(".bc-tab-btn");
      tabButtons.forEach(btn => {
        const view = btn.dataset.view;
        if (view === this.currentView) {
          btn.classList.add("bc-active");
        } else {
          btn.classList.remove("bc-active");
        }
      });
    }

    // Add event listeners to tab buttons (only if not already added)
    this.picker.querySelectorAll(".bc-tab-btn").forEach(btn => {
      if (!btn.hasAttribute('data-listener-added')) {
        btn.setAttribute('data-listener-added', 'true');
        btn.addEventListener("click", (e) => {
          e.preventDefault();
          e.stopPropagation();
          
          const view = btn.dataset.view;
          this.currentView = view;
          
          // Clear selections when switching tabs to ensure clean state
          if (view === "month") {
            // Clear range selections when switching to month mode
            this.rangeStart = null;
            this.rangeEnd = null;
            this.selectedRange = { start: null, end: null };
            // Clear range info display
            const rangeInfo = this.picker.querySelector(".bc-range-info");
            if (rangeInfo) {
              rangeInfo.innerHTML = "";
            }
            // Ensure we have a valid year for month selection
            if (!this.selectedYear) {
              this.selectedYear = new Date().getFullYear();
            }
          } else if (view === "year") {
            // Clear month and range selections when switching to year mode
            this.selectedMonth = null;
            this.rangeStart = null;
            this.rangeEnd = null;
            this.selectedRange = { start: null, end: null };
            // Clear range info display
            const rangeInfo = this.picker.querySelector(".bc-range-info");
            if (rangeInfo) {
              rangeInfo.innerHTML = "";
            }
          } else if (view === "range") {
            // Clear month selection when switching to range mode
            this.selectedMonth = null;
          }
          
          // Update tab active states
          this.picker.querySelectorAll(".bc-tab-btn").forEach(tabBtn => {
            if (tabBtn.dataset.view === this.currentView) {
              tabBtn.classList.add("bc-active");
            } else {
              tabBtn.classList.remove("bc-active");
            }
          });
          
          // Small delay to ensure DOM updates properly before rendering
          setTimeout(() => {
            this.renderPicker();
            this.updateLabel();
          }, 10);
        });
      }
    });
  }

  renderPicker() {
    if (!this.picker) {
      console.warn("BestCalendar: Picker not initialized yet");
      return;
    }
    
    // Ensure the picker has the proper structure
    if (!this.picker.querySelector(".bc-content")) {
      this.renderTabs();
    }
    
    const content = this.picker.querySelector(".bc-content");
    if (!content) {
      console.error('No content element found after renderTabs');
      return;
    }

    if (this.currentView === "month") {
      this.renderMonthView(content);
    } else if (this.currentView === "year") {
      this.renderYearView(content);
    } else if (this.currentView === "range") {
      this.renderRangeView(content);
    }
  }

  renderMonthView(content) {
    const months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
    const availableMonths = this.getAvailableMonths();
    
    content.innerHTML = `
      <div class="bc-month-grid">
        ${months.map((m, i) => {
          const monthNum = i + 1;
          const isAvailable = availableMonths.includes(monthNum);
          const isSelected = this.selectedMonth === monthNum;
          const className = `bc-month-cell ${isSelected ? 'bc-selected' : ''} ${!isAvailable ? 'bc-disabled' : ''}`;
          return `<div class="${className}" data-month="${monthNum}" ${!isAvailable ? 'data-disabled="true"' : ''}>${m}</div>`;
        }).join("")}
      </div>
    `;

    // Use event delegation for more reliable event handling
    const monthGrid = content.querySelector(".bc-month-grid");
    if (monthGrid) {
      // Remove any existing event listeners by cloning the element
      const newGrid = monthGrid.cloneNode(true);
      monthGrid.parentNode.replaceChild(newGrid, monthGrid);
      
      // Create a bound event handler
      this.monthClickHandler = (e) => {
        e.preventDefault();
        e.stopPropagation();
        
        const cell = e.target.closest('.bc-month-cell');
        if (!cell || cell.dataset.disabled) {
          return;
        }
        
        const month = parseInt(cell.dataset.month);
        if (!isNaN(month)) {
          this.handleMonthSelection(month);
        }
      };
      
      // Add the event listener to the grid container
      newGrid.addEventListener("click", this.monthClickHandler);
    }
  }

  renderYearView(content) {
    try {
      const years = [...new Set(this.data.map(d => {
        try {
          if (!d || !d.month || typeof d.month !== 'string') {
            return null;
          }
          return parseInt(d.month.split("-")[0]);
        } catch (error) {
          console.warn('Error parsing year from data:', d?.month, error);
          return null;
        }
      }).filter(year => year !== null))].sort();
      
      content.innerHTML = `
        <div class="bc-year-grid">
          ${years.map(y => {
            const isSelected = this.selectedYear === y;
            const className = `bc-year-cell ${isSelected ? 'bc-selected' : ''}`;
            return `<div class="${className}" data-year="${y}">${y}</div>`;
          }).join("")}
        </div>
      `;

      // Use event delegation for more reliable event handling
      const yearGrid = content.querySelector(".bc-year-grid");
      if (yearGrid) {
        // Remove any existing event listeners by cloning the element
        const newGrid = yearGrid.cloneNode(true);
        yearGrid.parentNode.replaceChild(newGrid, yearGrid);
        
        // Create a bound event handler
        this.yearClickHandler = (e) => {
          e.preventDefault();
          e.stopPropagation();
          
          const cell = e.target.closest('.bc-year-cell');
          if (!cell) {
            return;
          }
          
          const year = parseInt(cell.dataset.year);
          if (!isNaN(year)) {
            this.handleYearSelection(year);
          }
        };
        
        // Add the event listener to the grid container
        newGrid.addEventListener("click", this.yearClickHandler);
      }
    } catch (error) {
      console.error('Error in renderYearView:', error);
      content.innerHTML = '<div style="padding: 20px; text-align: center; color: #666;">Error loading years</div>';
    }
  }

  renderRangeView(content) {
    const months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
    const availableMonths = this.getAvailableMonths();
    
    content.innerHTML = `
      <div class="bc-month-grid">
        ${months.map((m, i) => {
          const monthNum = i + 1;
          const monthStr = `${this.selectedYear || new Date().getFullYear()}-${monthNum.toString().padStart(2, '0')}`;
          const isAvailable = availableMonths.includes(monthNum);
          const isStart = this.rangeStart === monthNum;
          const isEnd = this.rangeEnd === monthNum;
          const isInRange = this.isMonthInRange(monthNum);
          
          let className = `bc-month-cell`;
          if (!isAvailable) className += ' bc-disabled';
          else if (isStart) className += ' bc-range-start';
          else if (isEnd) className += ' bc-range-end';
          else if (isInRange) className += ' bc-range-middle';
          
          return `<div class="${className}" data-range-month="${monthNum}" ${!isAvailable ? 'data-disabled="true"' : ''}>${m}</div>`;
        }).join("")}
      </div>
      <div class="bc-range-actions" style="margin-top: 12px; display: flex; gap: 8px; justify-content: center;">
        <button type="button" class="bc-close-btn" style="padding: 6px 12px; background: #f0f0f0; border: 1px solid #ccc; border-radius: 4px; cursor: pointer; font-size: 12px;">Close</button>
        ${this.rangeStart && !this.rangeEnd ? '<button type="button" class="bc-complete-btn" style="padding: 6px 12px; background: #0072CE; color: white; border: 1px solid #0072CE; border-radius: 4px; cursor: pointer; font-size: 12px;">Complete Range</button>' : ''}
      </div>
    `;

    // Use event delegation for more reliable event handling
    const rangeGrid = content.querySelector(".bc-month-grid");
    if (rangeGrid) {
      // Remove any existing event listeners by cloning the element
      const newGrid = rangeGrid.cloneNode(true);
      rangeGrid.parentNode.replaceChild(newGrid, rangeGrid);
      
      // Create a bound event handler
      this.rangeClickHandler = (e) => {
        e.preventDefault();
        e.stopPropagation();
        
        const cell = e.target.closest('.bc-month-cell');
        if (!cell || cell.dataset.disabled) {
          return;
        }
        
        const month = parseInt(cell.dataset.rangeMonth);
        if (!isNaN(month)) {
          this.handleRangeMonthSelection(month);
        }
      };
      
      // Add the event listener to the grid container
      newGrid.addEventListener("click", this.rangeClickHandler);
    }

    // Add close button functionality
    const closeBtn = content.querySelector(".bc-close-btn");
    if (closeBtn) {
      closeBtn.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        this.hidePicker();
      });
    }

    // Add complete button functionality
    const completeBtn = content.querySelector(".bc-complete-btn");
    if (completeBtn) {
      completeBtn.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        // Complete the range by setting end to the same as start
        this.rangeEnd = this.rangeStart;
        this.selectedRange = {
          start: `${this.selectedYear || new Date().getFullYear()}-${this.rangeStart.toString().padStart(2, '0')}`,
          end: `${this.selectedYear || new Date().getFullYear()}-${this.rangeEnd.toString().padStart(2, '0')}`
        };
        this.hidePicker();
        this.triggerCallback({ 
          range: { 
            start: this.selectedRange.start, 
            end: this.selectedRange.end 
          }
        });
      });
    }

    this.updateRangeInfo();
  }

  getAvailableMonths() {
    // If no data is available yet, return all months (1-12) to allow selection
    if (!this.data || this.data.length === 0) {
      return [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12];
    }
    
    try {
      const year = this.selectedYear || new Date().getFullYear();
      const availableMonths = [...new Set(
        this.data.filter(row => {
          // Add safety checks for data format
          if (!row || !row.month || typeof row.month !== 'string') {
            return false;
          }
          return row.month.startsWith(year.toString());
        }).map(row => {
          try {
            return parseInt(row.month.split("-")[1]);
          } catch (error) {
            console.warn('Error parsing month from data:', row.month, error);
            return null;
          }
        }).filter(month => month !== null)
      )].sort();
      
      // If no months found for the year, return all months to allow selection
      return availableMonths.length > 0 ? availableMonths : [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12];
    } catch (error) {
      console.error('Error in getAvailableMonths:', error);
      // Return all months as fallback
      return [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12];
    }
  }

  isMonthInRange(month) {
    if (!this.rangeStart || !this.rangeEnd) return false;
    return month >= this.rangeStart && month <= this.rangeEnd;
  }

  handleMonthSelection(month) {
    // Check current view instead of options.range
    if (this.currentView === "month") {
      // Single month selection mode
      this.selectedMonth = month;
      // Ensure selectedYear is set for proper period tracking
      if (!this.selectedYear) {
        this.selectedYear = new Date().getFullYear();
      }
      this.updateLabel();
      this.hidePicker();
      this.triggerCallback({ month: `${this.selectedYear}-${month.toString().padStart(2, '0')}`, year: this.selectedYear });
      return;
    } else if (this.currentView === "range") {
      // Range mode - handled by handleRangeMonthSelection
      this.handleRangeMonthSelection(month);
    }
    // Year view doesn't handle month selection
  }

  handleRangeMonthSelection(month) {
    if (!this.rangeStart) {
      // First selection - set start
      this.rangeStart = month;
      this.rangeEnd = null;
    } else if (!this.rangeEnd) {
      // Second selection - set end
      if (month < this.rangeStart) {
        this.rangeEnd = this.rangeStart;
        this.rangeStart = month;
      } else {
        this.rangeEnd = month;
      }
      
      // Update for compatibility with existing code
      this.selectedRange = {
        start: `${this.selectedYear || new Date().getFullYear()}-${this.rangeStart.toString().padStart(2, '0')}`,
        end: `${this.selectedYear || new Date().getFullYear()}-${this.rangeEnd.toString().padStart(2, '0')}`
      };
      
      // Show completion feedback
      this.showRangeCompletion();
      
      // Close after delay
      setTimeout(() => {
        this.hidePicker();
        this.triggerCallback({ 
          range: { 
            start: this.selectedRange.start, 
            end: this.selectedRange.end 
          }
        });
      }, this.options.autoCloseDelay);
    } else {
      // Reset and start new selection
      this.rangeStart = month;
      this.rangeEnd = null;
      this.selectedRange = { start: null, end: null };
    }
    
    this.renderRangeView(this.picker.querySelector(".bc-content"));
    this.updateLabel();
  }

  showRangeCompletion() {
    const rangeInfo = this.picker.querySelector(".bc-range-info");
    if (rangeInfo) {
      const startDate = this.formatMonthDisplay(this.selectedRange.start);
      const endDate = this.formatMonthDisplay(this.selectedRange.end);
      rangeInfo.innerHTML = `<div class="bc-range-selected" style="background: #0072CE; color: white; padding: 8px; border-radius: 4px; animation: bc-pulse 0.5s;">Range Complete: ${startDate} to ${endDate}</div>`;
    }
  }

  formatMonthDisplay(monthStr) {
    const [y, m] = monthStr.split("-");
    const monthNames = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
    return monthNames[parseInt(m)-1] + " " + y;
  }

  handleYearSelection(year) {
    this.selectedYear = year;
    this.updateLabel();
    this.hidePicker();
    this.triggerCallback({ month: null, year: year });
  }

  updateLabel() {
    if (!this.label) {
      return;
    }
    
    if (this.options.range && this.selectedRange && this.selectedRange.start && this.selectedRange.end) {
      const startDate = this.formatMonthDisplay(this.selectedRange.start);
      const endDate = this.formatMonthDisplay(this.selectedRange.end);
      this.label.textContent = `${startDate} - ${endDate}`;
    } else if (this.options.range && this.selectedRange && this.selectedRange.start) {
      const startDate = this.formatMonthDisplay(`${this.selectedYear || new Date().getFullYear()}-${this.selectedRange.start.split('-')[1]}`);
      this.label.textContent = `${startDate} - Select End`;
    } else if (this.selectedMonth) {
      // Single month selection - this is the key fix
      const year = this.selectedYear || new Date().getFullYear();
      const monthName = new Date(year, this.selectedMonth - 1).toLocaleString("default", { month: "short" });
      this.label.textContent = `${monthName} ${year}`;
    } else if (this.selectedYear) {
      this.label.textContent = `${this.selectedYear} (Year)`;
    } else {
      this.label.textContent = "Select Period";
    }
  }

  updateRangeInfo() {
    const rangeInfo = this.picker.querySelector(".bc-range-info");
    if (!rangeInfo) return;
    
    if (this.selectedRange && this.selectedRange.start && this.selectedRange.end) {
      const startDate = this.formatMonthDisplay(`${this.selectedYear || new Date().getFullYear()}-${this.selectedRange.start.split('-')[1]}`);
      const endDate = this.formatMonthDisplay(`${this.selectedYear || new Date().getFullYear()}-${this.selectedRange.end.split('-')[1]}`);
      rangeInfo.innerHTML = `<div class="bc-range-selected">Selected: ${startDate} to ${endDate}</div>`;
    } else if (this.selectedRange && this.selectedRange.start) {
      const startDate = this.formatMonthDisplay(`${this.selectedYear || new Date().getFullYear()}-${this.selectedRange.start.split('-')[1]}`);
      rangeInfo.innerHTML = `<div class="bc-range-selecting">Start: ${startDate} - Select end month</div>`;
    } else {
      rangeInfo.innerHTML = `<div class="bc-range-prompt">Select start month</div>`;
    }
  }

  triggerCallback(period) {
    if (this.options.onPeriodChange) {
      try {
        this.options.onPeriodChange(period);
      } catch (error) {
        console.error('Error in callback:', error);
      }
    }
  }

  // Compatibility methods with existing code
  getSelectedPeriod() {
    if (this.options.range && this.selectedRange.start && this.selectedRange.end) {
      return {
        range: this.selectedRange
      };
    } else if (this.selectedMonth) {
      // If we have a selected month, ensure we have a year
      const year = this.selectedYear || new Date().getFullYear();
      return {
        month: `${year}-${this.selectedMonth.toString().padStart(2, '0')}`,
        year: year
      };
    } else if (this.selectedYear) {
      return {
        year: this.selectedYear
      };
    }
    return null;
  }

  getSelectedRange() {
    return this.selectedRange.start && this.selectedRange.end ? this.selectedRange : null;
  }



  setData(data) {
    this.data = data || [];
    
    // Only render if picker is initialized
    if (this.picker) {
      this.renderPicker();
      this.hidePicker();
    } else {
      // If picker isn't ready yet, queue the render for after init
      this.pendingData = data;
    }
  }

  setSelectedMonth(monthStr) {
    if (!monthStr) return;
    
    const [year, month] = monthStr.split('-');
    this.selectedYear = parseInt(year);
    this.selectedMonth = parseInt(month);
    this.updateLabel();
    
    // Trigger callback to notify of the change
    this.triggerCallback({ 
      month: monthStr, 
      year: this.selectedYear 
    });
  }

  reset() {
    this.selectedMonth = null;
    this.selectedYear = null;
    this.rangeStart = null;
    this.rangeEnd = null;
    this.selectedRange = { start: null, end: null };
    this.updateLabel();
    this.triggerCallback({ month: null, year: null, range: null });
  }

  resetRange() {
    this.rangeStart = null;
    this.rangeEnd = null;
    this.selectedRange = { start: null, end: null };
    this.updateLabel();
    this.updateRangeInfo();
  }

  destroy() {
    this.isDestroyed = true;
    if (this.picker) {
      this.picker.innerHTML = "";
      this.hidePicker();
    }
    // Don't overwrite the global BestCalendar class
    // window.BestCalendar = undefined;
  }
}

// Global export
window.BestCalendar = BestCalendar;

} // End of duplicate prevention block