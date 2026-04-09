import type { AOCData, AOCFilters } from '../types';

interface AOCRemarksProps {
  data: AOCData[];
  filters: AOCFilters;
  loading: boolean;
}

export function AOCRemarks({ data, filters, loading }: AOCRemarksProps) {
  if (loading) {
    return (
      <div
        style={{
          background: '#fff',
          border: '1.5px solid #0072CE',
          borderRadius: '12px',
          minHeight: '200px',
          padding: '0.7rem 0.8rem',
          fontSize: '1.3rem',
          lineHeight: 1.5,
          marginTop: '20px',
          marginBottom: '1.2rem',
          color: '#222',
          boxShadow: '0 2px 12px rgba(0,114,206,0.08)',
          textAlign: 'center',
        }}
      >
        Loading data...
      </div>
    );
  }

  // Check if period filter is selected (month or year)
  const hasPeriodSelected = !!(filters.month || filters.year);

  // If no period is selected, show the instruction message
  if (!hasPeriodSelected) {
    return (
      <div
        style={{
          background: '#fff',
          border: '1.5px solid #0072CE',
          borderRadius: '12px',
          minHeight: '200px',
          padding: '0.7rem 0.8rem',
          fontSize: '1.3rem',
          lineHeight: 1.5,
          marginTop: '20px',
          marginBottom: '1.2rem',
          color: '#666',
          boxShadow: '0 2px 12px rgba(0,114,206,0.08)',
          textAlign: 'center',
          fontStyle: 'italic',
        }}
      >
        PLEASE SELECT PERIOD (MONTH) TO SEE THE AOC
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div
        style={{
          background: '#fff',
          border: '1.5px solid #0072CE',
          borderRadius: '12px',
          minHeight: '200px',
          padding: '0.7rem 0.8rem',
          fontSize: '1.3rem',
          lineHeight: 1.5,
          marginTop: '20px',
          marginBottom: '1.2rem',
          color: '#222',
          boxShadow: '0 2px 12px rgba(0,114,206,0.08)',
        }}
      >
        (No remarks found for this filter)
      </div>
    );
  }

  return (
    <div
      style={{
        background: '#fff',
        border: '1.5px solid #0072CE',
        borderRadius: '12px',
        minHeight: '200px',
        maxHeight: '600px',
        overflowY: 'auto',
        padding: '0.7rem 0.8rem',
        fontSize: '1.3rem',
        lineHeight: 1.5,
        marginTop: '20px',
        marginBottom: '1.2rem',
        whiteSpace: 'pre-line',
        color: '#222',
        boxShadow: '0 2px 12px rgba(0,114,206,0.08)',
      }}
    >
      {data.map((item, index) => (
        <div key={item.id || index}>
          <div style={{ marginBottom: '1.1em' }}>
            <b style={{ color: '#0072CE' }}>{index + 1}.</b>{' '}
            {item.remarks || '(No remarks found for this entry)'}
          </div>
          {index < data.length - 1 && (
            <hr
              style={{
                margin: '1.1em 0',
                borderTop: '1px dashed #0072CE',
                borderBottom: 'none',
                borderLeft: 'none',
                borderRight: 'none',
              }}
            />
          )}
        </div>
      ))}
    </div>
  );
}

