import type { BessV1Aggregates } from '../types';
import { useTheme } from '../../../contexts/ThemeContext';

interface BessV1KPIsProps {
  aggregates: BessV1Aggregates | null;
  loading: boolean;
}

interface MetricDescriptor {
  label: string;
  actualValue: number | null;
  budgetValue: number | null;
  unit: string;
  decimals: number;
  threshold?: number;
  target?: number;
  icon: string;
}

const cardBaseStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  padding: '6px 8px',
  borderRadius: '8px',
  minHeight: '50px',
  gap: '6px',
};

const statusColors: Record<'good' | 'warn' | 'bad', { border: string; background: string; icon: string }> = {
  good: { border: '#22c55e', background: 'rgba(34, 197, 94, 0.1)', icon: '#22c55e' },
  warn: { border: '#fb923c', background: 'rgba(251, 146, 60, 0.1)', icon: '#fb923c' },
  bad: { border: '#f87171', background: 'rgba(248, 113, 113, 0.1)', icon: '#f87171' },
};

function formatValue(value: number | null, decimals: number, unit: string): string {
  if (value === null || Number.isNaN(value)) return '—';
  return `${value.toFixed(decimals)}${unit}`;
}

function getStatus(actual: number | null, threshold?: number, target?: number): 'good' | 'warn' | 'bad' | null {
  if (actual === null || threshold === undefined || target === undefined) return null;
  if (actual >= target) return 'good';
  if (actual >= threshold) return 'warn';
  return 'bad';
}

export function BessV1KPIs({ aggregates, loading }: BessV1KPIsProps) {
  const { theme } = useTheme();
  
  // Theme-aware colors
  const containerBg = theme === 'dark'
    ? 'linear-gradient(to bottom right, rgba(15, 23, 42, 0.9), rgba(30, 41, 59, 0.6))'
    : 'linear-gradient(to bottom right, rgba(255, 255, 255, 0.95), rgba(248, 250, 252, 0.9))';
  const containerBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(226, 232, 240, 0.8)';
  const cardBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.6)' : 'rgba(255, 255, 255, 0.8)';
  const cardBorder = theme === 'dark' ? '#475569' : '#cbd5e0';
  const labelColor = theme === 'dark' ? '#cbd5e1' : '#4a5568';
  const valueColor = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';
  const loadingColor = theme === 'dark' ? '#38bdf8' : '#0072ce';
  const noDataColor = theme === 'dark' ? '#94a3b8' : '#718096';
  
  if (loading) {
    return (
      <div style={{ padding: '20px', textAlign: 'center', color: loadingColor }}>
        Loading KPIs...
      </div>
    );
  }

  if (!aggregates) {
    return (
      <div style={{ padding: '16px', textAlign: 'center', color: noDataColor }}>
        No data available for the selected filters.
      </div>
    );
  }

  const budgetVsActualMetrics: MetricDescriptor[] = [
    {
      label: 'CUF (%) Actual vs Budget',
      actualValue: aggregates.cufPctOverall,
      budgetValue: aggregates.budgetCUF,
      unit: '%',
      decimals: 1,
      threshold: 2.5,
      target: 3.0,
      icon: '⚡',
    },
    {
      label: 'Cycles Actual vs Budget',
      actualValue: aggregates.actualCycles,
      budgetValue: aggregates.budgetCycles,
      unit: '',
      decimals: 0,
      threshold: 15,
      target: 20,
      icon: '🔁',
    },
    {
      label: 'Average RTE (%) Actual vs Budget',
      actualValue: aggregates.avgRTEpct,
      budgetValue: aggregates.budgetRTEpct,
      unit: '%',
      decimals: 1,
      threshold: 90,
      target: 95,
      icon: '🔋',
    },
  ];

  const standardMetrics = [
    { label: 'Battery Capacity (MWh)', value: aggregates.totalCapMWh, unit: ' MWh', decimals: 1, icon: '📦' },
    { label: 'Min SOC (%)', value: aggregates.minSOC, unit: '%', decimals: 1, icon: '📉' },
    { label: 'Max SOC (%)', value: aggregates.maxSOC, unit: '%', decimals: 1, icon: '📈' },
    { label: 'Min ESS Temp (°C)', value: aggregates.minTemp, unit: '°C', decimals: 1, icon: '❄️' },
    { label: 'Max ESS Temp (°C)', value: aggregates.maxTemp, unit: '°C', decimals: 1, icon: '🔥' },
  ];

  return (
    <div
      className="rounded-xl shadow-xl"
      style={{
        margin: '0 8px 8px 8px',
        padding: '8px',
        border: `1px solid ${containerBorder}`,
        background: containerBg,
        overflow: 'visible',
        position: 'relative',
        transition: 'background 0.3s ease, border-color 0.3s ease',
      }}
    >
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(8, 1fr)',
          gap: '6px',
          overflow: 'visible',
        }}
      >
        {budgetVsActualMetrics.map((metric) => {
          const status = getStatus(metric.actualValue, metric.threshold, metric.target);
          const colors = status ? statusColors[status] : null;
          const displayValue =
            metric.actualValue === null && metric.budgetValue === null
              ? '—'
              : `${formatValue(metric.actualValue, metric.decimals, metric.unit)} / ${formatValue(metric.budgetValue, metric.decimals, metric.unit)}`;

          return (
            <div
              key={metric.label}
              className="rounded-xl shadow-xl"
              style={{
                ...cardBaseStyle,
                border: `1px solid ${colors?.border ?? cardBorder}`,
                background: colors?.background ?? cardBg,
                transition: 'background 0.3s ease, border-color 0.3s ease',
              }}
            >
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: '0.55rem', fontWeight: 600, color: labelColor, lineHeight: '1.1', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{metric.label}</div>
                <div style={{ fontSize: '0.75rem', fontWeight: 700, color: valueColor, marginTop: '2px', lineHeight: '1.1' }}>
                  {displayValue}
                </div>
              </div>
              <div style={{ fontSize: '1.1rem', color: colors?.icon ?? '#0072ce', flexShrink: 0 }}>{metric.icon}</div>
            </div>
          );
        })}

        {standardMetrics.map((metric) => (
          <div 
            key={metric.label} 
            className="rounded-xl shadow-xl" 
            style={{
              ...cardBaseStyle,
              border: `1px solid ${cardBorder}`,
              background: cardBg,
              transition: 'background 0.3s ease, border-color 0.3s ease',
            }}
          >
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: '0.55rem', fontWeight: 600, color: labelColor, lineHeight: '1.1', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{metric.label}</div>
              <div style={{ fontSize: '0.75rem', fontWeight: 700, color: valueColor, marginTop: '2px', lineHeight: '1.1' }}>
                {formatValue(metric.value ?? null, metric.decimals, metric.unit)}
              </div>
            </div>
            <div style={{ fontSize: '1.1rem', color: '#0072ce', flexShrink: 0 }}>{metric.icon}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

