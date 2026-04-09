/**
 * KPI Cards Component for Sales Dashboard - React Style V1
 */
 
import type { KPIMetrics } from '../types';
import { useTheme } from '../../../contexts/ThemeContext';
import { useResponsiveFontSize } from '../../../utils/fontScaling';

interface KPICardsProps {
  metrics: KPIMetrics;
}

export function KPICards({ metrics }: KPICardsProps) {
  const { theme } = useTheme();
  
  // Responsive font sizes
  const labelFontSize = useResponsiveFontSize(9, 13, 8);
  const unitFontSize = useResponsiveFontSize(9, 13, 8);
  
  const formatNumber = (num: number, decimals = 0): string => {
    return num.toLocaleString('en-US', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    });
  };

  const kpiCards = [
    {
      label: 'Solar Energy',
      value: formatNumber(metrics.solarEnergy, 0),
      unit: 'MWh',
      icon: '☀️',
      accentColor: '#facc15',
    },
    {
      label: 'BESS Discharge',
      value: formatNumber(metrics.bessEnergy, 0),
      unit: 'MWh',
      icon: '🔋',
      accentColor: '#8b5cf6',
    },
    {
      label: 'CO₂ Saved',
      value: formatNumber(metrics.totalCO2, 0),
      unit: 'Tons',
      icon: '🌿',
      accentColor: '#14b8a6',
    },
    {
      label: 'Trees Equivalent',
      value: formatNumber(metrics.treesSaved, 0),
      unit: 'Trees',
      icon: '🌳',
      accentColor: '#22c55e',
    },
    {
      label: 'Solar Assets',
      value: formatNumber(metrics.solarAssetsCount, 0),
      unit: 'Assets',
      icon: '🏢',
      accentColor: '#d946ef',
    },
    {
      label: 'Solar Capacity',
      value: formatNumber(metrics.solarDcCapacity, 2),
      unit: 'MWp',
      icon: '⚡',
      accentColor: '#f97316',
    },
    {
      label: 'Battery Capacity',
      value: formatNumber(metrics.bessCapacity, 2),
      unit: 'MWh',
      icon: '🔋',
      accentColor: '#3b82f6',
    },
  ];

  return (
    <div className="grid w-full grid-cols-2 gap-2 md:grid-cols-3 lg:grid-cols-7">
      {kpiCards.map((card, index) => {
        const cardBg = theme === 'dark' 
          ? 'linear-gradient(to bottom right, rgba(15, 23, 42, 0.9), rgba(30, 41, 59, 0.6))'
          : 'linear-gradient(to bottom right, #ffffff, #f8fafc)';
        const cardBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(226, 232, 240, 0.8)';
        const labelColor = theme === 'dark' ? '#94a3b8' : '#718096';
        const unitColor = theme === 'dark' ? '#cbd5e0' : '#4a5568';
        
        return (
          <div
            key={index}
            className="relative flex min-h-[32px] flex-col justify-between overflow-hidden rounded-xl p-1.5 shadow-xl"
            style={{
              border: `1px solid ${cardBorder}`,
              background: cardBg,
              transition: 'background 0.3s ease, border-color 0.3s ease',
            }}
          >
            <div className="mb-0.5 flex items-center justify-between">
              <span 
                className="font-medium uppercase leading-tight tracking-wide"
                style={{ color: labelColor, fontSize: `${labelFontSize}px` }}
              >
                {card.label}
              </span>
              <span className="text-base opacity-90">{card.icon}</span>
            </div>
            <div className="flex items-baseline gap-1">
              <span className="text-base font-bold leading-none" style={{ color: card.accentColor }}>
                {card.value}
              </span>
              <span 
                className="font-medium"
                style={{ color: unitColor, fontSize: `${unitFontSize}px` }}
              >
                {card.unit}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

