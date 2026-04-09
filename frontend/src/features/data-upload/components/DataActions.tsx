/**
 * Data Actions Component - React Style V1
 */
 
import { useState } from 'react';
import { DataPreviewModal } from './DataPreviewModal';
import { DeleteDataModal } from './DeleteDataModal';
import { DownloadDataModal } from './DownloadDataModal';
import { useTheme } from '../../../contexts/ThemeContext';

interface DataActionsProps {
  onRefreshCounts: () => void;
}

export function DataActions({ onRefreshCounts }: DataActionsProps) {
  const { theme } = useTheme();
  const [showPreview, setShowPreview] = useState(false);
  const [showDelete, setShowDelete] = useState(false);
  const [showDownload, setShowDownload] = useState(false);

  // Theme-aware colors
  const textPrimary = theme === 'dark' ? '#f1f5f9' : '#1a1a1a';
  const refreshButtonBg = theme === 'dark' ? 'rgba(56, 189, 248, 0.3)' : 'rgba(59, 130, 246, 0.15)';
  const refreshButtonBorder = theme === 'dark' ? 'rgba(56, 189, 248, 0.5)' : 'rgba(59, 130, 246, 0.5)';
  const refreshButtonText = theme === 'dark' ? '#7dd3fc' : '#1e40af';
  const refreshButtonHoverBg = theme === 'dark' ? 'rgba(56, 189, 248, 0.5)' : 'rgba(59, 130, 246, 0.25)';
  const previewButtonBg = theme === 'dark' ? 'rgba(250, 204, 21, 0.3)' : 'rgba(250, 204, 21, 0.15)';
  const previewButtonBorder = theme === 'dark' ? 'rgba(250, 204, 21, 0.5)' : 'rgba(250, 204, 21, 0.5)';
  const previewButtonText = theme === 'dark' ? '#fde047' : '#a16207';
  const previewButtonHoverBg = theme === 'dark' ? 'rgba(250, 204, 21, 0.5)' : 'rgba(250, 204, 21, 0.25)';
  const downloadButtonBg = theme === 'dark' ? 'rgba(34, 197, 94, 0.3)' : 'rgba(34, 197, 94, 0.15)';
  const downloadButtonBorder = theme === 'dark' ? 'rgba(34, 197, 94, 0.5)' : 'rgba(34, 197, 94, 0.5)';
  const downloadButtonText = theme === 'dark' ? '#86efac' : '#15803d';
  const downloadButtonHoverBg = theme === 'dark' ? 'rgba(34, 197, 94, 0.5)' : 'rgba(34, 197, 94, 0.25)';
  const deleteButtonBg = theme === 'dark' ? 'rgba(248, 113, 113, 0.3)' : 'rgba(239, 68, 68, 0.15)';
  const deleteButtonBorder = theme === 'dark' ? 'rgba(248, 113, 113, 0.5)' : 'rgba(239, 68, 68, 0.5)';
  const deleteButtonText = theme === 'dark' ? '#fca5a5' : '#dc2626';
  const deleteButtonHoverBg = theme === 'dark' ? 'rgba(248, 113, 113, 0.5)' : 'rgba(239, 68, 68, 0.25)';

  return (
    <>
      <div className="space-y-2">
        <h6 className="text-xs font-bold" style={{ color: textPrimary }}>Data Actions</h6>
        <div className="grid grid-cols-2 gap-2">
          <button
            className="rounded-lg border px-3 py-1.5 text-[10px] font-semibold transition"
            style={{
              borderColor: refreshButtonBorder,
              backgroundColor: refreshButtonBg,
              color: refreshButtonText,
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = refreshButtonHoverBg;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = refreshButtonBg;
            }}
            onClick={onRefreshCounts}
          >
            🔄 Refresh Counts
          </button>
          <button
            className="rounded-lg border px-3 py-1.5 text-[10px] font-semibold transition"
            style={{
              borderColor: previewButtonBorder,
              backgroundColor: previewButtonBg,
              color: previewButtonText,
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = previewButtonHoverBg;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = previewButtonBg;
            }}
            onClick={() => setShowPreview(true)}
          >
            👁️ Preview Data
          </button>
          <button
            className="rounded-lg border px-3 py-1.5 text-[10px] font-semibold transition"
            style={{
              borderColor: downloadButtonBorder,
              backgroundColor: downloadButtonBg,
              color: downloadButtonText,
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = downloadButtonHoverBg;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = downloadButtonBg;
            }}
            onClick={() => setShowDownload(true)}
          >
            📥 Download Data
          </button>
          <button
            className="rounded-lg border px-3 py-1.5 text-[10px] font-semibold transition"
            style={{
              borderColor: deleteButtonBorder,
              backgroundColor: deleteButtonBg,
              color: deleteButtonText,
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = deleteButtonHoverBg;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = deleteButtonBg;
            }}
            onClick={() => setShowDelete(true)}
          >
            🗑️ Delete Data
          </button>
        </div>
      </div>

      {showPreview && <DataPreviewModal onClose={() => setShowPreview(false)} />}
      {showDelete && (
        <DeleteDataModal
          onClose={() => setShowDelete(false)}
          onSuccess={onRefreshCounts}
        />
      )}
      {showDownload && <DownloadDataModal onClose={() => setShowDownload(false)} />}
    </>
  );
}

