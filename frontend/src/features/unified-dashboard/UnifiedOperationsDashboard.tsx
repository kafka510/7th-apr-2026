 
import { useState, useEffect } from 'react';
import { fetchDashboardData } from './api';
import type { DashboardData } from './types';
import { DashboardHeader } from './components/DashboardHeader';
import { DashboardSidebar } from './components/DashboardSidebar';
import { DashboardContent } from './components/DashboardContent';
import { useTheme } from '../../contexts/ThemeContext';

export function UnifiedOperationsDashboard() {
  const { theme } = useTheme();
  const [loading, setLoading] = useState(true);
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<string | null>(null);

  useEffect(() => {
    const loadDashboard = async () => {
      try {
        const data = await fetchDashboardData();
        setDashboardData(data);
        
        // Restore last active tab from localStorage
        const savedTab = localStorage.getItem('unified-dashboard-activeTab');
        const allTabIds = new Set<string>();
        data.menu.sections.forEach((section) => {
          if (section.type === 'single') {
            section.items.forEach((item) => {
              if (item.tabId) allTabIds.add(item.tabId);
            });
          } else if (section.type === 'group') {
            section.group.items.forEach((item) => {
              if (item.tabId) allTabIds.add(item.tabId);
            });
          }
        });

        if (savedTab && allTabIds.has(savedTab)) {
          setActiveTab(savedTab);
        } else if (allTabIds.size > 0) {
          // Set first available tab as default
          const firstTabId = Array.from(allTabIds)[0];
          setActiveTab(firstTabId);
        }
      } catch (error) {
        console.error('[UnifiedDashboard] Error loading dashboard data:', error);
      } finally {
        setLoading(false);
      }
    };

    loadDashboard();
  }, []);

  // Listen for download requests from iframes
  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      // Only process download requests
      if (!event.data || (event.data.type !== 'download_request' && event.data.type !== 'DOWNLOAD_REQUEST')) {
        return;
      }


      // Verify the message is from our own domain
      // In development, be more lenient with origin checking (localhost variations)
      const currentOrigin = window.location.origin;
      const eventOrigin = event.origin;
      const isLocalhost = currentOrigin.includes('localhost') || currentOrigin.includes('127.0.0.1');
      const isSameOrigin = eventOrigin === currentOrigin;
      const isLocalhostVariation = isLocalhost && (
        eventOrigin.includes('localhost') || eventOrigin.includes('127.0.0.1')
      );
      
      // For download requests, also check if it's from the same protocol and host (ignore port differences in dev)
      const currentUrl = new URL(currentOrigin);
      const eventUrl = new URL(eventOrigin);
      const isSameHost = currentUrl.hostname === eventUrl.hostname && currentUrl.protocol === eventUrl.protocol;

      if (!isSameOrigin && !isLocalhostVariation && !isSameHost) {
        console.warn('[UnifiedDashboard] Rejected download request from different origin:', eventOrigin, 'expected:', currentOrigin);
        return;
      }

        // Handle download request
        try {
          // Ensure URL is absolute
          let downloadUrl = event.data.url;
          if (!downloadUrl.startsWith('http://') && !downloadUrl.startsWith('https://')) {
            // Make it absolute using current origin
            downloadUrl = window.location.origin + (downloadUrl.startsWith('/') ? downloadUrl : '/' + downloadUrl);
          }

          // Use anchor element click - this is the most reliable method
          // The server's Content-Disposition: attachment header will trigger the download
          const link = document.createElement('a');
          link.href = downloadUrl;
          link.style.display = 'none';
          document.body.appendChild(link);

          // Trigger click
          link.click();

          // Remove link after click
          setTimeout(() => {
            if (document.body.contains(link)) {
              document.body.removeChild(link);
            }
          }, 100);
        } catch (error) {
          console.error('[UnifiedDashboard] Failed to initiate download from parent:', error);
          // Fallback: try direct navigation
          try {
            let downloadUrl = event.data.url;
            if (!downloadUrl.startsWith('http://') && !downloadUrl.startsWith('https://')) {
              downloadUrl = window.location.origin + (downloadUrl.startsWith('/') ? downloadUrl : '/' + downloadUrl);
            }
            window.location.href = downloadUrl;
          } catch (navError) {
            console.error('[UnifiedDashboard] Navigation fallback also failed:', navError);
          }
        }
    };

    window.addEventListener('message', handleMessage);

    return () => {
      window.removeEventListener('message', handleMessage);
    };
  }, []);

  const handleTabChange = (tabId: string) => {
    setActiveTab(tabId);
    localStorage.setItem('unified-dashboard-activeTab', tabId);
  };

  const toggleSidebar = () => {
    setSidebarOpen(!sidebarOpen);
  };

  if (loading || !dashboardData) {
    return (
      <div 
        className="d-flex align-items-center justify-content-center" 
        style={{ 
          height: '100vh',
          backgroundColor: theme === 'dark' ? '#1a2233' : '#f8fbff',
          color: theme === 'dark' ? '#f1f5f9' : '#1a1a1a',
          transition: 'background-color 0.3s ease, color 0.3s ease',
        }}
      >
        <div style={{ textAlign: 'center' }}>
          <div className="spinner-border text-primary" role="status" style={{ color: '#007bff' }}>
            <span className="visually-hidden">Loading...</span>
          </div>
          <p
            style={{
              marginTop: '10px',
              color: theme === 'dark' ? '#cbd5e0' : '#666666',
              fontSize: '14px',
            }}
          >
            Loading dashboard...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div
      className="dashboard-root"
      style={{
        minHeight: '100%',
        height: 'auto',
        overflow: 'visible',   // ✅ allow parent scroll
        position: 'relative',
        width: '100%',
        backgroundColor: theme === 'dark' ? '#1a2233' : '#f8fbff',
        transition: 'background-color 0.3s ease',
      }}
    >
      <DashboardHeader
        user={dashboardData.user}
        sidebarOpen={sidebarOpen}
        onToggleSidebar={toggleSidebar}
        activeTab={activeTab}
        menu={dashboardData.menu}
      />
      
      
      <DashboardSidebar
        menu={dashboardData.menu}
        activeTab={activeTab}
        onTabChange={handleTabChange}
        sidebarOpen={sidebarOpen}
      />
      
      <DashboardContent
        menu={dashboardData.menu}
        activeTab={activeTab}
        sidebarOpen={sidebarOpen}
      />
    </div>
  );
}

