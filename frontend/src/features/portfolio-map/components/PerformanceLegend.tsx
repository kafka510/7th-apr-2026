/**
 * Performance Legend Component for Portfolio Map
 */
 
import type { PerformanceFilter } from '../types';
import { useTheme } from '../../../contexts/ThemeContext';
import { useResponsiveFontSize } from '../../../utils/fontScaling';

interface PerformanceLegendProps {
  filter: PerformanceFilter;
  onFilterChange: (filter: PerformanceFilter) => void;
}

export function PerformanceLegend({ filter, onFilterChange }: PerformanceLegendProps) {
  const { theme } = useTheme();
  
  // Responsive font sizes
  const labelFontSize = useResponsiveFontSize(11, 15, 10);
  const buttonFontSize = useResponsiveFontSize(10, 14, 9);
  
  // Theme-aware colors
  const containerBg = theme === 'dark'
    ? 'linear-gradient(to bottom right, rgba(15, 23, 42, 0.9), rgba(30, 41, 59, 0.6))'
    : 'linear-gradient(to bottom right, rgba(255, 255, 255, 0.95), rgba(248, 250, 252, 0.9))';
  const containerBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(226, 232, 240, 0.8)';
  const labelColor = theme === 'dark' ? '#38bdf8' : '#0072ce';
  
  const buttons: Array<{ id: PerformanceFilter; label: string; gradient: string; textColor: string; borderColor: string }> = [
    {
      id: 'all',
      label: 'All Sites',
      gradient: 'linear-gradient(135deg, #6B7280 0%, #4B5563 100%)',
      textColor: 'black',
      borderColor: '#374151',
    },
    {
      id: 'excellent',
      label: '≥90%',
      gradient: 'linear-gradient(135deg, #2E8B57 0%, #228B22 100%)',
      textColor: 'white',
      borderColor: '#166534',
    },
    {
      id: 'good',
      label: '70-90%',
      gradient: 'linear-gradient(135deg, #FFB800 0%, #DAA520 100%)',
      textColor: 'white',
      borderColor: '#A16207',
    },
    {
      id: 'poor',
      label: '<70%',
      gradient: 'linear-gradient(135deg, #B22222 0%, #A40000 100%)',
      textColor: 'white',
      borderColor: '#991B1B',
    },
  ];

  return (
    <div className="w-full" style={{ height: '40px' }}>
      <div 
        className="flex w-full flex-row items-center gap-2 rounded-xl px-3 py-1.5 shadow-xl" 
        style={{ 
          height: '40px',
          border: `1px solid ${containerBorder}`,
          background: containerBg,
          transition: 'background 0.3s ease, border-color 0.3s ease',
        }}
      >
        <div 
          className="whitespace-nowrap font-bold"
          style={{ color: labelColor, transition: 'color 0.3s ease', fontSize: `${labelFontSize}px` }}
        >
          Yield Achievement:
        </div>
        <div className="flex flex-1 flex-row items-center justify-end gap-1.5">
          {buttons.map((btn) => (
            <button
              key={btn.id}
              type="button"
              onClick={() => onFilterChange(btn.id)}
              className={`legend-btn rounded-md border-2 px-2 py-0.5 font-semibold transition-all duration-200 hover:scale-105 ${
                filter === btn.id ? 'active' : ''
              }`}
              style={{
                background: btn.gradient,
                color: btn.textColor,
                borderColor: btn.borderColor,
                fontSize: `${buttonFontSize}px`,
              }}
            >
              {btn.label}
            </button>
          ))}
        </div>
      </div>
      <style>{`
        .legend-btn {
          position: relative;
          overflow: hidden;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
        }
        .legend-btn:hover {
          transform: scale(1.05);
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
        }
        .legend-btn.active {
          transform: scale(1.1);
          box-shadow: 0 6px 16px rgba(0, 0, 0, 0.3);
          border-width: 3px !important;
        }
        .legend-btn:active {
          transform: scale(0.95);
        }
        .legend-btn.active::before {
          content: '';
          position: absolute;
          top: -2px;
          left: -2px;
          right: -2px;
          bottom: -2px;
          background: linear-gradient(45deg, #ffffff, #f0f0f0);
          border-radius: 8px;
          z-index: -1;
          opacity: 0.8;
        }
      `}</style>
    </div>
  );
}

