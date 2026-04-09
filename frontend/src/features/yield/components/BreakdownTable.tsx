import { Fragment, useMemo, useState } from 'react';
import { useTheme } from '../../../contexts/ThemeContext';
import { useResponsiveFontSize } from '../../../utils/fontScaling';
import type { YieldDataEntry } from '../types';

type BreakdownTableProps = {
  data: YieldDataEntry[];
  loading?: boolean;
};

function toNumber(val: number | string | undefined | null): number {
  if (val === null || val === undefined || val === '') return 0;
  if (typeof val === 'number') return isNaN(val) ? 0 : val;
  const parsed = parseFloat(String(val));
  return isNaN(parsed) ? 0 : parsed;
}

function formatNumber(val: number): string {
  return Math.round(val).toLocaleString();
}

type FailureType = {
  // Primary key used for grouping/labels
  key: keyof YieldDataEntry | string;
  label: string;
  cls: string;
  color: string;
  // Optional alternate source field names coming from the backend/CSV
  aliases?: (keyof YieldDataEntry | string)[];
};

const FAILURE_TYPES: FailureType[] = [
  { key: 'string failure', label: 'String', cls: 'string', color: '#bbdefb' },
  { key: 'inverter failure', label: 'Inverter', cls: 'inverter', color: '#b3c6f7' },
  // AC failure may come from 'ac_failure' or 'ac failure'
  { key: 'ac_failure', label: 'AC', cls: 'ac', color: '#ffccbc', aliases: ['ac failure'] },
  // Scheduled outage may be spelled correctly or as 'schduled_outage_loss'
  { key: 'scheduled_outage_loss', label: 'Scheduled', cls: 'scheduled', color: '#ffe0b2', aliases: ['schduled_outage_loss'] },
];

// CSV Export Function
const exportToCSV = (groups: GroupedData, grandTotal: Record<string, number>) => {
  const csvRows: string[] = [];
  
  // Add headers
  const headers = ['Country', 'Portfolio', 'Asset', ...FAILURE_TYPES.map(ft => ft.label), 'Total'];
  csvRows.push(headers.join(','));
  
  // Add grand total row
  const grandTotalRow = [
    '"All"',
    '"All"',
    '"All"',
    ...FAILURE_TYPES.map(ft => Math.round(grandTotal[ft.key]).toString()),
    Math.round(grandTotal.total).toString()
  ];
  csvRows.push(grandTotalRow.join(','));
  
  // Add country, portfolio, and asset rows
  Object.entries(groups).forEach(([country, portfolios]) => {
    // Calculate country totals
    const countryTotal: Record<string, number> = {};
    FAILURE_TYPES.forEach((ft) => {
      countryTotal[ft.key as string] = 0;
    });
    countryTotal.total = 0;
    
    Object.values(portfolios).forEach((assets) => {
      Object.values(assets).forEach((vals) => {
        FAILURE_TYPES.forEach((ft) => {
          countryTotal[ft.key] += vals[ft.key] || 0;
        });
        countryTotal.total += vals.total;
      });
    });
    
    // Add country row
    const countryRow = [
      `"${country}"`,
      '""',
      '""',
      ...FAILURE_TYPES.map(ft => Math.round(countryTotal[ft.key]).toString()),
      Math.round(countryTotal.total).toString()
    ];
    csvRows.push(countryRow.join(','));
    
    // Add portfolio and asset rows
    Object.entries(portfolios).forEach(([portfolio, assets]) => {
      // Calculate portfolio totals
      const portfolioTotal: Record<string, number> = {};
      FAILURE_TYPES.forEach((ft) => {
        portfolioTotal[ft.key as string] = 0;
      });
      portfolioTotal.total = 0;
      
      Object.values(assets).forEach((vals) => {
        FAILURE_TYPES.forEach((ft) => {
          portfolioTotal[ft.key] += vals[ft.key] || 0;
        });
        portfolioTotal.total += vals.total;
      });
      
      // Add portfolio row
      const portfolioRow = [
        '""',
        `"${portfolio}"`,
        '""',
        ...FAILURE_TYPES.map(ft => Math.round(portfolioTotal[ft.key]).toString()),
        Math.round(portfolioTotal.total).toString()
      ];
      csvRows.push(portfolioRow.join(','));
      
      // Add asset rows
      Object.entries(assets).forEach(([asset, vals]) => {
        const assetRow = [
          '""',
          '""',
          `"${asset}"`,
          ...FAILURE_TYPES.map(ft => Math.round(vals[ft.key] || 0).toString()),
          Math.round(vals.total).toString()
        ];
        csvRows.push(assetRow.join(','));
      });
    });
  });
  
  // Create CSV content
  const csvContent = csvRows.join('\n');
  
  // Create blob and download
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  const url = URL.createObjectURL(blob);
  
  link.setAttribute('href', url);
  link.setAttribute('download', `Yield_Breakdown_${new Date().toISOString().split('T')[0]}.csv`);
  link.style.visibility = 'hidden';
  
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
};

type GroupedData = {
  [country: string]: {
    [portfolio: string]: {
      [asset: string]: {
        [key: string]: number;
        total: number;
      };
    };
  };
};

type ExpandedState = {
  [key: string]: boolean;
};

export const BreakdownTable = ({ data, loading = false }: BreakdownTableProps) => {
  const { theme } = useTheme();
  
  // Responsive font sizes
  const subtitleFontSize = useResponsiveFontSize(11, 15, 10);
  const buttonFontSize = useResponsiveFontSize(10, 14, 9);
  const [expanded, setExpanded] = useState<ExpandedState>({});
  
  // Theme-aware colors
  const containerBg = theme === 'dark'
    ? 'linear-gradient(to bottom right, rgba(15, 23, 42, 0.9), rgba(30, 41, 59, 0.7), rgba(15, 23, 42, 0.9))'
    : 'linear-gradient(to bottom right, rgba(255, 255, 255, 0.95), rgba(248, 250, 252, 0.9), rgba(255, 255, 255, 0.95))';
  const containerBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(203, 213, 225, 0.8)';
  const containerShadow = theme === 'dark' 
    ? '0 20px 25px -5px rgba(0, 0, 0, 0.4)' 
    : '0 10px 15px -3px rgba(0, 0, 0, 0.1)';
  const titleColor = theme === 'dark' ? '#ffffff' : '#1a1a1a';
  const subtitleColor = theme === 'dark' ? '#94a3b8' : '#64748b';
  const tableHeaderBg = theme === 'dark' ? 'rgba(51, 65, 59, 0.8)' : 'rgba(241, 245, 249, 0.9)';
  const tableHeaderText = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';
  const tableBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : 'rgba(203, 213, 225, 0.7)';
  const tableCellBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.3)' : 'rgba(248, 250, 252, 0.5)';
  const tableCellText = theme === 'dark' ? '#cbd5e1' : '#475569';
  const countryHeaderBg = theme === 'dark' ? '#1e3a8a' : '#3b82f6';
  const portfolioHeaderBg = theme === 'dark' ? '#2563eb' : '#60a5fa';
  const assetHeaderBg = theme === 'dark' ? 'rgba(59, 130, 246, 0.1)' : 'rgba(147, 197, 253, 0.5)';
  const assetHeaderText = theme === 'dark' ? '#e2e8f0' : '#1e40af';
  const grandTotalBg = theme === 'dark' ? 'rgba(250, 204, 21, 0.3)' : 'rgba(250, 204, 21, 0.15)';
  const loadingTextColor = theme === 'dark' ? '#94a3b8' : '#64748b';
  const spinnerBorder = theme === 'dark' ? 'rgba(71, 85, 105, 0.6)' : 'rgba(203, 213, 225, 0.7)';
  const exportButtonBg = theme === 'dark' ? 'rgba(59, 130, 246, 0.2)' : 'rgba(59, 130, 246, 0.1)';
  const exportButtonText = theme === 'dark' ? '#93c5fd' : '#1e40af';

  const { groups, maxFailure, grandTotal } = useMemo(() => {
    const groups: GroupedData = {};
    const grandTotal: Record<string, number> = {};
    FAILURE_TYPES.forEach((ft) => {
      grandTotal[ft.key as string] = 0;
    });
    grandTotal.total = 0;

    // Group data by Country > Portfolio > Asset
    data.forEach((row) => {
      const country = row.country || 'Unknown';
      const portfolio = row.portfolio || 'Unknown';
      const asset = String(row.assetno || 'Unknown');

      if (!groups[country]) groups[country] = {};
      if (!groups[country][portfolio]) groups[country][portfolio] = {};
      if (!groups[country][portfolio][asset]) {
        groups[country][portfolio][asset] = { total: 0 };
      }

      FAILURE_TYPES.forEach((ft) => {
        // Handle optional fields that might be undefined
        // Try primary key first, then any aliases
        const keysToCheck = [ft.key, ...(ft.aliases ?? [])];
        let rawValue: number | string | undefined | null = 0;
        for (const k of keysToCheck) {
          const candidate = (row as unknown as Record<string, number | string | undefined | null>)[k as string];
          if (candidate !== undefined && candidate !== null && candidate !== '') {
            rawValue = candidate;
            break;
          }
        }
        const value = toNumber(rawValue);
        const destKey = ft.key as string;
        groups[country][portfolio][asset][destKey] =
          (groups[country][portfolio][asset][destKey] || 0) + value;
        groups[country][portfolio][asset].total += value;
      });
    });

    // Calculate grand totals from grouped data (not from individual rows)
    Object.values(groups).forEach((portfolios) => {
      Object.values(portfolios).forEach((assets) => {
        Object.values(assets).forEach((vals) => {
          FAILURE_TYPES.forEach((ft) => {
            grandTotal[ft.key] += vals[ft.key] || 0;
          });
          grandTotal.total += vals.total;
        });
      });
    });

    // Calculate max absolute value for each failure type (for bar width calculation)
    const maxFailure: Record<string, number> = {};
    FAILURE_TYPES.forEach((ft) => {
      const k = ft.key as string;
      let max = 0;
      Object.values(groups).forEach((portfolios) => {
        Object.values(portfolios).forEach((assets) => {
          Object.values(assets).forEach((vals) => {
            max = Math.max(max, Math.abs(vals[k] || 0));
          });
        });
      });
      maxFailure[k] = max;
    });

    return { groups, maxFailure, grandTotal };
  }, [data]);

  const toggleExpand = (key: string) => {
    setExpanded((prev) => {
      const newState = { ...prev };
      const isCurrentlyExpanded = prev[key] === true;
      
      if (isCurrentlyExpanded) {
        // Collapsing: also collapse all children
        newState[key] = false;
        Object.keys(newState).forEach((k) => {
          if (k.startsWith(key + '-')) {
            delete newState[k];
          }
        });
      } else {
        // Expanding
        newState[key] = true;
      }
      
      return newState;
    });
  };

  const isExpanded = (key: string) => expanded[key] === true;

  if (loading) {
    return (
      <div 
        className="flex h-64 items-center justify-center rounded-xl border shadow-xl"
        style={{
          borderColor: containerBorder,
          background: containerBg,
          boxShadow: containerShadow,
        }}
      >
        <div className="flex flex-col items-center gap-2">
          <div 
            className="size-6 animate-spin rounded-full border-2 border-t-sky-500"
            style={{ borderColor: spinnerBorder }}
          />
          <div className="text-sm" style={{ color: loadingTextColor }}>Loading breakdown table...</div>
        </div>
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div 
        className="flex h-64 items-center justify-center rounded-xl border shadow-xl"
        style={{
          borderColor: containerBorder,
          background: containerBg,
          boxShadow: containerShadow,
        }}
      >
        <div style={{ color: loadingTextColor }}>No data available</div>
      </div>
    );
  }

  return (
    <div 
      className="flex flex-col rounded-xl border p-2 shadow-xl"
      style={{
        borderColor: containerBorder,
        background: containerBg,
        boxShadow: containerShadow,
      }}
    >
      <div className="mb-2 flex shrink-0 items-center justify-between">
        <div>
          <h2 style={{ color: titleColor, fontSize: '11px', fontWeight: 500 }}>Breakdown Table</h2>
          <p style={{ color: subtitleColor, fontSize: `${subtitleFontSize}px` }}>
            {data.length} record{data.length !== 1 ? 's' : ''}
          </p>
        </div>
        <button
          onClick={() => exportToCSV(groups, grandTotal)}
          className="flex items-center gap-1 rounded-lg px-3 py-1.5 font-semibold transition-all hover:shadow-md"
          style={{
            fontSize: `${buttonFontSize}px`,
            backgroundColor: exportButtonBg,
            color: exportButtonText,
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.backgroundColor = theme === 'dark' 
              ? 'rgba(59, 130, 246, 0.3)' 
              : 'rgba(59, 130, 246, 0.15)';
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
      </div>

      <div className="overflow-visible">
        <table className="breakdown-table w-full border-collapse text-[11px]">
          <thead>
            <tr>
              <th 
                rowSpan={2} 
                className="border p-1 text-center font-bold"
                style={{
                  borderColor: tableBorder,
                  backgroundColor: tableHeaderBg,
                  color: tableHeaderText,
                }}
              >
                Country
              </th>
              <th 
                rowSpan={2} 
                className="border p-1 text-center font-bold"
                style={{
                  borderColor: tableBorder,
                  backgroundColor: tableHeaderBg,
                  color: tableHeaderText,
                }}
              >
                Portfolio
              </th>
              <th 
                rowSpan={2} 
                className="border p-1 text-center font-bold"
                style={{
                  borderColor: tableBorder,
                  backgroundColor: tableHeaderBg,
                  color: tableHeaderText,
                }}
              >
                Asset
              </th>
              <th
                colSpan={FAILURE_TYPES.length + 1}
                className="border p-1 text-center font-bold"
                style={{
                  borderColor: tableBorder,
                  backgroundColor: tableHeaderBg,
                  color: tableHeaderText,
                }}
              >
                Loss (MWh)
              </th>
            </tr>
            <tr>
              {FAILURE_TYPES.map((ft) => (
                <th
                  key={ft.key}
                  className={`failure-col failure-col-${ft.cls} border p-1 text-center font-bold`}
                  style={{
                    borderColor: tableBorder,
                    backgroundColor: tableHeaderBg,
                    color: tableHeaderText,
                  }}
                >
                  {ft.label}
                </th>
              ))}
              <th 
                className="failure-col border p-1 text-center font-bold"
                style={{
                  borderColor: tableBorder,
                  backgroundColor: tableHeaderBg,
                  color: tableHeaderText,
                }}
              >
                Total
              </th>
            </tr>
          </thead>
          <tbody>
            {/* Grand Total Row */}
            <tr 
              className="grand-total-row border-b"
              style={{
                borderColor: tableBorder,
                backgroundColor: grandTotalBg,
              }}
            >
              <td 
                className="border p-1 text-center font-bold"
                style={{
                  borderColor: tableBorder,
                  color: tableHeaderText,
                }}
              >
                <b>All</b>
              </td>
              <td 
                className="border p-1 text-center font-bold"
                style={{
                  borderColor: tableBorder,
                  color: tableHeaderText,
                }}
              >
                <b>All</b>
              </td>
              <td 
                className="border p-1 text-center font-bold"
                style={{
                  borderColor: tableBorder,
                  color: tableHeaderText,
                }}
              >
                <b>All</b>
              </td>
              {FAILURE_TYPES.map((ft) => (
                <td
                  key={ft.key}
                  className={`failure-col failure-col-${ft.cls} border p-1 text-center font-bold`}
                  style={{
                    borderColor: tableBorder,
                    color: tableHeaderText,
                  }}
                >
                  <b>{formatNumber(Math.round(grandTotal[ft.key]))}</b>
                </td>
              ))}
              <td 
                className="failure-col border p-1 text-center font-bold"
                style={{
                  borderColor: tableBorder,
                  color: tableHeaderText,
                }}
              >
                <b>{formatNumber(Math.round(grandTotal.total))}</b>
              </td>
            </tr>

            {/* Country, Portfolio, Asset Rows */}
            {Object.entries(groups).map(([country, portfolios], cIdx) => {
              const countryId = `country-${cIdx}`;
              const countryExpanded = isExpanded(countryId);

              // Calculate country totals
              const countryTotal: Record<string, number> = {};
              FAILURE_TYPES.forEach((ft) => {
                countryTotal[ft.key as string] = 0;
              });
              countryTotal.total = 0;

              Object.values(portfolios).forEach((assets) => {
                Object.values(assets).forEach((vals) => {
                  FAILURE_TYPES.forEach((ft) => {
                    countryTotal[ft.key] += vals[ft.key] || 0;
                  });
                  countryTotal.total += vals.total;
                });
              });

              return (
                <Fragment key={countryId}>
                  {/* Country Row */}
                  <tr className="country-row border-b" style={{ borderColor: tableBorder }}>
                    <td 
                      className="border p-1 text-left font-semibold text-white"
                      style={{
                        borderColor: tableBorder,
                        backgroundColor: countryHeaderBg,
                      }}
                    >
                      <button
                        onClick={() => toggleExpand(countryId)}
                        className="mr-1 inline-block w-4 text-center font-bold"
                      >
                        {countryExpanded ? '−' : '+'}
                      </button>
                      {country}
                    </td>
                    <td 
                      className="border p-1"
                      style={{
                        borderColor: tableBorder,
                        backgroundColor: tableCellBg,
                        color: tableCellText,
                      }}
                    />
                    <td 
                      className="border p-1"
                      style={{
                        borderColor: tableBorder,
                        backgroundColor: tableCellBg,
                        color: tableCellText,
                      }}
                    />
                    {FAILURE_TYPES.map((ft) => (
                      <td
                        key={ft.key}
                        className={`failure-col failure-col-${ft.cls} border p-1 text-center`}
                        style={{
                          borderColor: tableBorder,
                          backgroundColor: tableCellBg,
                          color: tableCellText,
                        }}
                      >
                        {formatNumber(Math.round(countryTotal[ft.key]))}
                      </td>
                    ))}
                    <td 
                      className="failure-col border p-1 text-center"
                      style={{
                        borderColor: tableBorder,
                        backgroundColor: tableCellBg,
                        color: tableCellText,
                      }}
                    >
                      {formatNumber(Math.round(countryTotal.total))}
                    </td>
                  </tr>

                  {/* Portfolio Rows */}
                  {Object.entries(portfolios).map(([portfolio, assets], pIdx) => {
                    const portfolioId = `${countryId}-portfolio-${pIdx}`;
                    const portfolioExpanded = isExpanded(portfolioId);

                    // Calculate portfolio totals
                  const portfolioTotal: Record<string, number> = {};
                  FAILURE_TYPES.forEach((ft) => {
                    portfolioTotal[ft.key as string] = 0;
                  });
                  portfolioTotal.total = 0;

                    Object.values(assets).forEach((vals) => {
                      FAILURE_TYPES.forEach((ft) => {
                        portfolioTotal[ft.key] += vals[ft.key] || 0;
                      });
                      portfolioTotal.total += vals.total;
                    });

                    if (!countryExpanded) return null;

                    return (
                      <Fragment key={portfolioId}>
                        {/* Portfolio Row */}
                        <tr
                          className="portfolio-row border-b"
                          style={{ 
                            display: countryExpanded ? '' : 'none',
                            borderColor: tableBorder,
                          }}
                        >
                          <td 
                            className="border p-1"
                            style={{
                              borderColor: tableBorder,
                              backgroundColor: tableCellBg,
                              color: tableCellText,
                            }}
                          />
                          <td 
                            className="border p-1 text-left font-semibold text-white"
                            style={{
                              borderColor: tableBorder,
                              backgroundColor: portfolioHeaderBg,
                            }}
                          >
                            <button
                              onClick={() => toggleExpand(portfolioId)}
                              className="mr-1 inline-block w-4 text-center font-bold"
                            >
                              {portfolioExpanded ? '−' : '+'}
                            </button>
                            {portfolio}
                          </td>
                          <td 
                            className="border p-1"
                            style={{
                              borderColor: tableBorder,
                              backgroundColor: tableCellBg,
                              color: tableCellText,
                            }}
                          />
                          {FAILURE_TYPES.map((ft) => (
                            <td
                              key={ft.key}
                              className={`failure-col failure-col-${ft.cls} border p-1 text-center`}
                              style={{
                                borderColor: tableBorder,
                                backgroundColor: tableCellBg,
                                color: tableCellText,
                              }}
                            >
                              {formatNumber(Math.round(portfolioTotal[ft.key]))}
                            </td>
                          ))}
                          <td 
                            className="failure-col border p-1 text-center"
                            style={{
                              borderColor: tableBorder,
                              backgroundColor: tableCellBg,
                              color: tableCellText,
                            }}
                          >
                            {formatNumber(Math.round(portfolioTotal.total))}
                          </td>
                        </tr>

                        {/* Asset Rows */}
                        {Object.entries(assets).map(([asset, vals]) => {
                          if (!portfolioExpanded) return null;

                          return (
                            <tr
                              key={`${portfolioId}-asset-${asset}`}
                              className="asset-row border-b"
                              style={{ 
                                display: portfolioExpanded ? '' : 'none',
                                borderColor: tableBorder,
                                backgroundColor: tableCellBg,
                              }}
                            >
                              <td 
                                className="border p-1"
                                style={{
                                  borderColor: tableBorder,
                                  color: tableCellText,
                                }}
                              />
                              <td 
                                className="border p-1"
                                style={{
                                  borderColor: tableBorder,
                                  color: tableCellText,
                                }}
                              />
                              <td 
                                className="border p-1 text-left"
                                style={{
                                  borderColor: tableBorder,
                                  backgroundColor: assetHeaderBg,
                                  color: assetHeaderText,
                                }}
                              >
                                {asset}
                              </td>
                              {FAILURE_TYPES.map((ft) => {
                                const value = Math.round(vals[ft.key] || 0);
                                const max = maxFailure[ft.key] || 1;
                                let width = max > 0 ? (Math.abs(value) / max) * 100 : 0;
                                width = Math.max(width, value > 0 ? 10 : 0); // Minimum 10% for nonzero

                                return (
                                  <td
                                    key={ft.key}
                                    className={`breakdown-bar-cell failure-col failure-col-${ft.cls} relative border p-1 text-center`}
                                    style={{
                                      borderColor: tableBorder,
                                      color: tableCellText,
                                    }}
                                  >
                                    <div
                                      className="bar-indicator-bg absolute left-0 top-0 h-full"
                                      style={{
                                        width: `${width}%`,
                                        backgroundColor: ft.color,
                                        zIndex: 0,
                                      }}
                                    />
                                    <span className="bar-indicator-value relative z-10">{formatNumber(value)}</span>
                                  </td>
                                );
                              })}
                              <td 
                                className="failure-col border p-1 text-center"
                                style={{
                                  borderColor: tableBorder,
                                  color: tableCellText,
                                }}
                              >
                                {formatNumber(Math.round(vals.total))}
                              </td>
                            </tr>
                          );
                        })}
                      </Fragment>
                    );
                  })}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
