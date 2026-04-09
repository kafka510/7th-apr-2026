// Shared Chart.js type definitions

export interface ChartInstance {
  destroy: () => void;
  getElementsAtEventForMode?: (event: MouseEvent, mode: string, options: unknown, useFinalPosition: boolean) => unknown[];
}

export interface ChartStatic {
  new (ctx: CanvasRenderingContext2D, config: unknown): ChartInstance;
  register?: (...plugins: unknown[]) => void;
}

// Extended Chart type for CDN-loaded Chart.js with additional methods
export interface ChartStaticWithRegister extends ChartStatic {
  register?: (...plugins: unknown[]) => void;
  [key: string]: unknown; // Allow additional properties from CDN version
}

declare global {
  interface Window {
    Chart?: ChartStaticWithRegister;
    ChartDataLabels?: unknown;
  }
}

