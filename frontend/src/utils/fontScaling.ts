/**
 * Font Scaling Utility for Responsive Typography
 * 
 * This utility provides consistent font sizing across laptops and large monitors
 * by scaling fonts proportionally based on viewport width.
 * 
 * Base reference: 1920px width (standard large monitor)
 * Formula: fontSize = base * (viewportWidth / 1920)
 * 
 * Usage:
 *   import { getResponsiveFontSize, useResponsiveFontSize } from '@/utils/fontScaling';
 * 
 *   // In component:
 *   const fontSize = useResponsiveFontSize(12, 18, 9); // base, max, min
 *   <div style={{ fontSize: `${fontSize}px` }}>Text</div>
 * 
 *   // Or directly:
 *   const fontSize = getResponsiveFontSize(12, 18, 9);
 */

import React from 'react';

/**
 * Calculate responsive font size based on viewport width
 * @param base - Base font size at 1920px width (default: 12px)
 * @param max - Maximum font size cap (default: 18px)
 * @param min - Minimum font size floor (default: 9px)
 * @returns Calculated font size in pixels
 */
export function getResponsiveFontSize(base: number = 12, max: number = 18, min: number = 9): number {
  if (typeof window === 'undefined') {
    return base; // SSR fallback
  }
  
  const width = window.innerWidth;
  const calculatedSize = Math.round(base * (width / 1920));
  return Math.max(min, Math.min(max, calculatedSize));
}

/**
 * React hook for responsive font size that updates on window resize
 * @param base - Base font size at 1920px width
 * @param max - Maximum font size cap
 * @param min - Minimum font size floor
 * @returns Current responsive font size
 */
export function useResponsiveFontSize(
  base: number = 12,
  max: number = 18,
  min: number = 9
): number {
  const [fontSize, setFontSize] = React.useState(() => 
    getResponsiveFontSize(base, max, min)
  );

  React.useEffect(() => {
    const updateFontSize = () => {
      setFontSize(getResponsiveFontSize(base, max, min));
    };
    
    window.addEventListener('resize', updateFontSize);
    // Initial calculation
    updateFontSize();
    
    return () => window.removeEventListener('resize', updateFontSize);
  }, [base, max, min]);

  return fontSize;
}

// Re-export as getBigFont for backward compatibility
export const getBigFont = getResponsiveFontSize;

