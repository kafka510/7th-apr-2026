#!/usr/bin/env python3
"""
Capture dashboard as PNG/PDF using Playwright (Python)
This replaces the Node.js version for production environments without Node.js
"""

import sys
import asyncio
from playwright.async_api import async_playwright


async def capture_dashboard():
    """Capture dashboard screenshot/PDF"""
    if len(sys.argv) < 3:
        print("Usage: python capture_dashboard.py <url> <output> [format] [sessionid] [csrftoken] [activeTab] [route] [filters]")
        print("  format: png (default) or pdf")
        print("  sessionid: Session ID cookie value (optional)")
        print("  csrftoken: CSRF token cookie value (optional)")
        print("  activeTab: Active tab ID for SPA (optional)")
        print("  route: Route path for SPA (optional)")
        print("  filters: JSON string with filter data (optional)")
        sys.exit(1)

    # sys.argv[0] is the script name, sys.argv[1] is the first argument (url)
    dashboard_url = sys.argv[1]
    output_path = sys.argv[2]
    format_type = sys.argv[3] if len(sys.argv) > 3 else 'png'
    sessionid = sys.argv[4] if len(sys.argv) > 4 else ''
    csrftoken = sys.argv[5] if len(sys.argv) > 5 else ''
    active_tab = sys.argv[6] if len(sys.argv) > 6 else ''
    route_path = sys.argv[7] if len(sys.argv) > 7 else ''
    filters_json = sys.argv[8] if len(sys.argv) > 8 else ''

    browser = None
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']  # For Docker/server environments
            )

            # Get base URL from dashboard URL
            from urllib.parse import urlparse
            base_url = urlparse(dashboard_url).scheme + "://" + urlparse(dashboard_url).netloc

            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                device_scale_factor=1,
            )

            # ✅ EXPORT MODE: Inject flag BEFORE React loads
            await context.add_init_script("""
                document.documentElement.classList.add('export-mode');
                console.log('Export mode enabled via addInitScript');
            """)
            print('Added export-mode flag to context (runs before React loads)')

            # Set the initial route path for React router
            if route_path:
                await context.add_init_script(f"""
                    if ('{route_path}') {{
                        localStorage.setItem('spa-initial-route', '{route_path}');
                        console.log('Context InitScript: Set localStorage spa-initial-route to: {route_path}');
                    }}
                """)
                print(f'Added init script to context for route: {route_path}')

            # Set the active tab ID for the dashboard
            if active_tab:
                await context.add_init_script(f"""
                    if ('{active_tab}') {{
                        localStorage.setItem('unified-dashboard-activeTab', '{active_tab}');
                        console.log('Context InitScript: Set localStorage activeTab to: {active_tab}');
                    }}
                """)
                print(f'Added init script to context for activeTab: {active_tab}')

            # Set filter data from the filters parameter
            # CRITICAL: React components read from 'dashboard-filters-<dashboardId>' keys
            # We must restore filters to the EXACT keys React expects, not generic keys
            if filters_json:
                try:
                    import json
                    filters_data = json.loads(filters_json)
                    
                    # Build init script that restores filters to the correct keys
                    filters_js = json.dumps(filters_data)
                    await context.add_init_script(f"""
                        (function() {{
                            try {{
                                const filters = {filters_js};
                                
                                // Restore each dashboard-filters-* key that React expects
                                for (const [key, value] of Object.entries(filters)) {{
                                    if (key.startsWith('dashboard-filters-')) {{
                                        localStorage.setItem(key, JSON.stringify(value));
                                        console.log('Export: Restored filters to', key);
                                    }}
                                }}
                                
                                // Also handle urlParams if present
                                if (filters.urlParams) {{
                                    // urlParams will be applied via URL navigation
                                    console.log('Export: urlParams will be applied via URL');
                                }}
                            }} catch (e) {{
                                console.error('Export filter restore failed', e);
                            }}
                        }})();
                    """)
                    
                    # Log which filter keys we're restoring
                    dashboard_filter_keys = [k for k in filters_data.keys() if k.startswith('dashboard-filters-')]
                    print(f'Restoring filters to keys: {dashboard_filter_keys}')
                except Exception as e:
                    print(f'Warning: Could not parse filter data: {e}')

            # Set cookies
            cookies = []
            if sessionid:
                cookies.append({
                    'name': 'sessionid',
                    'value': sessionid,
                    'url': base_url,
                })
            if csrftoken:
                cookies.append({
                    'name': 'csrftoken',
                    'value': csrftoken,
                    'url': base_url,
                })

            if cookies:
                print(f'Setting {len(cookies)} cookies for {base_url}')
                await context.add_cookies(cookies)
                print('Cookies set successfully')
            else:
                print('Warning: No cookies provided - authentication may fail')

            page = await context.new_page()

            print(f'Navigating to: {dashboard_url}')
            if route_path:
                print(f'Route path: {route_path}')
            if active_tab:
                print(f'Active tab ID: {active_tab}')

            # Navigate to the dashboard URL
            await page.goto(dashboard_url, wait_until='networkidle', timeout=60000)

            # Verify we're not on login page
            page_title = await page.title()
            actual_url = page.url
            print(f'Page title: {page_title}')
            print(f'Actual URL after navigation: {actual_url}')

            if 'login' in page_title.lower() or '/login' in actual_url:
                raise Exception('Authentication failed - redirected to login page. Cookies may be invalid or expired.')

            # Apply URL parameters from filters if present
            if filters_json:
                try:
                    import json
                    from urllib.parse import urlparse, parse_qs, urlencode
                    filters_data = json.loads(filters_json)
                    if 'urlParams' in filters_data and filters_data['urlParams']:
                        # Update URL with filter parameters
                        url_params = filters_data['urlParams']
                        current_url = page.url
                        url_obj = urlparse(current_url)
                        query_params = parse_qs(url_obj.query)
                        # Merge filter params
                        for key, value in url_params.items():
                            query_params[key] = [str(value)]
                        new_query = urlencode(query_params, doseq=True)
                        new_url = f"{url_obj.scheme}://{url_obj.netloc}{url_obj.path}?{new_query}" if new_query else f"{url_obj.scheme}://{url_obj.netloc}{url_obj.path}"
                        if new_url != current_url:
                            print(f'Navigating to URL with filters: {new_url}')
                            await page.goto(new_url, wait_until='networkidle', timeout=60000)
                except Exception as e:
                    print(f'Warning: Could not apply URL filter parameters: {e}')

            # For SPA: After navigation, verify and ensure correct tab is shown
            if active_tab:
                await page.wait_for_timeout(2000)

                stored_tab = await page.evaluate("localStorage.getItem('unified-dashboard-activeTab')")
                print(f'localStorage activeTab after navigation: {stored_tab}')

                if stored_tab != active_tab:
                    print('localStorage mismatch or missing, setting and reloading...')
                    await page.evaluate(f"localStorage.setItem('unified-dashboard-activeTab', '{active_tab}')")
                    await page.reload(wait_until='networkidle', timeout=60000)
                    print('Page reloaded with correct activeTab')
                    await page.wait_for_timeout(3000)

                # Wait for the correct tab's iframe to be visible
                print('Waiting for active tab iframe to become visible...')
                try:
                    await page.wait_for_function("""
                        () => {
                            const iframes = Array.from(document.querySelectorAll('iframe'));
                            return iframes.some(iframe => {
                                const style = window.getComputedStyle(iframe);
                                return style.display !== 'none' && 
                                       style.visibility !== 'hidden' && 
                                       style.opacity !== '0';
                            });
                        }
                    """, timeout=10000)
                    print('Active tab iframe is visible')
                except Exception as e:
                    print(f'Could not verify active tab iframe visibility: {e}')

            # Wait for dashboard to be fully loaded
            await page.wait_for_timeout(3000)
            
            # Wait for filters to be applied (if any)
            # Filters might trigger data reloads, so wait a bit more
            if filters_json:
                print('Waiting for filters to be applied...')
                
                # Step 1: Debug - Check what filters are actually in localStorage
                debug_filters = await page.evaluate("""
                    () => {
                        const keys = Object.keys(localStorage);
                        return {
                            allKeys: keys,
                            dashboardFilterKeys: keys.filter(k => k.startsWith('dashboard-filters-'))
                                .map(k => ({ key: k, value: localStorage.getItem(k) }))
                        };
                    }
                """)
                print(f'DEBUG: Filter state before reload - Dashboard filter keys: {[k["key"] for k in debug_filters["dashboardFilterKeys"]]}')
                
                # Step 2: Filters should already be in localStorage from init script
                # But verify and reload to ensure React reads them on mount
                print('Reloading page to ensure React components read filters from localStorage on mount...')
                await page.reload(wait_until='networkidle', timeout=60000)
                print('Page reloaded')
                await page.wait_for_timeout(2000)  # Wait for React to initialize
                
                # Step 3: Debug - Verify filters are still there after reload
                debug_filters_after = await page.evaluate("""
                    () => {
                        const keys = Object.keys(localStorage);
                        return {
                            allKeys: keys,
                            dashboardFilterKeys: keys.filter(k => k.startsWith('dashboard-filters-'))
                                .map(k => ({ key: k, value: localStorage.getItem(k) }))
                        };
                    }
                """)
                print(f'DEBUG: Filter state after reload - Dashboard filter keys: {[k["key"] for k in debug_filters_after["dashboardFilterKeys"]]}')
                
                # Step 4: CRITICAL - Trigger filter application
                # React components read filters on mount, but we need to ensure they're applied
                # Dispatch events that dashboards might listen to, and trigger any global filter apply functions
                await page.evaluate("""
                    (() => {
                        console.log('Export: Triggering filter application...');
                        
                        // Trigger common filter application events
                        window.dispatchEvent(new CustomEvent('dashboard:filters-applied'));
                        window.dispatchEvent(new CustomEvent('dashboard:apply-filters-from-storage'));
                        window.dispatchEvent(new CustomEvent('dashboard:save-filters-before-download'));
                        
                        // Try to trigger global filter apply functions if they exist
                        if (window.applyDashboardFilters && typeof window.applyDashboardFilters === 'function') {
                            window.applyDashboardFilters();
                            console.log('Export: Called window.applyDashboardFilters()');
                        }
                        
                        // Try Redux/Zustand store dispatch if available
                        if (window.store && window.store.dispatch && typeof window.store.dispatch === 'function') {
                            window.store.dispatch({ type: 'APPLY_FILTERS_FROM_STORAGE' });
                            console.log('Export: Dispatched APPLY_FILTERS_FROM_STORAGE action');
                        }
                        
                        // Force React to re-read filters by triggering a storage event
                        // This simulates localStorage being updated, which some components listen to
                        window.dispatchEvent(new StorageEvent('storage', {
                            key: 'dashboard-filters-sales',
                            newValue: localStorage.getItem('dashboard-filters-sales'),
                            storageArea: localStorage
                        }));
                        
                        console.log('Export: Triggered all filter application hooks');
                    })();
                """)
                print('Triggered filter application events and hooks')
                
                # Step 5: Wait for dashboard to signal filters are ready
                # Sales component sets 'data-filters-ready' attribute when data and filters are ready
                try:
                    await page.wait_for_function("""
                        () => {
                            return document.body.getAttribute('data-filters-ready') === 'true';
                        }
                    """, timeout=15000)
                    print('Dashboard signaled filters are ready')
                except Exception:
                    print('Timeout waiting for dashboard-filters-ready signal, continuing...')
                
                # Step 6: Wait for filters to be applied and data to update
                await page.wait_for_timeout(2000)
                
                # Step 7: Debug - Check API calls to verify filters are being used
                api_calls = []
                def log_request(request):
                    url = request.url
                    if '/api/' in url or '/sales-data' in url or '/dashboard' in url or '/data/' in url:
                        api_calls.append(url)
                
                page.on('request', log_request)
                await page.wait_for_timeout(3000)
                page.remove_listener('request', log_request)
                
                print('DEBUG: API calls after filter application:')
                for url in api_calls:
                    print(f'  - {url[:150]}')
                
                # Step 8: Verify filters are actually in React state by checking the DOM
                # Look for filter UI elements that should show selected values
                filter_state_check = await page.evaluate("""
                    () => {
                        // Check if filter dropdowns show selected values
                        const filterElements = document.querySelectorAll('[class*="filter"], [class*="select"], [data-filter]');
                        const hasActiveFilters = Array.from(filterElements).some(el => {
                            const text = el.textContent || '';
                            const hasSelection = text.includes('Selected') || 
                                                el.getAttribute('aria-selected') === 'true' ||
                                                el.classList.contains('selected');
                            return hasSelection;
                        });
                        
                        // Check localStorage one more time
                        const filterKeys = Object.keys(localStorage)
                            .filter(k => k.startsWith('dashboard-filters-'))
                            .map(k => ({ key: k, value: localStorage.getItem(k) }));
                        
                        return {
                            hasActiveFilters,
                            filterKeys: filterKeys.map(f => f.key),
                            filterValues: filterKeys
                        };
                    }
                """)
                print(f'DEBUG: Filter state check - Has active filters in UI: {filter_state_check["hasActiveFilters"]}')
                print(f'DEBUG: Filter keys in localStorage: {filter_state_check["filterKeys"]}')
                
                # Step 2: After reload, React components should have read filters from localStorage on mount
                # Now we just need to wait for the filtered data to load and render
                print('Waiting for filtered data to load after reload...')
                
                # Wait for network to be idle (all data loaded)
                try:
                    await page.wait_for_load_state('networkidle', timeout=30000)
                    print('Network is idle - data should be loaded')
                except Exception:
                    print('Network idle timeout, continuing anyway...')
                
                # Wait for loading indicators to disappear
                try:
                    await page.wait_for_function("""
                        () => {
                            const loaders = document.querySelectorAll('[class*="loading"], [class*="spinner"], [class*="Loading"]');
                            return Array.from(loaders).every(loader => {
                                const style = window.getComputedStyle(loader);
                                return style.display === 'none' || style.visibility === 'hidden';
                            });
                        }
                    """, timeout=15000)
                    print('All loaders disappeared')
                except Exception:
                    print('Timeout waiting for loaders, continuing anyway...')
                
                # Wait for charts/data to be rendered
                try:
                    await page.wait_for_function("""
                        () => {
                            // Check if there are chart containers or data elements visible
                            const charts = document.querySelectorAll('[id*="chart"], [class*="chart"], canvas, svg');
                            const hasCharts = charts.length > 0;
                            
                            // Check if there are data tables or lists
                            const dataElements = document.querySelectorAll('table, [class*="data"], [class*="table"]');
                            const hasData = dataElements.length > 0;
                            
                            // At least one should be present
                            return hasCharts || hasData;
                        }
                    """, timeout=10000)
                    print('Charts/data elements are present')
                except Exception:
                    print('Could not verify charts/data elements, continuing...')
                
                # Final wait for any animations or transitions
                await page.wait_for_timeout(2000)
                print('Filters should be applied and filtered data should be rendered')
                
                # Step 5: Wait for any loading indicators to disappear
                try:
                    await page.wait_for_function("""
                        () => {
                            const loaders = document.querySelectorAll('[class*="loading"], [class*="spinner"], [class*="Loading"]');
                            return Array.from(loaders).every(loader => {
                                const style = window.getComputedStyle(loader);
                                return style.display === 'none' || style.visibility === 'hidden';
                            });
                        }
                    """, timeout=15000)
                    print('All loaders disappeared')
                except Exception:
                    print('Timeout waiting for loaders, continuing anyway...')
                
                # Step 6: Wait for charts/data to be rendered (check for chart containers or data elements)
                try:
                    await page.wait_for_function("""
                        () => {
                            // Check if there are chart containers or data elements visible
                            const charts = document.querySelectorAll('[id*="chart"], [class*="chart"], canvas, svg');
                            const hasCharts = charts.length > 0;
                            
                            // Check if there are data tables or lists
                            const dataElements = document.querySelectorAll('table, [class*="data"], [class*="table"]');
                            const hasData = dataElements.length > 0;
                            
                            // At least one should be present
                            return hasCharts || hasData;
                        }
                    """, timeout=10000)
                    print('Charts/data elements are present')
                except Exception:
                    print('Could not verify charts/data elements, continuing...')
                
                # Step 7: Final wait for any animations or transitions
                await page.wait_for_timeout(2000)
                print('Filters should be applied and data loaded')

            # Extra wait for map tiles, markers, and async map rendering
            try:
                await page.wait_for_selector('img[src*="googleapis"], img[src*="map"], canvas, .leaflet-container, [class*="map"]', timeout=5000)
            except Exception:
                print('No map elements detected (page may not contain a map)')

            # Additional wait for maps/tiles/markers to fully settle
            await page.wait_for_timeout(5000)

            # Set viewport size for map pages
            await page.set_viewport_size({'width': 1920, 'height': 1200})
            await page.wait_for_timeout(1000)

            # Hide ALL navbars (Django + React) in export mode
            await page.add_style_tag(content="""
                /* === EXPORT MODE: HIDE ALL NAV BARS === */
                #main-navbar,
                .django-navbar,
                header.navbar,
                nav.navbar,
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
                body,
                .dashboard-root,
                .content-area,
                .app-layout {
                    padding-top: 0 !important;
                    margin-top: 0 !important;
                }
            """)
            print('Hidden all navbars (Django + React) for screenshot')

            if format_type == 'pdf':
                # Generate PDF
                await page.pdf(
                    path=output_path,
                    format='A4',
                    print_background=True,
                    margin={
                        'top': '10mm',
                        'right': '10mm',
                        'bottom': '10mm',
                        'left': '10mm'
                    }
                )
            else:
                # Force "export mode" layout - remove ALL viewport-locked constraints
                await page.add_style_tag(content="""
                    /* ===== EXPORT MODE: FORCE FULL CONTENT HEIGHT ===== */
                    html, body {
                        height: auto !important;
                        min-height: auto !important;
                        overflow: visible !important;
                    }
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
                    .dashboard-root::after,
                    .content-area::after {
                        display: none !important;
                        content: none !important;
                    }
                    ::-webkit-scrollbar {
                        display: none !important;
                    }
                """)
                print('Applied export mode layout (forced full content height)')

                await page.wait_for_timeout(500)

                # Debug: Verify content height
                content_height = await page.evaluate("""
                    () => {
                        const contentArea = document.querySelector('.content-area');
                        return contentArea ? contentArea.scrollHeight : null;
                    }
                """)
                print(f'Content scrollHeight after export mode: {content_height}')

                # Capture the content container
                try:
                    content_element = await page.query_selector('.content-area')
                    if not content_element:
                        print('.content-area not found, trying #react-root')
                        content_element = await page.query_selector('#react-root')

                    if not content_element:
                        raise Exception('Active content container (.content-area or #react-root) not found')

                    print('Capturing content element (content-only screenshot)')
                    await content_element.screenshot(path=output_path)
                    print('Screenshot captured successfully')
                except Exception as error:
                    print(f'Error capturing content element: {error}')
                    print('Falling back to full page screenshot')
                    await page.screenshot(path=output_path, full_page=True)

            await browser.close()
            print(f'Successfully captured dashboard to {output_path}')
            sys.exit(0)

    except Exception as error:
        print(f'Error capturing dashboard: {error}')
        if browser:
            await browser.close()
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(capture_dashboard())

