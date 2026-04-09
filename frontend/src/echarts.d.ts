/**
 * Global type definitions for ECharts library
 * This file provides shared types to avoid conflicts across components
 */

// Export these interfaces so they can be imported and extended
export interface EChartsInstance {
  setOption: (option: unknown, notMerge?: boolean, lazyUpdate?: boolean) => void;
  resize: (opts?: { width?: number | string; height?: number | string; silent?: boolean }) => void;
  dispose: () => void;
  getOption: () => unknown;
  getWidth: () => number;
  clear: () => void;
  on: (eventName: string, handler: (params: unknown) => void) => void;
  off: (eventName: string, handler?: (params: unknown) => void) => void;
  getZr?: () => {
    on: (event: string, handler: (params: unknown) => void) => void;
  };
  convertFromPixel?: (coord: { seriesIndex: number }, point: [number, number]) => [number, number] | null;
}

export interface EChartsStatic {
  init: (
    dom: HTMLElement | null,
    theme?: string | null,
    opts?: { renderer?: string; width?: string | number; height?: string | number }
  ) => EChartsInstance;
  registerTheme: (name: string, theme: unknown) => void;
  registerMap: (name: string, geoJson: unknown, specialAreas?: unknown) => void;
  connect: (group: string | EChartsInstance[]) => void;
  disconnect: (group: string) => void;
  dispose: (target: EChartsInstance | HTMLElement) => void;
  getInstanceByDom: (target: HTMLElement) => EChartsInstance | undefined;
  use: (ext: unknown) => void;
}

// Global declaration for window.echarts
declare global {
  interface Window {
    echarts: EChartsStatic | undefined;
  }
}

