import { useEffect, useMemo, useRef, useState } from 'react';

import type { BasicOption } from '../types';

type FilterMultiSelectProps = {
  label: string;
  options: BasicOption[];
  selected: string[];
  onChange: (values: string[]) => void;
  placeholder?: string;
  disabled?: boolean;
};

export const FilterMultiSelect = ({
  label,
  options,
  selected,
  onChange,
  placeholder = 'All',
  disabled = false,
}: FilterMultiSelectProps) => {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState('');
  const containerRef = useRef<HTMLDivElement | null>(null);
  const searchInputRef = useRef<HTMLInputElement | null>(null);

  const valueToLabel = useMemo(() => {
    const map = new Map<string, string>();
    if (options && Array.isArray(options)) {
      options.forEach((option) => {
        map.set(option.value, option.label);
      });
    }
    return map;
  }, [options]);

  const filteredOptions = useMemo(() => {
    if (!options || !Array.isArray(options)) {
      return [];
    }
    if (!search.trim()) {
      return options;
    }

    const needle = search.trim().toLowerCase();
    return options.filter((option) => option.label.toLowerCase().includes(needle));
  }, [options, search]);

  const summary = useMemo(() => {
    if (selected.length === 0) {
      return placeholder;
    }
    if (selected.length <= 2) {
      return selected
        .map((value) => valueToLabel.get(value) ?? value)
        .join(', ');
    }
    return `${selected.length} selected`;
  }, [placeholder, selected, valueToLabel]);

  const toggleValue = (value: string) => {
    if (selected.includes(value)) {
      onChange(selected.filter((item) => item !== value));
    } else {
      onChange([...selected, value]);
    }
    // Auto-close dropdown after selection
    setIsOpen(false);
  };

  const handleSelectAll = () => {
    if (!options || !Array.isArray(options)) {
      return;
    }
    if (selected.length === options.length) {
      onChange([]);
    } else {
      onChange(options.map((option) => option.value));
    }
    // Auto-close dropdown after select all
    setIsOpen(false);
  };

  const handleClear = () => {
    onChange([]);
    setSearch('');
    // Auto-close dropdown after clear
    setIsOpen(false);
  };

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (!isOpen) {
        return;
      }
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    window.addEventListener('mousedown', handleClickOutside);
    return () => window.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

  useEffect(() => {
    if (isOpen && searchInputRef.current) {
      searchInputRef.current.focus();
    }
  }, [isOpen]);

  return (
    <div ref={containerRef} className="relative space-y-1">
      <div className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-slate-500">{label}</div>

      <button
        type="button"
        disabled={disabled}
        onClick={() => setIsOpen((previous) => !previous)}
        className="flex w-full items-center justify-between rounded-lg border border-slate-200 bg-white px-2 py-1 text-left text-xs font-medium text-slate-700 shadow-sm transition hover:border-sky-300 hover:text-slate-900 hover:shadow disabled:cursor-not-allowed disabled:opacity-50"
      >
        <span className="flex-1 truncate">{summary}</span>
        <span className="ml-2 shrink-0 text-[10px] text-slate-400">{isOpen ? '▲' : '▼'}</span>
      </button>

      {isOpen && !disabled ? (
        <div className="absolute z-40 mt-1 max-h-64 w-full overflow-hidden rounded-lg border border-slate-200 bg-white shadow-xl shadow-slate-200/60">
          <div className="flex items-center gap-1.5 border-b border-slate-200 bg-slate-50 px-2 py-1.5 text-xs text-slate-600">
            <input
              ref={searchInputRef}
              type="text"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search…"
              className="w-full rounded-md border border-slate-300 bg-white px-1.5 py-0.5 text-xs text-slate-700 focus:border-sky-400 focus:outline-none focus:ring-1 focus:ring-sky-200"
            />
            <button
              type="button"
              onClick={handleSelectAll}
              className="rounded-md border border-slate-200 bg-white px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-slate-600 transition hover:border-sky-300 hover:text-sky-600"
            >
              {options && selected.length === options.length ? 'Clear All' : 'Select All'}
            </button>
            {selected.length > 0 ? (
              <button
                type="button"
                onClick={handleClear}
                className="rounded-md border border-transparent px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-slate-500 transition hover:text-slate-700"
              >
                Reset
              </button>
            ) : null}
          </div>

          <div className="max-h-52 overflow-y-auto px-0.5 py-1">
            {filteredOptions.length === 0 ? (
              <div className="px-2 py-1.5 text-[10px] text-slate-400">No matches found</div>
            ) : (
              filteredOptions.map((option) => {
                const isSelected = selected.includes(option.value);
                return (
                  <label
                    key={option.value}
                    className={`flex cursor-pointer items-center gap-1.5 rounded-md px-2 py-1 text-xs transition ${
                      isSelected ? 'bg-sky-100/80 text-sky-700' : 'text-slate-700 hover:bg-slate-100'
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => toggleValue(option.value)}
                      className="size-3 rounded border-slate-300 text-sky-600 focus:ring-sky-500"
                    />
                    <span className="flex-1 truncate">{option.label}</span>
                  </label>
                );
              })
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
};


