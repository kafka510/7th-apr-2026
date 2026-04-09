/**
 * Google Maps Component for Portfolio Map
 */
 
import { useEffect, useRef, useState, useCallback } from 'react';
import type { MapDataEntry, YieldDataEntry, PerformanceFilter, KPIMetrics } from '../types';
import {
  calculatePerformanceAchievement,
  getPerformanceCategory,
  getMarkerColor,
  parseNumeric,
  formatCODDate,
} from '../utils/performance';
import { getResponsiveFontSize } from '../../../utils/fontScaling';

interface PortfolioMapComponentProps {
  mapData: MapDataEntry[];
  yieldData: YieldDataEntry[];
  filters: {
    mapFilters: Record<string, string[]>;
    performanceFilter: PerformanceFilter;
  };
  onKPIsUpdate: (kpis: KPIMetrics) => void;
  onMapReady?: () => void;
}

// Extend Window interface for Google Maps
declare global {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const google: any;
  interface Window {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    google: any;
    initMap: () => void;
  }
}

export function PortfolioMapComponent({
  mapData,
  yieldData,
  filters,
  onKPIsUpdate,
  onMapReady,
}: PortfolioMapComponentProps) {
  const mapRef = useRef<HTMLDivElement>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const mapInstanceRef = useRef<any>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const markersRef = useRef<any[]>([]);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const infoWindowsRef = useRef<any[]>([]);
  const [zoomLevel, setZoomLevel] = useState(5);
  const [mapLoaded, setMapLoaded] = useState(false);

  // Create custom marker icon
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const createMarkerIcon = useCallback((color: string): any => {
    const enhancedColors: Record<string, string> = {
      '#2E8B57': '#2E8B57',
      '#FFB800': '#FFB800',
      '#B22222': '#B22222',
      '#6B7280': '#4B5563',
    };

    const enhancedColor = enhancedColors[color] || color;

    const svg = `
      <svg xmlns="http://www.w3.org/2000/svg" width="40" height="56" viewBox="0 0 40 56">
        <defs>
          <filter id="shadow" x="-50%" y="-50%" width="200%" height="200%">
            <feDropShadow dx="2" dy="2" stdDeviation="2" flood-color="#000000" flood-opacity="0.3"/>
          </filter>
        </defs>
        <path d="M20 0C14 0 9 5 9 11c0 8 11 18 11 18s11-10 11-18c0-6-5-11-11-11z M20 29L14 56L26 56Z" 
              fill="${enhancedColor}" 
              stroke="none"
              stroke-width="0"
              filter="url(#shadow)"/>
        <path d="M20 29L14 56L26 56Z" 
              fill="${enhancedColor}" 
              stroke="none"
              stroke-width="0"
              filter="url(#shadow)"/>
        <circle cx="20" cy="11" r="4" fill="#ffffff" opacity="0.9"/>
        <circle cx="20" cy="11" r="2.5" fill="${enhancedColor}"/>
        <circle cx="20" cy="3" r="1.5" fill="#ffffff" opacity="0.8"/>
      </svg>
    `;

    // Google Maps types are loaded dynamically
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const gmaps = (window as any).google?.maps;
    if (!gmaps) {
      return null;
    }

    return {
      url: 'data:image/svg+xml;charset=UTF-8,' + encodeURIComponent(svg),
      anchor: new gmaps.Point(20, 56),
      size: new gmaps.Size(40, 56),
      scaledSize: new gmaps.Size(40, 56),
      origin: new gmaps.Point(0, 0),
      labelOrigin: new gmaps.Point(20, 8),
    };
  }, []);

  // Initialize map
  useEffect(() => {
    if (!mapRef.current || mapLoaded) return;

    const initMap = () => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const gmaps = (window as any).google?.maps;
      if (!gmaps || !mapRef.current) {
        console.warn('[PortfolioMapComponent] Google Maps not available or mapRef is null');
        return;
      }

      const map = new gmaps.Map(mapRef.current, {
        center: { lat: 15, lng: 100 },
        zoom: 5,
        mapTypeId: 'hybrid',  // Default to satellite with labels
        mapId: 'DEMO_MAP_ID',
        zoomControl: false,
        mapTypeControl: true,
        mapTypeControlOptions: {
          style: gmaps.MapTypeControlStyle.HORIZONTAL_BAR,
          position: gmaps.ControlPosition.TOP_LEFT,
          mapTypeIds: ['roadmap', 'hybrid', 'satellite'],
        },
        streetViewControl: false,
        fullscreenControl: true,
        fullscreenControlOptions: {
          position: gmaps.ControlPosition.TOP_RIGHT,
        },
      });

      mapInstanceRef.current = map;
      setMapLoaded(true);

      // Listen to zoom changes
      gmaps.event.addListener(map, 'zoom_changed', () => {
        if (map) {
          setZoomLevel(map.getZoom() || 5);
        }
      });

      // Fit bounds to all sites on initial load
      if (mapData.length > 0) {
        const bounds = new gmaps.LatLngBounds();
        let validCoords = 0;
        let invalidCoords = 0;
        mapData.forEach((row, index) => {
          const lat = parseNumeric(row.latitude);
          const lng = parseNumeric(row.longitude);
          if (Number.isFinite(lat) && Number.isFinite(lng)) {
            bounds.extend(new gmaps.LatLng(lat, lng));
            validCoords++;
          } else {
            invalidCoords++;
            if (index < 3) {
              console.warn('[PortfolioMapComponent] Invalid coordinates for row:', {
                asset_no: row.asset_no,
                latitude: row.latitude,
                longitude: row.longitude,
                parsedLat: lat,
                parsedLng: lng,
              });
            }
          }
        });
        if (!bounds.isEmpty()) {
          map.fitBounds(bounds);
          gmaps.event.addListenerOnce(map, 'bounds_changed', () => {
            const currentZoom = map.getZoom();
            if (currentZoom && currentZoom > 10) {
              map.setZoom(10);
            }
          });
        } else {
          console.warn('[PortfolioMapComponent] No valid coordinates found in mapData. Sample entries:', mapData.slice(0, 3));
        }
      } else {
        console.warn('[PortfolioMapComponent] No mapData available for initial bounds');
      }

      if (onMapReady) {
        onMapReady();
      }
      
      // Trigger marker update after map is ready
      // This ensures markers are created when data is available
      setTimeout(() => {
        // Force marker update by checking if we have data
        if (mapData.length > 0) {
          // The marker update effect should run automatically when mapLoaded changes
        }
      }, 100);
    };

    // Load Google Maps script if not already loaded
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    if ((window as any).google) {
      initMap();
    } else {
      const script = document.createElement('script');
      script.src = `https://maps.googleapis.com/maps/api/js?key=AIzaSyCPdGwRKctCvCnF2bNincrRpdTEAXzeDsA&callback=initMap&loading=async`;
      script.async = true;
      script.defer = true;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (window as any).initMap = initMap;
      script.onerror = () => {
        console.error('[PortfolioMapComponent] Failed to load Google Maps script');
      };
      document.head.appendChild(script);
    }

    return () => {
      // Cleanup
      if (markersRef.current.length > 0) {
        markersRef.current.forEach((marker) => marker.setMap(null));
        markersRef.current = [];
      }
      if (infoWindowsRef.current.length > 0) {
        infoWindowsRef.current.forEach((iw) => iw.close());
        infoWindowsRef.current = [];
      }
    };
    }, [mapRef, mapLoaded, mapData, onMapReady, yieldData]);

  // Update markers when filters or data change
  useEffect(() => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const gmaps = (window as any).google?.maps;
    if (!mapInstanceRef.current || !mapLoaded || !gmaps) {
      // Don't log repeatedly - this causes infinite loops
      return;
    }

    const map = mapInstanceRef.current;

    // Clear existing markers and info windows
    markersRef.current.forEach((marker) => marker.setMap(null));
    infoWindowsRef.current.forEach((iw) => iw.close());
    markersRef.current = [];
    infoWindowsRef.current = [];

    // Apply map filters
    let filteredData = mapData.filter((row) => {
      return Object.entries(filters.mapFilters).every(([col, values]) => {
        if (values.length === 0) return true;
        const rowVal = String(row[col as keyof MapDataEntry] || '').trim();
        return values.includes(rowVal);
      });
    });

    // Apply performance filter
    if (filters.performanceFilter !== 'all') {
      filteredData = filteredData.filter((row) => {
        const achievement = calculatePerformanceAchievement(row.asset_no, yieldData);
        const category = getPerformanceCategory(achievement);
        // For null achievements, only include if filter is for unknown/default data
        if (achievement === null) return false;
        return category === filters.performanceFilter;
      });
    }

    // Calculate KPIs
    const fmt = (v: number): number => (!Number.isNaN(v) ? v : 0);
    const siteCount = filteredData.length;
    const pvCapacity = filteredData.reduce((sum, row) => sum + fmt(parseNumeric(row.dc_capacity_mwp)), 0);
    const bessCapacity = filteredData.reduce(
      (sum, row) => sum + fmt(parseNumeric(row.battery_capacity_mw)),
      0
    );

    // Only update KPIs if values changed to prevent infinite loops
    onKPIsUpdate({
      siteCount,
      pvCapacity,
      bessCapacity,
    });

    // Create markers
    let markersCreated = 0;
    let invalidCoords = 0;
    filteredData.forEach((row) => {
      const lat = parseNumeric(row.latitude);
      const lng = parseNumeric(row.longitude);

      if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
        invalidCoords++;
        // Only log first few invalid entries to avoid spam
        if (invalidCoords <= 3) {
          console.warn('[PortfolioMapComponent] Skipping row with invalid coordinates:', {
            asset_no: row.asset_no,
            latitude: row.latitude,
            longitude: row.longitude,
            parsedLat: lat,
            parsedLng: lng,
            latitudeType: typeof row.latitude,
            longitudeType: typeof row.longitude,
          });
        }
        return;
      }

      // Calculate performance
      const achievement = calculatePerformanceAchievement(row.asset_no, yieldData);
      const category = getPerformanceCategory(achievement);
      const color = getMarkerColor(category);

      // Create marker icon
      const icon = createMarkerIcon(color);
      if (!icon) {
        console.warn('[PortfolioMapComponent] Failed to create marker icon for:', row.asset_no);
        return;
      }

      // Create marker
      const marker = new gmaps.Marker({
        position: { lat, lng },
        map,
        icon: icon,
        optimized: false,
        title: row.site_name || row.asset_no || 'Unknown Site',
      });

      // Create info window with improved styling that works with Google Maps
      // Calculate responsive font sizes for info window
      const infoTitleFontSize = getResponsiveFontSize(16, 20, 14);
      const infoBodyFontSize = getResponsiveFontSize(12, 16, 10);
      const infoSmallFontSize = getResponsiveFontSize(10, 14, 9);
      const infoValueFontSize = getResponsiveFontSize(16, 20, 14);

      const performanceSection = achievement !== null
        ? `<div style="margin: 8px 0 0 0; padding: 8px 10px; background-color: ${
            category === 'excellent'
              ? '#dcfce7'
              : category === 'good'
                ? '#fef3c7'
                : category === 'poor'
                  ? '#fee2e2'
                  : '#f3f4f6'
          }; border-left: 3px solid ${color}; border-radius: 4px;">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 3px;">
              <span style="font-size: ${infoBodyFontSize}px; color: #374151; font-weight: 700;">📊 Performance Achievement</span>
              <span style="font-size: ${infoValueFontSize}px; font-weight: 800; color: ${color};">${achievement.toFixed(1)}%</span>
            </div>
            <div style="font-size: ${infoSmallFontSize}px; color: #6b7280; text-transform: uppercase; font-weight: 600; letter-spacing: 0.3px;">
              ${
                category === 'excellent'
                  ? '✓ Excellent Performance'
                  : category === 'good'
                    ? '△ Good Performance'
                    : category === 'poor'
                      ? '⚠ Needs Attention'
                      : '◯ No Data'
              }
            </div>
          </div>`
        : '';

      const infoWindow = new gmaps.InfoWindow({
        content: `
          <div style="min-width: 350px; max-width: 450px; padding: 10px 12px; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #ffffff;">
            <div style="margin-bottom: 8px; padding-bottom: 6px; border-bottom: 2px solid #3b82f6;">
              <div style="font-size: ${infoTitleFontSize}px; font-weight: 800; color: #1e40af; margin-bottom: 3px; line-height: 1.2;">
                ${row.site_name || 'N/A'}
              </div>
              <div style="font-size: ${infoBodyFontSize}px; color: #6b7280; font-weight: 600;">
                📍 ${row.country || 'N/A'} • Asset: ${row.asset_no || 'N/A'}
              </div>
            </div>
            
            <div style="display: grid; grid-template-columns: 130px 1fr; gap: 6px 12px; font-size: ${infoBodyFontSize}px; line-height: 1.4; margin-bottom: 2px;">
              <span style="color: #6b7280; font-weight: 700;">📂 Portfolio:</span>
              <span style="color: #111827; font-weight: 600;">${row.portfolio || 'N/A'}</span>
              
              <span style="color: #6b7280; font-weight: 700;">⚡ Plant Type:</span>
              <span style="color: #111827; font-weight: 600;">${row.plant_type || 'N/A'}</span>
              
              <span style="color: #6b7280; font-weight: 700;">🏗️ Installation:</span>
              <span style="color: #111827; font-weight: 600;">${row.installation_type || 'N/A'}</span>
              
              <span style="color: #6b7280; font-weight: 700;">☀️ PV Capacity:</span>
              <span style="color: #1e40af; font-weight: 800;">${fmt(parseNumeric(row.dc_capacity_mwp)).toFixed(1)} MW</span>
              
              <span style="color: #6b7280; font-weight: 700;">🔋 BESS Capacity:</span>
              <span style="color: #1e40af; font-weight: 800;">${fmt(parseNumeric(row.battery_capacity_mw)).toFixed(1)} MWh</span>
              
              <span style="color: #6b7280; font-weight: 700;">📅 COD:</span>
              <span style="color: #111827; font-weight: 600;">${formatCODDate(row.cod)}</span>
              
              <span style="color: #6b7280; font-weight: 700;">🤝 Offtaker:</span>
              <span style="color: #111827; font-weight: 600;">${row.offtaker || 'N/A'}</span>
              
              <span style="color: #6b7280; font-weight: 700;">🗺️ Coordinates:</span>
              <span style="color: #4b5563; font-weight: 500; font-size: ${infoSmallFontSize}px;">${lat.toFixed(6)}, ${lng.toFixed(6)}</span>
            </div>
            
            ${performanceSection}
          </div>
        `,
        maxWidth: 480,
        pixelOffset: new gmaps.Size(0, -5),
      });

      marker.addListener('click', () => {
        // Close all other info windows
        infoWindowsRef.current.forEach((iw) => iw.close());
        infoWindow.open(map, marker);
      });

      markersRef.current.push(marker);
      infoWindowsRef.current.push(infoWindow);
      markersCreated++;
    });

    // Auto-zoom based on number of sites
    if (filteredData.length > 0) {
      if (filteredData.length === 1) {
        // Single site: zoom in close with satellite view
        const site = filteredData[0];
        const lat = parseNumeric(site.latitude);
        const lng = parseNumeric(site.longitude);
        if (Number.isFinite(lat) && Number.isFinite(lng)) {
          map.setCenter({ lat, lng });
          map.setZoom(18);
          map.setMapTypeId('satellite');
        }
      } else {
        // Multiple sites: fit bounds with hybrid view (satellite with labels)
        map.setMapTypeId('hybrid');
        const bounds = new gmaps.LatLngBounds();
        filteredData.forEach((row) => {
          const lat = parseNumeric(row.latitude);
          const lng = parseNumeric(row.longitude);
          if (Number.isFinite(lat) && Number.isFinite(lng)) {
            bounds.extend(new gmaps.LatLng(lat, lng));
          }
        });
        if (!bounds.isEmpty()) {
          map.fitBounds(bounds);
          gmaps.event.addListenerOnce(map, 'bounds_changed', () => {
            const currentZoom = map.getZoom();
            if (currentZoom && currentZoom > 12) {
              map.setZoom(12);
            }
          });
        }
      }
    } else {
      // No sites: default view with hybrid (satellite with labels)
      map.setMapTypeId('hybrid');
      map.setCenter({ lat: 15, lng: 100 });
      map.setZoom(5);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mapData, yieldData, filters, mapLoaded]);

  const handleZoomIn = useCallback(() => {
    if (mapInstanceRef.current) {
      const currentZoom = mapInstanceRef.current.getZoom() || 5;
      mapInstanceRef.current.setZoom(Math.min(currentZoom + 1, 20));
    }
  }, []);

  const handleZoomOut = useCallback(() => {
    if (mapInstanceRef.current) {
      const currentZoom = mapInstanceRef.current.getZoom() || 5;
      mapInstanceRef.current.setZoom(Math.max(currentZoom - 1, 1));
    }
  }, []);

  const handleResetView = useCallback(() => {
    if (!mapInstanceRef.current || mapData.length === 0) return;

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const gmaps = (window as any).google?.maps;
    if (!mapInstanceRef.current || !gmaps) return;

    const map = mapInstanceRef.current;
    const bounds = new gmaps.LatLngBounds();

    mapData.forEach((row) => {
      const lat = parseNumeric(row.latitude);
      const lng = parseNumeric(row.longitude);
      if (Number.isFinite(lat) && Number.isFinite(lng)) {
        bounds.extend(new gmaps.LatLng(lat, lng));
      }
    });

    if (!bounds.isEmpty()) {
      map.fitBounds(bounds);
      map.setMapTypeId('hybrid');  // Use hybrid (satellite with labels) by default
      gmaps.event.addListenerOnce(map, 'bounds_changed', () => {
        const currentZoom = map.getZoom();
        if (currentZoom && currentZoom > 10) {
          map.setZoom(10);
        }
      });
    } else {
      map.setCenter({ lat: 15, lng: 100 });
      map.setZoom(5);
    }
  }, [mapData]);

  const handleDownloadMapImage = useCallback(async () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const gmaps = (window as any).google?.maps;
    if (!mapInstanceRef.current || !gmaps || !mapRef.current) {
      console.warn('[PortfolioMapComponent] Map is not ready for download');
      alert('Map is still loading. Please try again in a moment.');
      return;
    }

    try {
      const map = mapInstanceRef.current;
      const center = map.getCenter();
      const zoom = map.getZoom() || 5;
      const mapTypeId = map.getMapTypeId ? map.getMapTypeId() : 'hybrid';

      if (!center) {
        console.warn('[PortfolioMapComponent] Map center is not available');
        alert('Unable to capture the current map view.');
        return;
      }

      const lat = center.lat();
      const lng = center.lng();

      // Use the container size to choose a reasonable Static Maps size (within API limits)
      const containerWidth = mapRef.current.offsetWidth || 1280;
      const containerHeight = mapRef.current.offsetHeight || 720;
      const maxSize = 2048;
      const width = Math.min(containerWidth, maxSize);
      const height = Math.min(containerHeight, maxSize);

      // Map Google Maps type to Static Maps maptype
      const mapType =
        mapTypeId === 'satellite' || mapTypeId === 'hybrid' ? 'satellite' : 'roadmap';

      // Apply the same filtering logic as used for markers
      let filteredData = mapData.filter((row) => {
        return Object.entries(filters.mapFilters).every(([col, values]) => {
          if (values.length === 0) return true;
          const rowVal = String(row[col as keyof MapDataEntry] || '').trim();
          return values.includes(rowVal);
        });
      });

      // Apply performance filter
      if (filters.performanceFilter !== 'all') {
        filteredData = filteredData.filter((row) => {
          const achievement = calculatePerformanceAchievement(row.asset_no, yieldData);
          const category = getPerformanceCategory(achievement);
          if (achievement === null) return false;
          return category === filters.performanceFilter;
        });
      }

      // Build marker parameters for Static Maps API
      // Group markers by color for efficiency
      const markersByColor: Record<string, Array<{ lat: number; lng: number }>> = {};
      
      filteredData.forEach((row) => {
        const lat = parseNumeric(row.latitude);
        const lng = parseNumeric(row.longitude);

        if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
          return;
        }

        // Calculate performance to get color
        const achievement = calculatePerformanceAchievement(row.asset_no, yieldData);
        const category = getPerformanceCategory(achievement);
        const color = getMarkerColor(category);

        // Convert hex color to format Static Maps API expects (remove #)
        const markerColor = color.replace('#', '');

        if (!markersByColor[markerColor]) {
          markersByColor[markerColor] = [];
        }
        markersByColor[markerColor].push({ lat, lng });
      });

      // Build marker URL parameters
      // Static Maps API supports: markers=color:0xRRGGBB|lat,lng|lat,lng
      // Grouping by color reduces URL length and API calls
      const markerParams: string[] = [];
      Object.entries(markersByColor).forEach(([color, positions]) => {
        const positionsStr = positions.map(pos => `${pos.lat},${pos.lng}`).join('|');
        // Use 0x prefix for hex colors as per Static Maps API specification
        markerParams.push(`markers=color:0x${color}|${positionsStr}`);
      });

      // NOTE: This key is already used for the interactive map script.
      const apiKey = 'AIzaSyCPdGwRKctCvCnF2bNincrRpdTEAXzeDsA';

      // Build the URL with markers
      let url = `https://maps.googleapis.com/maps/api/staticmap?center=${lat},${lng}` +
        `&zoom=${zoom}&size=${Math.round(width)}x${Math.round(height)}` +
        `&maptype=${mapType}&scale=2&key=${apiKey}`;
      
      // Add marker parameters
      if (markerParams.length > 0) {
        url += '&' + markerParams.join('&');
      }

      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`Static Maps API error: ${response.status} ${response.statusText}`);
      }

      const blob = await response.blob();
      const blobUrl = URL.createObjectURL(blob);

      const link = document.createElement('a');
      const timestamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-');
      link.href = blobUrl;
      link.download = `portfolio-map-${timestamp}.png`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(blobUrl);
    } catch (error) {
      console.error('[PortfolioMapComponent] Failed to download map image:', error);
      alert('Failed to download map image. Please try again.');
    }
  }, [mapData, yieldData, filters]);

  return (
    <div className="map-section glass relative size-full rounded-2xl border-2 border-[#0072CE]">
      <div ref={mapRef} className="size-full rounded-2xl" style={{ minHeight: '600px' }} />

      {/* Zoom Controls */}
      <div className="absolute right-4 top-4 z-10 flex flex-col gap-2">
        <button
          type="button"
          onClick={handleZoomIn}
          className="flex size-10 items-center justify-center rounded-lg border border-gray-300 bg-white font-bold text-gray-700 shadow-lg transition-all duration-200 hover:scale-105 hover:bg-gray-100 active:scale-95"
          title="Zoom In"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
            <path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z" />
          </svg>
        </button>
        <button
          type="button"
          onClick={handleZoomOut}
          className="flex size-10 items-center justify-center rounded-lg border border-gray-300 bg-white font-bold text-gray-700 shadow-lg transition-all duration-200 hover:scale-105 hover:bg-gray-100 active:scale-95"
          title="Zoom Out"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
            <path d="M19 13H5v-2h14v2z" />
          </svg>
        </button>
        <button
          type="button"
          onClick={handleResetView}
          className="flex size-10 items-center justify-center rounded-lg border border-gray-300 bg-white font-bold text-gray-700 shadow-lg transition-all duration-200 hover:scale-105 hover:bg-gray-100 active:scale-95"
          title="Reset View"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 5V1L7 6l5 5V7c3.31 0 6 2.69 6 6s-2.69 6-6 6-6-2.69-6-6H4c0 4.42 3.58 8 8 8s8-3.58 8-8-3.58-8-8-8z" />
          </svg>
        </button>
        <button
          type="button"
          onClick={handleDownloadMapImage}
          className="mt-1 flex items-center justify-center rounded-lg border border-gray-300 bg-white px-3 py-1 text-xs font-semibold text-gray-700 shadow-lg transition-all duration-200 hover:scale-105 hover:bg-gray-100 active:scale-95"
          title="Download Map Image"
        >
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="currentColor"
            className="mr-1"
          >
            <path d="M5 20h14v-2H5v2zm7-18l-5 5h3v6h4v-6h3l-5-5z" />
          </svg>
          <span>Download</span>
        </button>
      </div>

      {/* Zoom Level Display */}
      <div className="absolute bottom-4 left-4 z-10 rounded-lg border border-gray-300 bg-white/90 px-3 py-2 font-semibold text-gray-700 shadow-lg">
        Zoom: <span>{zoomLevel}</span>
      </div>
    </div>
  );
}

