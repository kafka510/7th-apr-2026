import { useTheme } from '../../../contexts/ThemeContext';
import { useResponsiveFontSize } from '../../../utils/fontScaling';
import type { BESSKPIData } from '../types';

interface BESSKPICardsProps {
  kpiData: BESSKPIData[];
  loading: boolean;
}

export function BESSKPICards({ kpiData, loading }: BESSKPICardsProps) {
  const { theme } = useTheme();
  
  // Responsive font sizes
  const labelFontSize = useResponsiveFontSize(11.2, 15.2, 10); // 0.7rem = 11.2px base
  const valueFontSize = useResponsiveFontSize(16, 20, 14); // 1rem = 16px base
  const iconFontSize = useResponsiveFontSize(20.8, 24.8, 18); // 1.3rem = 20.8px base
  
  const containerBg = theme === 'dark' 
    ? '#0f172a' 
    : '#ffffff';
  const containerBorder = theme === 'dark' ? 'rgba(148,163,184,0.2)' : 'rgba(203, 213, 225, 0.8)';
  const cardBorder = theme === 'dark' ? 'rgba(148,163,184,0.3)' : 'rgba(203, 213, 225, 0.6)';
  const cardBg = theme === 'dark'
    ? 'linear-gradient(135deg, rgba(20,184,166,0.15) 0%, rgba(6,182,212,0.15) 100%)'
    : 'linear-gradient(135deg, rgba(20,184,166,0.08) 0%, rgba(6,182,212,0.08) 100%)';
  const labelColor = theme === 'dark' ? '#94a3b8' : '#64748b';
  const valueColor = theme === 'dark' ? '#f1f5f9' : '#1a1a1a';
  const loadingColor = theme === 'dark' ? '#38bdf8' : '#0072ce';
  if (loading) {
    return (
      <div style={{ padding: '20px', textAlign: 'center', color: loadingColor }}>
        Loading KPIs...
      </div>
    );
  }

  if (kpiData.length === 0) {
    return null;
  }

  return (
    <div
      style={{
        margin: '0 16px 12px 16px',
        background: containerBg,
        borderRadius: '16px',
        padding: '12px',
        border: `1px solid ${containerBorder}`,
        boxShadow: theme === 'dark' 
          ? '0 4px 6px -1px rgba(0, 0, 0, 0.3)' 
          : '0 1px 3px 0 rgba(0, 0, 0, 0.1)',
      }}
    >
      <div
        style={{
          display: 'flex',
          flexWrap: 'nowrap',
          gap: '8px',
          overflowX: 'auto',
        }}
      >
        {kpiData.map((kpi, index) => (
          <div
            key={index}
            style={{
              flex: '1 1 auto',
              minWidth: '140px',
              padding: '10px 12px',
              borderRadius: '12px',
              border: `1px solid ${cardBorder}`,
              background: cardBg,
              backdropFilter: 'blur(8px)',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              minHeight: '70px',
              boxSizing: 'border-box',
            }}
          >
            <div style={{ fontSize: `${labelFontSize}px`, fontWeight: 500, color: labelColor, lineHeight: 1.2, marginBottom: '8px' }}>
              {kpi.label}
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ fontSize: `${valueFontSize}px`, fontWeight: 700, color: valueColor }}>
                {kpi.value}{kpi.unit}
              </div>
              <div style={{ fontSize: `${iconFontSize}px`, marginLeft: '8px', flexShrink: 0 }}>
                {kpi.icon || '📊'}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

