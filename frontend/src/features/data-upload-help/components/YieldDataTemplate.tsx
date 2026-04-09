/**
 * Yield Data Template Component
 */
 
import type { TemplateType } from '../utils/templateDownloader';
import { useTheme } from '../../../contexts/ThemeContext';

interface YieldDataTemplateProps {
  onDownload: (type: TemplateType) => void;
}

export function YieldDataTemplate({ onDownload }: YieldDataTemplateProps) {
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
  const infoBg = theme === 'dark' ? 'rgba(59, 130, 246, 0.2)' : 'rgba(59, 130, 246, 0.1)';
  const infoBorder = theme === 'dark' ? 'rgba(59, 130, 246, 0.5)' : 'rgba(59, 130, 246, 0.3)';
  const infoText = theme === 'dark' ? '#93c5fd' : '#1e40af';
  const warningBg = theme === 'dark' ? 'rgba(250, 204, 21, 0.2)' : 'rgba(250, 204, 21, 0.1)';
  const warningBorder = theme === 'dark' ? 'rgba(250, 204, 21, 0.5)' : 'rgba(250, 204, 21, 0.3)';
  const warningText = theme === 'dark' ? '#fde047' : '#a16207';

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
        <h5 className="mb-0 font-bold" style={{ color: textPrimary }}>📊 Yield Data Template</h5>
        <button 
          className="btn btn-outline-primary btn-sm" 
          onClick={() => onDownload('yield')}
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
          <strong className="font-bold">Required columns:</strong> month, country, portfolio, assetno
        </p>
        <p className="font-medium" style={{ color: textPrimary }}>
          <strong className="font-bold">Note:</strong> All other columns are optional. Download the template CSV to see the complete structure with all available fields.
        </p>
        <div className="table-responsive">
          <table 
            className="table-bordered table-sm table"
            style={{ borderColor: tableBorder }}
          >
            <thead style={{ backgroundColor: tableHeaderBg }}>
              <tr>
                <th className="font-bold" style={{ color: tableHeaderText, borderColor: tableBorder }}>month</th>
                <th className="font-bold" style={{ color: tableHeaderText, borderColor: tableBorder }}>country</th>
                <th className="font-bold" style={{ color: tableHeaderText, borderColor: tableBorder }}>portfolio</th>
                <th className="font-bold" style={{ color: tableHeaderText, borderColor: tableBorder }}>assetno</th>
                <th className="font-bold" style={{ color: tableHeaderText, borderColor: tableBorder }}>dc_capacity_mw</th>
                <th className="font-bold" style={{ color: tableHeaderText, borderColor: tableBorder }}>ic_approved_budget</th>
                <th className="font-bold" style={{ color: tableHeaderText, borderColor: tableBorder }}>expected_budget</th>
                <th className="font-bold" style={{ color: tableHeaderText, borderColor: tableBorder }}>weather_loss_or_gain</th>
                <th className="font-bold" style={{ color: tableHeaderText, borderColor: tableBorder }}>grid_curtailment</th>
                <th className="font-bold" style={{ color: tableHeaderText, borderColor: tableBorder }}>string failure</th>
                <th className="font-bold" style={{ color: tableHeaderText, borderColor: tableBorder }}>inverter failure</th>
                <th className="font-bold" style={{ color: tableHeaderText, borderColor: tableBorder }}>expected_pr</th>
                <th className="font-bold" style={{ color: tableHeaderText, borderColor: tableBorder }}>actual_pr</th>
                <th className="font-bold" style={{ color: tableHeaderText, borderColor: tableBorder }}>revenue_loss</th>
                <th className="font-bold" style={{ color: tableHeaderText, borderColor: tableBorder }}>ppa_rate</th>
              </tr>
            </thead>
            <tbody style={{ backgroundColor: tableRowBg }}>
              <tr>
                <td className="font-medium" style={{ color: tableRowText, borderColor: tableBorder }}>2024-01</td>
                <td className="font-medium" style={{ color: tableRowText, borderColor: tableBorder }}>JP</td>
                <td className="font-medium" style={{ color: tableRowText, borderColor: tableBorder }}>Portfolio A</td>
                <td className="font-medium" style={{ color: tableRowText, borderColor: tableBorder }}>JP-MINA</td>
                <td className="font-medium" style={{ color: tableRowText, borderColor: tableBorder }}>10.5</td>
                <td className="font-medium" style={{ color: tableRowText, borderColor: tableBorder }}>1000.0</td>
                <td className="font-medium" style={{ color: tableRowText, borderColor: tableBorder }}>950.0</td>
                <td className="font-medium" style={{ color: tableRowText, borderColor: tableBorder }}>5.2</td>
                <td className="font-medium" style={{ color: tableRowText, borderColor: tableBorder }}>2.1</td>
                <td className="font-medium" style={{ color: tableRowText, borderColor: tableBorder }}>0.8</td>
                <td className="font-medium" style={{ color: tableRowText, borderColor: tableBorder }}>0.3</td>
                <td className="font-medium" style={{ color: tableRowText, borderColor: tableBorder }}>85.5</td>
                <td className="font-medium" style={{ color: tableRowText, borderColor: tableBorder }}>82.3</td>
                <td className="font-medium" style={{ color: tableRowText, borderColor: tableBorder }}>15000.0</td>
                <td className="font-medium" style={{ color: tableRowText, borderColor: tableBorder }}>0.15</td>
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
          <h6 className="font-bold" style={{ color: infoText }}>📝 Field Categories:</h6>
          <ul className="mb-0 font-medium" style={{ color: infoText }}>
            <li>
              <strong className="font-bold">Basic Info:</strong> month, country, portfolio, assetno
            </li>
            <li>
              <strong className="font-bold">Capacity:</strong> dc_capacity_mw, ac_capacity_mw, bess_capacity_mwh
            </li>
            <li>
              <strong className="font-bold">Budget & Generation:</strong> ic_approved_budget, expected_budget, weather_corrected_budget, actual_generation
            </li>
            <li>
              <strong className="font-bold">Losses:</strong> weather_loss_or_gain, grid_curtailment, actual_curtailment, grid_outage, grid_loss, scheduled_outage_loss, breakdown_loss, unclassified_loss, unclassified_loss_%, string failure, inverter failure, ac_failure
            </li>
            <li>
              <strong className="font-bold">Performance Ratio:</strong> expected_pr, actual_pr, pr_gap, pr_gap_observation, pr_gap_action_need_to_taken
            </li>
            <li>
              <strong className="font-bold">Revenue:</strong> revenue_loss, revenue_loss_observation, revenue_loss_action_need_to_taken, ppa_rate
            </li>
            <li>
              <strong className="font-bold">Dollar Values:</strong> ic_approved_budget_$, expected_budget_$, actual_generation_$, operational_budget_dollar, revenue_loss_op
            </li>
          </ul>
          <div 
            className="alert alert-warning mt-2"
            style={{
              backgroundColor: warningBg,
              borderColor: warningBorder,
              color: warningText,
            }}
          >
            <small className="font-medium" style={{ color: warningText }}>
              <strong className="font-bold">Note:</strong> Column names with spaces (like &quot;string failure&quot;, &quot;inverter failure&quot;) and special characters (like $ and %) are automatically normalized during upload. Use the exact names as shown in the CSV template.
            </small>
          </div>
        </div>
      </div>
    </div>
  );
}

