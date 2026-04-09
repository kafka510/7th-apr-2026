/**
 * Generation Budget Insights - Main Table Component
 * Displays IC Budget vs Expected Generation data
 */
import { useMemo } from 'react';
import { useTheme } from '../../../contexts/ThemeContext';
import { useResponsiveFontSize } from '../../../utils/fontScaling';
import type { ICBudgetDataEntry, AggregatedRow } from '../types';
import { aggregateByMonth, formatNumber, formatPercentage } from '../utils/dataUtils';

interface MainTableProps {
  data: ICBudgetDataEntry[];
}

// CSV Export Function
const exportToCSV = (tableRows: AggregatedRow[], fullYearSums: Record<string, number>, displayHeaders: string[]) => {
  // Helper function to format value for CSV (raw numbers, no commas)
  const formatForCSV = (value: number): string => {
    if (!Number.isFinite(value)) {
      return '';
    }
    return Math.round(value).toString();
  };

  // Helper function to format percentage for CSV
  const formatPercentageForCSV = (value: number): string => {
    if (!Number.isFinite(value)) {
      return '';
    }
    return value.toFixed(2);
  };

  // Prepare CSV data
  const csvRows: string[] = [];
  
  // Add headers
  csvRows.push(displayHeaders.join(','));
  
  // Add data rows
  tableRows.forEach((row) => {
    const rowData = [
      `"${row.Month}"`,
      formatForCSV(row['IC Approved Budget (MWh)']),
      formatForCSV(row['Expected Budget (MWh)']),
      formatForCSV(row['Actual Generation (MWh)']),
      formatForCSV(row['Grid Curtailment Budget (MWh)']),
      formatForCSV(row['Actual Curtailment (MWh)']),
      formatForCSV(row['Budget Irradiation (kWh/M2)']),
      formatForCSV(row['Actual Irradiation (kWh/M2)']),
      formatPercentageForCSV(row['Expected PR (%)']),
      formatPercentageForCSV(row['Actual PR (%)']),
    ];
    csvRows.push(rowData.join(','));
  });
  
  // Add total row
  const totalRow = ['"Total (2025)"'];
  displayHeaders.slice(1).forEach((header) => {
    if (header.includes('PR (%)')) {
      const validMonths = tableRows.filter((row) => {
        const value = row[header as keyof AggregatedRow] as number;
        return value && !isNaN(value) && value > 0;
      });
      const avg =
        validMonths.length > 0
          ? validMonths.reduce((sum, row) => sum + (row[header as keyof AggregatedRow] as number), 0) /
            validMonths.length
          : 0;
      totalRow.push(formatPercentageForCSV(avg));
    } else {
      const val = fullYearSums[header] || 0;
      totalRow.push(formatForCSV(val));
    }
  });
  csvRows.push(totalRow.join(','));
  
  // Create CSV content
  const csvContent = csvRows.join('\n');
  
  // Create blob and download
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  const url = URL.createObjectURL(blob);
  
  link.setAttribute('href', url);
  link.setAttribute('download', `IC_Budget_vs_Expected_${new Date().toISOString().split('T')[0]}.csv`);
  link.style.visibility = 'hidden';
  
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
};

export function MainTable({ data }: MainTableProps) {
  const { theme } = useTheme();
  
  // Responsive font sizes
  const bodyFontSize = useResponsiveFontSize(10, 14, 9);
  const tableFontSize = useResponsiveFontSize(12, 16, 10);
  const buttonFontSize = useResponsiveFontSize(10, 14, 9);
  
  const noDataBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.5)' : 'rgba(241, 245, 249, 0.8)';
  const noDataBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.5)' : 'rgba(203, 213, 225, 0.7)';
  const noDataText = theme === 'dark' ? '#cbd5e1' : '#475569';
  const exportButtonBg = theme === 'dark' ? 'rgba(59, 130, 246, 0.2)' : 'rgba(59, 130, 246, 0.1)';
  const exportButtonText = theme === 'dark' ? '#93c5fd' : '#1e40af';
  const tableBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.5)' : 'rgba(203, 213, 225, 0.7)';
  const tableHeaderBg = theme === 'dark'
    ? 'linear-gradient(to right, rgba(30, 41, 59, 0.8), rgba(51, 65, 85, 0.7))'
    : 'linear-gradient(to right, rgba(241, 245, 249, 0.9), rgba(226, 232, 240, 0.8))';
  const tableHeaderText = theme === 'dark' ? '#93c5fd' : '#1e40af';
  const tableRowBg1 = theme === 'dark' ? 'rgba(15, 23, 42, 0.4)' : 'rgba(255, 255, 255, 0.8)';
  const tableRowBg2 = theme === 'dark' ? 'rgba(30, 41, 59, 0.4)' : 'rgba(248, 250, 252, 0.8)';
  const tableRowHoverBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.6)' : 'rgba(241, 245, 249, 0.9)';
  const tableRowText = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';
  const totalRowBg = theme === 'dark' ? 'rgba(59, 130, 246, 0.3)' : 'rgba(59, 130, 246, 0.15)';
  const totalRowText = theme === 'dark' ? '#93c5fd' : '#1e40af';
  
  const { tableRows, fullYearSums } = useMemo(() => {
    if (data.length === 0) {
      return {
        tableRows: [],
        fullYearSums: {} as Record<string, number>,
      };
    }

    // Calculate cutoff date (N-1, previous month)
    const today = new Date();
    const cutoffDate = new Date(today.getFullYear(), today.getMonth() - 1, 1);

    const { aggregatedRows } = aggregateByMonth(data, cutoffDate);

    // Calculate full year totals
    const fullYearSums: Record<string, number> = {};
    const displayHeaders = [
      'IC Approved Budget (MWh)',
      'Expected Budget (MWh)',
      'Actual Generation (MWh)',
      'Grid Curtailment Budget (MWh)',
      'Actual Curtailment (MWh)',
      'Budget Irradiation (kWh/M2)',
      'Actual Irradiation (kWh/M2)',
    ];

    displayHeaders.forEach((h) => {
      fullYearSums[h] = 0;
    });

    aggregatedRows.forEach((row) => {
      displayHeaders.forEach((h) => {
        fullYearSums[h] += row[h as keyof AggregatedRow] as number;
      });
    });

    return {
      tableRows: aggregatedRows,
      fullYearSums,
    };
  }, [data]);

  const displayHeaders = [
    'Month',
    'IC Approved Budget (MWh)',
    'Expected Budget (MWh)',
    'Actual Generation (MWh)',
    'Grid Curtailment Budget (MWh)',
    'Actual Curtailment (MWh)',
    'Budget Irradiation (kWh/M2)',
    'Actual Irradiation (kWh/M2)',
    'Expected PR (%)',
    'Actual PR (%)',
  ];

  if (data.length === 0) {
    return (
      <div 
        className="rounded-lg border p-2"
        style={{
          backgroundColor: noDataBg,
          borderColor: noDataBorder,
          color: noDataText,
          fontSize: `${bodyFontSize}px`,
        }}
      >
        No data available for the selected filters.
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Export Button */}
      <div className="mb-2 flex shrink-0 justify-end">
        <button
          onClick={() => exportToCSV(tableRows, fullYearSums, displayHeaders)}
          className="flex items-center gap-1 rounded-lg px-3 py-1.5 font-semibold transition-all hover:shadow-md"
          style={{
            backgroundColor: exportButtonBg,
            color: exportButtonText,
            fontSize: `${buttonFontSize}px`,
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.backgroundColor = theme === 'dark' 
              ? 'rgba(59, 130, 246, 0.3)' 
              : 'rgba(59, 130, 246, 0.15)';
            e.currentTarget.style.boxShadow = theme === 'dark'
              ? '0 10px 15px -3px rgba(59, 130, 246, 0.2)'
              : '0 4px 6px -1px rgba(59, 130, 246, 0.15)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor = exportButtonBg;
            e.currentTarget.style.boxShadow = 'none';
          }}
        >
          <svg 
            xmlns="http://www.w3.org/2000/svg" 
            width="12" 
            height="12" 
            viewBox="0 0 24 24" 
            fill="none" 
            stroke="currentColor" 
            strokeWidth="2" 
            strokeLinecap="round" 
            strokeLinejoin="round"
          >
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="7 10 12 15 17 10" />
            <line x1="12" y1="15" x2="12" y2="3" />
          </svg>
          Export to CSV
        </button>
      </div>
      
      <div className="flex-1 overflow-auto">
        <table className="w-full border-collapse border" style={{ borderColor: tableBorder, fontSize: `${tableFontSize}px` }}>
        <thead className="sticky top-0 z-10">
          <tr style={{ background: tableHeaderBg }}>
            {displayHeaders.map((header) => (
              <th 
                key={header} 
                className="whitespace-nowrap border px-1 py-[0.5625rem] text-center font-semibold"
                style={{
                  borderColor: tableBorder,
                  color: tableHeaderText,
                  fontSize: `${tableFontSize}px`,
                }}
              >
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {tableRows.map((row, idx) => (
            <tr
              key={`${row.Month}-${idx}`}
              style={{
                backgroundColor: idx % 2 === 0 ? tableRowBg1 : tableRowBg2,
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = tableRowHoverBg;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = idx % 2 === 0 ? tableRowBg1 : tableRowBg2;
              }}
            >
              <td 
                className="whitespace-nowrap border px-1 py-2.5 text-center"
                style={{
                  borderColor: tableBorder,
                  color: tableRowText,
                  fontSize: `${tableFontSize}px`,
                }}
              >
                {row.Month}
              </td>
              <td 
                className="border px-1 py-2.5 text-center"
                style={{
                  borderColor: tableBorder,
                  color: tableRowText,
                  fontSize: `${tableFontSize}px`,
                }}
              >
                {formatNumber(row['IC Approved Budget (MWh)'])}
              </td>
              <td 
                className="border px-1 py-2.5 text-center"
                style={{
                  borderColor: tableBorder,
                  color: tableRowText,
                  fontSize: `${tableFontSize}px`,
                }}
              >
                {formatNumber(row['Expected Budget (MWh)'])}
              </td>
              <td 
                className="border px-1 py-2.5 text-center"
                style={{
                  borderColor: tableBorder,
                  color: tableRowText,
                  fontSize: `${tableFontSize}px`,
                }}
              >
                {formatNumber(row['Actual Generation (MWh)'])}
              </td>
              <td 
                className="border px-1 py-2.5 text-center"
                style={{
                  borderColor: tableBorder,
                  color: tableRowText,
                  fontSize: `${tableFontSize}px`,
                }}
              >
                {formatNumber(row['Grid Curtailment Budget (MWh)'])}
              </td>
              <td 
                className="border px-1 py-2.5 text-center"
                style={{
                  borderColor: tableBorder,
                  color: tableRowText,
                  fontSize: `${tableFontSize}px`,
                }}
              >
                {formatNumber(row['Actual Curtailment (MWh)'])}
              </td>
              <td 
                className="border px-1 py-2.5 text-center"
                style={{
                  borderColor: tableBorder,
                  color: tableRowText,
                  fontSize: `${tableFontSize}px`,
                }}
              >
                {formatNumber(row['Budget Irradiation (kWh/M2)'])}
              </td>
              <td 
                className="border px-1 py-2.5 text-center"
                style={{
                  borderColor: tableBorder,
                  color: tableRowText,
                  fontSize: `${tableFontSize}px`,
                }}
              >
                {formatNumber(row['Actual Irradiation (kWh/M2)'])}
              </td>
              <td 
                className="border px-1 py-2.5 text-center"
                style={{
                  borderColor: tableBorder,
                  color: tableRowText,
                  fontSize: `${tableFontSize}px`,
                }}
              >
                {formatPercentage(row['Expected PR (%)'])}
              </td>
              <td 
                className="border px-1 py-2.5 text-center"
                style={{
                  borderColor: tableBorder,
                  color: tableRowText,
                  fontSize: `${tableFontSize}px`,
                }}
              >
                {formatPercentage(row['Actual PR (%)'])}
              </td>
            </tr>
          ))}

          {/* Full Year Total Row */}
          <tr className="sticky bottom-0 font-bold" style={{ backgroundColor: totalRowBg }}>
            <td 
              className="whitespace-nowrap border px-1 py-2.5 text-center"
              style={{
                borderColor: tableBorder,
                color: totalRowText,
                fontSize: `${tableFontSize}px`,
              }}
            >
              Total (2025)
            </td>
            {displayHeaders.slice(1).map((header) => {
              if (header.includes('PR (%)')) {
                const validMonths = tableRows.filter((row) => {
                  const value = row[header as keyof AggregatedRow] as number;
                  return value && !isNaN(value) && value > 0;
                });
                const avg =
                  validMonths.length > 0
                    ? validMonths.reduce((sum, row) => sum + (row[header as keyof AggregatedRow] as number), 0) /
                      validMonths.length
                    : 0;
                return (
                  <td 
                    key={header} 
                    className="border px-1 py-2.5 text-center"
                    style={{
                      borderColor: tableBorder,
                      color: totalRowText,
                      fontSize: `${tableFontSize}px`,
                    }}
                  >
                    {formatPercentage(avg)}
                  </td>
                );
              } else {
                const val = (fullYearSums as Record<string, number>)[header] || 0;
                return (
                  <td 
                    key={header} 
                    className="border px-1 py-2.5 text-center"
                    style={{
                      borderColor: tableBorder,
                      color: totalRowText,
                      fontSize: `${tableFontSize}px`,
                    }}
                  >
                    {formatNumber(val)}
                  </td>
                );
              }
            })}
          </tr>
        </tbody>
      </table>
      </div>
    </div>
  );
}

