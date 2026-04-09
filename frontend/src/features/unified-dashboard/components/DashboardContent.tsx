 
import { useState, useRef, useEffect, useMemo } from "react";
import type { DashboardMenu } from "../types";
import { LossEventsPage } from '../../loss-analytics/LossEventsPage';
import { useTheme } from '../../../contexts/ThemeContext';

interface DashboardContentProps {
  menu: DashboardMenu;
  activeTab: string | null;
  sidebarOpen: boolean;
}

export function DashboardContent({
  menu,
  activeTab,
  sidebarOpen,
}: DashboardContentProps) {
  const { theme } = useTheme();
  const [loadedTabs, setLoadedTabs] = useState<Set<string>>(new Set());
  const loadedTabsRef = useRef<Set<string>>(new Set());
  const iframeRefs = useRef<Map<string, HTMLIFrameElement>>(new Map());

  // Notify all iframes when theme changes
  useEffect(() => {
    const iframes = document.querySelectorAll('iframe');
    iframes.forEach((iframe) => {
      try {
        iframe.contentWindow?.postMessage(
          { type: 'theme-changed', theme },
          '*'
        );
      } catch {
        // Ignore cross-origin errors
      }
    });
  }, [theme]);

  /* Track loaded tabs once */
  useEffect(() => {
    if (activeTab && !loadedTabsRef.current.has(activeTab)) {
      loadedTabsRef.current.add(activeTab);
      setLoadedTabs(new Set(loadedTabsRef.current));
    }
  }, [activeTab]);

  /* Build tab list */
  const tabs = useMemo(() => {
    const list: Array<{ id: string; url: string | null }> = [];
    for (const section of menu.sections) {
      if (section.type === "single") {
        section.items.forEach((item) =>
          list.push({ id: item.tabId!, url: item.url || null })
        );
      }
      if (section.type === "group") {
        section.group.items.forEach((item) =>
          list.push({ id: item.tabId!, url: item.url || null })
        );
      }
    }
    return list;
  }, [menu.sections]);

  const sidebarWidth = 250;

  return (
    <div
      className="main-area"
      style={{
        flex: 1,
        paddingTop: "50px",
        marginLeft: sidebarOpen ? `${sidebarWidth}px` : "0",
        position: "relative",
        overflow: "visible",
        height: "auto",
        minHeight: "unset",
        backgroundColor: theme === 'dark' ? '#1a2233' : '#f8fbff', // Theme-aware background
        boxSizing: "border-box",
        transition: 'background-color 0.3s ease',
      }}
    >
      {/* ===== CONTENT AREA (NO SCROLL - Django .content-area handles it) ===== */}
      <div
        className="content-scroll"
        style={{
          width: "100%",
          overflow: "visible",   // ✅ DO NOT SCROLL HERE
          position: "relative",
          backgroundColor: theme === 'dark' ? '#1a2233' : '#f8fbff', // Theme-aware background
          transition: 'background-color 0.3s ease',
        }}
      >
        {tabs.length === 0 ? (
          <div 
            style={{ 
              padding: 20, 
              textAlign: "center",
              backgroundColor: theme === 'dark' ? '#1a2233' : '#f8fbff',
              color: theme === 'dark' ? '#f1f5f9' : '#1a1a1a',
              transition: 'background-color 0.3s ease, color 0.3s ease',
            }}
          >
            <p>No tabs available.</p>
          </div>
        ) : (
          tabs.map((tab) => {
            const isActive = activeTab === tab.id;
            const isLoaded = loadedTabs.has(tab.id);
            const url = tab.url;

            return (
              <div
                key={tab.id}
                style={{
                  display: isActive ? "block" : "none",
                  width: "100%",
                  height: "auto",
                  minHeight: 0,
                  position: "relative",
                  backgroundColor: theme === 'dark' ? '#1a2233' : '#f8fbff', // Theme-aware background
                  transition: 'background-color 0.3s ease',
                }}
              >
                {/* Internal React tab for Loss Events */}
                {isLoaded && tab.id === 'dash-loss-events' ? (
                  <LossEventsPage />
                ) : isLoaded && url ? (
                  <iframe
                    ref={(el) => {
                      if (el) iframeRefs.current.set(tab.id, el);
                      else iframeRefs.current.delete(tab.id);
                    }}
                    src={url}
                    loading="lazy"
                    title={tab.id}
                    sandbox="
                      allow-scripts
                      allow-same-origin
                      allow-forms
                      allow-popups
                      allow-top-navigation-by-user-activation
                      allow-downloads
                      allow-modals
                    "
                    onLoad={(e) => {
                      const iframe = e.currentTarget;

                      try {
                        const iframeWindow = iframe.contentWindow;
                        const iframeDoc = iframe.contentDocument;

                        if (!iframeWindow || !iframeDoc) return;

                        // Many legacy Django templates force html/body to 100vh, which makes
                        // the iframe taller than the actual content and leaves a big empty patch.
                        // Normalize those heights so ResizeObserver can measure the real content.
                        try {
                          iframeDoc.documentElement.style.height = 'auto';
                          iframeDoc.documentElement.style.minHeight = '0';
                          iframeDoc.body.style.height = 'auto';
                          iframeDoc.body.style.minHeight = '0';
                        } catch {
                          // Ignore style errors; not critical
                        }

                        // Send current theme to iframe
                        try {
                          const currentTheme = localStorage.getItem('peak-energy-theme') || 'dark';
                          iframeWindow.postMessage(
                            { type: 'theme-changed', theme: currentTheme },
                            '*'
                          );
                        } catch {
                          // Ignore cross-origin errors
                        }

                        // ============== FINAL REAL FIX: ResizeObserver ============
                        // eslint-disable-next-line @typescript-eslint/no-explicit-any
                        const ResizeObserverClass = (iframeWindow as any).ResizeObserver;
                        if (ResizeObserverClass) {
                          const ro = new ResizeObserverClass(() => {
                            const newHeight = Math.max(
                              iframeDoc.documentElement.scrollHeight,
                              iframeDoc.body.scrollHeight
                            );
                            iframe.style.height = `${newHeight}px`;
                          });

                          ro.observe(iframeDoc.documentElement);
                          ro.observe(iframeDoc.body);
                        } else {
                          // Fallback: one‑time height adjustment
                          const newHeight = Math.max(
                            iframeDoc.documentElement.scrollHeight,
                            iframeDoc.body.scrollHeight
                          );
                          iframe.style.height = `${newHeight}px`;
                        }
                      } catch (error) {
                        console.error("ResizeObserver error:", error);
                      }
                    }}
                    style={{
                      width: "100%",
                      border: "none",

                      // Initial safe height before ResizeObserver adjusts it
                      height: "1200px",
                      display: "block",
                      backgroundColor: theme === 'dark' ? '#1a2233' : '#f8fbff', // Theme-aware background
                      transition: 'background-color 0.3s ease',
                    }}
                  />
                ) : (
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      height: "200px",
                      background: theme === 'dark' ? '#1a2233' : '#f8fbff', // Theme-aware background
                      transition: 'background-color 0.3s ease',
                    }}
                  >
                    <div style={{ textAlign: "center" }}>
                      <div className="spinner-border text-primary" role="status"></div>
                      <p style={{ marginTop: 10 }}>Loading...</p>
                    </div>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

