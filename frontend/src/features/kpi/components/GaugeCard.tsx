import type { GaugeInsight } from '../utils/gaugeInsights';
import { useTheme } from '../../../contexts/ThemeContext';
import { useResponsiveFontSize } from '../../../utils/fontScaling';

type GaugeCardProps = {
  label: string;
  actual: number;
  target: number;
  unit?: string;
  description?: string;
  loading?: boolean;
  gradientClass?: string;
  accentColor?: string;
  formatValue?: (value: number) => string;
  insight?: GaugeInsight | null;
};

const defaultNumberFormatter = new Intl.NumberFormat(undefined, {
  maximumFractionDigits: 1,
});

const defaultPercentFormatter = new Intl.NumberFormat(undefined, {
  maximumFractionDigits: 0,
});

const toneStyles: Record<
  'positive' | 'neutral' | 'negative',
  {
    badge: string;
    text: string;
    dot: string;
  }
> = {
  positive: {
    badge: 'bg-emerald-500/20 border-emerald-400/50 text-emerald-200',
    text: 'text-emerald-200',
    dot: 'bg-emerald-400/80',
  },
  neutral: {
    badge: 'bg-slate-500/20 border-slate-400/40 text-slate-200',
    text: 'text-slate-200',
    dot: 'bg-slate-400/70',
  },
  negative: {
    badge: 'bg-rose-500/20 border-rose-400/50 text-rose-200',
    text: 'text-rose-200',
    dot: 'bg-rose-400/80',
  },
};

export const GaugeCard = ({
  label,
  actual,
  target,
  unit,
  description,
  loading = false,
  gradientClass = 'from-slate-900 via-slate-900 to-slate-950',
  accentColor = 'rgba(56,189,248,0.85)',
  formatValue,
  insight,
}: GaugeCardProps) => {
  const { theme } = useTheme();
  
  // Responsive font sizes
  const titleFontSize = useResponsiveFontSize(12, 18, 9);
  const descriptionFontSize = useResponsiveFontSize(10, 16, 8);
  const insightTitleFontSize = useResponsiveFontSize(11, 17, 9);
  const badgeFontSize = useResponsiveFontSize(9, 15, 7);
  const labelFontSize = useResponsiveFontSize(16, 24, 12); // For "Actual:", "Target:", "Delta:"
  const deltaFontSize = useResponsiveFontSize(18, 28, 14); // For delta value
  const gaugeValueFontSize = useResponsiveFontSize(24, 36, 18); // For large gauge percentage (replaces text-2xl)
  const actualTargetFontSize = useResponsiveFontSize(24, 36, 18); // For actual/target values (replaces text-2xl)
  
  const titleColor = theme === 'dark' ? 'rgba(203, 213, 225, 0.9)' : '#475569';
  const descriptionColor = theme === 'dark' ? 'rgba(148, 163, 184, 0.7)' : '#64748b';
  const valueColor = theme === 'dark' ? '#ffffff' : '#1a1a1a';
  const gaugeBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.6)' : '#f8fafc';
  const gaugeBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(203, 213, 225, 0.7)';
  const innerGaugeBg = theme === 'dark' ? '#0f172a' : '#ffffff';
  const innerGaugeBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : 'rgba(226, 232, 240, 0.8)';
  const dividerColor = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : 'rgba(226, 232, 240, 0.8)';
  const insightTextColor = theme === 'dark' ? 'rgba(203, 213, 225, 0.7)' : '#64748b';
  const resolvedFormatter =
    formatValue ??
    ((value: number) => {
      if (unit === '%') {
        return `${defaultPercentFormatter.format(value)}${unit}`;
      }
      return `${defaultNumberFormatter.format(value)}${unit ? ` ${unit}` : ''}`;
    });

  const hasBaseline = target > 0;
  const percentage = hasBaseline ? (actual / target) * 100 : 0;
  const clampedPercentage = Math.max(0, Math.min(percentage, 160));
  const exceeds100 = percentage > 100;
  
  // Calculate gauge sweep and background
  let gaugeBackground: string;
  
  if (percentage <= 100) {
    // Normal case: fill up to the percentage
    const gaugeSweep = Math.min(clampedPercentage, 100);
    gaugeBackground = `conic-gradient(${accentColor} ${gaugeSweep}%, rgba(148,163,184,0.15) ${gaugeSweep}% 100%)`;
  } else {
    // Over 100%: fill 0-100% with accent color, 100%-actual with darker accent color
    const gaugeSweep = Math.min(clampedPercentage, 120);
    // Extract RGB values from accent color and create a darker version (60% opacity instead of 85%)
    const darkerAccent = accentColor.replace(/[\d.]+\)$/, '0.35)'); // Reduce opacity for darker effect
    gaugeBackground = `conic-gradient(${accentColor} 100%, ${darkerAccent} 100% ${gaugeSweep}%, rgba(148,163,184,0.15) ${gaugeSweep}% 100%)`;
  }

  // Extract RGB values from accent color for glow effect
  const extractRgb = (rgba: string): [number, number, number] => {
    const match = rgba.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
    if (match) {
      return [parseInt(match[1]), parseInt(match[2]), parseInt(match[3])];
    }
    // Default to sky-400 if parsing fails
    return [56, 189, 248];
  };

  const [r, g, b] = extractRgb(accentColor);
  
  // Create glowing box-shadow effect similar to charts
  // Multiple shadow layers for glitter/glow effect
  const glowShadow = exceeds100
    ? `0 0 8px rgba(${r}, ${g}, ${b}, 0.6), 0 0 16px rgba(${r}, ${g}, ${b}, 0.4), 0 0 24px rgba(${r}, ${g}, ${b}, 0.3), 0 2px 8px rgba(${r}, ${g}, ${b}, 0.5)`
    : `0 0 6px rgba(${r}, ${g}, ${b}, 0.5), 0 0 12px rgba(${r}, ${g}, ${b}, 0.3), 0 2px 6px rgba(${r}, ${g}, ${b}, 0.4)`;
  
  // Enhanced glow on hover
  const hoverGlowShadow = `0 0 12px rgba(${r}, ${g}, ${b}, 0.8), 0 0 24px rgba(${r}, ${g}, ${b}, 0.6), 0 0 36px rgba(${r}, ${g}, ${b}, 0.4), 0 4px 12px rgba(${r}, ${g}, ${b}, 0.6)`;

  const delta = actual - target;
  const deltaLabel =
    Math.abs(delta) < 0.001
      ? 'In line with forecast'
      : `${delta > 0 ? '+' : ''}${defaultNumberFormatter.format(delta)}${unit ? ` ${unit}` : ''}`;

  return (
    <>
      {/* CSS Animations for glowing effect */}
      <style>{`
        @keyframes pulse-glow {
          0%, 100% {
            filter: drop-shadow(0 0 4px rgba(255, 215, 0, 0.6)) drop-shadow(0 0 8px rgba(${r}, ${g}, ${b}, 0.4));
          }
          50% {
            filter: drop-shadow(0 0 8px rgba(255, 215, 0, 0.9)) drop-shadow(0 0 16px rgba(${r}, ${g}, ${b}, 0.6));
          }
        }
        @keyframes pulse-marker {
          0%, 100% {
            opacity: 1;
            transform: translate(-50%, -4px) scale(1);
          }
          50% {
            opacity: 0.7;
            transform: translate(-50%, -4px) scale(1.2);
          }
        }
      `}</style>
      <div
        className={`group relative overflow-hidden rounded-lg bg-gradient-to-br ${gradientClass} p-1.5 shadow-md shadow-slate-950/40 transition-all hover:shadow-lg`}
      >
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_right,_rgba(255,255,255,0.08),_transparent_60%)]" />
        <div className="relative flex flex-col gap-1.5 overflow-visible">
        {/* Title */}
        <div className="text-center">
          <p 
            className="font-semibold uppercase tracking-wide"
            style={{ color: titleColor, fontSize: `${titleFontSize}px` }}
          >
            {label}
          </p>
          {description ? (
            <p 
              className="mt-0.5 line-clamp-1"
              style={{ color: descriptionColor, fontSize: `${descriptionFontSize}px` }}
            >
              {description}
            </p>
          ) : null}
        </div>

        {/* Main Content: Gauge on Left, Details on Right - Aligned at same height */}
        <div className="flex items-center justify-between gap-2 overflow-visible">
          {/* Large Gauge on Left */}
          <div
            className="relative size-36 shrink-0 overflow-visible rounded-full border-4 p-3 ring-1 transition-all duration-300 group-hover:scale-105"
            style={{
              background: gaugeBackground,
              borderColor: gaugeBorder,
              backgroundColor: gaugeBg,
              boxShadow: `${theme === 'dark' ? 'inset 0 2px 4px rgba(0, 0, 0, 0.6), ' : 'inset 0 2px 4px rgba(0, 0, 0, 0.1), '}${glowShadow}`,
              filter: exceeds100 ? 'drop-shadow(0 0 4px rgba(255, 215, 0, 0.6))' : 'none',
              animation: exceeds100 ? 'pulse-glow 2s ease-in-out infinite' : 'none',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.boxShadow = `${theme === 'dark' ? 'inset 0 2px 4px rgba(0, 0, 0, 0.6), ' : 'inset 0 2px 4px rgba(0, 0, 0, 0.1), '}${hoverGlowShadow}`;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.boxShadow = `${theme === 'dark' ? 'inset 0 2px 4px rgba(0, 0, 0, 0.6), ' : 'inset 0 2px 4px rgba(0, 0, 0, 0.1), '}${glowShadow}`;
            }}
          >
            {/* 100% Marker - Visual indicator when gauge exceeds 100% */}
            {exceeds100 && (
              <>
                {/* Marker line at 100% position (top of gauge) */}
                <div
                  className="pointer-events-none absolute left-1/2 top-0 z-10 h-3 w-0.5"
                  style={{
                    backgroundColor: '#ffd700',
                    boxShadow: `0 0 4px rgba(255, 215, 0, 0.8), 0 0 8px rgba(255, 215, 0, 0.6)`,
                    transform: 'translateX(-50%)',
                    animation: 'pulse-marker 1.5s ease-in-out infinite',
                  }}
                />
                {/* Marker dot at 100% position */}
                <div
                  className="pointer-events-none absolute left-1/2 top-0 z-10 size-2 rounded-full"
                  style={{
                    backgroundColor: '#ffd700',
                    boxShadow: `0 0 6px rgba(255, 215, 0, 1), 0 0 12px rgba(255, 215, 0, 0.8)`,
                    transform: 'translate(-50%, -4px)',
                    animation: 'pulse-marker 1.5s ease-in-out infinite',
                  }}
                />
              </>
            )}
            <div 
              className="absolute inset-3 flex flex-col items-center justify-center gap-0 rounded-full border text-center"
              style={{
                borderColor: innerGaugeBorder,
                backgroundColor: innerGaugeBg,
              }}
            >
              <span 
                className="font-bold leading-tight"
                style={{ color: valueColor, fontSize: `${gaugeValueFontSize}px` }}
              >
                {loading
                  ? '—'
                  : hasBaseline
                  ? `${defaultPercentFormatter.format(Math.max(0, percentage))}%`
                  : '—'}
              </span>
              <span 
                className="uppercase leading-tight tracking-wide"
                style={{ color: descriptionColor, fontSize: `${descriptionFontSize}px` }}
              >
                vs target
              </span>
            </div>
          </div>

          {/* Actual, Target, Delta on Right - Aligned with gauge */}
          <div className="flex flex-1 flex-col gap-0.5" style={{ fontSize: `${descriptionFontSize}px` }}>
            <div className="flex items-baseline gap-1">
              <span 
                className="shrink-0 font-medium uppercase tracking-wide"
                style={{ color: descriptionColor, fontSize: `${labelFontSize}px` }}
              >
                Actual:
              </span>
              <p 
                className="truncate font-bold"
                style={{ color: valueColor, fontSize: `${actualTargetFontSize}px` }}
              >
                {loading ? '—' : resolvedFormatter(actual)}
              </p>
            </div>
            <div className="flex items-baseline gap-1">
              <span 
                className="shrink-0 font-medium uppercase tracking-wide"
                style={{ color: descriptionColor, fontSize: `${labelFontSize}px` }}
              >
                Target:
              </span>
              <p 
                className="truncate font-bold"
                style={{ color: valueColor, fontSize: `${actualTargetFontSize}px` }}
              >
                {loading ? '—' : resolvedFormatter(target)}
              </p>
            </div>
            <div className="flex items-baseline gap-1">
              <span 
                className="shrink-0 font-medium uppercase tracking-wide"
                style={{ color: descriptionColor, fontSize: `${labelFontSize}px` }}
              >
                Delta:
              </span>
              <p
                className="truncate font-semibold"
                style={{
                  fontSize: `${deltaFontSize}px`,
                  color: delta > 0 
                    ? theme === 'dark' ? '#6ee7b7' : '#059669'
                    : delta < 0 
                    ? theme === 'dark' ? '#fca5a5' : '#dc2626'
                    : theme === 'dark' ? '#cbd5e1' : '#64748b'
                }}
              >
                {loading ? '—' : deltaLabel}
              </p>
            </div>
          </div>
        </div>

        {/* Insight at Bottom */}
        {insight && !loading && (
          <div 
            className="border-t pt-1.5"
            style={{ borderColor: dividerColor }}
          >
            <div className="flex items-start justify-between gap-1">
              <div className="min-w-0 flex-1">
                <p className={`font-semibold ${toneStyles[insight.tone].text} truncate`} style={{ fontSize: `${insightTitleFontSize}px` }}>
                  {insight.headline}
                </p>
                <p 
                  className="mt-0.5 line-clamp-2"
                  style={{ color: insightTextColor, fontSize: `${descriptionFontSize}px` }}
                >
                  {insight.detail}
                </p>
              </div>
              <span
                className={`inline-flex shrink-0 items-center gap-0.5 rounded-full border px-1 py-0.5 font-semibold uppercase tracking-wide ${toneStyles[insight.tone].badge}`}
                style={{ fontSize: `${badgeFontSize}px` }}
              >
                <span className={`size-0.5 rounded-full ${toneStyles[insight.tone].dot}`} />
                {insight.tone === 'positive'
                  ? 'Above'
                  : insight.tone === 'negative'
                  ? 'Below'
                  : 'On'}
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
    </>
  );
};

