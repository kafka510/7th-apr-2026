import { useExportTask } from '../contexts/ExportTaskContext';

export function DownloadImageButton() {
  const { status, fileUrl, error, startTask, downloadFile, clearTask } = useExportTask();

  const handleDownload = async () => {
    // If file is ready, download it
    if (status === 'completed' && fileUrl) {
      downloadFile();
      return;
    }

    // If there's an error, clear it and start new task
    if (status === 'failed') {
      clearTask();
    }

    // Don't start new task if one is already in progress
    if (status === 'pending' || status === 'processing') {
      return;
    }

    try {
      // 🔥 THIS IS KEY: Get the ACTUAL current page URL (not a static URL)
      // window.location.href gives us the exact page the user is currently viewing
      const currentUrl = window.location.href;
      
      // For SPA: Get the route path explicitly (pathname + query string)
      // This ensures Playwright can navigate to the exact route, not just the base URL
      const routePath = window.location.pathname + window.location.search;
      
      // For SPA: Get the active tab ID from localStorage (dashboard uses this to show the correct tab)
      // This ensures Playwright captures the correct tab content, not just the default/first tab
      const activeTab = localStorage.getItem('unified-dashboard-activeTab') || '';

      // Capture filter state from localStorage
      // CRITICAL: Only capture 'dashboard-filters-*' keys - these are the SOURCE OF TRUTH
      // React components read from these exact keys on mount
      const filterData: Record<string, any> = {};
      
      try {
        // Only capture dashboard-filters-* keys (the keys React actually uses)
        for (let i = 0; i < localStorage.length; i++) {
          const key = localStorage.key(i);
          if (key && key.startsWith('dashboard-filters-')) {
            const value = localStorage.getItem(key);
            if (value) {
              try {
                filterData[key] = JSON.parse(value);
              } catch {
                // If parsing fails, skip this key
                console.warn(`Failed to parse filter data for ${key}`);
              }
            }
          }
        }
      } catch (error) {
        console.warn('Error reading localStorage for filters:', error);
      }
      
      // Also capture URL query parameters as filters (if any)
      // These will be applied via URL navigation in the capture script
      const urlParams = new URLSearchParams(window.location.search);
      if (urlParams.toString()) {
        filterData['urlParams'] = Object.fromEntries(urlParams.entries());
      }

      // Start async task
      await startTask(currentUrl, 'png', routePath, activeTab, filterData);
      
    } catch (error) {
      console.error('Error starting download:', error);
      // Error is handled by context
    }
  };

  // Determine button state
  const isDisabled = status === 'pending' || status === 'processing';
  const isCompleted = status === 'completed';
  const isFailed = status === 'failed';
  const showSpinner = status === 'pending' || status === 'processing';

  // Get tooltip text based on status
  const getTooltip = () => {
    if (isCompleted) return 'Click to download your screenshot';
    if (isFailed) return error || 'Export failed. Click to try again.';
    if (showSpinner) return 'Generating screenshot...';
    return 'Download full screen screenshot';
  };

  return (
    <button
      onClick={handleDownload}
      type="button"
      disabled={isDisabled}
      aria-label={getTooltip()}
      title={getTooltip()}
      style={{
        background: 'transparent',
        border: 'none',
        cursor: isDisabled ? 'wait' : 'pointer',
        padding: '4px 8px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        borderRadius: '6px',
        transition: 'background-color 0.2s, opacity 0.2s',
        color: 'inherit',
        opacity: isDisabled ? 0.6 : isFailed ? 0.8 : 1,
        flexShrink: 0,
        minWidth: '32px',
      }}
      onMouseEnter={(e) => {
        if (!isDisabled) {
          e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.1)';
        }
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.backgroundColor = 'transparent';
      }}
    >
      {showSpinner ? (
        // Loading spinner
        <svg
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          style={{ animation: 'spin 1s linear infinite' }}
        >
          <path d="M21 12a9 9 0 1 1-6.219-8.56" />
        </svg>
      ) : isCompleted ? (
        // Checkmark icon (ready to download)
        <svg
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          style={{ color: '#10b981' }}
        >
          <path d="M20 6L9 17l-5-5" />
        </svg>
      ) : (
        // Download icon
        <svg
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
          <polyline points="7 10 12 15 17 10" />
          <line x1="12" y1="15" x2="12" y2="3" />
        </svg>
      )}
      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </button>
  );
}


