/**
 * Data Upload Page Component - React Style V1
 */
 
import { useState, useEffect } from 'react';
import { uploadCSVFile } from './api';
import type { DataType, UploadMode } from './types';
import { UploadForm } from './components/UploadForm';
import { DataOverview } from './components/DataOverview';
import { useTheme } from '../../contexts/ThemeContext';
import { getGradientBg } from '../../utils/themeColors';
import { useFilterPersistence } from '../../hooks/useFilterPersistence';
import { loadFilters } from '../../utils/filterPersistence';

const DASHBOARD_ID = 'data-upload';

type LastUploadOptions = {
  dataType?: DataType;
  uploadMode?: UploadMode;
  startDate?: string;
  endDate?: string;
  skipDuplicates?: boolean;
  validateData?: boolean;
  batchSize?: number;
};

export function DataUpload() {
  const { theme } = useTheme();
  const [isUploading, setIsUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  // Persist last used upload options so downloads/export can restore state
  const [lastUploadOptions, setLastUploadOptions] = useState<LastUploadOptions>(() => {
    const stored = loadFilters<LastUploadOptions>(DASHBOARD_ID);
    if (stored && typeof stored === 'object') {
      return stored;
    }
    return {};
  });

  // Persist options globally (used by Playwright export)
  useFilterPersistence(DASHBOARD_ID, lastUploadOptions);

  const handleUpload = async (
    file: File,
    dataType: DataType,
    uploadMode: UploadMode,
    options?: {
      startDate?: string;
      endDate?: string;
      skipDuplicates?: boolean;
      validateData?: boolean;
      batchSize?: number;
    }
  ) => {
    try {
      setIsUploading(true);
      setUploadMessage(null);

      // Track latest options for persistence
      setLastUploadOptions({
        dataType,
        uploadMode,
        startDate: options?.startDate,
        endDate: options?.endDate,
        skipDuplicates: options?.skipDuplicates,
        validateData: options?.validateData,
        batchSize: options?.batchSize,
      });

      const result = await uploadCSVFile(file, dataType, uploadMode, options);

      if (result.success) {
        const stats = [
          `✅ Successfully processed ${file.name}`,
          `📊 Statistics: ${result.records_imported || 0} imported, ${result.records_updated || 0} updated, ${result.records_skipped || 0} skipped`,
        ];

        if (result.warnings && result.warnings.length > 0) {
          stats.push('⚠️ Warnings:');
          result.warnings.slice(0, 3).forEach((warning) => {
            stats.push(`  • ${warning}`);
          });
          if (result.warnings.length > 3) {
            stats.push(`  • ... and ${result.warnings.length - 3} more warnings`);
          }
        }

        setUploadMessage({
          type: 'success',
          message: stats.join('\n'),
        });
      } else {
        let errorMsg = `❌ Upload failed: ${result.error || 'Unknown error'}`;

        if (result.validation_details?.statistics) {
          const stats = result.validation_details.statistics;
          errorMsg += `\n📊 File Statistics: ${stats.total_rows} rows, ${stats.total_columns} columns`;
          if (stats.empty_rows > 0) {
            errorMsg += `\n⚠️ ${stats.empty_rows} empty rows found`;
          }
          if (stats.missing_data_count > 0) {
            errorMsg += `\n⚠️ ${stats.missing_data_count} missing values found`;
          }
        }

        setUploadMessage({
          type: 'error',
          message: errorMsg,
        });
      }
    } catch (error) {
      setUploadMessage({
        type: 'error',
        message: `❌ Error during upload: ${error instanceof Error ? error.message : 'Unknown error'}`,
      });
    } finally {
      setIsUploading(false);
    }
  };

  // Check if we're in an iframe - only show header if not in iframe
  const [showHeader, setShowHeader] = useState(false);

  useEffect(() => {
    // Only show header when page is NOT in iframe (same as old template)
    if (typeof window !== 'undefined' && window.self === window.top) {
      setShowHeader(true);
    }
  }, []);

  // Signal when Data Upload page is ready for export/download
  useEffect(() => {
    // For this management page, consider it "ready" when the component has mounted
    // and there is no active upload in progress.
    if (!isUploading) {
      document.body.setAttribute('data-filters-ready', 'true');
      window.dispatchEvent(
        new CustomEvent('dashboard-filters-ready', { detail: { dashboardId: DASHBOARD_ID } }),
      );
    } else {
      document.body.removeAttribute('data-filters-ready');
    }
  }, [isUploading]);

  // Theme-aware colors
  const bgGradient = getGradientBg(theme);
  const textPrimary = theme === 'dark' ? '#f1f5f9' : '#1a1a1a';
  const buttonBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.5)' : 'rgba(255, 255, 255, 0.9)';
  const buttonBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : 'rgba(203, 213, 225, 0.8)';
  const buttonText = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';
  const buttonHoverBorder = theme === 'dark' ? '#38bdf8' : '#0072ce';
  const buttonHoverBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.8)' : 'rgba(248, 250, 252, 0.9)';
  const successBorder = theme === 'dark' ? 'rgba(56, 189, 248, 0.5)' : 'rgba(59, 130, 246, 0.5)';
  const successBg = theme === 'dark' ? 'rgba(56, 189, 248, 0.2)' : 'rgba(59, 130, 246, 0.1)';
  const successText = theme === 'dark' ? '#7dd3fc' : '#1e40af';
  const errorBorder = theme === 'dark' ? 'rgba(248, 113, 113, 0.5)' : 'rgba(239, 68, 68, 0.5)';
  const errorBg = theme === 'dark' ? 'rgba(248, 113, 113, 0.2)' : 'rgba(239, 68, 68, 0.1)';
  const errorText = theme === 'dark' ? '#fca5a5' : '#dc2626';

  return (
    <div 
      className="flex w-full flex-col"
      style={{ background: bgGradient, minHeight: '100%' }}
    >
      <div className="flex min-h-full flex-col gap-2 p-2">
        {/* Header - Only show when NOT in iframe */}
        {showHeader && (
          <div className="mb-2 flex items-center justify-between" id="page-header">
            <div className="flex items-center gap-3">
              <h2 className="text-xl font-bold" style={{ color: textPrimary }}>📁 Data Upload & Management</h2>
              <a
                href="/dashboard/"
                className="rounded-lg border px-3 py-1.5 text-xs font-semibold transition"
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
                title="Back to Main Dashboard"
              >
                🏠 Dashboard
              </a>
            </div>
            <div>
              <a
                href="/data-upload-help/"
                className="rounded-lg border px-3 py-1.5 text-xs font-semibold transition"
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
              >
                📋 Help & Templates
              </a>
            </div>
          </div>
        )}

        {/* Upload Message */}
        {uploadMessage && (
          <div
            className="rounded-xl border px-4 py-3"
            style={{
              borderColor: uploadMessage.type === 'success' ? successBorder : errorBorder,
              backgroundColor: uploadMessage.type === 'success' ? successBg : errorBg,
            }}
          >
            <pre
              className="mb-0 whitespace-pre-wrap text-sm font-medium"
              style={{
                color: uploadMessage.type === 'success' ? successText : errorText,
              }}
            >
              {uploadMessage.message}
            </pre>
          </div>
        )}

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 gap-2 lg:grid-cols-2">
          {/* File Upload Section */}
          <div className="flex flex-col">
            <UploadForm onUpload={handleUpload} isUploading={isUploading} />
          </div>

          {/* Data Management Section */}
          <div className="flex flex-col">
            <DataOverview />
          </div>
        </div>
      </div>
    </div>
  );
}

