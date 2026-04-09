/**
 * BESS V1 Data Template Component
 */
 
import type { TemplateType } from '../utils/templateDownloader';
import { useTheme } from '../../../contexts/ThemeContext';

interface BESSV1DataTemplateProps {
  onDownload: (type: TemplateType) => void;
}

export function BESSV1DataTemplate({ onDownload }: BESSV1DataTemplateProps) {
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
        <h5 className="mb-0 font-bold" style={{ color: textPrimary }}>⚡ BESS V1 Performance Template</h5>
        <button 
          className="btn btn-outline-primary btn-sm" 
          onClick={() => onDownload('bess_v1')}
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
          <strong className="font-bold">Required columns:</strong> month, country, portfolio, asset_no
        </p>
        <p className="mb-2 font-medium" style={{ color: textPrimary }}>
          <strong className="font-bold">Includes:</strong> actual vs budget energy flows, CUF and RTE metrics, system losses, and cycle counts.
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
                <th className="font-bold" style={{ color: tableHeaderText, borderColor: tableBorder }}>asset_no</th>
                <th className="font-bold" style={{ color: tableHeaderText, borderColor: tableBorder }}>battery_capacity_mwh</th>
                <th className="font-bold" style={{ color: tableHeaderText, borderColor: tableBorder }}>actual_pv_energy_kwh</th>
                <th className="font-bold" style={{ color: tableHeaderText, borderColor: tableBorder }}>actual_export_energy_kwh</th>
                <th className="font-bold" style={{ color: tableHeaderText, borderColor: tableBorder }}>actual_charge_energy_kwh</th>
                <th className="font-bold" style={{ color: tableHeaderText, borderColor: tableBorder }}>actual_avg_rte</th>
                <th className="font-bold" style={{ color: tableHeaderText, borderColor: tableBorder }}>actual_cuf</th>
                <th className="font-bold" style={{ color: tableHeaderText, borderColor: tableBorder }}>actual_no_of_cycles</th>
              </tr>
            </thead>
            <tbody style={{ backgroundColor: tableRowBg }}>
              <tr>
                <td className="font-medium" style={{ color: tableRowText, borderColor: tableBorder }}>2025-01</td>
                <td className="font-medium" style={{ color: tableRowText, borderColor: tableBorder }}>Korea</td>
                <td className="font-medium" style={{ color: tableRowText, borderColor: tableBorder }}>Blackwood</td>
                <td className="font-medium" style={{ color: tableRowText, borderColor: tableBorder }}>KR_BW_18</td>
                <td className="font-medium" style={{ color: tableRowText, borderColor: tableBorder }}>1.4976</td>
                <td className="font-medium" style={{ color: tableRowText, borderColor: tableBorder }}>39748</td>
                <td className="font-medium" style={{ color: tableRowText, borderColor: tableBorder }}>38327</td>
                <td className="font-medium" style={{ color: tableRowText, borderColor: tableBorder }}>19371</td>
                <td className="font-medium" style={{ color: tableRowText, borderColor: tableBorder }}>93.67</td>
                <td className="font-medium" style={{ color: tableRowText, borderColor: tableBorder }}>43.44%</td>
                <td className="font-medium" style={{ color: tableRowText, borderColor: tableBorder }}>31</td>
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
          <h6 className="mb-2 font-bold" style={{ color: infoText }}>Key Metrics Captured:</h6>
          <ul className="mb-0 font-medium" style={{ color: infoText }}>
            <li>
              <strong className="font-bold">Energy Flow:</strong> PV generation, PV to grid/BESS, export energy, system losses.
            </li>
            <li>
              <strong className="font-bold">Operational KPIs:</strong> CUF (actual & budget), battery cycles, round trip efficiency, SOC and temperature ranges.
            </li>
            <li>
              <strong className="font-bold">Budget Comparison:</strong> Budgeted energy, grid imports, and RTE to analyze performance gaps.
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
}

