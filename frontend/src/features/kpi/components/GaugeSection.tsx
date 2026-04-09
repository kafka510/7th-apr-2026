import { useMemo } from 'react';
import { useTheme } from '../../../contexts/ThemeContext';
import { useResponsiveFontSize } from '../../../utils/fontScaling';

import type { KpiGaugeValues } from '../types';
import { buildGaugeInsights } from '../utils/gaugeInsights';

import { GaugeCard } from './GaugeCard';

type GaugeSectionProps = {
  values: KpiGaugeValues;
  loading?: boolean;
};

const energyFormatter = new Intl.NumberFormat(undefined, {
  maximumFractionDigits: 1,
});

const irradiationFormatter = new Intl.NumberFormat(undefined, {
  maximumFractionDigits: 2,
});

export const GaugeSection = ({ values, loading = false }: GaugeSectionProps) => {
  const { theme } = useTheme();
  
  // Responsive font sizes
  const labelFontSize = useResponsiveFontSize(8, 12, 7);
  const descriptionFontSize = useResponsiveFontSize(8, 12, 7);
  
  const insightsResult = useMemo(() => buildGaugeInsights(values), [values]);
  // Map insights by their ID for easy lookup
  const insightsMap = useMemo(() => {
    const map = new Map<string, typeof insightsResult.insights[0]>();
    insightsResult.insights.forEach((insight) => {
      map.set(insight.id, insight);
    });
    return map;
  }, [insightsResult]);

  const sectionBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.7)' : 'rgba(255, 255, 255, 0.95)';
  const sectionShadow = theme === 'dark' 
    ? '0 20px 25px -5px rgba(0, 0, 0, 0.4)' 
    : '0 10px 15px -3px rgba(0, 0, 0, 0.1)';
  const labelColor = theme === 'dark' ? '#64748b' : '#94a3b8';
  const titleColor = theme === 'dark' ? '#ffffff' : '#1a1a1a';
  const descriptionColor = theme === 'dark' ? '#94a3b8' : '#64748b';

  return (
    <section 
      className="space-y-1.5 rounded-xl p-1.5"
      style={{
        backgroundColor: sectionBg,
        boxShadow: sectionShadow,
      }}
    >
      <div className="flex flex-col gap-1 md:flex-row md:items-center md:justify-between">
        <div>
          <p 
            className="font-semibold uppercase tracking-[0.15em]"
            style={{ color: labelColor, fontSize: `${labelFontSize}px` }}
          >
            Performance Gauges
          </p>
          <h2 
            className="text-xs font-semibold md:text-sm"
            style={{ color: titleColor }}
          >
            Compare actual output against budgets and expected performance
          </h2>
        </div>
        <p 
          className="max-w-md"
          style={{ color: descriptionColor, fontSize: `${descriptionFontSize}px` }}
        >
          Gauges exclude Taiwan sites. Ratios above 100% indicate performance exceeding baseline.
        </p>
      </div>

      <div className="grid gap-1.5 lg:grid-cols-2">
        <GaugeCard
          label="IC Approved vs Actual"
          actual={values.actualGeneration}
          target={values.icBudget}
          unit="MWh"
          description="IC approved budget compared with actual generation."
          loading={loading}
          gradientClass="from-blue-500/15 via-blue-500/5 to-slate-950"
          accentColor="rgba(59,130,246,0.85)"
          formatValue={(value) => `${energyFormatter.format(value)} MWh`}
          insight={insightsMap.get('ic-budget') || null}
        />

        <GaugeCard
          label="Expected vs Actual"
          actual={values.actualGeneration}
          target={values.expectedBudget}
          unit="MWh"
          description="Forecast generation compared with actual generation."
          loading={loading}
          gradientClass="from-emerald-500/15 via-emerald-500/5 to-slate-950"
          accentColor="rgba(16,185,129,0.85)"
          formatValue={(value) => `${energyFormatter.format(value)} MWh`}
          insight={insightsMap.get('expected-budget') || null}
        />

        <GaugeCard
          label="Performance Ratio"
          actual={Math.max(0, values.actualPR * 100)}
          target={Math.max(0, values.expectedPR * 100)}
          unit="%"
          description="Actual PR against expected PR weighted by capacity."
          loading={loading}
          gradientClass="from-violet-500/15 via-violet-500/5 to-slate-950"
          accentColor="rgba(139,92,246,0.85)"
          formatValue={(value) => {
            // Backend now sends PR as decimal (0.8248 for 82.48%), we multiply by 100 to get percentage
            // Ensure we display as integer percentage
            const percentValue = Math.max(0, Math.round(value));
            return `${percentValue}%`;
          }}
          insight={insightsMap.get('performance-ratio') || null}
        />

        <GaugeCard
          label="Irradiation"
          actual={values.actualIrr}
          target={values.budgetIrr}
          unit="kWh/m²"
          description="Measured irradiation compared with budget."
          loading={loading}
          gradientClass="from-amber-500/15 via-amber-500/5 to-slate-950"
          accentColor="rgba(245,158,11,0.85)"
          formatValue={(value) => `${irradiationFormatter.format(value)} kWh/m²`}
          insight={insightsMap.get('irradiation') || null}
        />
      </div>
    </section>
  );
};

