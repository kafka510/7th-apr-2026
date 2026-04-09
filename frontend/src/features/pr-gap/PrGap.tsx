import { useState, useMemo, useEffect } from 'react';
import { useTheme } from '../../contexts/ThemeContext';
import { PrGapFilters } from './components/PrGapFilters';
import { PrGapCharts } from './components/PrGapCharts';
import { usePrGapData } from './hooks/usePrGapData';
import type { PrGapFilters as PrGapFiltersType } from './types';

export function PrGap() {
  const { theme } = useTheme();
  // Start with empty filters - will compute default after data loads
  const [userFilters, setUserFilters] = useState<PrGapFiltersType>({
    countries: [],
    portfolios: [],
  });
  
  // Theme-aware colors
  const bgGradient = theme === 'dark'
    ? 'linear-gradient(to bottom right, #0f172a, #1e293b, #0f172a)'
    : 'linear-gradient(to bottom right, #f8fbff, #ffffff, #f8fbff)';
  const textColor = theme === 'dark' ? '#f1f5f9' : '#1a1a1a';
  
  // First fetch with empty filters to get filterOptions, prData, and lossData
  const { filterOptions, prData, lossData, loading: optionsLoading, error: optionsError } = usePrGapData({
    countries: [],
    portfolios: [],
  });

  // Compute effective filters: use user filters if set, otherwise default to latest month
  const effectiveFilters = useMemo<PrGapFiltersType>(() => {
    // If user has set filters, use those
    if (userFilters.month || userFilters.year || userFilters.range || userFilters.countries.length > 0 || userFilters.portfolios.length > 0) {
      return userFilters;
    }
    
    // Otherwise, default to latest available month when data is loaded
    if (!optionsLoading && filterOptions.months.length > 0) {
      const latestMonth = filterOptions.months[filterOptions.months.length - 1];
      return { 
        month: latestMonth,
        countries: [],
        portfolios: [],
      };
    }
    
    // Return empty filters while loading
    return {
      countries: [],
      portfolios: [],
    };
  }, [userFilters, optionsLoading, filterOptions.months]);

  // Use effective filters for actual data fetching
  const { filteredData, loading, error: dataError } = usePrGapData(effectiveFilters);

  // Combine errors from both calls
  const error: Error | null = optionsError || dataError;

  // Ensure the component fills the viewport, especially in iframes
  useEffect(() => {
    const root = document.getElementById('react-root');
    if (root) {
      // Set explicit height for iframe compatibility
      const setHeight = () => {
        if (window.self !== window.top) {
          // In iframe - use parent's available height or viewport
          root.style.height = '100%';
          root.style.minHeight = '100vh';
        } else {
          // Standalone - use viewport height
          root.style.height = '100vh';
          root.style.minHeight = '100vh';
        }
      };
      
      setHeight();
      window.addEventListener('resize', setHeight);
      return () => window.removeEventListener('resize', setHeight);
    }
  }, []);

  const handleFiltersChange = (newFilters: PrGapFiltersType) => {
    setUserFilters(newFilters);
  };

  const handleReset = () => {
    setUserFilters({
      countries: [],
      portfolios: [],
    });
  };

  const handleAssetClick = (asset: string, month: string) => {
    // Asset click handler - can be enhanced with breakdown details modal
    console.log('Asset clicked:', asset, 'Month:', month);
    // TODO: Implement breakdown details modal when lossData is available
  };

  return (
    <div 
      className="flex w-full flex-col"
      style={{
        background: bgGradient,
        color: textColor,
        transition: 'background 0.3s ease, color 0.3s ease',
        minHeight: '100%',
      }}
    >
      <main className="flex flex-col gap-2 p-2">
        {/* Filter Bar */}
        <div className="flex shrink-0">
          <div className="min-w-0 flex-1">
            <PrGapFilters
              filters={effectiveFilters}
              options={filterOptions}
              loading={loading}
              onFiltersChange={handleFiltersChange}
              onReset={handleReset}
            />
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div 
            className="shrink-0 rounded-lg border p-2 text-xs shadow-lg"
            style={{
              borderColor: theme === 'dark' ? 'rgba(239, 68, 68, 0.5)' : 'rgba(220, 38, 38, 0.3)',
              background: theme === 'dark' 
                ? 'linear-gradient(to right, rgba(127, 29, 29, 0.3), rgba(153, 27, 27, 0.2))' 
                : 'linear-gradient(to right, rgba(254, 242, 242, 0.8), rgba(254, 226, 226, 0.6))',
              color: theme === 'dark' ? '#fca5a5' : '#991b1b',
              boxShadow: theme === 'dark' 
                ? '0 10px 15px -3px rgba(127, 29, 29, 0.3)' 
                : '0 10px 15px -3px rgba(220, 38, 38, 0.1)',
            }}
          >
            <div className="flex items-center gap-2">
              <svg className="size-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>Failed to load PR gap data: {error?.message || 'Unknown error'}</span>
            </div>
          </div>
        )}

        {/* Main Content - Charts */}
        {!loading && !error && filteredData.length > 0 && (
          <div className="flex min-h-0 flex-1">
            <PrGapCharts
              data={filteredData}
              selectedMonth={effectiveFilters.month}
              selectedYear={effectiveFilters.year}
              onAssetClick={handleAssetClick}
              prData={prData}
              lossData={lossData}
            />
          </div>
        )}

        {/* Loading State */}
        {(loading || optionsLoading) && (
          <div 
            className="flex flex-1 items-center justify-center rounded-xl border shadow-xl"
            style={{
              borderColor: theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(203, 213, 225, 0.8)',
              background: theme === 'dark'
                ? 'linear-gradient(to bottom right, rgba(30, 41, 59, 0.9), rgba(51, 65, 85, 0.6))'
                : 'linear-gradient(to bottom right, rgba(255, 255, 255, 0.95), rgba(248, 250, 252, 0.9))',
              boxShadow: theme === 'dark' 
                ? '0 20px 25px -5px rgba(0, 0, 0, 0.4)' 
                : '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
            }}
          >
            <div className="text-center">
              <div className="mb-3 flex justify-center">
                <svg 
                  className="size-12 animate-spin" 
                  fill="none" 
                  viewBox="0 0 24 24"
                  style={{ color: theme === 'dark' ? '#60a5fa' : '#0072ce' }}
                >
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
              </div>
              <h2 
                className="mb-2 text-lg font-semibold"
                style={{ color: textColor }}
              >
                Loading Data
              </h2>
              <p 
                className="text-sm"
                style={{ color: theme === 'dark' ? '#94a3b8' : '#64748b' }}
              >
                Please wait while we fetch the PR gap data...
              </p>
            </div>
          </div>
        )}

        {/* No Data Message */}
        {!loading && !error && filteredData.length === 0 && (
          <div 
            className="flex flex-1 items-center justify-center rounded-xl border shadow-xl"
            style={{
              borderColor: theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(203, 213, 225, 0.8)',
              background: theme === 'dark'
                ? 'linear-gradient(to bottom right, rgba(30, 41, 59, 0.9), rgba(51, 65, 85, 0.6))'
                : 'linear-gradient(to bottom right, rgba(255, 255, 255, 0.95), rgba(248, 250, 252, 0.9))',
              boxShadow: theme === 'dark' 
                ? '0 20px 25px -5px rgba(0, 0, 0, 0.4)' 
                : '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
            }}
          >
            <div className="text-center">
              <div className="mb-3 flex justify-center">
                <svg 
                  className="size-12" 
                  fill="none" 
                  viewBox="0 0 24 24" 
                  stroke="currentColor"
                  style={{ color: theme === 'dark' ? '#64748b' : '#94a3b8' }}
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <h2 
                className="mb-2 text-lg font-semibold"
                style={{ color: textColor }}
              >
                No Data Available
              </h2>
              <p 
                className="text-sm"
                style={{ color: theme === 'dark' ? '#94a3b8' : '#64748b' }}
              >
                No records found with the current filters. Try adjusting your filter selections.
              </p>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

// Helper function to get breakdown details
// TODO: Uncomment when implementing breakdown details modal
/*
function getBreakdownDetails(
  assetNo: string,
  month: string,
  lossData: Array<Record<string, unknown>>
): Array<Record<string, unknown>> {
  if (!lossData || lossData.length === 0) {
    return [];
  }

  // Convert month format if needed
  let searchMonth = month;
  if (month && month.includes('-')) {
    const [year, monthNum] = month.split('-');
    if (year && monthNum) {
      const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
      searchMonth = `${monthNames[parseInt(monthNum) - 1]}-${year.slice(-2)}`;
    }
  }

  const results = lossData.filter((row) => {
    const rowAsset = (row.asset_no || row.asset || 'Unknown') as string;
    const rowMonth = (row.month || row.l || 'Unknown') as string;

    const assetMatch =
      String(rowAsset).toLowerCase().includes(String(assetNo).toLowerCase()) ||
      String(assetNo).toLowerCase().includes(String(rowAsset).toLowerCase());

    const rowMonthStr = String(rowMonth).toLowerCase();
    const searchMonthStr = String(searchMonth).toLowerCase();

    let monthMatch = false;
    if (rowMonthStr === searchMonthStr) {
      monthMatch = true;
    } else if (rowMonthStr.includes('-') && searchMonthStr.includes('-')) {
      const rowParts = rowMonthStr.split('-');
      const searchParts = searchMonthStr.split('-');
      if (rowParts.length >= 2 && searchParts.length >= 2) {
        const rowMonthName = rowParts[1];
        const searchMonthName = searchParts[0];
        if (rowMonthName === searchMonthName) {
          monthMatch = true;
        }
      }
    }

    return assetMatch && monthMatch;
  });

  // Filter to only include those with generation loss data
  return results.filter((breakdown) => {
    const hasGenerationLoss =
      (breakdown['generation_loss_kwh'] !== null && breakdown['generation_loss_kwh'] !== undefined) ||
      (breakdown['generation_loss_(kwh)'] !== null && breakdown['generation_loss_(kwh)'] !== undefined);
    return hasGenerationLoss;
  });
}

// Helper function to create detailed tooltip
function createDetailedTooltip(
  assetNo: string,
  month: string,
  breakdowns: Array<Record<string, unknown>>
): string {
  if (breakdowns.length === 0) {
    return `No breakdown data available for asset ${assetNo} in ${month}`;
  }

  let tooltipContent = `
    <div style="padding: 15px; max-width: 900px;">
      <h3 style="margin: 0 0 10px 0;">Breakdown Details</h3>
      <p><b>Asset:</b> ${assetNo}</p>
      <p><b>Month:</b> ${month}</p>
      <p><b>Total Instances:</b> ${breakdowns.length}</p>
      <table style="width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 10px;">
        <thead>
          <tr style="background: #0072CE; color: white;">
            <th style="padding: 10px; border: 1px solid #ddd;">#</th>
            <th style="padding: 10px; border: 1px solid #ddd;">DC Capacity</th>
            <th style="padding: 10px; border: 1px solid #ddd;">BD Description</th>
            <th style="padding: 10px; border: 1px solid #ddd;">Action</th>
            <th style="padding: 10px; border: 1px solid #ddd;">Status</th>
            <th style="padding: 10px; border: 1px solid #ddd;">Gen Loss (kWh)</th>
          </tr>
        </thead>
        <tbody>
  `;

  breakdowns.forEach((breakdown, index) => {
    const dcCapacity =
      breakdown['breakdown_dc_capacity_(kw)'] ||
      breakdown['breakdown_dc_capacity_kw'] ||
      breakdown['breakdown_dc_capacity'] ||
      breakdown['dc_capacity'] ||
      'N/A';
    const bdDescription = (breakdown['bd_description'] || 'N/A') as string;
    const actionToBeTaken = (breakdown['action_to_be_taken'] || 'N/A') as string;
    const bdStatus = (breakdown['status_of_bd'] || 'N/A') as string;
    let generationLoss = 'N/A';
    if (breakdown['generation_loss_kwh'] !== null && breakdown['generation_loss_kwh'] !== undefined) {
      generationLoss = String(breakdown['generation_loss_kwh']);
    } else if (breakdown['generation_loss_(kwh)'] !== null && breakdown['generation_loss_(kwh)'] !== undefined) {
      generationLoss = String(breakdown['generation_loss_(kwh)']);
    }

    tooltipContent += `
      <tr style="background: ${index % 2 === 0 ? '#f8f9fa' : 'white'};">
        <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">${index + 1}</td>
        <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">${dcCapacity}</td>
        <td style="padding: 8px; border: 1px solid #ddd;">${bdDescription.substring(0, 80)}${bdDescription.length > 80 ? '...' : ''}</td>
        <td style="padding: 8px; border: 1px solid #ddd;">${actionToBeTaken.substring(0, 70)}${actionToBeTaken.length > 70 ? '...' : ''}</td>
        <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">${bdStatus}</td>
        <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">${generationLoss}</td>
      </tr>
    `;
  });

  tooltipContent += `
        </tbody>
      </table>
    </div>
  `;

  return tooltipContent;
}
*/

