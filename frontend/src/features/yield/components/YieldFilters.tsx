import type { YieldFilterOptions, YieldFilters } from '../types';

interface YieldFiltersProps {
  filters: YieldFilters;
  options: YieldFilterOptions | null;
  loading: boolean;
  onFiltersChange: (filters: YieldFilters) => void;
  onReset: () => void;
}

export function YieldFilters({
  filters,
  options,
  loading,
  onFiltersChange,
  onReset,
}: YieldFiltersProps) {
  // Derive state directly from props to avoid sync issues
  const selectedMonth = filters.month || '';
  const selectedYear = filters.year || '';
  const selectedCountries = filters.countries || [];
  const selectedPortfolios = filters.portfolios || [];
  const selectedAssets = filters.assets || [];

  const handleMonthChange = (value: string) => {
    onFiltersChange({
      ...filters,
      month: value || null,
      year: null,
    });
  };

  const handleYearChange = (value: string) => {
    onFiltersChange({
      ...filters,
      year: value || null,
      month: null,
    });
  };

  const handleCountryToggle = (country: string) => {
    const newCountries = selectedCountries.includes(country)
      ? selectedCountries.filter((c) => c !== country)
      : [...selectedCountries, country];
    onFiltersChange({
      ...filters,
      countries: newCountries,
    });
  };

  const handlePortfolioToggle = (portfolio: string) => {
    const newPortfolios = selectedPortfolios.includes(portfolio)
      ? selectedPortfolios.filter((p) => p !== portfolio)
      : [...selectedPortfolios, portfolio];
    onFiltersChange({
      ...filters,
      portfolios: newPortfolios,
    });
  };

  const handleAssetToggle = (asset: string) => {
    const newAssets = selectedAssets.includes(asset)
      ? selectedAssets.filter((a) => a !== asset)
      : [...selectedAssets, asset];
    onFiltersChange({
      ...filters,
      assets: newAssets,
    });
  };

  const handleSelectAll = (type: 'countries' | 'portfolios' | 'assets') => {
    if (!options) return;

    const allValues = options[type] || [];
    const currentValues =
      type === 'countries'
        ? selectedCountries
        : type === 'portfolios'
          ? selectedPortfolios
          : selectedAssets;
    const isAllSelected = allValues.every((val: string) => currentValues.includes(val));

    if (isAllSelected) {
      // Deselect all
      if (type === 'countries') {
        onFiltersChange({ ...filters, countries: [] });
      } else if (type === 'portfolios') {
        onFiltersChange({ ...filters, portfolios: [] });
      } else {
        onFiltersChange({ ...filters, assets: [] });
      }
    } else {
      // Select all
      if (type === 'countries') {
        onFiltersChange({ ...filters, countries: allValues });
      } else if (type === 'portfolios') {
        onFiltersChange({ ...filters, portfolios: allValues });
      } else {
        onFiltersChange({ ...filters, assets: allValues });
      }
    }
  };

  const handleReset = () => {
    onReset();
  };

  return (
    <div className="mb-2 flex flex-wrap items-center gap-3 rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
      <div className="flex flex-wrap items-center gap-3">
        {/* Month Filter */}
        <div className="flex items-center gap-2">
          <span className="text-base" title="Month">📅</span>
          <select
            value={selectedMonth}
            onChange={(e) => handleMonthChange(e.target.value)}
            disabled={loading || !options?.months}
            className="min-w-[160px] rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-900 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500 disabled:opacity-50"
          >
            <option value="">All Months</option>
            {options?.months.map((month: string) => (
              <option key={month} value={month}>
                {month}
              </option>
            ))}
          </select>
        </div>

        {/* Year Filter */}
        <div className="flex items-center gap-2">
          <span className="text-base" title="Year">📅</span>
          <select
            value={selectedYear}
            onChange={(e) => handleYearChange(e.target.value)}
            disabled={loading || !options?.years}
            className="min-w-[120px] rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-900 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500 disabled:opacity-50"
          >
            <option value="">All Years</option>
            {options?.years.map((year: string) => (
              <option key={year} value={year}>
                {year}
              </option>
            ))}
          </select>
        </div>

        {/* Country Multi-Select */}
        <div className="relative flex items-center gap-2">
          <span className="text-base" title="Country">🌍</span>
          <div className="relative">
            <select
              multiple
              value={selectedCountries}
              onChange={(e) => {
                const values = Array.from(e.target.selectedOptions, (opt) => opt.value);
                values.forEach((val) => handleCountryToggle(val));
              }}
              disabled={loading || !options?.countries}
              size={4}
              className="min-w-[180px] rounded-lg border border-slate-300 bg-white px-2 py-1 text-sm text-slate-900 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500 disabled:opacity-50"
            >
              <option
                value="__select_all__"
                onClick={(e) => {
                  e.preventDefault();
                  handleSelectAll('countries');
                }}
                className="font-semibold text-sky-400"
              >
                {selectedCountries.length === options?.countries.length
                  ? 'Deselect All'
                  : 'Select All'}
              </option>
              {options?.countries.map((country: string) => (
                <option key={country} value={country}>
                  {country}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Portfolio Multi-Select */}
        <div className="relative flex items-center gap-2">
          <span className="text-base" title="Portfolio">📂</span>
          <div className="relative">
            <select
              multiple
              value={selectedPortfolios}
              onChange={(e) => {
                const values = Array.from(e.target.selectedOptions, (opt) => opt.value);
                values.forEach((val) => handlePortfolioToggle(val));
              }}
              disabled={loading || !options?.portfolios}
              size={4}
              className="min-w-[180px] rounded-lg border border-slate-300 bg-white px-2 py-1 text-sm text-slate-900 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500 disabled:opacity-50"
            >
              <option
                value="__select_all__"
                onClick={(e) => {
                  e.preventDefault();
                  handleSelectAll('portfolios');
                }}
                className="font-semibold text-sky-400"
              >
                {selectedPortfolios.length === options?.portfolios.length
                  ? 'Deselect All'
                  : 'Select All'}
              </option>
              {options?.portfolios.map((portfolio: string) => (
                <option key={portfolio} value={portfolio}>
                  {portfolio}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Asset Multi-Select */}
        <div className="relative flex items-center gap-2">
          <span className="text-base" title="Asset">🏭</span>
          <div className="relative" style={{ minWidth: '225px', maxWidth: '400px' }}>
            <select
              multiple
              value={selectedAssets}
              onChange={(e) => {
                const values = Array.from(e.target.selectedOptions, (opt) => opt.value);
                values.forEach((val) => handleAssetToggle(val));
              }}
              disabled={loading || !options?.assets}
              size={4}
              className="w-full min-w-[225px] rounded-lg border border-slate-300 bg-white px-2 py-1 text-sm text-slate-900 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500 disabled:opacity-50"
            >
              <option
                value="__select_all__"
                onClick={(e) => {
                  e.preventDefault();
                  handleSelectAll('assets');
                }}
                className="font-semibold text-sky-400"
              >
                {selectedAssets.length === options?.assets.length
                  ? 'Deselect All'
                  : 'Select All'}
              </option>
              {options?.assets.map((asset: string) => (
                <option key={asset} value={asset}>
                  {asset}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Reset Button */}
        <div className="ml-auto">
          <button
            onClick={handleReset}
            disabled={loading}
            className="rounded-lg bg-rose-500 px-4 py-1.5 text-sm font-medium text-white transition hover:bg-rose-600 disabled:opacity-50"
          >
            Reset
          </button>
        </div>
      </div>
    </div>
  );
}

