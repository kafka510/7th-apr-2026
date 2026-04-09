/**
 * Loss Calculation Test Component
 * 
 * Provides UI for testing loss calculations synchronously (without Celery)
 */
import { useState, useEffect, useRef, useReducer } from 'react';
import type { Asset } from '../analytics/types';
import { getCSRFToken } from '../../utils/csrf';

// Extend Window interface for global variables
declare global {
  interface Window {
    CALCULATION_TEST_ASSETS?: Asset[];
  }
}

interface Device {
  device_id: string;
  device_name: string;
  device_type: string;
  module_datasheet_id: number | null;
  modules_in_series: number | null;
}

interface InverterDevice {
  device_id: string;
  device_name: string;
  device_type: string;
}

interface InverterExpectedPowerSummary {
  success: boolean;
  inverter_id: string;
  start_ts?: string;
  end_ts?: string;
  groups_count?: number;
  group_device_ids?: string[];
  deleted_existing_points?: number;
  points_written?: number;
  points_skipped_missing_inputs?: number;
  warnings?: string[];
  error?: string;
  /** DC capacity (kW) used when PVsyst PR model was used */
  dc_cap_used_kw?: number | null;
  /** PR (pv_syst_pr) from asset when PVsyst PR model was used */
  pr_used?: number | null;
  /** Power model used, e.g. 'pvsyst_pr_v1' */
  power_model_used?: string | null;
}

interface CalculationResult {
  timestamp: string;
  expected_power: number;
  actual_power: number;
  power_loss: number;
  loss_percentage: number;
  irradiance: number;
  temperature: number | null;
}

/** Per-step timing from SDM model (ms) */
interface TimingBreakdownMs {
  get_module_ds_ms?: number;
  get_fitted_parameters_ms?: number;
  param_cache_ms?: number;
  param_db_read_ms?: number;
  param_fit_sdm_ms?: number;
  param_db_write_ms?: number;
  estimate_power_vmpp_ms?: number;
  other_ms?: number;
  total_ms?: number;
}

interface CalculationResponse {
  success: boolean;
  device_id: string;
  total_calculations: number;
  successful: number;
  failed: number;
  expected_power_calculated?: number;
  errors: string[];
  results: CalculationResult[];
  error?: string;
  time_taken_ms?: number;
  time_taken_seconds?: number;
  /** Per-step timing totals for this device run (ms) */
  timing_breakdown_ms_total?: TimingBreakdownMs;
  /** Per-step timing average per expected-power calculation (ms) */
  timing_breakdown_ms_avg_per_calc?: TimingBreakdownMs;
}

/** Transposition API response (admin-only) */
interface TransposeResponse {
  success: boolean;
  time_taken_seconds?: number;
  device_ids_used?: string[];
  records_written?: number;
  ghi_points?: number;
  tilt_configs_count?: number;
  error?: string;
}

/** Satellite GHI/TEMP CSV upload response */
interface SatelliteUploadResponse {
  success: boolean;
  asset_code?: string;
  device_id?: string;
  deleted_count?: number;
  rows_written?: number;
  start_ts?: string;
  end_ts?: string;
  error?: string;
}

// Get assets from the page
function getAssetsFromPage(): Asset[] {
  if (typeof document === 'undefined') {
    return [];
  }
  
  try {
    const scriptTag = document.getElementById('calculation-test-assets-data');
    if (scriptTag && scriptTag.textContent) {
      const assetsStr = scriptTag.textContent.trim();
      if (assetsStr) {
        const parsed = JSON.parse(assetsStr);
        return Array.isArray(parsed) ? parsed : [];
      }
    }
    
    // Fallback to window variable
    if (window.CALCULATION_TEST_ASSETS) {
      return Array.isArray(window.CALCULATION_TEST_ASSETS) ? window.CALCULATION_TEST_ASSETS : [];
    }
  } catch (e) {
    console.error('Failed to parse assets:', e);
  }
  
  return [];
}

export function CalculationTest() {
  const [assets] = useState<Asset[]>(getAssetsFromPage());
  const [selectedAsset, setSelectedAsset] = useState<string>('');
  const [devices, setDevices] = useState<Device[]>([]);
  const [selectedDevices, setSelectedDevices] = useState<Set<string>>(new Set());
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');
  const [timeInterval, setTimeInterval] = useState<number>(15);
  const [loadingDevices, setLoadingDevices] = useState(false);
  const [assetRangeTaskId, setAssetRangeTaskId] = useState<string | null>(null);
  const [assetRangeMessage, setAssetRangeMessage] = useState<string | null>(null);
  const [assetRangeTaskStatus, setAssetRangeTaskStatus] = useState<'idle' | 'pending' | 'success' | 'failure'>('idle');
  const [assetRangeTaskResult, setAssetRangeTaskResult] = useState<{ string_tasks?: { device_id: string; task_id: string }[]; inverter_tasks?: { device_id: string; task_id: string }[]; message?: string; error?: string } | null>(null);

  // Inverter expected power test state
  const [inverters, setInverters] = useState<InverterDevice[]>([]);
  const [loadingInverters, setLoadingInverters] = useState(false);
  const [selectedInverters, setSelectedInverters] = useState<Set<string>>(new Set());
  const [inverterSummaries, setInverterSummaries] = useState<InverterExpectedPowerSummary[]>([]);
  const [inverterError, setInverterError] = useState<string | null>(null);
  const [inverterLoading, setInverterLoading] = useState(false);

  // Transposition Test (admin-only section)
  const [transposeAsset, setTransposeAsset] = useState<string>('');
  const [transposeDevices, setTransposeDevices] = useState<Device[]>([]);
  const [transposeLoadingDevices, setTransposeLoadingDevices] = useState(false);
  const [transposeIrradianceDeviceId, setTransposeIrradianceDeviceId] = useState<string>('');
  const [transposeMetric, setTransposeMetric] = useState<string>('ghi');
  const [transposeStartDate, setTransposeStartDate] = useState<string>('');
  const [transposeEndDate, setTransposeEndDate] = useState<string>('');
  const [transposeLoading, setTransposeLoading] = useState(false);
  const [transposeResult, setTransposeResult] = useState<TransposeResponse | null>(null);
  const [transposeError, setTransposeError] = useState<string | null>(null);
  const [transposeTaskId, setTransposeTaskId] = useState<string | null>(null);
  const [transposeTaskStatus, setTransposeTaskStatus] = useState<'idle' | 'pending' | 'success' | 'failure'>('idle');

  // Upload Satellite GHI/TEMP CSV
  const [uploadAsset, setUploadAsset] = useState<string>('');
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadLoading, setUploadLoading] = useState(false);
  const [uploadResult, setUploadResult] = useState<SatelliteUploadResponse | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  
  // Use reducer to batch all calculation-related state updates together
  // This prevents React DOM reconciliation issues by updating all state at once
  type CalculationState = {
    loading: boolean;
    results: Map<string, CalculationResponse>;
    error: string | null;
    progressText: string;
  };
  
  type CalculationAction =
    | { type: 'START' }
    | { type: 'UPDATE_PROGRESS'; payload: string }
    | { type: 'COMPLETE'; payload: { results: Map<string, CalculationResponse>; error: string | null } }
    | { type: 'ERROR'; payload: string | null }
    | { type: 'RESET' };
  
  const initialState: CalculationState = {
    loading: false,
    results: new Map(),
    error: null,
    progressText: '',
  };
  
  const [calcState, dispatchCalc] = useReducer(
    (state: CalculationState, action: CalculationAction): CalculationState => {
      switch (action.type) {
        case 'START':
          return { ...state, loading: true, error: null, results: new Map(), progressText: 'Initializing...' };
        case 'UPDATE_PROGRESS':
          return { ...state, progressText: action.payload };
        case 'COMPLETE':
          return { ...state, loading: false, results: action.payload.results, error: action.payload.error, progressText: 'Completed' };
        case 'ERROR':
          return { ...state, loading: false, error: action.payload, progressText: '' };
        case 'RESET':
          return initialState;
        default:
          return state;
      }
    },
    initialState
  );
  
  const { loading, results, error } = calcState;
  const resultsRef = useRef<Map<string, CalculationResponse>>(new Map());
  const progressTextRef = useRef<string>('');
  const isCalculatingRef = useRef<boolean>(false);
  const loadingIndicatorRef = useRef<HTMLDivElement>(null);


  // Set default dates (today and 7 days ago)
  useEffect(() => {
    const today = new Date();
    const weekAgo = new Date();
    weekAgo.setDate(weekAgo.getDate() - 7);
    
    setEndDate(today.toISOString().split('T')[0] + 'T23:59:59');
    setStartDate(weekAgo.toISOString().split('T')[0] + 'T00:00:00');
  }, []);


  // Load devices when asset is selected
  useEffect(() => {
    if (!selectedAsset) {
      setDevices([]);
      setSelectedDevices(new Set());
      setInverters([]);
      setSelectedInverters(new Set());
      return;
    }

    const fetchDevices = async () => {
      setLoadingDevices(true);
      dispatchCalc({ type: 'ERROR', payload: null });
      try {
        const response = await fetch(
          `/api/calculation-test/devices/?asset_code=${encodeURIComponent(selectedAsset)}`,
          {
            credentials: 'include',
          }
        );
        
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        if (data.success) {
          setDevices(data.devices || []);
        } else {
          throw new Error(data.error || 'Failed to fetch devices');
        }
      } catch (err) {
        dispatchCalc({ type: 'ERROR', payload: err instanceof Error ? err.message : 'Failed to load devices' });
        console.error('Error fetching devices:', err);
      } finally {
        setLoadingDevices(false);
      }
    };
    
    const fetchInverters = async () => {
      setLoadingInverters(true);
      setInverterError(null);
      try {
        // Use site-onboarding API to list configured inverters for this asset
        const response = await fetch(
          `/api/site-onboarding/device-pv-config/?asset_code=${encodeURIComponent(selectedAsset)}&level=inverter&configured=true`,
          { credentials: 'include' }
        );
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        const invs = (data.devices || []) as any[];
        setInverters(
          invs.map((d) => ({
            device_id: d.device_id,
            device_name: d.device_name,
            device_type: d.device_type,
          }))
        );
        setSelectedInverters(new Set());
      } catch (err) {
        console.error('Error fetching inverters for expected power test:', err);
        setInverterError(err instanceof Error ? err.message : 'Failed to load inverters');
        setInverters([]);
        setSelectedInverters(new Set());
      } finally {
        setLoadingInverters(false);
      }
    };

    fetchDevices();
    fetchInverters();
  }, [selectedAsset]);

  // Load devices for Transposition Test when transpose asset is selected
  useEffect(() => {
    if (!transposeAsset) {
      setTransposeDevices([]);
      setTransposeIrradianceDeviceId('');
      return;
    }
    const fetchTransposeDevices = async () => {
      setTransposeLoadingDevices(true);
      setTransposeError(null);
      try {
        const response = await fetch(
          `/api/calculation-test/devices/?asset_code=${encodeURIComponent(transposeAsset)}&device_type=wst`,
          { credentials: 'include' }
        );
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        if (data.success) {
          setTransposeDevices(data.devices || []);
          setTransposeIrradianceDeviceId('');
        } else {
          throw new Error(data.error || 'Failed to fetch devices');
        }
      } catch (err) {
        setTransposeError(err instanceof Error ? err.message : 'Failed to load devices');
      } finally {
        setTransposeLoadingDevices(false);
      }
    };
    fetchTransposeDevices();
  }, [transposeAsset]);

  // Default dates for Transposition Test
  useEffect(() => {
    if (transposeStartDate || transposeEndDate) return;
    const today = new Date();
    const weekAgo = new Date();
    weekAgo.setDate(weekAgo.getDate() - 7);
    setTransposeEndDate(today.toISOString().slice(0, 16));
    setTransposeStartDate(weekAgo.toISOString().slice(0, 16));
  }, []);

  // Poll transpose task status (loss_analytics async transposition)
  useEffect(() => {
    if (!transposeTaskId || transposeTaskStatus !== 'pending') return;
    let cancelled = false;
    const poll = async () => {
      try {
        const res = await fetch(`/api/loss/task/${encodeURIComponent(transposeTaskId)}/`, { credentials: 'include' });
        const data = await res.json().catch(() => ({}));
        if (cancelled) return;
        const status = (data.status || '').toUpperCase();
        if (status === 'SUCCESS') {
          const result = data.result || {};
          setTransposeTaskStatus('success');
          setTransposeResult({
            success: true,
            records_written: result.records_written,
            device_ids_used: result.device_ids_used,
            time_taken_seconds: result.time_taken_seconds,
          });
          setTransposeError(null);
        } else if (status === 'FAILURE') {
          setTransposeTaskStatus('failure');
          const err = data.result?.error ?? data.error ?? 'Transposition task failed';
          setTransposeError(err);
          setTransposeResult(null);
        }
        if (status === 'SUCCESS' || status === 'FAILURE') {
          setTransposeLoading(false);
        }
      } catch {
        if (cancelled) return;
        setTransposeTaskStatus('failure');
        setTransposeError('Failed to fetch task status');
        setTransposeLoading(false);
      }
    };
    poll();
    const interval = setInterval(poll, 2000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [transposeTaskId, transposeTaskStatus]);

  // Poll asset range task status (loss_analytics pipeline)
  useEffect(() => {
    if (!assetRangeTaskId || assetRangeTaskStatus !== 'pending') return;
    let cancelled = false;
    const poll = async () => {
      try {
        const res = await fetch(`/api/loss/task/${encodeURIComponent(assetRangeTaskId)}/`, { credentials: 'include' });
        const data = await res.json().catch(() => ({}));
        if (cancelled) return;
        const status = (data.status || '').toUpperCase();
        if (status === 'SUCCESS') {
          setAssetRangeTaskStatus('success');
          setAssetRangeTaskResult(data.result || null);
          setAssetRangeMessage('Pipeline completed successfully.');
        } else if (status === 'FAILURE') {
          setAssetRangeTaskStatus('failure');
          setAssetRangeTaskResult({ error: data.error || 'Task failed' });
          setAssetRangeMessage(data.error || 'Pipeline failed.');
        }
      } catch {
        if (cancelled) return;
        setAssetRangeTaskStatus('failure');
        setAssetRangeTaskResult({ error: 'Failed to fetch task status' });
      }
    };
    poll();
    const interval = setInterval(poll, 2000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [assetRangeTaskId, assetRangeTaskStatus]);

  const handleDeviceToggle = (deviceId: string) => {
    setSelectedDevices(prev => {
      const newSet = new Set(prev);
      if (newSet.has(deviceId)) {
        newSet.delete(deviceId);
      } else {
        newSet.add(deviceId);
      }
      return newSet;
    });
  };

  const handleInverterToggle = (deviceId: string) => {
    setSelectedInverters(prev => {
      const next = new Set(prev);
      if (next.has(deviceId)) {
        next.delete(deviceId);
      } else {
        next.add(deviceId);
      }
      return next;
    });
  };

  const handleSelectAll = () => {
    if (selectedDevices.size === devices.length) {
      setSelectedDevices(new Set());
    } else {
      setSelectedDevices(new Set(devices.map(d => d.device_id)));
    }
  };

  const handleSelectAllInverters = () => {
    if (selectedInverters.size === inverters.length) {
      setSelectedInverters(new Set());
    } else {
      setSelectedInverters(new Set(inverters.map(d => d.device_id)));
    }
  };

  const handleTranspose = async () => {
    if (!transposeAsset || !transposeIrradianceDeviceId || !transposeStartDate || !transposeEndDate) {
      setTransposeError('Please select asset, irradiance sensor, and date range.');
      return;
    }
    setTransposeLoading(true);
    setTransposeError(null);
    setTransposeResult(null);
    setTransposeTaskId(null);
    setTransposeTaskStatus('idle');
    try {
      const response = await fetch('/api/loss/transpose/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCSRFToken() || '',
        },
        credentials: 'include',
        body: JSON.stringify({
          asset_code: transposeAsset,
          irradiance_device_id: transposeIrradianceDeviceId,
          metric: transposeMetric || 'ghi',
          start_date: transposeStartDate,
          end_date: transposeEndDate,
        }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        setTransposeError(data.error || `HTTP ${response.status}`);
        setTransposeLoading(false);
        return;
      }
      if (data.task_id) {
        setTransposeTaskId(data.task_id);
        setTransposeTaskStatus('pending');
      } else {
        setTransposeError(data.error || 'No task_id returned');
        setTransposeLoading(false);
      }
    } catch (err) {
      setTransposeError(err instanceof Error ? err.message : 'Request failed');
      setTransposeLoading(false);
    }
  };

  const handleUploadSatelliteCsv = async () => {
    if (!uploadAsset || !uploadFile) {
      setUploadError('Please select a site and choose a CSV file.');
      return;
    }
    setUploadLoading(true);
    setUploadError(null);
    setUploadResult(null);
    try {
      const formData = new FormData();
      formData.append('asset_code', uploadAsset);
      formData.append('csv_file', uploadFile);
      const response = await fetch('/api/calculation-test/upload-satellite-csv/', {
        method: 'POST',
        headers: {
          'X-CSRFToken': getCSRFToken() || '',
        },
        credentials: 'include',
        body: formData,
      });
      const data: SatelliteUploadResponse = await response.json();
      if (!response.ok) {
        setUploadError(data.error || `HTTP ${response.status}`);
        return;
      }
      if (data.success) {
        setUploadResult(data);
        setUploadFile(null);
      } else {
        setUploadError(data.error || 'Upload failed');
      }
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : 'Request failed');
    } finally {
      setUploadLoading(false);
    }
  };

  const handleCalculate = async () => {
    if (selectedDevices.size === 0 || !startDate || !endDate) {
      dispatchCalc({ type: 'ERROR', payload: 'Please select at least one device and date range' });
      return;
    }

    // Wrap everything in try-catch to prevent page from going blank
    try {
      // CRITICAL: Don't update state at all during the calculation process
      // Only update state at the very end to avoid React DOM reconciliation issues
      // This prevents React from trying to reconcile the DOM during async operations
      resultsRef.current.clear();
      progressTextRef.current = 'Initializing...';
      
      // Show loading indicator using direct DOM manipulation (bypasses React)
      // Use setTimeout to ensure the ref is available after React has rendered
      setTimeout(() => {
        if (loadingIndicatorRef.current) {
          loadingIndicatorRef.current.style.display = 'block';
          const progressEl = loadingIndicatorRef.current.querySelector('.progress-text');
          if (progressEl) {
            progressEl.textContent = 'Initializing...';
          }
        }
      }, 0);
      
      // Start calculations immediately without updating state
      // We'll only update state at the very end when everything is done
      (async () => {
        try {
          const deviceArray = Array.from(selectedDevices);
          const resultsMap = new Map<string, CalculationResponse>();
          const errors: string[] = [];

          // Process devices sequentially to avoid overwhelming the server
          // CRITICAL: Don't update any state during the loop to prevent React DOM errors
          // Only update refs, then update state once at the end
          for (let i = 0; i < deviceArray.length; i++) {
            const deviceId = deviceArray[i];
            const progressMsg = `Processing device ${i + 1}/${deviceArray.length}: ${deviceId}`;
            
            // Track start time for this device
            const startTime = Date.now();
            
            // Update ref for progress text
            progressTextRef.current = progressMsg;
            
            // Update progress text using direct DOM manipulation (bypasses React)
            if (loadingIndicatorRef.current) {
              const progressEl = loadingIndicatorRef.current.querySelector('.progress-text');
              if (progressEl) {
                progressEl.textContent = progressMsg;
              }
            }

      try {
        const response = await fetch('/api/loss-calculation/string/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken() || '',
          },
          credentials: 'include',
          body: JSON.stringify({
            device_id: deviceId,
            start_date: startDate,
            end_date: endDate,
            time_interval_minutes: timeInterval,
          }),
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({ error: `HTTP ${response.status}` }));
          throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
        }

        const data: CalculationResponse = await response.json();
        
        // Calculate time taken for this device
        const endTime = Date.now();
        const timeTaken = endTime - startTime;
        const timeTakenSeconds = (timeTaken / 1000).toFixed(2);
        
        // Add time taken to the result data
        const resultWithTime: CalculationResponse = {
          ...data,
          time_taken_ms: timeTaken,
          time_taken_seconds: parseFloat(timeTakenSeconds),
        };
        
        resultsMap.set(deviceId, resultWithTime);
        resultsRef.current.set(deviceId, resultWithTime);
        
        if (!data.success) {
          errors.push(`${deviceId}: ${data.error || 'Calculation failed'}`);
        }
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Failed to run calculation';
        console.error(`[${i + 1}/${deviceArray.length}] Error for ${deviceId}:`, err);
        errors.push(`${deviceId}: ${errorMsg}`);
        // Calculate time taken even for errors
        const endTime = Date.now();
        const timeTaken = endTime - startTime;
        const timeTakenSeconds = (timeTaken / 1000).toFixed(2);
        
        const errorResult = {
          success: false,
          device_id: deviceId,
          total_calculations: 0,
          successful: 0,
          failed: 0,
          errors: [errorMsg],
          results: [],
          error: errorMsg,
          time_taken_ms: timeTaken,
          time_taken_seconds: parseFloat(timeTakenSeconds),
        };
        resultsMap.set(deviceId, errorResult);
        resultsRef.current.set(deviceId, errorResult);
      }
      
      // Don't update results state during the loop to avoid React DOM issues
      // We'll update at the end only
    }

          // Hide loading indicator using direct DOM manipulation
          if (loadingIndicatorRef.current) {
            loadingIndicatorRef.current.style.display = 'none';
          }
          isCalculatingRef.current = false;
          
          // CRITICAL: Update all state at once using reducer dispatch
          // Use a longer delay to ensure React has fully settled
          setTimeout(() => {
            try {
              dispatchCalc({
                type: 'COMPLETE',
                payload: {
                  results: new Map(resultsRef.current),
                  error: errors.length > 0 ? `Some calculations failed:\n${errors.join('\n')}` : null,
                },
              });
            } catch (err) {
              console.error('Error updating final state:', err);
              dispatchCalc({
                type: 'ERROR',
                payload: 'Error displaying results. Calculations completed but results could not be displayed.',
              });
            }
          }, 300); // Longer delay to ensure React has fully settled
        } catch (err) {
          // Catch any errors in the async calculation block
          console.error('Fatal error in calculation loop:', err);
          setTimeout(() => {
            dispatchCalc({
              type: 'ERROR',
              payload: `An error occurred: ${err instanceof Error ? err.message : String(err)}. Please try again.`,
            });
          }, 200);
        }
      })(); // Immediately invoke async function
    } catch (err) {
      // Catch any errors in the outer try block
      console.error('Fatal error in handleCalculate:', err);
      setTimeout(() => {
        dispatchCalc({
          type: 'ERROR',
          payload: `An error occurred: ${err instanceof Error ? err.message : String(err)}. Please try again.`,
        });
      }, 0);
    }
  };

  const handleAssetRangeCelery = async () => {
    if (!selectedAsset || !startDate || !endDate) {
      dispatchCalc({ type: 'ERROR', payload: 'Please select an asset and date range for asset + duration run' });
      return;
    }

    try {
      setAssetRangeTaskId(null);
      setAssetRangeMessage(null);
      setAssetRangeTaskStatus('idle');
      setAssetRangeTaskResult(null);

      const response = await fetch('/api/loss/asset/range/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCSRFToken() || '',
        },
        credentials: 'include',
        body: JSON.stringify({
          asset_code: selectedAsset,
          start_date: startDate,
          end_date: endDate,
          time_interval_minutes: timeInterval,
        }),
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok || !data.success) {
        const msg = data.error || `HTTP ${response.status}`;
        throw new Error(msg);
      }

      setAssetRangeTaskId(data.task_id || null);
      setAssetRangeTaskStatus('pending');
      setAssetRangeTaskResult(null);
      setAssetRangeMessage('Asset loss pipeline queued. Polling task status...');
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to enqueue asset + duration loss calculation';
      console.error('Error enqueuing asset range calculation:', err);
      setAssetRangeMessage(msg);
    }
  };

  const handleInverterExpectedPower = async () => {
    if (!selectedAsset || selectedInverters.size === 0 || !startDate || !endDate) {
      setInverterError('Please select an asset, at least one inverter, and a date range.');
      return;
    }
    setInverterLoading(true);
    setInverterError(null);
    setInverterSummaries([]);
    try {
      const inverterIds = Array.from(selectedInverters);

      // Trigger Celery tasks via loss_analytics API (one task per inverter)
      const triggerResp = await fetch('/api/loss/inverter/expected-power/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCSRFToken() || '',
        },
        credentials: 'include',
        body: JSON.stringify({
          asset_code: selectedAsset,
          inverter_ids: inverterIds,
          start_date: startDate,
          end_date: endDate,
          inverter_efficiency: 0.97,
        }),
      });
      const triggerData = await triggerResp.json().catch(() => ({}));
      if (!triggerResp.ok || !triggerData.success) {
        const msg = triggerData.error || `HTTP ${triggerResp.status}`;
        setInverterError(msg);
        return;
      }

      const tasks: { inverter_id: string; task_id: string }[] = triggerData.tasks || [];
      const summaries: InverterExpectedPowerSummary[] = [];

      // Poll each inverter task sequentially for simplicity
      for (const { inverter_id, task_id } of tasks) {
        let attempts = 0;
        let done = false;
        while (!done && attempts < 60) {
          attempts += 1;
          try {
            const statusResp = await fetch(`/api/loss/task/${encodeURIComponent(task_id)}/`, {
              credentials: 'include',
            });
            const statusData = await statusResp.json().catch(() => ({}));
            const state = (statusData.status || '').toUpperCase();
            if (state === 'SUCCESS') {
              const r = statusData.result || {};
              summaries.push({
                success: true,
                inverter_id: r.inverter_id || inverter_id,
                start_ts: r.start_ts,
                end_ts: r.end_ts,
                groups_count: r.groups_count,
                group_device_ids: r.group_device_ids,
                deleted_existing_points: r.deleted_existing_points,
                points_written: r.points_written,
                dc_cap_used_kw: r.dc_cap_used_kw,
                pr_used: r.pr_used,
                power_model_used: r.power_model_used,
                points_skipped_missing_inputs: r.points_skipped_missing_gii,
                warnings: r.warnings || [],
              });
              done = true;
            } else if (state === 'FAILURE') {
              const errMsg = statusData.error || (statusData.result && statusData.result.error) || 'Task failed';
              summaries.push({
                success: false,
                inverter_id,
                error: errMsg,
                warnings: [],
              });
              done = true;
            } else {
              // PENDING / STARTED / RETRY – wait and poll again
              await new Promise((resolve) => setTimeout(resolve, 2000));
            }
          } catch (err) {
            summaries.push({
              success: false,
              inverter_id,
              error: err instanceof Error ? err.message : 'Failed to fetch inverter expected power status',
              warnings: [],
            });
            done = true;
          }
        }
      }

      setInverterSummaries(summaries);
    } finally {
      setInverterLoading(false);
    }
  };

  // Prevent page from going blank by ensuring component always renders
  if (!assets || assets.length === 0) {
    return (
      <div className="calculation-test p-4">
        <div className="alert alert-info">
          <strong>No assets available.</strong> Please ensure assets are configured.
        </div>
      </div>
    );
  }

  return (
    <div className="calculation-test" style={{ minHeight: '400px' }} key="calculation-test-container">
      <div className="row mb-4">
        <div className="col-md-6">
          <label className="form-label fw-bold text-dark">Select Asset:</label>
          <select
            className="text-dark form-select"
            value={selectedAsset}
            onChange={(e) => setSelectedAsset(e.target.value)}
            disabled={loading}
          >
            <option value="">-- Select Asset --</option>
            {assets.map((asset) => (
              <option key={asset.asset_code} value={asset.asset_code} className="text-dark">
                {asset.asset_name} ({asset.asset_code})
              </option>
            ))}
          </select>
        </div>

        <div className="col-md-6">
          <label className="form-label fw-bold text-dark">Select Device(s):</label>
          {loadingDevices ? (
            <div className="text-muted">Loading devices...</div>
          ) : devices.length === 0 ? (
            <div className="text-muted">No devices available. Select an asset first.</div>
          ) : (
            <div className="rounded border p-3" style={{ maxHeight: '200px', overflowY: 'auto' }}>
              <div className="mb-2">
                <button
                  type="button"
                  className="btn btn-sm btn-outline-secondary"
                  onClick={handleSelectAll}
                  disabled={loading || !selectedAsset}
                >
                  {selectedDevices.size === devices.length ? 'Deselect All' : 'Select All'}
                </button>
                <span className="text-muted ms-2">
                  {selectedDevices.size} of {devices.length} selected
                </span>
              </div>
              {devices.map((device) => (
                <div key={device.device_id} className="form-check">
                  <input
                    className="form-check-input"
                    type="checkbox"
                    id={`device-${device.device_id}`}
                    checked={selectedDevices.has(device.device_id)}
                    onChange={() => handleDeviceToggle(device.device_id)}
                    disabled={loading || !selectedAsset}
                  />
                  <label
                    className="form-check-label text-dark"
                    htmlFor={`device-${device.device_id}`}
                  >
                    {device.device_name} ({device.device_id})
                  </label>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Inverter Expected Power Test */}
      <div className="row mb-4">
        <div className="col-md-12">
          <div className="card">
            <div className="card-header">
              <h5 className="mb-0 text-dark">Inverter Expected Power (Configured Inverters Only)</h5>
            </div>
            <div className="card-body">
              {!selectedAsset ? (
                <div className="text-muted">Select an asset above to see configured inverters.</div>
              ) : loadingInverters ? (
                <div className="text-muted">Loading inverters...</div>
              ) : inverters.length === 0 ? (
                <div className="text-muted">
                  No configured inverters found for this asset. Configure inverter SDM groups and weather devices in Site Onboarding → PV Module configuration.
                </div>
              ) : (
                <div className="row">
                  <div className="col-md-6 mb-3">
                    <label className="form-label fw-bold text-dark">Select Inverter(s):</label>
                    <div className="rounded border p-3" style={{ maxHeight: '200px', overflowY: 'auto' }}>
                      <div className="mb-2">
                        <button
                          type="button"
                          className="btn btn-sm btn-outline-secondary"
                          onClick={handleSelectAllInverters}
                          disabled={inverterLoading || !selectedAsset}
                        >
                          {selectedInverters.size === inverters.length ? 'Deselect All' : 'Select All'}
                        </button>
                        <span className="text-muted ms-2">
                          {selectedInverters.size} of {inverters.length} selected
                        </span>
                      </div>
                      {inverters.map((inv) => (
                        <div key={inv.device_id} className="form-check">
                          <input
                            className="form-check-input"
                            type="checkbox"
                            id={`inv-${inv.device_id}`}
                            checked={selectedInverters.has(inv.device_id)}
                            onChange={() => handleInverterToggle(inv.device_id)}
                            disabled={inverterLoading || !selectedAsset}
                          />
                          <label
                            className="form-check-label text-dark"
                            htmlFor={`inv-${inv.device_id}`}
                          >
                            {inv.device_name} ({inv.device_id})
                          </label>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="col-md-6 mb-3 d-flex flex-column justify-content-end">
                    <p className="text-muted small mb-2">
                      This test calls the inverter expected-power service for each selected inverter, using the date range above.
                      It reads transposed GII (or configured irradiance devices) per SDM group and writes <code>expected_power</code> to <code>timeseries_data</code> with <code>device_id = inverter_id</code>.
                    </p>
                    <button
                      type="button"
                      className="btn btn-outline-primary"
                      onClick={handleInverterExpectedPower}
                      disabled={inverterLoading || selectedInverters.size === 0 || !selectedAsset || !startDate || !endDate}
                    >
                      {inverterLoading ? (
                        <>
                          <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                          Running inverter expected power for {selectedInverters.size} inverter{selectedInverters.size !== 1 ? 's' : ''}
                        </>
                      ) : (
                        <>
                          ⚡ Run Inverter Expected Power ({selectedInverters.size} inverter{selectedInverters.size !== 1 ? 's' : ''})
                        </>
                      )}
                    </button>
                    {inverterError && (
                      <div className="alert alert-danger mt-3 mb-0">
                        <strong>Error:</strong> {inverterError}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {inverterSummaries.length > 0 && (
                <div className="mt-3">
                  <h6 className="fw-bold text-dark mb-2">Inverter Expected Power Results</h6>
                  <div className="table-responsive">
                    <table className="table table-sm table-bordered mb-0">
                      <thead>
                        <tr>
                          <th className="text-dark">Inverter</th>
                          <th className="text-dark text-center">Groups</th>
                          <th className="text-dark text-center">Points written</th>
                          <th className="text-dark text-center">Skipped (missing inputs)</th>
                          <th className="text-dark text-center">Model / DC cap (kW)</th>
                          <th className="text-dark">Warnings / Error</th>
                        </tr>
                      </thead>
                      <tbody>
                        {inverterSummaries.map((s) => (
                          <tr key={s.inverter_id}>
                            <td className="text-dark">{s.inverter_id}</td>
                            <td className="text-dark text-center">{s.groups_count ?? '—'}</td>
                            <td className="text-dark text-center">{s.points_written ?? '—'}</td>
                            <td className="text-dark text-center">{s.points_skipped_missing_inputs ?? '—'}</td>
                            <td className="text-dark text-center small">
                              {s.power_model_used === 'pvsyst_pr_v1'
                                ? [
                                    'PVsyst PR',
                                    s.dc_cap_used_kw != null ? `${Number(s.dc_cap_used_kw).toFixed(2)} kW` : null,
                                    s.pr_used != null ? `PR=${Number(s.pr_used).toFixed(3)}` : null,
                                  ].filter(Boolean).join(', ') || 'PVsyst PR'
                                : '—'}
                            </td>
                            <td className="text-dark">
                              {s.success && (!s.warnings || s.warnings.length === 0) && !s.error && (
                                <span className="text-success">OK</span>
                              )}
                              {s.error && (
                                <div className="text-danger small">{s.error}</div>
                              )}
                              {s.warnings && s.warnings.length > 0 && (
                                <ul className="mb-0 ps-3 small">
                                  {s.warnings.map((w, idx) => (
                                    <li key={idx} className="text-warning">{w}</li>
                                  ))}
                                </ul>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="row mb-4">
        <div className="col-md-4">
          <label className="form-label fw-bold text-dark">Start Date & Time:</label>
          <input
            type="datetime-local"
            className="form-control text-dark"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            disabled={loading}
          />
        </div>

        <div className="col-md-4">
          <label className="form-label fw-bold text-dark">End Date & Time:</label>
          <input
            type="datetime-local"
            className="form-control text-dark"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            disabled={loading}
          />
        </div>

        <div className="col-md-4">
          <label className="form-label fw-bold text-dark">Time Interval (minutes):</label>
          <input
            type="number"
            className="form-control text-dark"
            value={timeInterval}
            onChange={(e) => setTimeInterval(parseInt(e.target.value, 10) || 15)}
            min="1"
            max="60"
            disabled={loading}
          />
          <small className="text-muted">Minimum interval between calculations</small>
        </div>
      </div>

      <div className="mb-4">
        <button
          className="btn btn-primary"
          onClick={handleCalculate}
          disabled={loading || selectedDevices.size === 0 || !startDate || !endDate}
        >
          {loading ? (
            <>
              <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
              <>Calculating {selectedDevices.size} device(s)...</>
            </>
          ) : (
            <>
              <i className="fas fa-calculator me-2"></i>
              Run Calculation ({selectedDevices.size} device{selectedDevices.size !== 1 ? 's' : ''})
            </>
          )}
        </button>
        <button
          className="btn btn-outline-secondary ms-3"
          onClick={handleAssetRangeCelery}
          disabled={loading || !selectedAsset || !startDate || !endDate}
        >
          Run Asset + Duration (Celery)
        </button>
        {assetRangeTaskId && (
          <div className="mt-2 text-muted">
            Task ID: <code>{assetRangeTaskId}</code>
            {assetRangeTaskStatus !== 'idle' && (
              <span className="ms-2">
                Status: <strong>{assetRangeTaskStatus === 'pending' ? 'Running...' : assetRangeTaskStatus === 'success' ? 'Success' : 'Failed'}</strong>
              </span>
            )}
          </div>
        )}
        {assetRangeMessage && (
          <div className="mt-2 small text-muted">
            {assetRangeMessage}
          </div>
        )}
        {assetRangeTaskStatus === 'success' && assetRangeTaskResult && (
          <div className="mt-2 small">
            {assetRangeTaskResult.message && <div className="text-success">{assetRangeTaskResult.message}</div>}
            {assetRangeTaskResult.string_tasks && assetRangeTaskResult.string_tasks.length > 0 && (
              <div>Strings queued: {assetRangeTaskResult.string_tasks.length}</div>
            )}
            {assetRangeTaskResult.inverter_tasks && assetRangeTaskResult.inverter_tasks.length > 0 && (
              <div>Inverters queued: {assetRangeTaskResult.inverter_tasks.length}</div>
            )}
          </div>
        )}
        {assetRangeTaskStatus === 'failure' && assetRangeTaskResult?.error && (
          <div className="mt-2 small text-danger">{assetRangeTaskResult.error}</div>
        )}
        {/* Loading indicator - always rendered, shown/hidden via direct DOM manipulation to avoid React reconciliation */}
        <div 
          ref={loadingIndicatorRef}
          className="bg-light mt-3 rounded border p-3" 
          key="loading-indicator"
          style={{ display: 'none' }}
        >
          <div className="text-center">
            <div className="spinner-border text-primary mb-2" role="status" style={{ width: '3rem', height: '3rem' }}>
              <span className="visually-hidden">Loading...</span>
            </div>
            <div>
              <strong>Processing calculations...</strong>
            </div>
            <div className="mt-2">
              <small className="text-info progress-text">
                <i className="fas fa-cog fa-spin me-1"></i>
                Initializing...
              </small>
            </div>
            <div className="mt-2">
              <small className="text-muted">
                Running calculations for {selectedDevices.size} device{selectedDevices.size !== 1 ? 's' : ''}. 
                Please wait, this may take a few moments.
              </small>
            </div>
          </div>
        </div>
      </div>

      {/* Always render error, use CSS to show/hide to prevent DOM reconciliation issues */}
      <div 
        className="alert alert-danger"
        style={{ display: error ? 'block' : 'none' }}
      >
        <strong>Error:</strong> {error}
      </div>

      {/* Always render results container, use CSS to show/hide to prevent DOM reconciliation issues */}
      <div 
        className="card"
        style={{ display: results.size > 0 ? 'block' : 'none' }}
      >
          <div className="card-header">
            <h5 className="text-dark mb-0">Calculation Results ({results.size} device{results.size !== 1 ? 's' : ''})</h5>
          </div>
          <div className="card-body text-dark">
            {/* Summary */}
            {(() => {
              const resultsArray = Array.from(results.values());
              const successful = resultsArray.filter(r => r.success).length;
              const failed = resultsArray.filter(r => !r.success).length;
              const totalCalculations = resultsArray.reduce((sum, r) => sum + (r.total_calculations || 0), 0);
              const totalSuccessful = resultsArray.reduce((sum, r) => sum + (r.successful || 0), 0);
              const totalFailed = resultsArray.reduce((sum, r) => sum + (r.failed || 0), 0);

              // Aggregate per-step timing across all device runs (sum ms)
              const timingKeys = [
                { key: 'get_module_ds_ms', label: 'Module datasheet (ModuleDS)' },
                { key: 'get_fitted_parameters_ms', label: 'Parameter resolution (cache/DB/fit)' },
                { key: 'param_cache_ms', label: '  → Cache lookup' },
                { key: 'param_db_read_ms', label: '  → DB read' },
                { key: 'param_fit_sdm_ms', label: '  → SDM fit from STC' },
                { key: 'param_db_write_ms', label: '  → DB write' },
                { key: 'estimate_power_vmpp_ms', label: 'MPP / Vmpp calculation' },
                { key: 'other_ms', label: 'Other / overhead' },
                { key: 'total_ms', label: 'Total (model)' },
              ] as const;
              const timingTotalAgg: Record<string, number> = {};
              let timingCount = 0;
              let totalExpectedPowerCalculated = 0;
              resultsArray.forEach((r) => {
                const tb = r.timing_breakdown_ms_total;
                if (tb && typeof tb === 'object') {
                  timingCount += 1;
                  totalExpectedPowerCalculated += r.expected_power_calculated ?? 0;
                  timingKeys.forEach(({ key }) => {
                    const v = (tb as Record<string, number>)[key];
                    if (typeof v === 'number') {
                      timingTotalAgg[key] = (timingTotalAgg[key] ?? 0) + v;
                    }
                  });
                }
              });
              const hasTiming = timingCount > 0;
              const avgPerCalcDiv = Math.max(totalExpectedPowerCalculated, 1);
              
              return (
                <>
                  <div className="alert alert-info mb-4">
                    <h6 className="fw-bold text-dark mb-2">Summary</h6>
                    <div className="row">
                      <div className="col-md-3">
                        <strong className="text-dark">Devices:</strong> <span className="text-dark">{successful} succeeded, {failed} failed</span>
                      </div>
                      <div className="col-md-3">
                        <strong className="text-success">Total Successful Calculations:</strong> <span className="text-dark">{totalSuccessful}</span>
                      </div>
                      <div className="col-md-3">
                        <strong className="text-danger">Total Failed Calculations:</strong> <span className="text-dark">{totalFailed}</span>
                      </div>
                      <div className="col-md-3">
                        <strong className="text-dark">Total Calculations:</strong> <span className="text-dark">{totalCalculations}</span>
                      </div>
                    </div>
                  </div>

                  {hasTiming && (
                    <div className="card mb-4">
                      <div className="card-header py-2">
                        <h6 className="fw-bold text-dark mb-0">Calculation timing breakdown</h6>
                      </div>
                      <div className="card-body py-3">
                        <p className="text-muted small mb-2">Time spent in each step (SDM model only). All values in <strong>ms</strong>. Total (model) = sum of SDM calculation time across all expected-power calls (~0.2 s). The &quot;Time taken&quot; per device below is the <strong>full run in seconds</strong> (DB reads, model, DB writes, I/O).</p>
                        <div className="table-responsive">
                          <table className="table-sm table-bordered mb-0 table">
                            <thead>
                              <tr>
                                <th className="text-dark">Step</th>
                                <th className="text-dark text-end">Total (ms)</th>
                                <th className="text-dark text-end">Avg per calc (ms)</th>
                              </tr>
                            </thead>
                            <tbody>
                              {timingKeys.map(({ key, label }) => (
                                <tr key={key}>
                                  <td className="text-dark">{label}</td>
                                  <td className="text-dark text-end">{typeof timingTotalAgg[key] === 'number' ? timingTotalAgg[key].toFixed(2) : '—'}</td>
                                  <td className="text-dark text-end">{typeof timingTotalAgg[key] === 'number' ? (timingTotalAgg[key] / avgPerCalcDiv).toFixed(2) : '—'}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    </div>
                  )}
                </>
              );
            })()}
            
            {Array.from(results.entries()).map(([deviceId, result]) => (
              <div key={deviceId} className="border-bottom mb-4 pb-3">
                <h6 className="fw-bold text-dark">{result.device_id}</h6>
                {result.success ? (
                  <>
                    <div className="row mb-2">
                      <div className="col-md-3">
                        <strong className="text-dark">Total Calculations:</strong> <span className="text-dark">{result.total_calculations}</span>
                      </div>
                      <div className="col-md-3">
                        <strong className="text-success">Successful:</strong> <span className="text-dark">{result.successful}</span>
                      </div>
                      <div className="col-md-3">
                        <strong className="text-danger">Failed:</strong> <span className="text-dark">{result.failed}</span>
                      </div>
                      <div className="col-md-3">
                        <strong className="text-info">Time taken (full run):</strong> <span className="text-dark">
                          {result.time_taken_seconds != null 
                            ? `${result.time_taken_seconds}s` 
                            : result.time_taken_ms != null 
                              ? `${(result.time_taken_ms / 1000).toFixed(2)}s`
                              : 'N/A'}
                        </span>
                        {result.timing_breakdown_ms_total?.total_ms != null && (
                          <span className="text-muted small d-block">Model only: {(result.timing_breakdown_ms_total.total_ms / 1000).toFixed(2)}s</span>
                        )}
                      </div>
                    </div>

                    {result.errors && result.errors.length > 0 && (
                      <div className="alert alert-warning mb-2">
                        <strong>Errors ({result.errors.length}):</strong>
                        <ul className="mb-0">
                          {result.errors.map((err, idx) => (
                            <li key={idx}>{err}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {result.results && result.results.length > 0 && (
                      <div>
                        <h6 className="text-dark">Sample Results (showing first {Math.min(result.results.length, 5)}):</h6>
                        <div className="calculation-results rounded border p-2">
                          <table className="table-sm table-striped mb-0 table">
                            <thead>
                              <tr>
                                <th className="text-dark">Timestamp</th>
                                <th className="text-dark">Expected (W)</th>
                                <th className="text-dark">Actual (W)</th>
                                <th className="text-dark">Loss (W)</th>
                                <th className="text-dark">Loss %</th>
                                <th className="text-dark">Irradiance (W/m²)</th>
                              </tr>
                            </thead>
                            <tbody>
                              {result.results.slice(0, 5).map((r, idx) => (
                                <tr key={idx}>
                                  <td className="text-dark">{r.timestamp ? new Date(r.timestamp).toLocaleString() : 'N/A'}</td>
                                  <td className="text-dark">{r.expected_power != null ? Number(r.expected_power).toFixed(2) : 'N/A'}</td>
                                  <td className="text-dark">{r.actual_power != null ? Number(r.actual_power).toFixed(2) : 'N/A'}</td>
                                  <td className="text-dark">{r.power_loss != null ? Number(r.power_loss).toFixed(2) : 'N/A'}</td>
                                  <td className="text-dark">{r.loss_percentage != null ? Number(r.loss_percentage).toFixed(2) : 'N/A'}%</td>
                                  <td className="text-dark">{r.irradiance != null ? Number(r.irradiance).toFixed(2) : 'N/A'}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    )}
                  </>
                ) : (
                  <div className="alert alert-danger mb-0">
                    <strong>Calculation Failed:</strong> {result.error}
                  </div>
                )}
              </div>
            ))}
            <small className="text-muted d-block mt-2">
              Results have been written to timeseries_data table. View them in Analytics page.
            </small>
          </div>
        </div>

      {/* Transposition Test (admin-only) */}
      <div className="card mt-4">
        <div className="card-header">
          <h5 className="text-dark mb-0">Transposition Test (GHI → GII)</h5>
        </div>
        <div className="card-body text-dark">
          <p className="text-muted small mb-3">
            Select asset, irradiance sensor and metric, then run transposition. GII is written to timeseries_data with device_id = asset_code_gii_tilt_azimuth. Asset must have tilt_configs in Site Onboarding.
          </p>
          <div className="row mb-3">
            <div className="col-md-6">
              <label className="form-label fw-bold">Asset</label>
              <select
                className="form-select text-dark"
                value={transposeAsset}
                onChange={(e) => setTransposeAsset(e.target.value)}
                disabled={transposeLoading}
              >
                <option value="">-- Select Asset --</option>
                {assets.map((a) => (
                  <option key={a.asset_code} value={a.asset_code}>{a.asset_name} ({a.asset_code})</option>
                ))}
              </select>
            </div>
            <div className="col-md-6">
              <label className="form-label fw-bold">Irradiance sensor</label>
              {transposeLoadingDevices ? (
                <div className="text-muted">Loading...</div>
              ) : (
                <select
                  className="form-select text-dark"
                  value={transposeIrradianceDeviceId}
                  onChange={(e) => setTransposeIrradianceDeviceId(e.target.value)}
                  disabled={transposeLoading || !transposeAsset}
                >
                  <option value="">-- Select device --</option>
                  {transposeDevices.map((d) => (
                    <option key={d.device_id} value={d.device_id}>{d.device_name} ({d.device_id})</option>
                  ))}
                </select>
              )}
            </div>
          </div>
          <div className="row mb-3">
            <div className="col-md-4">
              <label className="form-label fw-bold">Metric</label>
              <input
                type="text"
                className="form-control text-dark"
                value={transposeMetric}
                onChange={(e) => setTransposeMetric(e.target.value)}
                placeholder="e.g. ghi, irradiance"
                disabled={transposeLoading}
              />
            </div>
            <div className="col-md-4">
              <label className="form-label fw-bold">Start date & time</label>
              <input
                type="datetime-local"
                className="form-control text-dark"
                value={transposeStartDate}
                onChange={(e) => setTransposeStartDate(e.target.value)}
                disabled={transposeLoading}
              />
            </div>
            <div className="col-md-4">
              <label className="form-label fw-bold">End date & time</label>
              <input
                type="datetime-local"
                className="form-control text-dark"
                value={transposeEndDate}
                onChange={(e) => setTransposeEndDate(e.target.value)}
                disabled={transposeLoading}
              />
            </div>
          </div>
          <div className="mb-3">
            <button
              className="btn btn-primary"
              onClick={handleTranspose}
              disabled={transposeLoading || !transposeAsset || !transposeIrradianceDeviceId || !transposeStartDate || !transposeEndDate}
            >
              {transposeLoading ? (
                <>
                  <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true" />
                  Transposing...
                </>
              ) : (
                <>Transpose</>
              )}
            </button>
          </div>
          {transposeTaskStatus === 'pending' && transposeTaskId && (
            <div className="alert alert-info mb-2">
              <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true" />
              Task queued. Polling for completion… Task ID: <code>{transposeTaskId}</code>
            </div>
          )}
          {transposeError && (
            <div className="alert alert-danger mb-2">
              <strong>Error:</strong> {transposeError}
            </div>
          )}
          {transposeResult?.success && (
            <div className="alert alert-success mb-0">
              <strong>Transposition completed{transposeResult.time_taken_seconds != null ? ` in ${transposeResult.time_taken_seconds} s` : ''}.</strong>
              {transposeResult.records_written != null && (
                <div className="mt-2">Records written: <strong>{transposeResult.records_written}</strong></div>
              )}
              {transposeResult.device_ids_used && transposeResult.device_ids_used.length > 0 && (
                <div className="mt-2">
                  <strong>Device IDs used:</strong>
                  <ul className="mb-0 mt-1">
                    {transposeResult.device_ids_used.map((id) => (
                      <li key={id}><code>{id}</code></li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Upload Satellite GHI/TEMP CSV */}
      <div className="card mt-4">
        <div className="card-header">
          <h5 className="text-dark mb-0">Upload Satellite GHI/TEMP CSV</h5>
        </div>
        <div className="card-body text-dark">
          <p className="text-muted small mb-3">
            Upload a CSV with columns <code>time</code>, <code>GHI</code>, and <code>TEMP</code>. Data is written to <code>timeseries_data</code> with <code>device_id = asset_code_sat</code>, metrics <code>sat_ghi</code> and <code>sat_amb_temp</code>. If you upload again for the same time range, existing data for that range is replaced.
          </p>
          <div className="row mb-3">
            <div className="col-md-6">
              <label className="form-label fw-bold">Site</label>
              <select
                className="form-select text-dark"
                value={uploadAsset}
                onChange={(e) => setUploadAsset(e.target.value)}
                disabled={uploadLoading}
              >
                <option value="">-- Select Site --</option>
                {assets.map((a) => (
                  <option key={a.asset_code} value={a.asset_code}>{a.asset_name} ({a.asset_code})</option>
                ))}
              </select>
            </div>
            <div className="col-md-6">
              <label className="form-label fw-bold">CSV file</label>
              <input
                type="file"
                className="form-control text-dark"
                accept=".csv,.txt"
                onChange={(e) => setUploadFile(e.target.files?.[0] ?? null)}
                disabled={uploadLoading}
              />
              {uploadFile && <small className="text-muted d-block mt-1">{uploadFile.name}</small>}
            </div>
          </div>
          <button
            className="btn btn-primary"
            onClick={handleUploadSatelliteCsv}
            disabled={uploadLoading || !uploadAsset || !uploadFile}
          >
            {uploadLoading ? (
              <>
                <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true" />
                Uploading… writing to database (check server console for progress)
              </>
            ) : (
              <>Upload to database</>
            )}
          </button>
          {uploadError && (
            <div className="alert alert-danger mt-3 mb-0">
              <strong>Error:</strong> {uploadError}
            </div>
          )}
          {uploadResult?.success && (
            <div className="alert alert-success mt-3 mb-0">
              <strong>Upload complete.</strong> Device: <code>{uploadResult.device_id}</code>. Deleted existing in range: <strong>{uploadResult.deleted_count ?? 0}</strong>. Rows written: <strong>{uploadResult.rows_written ?? 0}</strong>.
              {uploadResult.start_ts && uploadResult.end_ts && (
                <div className="mt-2 small">Time range: {new Date(uploadResult.start_ts).toLocaleString()} – {new Date(uploadResult.end_ts).toLocaleString()}</div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

