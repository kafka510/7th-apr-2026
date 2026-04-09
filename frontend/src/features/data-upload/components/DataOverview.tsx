/**
 * Data Overview Component - React Style V1
 */
 
import { useEffect, useState } from 'react';
import { fetchDataCounts } from '../api';
import type { DataCounts } from '../types';
import { DataActions } from './DataActions';
import { UploadHistory } from './UploadHistory';
import { useTheme } from '../../../contexts/ThemeContext';

interface DataOverviewProps {
  onRefresh?: () => void;
}

export function DataOverview({ onRefresh }: DataOverviewProps) {
  const { theme } = useTheme();
  const [counts, setCounts] = useState<DataCounts | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Theme-aware colors
  const cardBg = theme === 'dark' 
    ? 'linear-gradient(to bottom right, rgba(30, 41, 59, 0.9), rgba(51, 65, 85, 0.6))'
    : 'linear-gradient(to bottom right, rgba(255, 255, 255, 0.95), rgba(248, 250, 252, 0.9))';
  const cardBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(203, 213, 225, 0.8)';
  const textPrimary = theme === 'dark' ? '#f1f5f9' : '#1a1a1a';
  const textTertiary = theme === 'dark' ? '#64748b' : '#94a3b8';
  const buttonBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.5)' : 'rgba(255, 255, 255, 0.9)';
  const buttonBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : 'rgba(203, 213, 225, 0.8)';
  const buttonText = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';
  const buttonHoverBorder = theme === 'dark' ? '#38bdf8' : '#0072ce';
  const buttonHoverBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.8)' : 'rgba(248, 250, 252, 0.9)';
  const spinnerBorder = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';
  const spinnerColor = theme === 'dark' ? '#38bdf8' : '#0072ce';
  const errorBorder = theme === 'dark' ? 'rgba(248, 113, 113, 0.5)' : 'rgba(239, 68, 68, 0.5)';
  const errorBg = theme === 'dark' ? 'rgba(248, 113, 113, 0.2)' : 'rgba(239, 68, 68, 0.1)';
  const errorText = theme === 'dark' ? '#fca5a5' : '#dc2626';
  const statCardBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.8)' : 'rgba(255, 255, 255, 0.9)';
  const statCardBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : 'rgba(203, 213, 225, 0.7)';
  const statLabelText = theme === 'dark' ? '#cbd5e1' : '#475569';
  const statValueText = theme === 'dark' ? '#38bdf8' : '#0072ce';

  const loadCounts = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchDataCounts();
      setCounts(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data counts');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCounts();
  }, []);

  useEffect(() => {
    if (onRefresh) {
      // Re-expose refresh function if needed
    }
  }, [onRefresh]);

  const formatCount = (count: number | undefined): string => {
    if (count === undefined) return 'N/A';
    return new Intl.NumberFormat().format(count);
  };

  return (
    <div 
      className="flex h-full flex-col gap-3 rounded-xl border p-3 shadow-xl"
      style={{
        borderColor: cardBorder,
        background: cardBg,
      }}
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <h5 className="text-sm font-bold" style={{ color: textPrimary }}>🗂️ Data Overview & Actions</h5>
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
          onClick={loadCounts}
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

      {/* Data Overview */}
      <div className="space-y-2">
        <h6 className="text-xs font-bold" style={{ color: textPrimary }}>Data Overview</h6>
        {loading ? (
          <div className="py-4 text-center">
            <div 
              className="inline-block size-4 animate-spin rounded-full border-2 border-t-transparent"
              style={{
                borderColor: spinnerColor,
              }}
            ></div>
            <span className="ml-2 text-xs" style={{ color: textTertiary }}>Loading...</span>
          </div>
        ) : error ? (
          <div 
            className="rounded-lg border px-3 py-2"
            style={{
              borderColor: errorBorder,
              backgroundColor: errorBg,
            }}
          >
            <span className="text-xs font-medium" style={{ color: errorText }}>Error: {error}</span>
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-2 lg:grid-cols-3">
            <div 
              className="rounded-lg border p-2 text-center"
              style={{
                borderColor: statCardBorder,
                backgroundColor: statCardBg,
              }}
            >
              <h6 className="mb-1 text-[9px] font-semibold" style={{ color: statLabelText }}>Yield Data</h6>
              <p className="text-sm font-bold" style={{ color: statValueText }}>{formatCount(counts?.yield_count)}</p>
            </div>
            <div 
              className="rounded-lg border p-2 text-center"
              style={{
                borderColor: statCardBorder,
                backgroundColor: statCardBg,
              }}
            >
              <h6 className="mb-1 text-[9px] font-semibold" style={{ color: statLabelText }}>BESS Data</h6>
              <p className="text-sm font-bold" style={{ color: statValueText }}>{formatCount(counts?.bess_count)}</p>
            </div>
            <div 
              className="rounded-lg border p-2 text-center"
              style={{
                borderColor: statCardBorder,
                backgroundColor: statCardBg,
              }}
            >
              <h6 className="mb-1 text-[9px] font-semibold" style={{ color: statLabelText }}>BESS V1 Data</h6>
              <p className="text-sm font-bold" style={{ color: statValueText }}>{formatCount(counts?.bess_v1_count)}</p>
            </div>
            <div 
              className="rounded-lg border p-2 text-center"
              style={{
                borderColor: statCardBorder,
                backgroundColor: statCardBg,
              }}
            >
              <h6 className="mb-1 text-[9px] font-semibold" style={{ color: statLabelText }}>AOC Data</h6>
              <p className="text-sm font-bold" style={{ color: statValueText }}>{formatCount(counts?.aoc_count)}</p>
            </div>
            <div 
              className="rounded-lg border p-2 text-center"
              style={{
                borderColor: statCardBorder,
                backgroundColor: statCardBg,
              }}
            >
              <h6 className="mb-1 text-[9px] font-semibold" style={{ color: statLabelText }}>Map Data</h6>
              <p className="text-sm font-bold" style={{ color: statValueText }}>{formatCount(counts?.map_count)}</p>
            </div>
          </div>
        )}
      </div>

      {/* Data Actions */}
      <DataActions onRefreshCounts={loadCounts} />

      {/* Upload History */}
      <UploadHistory />
    </div>
  );
}

