import type { KpiGaugeValues } from '../types';

export type GaugeInsightTone = 'positive' | 'neutral' | 'negative';

export type GaugeInsight = {
  id: 'ic-budget' | 'expected-budget' | 'performance-ratio' | 'irradiation';
  label: string;
  tone: GaugeInsightTone;
  headline: string;
  detail: string;
};

export type GaugeInsightsSummary = {
  tone: GaugeInsightTone;
  headline: string;
  detail: string;
};

export type GaugeInsightsResult = {
  summary: GaugeInsightsSummary;
  insights: GaugeInsight[];
};

const isFiniteNumber = (value: unknown): value is number =>
  typeof value === 'number' && Number.isFinite(value);

const normaliseValue = (value: unknown): number | null => {
  if (isFiniteNumber(value)) {
    return value;
  }

  if (typeof value === 'string' && value.trim() !== '') {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }

  return null;
};

const safeRatio = (numerator: unknown, denominator: unknown): number | null => {
  const normalisedNumerator = normaliseValue(numerator);
  const normalisedDenominator = normaliseValue(denominator);

  if (
    normalisedNumerator === null ||
    normalisedDenominator === null ||
    normalisedDenominator === 0
  ) {
    return null;
  }

  return normalisedNumerator / normalisedDenominator;
};

const formatPercentage = (value: number, fractionDigits = 1) =>
  `${(value * 100).toFixed(fractionDigits)}%`;

const describeTone = (tone: GaugeInsightTone): GaugeInsightsSummary['headline'] => {
  switch (tone) {
    case 'positive':
      return 'Overall performance looks strong';
    case 'negative':
      return 'Performance needs attention';
    default:
      return 'Performance is mixed';
  }
};

const describeToneDetail = (tone: GaugeInsightTone): GaugeInsightsSummary['detail'] => {
  switch (tone) {
    case 'positive':
      return 'Most gauges are exceeding or meeting their targets.';
    case 'negative':
      return 'Several gauges are falling behind target thresholds.';
    default:
      return 'Strengths and gaps are balanced across gauges.';
  }
};

export const buildGaugeInsights = (values: KpiGaugeValues): GaugeInsightsResult => {
  const insights: GaugeInsight[] = [];

  const icRatio = safeRatio(values.actualGeneration, values.icBudget);
  if (icRatio !== null) {
    let tone: GaugeInsightTone = 'negative';
    let detail = 'Actual generation is below the IC approved budget.';

    if (icRatio >= 1) {
      tone = 'positive';
      detail = 'Actual generation is outperforming the IC approved budget.';
    } else if (icRatio >= 0.9) {
      tone = 'positive';
      detail = 'Actual generation is closely tracking the IC approved budget.';
    } else if (icRatio >= 0.8) {
      tone = 'neutral';
      detail = 'Actual generation is within 20% of the IC approved budget.';
    }

    insights.push({
      id: 'ic-budget',
      label: 'IC vs Actual',
      tone,
      headline: `${formatPercentage(icRatio)} of IC budget`,
      detail,
    });
  }

  const expectedRatio = safeRatio(values.actualGeneration, values.expectedBudget);
  if (expectedRatio !== null) {
    let tone: GaugeInsightTone = 'negative';
    let detail = 'Actual generation is trailing the expected forecast.';

    if (expectedRatio >= 1) {
      tone = 'positive';
      detail = 'Actual generation is exceeding the expected forecast.';
    } else if (expectedRatio >= 0.9) {
      tone = 'positive';
      detail = 'Actual generation is broadly in line with the expected forecast.';
    }

    insights.push({
      id: 'expected-budget',
      label: 'Expected vs Actual',
      tone,
      headline: `${formatPercentage(expectedRatio)} of expected`,
      detail,
    });
  }

  const prExpected = normaliseValue(values.expectedPR);
  const prActual = normaliseValue(values.actualPR);
  if (prExpected !== null && prActual !== null && prExpected > 0 && prActual > 0) {
    const delta = prActual - prExpected;
    let tone: GaugeInsightTone = 'neutral';
    let detail = 'Actual PR matches the weighted expected PR.';

    if (delta > 0.5) {
      tone = 'positive';
      detail = 'Actual PR is comfortably above the weighted expectation.';
    } else if (delta > 0) {
      tone = 'positive';
      detail = 'Actual PR is slightly above the weighted expectation.';
    } else if (delta < -0.5) {
      tone = 'negative';
      detail = 'Actual PR is materially below the weighted expectation.';
    } else if (delta < 0) {
      tone = 'negative';
      detail = 'Actual PR is fractionally below the weighted expectation.';
    }

    insights.push({
      id: 'performance-ratio',
      label: 'Performance Ratio',
      tone,
      headline: `${(prActual * 100).toFixed(1)}% actual vs ${(prExpected * 100).toFixed(
        1,
      )}% expected`,
      detail,
    });
  }

  const irrRatio = safeRatio(values.actualIrr, values.budgetIrr);
  if (irrRatio !== null) {
    let tone: GaugeInsightTone = 'negative';
    let detail = 'Measured irradiation is below the budgeted level.';

    if (irrRatio >= 1) {
      tone = 'positive';
      detail = 'Measured irradiation is ahead of the budgeted level.';
    } else if (irrRatio >= 0.9) {
      tone = 'neutral';
      detail = 'Measured irradiation is within 10% of the budgeted level.';
    }

    insights.push({
      id: 'irradiation',
      label: 'Irradiation',
      tone,
      headline: `${formatPercentage(irrRatio)} of budget`,
      detail,
    });
  }

  const toneScores = insights.reduce(
    (acc, insight) => {
      acc[insight.tone] += 1;
      return acc;
    },
    { positive: 0, neutral: 0, negative: 0 } as Record<GaugeInsightTone, number>,
  );

  let summaryTone: GaugeInsightTone = 'neutral';
  if (toneScores.positive > toneScores.negative && toneScores.positive > 0) {
    summaryTone = 'positive';
  } else if (toneScores.negative > toneScores.positive && toneScores.negative > 0) {
    summaryTone = 'negative';
  }

  if (insights.length === 0) {
    return {
      summary: {
        tone: 'neutral',
        headline: 'Gauge data not available',
        detail: 'No valid gauge data was returned for the current filters.',
      },
      insights,
    };
  }

  const summary: GaugeInsightsSummary = {
    tone: summaryTone,
    headline: describeTone(summaryTone),
    detail: describeToneDetail(summaryTone),
  };

  return { summary, insights };
};


