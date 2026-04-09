const { chromium } = require('playwright');

(async () => {
  const dashboardUrl = process.argv[2];
  const outputPath = process.argv[3];
  const format = process.argv[4] || 'png'; // 'png' or 'pdf'
  const sessionid = process.argv[5]; // Session ID cookie
  const csrftoken = process.argv[6]; // CSRF token cookie
  const activeTab = process.argv[7] || ''; // Active tab ID for SPA (optional)
  const routePath = process.argv[8] || ''; // Route path for SPA (optional, e.g., /yield-report, /portfolio-map)
  const filtersJson = process.argv[9] || ''; // Dashboard filters JSON (optional)

  if (!dashboardUrl || !outputPath) {
    console.error('Usage: node capture_dashboard.js <url> <output> [format] [sessionid] [csrftoken] [activeTab] [route]');
    console.error('  format: png (default) or pdf');
    console.error('  sessionid: Session ID cookie value (optional)');
    console.error('  csrftoken: CSRF token cookie value (optional)');
    console.error('  activeTab: Active tab ID for SPA (optional)');
    console.error('  route: Route path for SPA (optional, e.g., /yield-report, /portfolio-map)');
    process.exit(1);
  }

  let browser;
  try {
    browser = await chromium.launch({ 
      headless: true,
      args: ['--no-sandbox', '--disable-setuid-sandbox'] // For Docker/server environments
    });
    
    // Get base URL from dashboard URL (origin: protocol + hostname + port)
    const baseUrl = new URL(dashboardUrl).origin;
    
    const context = await browser.newContext({
      viewport: { width: 1920, height: 1080 },
      deviceScaleFactor: 1, // Standard resolution (reduced from 2x to 1x for smaller file size)
    });

    // ✅ EXPORT MODE: Inject flag BEFORE React loads (ensures React can detect it)
    await context.addInitScript(() => {
      document.documentElement.classList.add('export-mode');
      console.log('Export mode enabled via addInitScript');
    });
    console.log('Added export-mode flag to context (runs before React loads)');

    // For SPA: Set localStorage BEFORE creating pages (runs for all pages in this context)
    // This MUST be done on the context, not the page, to ensure it runs before React initializes
    
    // Set the initial route path for React router to navigate to
    // This ensures React opens the exact page, not the default route
    if (routePath) {
      await context.addInitScript((route) => {
        if (route) {
          localStorage.setItem('spa-initial-route', route);
          console.log('Context InitScript: Set localStorage spa-initial-route to:', route);
        }
      }, routePath);
      console.log('Added init script to context for route:', routePath);
    }
    
    // Set the active tab ID for the dashboard
    if (activeTab) {
      await context.addInitScript((tabId) => {
        if (tabId) {
          localStorage.setItem('unified-dashboard-activeTab', tabId);
          console.log('Context InitScript: Set localStorage activeTab to:', tabId);
        }
      }, activeTab);
      console.log('Added init script to context for activeTab:', activeTab);
    }
    
    // ✅ RESTORE DASHBOARD FILTERS (CRITICAL FIX)
    // Restore filters BEFORE React loads so loadFiltersFromStorage() picks them up
    if (filtersJson) {
      try {
        const filters = JSON.parse(filtersJson);
        await context.addInitScript((filterData) => {
          // Restore all dashboard filters to localStorage
          for (const [key, value] of Object.entries(filterData)) {
            if (key.startsWith('dashboard-filters-')) {
              localStorage.setItem(key, value);
              console.log('Context InitScript: Restored filter', key);
            }
          }
        }, filters);
        console.log('Added init script to restore dashboard filters:', Object.keys(filters));
      } catch (e) {
        console.warn('Failed to parse filters JSON:', e.message);
      }
    }

    // ✅ CORRECT cookie injection using url property
    const cookies = [];

    if (sessionid) {
      cookies.push({
        name: 'sessionid',
        value: sessionid,
        url: baseUrl,   // 🔥 REQUIRED - Playwright uses this to determine domain
      });
    }

    if (csrftoken) {
      cookies.push({
        name: 'csrftoken',
        value: csrftoken,
        url: baseUrl,   // 🔥 REQUIRED
      });
    }

    // Add any other common Django cookies if needed
    // You can extend this list if your app uses other cookies

    if (cookies.length > 0) {
      console.log(`Setting ${cookies.length} cookies for ${baseUrl}`);
      await context.addCookies(cookies);
      console.log('Cookies set successfully');
    } else {
      console.warn('No cookies provided - authentication may fail');
    }

    const page = await context.newPage();

    // 🔍 VERIFICATION: Log the URL we're navigating to
    console.log('Navigating to:', dashboardUrl);
    if (routePath) {
      console.log('Route path:', routePath);
    }
    if (activeTab) {
      console.log('Active tab ID:', activeTab);
    }
    
    // Navigate to the dashboard URL
    // localStorage should already be set via context.addInitScript() above
    // React will read localStorage during initialization and show the correct tab
    await page.goto(dashboardUrl, { 
      waitUntil: 'networkidle',
      timeout: 60000 // 60 second timeout
    });
    
    // 🧪 QUICK VERIFICATION STEP
    const pageTitle = await page.title();
    const actualUrl = page.url();
    console.log('Page title:', pageTitle);
    console.log('Actual URL after navigation:', actualUrl);
    
    // Check if we're on login page (authentication failed)
    if (pageTitle.toLowerCase().includes('login') || actualUrl.includes('/login')) {
      throw new Error('Authentication failed - redirected to login page. Cookies may be invalid or expired.');
    }
    
    // For SPA: After navigation, verify and ensure correct tab is shown
    if (activeTab) {
      // Wait a bit for React to initialize
      await page.waitForTimeout(2000);
      
      // Check localStorage and verify it matches
      const storedTab = await page.evaluate(() => {
        return localStorage.getItem('unified-dashboard-activeTab');
      });
      console.log('localStorage activeTab after navigation:', storedTab);
      
      // If localStorage doesn't match OR if it's null/empty, set it and reload
      // Reload is necessary because React only reads localStorage during initial mount
      if (storedTab !== activeTab) {
        console.log('localStorage mismatch or missing, setting and reloading...');
        await page.evaluate((tabId) => {
          localStorage.setItem('unified-dashboard-activeTab', tabId);
        }, activeTab);
        
        // Reload the page so React re-initializes and reads the correct localStorage
        await page.reload({ waitUntil: 'networkidle', timeout: 60000 });
        console.log('Page reloaded with correct activeTab');
        
        // Wait a bit more for React to fully initialize after reload
        await page.waitForTimeout(3000);
      }
      
      // Wait for the correct tab's iframe to be visible
      // The active tab's iframe should have display: block (not display: none)
      console.log('Waiting for active tab iframe to become visible...');
      try {
        // Wait for iframes to load and check if at least one iframe is visible
        await page.waitForFunction(() => {
          const iframes = Array.from(document.querySelectorAll('iframe'));
          return iframes.some(iframe => {
            const style = window.getComputedStyle(iframe);
            return style.display !== 'none' && 
                   style.visibility !== 'hidden' && 
                   style.opacity !== '0';
          });
        }, { timeout: 10000 });
        console.log('Active tab iframe is visible');
      } catch (e) {
        console.warn('Could not verify active tab iframe visibility:', e.message);
        // Continue anyway - might still work
      }
    }
    
    // ✅ WAIT for filters to be applied and data to load
    // This ensures the page shows the correct filtered state, not the initial state
    console.log('Waiting for filters to be applied and data to load...');
    try {
      await page.waitForFunction(() => {
        return document.body.getAttribute('data-filters-ready') === 'true';
      }, { timeout: 15000 });
      console.log('Filters fully restored and applied, data loaded');
    } catch (e) {
      console.warn('Timeout waiting for filters-ready signal, continuing anyway:', e.message);
      // Continue with screenshot even if timeout - page might still be usable
    }
    
    // Wait for dashboard to be fully loaded
    // This ensures all charts, maps, and iframes are rendered
    await page.waitForTimeout(2000);
    
    // ✅ FIX FOR MAPS: Extra wait for map tiles, markers, and async map rendering
    // Maps are async + tile-based + WebGL/canvas-driven, they need extra time
    try {
      // Wait for map-related elements if they exist (maps, tiles, markers)
      // This helps ensure maps are fully rendered before screenshot
      await page.waitForSelector('img[src*="googleapis"], img[src*="map"], canvas, .leaflet-container, [class*="map"]', {
        timeout: 5000
      }).catch(() => {
        // If no map elements found, that's okay - not all pages have maps
        console.log('No map elements detected (page may not contain a map)');
      });
    } catch (e) {
      // Continue even if map selectors not found
      console.log('Map selector wait skipped:', e.message);
    }
    
    // Additional wait for maps/tiles/markers to fully settle
    // Maps need extra time for tiles to load and markers to position correctly
    await page.waitForTimeout(5000); // Maps NEED this extra time

    // Optional: Set viewport size for map pages (stabilizes zoom + tiles)
    // This helps ensure consistent rendering for map-heavy pages
    await page.setViewportSize({ width: 1920, height: 1200 });
    
    // Final small wait to ensure viewport changes are applied
    await page.waitForTimeout(1000);

    // ✅ FIX 1: Hide ALL navbars (Django + React) in export mode
    await page.addStyleTag({
      content: `
        /* === EXPORT MODE: HIDE ALL NAV BARS === */

        /* Django navbar (server-rendered) */
        #main-navbar,
        .django-navbar,
        header.navbar,
        nav.navbar {
          display: none !important;
        }

        /* React app top nav (client-rendered) */
        /* Hide any nav/header at the top of the page */
        nav:first-of-type,
        header:first-of-type,
        .top-navbar,
        .app-header,
        .app-topbar,
        .header,
        [class*="navbar"],
        [class*="topbar"],
        [class*="top-nav"] {
          display: none !important;
        }

        /* Safety: remove top spacing left by navs */
        body,
        .dashboard-root,
        .content-area,
        .app-layout {
          padding-top: 0 !important;
          margin-top: 0 !important;
        }
      `,
    });
    console.log('Hidden all navbars (Django + React) for screenshot');

    if (format === 'pdf') {
      // Generate PDF
      await page.pdf({
        path: outputPath,   // ✅ FIX: Use outputPath instead of output
        format: 'A4',
        printBackground: true,
        margin: {
          top: '10mm',
          right: '10mm',
          bottom: '10mm',
          left: '10mm'
        }
      });
    } else {
      // ✅ FIX 2: Force "export mode" layout - remove ALL viewport-locked constraints
      // This converts the page to a "print layout" where content expands naturally
      await page.addStyleTag({
        content: `
          /* ===== EXPORT MODE: FORCE FULL CONTENT HEIGHT ===== */

          html, body {
            height: auto !important;
            min-height: auto !important;
            overflow: visible !important;
          }

          /* Break viewport locking */
          .dashboard-root,
          .content-area,
          .main-area,
          .page-container,
          .page-scroll-root,
          .app-layout {
            height: auto !important;
            min-height: auto !important;
            max-height: none !important;
            overflow: visible !important;
          }

          /* Remove phantom space */
          .dashboard-root::after,
          .content-area::after {
            display: none !important;
            content: none !important;
          }

          /* Hide scrollbars */
          ::-webkit-scrollbar {
            display: none !important;
          }
        `,
      });
      console.log('Applied export mode layout (forced full content height)');
      
      // Wait for browser to reflow the layout (critical - DOM needs time to grow)
      await page.waitForTimeout(500);
      
      // Debug: Verify content height (optional - helps verify it's working)
      const contentHeight = await page.evaluate(() => {
        const contentArea = document.querySelector('.content-area');
        return contentArea ? contentArea.scrollHeight : null;
      });
      console.log('Content scrollHeight after export mode:', contentHeight);
      
      // ✅ Capture the content container - now it will have natural height
      try {
        // Try .content-area first (Django wrapper that contains React)
        let contentElement = await page.$('.content-area');
        if (!contentElement) {
          // Fallback to #react-root if .content-area not found
          console.log('.content-area not found, trying #react-root');
          contentElement = await page.$('#react-root');
        }
        
        if (!contentElement) {
          throw new Error('Active content container (.content-area or #react-root) not found');
        }
        
        console.log('Capturing content element (content-only screenshot)');
        await contentElement.screenshot({
          path: outputPath,
          // File size optimization: deviceScaleFactor reduced from 2 to 1 (4x fewer pixels)
          // This should reduce file size from ~6.6MB to ~1.6MB or less
        });
        console.log('Screenshot captured successfully');
      } catch (error) {
        console.error('Error capturing content element:', error.message);
        // Final fallback: full page screenshot
        console.warn('Falling back to full page screenshot');
        await page.screenshot({
          path: outputPath,
          fullPage: true,
        });
      }
    }

    await browser.close();
    console.log(`Successfully captured dashboard to ${outputPath}`); // ✅ FIX: Use outputPath instead of output
    process.exit(0);
  } catch (error) {
    console.error('Error capturing dashboard:', error.message);
    if (browser) {
      await browser.close();
    }
    process.exit(1);
  }
})();

