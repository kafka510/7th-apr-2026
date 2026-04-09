import * as React from 'react';
import * as Popover from '@radix-ui/react-popover';
import * as Checkbox from '@radix-ui/react-checkbox';
import { Check, ChevronDown } from 'lucide-react';
import { Label } from './label';
import { cn } from '../../lib/utils';
import { useTheme } from '../../contexts/ThemeContext';

export interface FormMultiSelectOption {
  value: string;
  label: string;
}

export interface FormMultiSelectProps {
  label: string;
  options: FormMultiSelectOption[];
  selected: string[];
  onChange: (values: string[]) => void;
  placeholder?: string;
  disabled?: boolean;
  required?: boolean;
  error?: string;
  singleSelect?: boolean;
  className?: string;
}

export const FormMultiSelect = React.forwardRef<HTMLDivElement, FormMultiSelectProps>(
  (
    {
      label,
      options,
      selected,
      onChange,
      placeholder = 'Select options',
      disabled = false,
      required = false,
      error,
      singleSelect = false,
      className,
    },
    ref
  ) => {
    const { theme } = useTheme();
    const isDark = theme === 'dark';
    const [open, setOpen] = React.useState(false);
    const [search, setSearch] = React.useState('');

    const buttonBg = isDark ? 'rgba(15, 23, 42, 0.8)' : '#ffffff';
    const buttonBorder = isDark ? 'rgba(51, 65, 85, 0.7)' : 'rgba(203, 213, 225, 0.8)';
    const buttonText = isDark ? '#e2e8f0' : '#1a1a1a';
    const buttonHoverBorder = isDark ? '#3b82f6' : '#0072ce';
    const errorBorder = isDark ? 'rgba(239, 68, 68, 0.5)' : '#f87171';
    const errorTextColor = isDark ? '#fca5a5' : '#dc2626';
    const dropdownBg = isDark ? 'rgba(15, 23, 42, 0.95)' : '#ffffff';
    const dropdownBorder = isDark ? 'rgba(51, 65, 85, 0.8)' : 'rgba(203, 213, 225, 0.8)';
    const optionText = isDark ? '#e2e8f0' : '#1a1a1a';
    const optionSelectedBg = isDark ? 'rgba(59, 130, 246, 0.2)' : 'rgba(59, 130, 246, 0.1)';
    const optionHoverBg = isDark ? 'rgba(30, 41, 59, 0.7)' : 'rgba(241, 245, 249, 0.9)';

    const filteredOptions = React.useMemo(() => {
      if (!search) return options;
      const lowerSearch = search.toLowerCase();
      return options.filter((option) => option.label.toLowerCase().includes(lowerSearch));
    }, [options, search]);

    const summary = React.useMemo(() => {
      if (selected.length === 0) return placeholder;
      if (singleSelect) {
        const opt = options.find((o) => o.value === selected[0]);
        return opt ? opt.label : selected[0];
      }
      if (selected.length === options.length) return 'All selected';
      if (selected.length <= 2) {
        return selected
          .map((val) => {
            const opt = options.find((o) => o.value === val);
            return opt ? opt.label : val;
          })
          .join(', ');
      }
      return `${selected.length} selected`;
    }, [placeholder, selected, options, singleSelect]);

    const toggleOption = (value: string) => {
      if (singleSelect) {
        if (selected.includes(value)) {
          onChange([]);
        } else {
          onChange([value]);
        }
        setOpen(false);
      } else {
        if (selected.includes(value)) {
          onChange(selected.filter((item) => item !== value));
        } else {
          onChange([...selected, value]);
        }
      }
    };

    const handleSelectAll = () => {
      if (selected.length === options.length) {
        onChange([]);
      } else {
        onChange(options.map((opt) => opt.value));
      }
    };

    const handleClear = () => {
      onChange([]);
      setSearch('');
    };

    return (
      <div ref={ref} className={cn('flex flex-col gap-1', className)}>
        <Label>
          {label} {required && <span style={{ color: errorTextColor }}>*</span>}
        </Label>
        <Popover.Root open={open} onOpenChange={setOpen}>
          <Popover.Trigger asChild>
            <button
              type="button"
              disabled={disabled}
              className="flex h-9 w-full items-center justify-between rounded-lg border px-2 py-1.5 text-left text-sm shadow-sm transition disabled:cursor-not-allowed disabled:opacity-50"
              style={{
                backgroundColor: buttonBg,
                borderColor: error ? errorBorder : buttonBorder,
                color: buttonText,
                boxShadow: isDark ? 'inset 0 2px 4px rgba(0, 0, 0, 0.3)' : 'inset 0 1px 2px rgba(0, 0, 0, 0.05)',
              }}
              onMouseEnter={(e) => {
                if (!disabled && !error) {
                  e.currentTarget.style.borderColor = buttonHoverBorder;
                }
              }}
              onMouseLeave={(e) => {
                if (!disabled && !error) {
                  e.currentTarget.style.borderColor = buttonBorder;
                }
              }}
            >
              <span className="truncate">{summary}</span>
              <ChevronDown className="size-4 opacity-50" style={{ color: isDark ? '#94a3b8' : '#64748b' }} />
            </button>
          </Popover.Trigger>
          <Popover.Portal>
            <Popover.Content
              className="z-50 w-[var(--radix-popover-trigger-width)] rounded-lg border shadow-xl"
              style={{
                backgroundColor: dropdownBg,
                borderColor: dropdownBorder,
                boxShadow: isDark 
                  ? '0 20px 25px -5px rgba(0, 0, 0, 0.5)' 
                  : '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
                maxHeight: '300px',
                display: 'flex',
                flexDirection: 'column',
              }}
              sideOffset={4}
            >
              <div className="flex items-center gap-2 border-b px-3 py-2" style={{ borderColor: dropdownBorder }}>
                <input
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search…"
                  className="flex-1 rounded border px-2 py-1 text-xs focus:outline-none focus:ring-1"
                  style={{
                    backgroundColor: isDark ? 'rgba(15, 23, 42, 0.8)' : '#ffffff',
                    borderColor: isDark ? 'rgba(51, 65, 85, 0.7)' : 'rgba(203, 213, 225, 0.8)',
                    color: isDark ? '#e2e8f0' : '#1a1a1a',
                  }}
                />
                {!singleSelect && (
                  <>
                    <button
                      type="button"
                      onClick={handleSelectAll}
                      className="whitespace-nowrap rounded border px-2 py-1 text-xs font-semibold transition"
                      style={{
                        backgroundColor: buttonBg,
                        borderColor: buttonBorder,
                        color: buttonText,
                      }}
                    >
                      {selected.length === options.length ? 'Clear All' : 'Select All'}
                    </button>
                    {selected.length > 0 && (
                      <button
                        type="button"
                        onClick={handleClear}
                        className="whitespace-nowrap rounded border border-transparent px-2 py-1 text-xs font-semibold transition"
                        style={{ color: isDark ? '#94a3b8' : '#64748b' }}
                      >
                        Reset
                      </button>
                    )}
                  </>
                )}
              </div>
              <div className="max-h-[250px] overflow-y-auto p-1">
                {filteredOptions.length === 0 ? (
                  <div className="px-3 py-2 text-xs" style={{ color: isDark ? '#94a3b8' : '#64748b' }}>
                    No matches
                  </div>
                ) : (
                  filteredOptions.map((option) => {
                    const isSelected = selected.includes(option.value);
                    return (
                      <label
                        key={option.value}
                        className="flex cursor-pointer items-center gap-2 rounded px-2 py-1.5 text-sm transition"
                        style={{
                          backgroundColor: isSelected ? optionSelectedBg : 'transparent',
                          color: optionText,
                        }}
                        onMouseEnter={(e) => {
                          if (!isSelected) {
                            e.currentTarget.style.backgroundColor = optionHoverBg;
                          }
                        }}
                        onMouseLeave={(e) => {
                          if (!isSelected) {
                            e.currentTarget.style.backgroundColor = 'transparent';
                          }
                        }}
                      >
                        <Checkbox.Root
                          checked={isSelected}
                          onCheckedChange={() => toggleOption(option.value)}
                          className="flex size-4 items-center justify-center rounded border"
                          style={{
                            borderColor: isDark ? 'rgba(71, 85, 105, 0.6)' : 'rgba(203, 213, 225, 0.7)',
                            backgroundColor: isSelected ? (isDark ? '#3b82f6' : '#0072ce') : 'transparent',
                          }}
                        >
                          <Checkbox.Indicator>
                            <Check className="size-3 text-white" />
                          </Checkbox.Indicator>
                        </Checkbox.Root>
                        <span className="flex-1">{option.label}</span>
                      </label>
                    );
                  })
                )}
              </div>
            </Popover.Content>
          </Popover.Portal>
        </Popover.Root>
        {error && (
          <p className="mt-0.5 text-xs" style={{ color: errorTextColor }}>
            {error}
          </p>
        )}
      </div>
    );
  }
);
FormMultiSelect.displayName = 'FormMultiSelect';

