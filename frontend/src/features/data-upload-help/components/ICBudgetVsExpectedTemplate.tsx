/**
 * IC Budget vs Expected Data Template Component
 */
 
import type { TemplateType } from '../utils/templateDownloader';
import { useTheme } from '../../../contexts/ThemeContext';

interface ICBudgetVsExpectedTemplateProps {
  onDownload: (type: TemplateType) => void;
}

export function ICBudgetVsExpectedTemplate({ onDownload }: ICBudgetVsExpectedTemplateProps) {
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
  const warningBg = theme === 'dark' ? 'rgba(250, 204, 21, 0.2)' : 'rgba(250, 204, 21, 0.1)';
  const warningBorder = theme === 'dark' ? 'rgba(250, 204, 21, 0.5)' : 'rgba(250, 204, 21, 0.3)';
  const warningText = theme === 'dark' ? '#fde047' : '#a16207';
  const infoBg = theme === 'dark' ? 'rgba(59, 130, 246, 0.2)' : 'rgba(59, 130, 246, 0.1)';
  const infoBorder = theme === 'dark' ? 'rgba(59, 130, 246, 0.5)' : 'rgba(59, 130, 246, 0.3)';
  const infoText = theme === 'dark' ? '#93c5fd' : '#1e40af';

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
        <h5 className="mb-0 font-bold" style={{ color: textPrimary }}>📊 IC Budget vs Expected Data Template</h5>
        <button 
          className="btn btn-outline-primary btn-sm" 
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
          📥 Download Template
        </button>
      </div>
      <div className="card-body" style={{ color: textPrimary }}>
        <p className="font-medium" style={{ color: textPrimary }}>
          <strong className="font-bold">Required columns:</strong> country, portfolio, month
        </p>
        <div 
          className="alert alert-warning"
          style={{
            backgroundColor: warningBg,
            borderColor: warningBorder,
            color: warningText,
          }}
        >
          <h6 className="font-bold" style={{ color: warningText }}>📅 Month Format:</h6>
          <p className="font-medium" style={{ color: warningText }}>
            The month column should be in the format: <strong className="font-bold">&quot;25-Apr&quot;</strong>,{' '}
            <strong className="font-bold">&quot;25-May&quot;</strong>, etc.
          </p>
          <ul className="mb-0 font-medium" style={{ color: warningText }}>
            <li>First part: 2-digit year (e.g., &quot;25&quot; for 2025)</li>
            <li>Second part: 3-letter month abbreviation (Jan, Feb, Mar, Apr, May, Jun, Jul, Aug, Sep, Oct, Nov, Dec)</li>
          </ul>
        </div>
        <div className="table-responsive">
          <table 
            className="table-bordered table-sm table"
            style={{ borderColor: tableBorder }}
          >
            <thead style={{ backgroundColor: tableHeaderBg }}>
              <tr>
                <th className="font-bold" style={{ color: tableHeaderText, borderColor: tableBorder }}>Country</th>
                <th className="font-bold" style={{ color: tableHeaderText, borderColor: tableBorder }}>Portfolio</th>
                <th className="font-bold" style={{ color: tableHeaderText, borderColor: tableBorder }}>DC Capacity (Mwp)</th>
                <th className="font-bold" style={{ color: tableHeaderText, borderColor: tableBorder }}>Month</th>
                <th className="font-bold" style={{ color: tableHeaderText, borderColor: tableBorder }}>IC Approved Budget (MWh)</th>
                <th className="font-bold" style={{ color: tableHeaderText, borderColor: tableBorder }}>Expected Budget (MWh)</th>
                <th className="font-bold" style={{ color: tableHeaderText, borderColor: tableBorder }}>Actual Generation (MWh)</th>
                <th className="font-bold" style={{ color: tableHeaderText, borderColor: tableBorder }}>Expected PR (%)</th>
                <th className="font-bold" style={{ color: tableHeaderText, borderColor: tableBorder }}>Actual PR (%)</th>
              </tr>
            </thead>
            <tbody style={{ backgroundColor: tableRowBg }}>
              <tr>
                <td className="font-medium" style={{ color: tableRowText, borderColor: tableBorder }}>Japan</td>
                <td className="font-medium" style={{ color: tableRowText, borderColor: tableBorder }}>JP Minamata</td>
                <td className="font-medium" style={{ color: tableRowText, borderColor: tableBorder }}>28.25</td>
                <td className="font-medium" style={{ color: tableRowText, borderColor: tableBorder }}>25-Jan</td>
                <td className="font-medium" style={{ color: tableRowText, borderColor: tableBorder }}>2072.6</td>
                <td className="font-medium" style={{ color: tableRowText, borderColor: tableBorder }}>2018.5</td>
                <td className="font-medium" style={{ color: tableRowText, borderColor: tableBorder }}>1554.2</td>
                <td className="font-medium" style={{ color: tableRowText, borderColor: tableBorder }}>76.43%</td>
                <td className="font-medium" style={{ color: tableRowText, borderColor: tableBorder }}>54.57%</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div 
          className="alert alert-info mt-3"
          style={{
            backgroundColor: infoBg,
            borderColor: infoBorder,
            color: infoText,
          }}
        >
          <h6 className="font-bold" style={{ color: infoText }}>📝 Column Details:</h6>
          <ul className="mb-0 font-medium" style={{ color: infoText }}>
            <li>
              <strong className="font-bold">Month:</strong> Will be automatically converted to a date and displayed as &quot;Jan 2025&quot;, &quot;Feb 2025&quot;, etc.
            </li>
            <li>
              <strong className="font-bold">DC Capacity (Mwp):</strong> DC capacity in megawatts peak
            </li>
            <li>
              <strong className="font-bold">PR (%):</strong> Performance Ratio in percentage format (can include % symbol or not)
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
}

