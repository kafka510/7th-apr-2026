/**
 * Data Upload Help Page Component
 */
 
import { useEffect, useState } from 'react';
import { YieldDataTemplate } from './components/YieldDataTemplate';
import { BESSDataTemplate } from './components/BESSDataTemplate';
import { BESSV1DataTemplate } from './components/BESSV1DataTemplate';
import { DailyDataTemplates } from './components/DailyDataTemplates';
import { MapDataTemplate } from './components/MapDataTemplate';
import { ICBudgetVsExpectedTemplate } from './components/ICBudgetVsExpectedTemplate';
import { LossCalculationTemplate } from './components/LossCalculationTemplate';
import { AdditionalTemplates } from './components/AdditionalTemplates';
import { UploadModesSidebar } from './components/UploadModesSidebar';
import { DataTypesSidebar } from './components/DataTypesSidebar';
import { TipsSidebar } from './components/TipsSidebar';
import { downloadTemplate } from './utils/templateDownloader';
import { useTheme } from '../../contexts/ThemeContext';
import { getGradientBg } from '../../utils/themeColors';

const DASHBOARD_ID = 'data-upload-help';

export function DataUploadHelp() {
  const { theme } = useTheme();
  
  // Only show header when page is NOT in iframe (same as old template)
  const [showHeader] = useState(() => {
    if (typeof window !== 'undefined') {
      return window.self === window.top;
    }
    return false;
  });

  // Theme-aware colors
  const bgGradient = getGradientBg(theme);
  const textPrimary = theme === 'dark' ? '#f1f5f9' : '#1a1a1a';
  const cardTextColor = theme === 'dark' ? '#e2e8f0' : '#1e293b';
  const infoBg = theme === 'dark' ? 'rgba(59, 130, 246, 0.2)' : 'rgba(59, 130, 246, 0.1)';
  const infoBorder = theme === 'dark' ? 'rgba(59, 130, 246, 0.5)' : 'rgba(59, 130, 246, 0.3)';
  const infoText = theme === 'dark' ? '#93c5fd' : '#1e40af';
  const warningBg = theme === 'dark' ? 'rgba(250, 204, 21, 0.2)' : 'rgba(250, 204, 21, 0.1)';
  const warningBorder = theme === 'dark' ? 'rgba(250, 204, 21, 0.5)' : 'rgba(250, 204, 21, 0.3)';
  const warningText = theme === 'dark' ? '#fde047' : '#a16207';
  const buttonBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.5)' : 'rgba(255, 255, 255, 0.9)';
  const buttonBorder = theme === 'dark' ? 'rgba(59, 130, 246, 0.5)' : 'rgba(59, 130, 246, 0.8)';
  const buttonText = theme === 'dark' ? '#93c5fd' : '#1e40af';

  // Consider help page "ready" as soon as it is rendered
  useEffect(() => {
    document.body.setAttribute('data-filters-ready', 'true');
    window.dispatchEvent(
      new CustomEvent('dashboard-filters-ready', { detail: { dashboardId: DASHBOARD_ID } }),
    );

    return () => {
      document.body.removeAttribute('data-filters-ready');
    };
  }, []);

  return (
    <div 
      className="container mt-4"
      style={{ 
        background: bgGradient,
        color: textPrimary,
        minHeight: '100vh',
        padding: '1rem',
      }}
    >
      <style>{`
        .card-body {
          color: ${cardTextColor} !important;
        }
        .card-body p, .card-body li, .card-body td, .card-body th, .card-body small, .card-body span {
          color: ${cardTextColor} !important;
        }
        .card-body h1, .card-body h2, .card-body h3, .card-body h4, .card-body h5, .card-body h6 {
          color: ${cardTextColor} !important;
        }
        .card-header h5, .card-header h6 {
          color: ${textPrimary} !important;
        }
        .list-group-item h6, .list-group-item small {
          color: ${cardTextColor} !important;
        }
        .alert h6, .alert ul, .alert li, .alert p, .alert small, .alert strong, .alert span {
          color: ${cardTextColor} !important;
        }
        .table th, .table td {
          color: ${cardTextColor} !important;
        }
      `}</style>

      {/* Header - Only show when NOT in iframe */}
      {showHeader && (
        <div className="d-flex justify-content-between align-items-center mb-3" id="page-header">
          <div className="d-flex align-items-center">
            <h2 className="font-bold" style={{ color: textPrimary }}>📋 Data Upload Help & Templates</h2>
            <a 
              href="/data-upload/" 
              className="btn btn-outline-primary btn-sm ms-3" 
              title="Back to Data Upload"
              style={{
                borderColor: buttonBorder,
                backgroundColor: buttonBg,
                color: buttonText,
              }}
            >
              📤 Data Upload
            </a>
          </div>
        </div>
      )}

      <div 
        className="alert alert-info"
        style={{
          backgroundColor: infoBg,
          borderColor: infoBorder,
          color: infoText,
        }}
      >
        <h5 className="font-bold">📝 CSV Format Requirements</h5>
        <ul className="font-medium">
          <li>Files must be in CSV format (.csv extension)</li>
          <li>First row should contain column headers</li>
          <li>Column names are case-insensitive and spaces are automatically converted to underscores</li>
          <li>Date fields should be in YYYY-MM-DD format</li>
          <li>Numeric fields should contain valid numbers</li>
          <li>
            <strong>File encoding:</strong> UTF-8, Latin-1, or Windows-1252 (the system will automatically detect the encoding)
          </li>
        </ul>
      </div>

      <div 
        className="alert alert-warning"
        style={{
          backgroundColor: warningBg,
          borderColor: warningBorder,
          color: warningText,
        }}
      >
        <h5 className="font-bold">⚠️ Encoding Issues</h5>
        <p className="font-medium">If you encounter encoding errors like &quot;utf-8 codec can&apos;t decode byte&quot;, try these solutions:</p>
        <ul className="font-medium">
          <li>Open the CSV file in a text editor (like Notepad++) and save it as UTF-8</li>
          <li>If using Excel, save the file as &quot;CSV UTF-8 (Comma delimited)&quot;</li>
          <li>Ensure the file doesn&apos;t contain special characters that might cause encoding issues</li>
        </ul>
      </div>

      <div className="row">
        <div className="col-md-8">
          <YieldDataTemplate onDownload={downloadTemplate} />
          <BESSDataTemplate onDownload={downloadTemplate} />
          <BESSV1DataTemplate onDownload={downloadTemplate} />
          <DailyDataTemplates onDownload={downloadTemplate} />
          <MapDataTemplate onDownload={downloadTemplate} />
          <ICBudgetVsExpectedTemplate onDownload={downloadTemplate} />
          <LossCalculationTemplate onDownload={downloadTemplate} />
          <AdditionalTemplates onDownload={downloadTemplate} />
        </div>

        <div className="col-md-4">
          <UploadModesSidebar />
          <DataTypesSidebar />
          <TipsSidebar />
        </div>
      </div>
    </div>
  );
}
