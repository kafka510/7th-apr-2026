import { useMemo } from 'react';
import { useTheme } from '../../../contexts/ThemeContext';
import type { TicketListItem, TicketListFilters } from '../types';
import { useResponsiveFontSize } from '../../../utils/fontScaling';

type TicketTableProps = {
  items: TicketListItem[];
  loading?: boolean;
  sort?: string;
  order?: 'asc' | 'desc';
  onSortChange: (sort: string, order: 'asc' | 'desc') => void;
  onRowClick?: (ticket: TicketListItem) => void;
  selectedIds?: Set<string>;
  onSelectChange?: (ticketId: string, selected: boolean) => void;
  canDelete?: boolean;
  page?: number;
  pageSize?: number;
  filters?: TicketListFilters | null;
};

const headers: Array<{ key: string; label: string; align?: 'left' | 'right' }> = [
  { key: 'sno', label: 'S No' },
  { key: 'ticket_number', label: 'Ticket' },
  { key: 'title', label: 'Title' },
  { key: 'status', label: 'Status' },
  { key: 'priority', label: 'Priority' },
  { key: 'category', label: 'Category' },
  { key: 'asset_number', label: 'Asset Number' },
  { key: 'assignee', label: 'Assignee' },
];

const renderSkeletonRows = (hasCheckbox: boolean, theme: 'light' | 'dark', tableBodyBg: string, tableBodyText: string) => {
  const skeletonBg = theme === 'dark' ? 'rgba(71, 85, 105, 0.7)' : 'rgba(203, 213, 225, 0.7)';
  return Array.from({ length: 5 }).map((_, index) => (
    <tr 
      key={`loading-row-${index}`}
      style={{
        backgroundColor: tableBodyBg,
        color: tableBodyText,
      }}
    >
      {hasCheckbox && <td className="px-3 py-2"><div className="size-4 animate-pulse rounded" style={{ backgroundColor: skeletonBg }} /></td>}
      {headers.map((header) => (
        <td key={header.key} className="px-3 py-2">
          <div className="h-4 animate-pulse rounded" style={{ backgroundColor: skeletonBg }} />
        </td>
      ))}
    </tr>
  ));
};

export const TicketTable = ({
  items,
  loading,
  sort,
  order = 'asc',
  onSortChange,
  onRowClick,
  selectedIds = new Set(),
  onSelectChange,
  canDelete = false,
  page = 1,
  pageSize = 20,
  filters,
}: TicketTableProps) => {
  const { theme } = useTheme();
  
  // Responsive font sizes
  const headerFontSize = useResponsiveFontSize(10, 14, 9);
  const bodyFontSize = useResponsiveFontSize(10, 14, 9);
  const smallFontSize = useResponsiveFontSize(9, 13, 8);
  const badgeFontSize = useResponsiveFontSize(9, 13, 8);
  
  const containerBg = theme === 'dark'
    ? 'linear-gradient(to bottom right, rgba(15, 23, 42, 0.9), rgba(30, 41, 59, 0.6))'
    : 'linear-gradient(to bottom right, rgba(255, 255, 255, 0.95), rgba(248, 250, 252, 0.9))';
  const containerBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(203, 213, 225, 0.8)';
  const containerShadow = theme === 'dark' 
    ? '0 20px 25px -5px rgba(0, 0, 0, 0.4)' 
    : '0 10px 15px -3px rgba(0, 0, 0, 0.1)';
  const tableHeaderBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.8)' : 'rgba(241, 245, 249, 0.9)';
  const tableHeaderText = theme === 'dark' ? '#cbd5e1' : '#1a1a1a';
  const tableBodyBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.5)' : '#ffffff';
  const tableBodyText = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';
  const tableRowHoverBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.7)' : 'rgba(248, 250, 252, 0.9)';
  const tableDivider = theme === 'dark' ? 'rgba(51, 65, 85, 0.5)' : 'rgba(226, 232, 240, 0.8)';
  const checkboxBorder = theme === 'dark' ? 'rgba(100, 116, 139, 0.6)' : 'rgba(203, 213, 225, 0.8)';
  const checkboxBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.8)' : '#ffffff';
  const linkColor = theme === 'dark' ? '#60a5fa' : '#0072ce';
  const linkHoverColor = theme === 'dark' ? '#93c5fd' : '#0056a3';
  const sortButtonHoverText = theme === 'dark' ? '#60a5fa' : '#0072ce';
  const sortActiveText = theme === 'dark' ? '#60a5fa' : '#0072ce';
  const noDataText = theme === 'dark' ? '#94a3b8' : '#64748b';
  
  // Calculate starting serial number for current page
  const startSerialNumber = (page - 1) * pageSize + 1;

  // Create mapping from asset_code to asset_number
  // This connects asset_code from tickets to asset_number using site options and asset number options
  const assetCodeToAssetNumber = useMemo(() => {
    const map = new Map<string, string>();
    
    // Strategy 1: Map from siteOptions - if site has assetCode, try to find matching asset_number
    if (filters?.siteOptions && filters?.assetNumberOptions) {
      filters.siteOptions.forEach((site) => {
        if (site.assetCode) {
          // Try multiple matching strategies
          const matchingAssetNumber = filters.assetNumberOptions.find(
            (opt) => {
              // Match if site.value or site.label equals asset_number value/label
              return opt.value === site.value || 
                     opt.label === site.label ||
                     opt.value === site.assetCode ||
                     opt.label === site.assetCode ||
                     // Also check if site.value/label contains asset_code or vice versa
                     (site.value && opt.value && site.assetCode && opt.value.includes(site.assetCode)) ||
                     (site.label && opt.label && site.assetCode && opt.label.includes(site.assetCode));
            }
          );
          if (matchingAssetNumber) {
            map.set(site.assetCode, matchingAssetNumber.value);
          }
        }
      });
    }
    
    // Strategy 2: Direct mapping - if ticket's asset_code matches an asset_number in options
    if (filters?.assetNumberOptions && items.length > 0) {
      items.forEach((ticket) => {
        if (ticket.asset_code) {
          const assetCodeTrimmed = ticket.asset_code.trim();
          const matchingOption = filters.assetNumberOptions?.find(
            (opt) => opt.value === assetCodeTrimmed || 
                     opt.label === assetCodeTrimmed ||
                     opt.value === assetCodeTrimmed ||
                     opt.label === assetCodeTrimmed
          );
          if (matchingOption) {
            map.set(assetCodeTrimmed, matchingOption.value);
          }
        }
      });
    }
    
    // Strategy 3: If assetNumberOptions is populated from tickets, use those mappings
    // (This handles the case where assetNumberOptions were extracted from ticket items)
    if (filters?.assetNumberOptions) {
      filters.assetNumberOptions.forEach((option) => {
        // If option value matches any ticket's asset_code, create mapping
        items.forEach((ticket) => {
          if (ticket.asset_code && (ticket.asset_code === option.value || ticket.asset_code === option.label)) {
            map.set(ticket.asset_code, option.value);
          }
        });
      });
    }
    
    return map;
  }, [filters, items]);

  // Helper function to get asset_number for a ticket
  const getAssetNumber = (ticket: TicketListItem): string | null => {
    // Priority 1: Use asset_number if backend provides it directly
    if (ticket.asset_number?.trim()) {
      return ticket.asset_number.trim();
    }
    
    // Priority 2: Try to map from asset_code using our mapping
    if (ticket.asset_code?.trim()) {
      const assetCodeTrimmed = ticket.asset_code.trim();
      
      // Check if we have a mapping from assetCodeToAssetNumber
      if (assetCodeToAssetNumber.has(assetCodeTrimmed)) {
        const mappedValue = assetCodeToAssetNumber.get(assetCodeTrimmed);
        if (mappedValue) {
          return mappedValue;
        }
      }
      
      // Priority 3: Check if asset_code itself exists in assetNumberOptions
      // (In some systems, asset_code IS the asset_number)
      if (filters?.assetNumberOptions && filters.assetNumberOptions.length > 0) {
        const matchingOption = filters.assetNumberOptions.find(
          (opt) => opt.value === assetCodeTrimmed || opt.label === assetCodeTrimmed
        );
        if (matchingOption) {
          return matchingOption.value;
        }
        
        // Also check if any asset_number option contains this asset_code
        const partialMatch = filters.assetNumberOptions.find(
          (opt) => opt.value.includes(assetCodeTrimmed) || assetCodeTrimmed.includes(opt.value)
        );
        if (partialMatch) {
          return partialMatch.value;
        }
      }
      
      // Priority 4: If assetNumberOptions is populated from tickets (enriched filters),
      // and asset_code matches one of those values, use asset_code as asset_number
      // This handles the case where asset_code values were extracted as asset_number options
      if (filters?.assetNumberOptions && filters.assetNumberOptions.length > 0) {
        // Check if this asset_code was used to populate assetNumberOptions
        const isInOptions = filters.assetNumberOptions.some(
          (opt) => opt.value === assetCodeTrimmed || opt.label === assetCodeTrimmed
        );
        if (isInOptions) {
          return assetCodeTrimmed;
        }
      }
    }
    
    // No asset_number found - backend should populate this field
    return null;
  };
  // Helper function to get status badge styles
  const getStatusBadgeStyles = (status: string) => {
    const baseStyles: Record<string, { border: string; bg: string; text: string }> = {
      raised: {
        border: theme === 'dark' ? 'rgba(59, 130, 246, 0.5)' : 'rgba(59, 130, 246, 0.7)',
        bg: theme === 'dark' ? 'rgba(59, 130, 246, 0.2)' : 'rgba(59, 130, 246, 0.1)',
        text: theme === 'dark' ? '#93c5fd' : '#1e40af',
      },
      in_progress: {
        border: theme === 'dark' ? 'rgba(245, 158, 11, 0.5)' : 'rgba(245, 158, 11, 0.7)',
        bg: theme === 'dark' ? 'rgba(245, 158, 11, 0.2)' : 'rgba(245, 158, 11, 0.1)',
        text: theme === 'dark' ? '#fcd34d' : '#d97706',
      },
      submitted: {
        border: theme === 'dark' ? 'rgba(99, 102, 241, 0.5)' : 'rgba(99, 102, 241, 0.7)',
        bg: theme === 'dark' ? 'rgba(99, 102, 241, 0.2)' : 'rgba(99, 102, 241, 0.1)',
        text: theme === 'dark' ? '#a5b4fc' : '#4338ca',
      },
      waiting_for_approval: {
        border: theme === 'dark' ? 'rgba(245, 158, 11, 0.5)' : 'rgba(245, 158, 11, 0.7)',
        bg: theme === 'dark' ? 'rgba(245, 158, 11, 0.2)' : 'rgba(245, 158, 11, 0.1)',
        text: theme === 'dark' ? '#fcd34d' : '#d97706',
      },
      reopened: {
        border: theme === 'dark' ? 'rgba(217, 70, 239, 0.5)' : 'rgba(217, 70, 239, 0.7)',
        bg: theme === 'dark' ? 'rgba(217, 70, 239, 0.2)' : 'rgba(217, 70, 239, 0.1)',
        text: theme === 'dark' ? '#f0abfc' : '#a21caf',
      },
      closed: {
        border: theme === 'dark' ? 'rgba(16, 185, 129, 0.5)' : 'rgba(16, 185, 129, 0.7)',
        bg: theme === 'dark' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(16, 185, 129, 0.1)',
        text: theme === 'dark' ? '#6ee7b7' : '#059669',
      },
      cancelled: {
        border: theme === 'dark' ? 'rgba(51, 65, 85, 0.6)' : 'rgba(148, 163, 184, 0.7)',
        bg: theme === 'dark' ? 'rgba(51, 65, 85, 0.2)' : 'rgba(203, 213, 225, 0.3)',
        text: theme === 'dark' ? '#cbd5e1' : '#475569',
      },
    };
    return baseStyles[status] || {
      border: theme === 'dark' ? 'rgba(51, 65, 85, 0.6)' : 'rgba(148, 163, 184, 0.7)',
      bg: theme === 'dark' ? 'rgba(51, 65, 85, 0.2)' : 'rgba(203, 213, 225, 0.3)',
      text: theme === 'dark' ? '#cbd5e1' : '#475569',
    };
  };

  // Helper function to get priority badge styles
  const getPriorityBadgeStyles = (priority: string) => {
    const baseStyles: Record<string, { border: string; bg: string; text: string }> = {
      low: {
        border: theme === 'dark' ? 'rgba(16, 185, 129, 0.5)' : 'rgba(16, 185, 129, 0.7)',
        bg: theme === 'dark' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(16, 185, 129, 0.1)',
        text: theme === 'dark' ? '#6ee7b7' : '#059669',
      },
      medium: {
        border: theme === 'dark' ? 'rgba(59, 130, 246, 0.5)' : 'rgba(59, 130, 246, 0.7)',
        bg: theme === 'dark' ? 'rgba(59, 130, 246, 0.2)' : 'rgba(59, 130, 246, 0.1)',
        text: theme === 'dark' ? '#93c5fd' : '#1e40af',
      },
      high: {
        border: theme === 'dark' ? 'rgba(245, 158, 11, 0.5)' : 'rgba(245, 158, 11, 0.7)',
        bg: theme === 'dark' ? 'rgba(245, 158, 11, 0.2)' : 'rgba(245, 158, 11, 0.1)',
        text: theme === 'dark' ? '#fcd34d' : '#d97706',
      },
      critical: {
        border: theme === 'dark' ? 'rgba(244, 63, 94, 0.5)' : 'rgba(244, 63, 94, 0.7)',
        bg: theme === 'dark' ? 'rgba(244, 63, 94, 0.2)' : 'rgba(244, 63, 94, 0.1)',
        text: theme === 'dark' ? '#fca5a5' : '#dc2626',
      },
    };
    return baseStyles[priority] || {
      border: theme === 'dark' ? 'rgba(51, 65, 85, 0.6)' : 'rgba(148, 163, 184, 0.7)',
      bg: theme === 'dark' ? 'rgba(51, 65, 85, 0.2)' : 'rgba(203, 213, 225, 0.3)',
      text: theme === 'dark' ? '#cbd5e1' : '#475569',
    };
  };

  const categoryBadgeBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.6)' : 'rgba(241, 245, 249, 0.9)';
  const categoryBadgeBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : 'rgba(203, 213, 225, 0.8)';
  const categoryBadgeText = theme === 'dark' ? '#cbd5e1' : '#475569';

  return (
    <div 
      className="rounded-xl border shadow-xl"
      style={{
        borderColor: containerBorder,
        background: containerBg,
        boxShadow: containerShadow,
      }}
    >
      <div className="overflow-x-auto">
        <table 
          className="min-w-full divide-y text-xs" 
          style={{ 
            minWidth: '100%',
            borderColor: tableDivider,
          }}
        >
        <thead style={{ backgroundColor: tableHeaderBg }}>
          <tr>
            {canDelete && onSelectChange && (
              <th 
                className="px-3 py-2 text-left font-semibold uppercase tracking-wide"
                style={{ color: tableHeaderText, fontSize: `${headerFontSize}px` }}
              >
                <input
                  type="checkbox"
                  checked={items.length > 0 && items.every((item) => selectedIds.has(item.id))}
                  onChange={(e) => {
                    items.forEach((item) => {
                      onSelectChange(item.id, e.target.checked);
                    });
                  }}
                  className="size-4 rounded focus:ring-2"
                  style={{
                    borderColor: checkboxBorder,
                    backgroundColor: checkboxBg,
                    accentColor: theme === 'dark' ? '#60a5fa' : '#0072ce',
                  }}
                />
              </th>
            )}
            {headers.map((header) => {
              const isSortable = ['ticket_number', 'status', 'priority'].includes(
                header.key,
              );
              const isActive = sort === header.key;
              const isSerialNumber = header.key === 'sno';

              return (
                <th
                  key={header.key}
                  className={`px-3 py-2 text-left font-semibold uppercase tracking-wide ${
                    header.align === 'right' ? 'text-right' : ''
                  }`}
                  style={{ color: tableHeaderText, fontSize: `${headerFontSize}px` }}
                >
                  {isSerialNumber ? (
                    <span>{header.label}</span>
                  ) : (
                    <button
                      type="button"
                      disabled={!isSortable}
                      onClick={() => {
                        if (!isSortable) return;
                        const nextOrder = isActive && order === 'asc' ? 'desc' : 'asc';
                        onSortChange(header.key, nextOrder);
                      }}
                      className={`inline-flex items-center gap-0.5 ${
                        isSortable ? 'rounded-lg px-1 py-0.5 transition focus-visible:outline-none focus-visible:ring-1' : ''
                      }`}
                      style={{
                        color: tableHeaderText,
                      }}
                      onMouseEnter={(e) => {
                        if (isSortable) {
                          e.currentTarget.style.color = sortButtonHoverText;
                        }
                      }}
                      onMouseLeave={(e) => {
                        if (isSortable && !isActive) {
                          e.currentTarget.style.color = tableHeaderText;
                        }
                      }}
                    >
                      {header.label}
                      {isSortable ? (
                        <span
                          className="transition"
                          style={{
                            color: isActive ? sortActiveText : tableHeaderText,
                            opacity: isActive ? 1 : 0.3,
                            fontSize: `${smallFontSize}px`,
                          }}
                        >
                          {isActive ? (order === 'asc' ? '▲' : '▼') : '▲'}
                        </span>
                      ) : null}
                    </button>
                  )}
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody 
          className="divide-y"
          style={{ 
            borderColor: tableDivider,
            backgroundColor: tableBodyBg,
            color: tableBodyText,
          }}
        >
          {loading
            ? renderSkeletonRows(canDelete && !!onSelectChange, theme, tableBodyBg, tableBodyText)
            : items.length === 0
            ? [
                <tr 
                  key="empty-state"
                  style={{
                    backgroundColor: tableBodyBg,
                    color: tableBodyText,
                  }}
                >
                  <td 
                    colSpan={headers.length + (canDelete && onSelectChange ? 1 : 0)} 
                    className="px-3 py-6 text-center text-xs"
                    style={{ color: noDataText }}
                  >
                    No tickets match the current filters. Adjust filters or refresh the data.
                  </td>
                </tr>,
              ]
            : items.map((ticket, index) => {
                const statusStyles = getStatusBadgeStyles(ticket.status);
                const priorityStyles = getPriorityBadgeStyles(ticket.priority);
                const serialNumber = startSerialNumber + index;

                return (
                  <tr
                    key={ticket.id}
                    className="cursor-pointer transition"
                    style={{
                      borderColor: tableDivider,
                      backgroundColor: tableBodyBg,
                      color: tableBodyText,
                    }}
                    onClick={(e) => {
                      // Don't trigger row click if clicking checkbox
                      if ((e.target as HTMLElement).closest('input[type="checkbox"]')) {
                        return;
                      }
                      onRowClick?.(ticket);
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.backgroundColor = tableRowHoverBg;
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.backgroundColor = tableBodyBg;
                    }}
                  >
                    {canDelete && onSelectChange && (
                      <td className="px-3 py-2" onClick={(e) => e.stopPropagation()}>
                        <input
                          type="checkbox"
                          checked={selectedIds.has(ticket.id)}
                          onChange={(e) => {
                            e.stopPropagation();
                            onSelectChange(ticket.id, e.target.checked);
                          }}
                          className="size-3 rounded focus:ring-1"
                          style={{
                            borderColor: checkboxBorder,
                            backgroundColor: checkboxBg,
                            accentColor: theme === 'dark' ? '#60a5fa' : '#0072ce',
                          }}
                        />
                      </td>
                    )}
                    <td className="px-3 py-2">
                      <span className="text-xs font-medium" style={{ color: tableBodyText }}>{serialNumber}</span>
                    </td>
                    <td className="px-3 py-2">
                      <span 
                        className="text-xs font-semibold transition-colors"
                        style={{ color: linkColor }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.color = linkHoverColor;
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.color = linkColor;
                        }}
                      >
                        {ticket.ticket_number}
                      </span>
                    </td>
                    <td className="px-3 py-2">
                      <p 
                        className="min-w-[200px] whitespace-normal break-words text-xs" 
                        title={ticket.title}
                        style={{ color: tableBodyText }}
                      >
                        {ticket.title}
                      </p>
                    </td>
                    <td className="px-3 py-2">
                      <span
                        className="inline-flex items-center rounded-lg border px-2 py-0.5 font-semibold uppercase tracking-wide"
                        style={{
                          borderColor: statusStyles.border,
                          backgroundColor: statusStyles.bg,
                          color: statusStyles.text,
                          fontSize: `${badgeFontSize}px`,
                        }}
                      >
                        {ticket.status_display}
                      </span>
                    </td>
                    <td className="px-3 py-2">
                      <span
                        className="inline-flex items-center rounded-lg border px-2 py-0.5 font-semibold uppercase tracking-wide"
                        style={{
                          borderColor: priorityStyles.border,
                          backgroundColor: priorityStyles.bg,
                          color: priorityStyles.text,
                          fontSize: `${badgeFontSize}px`,
                        }}
                      >
                        {ticket.priority_display}
                      </span>
                    </td>
                    <td className="px-3 py-2">
                      {ticket.category ? (
                        <span 
                          className="rounded-lg border px-2 py-0.5 font-medium"
                          style={{
                            borderColor: categoryBadgeBorder,
                            backgroundColor: categoryBadgeBg,
                            color: categoryBadgeText,
                            fontSize: `${bodyFontSize}px`,
                          }}
                        >
                          {ticket.category}
                        </span>
                      ) : (
                        <span style={{ color: noDataText, fontSize: `${bodyFontSize}px` }}>—</span>
                      )}
                    </td>
                    <td className="px-3 py-2">
                      <div className="text-xs font-medium" style={{ color: tableBodyText }}>
                        {getAssetNumber(ticket) || '—'}
                      </div>
                    </td>
                    <td className="px-3 py-2">
                      <span className="text-xs" style={{ color: tableBodyText }}>{ticket.assigned_to || 'Unassigned'}</span>
                    </td>
                  </tr>
                );
              })}
        </tbody>
      </table>
      </div>
    </div>
  );
};

