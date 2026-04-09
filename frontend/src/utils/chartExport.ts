/**
 * Chart Export Utility
 * 
 * Exports ECharts charts with theme-aware styling.
 * Uses a temporary off-screen chart instance to ensure consistent exports.
 */

/**
 * Get ECharts theme options based on dark/light mode.
 * This is the industry-standard approach: explicitly set backgroundColor and text colors
 * in the chart options, NOT relying on CSS or container backgrounds.
 * 
 * @param isDark Whether the theme is dark mode
 * @returns ECharts option object with theme-aware colors
 */
export function getEChartsThemeOptions(isDark: boolean) {
  return {
    backgroundColor: isDark ? '#0f172a' : '#ffffff',
    textStyle: {
      color: isDark ? '#e5e7eb' : '#111827',
    },
    title: {
      textStyle: {
        color: isDark ? '#e5e7eb' : '#111827',
      },
    },
    legend: {
      textStyle: {
        color: isDark ? '#e5e7eb' : '#111827',
      },
    },
    axisLabel: {
      color: isDark ? '#e5e7eb' : '#111827',
    },
  };
}

/**
 * Exports a chart with theme-aware styling by creating a temporary off-screen chart instance.
 * Uses the same renderer (SVG) and dimensions as the source chart for exact replication.
 * The exported image will match the current UI theme (light or dark).
 * 
 * @param optionBuilder Function that returns the chart option configuration
 * @param filename Name of the downloaded file (without extension)
 * @param sourceChart Optional source chart instance to get dimensions from
 * @param isDark Optional theme flag. If not provided, detects theme from document
 */
export function exportChartLight(
  optionBuilder: () => any,
  filename: string,
  sourceChart?: any,
  isDark?: boolean
): void {
  if (!window.echarts) {
    console.error('ECharts is not loaded');
    return;
  }

  // Detect theme if not provided
  if (isDark === undefined) {
    isDark = document.documentElement.classList.contains('dark');
  }

  // Get theme-aware background color
  const backgroundColor = isDark ? '#0f172a' : '#ffffff';
  const themeOptions = getEChartsThemeOptions(isDark);

  // Get dimensions from source chart if available, otherwise use defaults
  let width = 900;
  let height = 500;
  if (sourceChart && sourceChart.getDom) {
    const dom = sourceChart.getDom();
    if (dom && dom.getBoundingClientRect) {
      const rect = dom.getBoundingClientRect();
      width = rect.width;
      height = rect.height;
    }
  }

  // Create a temporary off-screen container
  const container = document.createElement('div');
  container.style.position = 'fixed';
  container.style.left = '-10000px';
  container.style.top = '-10000px';
  container.style.width = `${width}px`;
  container.style.height = `${height}px`;
  document.body.appendChild(container);

  // Use SVG renderer - SAME AS UI
  const chart = window.echarts.init(container, null, {
    renderer: 'svg',
  });

  // Set the chart option with theme-aware background and disable animation
  const option = optionBuilder();
  chart.setOption({
    ...option,
    ...themeOptions,
    backgroundColor: backgroundColor, // Explicitly set based on theme
    animation: false, // IMPORTANT: Disable animation for stable snapshot
  });

  // Wait for chart to render, then export
  setTimeout(() => {
    try {
      const echartsInstance = chart as any;
      const url = echartsInstance.getDataURL({
        type: 'png',
        pixelRatio: window.devicePixelRatio || 2,
        backgroundColor: backgroundColor, // Critical: set backgroundColor for export
      });

      // Create download link
      const a = document.createElement('a');
      a.href = url;
      a.download = `${filename.replace(/\s+/g, '_')}.png`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    } catch (error) {
      console.error('Error exporting chart:', error);
    } finally {
      // Cleanup: dispose chart and remove container
      chart.dispose();
      document.body.removeChild(container);
    }
  }, 100);
}

