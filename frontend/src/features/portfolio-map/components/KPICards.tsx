/**
 * KPI Cards Component for Portfolio Map
 */
 
import type { KPIMetrics } from '../types';
import { useTheme } from '../../../contexts/ThemeContext';
import { useResponsiveFontSize } from '../../../utils/fontScaling';

interface KPICardsProps {
  metrics: KPIMetrics;
}

export function KPICards({ metrics }: KPICardsProps) {
  const { theme } = useTheme();
  const fmt = (v: number): string => (!Number.isNaN(v) ? v.toFixed(1) : '0.0');

  // Responsive font sizes
  const labelFontSize = useResponsiveFontSize(12, 16, 10); // 0.75rem base = 12px
  const valueFontSize = useResponsiveFontSize(14, 18, 12); // 0.875rem base = 14px
  const iconFontSize = useResponsiveFontSize(16, 20, 14); // 1rem base = 16px

  // Theme-aware colors
  const cardBg = theme === 'dark'
    ? 'linear-gradient(to bottom right, rgba(15, 23, 42, 0.9), rgba(30, 41, 59, 0.6))'
    : 'linear-gradient(to bottom right, rgba(255, 255, 255, 0.95), rgba(248, 250, 252, 0.9))';
  const cardBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(226, 232, 240, 0.8)';
  const labelColor = theme === 'dark' ? '#cbd5e1' : '#4a5568';
  const valueColor = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';

  return (
    <div className="kpi-cards-section grid grid-cols-1 gap-2 sm:grid-cols-3" style={{ height: '40px' }}>
      <div 
        className="kpi-card rounded-xl shadow-xl"
        style={{
          border: `1px solid ${cardBorder}`,
          background: cardBg,
          transition: 'background 0.3s ease, border-color 0.3s ease',
        }}
      >
        <span className="kpi-icon" style={{ fontSize: `${iconFontSize}px` }}>📍</span>
        <span className="kpi-label" style={{ color: labelColor, fontSize: `${labelFontSize}px` }}>Total Sites:</span>
        <span className="kpi-value" style={{ color: valueColor, fontSize: `${valueFontSize}px` }}>{metrics.siteCount}</span>
      </div>
      <div 
        className="kpi-card rounded-xl shadow-xl"
        style={{
          border: `1px solid ${cardBorder}`,
          background: cardBg,
          transition: 'background 0.3s ease, border-color 0.3s ease',
        }}
      >
        <span className="kpi-icon" style={{ fontSize: `${iconFontSize}px` }}>🔆</span>
        <span className="kpi-label" style={{ color: labelColor, fontSize: `${labelFontSize}px` }}>PV (MWp):</span>
        <span className="kpi-value" style={{ color: valueColor, fontSize: `${valueFontSize}px` }}>{fmt(metrics.pvCapacity)}</span>
      </div>
      <div 
        className="kpi-card rounded-xl shadow-xl"
        style={{
          border: `1px solid ${cardBorder}`,
          background: cardBg,
          transition: 'background 0.3s ease, border-color 0.3s ease',
        }}
      >
        <span className="kpi-icon" style={{ fontSize: `${iconFontSize}px` }}>🔋</span>
        <span className="kpi-label" style={{ color: labelColor, fontSize: `${labelFontSize}px` }}>BESS (MWh):</span>
        <span className="kpi-value" style={{ color: valueColor, fontSize: `${valueFontSize}px` }}>{fmt(metrics.bessCapacity)}</span>
      </div>
      <style>{`
        .kpi-cards-section {
          height: 40px !important;
        }
        .kpi-card {
          display: flex;
          flex-direction: row;
          align-items: center;
          gap: 0.4rem;
          padding: 0.3rem 0.6rem !important;
          height: 100% !important;
        }
        .kpi-card .kpi-icon {
          font-size: 1rem !important;
          flex-shrink: 0;
        }
        .kpi-card .kpi-label {
          font-size: 0.75rem !important;
          font-weight: 600;
          white-space: nowrap;
          flex-shrink: 0;
        }
        .kpi-card .kpi-value {
          font-size: 0.875rem !important;
          font-weight: 700;
          white-space: nowrap;
          flex-shrink: 0;
        }
        @media (max-width: 900px) {
          .kpi-card {
            min-height: 35px !important;
          }
        }
      `}</style>
    </div>
  );
}

