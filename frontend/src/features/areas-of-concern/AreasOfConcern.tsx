import { useState, useEffect } from 'react';
import { AOCFilters } from './components/AOCFilters';
import { AOCRemarks } from './components/AOCRemarks';
import { useAOCData } from './hooks/useAOCData';
import type { AOCFilters as AOCFiltersType } from './types';

export function AreasOfConcern() {
  // Set default filters to "All" for country and portfolio
  const [userFilters, setUserFilters] = useState<AOCFiltersType>({
    country: '__all__',
    portfolio: '__all__',
  });

  // Fetch data with empty filters to get filterOptions
  const { filterOptions, loading: optionsLoading } = useAOCData({});

  // Use user filters for actual data filtering
  const { filteredData, loading, error } = useAOCData(userFilters);

  // Ensure the component fills the viewport, especially in iframes
  useEffect(() => {
    const root = document.getElementById('react-root');
    if (root) {
      const setHeight = () => {
        if (window.self !== window.top) {
          root.style.height = '100%';
          root.style.minHeight = '100vh';
        } else {
          root.style.height = '100vh';
          root.style.minHeight = '100vh';
        }
      };

      setHeight();
      window.addEventListener('resize', setHeight);
      return () => window.removeEventListener('resize', setHeight);
    }
  }, []);

  const handleFiltersChange = (newFilters: AOCFiltersType) => {
    setUserFilters(newFilters);
  };

  const handleReset = () => {
    setUserFilters({
      country: '__all__',
      portfolio: '__all__',
    });
  };

  if (error) {
    return (
      <div style={{ padding: '20px', textAlign: 'center', color: '#c62828' }}>
        <h2>Error loading data</h2>
        <p>{error.message}</p>
      </div>
    );
  }

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        width: '100%',
        margin: 0,
        padding: 0,
        background: 'linear-gradient(135deg, #e6f1fc 0%, #f8fbff 100%)',
        overflow: 'hidden',
        boxSizing: 'border-box',
      }}
    >
      {/* Filters */}
      <AOCFilters
        filters={userFilters}
        options={filterOptions}
        loading={loading || optionsLoading}
        onFiltersChange={handleFiltersChange}
        onReset={handleReset}
      />

      {/* Remarks */}
      <div
        style={{
          flex: 1,
          minHeight: 0,
          padding: '0 1vw',
          overflow: 'auto',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <AOCRemarks data={filteredData} filters={userFilters} loading={loading || optionsLoading} />
      </div>
    </div>
  );
}

