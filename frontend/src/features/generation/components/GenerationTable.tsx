/**
 * Generation Table Component - Displays hierarchical generation data
 */
import { useMemo } from 'react';
import type { HierarchicalRow } from '../types';
import { formatNumber } from '../utils/calculations';
import { useTheme } from '../../../contexts/ThemeContext';
import { useResponsiveFontSize } from '../../../utils/fontScaling';

interface GenerationTableProps {
  rows: HierarchicalRow[];
  onToggleExpand: (rowId: string) => void;
  expandedRows: Set<string>;
  renderExportButton?: boolean;
}

// CSV Export Function for Generation Table
// eslint-disable-next-line react-refresh/only-export-components
export const exportGenerationToCSV = (rows: HierarchicalRow[]) => {
  const csvRows: string[] = [];
  
  // Add headers (including percentage columns from bar charts)
  const headers = [
    'Country',
    'Portfolio',
    'Assets',
    'DC (MWp)',
    'IC Budget (MWh)',
    'Exp Budget (MWh)',
    'Actual Gen (MWh)',
    'Act vs IC (%)',
    'Forecast (MWh)',
    'Forecast vs IC (%)'
  ];
  csvRows.push(headers.join(','));
  
  // Add data rows (export ALL rows including totals, countries, portfolios, assets)
  rows.forEach((row) => {
    // Calculate percentages for bar charts (allow values > 100%)
    const actVsIcPct = row.ic > 0 ? (row.ag / row.ic) * 100 : 0;
    const forecastValue = typeof row.fYield === 'string' ? parseFloat(row.fYield.replace(/,/g, '')) || 0 : (row.fYield || 0);
    const forecastVsIcPct = row.ic > 0 ? (forecastValue / row.ic) * 100 : 0;
    
    const rowData = [
      `"${String(row.country).replace(/<[^>]*>/g, '')}"`, // Strip HTML tags
      `"${String(row.portfolio).replace(/<[^>]*>/g, '')}"`,
      `"${String(row.asset).replace(/<[^>]*>/g, '')}"`,
      row.dc.toString(),
      Math.round(row.ic).toString(),
      Math.round(row.exp).toString(),
      Math.round(row.ag).toString(),
      actVsIcPct > 0 ? actVsIcPct.toFixed(1) : '',
      typeof row.fYield === 'string' ? `"${row.fYield}"` : Math.round(row.fYield || 0).toString(),
      forecastVsIcPct > 0 ? forecastVsIcPct.toFixed(1) : ''
    ];
    csvRows.push(rowData.join(','));
  });
  
  // Create CSV content
  const csvContent = csvRows.join('\n');
  
  // Create blob and download
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  const url = URL.createObjectURL(blob);
  
  link.setAttribute('href', url);
  link.setAttribute('download', `Generation_Report_${new Date().toISOString().split('T')[0]}.csv`);
  link.style.visibility = 'hidden';
  
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
};

export function GenerationTable({ rows, onToggleExpand, expandedRows, renderExportButton = true }: GenerationTableProps) {
  const { theme } = useTheme();
  
  // Responsive font sizes
  const bodyFontSize = useResponsiveFontSize(10, 14, 9); // For table cells and body text
  const headerFontSize = useResponsiveFontSize(9, 13, 8); // For table headers
  const buttonFontSize = useResponsiveFontSize(10, 14, 9); // For buttons
  const progressFontSize = useResponsiveFontSize(10, 14, 9); // For progress bar text
  
  // Theme-aware colors
  const tableBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : 'rgba(203, 213, 225, 0.8)';
  const tableColumnBorder = theme === 'dark' ? 'rgba(71, 85, 105, 0.6)' : 'rgba(203, 213, 225, 0.9)';
  const tableBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.5)' : '#ffffff';
  const tableHeaderBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.9)' : 'rgba(241, 245, 249, 0.9)';
  const tableHeaderText = theme === 'dark' ? '#38bdf8' : '#0072ce';
  const tableRowBg = theme === 'dark' ? 'transparent' : 'transparent';
  const tableRowHoverBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.3)' : 'rgba(248, 250, 252, 0.9)';
  const tableRowText = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';
  const tableTotalRowBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.5)' : 'rgba(241, 245, 249, 0.9)';
  const tableRowBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.5)' : 'rgba(226, 232, 240, 0.8)';
  const expandButtonBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.8)' : '#ffffff';
  const expandButtonBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : 'rgba(203, 213, 225, 0.8)';
  const expandButtonText = theme === 'dark' ? '#38bdf8' : '#0072ce';
  const expandButtonHoverBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.9)' : '#f8fafc';
  const expandButtonHoverBorder = theme === 'dark' ? '#38bdf8' : '#0072ce';
  const progressBarBg = theme === 'dark' ? 'rgba(51, 65, 85, 0.5)' : '#e2e8f0';
  const progressBarBorder = theme === 'dark' ? 'rgba(71, 85, 105, 0.7)' : '#cbd5e0';
  const progressBarText = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';
  const exportButtonBg = theme === 'dark' ? 'rgba(56, 189, 248, 0.2)' : 'rgba(0, 114, 206, 0.1)';
  const exportButtonText = theme === 'dark' ? '#7dd3fc' : '#0072ce';
  const exportButtonHoverBg = theme === 'dark' ? 'rgba(56, 189, 248, 0.3)' : 'rgba(0, 114, 206, 0.15)';
  
  const visibleRows = useMemo(() => {
    const visible: HierarchicalRow[] = [];
    const hiddenSet = new Set<string>();

    rows.forEach((row) => {
      // Check if parent is hidden
      if (row.parentId && hiddenSet.has(row.parentId)) {
        hiddenSet.add(row.id);
        return;
      }

      // Check if parent is collapsed - if parent exists and is not expanded, hide child
      if (row.parentId) {
        const parent = rows.find((r) => r.id === row.parentId);
        if (parent && !expandedRows.has(parent.id)) {
          hiddenSet.add(row.id);
          return;
        }
      }

      // If we get here, either:
      // 1. No parent (root level)
      // 2. Parent is expanded
      // In both cases, check isHidden flag
      // isHidden means "hidden by default", but if parent is expanded, show it anyway
      if (row.isHidden && !row.parentId) {
        // Root-level rows with isHidden should be hidden
        hiddenSet.add(row.id);
        return;
      }

      // If row has a parent and parent is expanded, show it even if isHidden is true
      // If row has no parent and isHidden is false, show it
      visible.push(row);
    });

    return visible;
  }, [rows, expandedRows]);

  const renderProgressBar = (value: number, max: number, color: string = '#38bdf8') => {
    if (!max || max === 0) return null;
    const percentage = (value / max) * 100;
    const hasValue = value > 0;
    // Cap bar width at 100% to prevent overflow, but show actual percentage in text
    const barWidth = Math.min(percentage, 100);
    
    return (
      <div className="flex items-center justify-center gap-2">
        {/* Fixed width container ensures uniform bar length across all rows */}
        <div 
          className="h-4 w-28 overflow-hidden rounded border shadow-inner"
          style={{
            borderColor: progressBarBorder,
            backgroundColor: progressBarBg
          }}
        >
          <div
            className={`h-full transition-all ${hasValue ? 'shadow-md' : ''}`}
            style={{
              width: `${barWidth}%`,
              backgroundColor: color,
              minWidth: hasValue ? '3px' : '0',
              borderRadius: barWidth >= 100 ? 'inherit' : '0 0.25rem 0.25rem 0',
            }}
          />
        </div>
        <span className="min-w-10 text-center font-semibold" style={{ color: progressBarText, fontSize: `${progressFontSize}px` }}>
          {percentage.toFixed(1)}%
        </span>
      </div>
    );
  };

  const renderRow = (row: HierarchicalRow) => {
    const indent = row.level * 20;
    const isExpanded = expandedRows.has(row.id);
    const canExpand = row.isExpandable;

    return (
      <tr
        key={row.id}
        className="border-b transition"
        style={{
          borderColor: tableRowBorder,
          backgroundColor: row.isTotal ? tableTotalRowBg : tableRowBg,
          fontWeight: row.isTotal ? '600' : 'normal',
        }}
        onMouseEnter={(e) => {
          if (!row.isTotal) {
            e.currentTarget.style.backgroundColor = tableRowHoverBg;
          }
        }}
        onMouseLeave={(e) => {
          if (!row.isTotal) {
            e.currentTarget.style.backgroundColor = tableRowBg;
          }
        }}
      >
        <td className="px-2 py-1.5 text-left" style={{ color: tableRowText, borderRight: `1px solid ${tableColumnBorder}` }}>
          <div className="flex items-center gap-1" style={{ paddingLeft: `${indent}px` }}>
            {canExpand && (
              <button
                type="button"
                onClick={() => onToggleExpand(row.id)}
                className="flex size-4 items-center justify-center rounded border font-bold transition-colors"
                style={{
                  borderColor: expandButtonBorder,
                  backgroundColor: expandButtonBg,
                  color: expandButtonText,
                  fontSize: `${bodyFontSize}px`,
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = expandButtonHoverBg;
                  e.currentTarget.style.borderColor = expandButtonHoverBorder;
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = expandButtonBg;
                  e.currentTarget.style.borderColor = expandButtonBorder;
                }}
              >
                {isExpanded ? '−' : '+'}
              </button>
            )}
            {!canExpand && <span className="w-4" />}
            <span style={{ color: tableRowText, fontSize: `${bodyFontSize}px` }} dangerouslySetInnerHTML={{ __html: row.country }} />
          </div>
        </td>
        <td className="px-2 py-1.5 text-center" style={{ color: tableRowText, borderRight: `1px solid ${tableColumnBorder}` }}>
          <span style={{ fontSize: `${bodyFontSize}px` }} dangerouslySetInnerHTML={{ __html: String(row.portfolio) }} />
        </td>
        <td className="px-2 py-1.5 text-center" style={{ color: tableRowText, borderRight: `1px solid ${tableColumnBorder}` }}>
          <span style={{ fontSize: `${bodyFontSize}px` }} dangerouslySetInnerHTML={{ __html: String(row.asset) }} />
        </td>
        <td className="px-2 py-1.5 text-center" style={{ color: tableRowText, fontSize: `${bodyFontSize}px`, borderRight: `1px solid ${tableColumnBorder}` }}>{formatNumber(row.dc)}</td>
        <td className="px-2 py-1.5 text-center" style={{ color: tableRowText, fontSize: `${bodyFontSize}px`, borderRight: `1px solid ${tableColumnBorder}` }}>{formatNumber(row.ic)}</td>
        <td className="px-2 py-1.5 text-center" style={{ color: tableRowText, fontSize: `${bodyFontSize}px`, borderRight: `1px solid ${tableColumnBorder}` }}>{formatNumber(row.exp)}</td>
        <td className="px-2 py-1.5 text-center" style={{ color: tableRowText, fontSize: `${bodyFontSize}px`, borderRight: `1px solid ${tableColumnBorder}` }}>{formatNumber(row.ag)}</td>
        <td className="px-2 py-1.5 text-center" style={{ borderRight: `1px solid ${tableColumnBorder}` }}>
          {renderProgressBar(row.ag, row.ic, row.ag >= row.ic ? '#22c55e' : '#f97316')}
        </td>
        <td className="px-2 py-1.5 text-center" style={{ color: tableRowText, fontSize: `${bodyFontSize}px`, borderRight: `1px solid ${tableColumnBorder}` }}>
          {typeof row.fYield === 'string' ? row.fYield : formatNumber(row.fYield || 0)}
        </td>
        <td className="px-2 py-1.5 text-center" style={{ borderRight: `1px solid ${tableColumnBorder}` }}>
          {(() => {
            const forecastValue = typeof row.fYield === 'string' ? parseFloat(row.fYield.replace(/,/g, '')) || 0 : (row.fYield || 0);
            return renderProgressBar(forecastValue, row.ic, '#3b82f6');
          })()}
        </td>
      </tr>
    );
  };

  const exportButton = (
    <button
      onClick={() => exportGenerationToCSV(rows)}
      className="flex items-center gap-1 rounded-lg px-3 py-1.5 font-semibold transition-all hover:shadow-md"
      style={{
        backgroundColor: exportButtonBg,
        color: exportButtonText,
        fontSize: `${buttonFontSize}px`,
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.backgroundColor = exportButtonHoverBg;
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.backgroundColor = exportButtonBg;
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
  );

  // If only rendering export button, return it directly
  if (renderExportButton === true) {
    return exportButton;
  }

  // Render table (with or without button based on renderExportButton prop)
  const tableContent = (
    <div 
      className="max-h-[600px] overflow-auto rounded-lg border shadow-lg"
      style={{ borderColor: tableBorder }}
    >
      <table 
        className="min-w-full border-collapse text-xs"
        style={{ backgroundColor: tableBg }}
      >
      <thead 
        className="sticky top-0 z-10 border-b backdrop-blur-sm"
        style={{ 
          backgroundColor: tableHeaderBg,
          borderColor: tableBorder
        }}
      >
        <tr>
          <th className="whitespace-nowrap px-2 py-1.5 text-left font-semibold tracking-wide" style={{ color: tableHeaderText, fontSize: `${headerFontSize}px`, borderRight: `1px solid ${tableColumnBorder}` }}>Country</th>
          <th className="whitespace-nowrap px-2 py-1.5 text-center font-semibold tracking-wide" style={{ color: tableHeaderText, fontSize: `${headerFontSize}px`, borderRight: `1px solid ${tableColumnBorder}` }}>Portfolio</th>
          <th className="whitespace-nowrap px-2 py-1.5 text-center font-semibold tracking-wide" style={{ color: tableHeaderText, fontSize: `${headerFontSize}px`, borderRight: `1px solid ${tableColumnBorder}` }}>Assets</th>
          <th className="whitespace-nowrap px-2 py-1.5 text-center font-semibold tracking-wide" style={{ color: tableHeaderText, fontSize: `${headerFontSize}px`, borderRight: `1px solid ${tableColumnBorder}` }}>DC (MWp)</th>
          <th className="whitespace-nowrap px-2 py-1.5 text-center font-semibold tracking-wide" style={{ color: tableHeaderText, fontSize: `${headerFontSize}px`, borderRight: `1px solid ${tableColumnBorder}` }}>
            IC Budget (MWh)
          </th>
          <th className="whitespace-nowrap px-2 py-1.5 text-center font-semibold tracking-wide" style={{ color: tableHeaderText, fontSize: `${headerFontSize}px`, borderRight: `1px solid ${tableColumnBorder}` }}>
            Exp Budget (MWh)
          </th>
          <th className="whitespace-nowrap px-2 py-1.5 text-center font-semibold tracking-wide" style={{ color: tableHeaderText, fontSize: `${headerFontSize}px`, borderRight: `1px solid ${tableColumnBorder}` }}>
            Actual Gen (MWh)
          </th>
          <th className="whitespace-nowrap px-2 py-1.5 text-center font-semibold tracking-wide" style={{ color: tableHeaderText, fontSize: `${headerFontSize}px`, borderRight: `1px solid ${tableColumnBorder}` }}>
            Act vs IC
          </th>
          <th className="whitespace-nowrap px-2 py-1.5 text-center font-semibold tracking-wide" style={{ color: tableHeaderText, fontSize: `${headerFontSize}px`, borderRight: `1px solid ${tableColumnBorder}` }}>
            Forecast (MWh)
          </th>
          <th className="whitespace-nowrap px-2 py-1.5 text-center font-semibold tracking-wide" style={{ color: tableHeaderText, fontSize: `${headerFontSize}px` }}>
            Forecast vs IC
          </th>
        </tr>
      </thead>
      <tbody>{visibleRows.map(renderRow)}</tbody>
    </table>
    </div>
  );

  // If renderExportButton is false, return only table
  if (renderExportButton === false) {
    return tableContent;
  }

  // Default: render with export button
  return (
    <div className="flex flex-col gap-2">
      {/* Export Button */}
      <div className="flex justify-end">
        {exportButton}
      </div>
      {tableContent}
    </div>
  );
}

