import { createContext, useContext, useEffect, useState, useCallback, useRef, useMemo } from 'react';
import type { ReactNode } from 'react';
import { createJSONHeadersWithCSRF } from '../utils/csrf';

export type ExportTaskStatus = 'idle' | 'pending' | 'processing' | 'completed' | 'failed';

interface ExportTaskContextType {
  taskId: string | null;
  status: ExportTaskStatus;
  fileUrl: string | null;
  error: string | null;
  startTask: (url: string, format?: 'png' | 'pdf', route?: string, activeTab?: string, filters?: Record<string, any>) => Promise<void>;
  checkStatus: () => Promise<void>;
  downloadFile: () => void;
  clearTask: () => void;
}

const ExportTaskContext = createContext<ExportTaskContextType | undefined>(undefined);

// localStorage keys
const TASK_ID_KEY = 'export-task-id';
const TASK_STATUS_KEY = 'export-task-status';
const TASK_FILE_URL_KEY = 'export-task-file-url';

// Polling configuration with exponential backoff
const INITIAL_POLL_DELAY = 3000; // 3 seconds before first poll
const MIN_POLL_INTERVAL = 2000; // 2 seconds (initial)
const MAX_POLL_INTERVAL = 15000; // 15 seconds (max)
const BASE_POLL_INTERVAL = 10000; // 10 seconds (base)
const POLL_INTERVAL_MULTIPLIER = 1.5; // Multiply interval by this on each backoff
const MAX_POLL_TIME = 5 * 60 * 1000; // 5 minutes
const MAX_RETRIES = 3;
const STATUS_CACHE_TTL = 2000; // 2 seconds cache for status responses

export function ExportTaskProvider({ children }: { children: ReactNode }) {
  const [taskId, setTaskId] = useState<string | null>(() => {
    return localStorage.getItem(TASK_ID_KEY);
  });
  const [status, setStatus] = useState<ExportTaskStatus>(() => {
    return (localStorage.getItem(TASK_STATUS_KEY) as ExportTaskStatus) || 'idle';
  });
  const [fileUrl, setFileUrl] = useState<string | null>(() => {
    return localStorage.getItem(TASK_FILE_URL_KEY);
  });
  const [error, setError] = useState<string | null>(null);

  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const startTimeRef = useRef<number | null>(null);
  const retryCountRef = useRef<number>(0);
  const currentPollIntervalRef = useRef<number>(MIN_POLL_INTERVAL);
  const isRequestPendingRef = useRef<boolean>(false);
  const lastStatusCacheRef = useRef<{ status: ExportTaskStatus; timestamp: number } | null>(null);
  const previousStatusRef = useRef<ExportTaskStatus>('idle');
  const isTabVisibleRef = useRef<boolean>(true);

  // Request notification permission on mount
  useEffect(() => {
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission().catch(() => {
        // User denied or error - silently fail
      });
    }
  }, []);

  // Page Visibility API - pause polling when tab is inactive
  useEffect(() => {
    const handleVisibilityChange = () => {
      isTabVisibleRef.current = !document.hidden;
      
      // If tab becomes visible and we have an active task, resume polling
      if (!document.hidden && taskId && (status === 'pending' || status === 'processing')) {
        if (!pollingIntervalRef.current) {
          startPolling();
        }
      }
      // If tab becomes hidden, we'll pause polling in the checkStatus function
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    isTabVisibleRef.current = !document.hidden;

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [taskId, status]);

  // Helper to download file from task_id
  const downloadFileFromTaskId = useCallback((taskId: string) => {
    // Use the download endpoint which handles file serving properly
    const downloadUrl = `/api/export/dashboard/download/${taskId}/`;
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = `dashboard-${Date.now()}.png`;
    link.target = '_blank';
    document.body.appendChild(link);
    link.click();
    if (document.body.contains(link)) {
      document.body.removeChild(link);
    }
  }, []);

  // Show browser notification when task completes
  const showNotification = useCallback((message: string, taskIdForDownload?: string) => {
    if ('Notification' in window && Notification.permission === 'granted') {
      const notification = new Notification('Dashboard Export Ready', {
        body: message,
        icon: '/static/PEAK_LOGO.jpg',
        tag: taskId || 'export-task',
      });

      notification.onclick = () => {
        window.focus();
        if (taskIdForDownload) {
          downloadFileFromTaskId(taskIdForDownload);
        }
        notification.close();
      };
    }
  }, [taskId, downloadFileFromTaskId]);


  // Clear task state
  const clearTask = useCallback(() => {
    setTaskId(null);
    setStatus('idle');
    setFileUrl(null);
    setError(null);
    previousStatusRef.current = 'idle';
    localStorage.removeItem(TASK_ID_KEY);
    localStorage.removeItem(TASK_STATUS_KEY);
    localStorage.removeItem(TASK_FILE_URL_KEY);
    localStorage.removeItem(`${TASK_ID_KEY}_timestamp`);
    
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }
    
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    
    startTimeRef.current = null;
    retryCountRef.current = 0;
    currentPollIntervalRef.current = MIN_POLL_INTERVAL;
    isRequestPendingRef.current = false;
    lastStatusCacheRef.current = null;
  }, []);

  // Check task status with optimizations
  const checkStatus = useCallback(async () => {
    if (!taskId) return;

    // Skip if tab is not visible (will resume when tab becomes visible)
    if (!isTabVisibleRef.current) {
      return;
    }

    // Request debouncing - skip if a request is already pending
    if (isRequestPendingRef.current) {
      return;
    }

    // Check cache - avoid duplicate requests within STATUS_CACHE_TTL
    const now = Date.now();
    if (lastStatusCacheRef.current && (now - lastStatusCacheRef.current.timestamp) < STATUS_CACHE_TTL) {
      // Use cached status if available
      return;
    }

    isRequestPendingRef.current = true;

    try {
      // Create new abort controller for this request
      const controller = new AbortController();
      abortControllerRef.current = controller;

      const response = await fetch(`/api/export/dashboard/status/${taskId}/`, {
        method: 'GET',
        credentials: 'include',
        signal: controller.signal,
      });

      if (response.status === 404) {
        // Task not found - clear it
        clearTask();
        isRequestPendingRef.current = false;
        return;
      }

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();

      // Cache the response
      lastStatusCacheRef.current = {
        status: data.status,
        timestamp: now,
      };

      // Only update localStorage if status actually changed
      const statusChanged = data.status !== previousStatusRef.current;
      
      if (statusChanged) {
        setStatus(data.status);
        previousStatusRef.current = data.status;
        localStorage.setItem(TASK_STATUS_KEY, data.status);
      }

      if (data.status === 'completed') {
        // Task completed
        setFileUrl(data.file_url);
        if (data.file_url) {
          localStorage.setItem(TASK_FILE_URL_KEY, data.file_url);
        }
        
        // Stop polling
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current);
          pollingIntervalRef.current = null;
        }

        // Reset polling interval for next task
        currentPollIntervalRef.current = MIN_POLL_INTERVAL;

        // Show notification (pass task_id for download)
        showNotification('Your dashboard screenshot is ready to download', taskId);

        // Reset retry count
        retryCountRef.current = 0;
      } else if (data.status === 'failed') {
        // Task failed
        setError(data.error || 'Export failed');
        
        // Stop polling
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current);
          pollingIntervalRef.current = null;
        }

        // Reset polling interval for next task
        currentPollIntervalRef.current = MIN_POLL_INTERVAL;

        // Show error notification
        if ('Notification' in window && Notification.permission === 'granted') {
          new Notification('Dashboard Export Failed', {
            body: data.error || 'Export failed. Please try again.',
            icon: '/static/PEAK_LOGO.jpg',
          });
        }

        // Reset retry count
        retryCountRef.current = 0;
      } else if (data.status === 'processing' || data.status === 'pending') {
        // Still processing - continue polling with exponential backoff
        retryCountRef.current = 0; // Reset retry on successful response
        
        // Increase polling interval (exponential backoff)
        currentPollIntervalRef.current = Math.min(
          Math.floor(currentPollIntervalRef.current * POLL_INTERVAL_MULTIPLIER),
          MAX_POLL_INTERVAL
        );

        // Restart polling with new interval (without resetting to initial delay)
        // Use the helper function that's defined above
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current);
          pollingIntervalRef.current = null;
        }
        pollingIntervalRef.current = setInterval(() => {
          if (!isTabVisibleRef.current) return;
          if (startTimeRef.current && Date.now() - startTimeRef.current > MAX_POLL_TIME) {
            setError('Export timed out. Please try again.');
            setStatus('failed');
            if (pollingIntervalRef.current) {
              clearInterval(pollingIntervalRef.current);
              pollingIntervalRef.current = null;
            }
            return;
          }
          checkStatus();
        }, currentPollIntervalRef.current);
      }

    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        // Request was aborted - ignore
        isRequestPendingRef.current = false;
        return;
      }

      // Network error - retry
      retryCountRef.current += 1;
      
      if (retryCountRef.current >= MAX_RETRIES) {
        // Max retries reached
        setError('Failed to check export status. Please refresh the page.');
        setStatus('failed');
        
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current);
          pollingIntervalRef.current = null;
        }
      }
      // Otherwise, continue polling (will retry on next interval)
    } finally {
      isRequestPendingRef.current = false;
    }
  }, [taskId, showNotification, clearTask]);

  // Helper to start interval polling (used by both startPolling and when updating interval)
  const startIntervalPolling = useCallback(() => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }

    pollingIntervalRef.current = setInterval(() => {
      // Skip if tab is not visible
      if (!isTabVisibleRef.current) {
        return;
      }

      // Check if max time exceeded
      if (startTimeRef.current && Date.now() - startTimeRef.current > MAX_POLL_TIME) {
        setError('Export timed out. Please try again.');
        setStatus('failed');
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current);
          pollingIntervalRef.current = null;
        }
        return;
      }

      // Check status
      checkStatus();
    }, currentPollIntervalRef.current);
  }, [checkStatus]);

  // Start polling with exponential backoff
  const startPolling = useCallback(() => {
    if (pollingIntervalRef.current) {
      return; // Already polling
    }

    // Reset polling interval to initial value only if starting fresh
    if (!startTimeRef.current) {
      currentPollIntervalRef.current = MIN_POLL_INTERVAL;
      startTimeRef.current = Date.now();
    }

    // Initial delay before first poll
    setTimeout(() => {
      if (!taskId) return; // Task was cleared

      // First poll after initial delay
      checkStatus();

      // Then start interval polling
      startIntervalPolling();
    }, INITIAL_POLL_DELAY);
  }, [checkStatus, taskId, startIntervalPolling]);

  // Start export task
  const startTask = useCallback(async (
    url: string,
    format: 'png' | 'pdf' = 'png',
    route?: string,
    activeTab?: string,
    filters?: Record<string, any>
  ) => {
    try {
      // Clear any previous task
      clearTask();

      // Prepare request body
      const body: Record<string, any> = {
        url,
        format,
      };

      if (route) body.route = route;
      if (activeTab) body.activeTab = activeTab;
      if (filters) body.filters = filters;

      // Create task using the same pattern as the API client
      const headers = createJSONHeadersWithCSRF();
      const response = await fetch('/api/export/dashboard/', {
        method: 'POST',
        headers: {
          ...headers,
        },
        credentials: 'include',
        body: JSON.stringify(body),
      });

      if (!response.ok) {
        // Handle 403 Forbidden (likely CSRF issue)
        if (response.status === 403) {
          const errorData = await response.json().catch(() => ({ error: 'Forbidden' }));
          throw new Error(errorData.error || 'CSRF verification failed. Please refresh the page and try again.');
        }
        const errorData = await response.json().catch(() => ({ error: 'Unknown error' }));
        throw new Error(errorData.error || `Server error: ${response.status}`);
      }

      const data = await response.json();

      // Set task state
      setTaskId(data.task_id);
      setStatus('pending');
      previousStatusRef.current = 'pending';
      setError(null);
      
      // Reset polling interval for new task
      currentPollIntervalRef.current = MIN_POLL_INTERVAL;
      lastStatusCacheRef.current = null;
      
      // Save to localStorage with timestamp
      localStorage.setItem(TASK_ID_KEY, data.task_id);
      localStorage.setItem(TASK_STATUS_KEY, 'pending');
      localStorage.setItem(`${TASK_ID_KEY}_timestamp`, Date.now().toString());

      // Start polling (with initial delay)
      startPolling();

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to start export';
      setError(errorMessage);
      setStatus('failed');
    }
  }, [clearTask, startPolling]);

  // Download file
  const downloadFile = useCallback(() => {
    if (!taskId) return;

    downloadFileFromTaskId(taskId);
    
    // Clear task after download
    clearTask();
  }, [taskId, downloadFileFromTaskId, clearTask]);

  // Resume polling on mount if task exists - but validate first
  useEffect(() => {
    const validateAndResumeTask = async () => {
      if (!taskId) return;

      // Check if task is too old (more than 1 hour) - clear it
      const taskTimestamp = localStorage.getItem(`${TASK_ID_KEY}_timestamp`);
      if (taskTimestamp) {
        const age = Date.now() - parseInt(taskTimestamp, 10);
        const MAX_AGE = 60 * 60 * 1000; // 1 hour
        if (age > MAX_AGE) {
          // Task is too old, clear it
          clearTask();
          return;
        }
      }

      // Validate task exists on server before resuming
      if (status === 'pending' || status === 'processing') {
        try {
          const response = await fetch(`/api/export/dashboard/status/${taskId}/`, {
            method: 'GET',
            credentials: 'include',
          });

          if (response.status === 404) {
            // Task doesn't exist on server - clear it
            clearTask();
            return;
          }

          if (response.ok) {
            const data = await response.json();
            // Update status from server (only if changed)
            const statusChanged = data.status !== previousStatusRef.current;
            if (statusChanged) {
              setStatus(data.status);
              previousStatusRef.current = data.status;
              localStorage.setItem(TASK_STATUS_KEY, data.status);
            }

            if (data.status === 'completed') {
              setFileUrl(data.file_url);
              if (data.file_url) {
                localStorage.setItem(TASK_FILE_URL_KEY, data.file_url);
              }
              showNotification('Your dashboard screenshot is ready to download', taskId);
            } else if (data.status === 'failed') {
              setError(data.error || 'Export failed');
            } else if (data.status === 'pending' || data.status === 'processing') {
              // Task is still valid - resume polling with optimizations
              currentPollIntervalRef.current = BASE_POLL_INTERVAL; // Start with base interval for resumed tasks
              startPolling();
            }
          }
        } catch (err) {
          // Network error - clear task to avoid infinite polling
          console.warn('Failed to validate task on mount, clearing:', err);
          clearTask();
        }
      }
    };

    validateAndResumeTask();

    return () => {
      // Cleanup on unmount
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
        abortControllerRef.current = null;
      }
    };
  }, [taskId, status, startPolling, clearTask, showNotification]);

  // Listen for storage events (sync across tabs)
  useEffect(() => {
    const handleStorage = (e: StorageEvent) => {
      if (e.key === TASK_ID_KEY && e.newValue !== taskId) {
        setTaskId(e.newValue);
      }
      if (e.key === TASK_STATUS_KEY && e.newValue !== status) {
        setStatus(e.newValue as ExportTaskStatus);
      }
      if (e.key === TASK_FILE_URL_KEY && e.newValue !== fileUrl) {
        setFileUrl(e.newValue);
      }
    };

    window.addEventListener('storage', handleStorage);
    return () => window.removeEventListener('storage', handleStorage);
  }, [taskId, status, fileUrl]);

  // Memoize context value to prevent unnecessary re-renders
  const value: ExportTaskContextType = useMemo(() => ({
    taskId,
    status,
    fileUrl,
    error,
    startTask,
    checkStatus,
    downloadFile,
    clearTask,
  }), [taskId, status, fileUrl, error, startTask, checkStatus, downloadFile, clearTask]);

  return (
    <ExportTaskContext.Provider value={value}>
      {children}
    </ExportTaskContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useExportTask() {
  const context = useContext(ExportTaskContext);
  if (context === undefined) {
    throw new Error('useExportTask must be used within an ExportTaskProvider');
  }
  return context;
}

