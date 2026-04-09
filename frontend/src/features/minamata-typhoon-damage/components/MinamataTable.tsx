import React from 'react';
import type { MinamataTableRow } from '../types';

interface MinamataTableProps {
  rows: MinamataTableRow[];
  loading: boolean;
}

function getBigFont(base = 12, max = 18, min = 9): number {
  const width = window.innerWidth;
  return Math.max(min, Math.min(max, Math.round(base * (width / 1920))));
}

export function MinamataTable({ rows, loading }: MinamataTableProps) {
  const [fontSize, setFontSize] = React.useState(getBigFont(12, 18, 9));

  React.useEffect(() => {
    const updateFontSize = () => {
      setFontSize(getBigFont(12, 18, 9));
    };
    
    window.addEventListener('resize', updateFontSize);
    return () => window.removeEventListener('resize', updateFontSize);
  }, []);

  if (loading) {
    return (
      <div style={{ 
        padding: '2rem', 
        textAlign: 'center', 
        color: '#666',
        fontSize: `${fontSize}px`
      }}>
        Loading data...
      </div>
    );
  }

  if (rows.length === 0) {
    return (
      <div style={{ 
        padding: '2rem', 
        textAlign: 'center', 
        color: '#666',
        fontSize: `${fontSize}px`
      }}>
        No data available.
      </div>
    );
  }

  const formatNumber = (value: number | string): string => {
    if (value === null || value === undefined || value === '') return '';
    const num = typeof value === 'string' ? parseFloat(value) : value;
    if (isNaN(num)) return String(value);
    return Math.round(num).toLocaleString();
  };

  return (
    <div style={{ overflow: 'auto', flex: 1, minHeight: 0 }}>
      <table
        style={{
          width: '100%',
          borderCollapse: 'collapse',
          border: '1px solid #dee2e6',
          fontSize: `${fontSize}px`,
        }}
      >
        <thead>
          <tr>
            <th
              style={{
                background: '#212121',
                color: '#fff',
                fontWeight: 600,
                textAlign: 'center',
                verticalAlign: 'middle',
                padding: '0.15rem 0.4rem',
                height: '1.6rem',
                fontSize: `${fontSize}px`,
              }}
            >
              Month
            </th>
            <th
              style={{
                background: '#212121',
                color: '#fff',
                fontWeight: 600,
                textAlign: 'center',
                verticalAlign: 'middle',
                padding: '0.15rem 0.4rem',
                height: '1.6rem',
                fontSize: `${fontSize}px`,
              }}
            >
              No of Strings Breakdown
            </th>
            <th
              style={{
                background: '#212121',
                color: '#fff',
                fontWeight: 600,
                textAlign: 'center',
                verticalAlign: 'middle',
                padding: '0.15rem 0.4rem',
                height: '1.6rem',
                fontSize: `${fontSize}px`,
              }}
            >
              Budgeted Gen (MWh)
            </th>
            <th
              style={{
                background: '#212121',
                color: '#fff',
                fontWeight: 600,
                textAlign: 'center',
                verticalAlign: 'middle',
                padding: '0.15rem 0.4rem',
                height: '1.6rem',
                fontSize: `${fontSize}px`,
              }}
            >
              Loss due to String Failure (MWh)
            </th>
            <th
              style={{
                background: '#212121',
                color: '#fff',
                fontWeight: 600,
                textAlign: 'center',
                verticalAlign: 'middle',
                padding: '0.15rem 0.4rem',
                height: '1.6rem',
                fontSize: `${fontSize}px`,
              }}
            >
              Loss in USD
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => {
            const isTotal = row.isTotal || (row.month || '').toLowerCase().includes('total');
            return (
              <tr
                key={index}
                style={{
                  background: isTotal 
                    ? '#eaf3fb' 
                    : index % 2 === 0 
                      ? '#fff' 
                      : '#eaf3fb',
                  fontWeight: isTotal ? 'bold' : 'normal',
                  fontSize: `${fontSize}px`,
                  color: '#333',
                }}
              >
                <td
                  style={{
                    textAlign: 'center',
                    verticalAlign: 'middle',
                    padding: '0.15rem 0.4rem',
                    height: '1.6rem',
                    fontSize: `${fontSize}px`,
                    color: '#333',
                  }}
                >
                  {row.month}
                </td>
                <td
                  style={{
                    textAlign: 'center',
                    verticalAlign: 'middle',
                    padding: '0.15rem 0.4rem',
                    height: '1.6rem',
                    fontSize: `${fontSize}px`,
                    color: '#333',
                  }}
                >
                  {formatNumber(row.no_of_strings_breakdown)}
                </td>
                <td
                  style={{
                    textAlign: 'center',
                    verticalAlign: 'middle',
                    padding: '0.15rem 0.4rem',
                    height: '1.6rem',
                    fontSize: `${fontSize}px`,
                    color: '#333',
                  }}
                >
                  {formatNumber(row.budgeted_gen_mwh)}
                </td>
                <td
                  style={{
                    textAlign: 'center',
                    verticalAlign: 'middle',
                    padding: '0.15rem 0.4rem',
                    height: '1.6rem',
                    fontSize: `${fontSize}px`,
                    color: '#333',
                  }}
                >
                  {formatNumber(row.loss_due_to_string_failure_mwh)}
                </td>
                <td
                  style={{
                    textAlign: 'center',
                    verticalAlign: 'middle',
                    padding: '0.15rem 0.4rem',
                    height: '1.6rem',
                    fontSize: `${fontSize}px`,
                    color: '#333',
                  }}
                >
                  {formatNumber(row.loss_in_usd)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

