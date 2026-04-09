/**
 * Hook to fetch and manage portfolio map data
 */
import { useState, useEffect, useCallback } from 'react';
import { fetchPortfolioMapData } from '../api';
import type { PortfolioMapData } from '../types';
import { parseNumeric, normalizeValue } from '../utils/performance';

export function usePortfolioMapData() {
  const [data, setData] = useState<PortfolioMapData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchPortfolioMapData();
      
      // fetchPortfolioMapData already validates and extracts only mapData and yieldData
      let data: PortfolioMapData | null = result || null;
      
      // Log data structure (only once, not on every render)
      if (data?.mapData && data.mapData.length > 0) {
        const firstEntry = data.mapData[0];
        console.log('[usePortfolioMapData] First map data entry structure:', {
          asset_no: firstEntry.asset_no,
          country: firstEntry.country,
          latitude: firstEntry.latitude,
          longitude: firstEntry.longitude,
          latitudeType: typeof firstEntry.latitude,
          longitudeType: typeof firstEntry.longitude,
          allKeys: Object.keys(firstEntry),
        });
        
        // Check how many entries have valid coordinates
        const withCoords = data.mapData.filter(row => {
          const lat = parseNumeric(row.latitude);
          const lng = parseNumeric(row.longitude);
          return Number.isFinite(lat) && Number.isFinite(lng);
        });
        console.log('[usePortfolioMapData] Coordinates summary:', {
          total: data.mapData.length,
          valid: withCoords.length,
          invalid: data.mapData.length - withCoords.length,
        });
        
        // Sample invalid entries for debugging
        if (withCoords.length === 0 && data.mapData.length > 0) {
          const sample = data.mapData.slice(0, 3);
          console.warn('[usePortfolioMapData] Sample entries with invalid coordinates:', sample.map(row => ({
            asset_no: row.asset_no,
            latitude: row.latitude,
            longitude: row.longitude,
          })));
        }
        
        // Check unique countries
        const countryRawValues = data.mapData.map(row => ({
          raw: row.country,
          normalized: normalizeValue(row.country),
          type: typeof row.country,
        }));
        const countries = [...new Set(countryRawValues.map(c => c.normalized).filter(Boolean))];
        console.log('[usePortfolioMapData] Countries found:', {
          count: countries.length,
          countries: countries.sort(),
          sampleRaw: countryRawValues.slice(0, 5),
          allRaw: countryRawValues,
        });
        
        // Validate data structure - check if we have all required fields
        const requiredFields = ['site_name', 'installation_type', 'plant_type', 'offtaker', 'cod', 'battery_capacity_mw'];
        const missingFields = requiredFields.filter(field => !(field in firstEntry));
        if (missingFields.length > 0) {
          console.error('[usePortfolioMapData] Missing required fields in map data:', missingFields);
          console.error('[usePortfolioMapData] This suggests the API endpoint is returning wrong data structure!');
        }
      }
      
      // Ensure all required arrays exist
      if (data) {
        data = {
          ...data,
          mapData: data.mapData || [],
          yieldData: data.yieldData || [],
        };
        console.log('[usePortfolioMapData] Final data structure:', {
          mapDataLength: data.mapData.length,
          yieldDataLength: data.yieldData.length,
        });
      }
      
      setData(data);
    } catch (err) {
      console.error('[usePortfolioMapData] Error:', err);
      setError(err instanceof Error ? err.message : 'Failed to load portfolio map data');
      setData(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  return { data, loading, error, refetch: loadData };
}

