import type { YieldData, WaterfallStep } from '../types';

export function calculateWaterfallSteps(data: YieldData[]): WaterfallStep[] {
  // Helper to safely convert value to number
  const toNum = (val: number | string | undefined): number => {
    if (val === undefined) return 0;
    if (typeof val === 'number') return isNaN(val) ? 0 : val;
    if (typeof val === 'string') {
      const num = parseFloat(val);
      return isNaN(num) ? 0 : num;
    }
    return 0;
  };

  // Helper to sum a field across all data
  const sum = (key: keyof YieldData): number => {
    return data.reduce((acc, r) => acc + toNum(r[key]), 0);
  };

  // Helper for budget sum (treats empty/zero as valid)
  const sumBudget = (key: keyof YieldData): number => {
    return data.reduce((acc, r) => {
      const val = toNum(r[key]);
      return acc + (val || 0);
    }, 0);
  };

  return [
    { name: 'IC<br>Approved<br>Budget', value: sumBudget('ic_approved_budget'), type: 'absolute' },
    { name: 'Expected<br>Budget', value: sumBudget('expected_budget'), type: 'absolute' },
    { name: 'Weather<br>Loss or<br>Gain', value: sum('weather_loss_or_gain'), type: 'relative' },
    { name: 'Grid<br>Curtailment<br>Loss or Gain', value: sum('grid_curtailment'), type: 'relative' },
    { name: 'Grid<br>Outage', value: sum('grid_outage'), type: 'relative' },
    { name: 'Operation<br>Budget', value: sumBudget('operation_budget'), type: 'absolute' },
    { name: 'Breakdown<br>Loss', value: sum('breakdown_loss'), type: 'relative' },
    { name: 'Scheduled<br>Outage<br>Loss', value: sum('scheduled_outage_loss'), type: 'relative' },
    { name: '&nbsp;<br>Unclassified<br>Loss or Gain', value: sum('unclassified_loss'), type: 'relative' },
    { name: 'Actual<br>Generation', value: sum('actual_generation'), type: 'absolute' },
  ];
}

export function formatNumber(val: number | string): string {
  const num = typeof val === 'number' ? val : parseFloat(String(val));
  if (isNaN(num)) return '0';
  return num.toLocaleString('en-US', { maximumFractionDigits: 0 });
}

export function getWaterfallColors(steps: WaterfallStep[]): (string | null)[] {
  return steps.map((step) => {
    if (step.name === 'IC<br>Approved<br>Budget') return '#4CAF50'; // Green
    if (step.name === 'Actual<br>Generation') return '#1976D2'; // Blue
    if (step.type === 'relative') {
      return step.value < 0 ? '#FF4136' : '#8BC34A'; // Red for negative, light green for positive
    }
    return '#1976D2'; // Blue for other absolute values
  });
}

// Drill-down mapping
export const drillDownMap: Record<string, string> = {
  'IC<br>Approved<br>Budget': 'ic_approved_budget',
  'Expected<br>Budget': 'expected_budget',
  'Weather<br>Loss or<br>Gain': 'weather_loss_or_gain',
  'Grid<br>Curtailment<br>Loss or Gain': 'grid_curtailment',
  'Grid<br>Outage': 'grid_outage',
  'Operation<br>Budget': 'operation_budget',
  'Breakdown<br>Loss': 'breakdown_loss',
  'Scheduled<br>Outage<br>Loss': 'scheduled_outage_loss',
  '&nbsp;<br>Unclassified<br>Loss or Gain': 'unclassified_loss',
  'Actual<br>Generation': 'actual_generation',
};

