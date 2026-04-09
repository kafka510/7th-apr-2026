/**
 * Insights Box Component for Sales Dashboard - React Style V1
 */
 
import type { KPIMetrics } from '../types';
import { useTheme } from '../../../contexts/ThemeContext';

interface InsightsBoxProps {
  metrics: KPIMetrics;
}

export function InsightsBox({ metrics }: InsightsBoxProps) {
  const { theme } = useTheme();
  const formatNumber = (num: number, decimals = 0): string => {
    if (num >= 1000) {
      return `${(num / 1000).toFixed(decimals)}K`;
    }
    return num.toLocaleString('en-US', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    });
  };

  const boxBg = theme === 'dark' 
    ? 'linear-gradient(to bottom right, rgba(15, 23, 42, 0.9), rgba(30, 41, 59, 0.6))'
    : 'linear-gradient(to bottom right, #ffffff, #f8fafc)';
  const boxBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(226, 232, 240, 0.8)';
  const innerBg = theme === 'dark' 
    ? 'linear-gradient(to bottom right, rgba(30, 41, 59, 0.6), rgba(15, 23, 42, 0.6))'
    : 'linear-gradient(to bottom right, #f8fafc, #f1f5f9)';
  const innerBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.5)' : 'rgba(203, 213, 225, 0.5)';
  const titleColor = theme === 'dark' ? '#60a5fa' : '#0072ce';
  const textColor = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';

  return (
    <div className="w-full">
      <div 
        className="rounded-xl p-4 shadow-xl"
        style={{
          border: `1px solid ${boxBorder}`,
          background: boxBg,
          transition: 'background 0.3s ease, border-color 0.3s ease',
        }}
      >
        <div className="mb-2 flex items-center gap-2">
          <span 
            className="text-sm font-semibold uppercase tracking-wide"
            style={{ color: titleColor }}
          >
            💡 Key Insights
          </span>
        </div>
        <div 
          className="rounded-lg p-3 text-sm leading-relaxed"
          style={{
            border: `1px solid ${innerBorder}`,
            background: innerBg,
            color: textColor,
            transition: 'background 0.3s ease, border-color 0.3s ease, color 0.3s ease',
          }}
        >
          <span>🌞</span> Solar generation reached{' '}
          <span className="font-bold" style={{ color: '#60a5fa' }}>{formatNumber(metrics.solarEnergy, 0)} MWh</span>,{' '}
          <span>⚡</span> BESS discharged{' '}
          <span className="font-bold" style={{ color: '#8b5cf6' }}>{formatNumber(metrics.bessEnergy, 0)} MWh</span>,{' '}
          <span>🌱</span> equivalent to saving{' '}
          <span className="font-bold" style={{ color: '#14b8a6' }}>{formatNumber(metrics.totalCO2, 0)} tons CO₂</span> and protecting{' '}
          <span className="font-bold" style={{ color: '#22c55e' }}>{formatNumber(metrics.treesSaved, 0)} trees</span>.
        </div>
      </div>
    </div>
  );
}

