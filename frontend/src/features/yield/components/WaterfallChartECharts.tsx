import { useEffect, useMemo, useRef, useState } from 'react';
import ReactECharts from 'echarts-for-react';
import type { WaterfallStep } from '../types';

interface Props {
  steps: WaterfallStep[];
  title?: string;
  // 'dark' | 'light' from ThemeContext to match app theme
  theme?: 'dark' | 'light';
}

/** Laptop breakpoint: below this = laptop (reduced fonts, rotated labels). Above = big monitor (current layout). */
const LAPTOP_BREAKPOINT = 1400;

export function WaterfallChartECharts({
  steps,
  title = 'Yield Analysis',
  theme = 'dark',
}: Props) {
  const chartRef = useRef<ReactECharts>(null);
  const [isLaptop, setIsLaptop] = useState(
    () => typeof window !== 'undefined' && window.innerWidth < LAPTOP_BREAKPOINT,
  );

  useEffect(() => {
    const onResize = () => {
      setIsLaptop(window.innerWidth < LAPTOP_BREAKPOINT);
    };
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  const option = useMemo(() => {
    /* ------------------------------------------------------------------
       1️⃣ TRUE WATERFALL: TOTALS FROM ZERO, LOSSES RELATIVE TO LAST TOTAL
       ------------------------------------------------------------------ */
    let lastTotalBaseline = 0;

    const baseData: number[] = [];
    const visibleData: number[] = [];

    // Identify TOTAL bars by their label (business rule)
    // Use the exact prefixes from the step names so totals are classified correctly.
    const TOTAL_KEYWORDS = [
      'IC<br>Approved',      // IC Approved Budget
      'Expected<br>Budget',  // Expected Budget
      'Operation<br>Budget', // Operational Budget
      'Actual<br>Generation',// Actual Generation
    ];

    steps.forEach((step) => {
      const isTotal = TOTAL_KEYWORDS.some((k) => step.name.startsWith(k));

      if (isTotal) {
        // TOTAL bars always start from zero
        baseData.push(0);
        visibleData.push(step.value);
        // This total becomes the new baseline for subsequent losses/gains
        lastTotalBaseline = step.value;
        return;
      }

      // RELATIVE bars (loss or gain) are rendered as positive-height deltas
      const magnitude = Math.abs(step.value);

      if (step.value < 0) {
        // LOSS → step DOWN from last total using base shift
        const base = lastTotalBaseline - magnitude;
        baseData.push(base);
        visibleData.push(magnitude);
        lastTotalBaseline = base;
      } else {
        // GAIN → step UP from last total
        baseData.push(lastTotalBaseline);
        visibleData.push(magnitude);
        lastTotalBaseline += magnitude;
      }
    });
    
    
    
    
    
    
    
    
    
    /* ------------------------------------------------------------------
       2️⃣ PERCENTAGE CALCULATION (MATCHES YOUR PLOTLY LOGIC)
       ------------------------------------------------------------------ */
    const expectedBudget = steps[1]?.value || 0;

    const percentages = steps.map((s) =>
      expectedBudget !== 0 ? (s.value / expectedBudget) * 100 : 0,
    );

    /* ------------------------------------------------------------------
       3️⃣ RESPONSIVE FONT SIZES & LAYOUT (Laptop vs Big Monitor)
       - Laptop (< 1400px): smaller fonts, horizontal labels (alternating up/down), wider bars, less right margin
       - Big monitor (≥ 1400px): current layout unchanged
       ------------------------------------------------------------------ */
    const width = typeof window !== 'undefined' ? window.innerWidth : 1920;
    const isNarrowViewport = width < LAPTOP_BREAKPOINT;
    const isLargeScreen = width >= 1600;

    // Laptop: reduced fonts to prevent overlap with horizontal labels. Big monitor: unchanged.
    const valueFontSize = isNarrowViewport ? 11 : (isLargeScreen ? 18 : 16);
    const percentFontSize = isNarrowViewport ? 9 : (isLargeScreen ? 13 : 11);
    const axisFontSize = isNarrowViewport ? 9 : (isLargeScreen ? 13 : 12);
    const titleFontSize = isNarrowViewport ? 13 : (isLargeScreen ? 18 : 16);

    // Laptop: horizontal labels (alternating up/down), wider bars, minimal right margin
    const gridBottom = isNarrowViewport ? 120 : 110;
    const barWidth = isNarrowViewport ? 36 : (isLargeScreen ? 44 : 36);
    const gridRight = isNarrowViewport ? 8 : 28;

    const isDark = theme === 'dark';
    // Use brighter colors for better visibility in dark mode
    const textColor = isDark ? '#f1f5f9' : '#0f172a';
    const axisColor = isDark ? '#e2e8f0' : '#475569';
    const labelValueColor = isDark ? '#f1f5f9' : '#0f172a';
    const labelBgColor = isDark ? 'rgba(15,23,42,0.9)' : 'rgba(255,255,255,0.9)';
    const gridLineColor = isDark ? '#334155' : '#e2e8f0';
    // Theme-aware colors for percentage annotations - ensure good contrast
    const percentTextColor = isDark ? '#f9fafb' : '#0f172a';

    /* ------------------------------------------------------------------
       4️⃣ PERCENTAGE OVERLAY (USING markPoint SO LABELS ACTUALLY RENDER)
       ------------------------------------------------------------------ */
    const maxVisible = Math.max(...visibleData, 0);
    const percentY = maxVisible * 0.12;

    return {
      // Use transparent background so the parent card gradient/theme shows through
      backgroundColor: 'transparent',

      title: {
        text: title,
        left: 'center',
        textStyle: {
          color: textColor,
          fontSize: titleFontSize,
          fontWeight: 700,
        },
        // Add horizontal padding so first/last characters are not clipped
        padding: [0, 16, 0, 16],
      },

      grid: {
        top: 52,
        left: isNarrowViewport ? 38 : 30,
        right: gridRight,
        bottom: gridBottom,
      },

      xAxis: {
        type: 'category',
        data: steps.map((s) => s.name.replace(/<br>/g, '\n')),
        axisTick: { alignWithLabel: true },
        axisLabel: {
          color: axisColor,
          fontSize: axisFontSize,
          lineHeight: 12,
          margin: isNarrowViewport ? 18 : 20,
          interval: 0,
          rotate: 0,
          // Alternating up/down labels to avoid overlap in horizontal mode
          formatter: (value: string, index: number) => {
            const isEven = index % 2 === 0;
            const style = isEven ? 'labelUpBold' : 'labelDownBold';
            return `{${style}|${value}}`;
          },
          fontWeight: 700,
          rich: {
            labelUpBold: {
              fontWeight: 700,
              fontSize: axisFontSize,
              color: axisColor,
              padding: [6, 0, 0, 0],
            },
            labelDownBold: {
              fontWeight: 700,
              fontSize: axisFontSize,
              color: axisColor,
              padding: [0, 0, 6, 0],
            },
          },
        },
        axisLine: {
          lineStyle: { color: gridLineColor },
        },
      },

      yAxis: {
        type: 'value',
        axisLabel: {
          color: axisColor,
          fontSize: axisFontSize,
          // Format axis ticks in K format (e.g., 350K instead of 350000), integers only
          formatter: (val: number) => {
            const rounded = Math.round(val);
            const abs = Math.abs(rounded);
            if (abs >= 1000) {
              const k = Math.round(rounded / 1000);
              return `${k}K`;
            }
            return String(rounded);
          },
        },
        axisLine: {
          lineStyle: { color: gridLineColor },
        },
        splitLine: {
          lineStyle: { color: gridLineColor },
        },
      },

      series: [
        /* --------------------------------------------------------------
           INVISIBLE BASE (CRITICAL FOR WATERFALL)
           -------------------------------------------------------------- */
        {
          type: 'bar',
          stack: 'total',
          barGap: '-100%',
          itemStyle: {
            color: 'transparent',
          },
          data: baseData,
        },

        /* --------------------------------------------------------------
           VISIBLE WATERFALL BARS (STYLED)
           -------------------------------------------------------------- */
        {
          type: 'bar',
          stack: 'total',
          barWidth,
          data: visibleData,

          itemStyle: {
            // Rounded tops for a premium look similar to BESS dashboard
            borderRadius: [12, 12, 0, 0],

            // Per-bar color mapping
            color: (params: any) => {
              const step = steps[params.dataIndex];

              if (step.name.includes('IC')) return '#16a34a'; // IC Approved
              // Always make losses red for clarity
              if (step.type === 'relative' && step.value < 0) return '#ff3b30'; // Loss
              if (step.type === 'relative') return '#22c55e'; // Gain
              return '#0ea5e9'; // Expected / Actual
            },

            // Soft outer glow around bars (no hard block at the bottom)
            shadowBlur: (params: any) => {
              const step = steps[params.dataIndex];
              return step.type === 'relative' ? 10 : 18;
            },
            shadowOffsetX: 0,
            // Keep shadow centered on the bar, not dropped below the x-axis
            shadowOffsetY: 0,

            shadowColor: (params: any) => {
              const step = steps[params.dataIndex];
              if (step.name.includes('IC')) return 'rgba(22,163,74,0.55)';
              if (step.value < 0) return 'rgba(239,68,68,0.5)';
              return 'rgba(14,165,233,0.5)';
            },
          },

          emphasis: {
            itemStyle: {
              shadowBlur: 32,
            },
          },

          label: {
            show: true,
            // Place labels OUTSIDE the bars at the top
            position: 'top',
            // Improve contrast especially in dark mode
            color: labelValueColor,
            backgroundColor: labelBgColor,
            borderRadius: 6,
            padding: [4, 8],
            fontSize: valueFontSize,
            fontWeight: 700,
            // No decimals on bar values, always integers with grouping
            formatter: (p: any) => {
              if (typeof p.value === 'number') {
                const idx = p.dataIndex;
                const step = steps[idx];
                const isTotal =
                  ['Approved', 'Expected', 'Operational', 'Actual'].some((k) =>
                    step.name.includes(k),
                  );
                const raw = step.value;

                // Totals: show value as-is (positive)
                if (isTotal) {
                  return Math.round(raw).toLocaleString('en-US', {
                    maximumFractionDigits: 0,
                  });
                }

                // Relatives: show signed value (negative for losses, positive for gains)
                const sign = raw < 0 ? '-' : '';
                const magnitude = Math.abs(raw);
                const rounded = Math.round(magnitude);
                return `${sign}${rounded.toLocaleString('en-US', {
                  maximumFractionDigits: 0,
                })}`;
              }
              return p.value;
            },
          } as any,

          // Percentage labels relative to Expected Budget
          markPoint: {
            symbol: 'circle',
            symbolSize: 0, // hide the actual symbol, keep only the label
            label: {
              show: true,
              formatter: (p: any) => {
                const idx = p.dataIndex ?? p.dataIndexInside ?? 0;
                const pct = percentages[idx] ?? 0;
                return `${Math.round(pct)}%`;
              },
              color: percentTextColor,
              backgroundColor: 'transparent',
              padding: [2, 4],
              fontSize: percentFontSize,
              fontWeight: 600,
            },
            data: steps.map((_step, i) => ({
              // category axis index + constant y-position
              coord: [i, percentY],
            })),
          },
        },
      ],
    };
  }, [steps, title, theme, isLaptop]);

  const handleDownloadImage = () => {
    const instance = chartRef.current?.getEchartsInstance();
    if (instance) {
      const bgColor = theme === 'dark' ? '#0f172a' : '#ffffff';
      const url = instance.getDataURL({
        type: 'png',
        pixelRatio: 2,
        backgroundColor: bgColor,
      });
      const link = document.createElement('a');
      link.href = url;
      link.download = 'yield_waterfall_chart.png';
      link.click();
    }
  };

  const buttonHoverBg = theme === 'dark' ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.05)';

  return (
    <div className="relative w-full">
      <button
        type="button"
        onClick={handleDownloadImage}
        aria-label="Download chart as image"
        title="Download chart as image"
        style={{
          position: 'absolute',
          top: 4,
          right: 4,
          zIndex: 10,
          background: 'transparent',
          border: 'none',
          cursor: 'pointer',
          padding: 6,
          borderRadius: 6,
          color: theme === 'dark' ? '#e2e8f0' : '#475569',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.backgroundColor = buttonHoverBg;
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.backgroundColor = 'transparent';
        }}
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
          <polyline points="7 10 12 15 17 10" />
          <line x1="12" y1="15" x2="12" y2="3" />
        </svg>
      </button>
      <ReactECharts
        ref={chartRef}
        option={option}
        style={{ height: 540, width: '100%' }}
        opts={{ renderer: 'canvas' }}
      />
    </div>
  );
}



