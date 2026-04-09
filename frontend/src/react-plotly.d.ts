/* eslint-disable @typescript-eslint/no-explicit-any */
declare module 'react-plotly.js' {
  import { Component } from 'react';
  
  export interface PlotParams {
    data: any[];
    layout?: any;
    config?: Partial<Plotly.Config>;
    frames?: any[];
    revision?: number;
    onInitialized?: (figure: any, graphDiv: HTMLElement) => void;
    onUpdate?: (figure: any, graphDiv: HTMLElement) => void;
    onPurge?: (figure: any, graphDiv: HTMLElement) => void;
    onError?: (err: Error) => void;
    debug?: boolean;
    useResizeHandler?: boolean;
    style?: React.CSSProperties;
    className?: string;
    onRelayout?: (event: any) => void;
    onRedraw?: () => void;
    onClick?: (event: any) => void;
  }

  export default class Plot extends Component<PlotParams> {}
}

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

