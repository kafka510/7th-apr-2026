/**
 * Loss Calculation Template Component
 */
 
import type { TemplateType } from '../utils/templateDownloader';
import { useTheme } from '../../../contexts/ThemeContext';

interface LossCalculationTemplateProps {
  onDownload: (type: TemplateType) => void;
}

export function LossCalculationTemplate({ onDownload }: LossCalculationTemplateProps) {
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
        <h5 className="mb-0 font-bold" style={{ color: textPrimary }}>📊 Loss Calculation Template</h5>
        <button 
          className="btn btn-outline-primary btn-sm" 
          onClick={() => onDownload('loss_calculation')}
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
          <strong className="font-bold">Required columns:</strong> month, asset_no
        </p>
        <div 
          className="alert alert-warning"
          style={{
            backgroundColor: warningBg,
            borderColor: warningBorder,
            color: warningText,
          }}
        >
          <h6 className="font-bold" style={{ color: warningText }}>⚠️ Column Name Mapping:</h6>
          <p className="font-medium" style={{ color: warningText }}>Your CSV column names will be automatically mapped to database fields:</p>
          <ul className="mb-0 font-medium" style={{ color: warningText }}>
            <li>
              <strong className="font-bold">&quot;S No&quot;</strong> → <code style={{ color: warningText }}>l</code> (Loss ID)
            </li>
            <li>
              <strong className="font-bold">&quot;Start Dae&quot;</strong> → <code style={{ color: warningText }}>start_date</code>
            </li>
            <li>
              <strong className="font-bold">&quot;Subcatergory&quot;</strong> → <code style={{ color: warningText }}>subcategory</code>
            </li>
            <li>
              <strong className="font-bold">&quot;Budget PR (%)&quot;</strong> → <code style={{ color: warningText }}>budget_pr_percent</code>
            </li>
            <li>
              <strong className="font-bold">&quot;PPA Rate in USD&quot;</strong> → <code style={{ color: warningText }}>ppa_rate_usd</code>
            </li>
            <li>
              <strong className="font-bold">&quot;Revenue Loss in USD&quot;</strong> → <code style={{ color: warningText }}>revenue_loss_usd</code>
            </li>
          </ul>
        </div>
        <div className="table-responsive">
          <table 
            className="table-bordered table-sm table"
            style={{ borderColor: tableBorder }}
          >
            <thead style={{ backgroundColor: tableHeaderBg }}>
              <tr>
                <th className="font-bold" style={{ color: tableHeaderText, borderColor: tableBorder }}>L</th>
                <th className="font-bold" style={{ color: tableHeaderText, borderColor: tableBorder }}>Month</th>
                <th className="font-bold" style={{ color: tableHeaderText, borderColor: tableBorder }}>Start Date</th>
                <th className="font-bold" style={{ color: tableHeaderText, borderColor: tableBorder }}>Asset No</th>
                <th className="font-bold" style={{ color: tableHeaderText, borderColor: tableBorder }}>Category</th>
                <th className="font-bold" style={{ color: tableHeaderText, borderColor: tableBorder }}>Subcategory</th>
                <th className="font-bold" style={{ color: tableHeaderText, borderColor: tableBorder }}>Budget PR (%)</th>
                <th className="font-bold" style={{ color: tableHeaderText, borderColor: tableBorder }}>Generation Loss (kWh)</th>
                <th className="font-bold" style={{ color: tableHeaderText, borderColor: tableBorder }}>PPA Rate in USD</th>
                <th className="font-bold" style={{ color: tableHeaderText, borderColor: tableBorder }}>Revenue Loss in USD</th>
              </tr>
            </thead>
            <tbody style={{ backgroundColor: tableRowBg }}>
              <tr>
                <td className="font-medium" style={{ color: tableRowText, borderColor: tableBorder }}>8</td>
                <td className="font-medium" style={{ color: tableRowText, borderColor: tableBorder }}>25-Jan</td>
                <td className="font-medium" style={{ color: tableRowText, borderColor: tableBorder }}>28-Jan-25</td>
                <td className="font-medium" style={{ color: tableRowText, borderColor: tableBorder }}>KR_BW_06</td>
                <td className="font-medium" style={{ color: tableRowText, borderColor: tableBorder }}>Plant</td>
                <td className="font-medium" style={{ color: tableRowText, borderColor: tableBorder }}>Inverter Failure</td>
                <td className="font-medium" style={{ color: tableRowText, borderColor: tableBorder }}>0.859570552</td>
                <td className="font-medium" style={{ color: tableRowText, borderColor: tableBorder }}>-11661.59</td>
                <td className="font-medium" style={{ color: tableRowText, borderColor: tableBorder }}>0.078421904</td>
                <td className="font-medium" style={{ color: tableRowText, borderColor: tableBorder }}>-914.5240919</td>
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
              <strong className="font-bold">Month:</strong> Format like &quot;25-Jan&quot;, &quot;25-Feb&quot;, etc.
            </li>
            <li>
              <strong className="font-bold">Asset No:</strong> Asset identifier (required)
            </li>
            <li>
              <strong className="font-bold">Dates:</strong> Can be in various formats (DD-MMM-YY, DD-MM-YYYY, etc.)
            </li>
            <li>
              <strong className="font-bold">Numeric fields:</strong> Use decimal numbers for percentages and rates
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
}

