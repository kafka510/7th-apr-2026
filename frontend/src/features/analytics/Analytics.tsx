/**
 * Analytics Dashboard Main Component
 * 
 * This is a simplified initial version. Full implementation will include:
 * - Device selector with grouping
 * - Measurement points selector
 * - Chart.js visualization with zoom/pan
 * - CSV download
 */
 
import { useState, useEffect } from 'react';
import { SiteSelector } from './components/SiteSelector';
import { DateRangePicker } from './components/DateRangePicker';
import { DeviceSelector } from './components/DeviceSelector';
import { MeasurementPointsSelector } from './components/MeasurementPointsSelector';
import { ChartDisplay } from './components/ChartDisplay';
import type {
  Asset,
  AnalyticsFilters,
  Device,
  MeasurementPointsByDeviceType,
  MeasurementPointsDiagnostics,
  TimeSeriesData,
  AnalyticsDataResponse,
} from './types';
import { fetchDevices, fetchMeasurementPoints, fetchTimeSeriesData, getCSVDownloadUrl } from './api';

// Get assets from the page (passed from Django template)
function getAssetsFromPage(): Asset[] {
  if (typeof document === 'undefined') {
    return [];
  }
  
  try {
    // Try to get assets from script tag (preferred method)
    const scriptTag = document.getElementById('analytics-assets-data');
    if (scriptTag && scriptTag.textContent) {
      const assetsStr = scriptTag.textContent.trim();
      if (assetsStr) {
        const parsed = JSON.parse(assetsStr);
        return Array.isArray(parsed) ? parsed : [];
      }
    }
    
    // Fallback to data attribute (for backwards compatibility)
    const root = document.getElementById('react-root');
    if (root && root.dataset.assets) {
      let assetsStr = root.dataset.assets;
      
      // Handle HTML entity decoding if needed
      if (assetsStr.includes('&quot;') || assetsStr.includes('&#39;')) {
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = assetsStr;
        assetsStr = tempDiv.textContent || tempDiv.innerText || assetsStr;
      }
      
      assetsStr = assetsStr.trim();
      if (assetsStr && assetsStr !== 'null' && assetsStr !== 'undefined') {
        const parsed = JSON.parse(assetsStr);
        return Array.isArray(parsed) ? parsed : [];
      }
    }
  } catch (e) {
    console.error('Failed to parse assets:', e);
  }
  
  return [];
}

export function Analytics() {
  const [assets] = useState<Asset[]>(getAssetsFromPage());
  
  const [filters, setFilters] = useState<AnalyticsFilters>({
    assetCode: null,
    deviceIds: [],
    metrics: [],
    startDate: null,
    endDate: null,
  });
  const [devices, setDevices] = useState<Device[]>([]);
  const [measurementPoints, setMeasurementPoints] = useState<MeasurementPointsByDeviceType>({});
  const [measurementPointsDiagnostics, setMeasurementPointsDiagnostics] = useState<MeasurementPointsDiagnostics | null>(null);
  const [measurementPointsError, setMeasurementPointsError] = useState<string | null>(null);
  const [loadingMeasurementPoints, setLoadingMeasurementPoints] = useState(false);
  const [loading, setLoading] = useState(false);
  const [loadingDevices, setLoadingDevices] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [chartData, setChartData] = useState<TimeSeriesData[] | null>(null);
  const [chartResponse, setChartResponse] = useState<AnalyticsDataResponse | null>(null);
  const [selectedTimezone, setSelectedTimezone] = useState<string | null>(null);

  // Initialize default dates
  useEffect(() => {
    const today = new Date().toISOString().split('T')[0];
    const weekAgo = new Date();
    weekAgo.setDate(weekAgo.getDate() - 7);
    const defaultStartDate = weekAgo.toISOString().split('T')[0];

    setFilters((prev) => ({
      ...prev,
      startDate: prev.startDate || defaultStartDate,
      endDate: prev.endDate || today,
    }));
  }, []);

  // Load devices when asset is selected
  useEffect(() => {
    if (filters.assetCode) {
      setLoadingDevices(true);
      setError(null);
      fetchDevices(filters.assetCode)
        .then((deviceList) => {
          setDevices(deviceList);
        })
        .catch((err) => {
          setError(err instanceof Error ? err.message : 'Failed to load devices');
          setDevices([]);
        })
        .finally(() => {
          setLoadingDevices(false);
        });
    } else {
      setDevices([]);
      setMeasurementPoints({});
      setMeasurementPointsDiagnostics(null);
      setMeasurementPointsError(null);
      setFilters((prev) => ({ ...prev, deviceIds: [], metrics: [] }));
    }
  }, [filters.assetCode]);

  // Load measurement points when devices are selected (after device list is ready)
  useEffect(() => {
    if (!filters.assetCode || filters.deviceIds.length === 0 || loadingDevices) {
      if (!filters.assetCode || filters.deviceIds.length === 0) {
        setMeasurementPoints({});
        setMeasurementPointsDiagnostics(null);
        setMeasurementPointsError(null);
        setLoadingMeasurementPoints(false);
        setFilters((prev) => ({ ...prev, metrics: [] }));
      }
      return;
    }

    const selectedDevices = devices.filter((d) => filters.deviceIds.includes(d.device_id));
    if (selectedDevices.length === 0) {
      // Race: wait for device list to include selected IDs, or stale selection after refresh
      if (devices.length > 0) {
        setMeasurementPoints({});
        setMeasurementPointsDiagnostics(null);
        setMeasurementPointsError(
          'Selected devices are not in the current list for this site. Clear device selection and pick again.'
        );
        setLoadingMeasurementPoints(false);
      }
      return;
    }

    const deviceTypes = [...new Set(selectedDevices.map((d) => d.device_type).filter(Boolean))];

    setLoadingMeasurementPoints(true);
    setMeasurementPointsError(null);
    fetchMeasurementPoints(filters.assetCode, deviceTypes)
      .then(({ data, diagnostics }) => {
        setMeasurementPoints(data);
        setMeasurementPointsDiagnostics(diagnostics);
      })
      .catch((err) => {
        console.error('Failed to load measurement points:', err);
        setMeasurementPoints({});
        setMeasurementPointsDiagnostics(null);
        setMeasurementPointsError(err instanceof Error ? err.message : 'Failed to load measurement points');
      })
      .finally(() => {
        setLoadingMeasurementPoints(false);
      });
  }, [filters.assetCode, filters.deviceIds, devices, loadingDevices]);

  const handleAssetChange = (assetCode: string | null, timezone: string | null) => {
    setSelectedTimezone(timezone);
    setFilters({
      assetCode,
      deviceIds: [],
      metrics: [],
      startDate: filters.startDate,
      endDate: filters.endDate,
    });
    setChartData(null);
    setMeasurementPoints({});
    setMeasurementPointsDiagnostics(null);
    setMeasurementPointsError(null);
  };

  const handleLoadData = async () => {
    if (!filters.assetCode || filters.deviceIds.length === 0 || filters.metrics.length === 0) {
      alert('Please select a site, at least one device, and at least one measurement point');
      return;
    }

    if (!filters.startDate || !filters.endDate) {
      alert('Please select start and end dates');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const result = await fetchTimeSeriesData(
        filters.assetCode,
        filters.deviceIds,
        filters.metrics,
        filters.startDate,
        filters.endDate
      );

      if (result.success && result.data) {
        setChartData(result.data);
        setChartResponse(result);
        setSelectedTimezone(result.timezone_offset || null);
      } else {
        const errorMsg = result.error || 'Failed to load data';
        setError(errorMsg);
        setChartData(null);
        setChartResponse(null);
      }
    } catch (err) {
      console.error('Error loading data:', err);
      setError(err instanceof Error ? err.message : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex w-full flex-col bg-slate-50" style={{ minHeight: '100%' }}>
      <div className="flex-1 p-5">
      {/* Page Header */}
      <div className="mb-6 rounded-lg bg-gradient-to-r from-purple-600 to-purple-800 p-6 text-white shadow-lg">
        <h1 className="mb-2 text-3xl font-bold">Analytics Dashboard</h1>
        <p className="text-purple-100">Visualize device data with timezone-aware chart display</p>
      </div>

      {error && (
        <div className="mb-4 rounded-lg border border-yellow-400 bg-yellow-50 p-4 text-yellow-800">
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Controls Section */}
      <div className="mb-6 rounded-lg bg-white p-6 shadow-md">
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
          {/* Site Selection */}
          <div className="lg:col-span-1">
            <SiteSelector
              assets={assets}
              selectedAssetCode={filters.assetCode}
              onAssetChange={handleAssetChange}
            />
          </div>

          {/* Date Range */}
          <div className="lg:col-span-2">
            <DateRangePicker
              startDate={filters.startDate}
              endDate={filters.endDate}
              onStartDateChange={(date) => setFilters({ ...filters, startDate: date })}
              onEndDateChange={(date) => setFilters({ ...filters, endDate: date })}
              disabled={!filters.assetCode}
            />
          </div>
        </div>

        {/* Device Selection */}
        {filters.assetCode && (
          <DeviceSelector
            devices={devices}
            selectedDeviceIds={filters.deviceIds}
            onDeviceSelectionChange={(deviceIds) =>
              setFilters({ ...filters, deviceIds, metrics: [] })
            }
            loading={loadingDevices}
          />
        )}

        {/* Measurement Points Selection */}
        {filters.assetCode && filters.deviceIds.length > 0 && (
          <MeasurementPointsSelector
            measurementPoints={measurementPoints}
            selectedMetrics={filters.metrics}
            onMetricsChange={(metrics) => setFilters({ ...filters, metrics })}
            loading={loadingMeasurementPoints}
            error={measurementPointsError}
            diagnostics={measurementPointsDiagnostics}
          />
        )}

        {/* Load Data Button */}
        <div className="mt-6 text-center">
          <button
            type="button"
            onClick={handleLoadData}
            disabled={loading || !filters.assetCode || filters.deviceIds.length === 0 || filters.metrics.length === 0}
            className="rounded-lg bg-gradient-to-r from-purple-600 to-purple-800 px-8 py-3 font-semibold text-white shadow-md transition-all hover:translate-y-[-2px] hover:shadow-lg disabled:cursor-not-allowed disabled:opacity-60 disabled:hover:translate-y-0"
          >
            {loading ? 'Loading...' : 'Load Chart Data'}
          </button>
        </div>
      </div>

      {/* Chart Display Section */}
      {chartData && chartData.length > 0 && (
        <>
          <ChartDisplay
            data={chartData}
            timezone={selectedTimezone}
            recordCount={chartResponse?.record_count}
            dataQuality={chartResponse?.data_quality}
          />
          {/* CSV Download Button */}
          <div className="mt-4 text-center">
            <a
              href={getCSVDownloadUrl(
                filters.assetCode!,
                filters.deviceIds,
                filters.metrics,
                filters.startDate!,
                filters.endDate!
              )}
              className="inline-block rounded-lg bg-green-500 px-6 py-2 text-sm font-medium text-white shadow-md transition-all hover:bg-green-600 hover:shadow-lg"
              download
            >
              Download CSV
            </a>
          </div>
        </>
      )}

      {/* No Data Message */}
      {chartData && chartData.length === 0 && (
        <div className="rounded-lg bg-white p-12 text-center shadow-md">
          <p className="text-lg text-slate-600">No data available for the selected criteria.</p>
          <p className="text-sm text-slate-500">Please try different devices, measurement points, or date range.</p>
          <p className="mt-2 text-xs text-slate-400">Response received but data array is empty.</p>
        </div>
      )}
      
      {/* Loading State */}
      {loading && (
        <div className="rounded-lg bg-white p-12 text-center shadow-md">
          <p className="text-lg text-slate-600">Loading chart data...</p>
        </div>
      )}
      
      {/* Initial State - No data loaded yet */}
      {!loading && !chartData && !error && (
        <div className="rounded-lg bg-white p-12 text-center shadow-md">
          <p className="text-lg text-slate-600">Select filters and click &quot;Load Chart Data&quot; to view analytics</p>
        </div>
      )}
      </div>
    </div>
  );
}

