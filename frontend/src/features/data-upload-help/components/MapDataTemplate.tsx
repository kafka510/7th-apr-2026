/**
 * Map Data Template Component
 */
 
import type { TemplateType } from '../utils/templateDownloader';
import { useTheme } from '../../../contexts/ThemeContext';

interface MapDataTemplateProps {
  onDownload: (type: TemplateType) => void;
}

export function MapDataTemplate({ onDownload }: MapDataTemplateProps) {
  const { theme } = useTheme();
  
  // Theme-aware colors
  const cardBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.5)' : '#ffffff';
  const cardBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : 'rgba(203, 213, 225, 0.8)';
  const cardHeaderBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.5)' : 'rgba(241, 245, 249, 0.9)';
  const textPrimary = theme === 'dark' ? '#f1f5f9' : '#1e293b';
  const tableHeaderBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.5)' : 'rgba(241, 245, 249, 0.9)';
  const tableHeaderText = theme === 'dark' ? '#cbd5e1' : '#475569';
  const tableRowBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.3)' : '#ffffff';
  const tableRowText = theme === 'dark' ? '#e2e8f0' : '#1e293b';
  const tableBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : 'rgba(203, 213, 225, 0.8)';
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
        <h5 className="mb-0 font-bold" style={{ color: textPrimary }}>🗺️ Map Data Template</h5>
        <button 
          className="btn btn-outline-primary btn-sm" 
          onClick={() => onDownload('map')}
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
          📥 Download Template
        </button>
      </div>
      <div className="card-body" style={{ color: textPrimary }}>
        <p className="font-medium" style={{ color: textPrimary }}>
          <strong className="font-bold">Required columns:</strong> asset_no, country, site_name, portfolio
        </p>
        <div className="table-responsive">
          <table 
            className="table-bordered table-sm table"
            style={{ borderColor: tableBorder }}
          >
            <thead style={{ backgroundColor: tableHeaderBg }}>
              <tr>
                <th className="font-bold" style={{ color: tableHeaderText, borderColor: tableBorder }}>asset_no</th>
                <th className="font-bold" style={{ color: tableHeaderText, borderColor: tableBorder }}>country</th>
                <th className="font-bold" style={{ color: tableHeaderText, borderColor: tableBorder }}>site_name</th>
                <th className="font-bold" style={{ color: tableHeaderText, borderColor: tableBorder }}>portfolio</th>
                <th className="font-bold" style={{ color: tableHeaderText, borderColor: tableBorder }}>dc_capacity_mwp</th>
                <th className="font-bold" style={{ color: tableHeaderText, borderColor: tableBorder }}>latitude</th>
                <th className="font-bold" style={{ color: tableHeaderText, borderColor: tableBorder }}>longitude</th>
              </tr>
            </thead>
            <tbody style={{ backgroundColor: tableRowBg }}>
              <tr>
                <td className="font-medium" style={{ color: tableRowText, borderColor: tableBorder }}>JP-MINA</td>
                <td className="font-medium" style={{ color: tableRowText, borderColor: tableBorder }}>JP</td>
                <td className="font-medium" style={{ color: tableRowText, borderColor: tableBorder }}>Minamata Solar Plant</td>
                <td className="font-medium" style={{ color: tableRowText, borderColor: tableBorder }}>Portfolio A</td>
                <td className="font-medium" style={{ color: tableRowText, borderColor: tableBorder }}>10.5</td>
                <td className="font-medium" style={{ color: tableRowText, borderColor: tableBorder }}>32.2094</td>
                <td className="font-medium" style={{ color: tableRowText, borderColor: tableBorder }}>130.4017</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

