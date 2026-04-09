/**
 * Upload History Component - React Style V1
 */
 
import { useEffect, useState } from 'react';
import { fetchUploadHistory } from '../api';
import type { UploadHistoryItem } from '../types';
import { useTheme } from '../../../contexts/ThemeContext';

export function UploadHistory() {
  const { theme } = useTheme();
  const [history, setHistory] = useState<UploadHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isExpanded, setIsExpanded] = useState(false);

  // Theme-aware colors
  const textPrimary = theme === 'dark' ? '#f1f5f9' : '#1a1a1a';
  const textTertiary = theme === 'dark' ? '#64748b' : '#94a3b8';
  const buttonBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.5)' : 'rgba(255, 255, 255, 0.9)';
  const buttonBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : 'rgba(203, 213, 225, 0.8)';
  const buttonText = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';
  const buttonHoverBorder = theme === 'dark' ? '#38bdf8' : '#0072ce';
  const buttonHoverBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.8)' : 'rgba(248, 250, 252, 0.9)';
  const spinnerBorder = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';
  const tableBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.6)' : 'rgba(255, 255, 255, 0.9)';
  const tableBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : 'rgba(203, 213, 225, 0.7)';
  const tableHeaderBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.5)' : 'rgba(241, 245, 249, 0.9)';
  const tableHeaderBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : 'rgba(203, 213, 225, 0.7)';
  const tableHeaderText = theme === 'dark' ? '#cbd5e1' : '#475569';
  const tableRowText = theme === 'dark' ? '#cbd5e1' : '#1a1a1a';
  const tableRowHoverBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.3)' : 'rgba(248, 250, 252, 0.9)';
  const tableDivider = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(203, 213, 225, 0.8)';
  const badgeBg = theme === 'dark' ? 'rgba(51, 65, 85, 0.5)' : 'rgba(241, 245, 249, 0.9)';
  const badgeText = theme === 'dark' ? '#cbd5e1' : '#475569';
  const successText = theme === 'dark' ? '#38bdf8' : '#0072ce';
  const errorText = theme === 'dark' ? '#f87171' : '#dc2626';
  const warningText = theme === 'dark' ? '#fbbf24' : '#d97706';

  const loadHistory = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchUploadHistory();
      setHistory(data.uploads || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load upload history');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadHistory();
  }, []);

  const getStatusColor = (status: string): string => {
    if (status === 'success') return successText;
    if (status === 'failed') return errorText;
    return warningText;
  };

  const getStatusIcon = (status: string): string => {
    if (status === 'success') return '✅';
    if (status === 'failed') return '❌';
    return '⚠️';
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h6 className="text-xs font-bold" style={{ color: textPrimary }}>Upload History</h6>
          <button
            className="rounded-lg border px-1.5 py-0.5 text-[10px] font-semibold transition hover:opacity-80"
            style={{
              borderColor: buttonBorder,
              backgroundColor: buttonBg,
              color: buttonText,
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = buttonHoverBorder;
              e.currentTarget.style.backgroundColor = buttonHoverBg;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = buttonBorder;
              e.currentTarget.style.backgroundColor = buttonBg;
            }}
            onClick={() => setIsExpanded(!isExpanded)}
            title={isExpanded ? 'Collapse table' : 'Expand table'}
          >
            {isExpanded ? '▲' : '▼'}
          </button>
        </div>
        <button
          className="rounded-lg border px-2 py-1 text-[10px] font-semibold transition disabled:cursor-not-allowed disabled:opacity-50"
          style={{
            borderColor: buttonBorder,
            backgroundColor: buttonBg,
            color: buttonText,
          }}
          onMouseEnter={(e) => {
            if (!e.currentTarget.disabled) {
              e.currentTarget.style.borderColor = buttonHoverBorder;
              e.currentTarget.style.backgroundColor = buttonHoverBg;
            }
          }}
          onMouseLeave={(e) => {
            if (!e.currentTarget.disabled) {
              e.currentTarget.style.borderColor = buttonBorder;
              e.currentTarget.style.backgroundColor = buttonBg;
            }
          }}
          onClick={loadHistory}
          disabled={loading}
        >
          {loading ? (
            <span 
              className="inline-block size-3 animate-spin rounded-full border-2 border-t-transparent"
              style={{
                borderColor: spinnerBorder,
              }}
            ></span>
          ) : (
            '🔄 Refresh'
          )}
        </button>
      </div>
      {isExpanded && (
        <div 
          className="overflow-x-auto rounded-lg border"
          style={{
            borderColor: tableBorder,
            backgroundColor: tableBg,
          }}
        >
        <table className="w-full text-[10px]" style={{ color: tableRowText }}>
          <thead 
            className="border-b"
            style={{
              borderColor: tableHeaderBorder,
              backgroundColor: tableHeaderBg,
            }}
          >
            <tr>
              <th className="px-2 py-1.5 text-left font-semibold" style={{ color: tableHeaderText }}>Date</th>
              <th className="px-2 py-1.5 text-left font-semibold" style={{ color: tableHeaderText }}>File</th>
              <th className="px-2 py-1.5 text-left font-semibold" style={{ color: tableHeaderText }}>Type</th>
              <th className="px-2 py-1.5 text-left font-semibold" style={{ color: tableHeaderText }}>Status</th>
              <th className="px-2 py-1.5 text-left font-semibold" style={{ color: tableHeaderText }}>Records</th>
              <th className="px-2 py-1.5 text-left font-semibold" style={{ color: tableHeaderText }}>User</th>
            </tr>
          </thead>
          <tbody style={{ borderColor: tableDivider }}>
            {loading ? (
              <tr>
                <td colSpan={6} className="px-2 py-3 text-center" style={{ color: textTertiary }}>
                  Loading...
                </td>
              </tr>
            ) : error ? (
              <tr>
                <td colSpan={6} className="px-2 py-3 text-center" style={{ color: errorText }}>
                  {error}
                </td>
              </tr>
            ) : history.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-2 py-3 text-center" style={{ color: textTertiary }}>
                  No upload history found
                </td>
              </tr>
            ) : (
              history.map((upload, index) => (
                <tr 
                  key={index}
                  style={{
                    borderTop: index > 0 ? `1px solid ${tableDivider}` : 'none',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.backgroundColor = tableRowHoverBg;
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = 'transparent';
                  }}
                >
                  <td className="px-2 py-1.5">{upload.import_date || 'N/A'}</td>
                  <td className="px-2 py-1.5" style={{ color: tableRowText }}>{upload.file_name}</td>
                  <td className="px-2 py-1.5">
                    <span 
                      className="rounded px-1.5 py-0.5 text-[9px]"
                      style={{
                        backgroundColor: badgeBg,
                        color: badgeText,
                      }}
                    >
                      {upload.data_type}
                    </span>
                  </td>
                  <td className="px-2 py-1.5" style={{ color: getStatusColor(upload.status) }}>
                    {getStatusIcon(upload.status)} {upload.status}
                  </td>
                  <td className="px-2 py-1.5" style={{ color: tableRowText }}>
                    {upload.records_imported} imported, {upload.records_skipped} skipped
                  </td>
                  <td className="px-2 py-1.5" style={{ color: tableRowText }}>{upload.imported_by}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
        </div>
      )}
    </div>
  );
}

