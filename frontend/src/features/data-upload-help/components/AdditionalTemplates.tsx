/**
 * Additional Templates Component
 */
 
import type { TemplateType } from '../utils/templateDownloader';
import { useTheme } from '../../../contexts/ThemeContext';

interface AdditionalTemplatesProps {
  onDownload: (type: TemplateType) => void;
}

export function AdditionalTemplates({ onDownload }: AdditionalTemplatesProps) {
  const { theme } = useTheme();
  
  // Theme-aware colors
  const cardBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.5)' : '#ffffff';
  const cardBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : 'rgba(203, 213, 225, 0.8)';
  const cardHeaderBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.5)' : 'rgba(241, 245, 249, 0.9)';
  const textPrimary = theme === 'dark' ? '#f1f5f9' : '#1e293b';
  const textSecondary = theme === 'dark' ? '#94a3b8' : '#64748b';
  const buttonBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.5)' : 'rgba(255, 255, 255, 0.9)';
  const buttonBorder = theme === 'dark' ? 'rgba(59, 130, 246, 0.5)' : 'rgba(59, 130, 246, 0.8)';
  const buttonText = theme === 'dark' ? '#93c5fd' : '#1e40af';
  const buttonHoverBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.8)' : 'rgba(59, 130, 246, 0.1)';

  return (
    <div 
      className="card mb-4"
      style={{
        backgroundColor: cardBg,
        borderColor: cardBorder,
      }}
    >
      <div 
        className="card-header d-flex justify-content-between align-items-center"
        style={{
          backgroundColor: cardHeaderBg,
          borderColor: cardBorder,
        }}
      >
        <h5 className="mb-0 font-bold" style={{ color: textPrimary }}>📋 Additional Templates</h5>
        <div>
          <button 
            className="btn btn-outline-primary btn-sm me-2" 
            onClick={() => onDownload('aoc')}
            style={{
              borderColor: buttonBorder,
              backgroundColor: buttonBg,
              color: buttonText,
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = buttonHoverBg;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = buttonBg;
            }}
          >
            📥 AOC Template
          </button>
          <button 
            className="btn btn-outline-primary btn-sm me-2" 
            onClick={() => onDownload('ice')}
            style={{
              borderColor: buttonBorder,
              backgroundColor: buttonBg,
              color: buttonText,
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = buttonHoverBg;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = buttonBg;
            }}
          >
            📥 ICE Template
          </button>
          <button 
            className="btn btn-outline-primary btn-sm me-2" 
            onClick={() => onDownload('icvsexvscur')}
            style={{
              borderColor: buttonBorder,
              backgroundColor: buttonBg,
              color: buttonText,
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = buttonHoverBg;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = buttonBg;
            }}
          >
            📥 IC Budget vs Expected Template
          </button>
          <button 
            className="btn btn-outline-primary btn-sm" 
            onClick={() => onDownload('minamata')}
            style={{
              borderColor: buttonBorder,
              backgroundColor: buttonBg,
              color: buttonText,
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = buttonHoverBg;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = buttonBg;
            }}
          >
            📥 Minamata Template
          </button>
        </div>
      </div>
      <div className="card-body" style={{ color: textPrimary }}>
        <div className="row">
          <div className="col-md-4">
            <h6 className="font-bold" style={{ color: textPrimary }}>AOC Data</h6>
            <small className="font-medium" style={{ color: textSecondary }}>
              Areas of Concern data with columns: s_no, month, asset_no, country, portfolio
            </small>
          </div>
          <div className="col-md-4">
            <h6 className="font-bold" style={{ color: textPrimary }}>ICE Data</h6>
            <small className="font-medium" style={{ color: textSecondary }}>ICE performance data with columns: month, portfolio</small>
          </div>
          <div className="col-md-4">
            <h6 className="font-bold" style={{ color: textPrimary }}>IC Budget vs Expected Data</h6>
            <small className="font-medium" style={{ color: textSecondary }}>
              IC Budget vs Expected Generation data with columns: country, portfolio, month
            </small>
          </div>
          <div className="col-md-4">
            <h6 className="font-bold" style={{ color: textPrimary }}>Minamata Data</h6>
            <small className="font-medium" style={{ color: textSecondary }}>String loss data with columns: month</small>
          </div>
        </div>
      </div>
    </div>
  );
}

