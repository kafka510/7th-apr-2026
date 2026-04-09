import { useMemo } from 'react';
import type { AOCFilters, AOCFilterOptions } from '../types';

interface AOCFiltersProps {
  filters: AOCFilters;
  options: AOCFilterOptions;
  loading: boolean;
  onFiltersChange: (filters: AOCFilters) => void;
  onReset: () => void;
}

export function AOCFilters({
  filters,
  options,
  loading,
  onFiltersChange,
  onReset,
}: AOCFiltersProps) {
  const handleMonthChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value;
    onFiltersChange({
      ...filters,
      month: value || undefined,
      year: undefined,
    });
  };

  const handleCountryChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value;
    onFiltersChange({
      ...filters,
      country: value || undefined,
    });
  };

  const handlePortfolioChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value;
    onFiltersChange({
      ...filters,
      portfolio: value || undefined,
    });
  };

  // Get available portfolios based on selected country
  const availablePortfolios = useMemo(() => {
    if (!filters.country || filters.country === '__all__') {
      return options.portfolios;
    }
    // In a full implementation, this would filter portfolios based on the selected country
    // For now, return all portfolios
    return options.portfolios;
  }, [options.portfolios, filters.country]);

  return (
    <div style={{ padding: '0 1vw', background: 'white', boxShadow: '0 8px 40px 0 rgba(0,0,0,0.09)', marginBottom: '8px' }}>
      <div style={{ display: 'flex', gap: '2rem', alignItems: 'flex-end', flexWrap: 'wrap', width: '100%' }}>
        <div style={{ minWidth: '180px', maxWidth: '280px', flex: '1 1 200px' }}>
          <label style={{ fontSize: '0.82rem', fontWeight: 600, color: '#0072CE', marginBottom: '4px', display: 'block' }}>
            Country
          </label>
          <select
            value={filters.country || '__all__'}
            onChange={handleCountryChange}
            disabled={loading}
            style={{
              background: 'rgba(255,255,255,0.95)',
              color: '#222',
              borderRadius: '0.75rem',
              border: 'none',
              width: '100%',
              height: '2.2rem',
              padding: '0.1rem 0.8rem',
              fontSize: '1rem',
              fontWeight: 600,
              boxShadow: '0 2px 12px rgba(0,0,0,0.03)',
            }}
          >
            <option value="__all__">All Countries</option>
            {options.countries.map((country) => (
              <option key={country} value={country}>
                {country}
              </option>
            ))}
          </select>
        </div>

        <div style={{ minWidth: '180px', maxWidth: '280px', flex: '1 1 200px' }}>
          <label style={{ fontSize: '0.82rem', fontWeight: 600, color: '#0072CE', marginBottom: '4px', display: 'block' }}>
            Portfolio
          </label>
          <select
            value={filters.portfolio || '__all__'}
            onChange={handlePortfolioChange}
            disabled={loading}
            style={{
              background: 'rgba(255,255,255,0.95)',
              color: '#222',
              borderRadius: '0.75rem',
              border: 'none',
              width: '100%',
              height: '2.2rem',
              padding: '0.1rem 0.8rem',
              fontSize: '1rem',
              fontWeight: 600,
              boxShadow: '0 2px 12px rgba(0,0,0,0.03)',
            }}
          >
            <option value="__all__">All Portfolio</option>
            {availablePortfolios.map((portfolio) => (
              <option key={portfolio} value={portfolio}>
                {portfolio}
              </option>
            ))}
          </select>
        </div>

        <div style={{ minWidth: '180px', maxWidth: '280px', flex: '1 1 200px' }}>
          <label style={{ fontSize: '0.82rem', fontWeight: 600, color: '#0072CE', marginBottom: '4px', display: 'block' }}>
            Month
          </label>
          <select
            value={filters.month || ''}
            onChange={handleMonthChange}
            disabled={loading}
            style={{
              background: 'rgba(255,255,255,0.95)',
              color: '#222',
              borderRadius: '0.75rem',
              border: 'none',
              width: '100%',
              height: '2.2rem',
              padding: '0.1rem 0.8rem',
              fontSize: '1rem',
              fontWeight: 600,
              boxShadow: '0 2px 12px rgba(0,0,0,0.03)',
            }}
          >
            <option value="">Select Month</option>
            {options.months.map((month) => (
              <option key={month} value={month}>
                {month}
              </option>
            ))}
          </select>
        </div>

        <div style={{ minWidth: '80px' }}>
          <label style={{ fontSize: '0.82rem', fontWeight: 600, color: '#0072CE', marginBottom: '4px', display: 'block' }}>
            &nbsp;
          </label>
          <button
            type="button"
            onClick={onReset}
            disabled={loading}
            style={{
              background: '#e60000',
              border: '1px solid #e60000',
              borderRadius: '0.75rem',
              padding: '0.1rem 0.8rem',
              fontSize: '1rem',
              color: '#ffffff',
              cursor: loading ? 'not-allowed' : 'pointer',
              textAlign: 'center',
              transition: 'background 0.2s, border-color 0.2s',
              height: '2.2rem',
              fontWeight: 600,
              minWidth: '80px',
              opacity: loading ? 0.6 : 1,
            }}
            onMouseEnter={(e) => {
              if (!loading) {
                e.currentTarget.style.background = '#cc0000';
                e.currentTarget.style.borderColor = '#cc0000';
              }
            }}
            onMouseLeave={(e) => {
              if (!loading) {
                e.currentTarget.style.background = '#e60000';
                e.currentTarget.style.borderColor = '#e60000';
              }
            }}
          >
            Reset
          </button>
        </div>
      </div>
    </div>
  );
}

