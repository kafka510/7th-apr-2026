/**
 * Multi-Select Dropdown with Checkboxes
 * Used for hierarchical filtering (Inverters, JBs)
 */
import React, { useState, useRef, useEffect } from 'react';

interface Option {
  value: string;
  label: string;
}

interface MultiSelectDropdownProps {
  options: Option[];
  selectedValues: string[];
  onChange: (selected: string[]) => void;
  placeholder?: string;
  label: string;
  disabled?: boolean;
}

export const MultiSelectDropdown: React.FC<MultiSelectDropdownProps> = ({
  options,
  selectedValues,
  onChange,
  placeholder = '-- Select --',
  label,
  disabled = false,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleToggle = (value: string) => {
    if (selectedValues.includes(value)) {
      onChange(selectedValues.filter((v) => v !== value));
    } else {
      onChange([...selectedValues, value]);
    }
  };

  const handleSelectAll = () => {
    if (selectedValues.length === options.length) {
      onChange([]);
    } else {
      onChange(options.map((opt) => opt.value));
    }
  };

  const displayText = selectedValues.length === 0
    ? placeholder
    : selectedValues.length === options.length
    ? `All ${options.length} selected`
    : `${selectedValues.length} selected`;

  return (
    <div className="multi-select-dropdown" ref={dropdownRef}>
      <label className="fw-medium text-dark mb-1 text-sm">{label}</label>
      <div className="position-relative">
        <button
          type="button"
          className="form-select text-start"
          onClick={() => !disabled && setIsOpen(!isOpen)}
          disabled={disabled}
        >
          {displayText}
        </button>

        {isOpen && !disabled && (
          <div
            className="position-absolute w-100 rounded border bg-white shadow-lg"
            style={{ zIndex: 1000, maxHeight: '300px', overflowY: 'auto' }}
          >
            {/* Select All Option */}
            <div className="border-bottom p-2">
              <label className="d-flex align-items-center text-dark cursor-pointer">
                <input
                  type="checkbox"
                  className="form-check-input me-2"
                  checked={selectedValues.length === options.length}
                  onChange={handleSelectAll}
                />
                <strong>Select All ({options.length})</strong>
              </label>
            </div>

            {/* Individual Options */}
            {options.map((option) => (
              <div key={option.value} className="hover:bg-light p-2">
                <label className="d-flex align-items-center text-dark mb-0 cursor-pointer">
                  <input
                    type="checkbox"
                    className="form-check-input me-2"
                    checked={selectedValues.includes(option.value)}
                    onChange={() => handleToggle(option.value)}
                  />
                  <span className="text-sm">{option.label}</span>
                </label>
              </div>
            ))}

            {options.length === 0 && (
              <div className="text-muted p-3 text-center">No options available</div>
            )}
          </div>
        )}
      </div>

      {/* Selected Count */}
      {selectedValues.length > 0 && (
        <small className="text-muted">
          {selectedValues.length} of {options.length} selected
        </small>
      )}
    </div>
  );
};



