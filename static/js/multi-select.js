/**
 * Multi-Select Component - Reusable dropdown with multiple selection and checkboxes
 */
class MultiSelect {
  constructor(triggerId, dropdownId, placeholderId, selectedItemsId, onChange = null) {
    this.trigger = document.getElementById(triggerId);
    this.dropdown = document.getElementById(dropdownId);
    this.placeholder = document.getElementById(placeholderId);
    this.selectedItemsContainer = selectedItemsId ? document.getElementById(selectedItemsId) : null;
    this.options = [];
    this.selectedValues = [];
    this.onChange = onChange;
    this.lastToggleTimeMs = 0;
    this.ignoreUntilMs = 0;
    this._initialized = false;
    this.onChangeTimer = null; // Timer for debouncing onChange calls
    
    if (!this.trigger || !this.dropdown || !this.placeholder) {
      return;
    }
    
    this.init();
  }
  
  /**
   * Initialize the multi-select component
   */
  init() {
    if (this._initialized) return;
    this._initialized = true;
    this.trigger.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      this.toggleDropdown();
    });
    
    // Prevent dropdown clicks from bubbling up
    this.dropdown.addEventListener('click', (e) => {
      e.stopPropagation();
    });
    
    // Close dropdown when clicking outside (but not on other multi-select elements)
    this.handleOutsideClick = (e) => {
      // Only act if currently open
      if (!this.isOpen()) return;
      const now = (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now();
      if (now < this.ignoreUntilMs) return;
      // Check if click is on this specific multi-select
      const isOnThis = this.trigger.contains(e.target) || this.dropdown.contains(e.target);
      if (!isOnThis) {
        this.closeDropdown();
      }
    };
    
    document.addEventListener('mousedown', this.handleOutsideClick, true);

    // Close dropdown on escape key
    this.handleKeydown = (e) => {
      if (e.key === 'Escape' && this.isOpen()) {
        this.closeDropdown();
      }
    };
    
    document.addEventListener('keydown', this.handleKeydown);
  }
  
  /**
   * Set options for the dropdown
   */
  setOptions(options) {
    this.options = options;
    this.renderOptions();
  }
  
  /**
   * Render the dropdown options with checkboxes
   */
  renderOptions() {
    this.dropdown.innerHTML = '';
    
    if (this.options.length === 0) {
      const noOptionsDiv = document.createElement('div');
      noOptionsDiv.className = 'multi-select-option disabled';
      noOptionsDiv.textContent = 'No options available';
      this.dropdown.appendChild(noOptionsDiv);
      return;
    }
    
    // Add "Select All" option if there are multiple options
    if (this.options.length > 1) {
      const selectAllDiv = document.createElement('div');
      selectAllDiv.className = 'multi-select-option select-all-option';
      
      const isAllSelected = this.selectedValues.length === this.options.length;
      const isPartiallySelected = this.selectedValues.length > 0 && this.selectedValues.length < this.options.length;
      
      selectAllDiv.innerHTML = `
        <div class="checkbox-container">
          <input type="checkbox" id="select-all-${this.dropdown.id}" ${isAllSelected ? 'checked' : ''} ${isPartiallySelected ? 'data-indeterminate="true"' : ''}>
          <label for="select-all-${this.dropdown.id}" class="checkbox-label">
            <span class="checkbox-custom"></span>
            <span class="checkbox-text">Select All</span>
          </label>
        </div>
      `;
      
      const selectAllCheckbox = selectAllDiv.querySelector('input[type="checkbox"]');
      
      // Set indeterminate state if needed
      if (isPartiallySelected) {
        selectAllCheckbox.indeterminate = true;
      }
      
      selectAllCheckbox.addEventListener('change', (e) => {
        e.stopPropagation();
        if (e.target.checked) {
          this.selectAll();
        } else {
          this.clearSelection();
        }
        
        // Auto-close dropdown after select all/clear
        setTimeout(() => {
          this.closeDropdown();
        }, 150);
      });
      
      this.dropdown.appendChild(selectAllDiv);
      
      // Add separator
      const separator = document.createElement('div');
      separator.className = 'multi-select-separator';
      this.dropdown.appendChild(separator);
    }
    
    this.options.forEach(option => {
      const div = document.createElement('div');
      div.className = 'multi-select-option';
      div.dataset.value = option.value;
      
      const isSelected = this.selectedValues.includes(option.value);
      const isMaxReached = this.dropdown.id === 'advancedParameterFilterDropdown' && 
                          this.selectedValues.length >= 4 && !isSelected;
      
      if (isMaxReached) {
        div.classList.add('disabled');
        div.style.opacity = '0.5';
        div.style.cursor = 'not-allowed';
      }
      
      div.innerHTML = `
        <div class="checkbox-container">
          <input type="checkbox" id="option-${option.value}-${this.dropdown.id}" ${isSelected ? 'checked' : ''} ${isMaxReached ? 'disabled' : ''}>
          <label for="option-${option.value}-${this.dropdown.id}" class="checkbox-label">
            <span class="checkbox-custom"></span>
            <span class="checkbox-text">${option.label}</span>
          </label>
        </div>
      `;
      
      const checkbox = div.querySelector('input[type="checkbox"]');
      if (!isMaxReached) {
        checkbox.addEventListener('change', (e) => {
          e.stopPropagation();
          this.toggleOption(option.value);
        });
        
        // Also allow clicking on the option div to toggle
        div.addEventListener('click', (e) => {
          if (e.target.type !== 'checkbox') {
            e.preventDefault();
            this.toggleOption(option.value);
          }
        });
      }
      
      this.dropdown.appendChild(div);
    });
  }
  
  /**
   * Select all options
   */
  selectAll() {
    // Check if this is the parameters dropdown and limit to 4 selections
    if (this.dropdown.id === 'advancedParameterFilterDropdown') {
      // Only select the first 4 options
      this.selectedValues = this.options.slice(0, 4).map(opt => opt.value);
      this.showMaxSelectionNotification();
    } else {
      this.selectedValues = this.options.map(opt => opt.value);
    }
    
    this.updateDisplay();
    this.renderOptions();
    
    if (this.onChange) {
      this.onChange(this.selectedValues);
    }
  }
  
  /**
   * Toggle selection of an option
   */
  toggleOption(value) {
    const index = this.selectedValues.indexOf(value);
    if (index > -1) {
      // Remove the option if it's already selected
      this.selectedValues.splice(index, 1);
    } else {
      // Check if this is the parameters dropdown and enforce max limit
      if (this.dropdown.id === 'advancedParameterFilterDropdown' && this.selectedValues.length >= 4) {
        // Show a notification that maximum 4 parameters can be selected
        this.showMaxSelectionNotification();
        return; // Don't add the option
      }
      this.selectedValues.push(value);
    }
    
    // Update display without full re-render for better performance and to avoid click order issues
    this.updateDisplay();
    
    // Only update the specific checkbox state instead of re-rendering everything
    const optionDiv = this.dropdown.querySelector(`.multi-select-option[data-value="${value}"]`);
    if (optionDiv) {
      const checkbox = optionDiv.querySelector('input[type="checkbox"]');
      if (checkbox) {
        checkbox.checked = index === -1; // true if adding, false if removing
        if (index === -1) {
          optionDiv.classList.add('selected');
        } else {
          optionDiv.classList.remove('selected');
        }
      }
    }
    
    // Update Select All checkbox state if it exists
    const selectAllCheckbox = this.dropdown.querySelector(`input[id^="select-all-"]`);
    if (selectAllCheckbox) {
      const isAllSelected = this.selectedValues.length === this.options.length;
      const isPartiallySelected = this.selectedValues.length > 0 && this.selectedValues.length < this.options.length;
      selectAllCheckbox.checked = isAllSelected;
      selectAllCheckbox.indeterminate = isPartiallySelected;
    }
    
    // Re-render when reaching OR dropping below the limit for parameters (to enable/disable other options)
    // This ensures options are re-enabled when dropping from 4 to 3 selections
    if (this.dropdown.id === 'advancedParameterFilterDropdown') {
      const wasAtLimit = index > -1 && (this.selectedValues.length + 1) >= 4; // Was at limit before removal
      const isAtLimit = this.selectedValues.length >= 4; // Is at limit after toggle
      
      // Re-render if we're at the limit OR if we just dropped below it
      if (isAtLimit || wasAtLimit) {
        this.renderOptions();
      }
    }
    
    // Use setTimeout to ensure state is fully updated before triggering onChange
    // This prevents issues when clicking items quickly in sequence
    if (this.onChange) {
      // Clear any pending onChange calls to prevent race conditions
      if (this.onChangeTimer) {
        clearTimeout(this.onChangeTimer);
      }
      this.onChangeTimer = setTimeout(() => {
        // Make a copy of selectedValues to ensure we're passing the current state
        const currentSelection = [...this.selectedValues];
        this.onChange(currentSelection);
      }, 0); // Use 0ms timeout to push to next event loop tick, ensuring state is consistent
    }
  }
  
  /**
   * Show notification when maximum selection limit is reached
   */
  showMaxSelectionNotification() {
    // Create a temporary notification element
    const notification = document.createElement('div');
    notification.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      background: #ff6b6b;
      color: white;
      padding: 12px 20px;
      border-radius: 8px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.15);
      font-family: 'Inter', 'Segoe UI', Arial, sans-serif;
      font-size: 14px;
      font-weight: 500;
      z-index: 10000;
      opacity: 0;
      transform: translateX(100%);
      transition: all 0.3s ease;
    `;
    notification.innerHTML = `
      <i class="fas fa-exclamation-triangle" style="margin-right: 8px;"></i>
      Maximum 4 parameters can be selected
    `;
    
    document.body.appendChild(notification);
    
    // Animate in
    setTimeout(() => {
      notification.style.opacity = '1';
      notification.style.transform = 'translateX(0)';
    }, 100);
    
    // Remove after 3 seconds
    setTimeout(() => {
      notification.style.opacity = '0';
      notification.style.transform = 'translateX(100%)';
      setTimeout(() => {
        if (notification.parentNode) {
          notification.parentNode.removeChild(notification);
        }
      }, 300);
    }, 3000);
  }

  /**
   * Update the display text and selected items
   */
  updateDisplay() {
    if (this.selectedValues.length === 0) {
      this.placeholder.textContent = this.placeholder.dataset.default || 'Select options';
    } else if (this.selectedValues.length === 1) {
      // Show the single selected item name
      const option = this.options.find(opt => opt.value === this.selectedValues[0]);
      this.placeholder.textContent = option ? option.label : '1 selected';
    } else {
      // Show count for multiple selections
      this.placeholder.textContent = `${this.selectedValues.length} selected`;
    }
    
    this.renderSelectedItems();
  }
  
  /**
   * Render the selected items as tags
   */
  renderSelectedItems() {
    // If no container is provided, skip rendering selected items
    const container = this.selectedItemsContainer;
    if (!container) return;
    
    const markedHidden = container.hasAttribute('data-hide');
    const inlineHidden = container.style && container.style.display === 'none';
    let computedHidden = false;
    try { computedHidden = getComputedStyle(container).display === 'none'; } catch (_) {}
    if (markedHidden || inlineHidden || computedHidden) {
      return;
    }
    this.selectedItemsContainer.innerHTML = '';
    
    this.selectedValues.forEach(value => {
      const option = this.options.find(opt => opt.value === value);
      if (option) {
        const item = document.createElement('div');
        item.className = 'selected-item';
        item.innerHTML = `${option.label} <span class="remove" data-value="${value}">×</span>`;
        
        item.querySelector('.remove').addEventListener('click', (e) => {
          e.stopPropagation();
          this.toggleOption(value);
        });
        
        this.selectedItemsContainer.appendChild(item);
      }
    });
  }
  
  /**
   * Toggle dropdown visibility
   */
  toggleDropdown() {
    const isVisible = this.isOpen();
    const now = (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now();
    if (now - this.lastToggleTimeMs < 180) {
      return;
    }
    this.lastToggleTimeMs = now;
    
    if (isVisible) {
      // Close dropdown
      this.closeDropdown();
    } else {
      // Open dropdown
      this.dropdown.style.display = 'block';
      this.trigger.classList.add('active');
      // Temporarily ignore outside click for a short time to avoid immediate close
      const now2 = (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now();
      this.ignoreUntilMs = now2 + 180;
    }
  }
  
  /**
   * Close the dropdown
   */
  closeDropdown() {
    this.dropdown.style.display = 'none';
    this.trigger.classList.remove('active');
  }
  
  /**
   * Check if dropdown is open
   */
  isOpen() {
    return this.dropdown.style.display === 'block';
  }
  
  /**
   * Get selected values
   */
  getSelectedValues() {
    return [...this.selectedValues];
  }
  
  /**
   * Set selected values
   */
  setSelectedValues(values) {
    // Check if this is the parameters dropdown and limit to 4 selections
    if (this.dropdown.id === 'advancedParameterFilterDropdown' && values.length > 4) {
      this.selectedValues = values.slice(0, 4);
      this.showMaxSelectionNotification();
    } else {
      this.selectedValues = [...values];
    }
    this.updateDisplay();
    this.renderOptions();
  }
  
  /**
   * Clear all selections
   */
  clearSelection() {
    this.selectedValues = [];
    this.updateDisplay();
    this.renderOptions();
  }
  
  /**
   * Enable/disable the component
   */
  setEnabled(enabled) {
    this.trigger.style.pointerEvents = enabled ? 'auto' : 'none';
    this.trigger.style.opacity = enabled ? '1' : '0.5';
  }
  
  /**
   * Destroy the component
   */
  destroy() {
    // Remove event listeners
    if (this.trigger) {
      this.trigger.removeEventListener('click', this.toggleDropdown);
    }
    if (this.handleOutsideClick) {
      document.removeEventListener('mousedown', this.handleOutsideClick, true);
    }
    if (this.handleKeydown) {
      document.removeEventListener('keydown', this.handleKeydown);
    }
    
    // Clear references
    this.trigger = null;
    this.dropdown = null;
    this.placeholder = null;
    this.selectedItemsContainer = null;
    this.options = [];
    this.selectedValues = [];
    this.onChange = null;
  }
}

/**
 * Multi-Select Factory - Helper for creating multiple instances
 */
class MultiSelectFactory {
  static create(triggerId, dropdownId, placeholderId, selectedItemsId, onChange = null) {
    return new MultiSelect(triggerId, dropdownId, placeholderId, selectedItemsId, onChange);
  }
  
  /**
   * Create multiple multi-select instances from configuration
   */
  static createMultiple(configs) {
    const instances = {};
    
    configs.forEach(config => {
      instances[config.name] = MultiSelectFactory.create(
        config.triggerId,
        config.dropdownId,
        config.placeholderId,
        config.selectedItemsId,
        config.onChange
      );
    });
    
    return instances;
  }
}

// Export for use in other modules
window.MultiSelect = MultiSelect;
window.MultiSelectFactory = MultiSelectFactory;
