/* eslint-disable @typescript-eslint/no-namespace */
/* eslint-disable @typescript-eslint/no-explicit-any */
import { useRef } from 'react';
import Plot from 'react-plotly.js';
import type { WaterfallStep } from '../types';
import { formatNumber, getWaterfallColors, drillDownMap } from '../utils/waterfall';
import { useResponsiveFontSize } from '../../../utils/fontScaling';

// Type declarations for Plotly
declare namespace Plotly {
  interface PlotMouseEvent {
    points: Array<{
      pointNumber: number;
      x: any;
      y: any;
      data: any;
      fullData: any;
    }>;
    event: MouseEvent;
  }

  interface Config {
    responsive?: boolean;
    displayModeBar?: boolean;
    staticPlot?: boolean;
    editable?: boolean;
    scrollZoom?: boolean;
    doubleClick?: 'reset' | 'autosize' | 'reset+autosize' | false;
    showTips?: boolean;
  }

  namespace Plots {
    function resize(element: HTMLElement): void;
  }
}

interface WaterfallChartProps {
  steps: WaterfallStep[];
  title?: string;
  onBarClick?: (category: string) => void;
}

export function WaterfallChart({ steps, title = 'Yield Analysis', onBarClick }: WaterfallChartProps) {
  const plotDivRef = useRef<HTMLDivElement>(null);
  
  // Responsive font size for data labels: 31.5px base, scales between 21px (laptops) and 42px (large monitors)
  const dataLabelFontSize = useResponsiveFontSize(31.5, 42, 21);

  const xCategories = steps.map((s) => s.name);
  const colors = getWaterfallColors(steps);

  const trace = {
    type: 'waterfall' as const,
    orientation: 'v' as const,
    measure: steps.map((s) => s.type),
    x: xCategories,
    y: steps.map((s) => s.value),
    text: steps.map((s) => (s.value === 0 ? '0' : formatNumber(s.value))),
    textposition: 'outside' as const,
    textfont: {
      size: dataLabelFontSize,
      color: '#e2e8f0',
      family: 'Arial, sans-serif',
    },
    hoverinfo: 'x+y' as const,
    showlegend: false,
    marker: {
      // ✅ FIX: Force "IC Approved Budget" to green, use colors array for others
      color: steps.map((step, i) => {
        // Explicitly check for IC Approved Budget (with <br> tags as used in the step name)
        if (step.name === 'IC<br>Approved<br>Budget') {
          return '#22c55e'; // Bright green for IC Approved Budget
        }
        // Fallback to colors array, handling null values
        return colors[i] ?? colors[i - 1] ?? '#1976D2';
      }),
      line: {
        // ✅ FIX: Use Plotly-native borders with thicker width and glow color for IC Approved Budget
        width: steps.map((step) => 
          step.name === 'IC<br>Approved<br>Budget' ? 4 : 2
        ),
        color: steps.map((step) => 
          step.name === 'IC<br>Approved<br>Budget'
            ? 'rgba(22,163,74,0.9)' // Semi-transparent green border for glow effect
            : '#020617' // Dark border for other bars
        ),
      },
    },
    connector: {
      line: { color: '#475569' },
    },
  };

  const yMax = Math.max(...steps.map((s) => s.value), 1) * 1.15;

  const layout = {
    title: {
      text: title,
      font: { size: 18, family: 'Arial Black, Arial, sans-serif', color: '#e2e8f0' },
    },
    xaxis: {
      title: {
        font: { size: 14, family: 'Arial Black, Arial, sans-serif', color: '#cbd5e1' },
      },
      tickfont: { size: 12, family: 'Arial, sans-serif', color: '#cbd5e1' },
      tickmode: 'array' as const,
      tickvals: xCategories,
      ticktext: xCategories.map((name, i) => (i % 2 === 0 ? `<b>${name}</b>` : name)),
      tickangle: 0,
      automargin: true,
      fixedrange: true,
      gridcolor: '#334155',
    },
    yaxis: {
      title: {
        text: 'Energy (MWh)',
        font: { size: 14, color: '#cbd5e1' },
      },
      tickfont: { size: 12, color: '#cbd5e1' },
      zeroline: true,
      range: [0, yMax],
      fixedrange: true,
      gridcolor: '#334155',
    },
    hovermode: false as const,
    autosize: true,
    height: 600,
    margin: { t: 50, b: 80, l: 80, r: 20 },
    dragmode: false as const,
    showlegend: false,
    plot_bgcolor: '#0f172a',
    paper_bgcolor: '#0f172a',
  };

  const config = {
    responsive: true,
    displayModeBar: true,
    modeBarButtonsToRemove: ['zoom2d', 'pan2d', 'select2d', 'lasso2d', 'zoomIn2d', 'zoomOut2d', 'autoScale2d', 'resetScale2d'],
    displaylogo: false,
    toImageButtonOptions: {
      format: 'png',
      filename: 'yield_waterfall_chart',
      height: 1000,
      width: 1400,
      scale: 2
    },
    staticPlot: false,
    editable: false,
    scrollZoom: false,
    doubleClick: 'reset',
    showTips: false,
  } as Partial<Plotly.Config>;

  // Click handling is done via the onClick prop in the Plot component below

  // Calculate percentage annotations
  const maxY = Math.max(...steps.map((step) => Math.abs(step.value)));
  const percentY = maxY * 0.1;
  const percentages = steps.map((step) => {
    const expectedBudgetValue = steps[1]?.value || 0;
    return expectedBudgetValue && expectedBudgetValue !== 0
      ? (step.value / expectedBudgetValue) * 100
      : 0;
  });

  const annotations = steps.map((_step, i) => ({
    x: xCategories[i],
    y: percentY,
    text: `<b>${Math.round(percentages[i])}%</b>`,
    showarrow: false,
    font: {
      size: 22.5, // 1.5x increase to match data label font size increase
      color: '#000',
      family: 'Arial, sans-serif',
    },
    xanchor: 'center' as const,
    yanchor: 'middle' as const,
    align: 'center' as const,
  }));

  const handlePlotClick = (event: any) => {
    if (event?.points && event.points.length > 0) {
      const point = event.points[0];
      const category = xCategories[point.pointNumber];
      const drillDownCategory = drillDownMap[category];
      if (drillDownCategory && onBarClick) {
        onBarClick(drillDownCategory);
      }
    }
  };

  // ❌ REMOVED: DOM/CSS mutation effects that don't work in exported images
  // Plotly exports images from its internal SVG/canvas, ignoring DOM/CSS hacks
  // All styling is now done via Plotly-native marker.color and marker.line properties above

  return (
    <div ref={plotDivRef} className="waterfall-bar-container w-full">
      <Plot 
        data={[trace]} 
        layout={{ ...layout, annotations }} 
        config={config}
        onClick={handlePlotClick}
      />
    </div>
  );
}

