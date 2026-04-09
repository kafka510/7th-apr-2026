/**
 * BestCalendar Component
 * A simple calendar component for month/year selection
 */
class BestCalendar {
    constructor(options) {
        this.triggerId = options.triggerId || 'monthMatrixTrigger';
        this.pickerId = options.pickerId || 'monthMatrixPicker';
        this.labelId = options.labelId || 'selectedMonthLabel';
        this.onPeriodChange = options.onPeriodChange || function() {};
        
        this.trigger = document.getElementById(this.triggerId);
        this.picker = document.getElementById(this.pickerId);
        this.label = document.getElementById(this.labelId);
        
        this.selectedMonth = null;
        this.selectedYear = null;
        this.data = [];
        
        this.init();
    }
    
    init() {
        if (this.trigger) {
            this.trigger.addEventListener('click', () => {
                this.togglePicker();
            });
        }
        
        // Close picker when clicking outside
        document.addEventListener('click', (e) => {
            if (!this.picker?.contains(e.target) && !this.trigger?.contains(e.target)) {
                this.hidePicker();
            }
        });
    }
    
      setData(data) {
    this.data = data || [];
  }
    
    setSelectedMonth(month) {
        this.selectedMonth = month;
        if (this.label) {
            if (month) {
                const [year, monthNum] = month.split('-');
                const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
                const monthName = monthNames[parseInt(monthNum) - 1];
                this.label.textContent = `${monthName} ${year}`;
            } else {
                this.label.textContent = 'Select Period';
            }
        }

    }

    setSelectedYear(year) {
        this.selectedYear = year;
    }
    
    clearSelection() {
        this.selectedMonth = null;
        this.selectedYear = null;
        if (this.label) {
            this.label.textContent = 'Select Period';
        }
    }
    
    getSelectedPeriod() {
        return {
            month: this.selectedMonth,
            year: this.selectedYear
        };
    }
    
    getOriginalMonth() {
        // For compatibility with the HTML code
        return this.selectedMonth;
    }
    
    togglePicker() {
        if (this.picker) {
            if (this.picker.style.display === 'none' || !this.picker.style.display) {
                this.showPicker();
            } else {
                this.hidePicker();
            }
        }
    }
    
    showPicker() {
        if (this.picker) {
            this.picker.style.display = 'block';
            this.renderPicker();
        }
    }
    
    hidePicker() {
        if (this.picker) {
            this.picker.style.display = 'none';
        }
    }
    
    renderPicker() {
        if (!this.picker) return;
        
        // Create a simple month picker
        const months = [
            'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
            'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
        ];
        
        const currentYear = new Date().getFullYear();
        const years = [currentYear - 1, currentYear, currentYear + 1];
        
        let html = '<div class="calendar-picker">';
        html += '<div class="calendar-header">';
        html += '<button class="calendar-nav" onclick="this.parentElement.parentElement.querySelector(\'.year-select\').selectedIndex--">‹</button>';
        html += '<select class="year-select">';
        years.forEach(year => {
            html += `<option value="${year}" ${year === currentYear ? 'selected' : ''}>${year}</option>`;
        });
        html += '</select>';
        html += '<button class="calendar-nav" onclick="this.parentElement.parentElement.querySelector(\'.year-select\').selectedIndex++">›</button>';
        html += '</div>';
        html += '<div class="calendar-grid">';
        
        months.forEach((month, index) => {
            const monthNum = String(index + 1).padStart(2, '0');
            const year = currentYear;
            const monthKey = `${year}-${monthNum}`;
            const hasData = this.data.some(item => item.month === monthKey);
            const isSelected = this.selectedMonth === monthKey;
            
            let className = 'calendar-month';
            if (hasData) className += ' has-data';
            if (isSelected) className += ' selected';
            
            html += `<div class="${className}" data-month="${monthKey}">${month}</div>`;
        });
        
        html += '</div></div>';
        
        this.picker.innerHTML = html;
        
        // Add event listeners
        const monthElements = this.picker.querySelectorAll('.calendar-month');
        monthElements.forEach(el => {
            el.addEventListener('click', () => {
                const month = el.dataset.month;
                this.setSelectedMonth(month);
                this.hidePicker();
                this.onPeriodChange({ month, year: parseInt(month.split('-')[0]) });
            });
        });
        
        const yearSelect = this.picker.querySelector('.year-select');
        if (yearSelect) {
            yearSelect.addEventListener('change', () => {
                const selectedYear = parseInt(yearSelect.value);
                this.updateMonthsForYear(selectedYear);
            });
        }
    }
    
    updateMonthsForYear(year) {
        const monthElements = this.picker.querySelectorAll('.calendar-month');
        monthElements.forEach((el, index) => {
            const monthNum = String(index + 1).padStart(2, '0');
            const monthKey = `${year}-${monthNum}`;
            const hasData = this.data.some(item => item.month === monthKey);
            const isSelected = this.selectedMonth === monthKey;
            
            el.dataset.month = monthKey;
            
            let className = 'calendar-month';
            if (hasData) className += ' has-data';
            if (isSelected) className += ' selected';
            
            el.className = className;
        });
    }
}

// Add some basic styles
const style = document.createElement('style');
style.textContent = `
    .calendar-picker {
        position: absolute;
        background: white;
        border: 1px solid #b3d7f2;
        border-radius: 8px;
        box-shadow: 0 4px 16px rgba(0,0,0,0.1);
        z-index: 1000;
        padding: 12px;
        min-width: 240px;
        font-family: 'Inter', Arial, sans-serif;
    }
    
    .calendar-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 12px;
        padding-bottom: 8px;
        border-bottom: 1px solid #e0e0e0;
    }
    
    .calendar-nav {
        background: #f8fbff;
        border: 1px solid #b3d7f2;
        border-radius: 4px;
        cursor: pointer;
        padding: 6px 10px;
        font-size: 14px;
        color: #0072CE;
        transition: all 0.2s ease;
    }
    
    .calendar-nav:hover {
        background: #e6f1fc;
        border-color: #0072CE;
    }
    
    .year-select {
        border: 1px solid #b3d7f2;
        padding: 6px 10px;
        border-radius: 4px;
        background: #f8fbff;
        color: #0072CE;
        font-size: 14px;
        font-weight: 500;
        outline: none;
    }
    
    .year-select:focus {
        border-color: #0072CE;
        box-shadow: 0 0 0 2px rgba(0, 114, 206, 0.2);
    }
    
    .calendar-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 6px;
    }
    
    .calendar-month {
        padding: 8px 4px;
        text-align: center;
        cursor: pointer;
        border-radius: 4px;
        border: 1px solid #e0e0e0;
        background: #f8fbff;
        font-size: 12px;
        font-weight: 500;
        color: #333;
        transition: all 0.2s ease;
        min-height: 32px;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    
    .calendar-month:hover {
        background: #e6f1fc;
        border-color: #0072CE;
        color: #0072CE;
    }
    
    .calendar-month.has-data {
        background: #e3f2fd;
        border-color: #2196f3;
        color: #1976d2;
        font-weight: 600;
    }
    
    .calendar-month.has-data:hover {
        background: #bbdefb;
        border-color: #1976d2;
    }
    
    .calendar-month.selected {
        background: #0072CE;
        border-color: #0072CE;
        color: white;
        font-weight: 600;
    }
    
    .calendar-month.selected:hover {
        background: #0056a3;
        border-color: #0056a3;
    }
    
    /* Responsive design */
    @media (max-width: 768px) {
        .calendar-picker {
            min-width: 200px;
            padding: 8px;
        }
        
        .calendar-grid {
            grid-template-columns: repeat(3, 1fr);
            gap: 4px;
        }
        
        .calendar-month {
            padding: 6px 2px;
            font-size: 11px;
            min-height: 28px;
        }
        
        .calendar-nav {
            padding: 4px 8px;
            font-size: 12px;
        }
        
        .year-select {
            padding: 4px 8px;
            font-size: 12px;
        }
    }
    
    @media (max-width: 480px) {
        .calendar-picker {
            min-width: 180px;
            padding: 6px;
        }
        
        .calendar-grid {
            grid-template-columns: repeat(3, 1fr);
            gap: 3px;
        }
        
        .calendar-month {
            padding: 4px 1px;
            font-size: 10px;
            min-height: 24px;
        }
    }
`;
document.head.appendChild(style);

// Make BestCalendar available globally
window.BestCalendar = BestCalendar; 