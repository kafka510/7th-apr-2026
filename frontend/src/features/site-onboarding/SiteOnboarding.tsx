 
import { useEffect, useState } from 'react';
import { AssetListTab } from './components/AssetListTab';
import { DeviceListTab } from './components/DeviceListTab';
import { DeviceMappingTab } from './components/DeviceMappingTab';
import { BudgetValuesTab } from './components/BudgetValuesTab';
import { ICBudgetTab } from './components/ICBudgetTab';
import { PVModulesTab } from './components/PVModulesTab';
import { SpareManagementTab } from './components/SpareManagementTab';
import { DataCollectionTab } from './components/DataCollectionTab';
import { DeviceStateMappingTab } from './components/DeviceStateMappingTab';
import { AssetContractsTab } from './components/AssetContractsTab';
import { AlertContainer } from './components/AlertContainer';
import { useTheme } from '../../contexts/ThemeContext';
import { getGradientBg } from '../../utils/themeColors';
import { useFilterPersistence } from '../../hooks/useFilterPersistence';
import { loadFilters } from '../../utils/filterPersistence';

type Tab =
  | 'asset-list'
  | 'device-list'
  | 'device-mapping'
  | 'pv-modules'
  | 'budget-values'
  | 'ic-budget'
  | 'data-collection'
  | 'device-state-mapping'
  | 'asset-contracts'
  | 'spare-management';

export function SiteOnboarding() {
  const { theme } = useTheme();

  const [activeTab, setActiveTab] = useState<Tab>(() => {
    const stored = loadFilters<{ activeTab?: Tab }>('site-onboarding');
    if (stored && typeof stored === 'object' && stored.activeTab) {
      return stored.activeTab;
    }
    return 'asset-list';
  });
  const [alerts, setAlerts] = useState<Array<{ id: string; type: 'success' | 'danger' | 'warning' | 'info'; message: string }>>([]);

  // Only show header when page is NOT in iframe
  const showHeader = typeof window !== 'undefined' && window.self === window.top;

  const removeAlert = (id: string) => {
    setAlerts((prev) => prev.filter((alert) => alert.id !== id));
  };

  // Theme-aware colors
  const bgGradient = getGradientBg(theme);
  const textPrimary = theme === 'dark' ? '#f1f5f9' : '#1a1a1a';
  const buttonBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.5)' : 'rgba(255, 255, 255, 0.9)';
  const buttonBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : 'rgba(203, 213, 225, 0.8)';
  const buttonText = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';
  const buttonHoverBorder = theme === 'dark' ? '#38bdf8' : '#0072ce';
  const buttonHoverBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.8)' : 'rgba(248, 250, 252, 0.9)';
  const badgeBg = theme === 'dark' ? 'rgba(220, 38, 38, 0.3)' : 'rgba(220, 38, 38, 0.1)';
  const badgeText = theme === 'dark' ? '#fca5a5' : '#dc2626';
  const tabBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.5)' : 'rgba(255, 255, 255, 0.9)';
  const tabBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.8)' : 'rgba(203, 213, 225, 0.8)';
  const tabActiveBg = theme === 'dark' ? 'rgba(56, 189, 248, 0.3)' : 'rgba(59, 130, 246, 0.15)';
  const tabActiveText = theme === 'dark' ? '#7dd3fc' : '#1e40af';
  const tabInactiveText = theme === 'dark' ? '#94a3b8' : '#64748b';
  const tabHoverBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.5)' : 'rgba(248, 250, 252, 0.9)';
  const tabHoverText = theme === 'dark' ? '#e2e8f0' : '#1a1a1a';

  // Persist active tab globally for Playwright export/download
  useFilterPersistence('site-onboarding', { activeTab });

  // Consider Site Onboarding ready when rendered (no async data gating at top level)
  useEffect(() => {
    document.body.setAttribute('data-filters-ready', 'true');
    window.dispatchEvent(
      new CustomEvent('dashboard-filters-ready', { detail: { dashboardId: 'site-onboarding' } }),
    );

    return () => {
      document.body.removeAttribute('data-filters-ready');
    };
  }, []);

  return (
    <div 
      className="flex w-full flex-col"
      style={{ background: bgGradient, minHeight: '100%' }}
    >
      <style>{`
        /* Theme-aware Bootstrap component styling */
        .card-header h5, .card-header h6 {
          color: ${textPrimary} !important;
        }
        .card-body, .card-body p, .card-body li, .card-body td, .card-body th, .card-body small, .card-body span {
          color: ${textPrimary} !important;
        }
        .card-body h1, .card-body h2, .card-body h3, .card-body h4, .card-body h5, .card-body h6 {
          color: ${textPrimary} !important;
        }
        .list-group-item h6, .list-group-item small {
          color: ${textPrimary} !important;
        }
        .table th, .table td {
          color: ${textPrimary} !important;
        }
        .modal-title, .form-label {
          color: ${textPrimary} !important;
        }
        .alert strong, .alert span, .alert p, .alert ul, .alert li {
          color: ${textPrimary} !important;
        }
      `}</style>
      <div className="flex h-full flex-col gap-2 overflow-auto p-2">
        {/* Header - only show when not in iframe */}
        {showHeader && (
          <div className="mb-2 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <h2 className="text-xl font-bold" style={{ color: textPrimary }}>🏗️ Site Onboarding Management</h2>
              <span 
                className="rounded-lg px-2 py-1 text-[10px] font-semibold uppercase"
                style={{
                  backgroundColor: badgeBg,
                  color: badgeText,
                }}
              >
                Admin Only
              </span>
              <a
                href="/operations-dashboard/"
                className="rounded-lg border px-3 py-1.5 text-xs font-semibold transition"
                style={{
                  borderColor: buttonBorder,
                  backgroundColor: buttonBg,
                  color: buttonText,
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = buttonHoverBorder;
                  e.currentTarget.style.backgroundColor = buttonHoverBg;
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = buttonBorder;
                  e.currentTarget.style.backgroundColor = buttonBg;
                }}
                title="Back to Main Dashboard"
              >
                🏠 Dashboard
              </a>
              <a
                href="/site-onboarding/wizard/"
                className="rounded-lg border px-3 py-1.5 text-xs font-semibold transition"
                style={{
                  borderColor: buttonBorder,
                  backgroundColor: buttonBg,
                  color: buttonText,
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = buttonHoverBorder;
                  e.currentTarget.style.backgroundColor = buttonHoverBg;
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = buttonBorder;
                  e.currentTarget.style.backgroundColor = buttonBg;
                }}
                title="Single-site onboarding wizard"
              >
                ✨ Single-site wizard
              </a>
            </div>
            <div>
              <button
                className="rounded-lg border px-3 py-1.5 text-xs font-semibold transition"
                style={{
                  borderColor: buttonBorder,
                  backgroundColor: buttonBg,
                  color: buttonText,
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = buttonHoverBorder;
                  e.currentTarget.style.backgroundColor = buttonHoverBg;
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = buttonBorder;
                  e.currentTarget.style.backgroundColor = buttonBg;
                }}
                onClick={() => window.open('/data-upload-help/', '_blank')}
              >
                📋 Help & Guidelines
              </button>
            </div>
          </div>
        )}

        {/* When in iframe (no header): show wizard link so users can reach it from Data Management */}
        {!showHeader && (
          <div className="mb-2 flex items-center gap-2">
            <a
              href="/site-onboarding/wizard/"
              className="rounded-lg border px-3 py-1.5 text-xs font-semibold transition"
              style={{
                borderColor: buttonBorder,
                backgroundColor: buttonBg,
                color: buttonText,
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = buttonHoverBorder;
                e.currentTarget.style.backgroundColor = buttonHoverBg;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = buttonBorder;
                e.currentTarget.style.backgroundColor = buttonBg;
              }}
              title="Single-site onboarding wizard"
            >
              ✨ Single-site wizard
            </a>
          </div>
        )}

        {/* Alert Container */}
        <AlertContainer alerts={alerts} onRemove={removeAlert} />

        {/* Tab Navigation */}
        <div 
          className="flex gap-1 rounded-xl border p-1"
          style={{
            borderColor: tabBorder,
            backgroundColor: tabBg,
          }}
        >
          <button
            className="flex-1 rounded-lg px-3 py-2 text-xs font-semibold transition"
            style={{
              backgroundColor: activeTab === 'asset-list' ? tabActiveBg : 'transparent',
              color: activeTab === 'asset-list' ? tabActiveText : tabInactiveText,
              boxShadow: activeTab === 'asset-list' ? '0 4px 6px -1px rgba(0, 0, 0, 0.1)' : 'none',
            }}
            onClick={() => setActiveTab('asset-list')}
            onMouseEnter={(e) => {
              if (activeTab !== 'asset-list') {
                e.currentTarget.style.backgroundColor = tabHoverBg;
                e.currentTarget.style.color = tabHoverText;
              }
            }}
            onMouseLeave={(e) => {
              if (activeTab !== 'asset-list') {
                e.currentTarget.style.backgroundColor = 'transparent';
                e.currentTarget.style.color = tabInactiveText;
              }
            }}
            type="button"
          >
            🏢 Asset List
          </button>
          <button
            className="flex-1 rounded-lg px-3 py-2 text-xs font-semibold transition"
            style={{
              backgroundColor: activeTab === 'device-list' ? tabActiveBg : 'transparent',
              color: activeTab === 'device-list' ? tabActiveText : tabInactiveText,
              boxShadow: activeTab === 'device-list' ? '0 4px 6px -1px rgba(0, 0, 0, 0.1)' : 'none',
            }}
            onClick={() => setActiveTab('device-list')}
            onMouseEnter={(e) => {
              if (activeTab !== 'device-list') {
                e.currentTarget.style.backgroundColor = tabHoverBg;
                e.currentTarget.style.color = tabHoverText;
              }
            }}
            onMouseLeave={(e) => {
              if (activeTab !== 'device-list') {
                e.currentTarget.style.backgroundColor = 'transparent';
                e.currentTarget.style.color = tabInactiveText;
              }
            }}
            type="button"
          >
            📱 Device List
          </button>
          <button
            className="flex-1 rounded-lg px-3 py-2 text-xs font-semibold transition"
            style={{
              backgroundColor: activeTab === 'device-mapping' ? tabActiveBg : 'transparent',
              color: activeTab === 'device-mapping' ? tabActiveText : tabInactiveText,
              boxShadow: activeTab === 'device-mapping' ? '0 4px 6px -1px rgba(0, 0, 0, 0.1)' : 'none',
            }}
            onClick={() => setActiveTab('device-mapping')}
            onMouseEnter={(e) => {
              if (activeTab !== 'device-mapping') {
                e.currentTarget.style.backgroundColor = tabHoverBg;
                e.currentTarget.style.color = tabHoverText;
              }
            }}
            onMouseLeave={(e) => {
              if (activeTab !== 'device-mapping') {
                e.currentTarget.style.backgroundColor = 'transparent';
                e.currentTarget.style.color = tabInactiveText;
              }
            }}
            type="button"
          >
            🔗 Device Mapping
          </button>
          <button
            className="flex-1 rounded-lg px-3 py-2 text-xs font-semibold transition"
            style={{
              backgroundColor: activeTab === 'budget-values' ? tabActiveBg : 'transparent',
              color: activeTab === 'budget-values' ? tabActiveText : tabInactiveText,
              boxShadow: activeTab === 'budget-values' ? '0 4px 6px -1px rgba(0, 0, 0, 0.1)' : 'none',
            }}
            onClick={() => setActiveTab('budget-values')}
            onMouseEnter={(e) => {
              if (activeTab !== 'budget-values') {
                e.currentTarget.style.backgroundColor = tabHoverBg;
                e.currentTarget.style.color = tabHoverText;
              }
            }}
            onMouseLeave={(e) => {
              if (activeTab !== 'budget-values') {
                e.currentTarget.style.backgroundColor = 'transparent';
                e.currentTarget.style.color = tabInactiveText;
              }
            }}
            type="button"
          >
            💰 Budget Values
          </button>
          <button
            className="flex-1 rounded-lg px-3 py-2 text-xs font-semibold transition"
            style={{
              backgroundColor: activeTab === 'pv-modules' ? tabActiveBg : 'transparent',
              color: activeTab === 'pv-modules' ? tabActiveText : tabInactiveText,
              boxShadow: activeTab === 'pv-modules' ? '0 4px 6px -1px rgba(0, 0, 0, 0.1)' : 'none',
            }}
            onClick={() => setActiveTab('pv-modules')}
            onMouseEnter={(e) => {
              if (activeTab !== 'pv-modules') {
                e.currentTarget.style.backgroundColor = tabHoverBg;
                e.currentTarget.style.color = tabHoverText;
              }
            }}
            onMouseLeave={(e) => {
              if (activeTab !== 'pv-modules') {
                e.currentTarget.style.backgroundColor = 'transparent';
                e.currentTarget.style.color = tabInactiveText;
              }
            }}
            type="button"
          >
            🔆 PV Modules
          </button>
          <button
            className="flex-1 rounded-lg px-3 py-2 text-xs font-semibold transition"
            style={{
              backgroundColor: activeTab === 'ic-budget' ? tabActiveBg : 'transparent',
              color: activeTab === 'ic-budget' ? tabActiveText : tabInactiveText,
              boxShadow: activeTab === 'ic-budget' ? '0 4px 6px -1px rgba(0, 0, 0, 0.1)' : 'none',
            }}
            onClick={() => setActiveTab('ic-budget')}
            onMouseEnter={(e) => {
              if (activeTab !== 'ic-budget') {
                e.currentTarget.style.backgroundColor = tabHoverBg;
                e.currentTarget.style.color = tabHoverText;
              }
            }}
            onMouseLeave={(e) => {
              if (activeTab !== 'ic-budget') {
                e.currentTarget.style.backgroundColor = 'transparent';
                e.currentTarget.style.color = tabInactiveText;
              }
            }}
            type="button"
          >
            📊 IC Budget
          </button>
          <button
            className="flex-1 rounded-lg px-3 py-2 text-xs font-semibold transition"
            style={{
              backgroundColor: activeTab === 'data-collection' ? tabActiveBg : 'transparent',
              color: activeTab === 'data-collection' ? tabActiveText : tabInactiveText,
              boxShadow: activeTab === 'data-collection' ? '0 4px 6px -1px rgba(0, 0, 0, 0.1)' : 'none',
            }}
            onClick={() => setActiveTab('data-collection')}
            onMouseEnter={(e) => {
              if (activeTab !== 'data-collection') {
                e.currentTarget.style.backgroundColor = tabHoverBg;
                e.currentTarget.style.color = tabHoverText;
              }
            }}
            onMouseLeave={(e) => {
              if (activeTab !== 'data-collection') {
                e.currentTarget.style.backgroundColor = 'transparent';
                e.currentTarget.style.color = tabInactiveText;
              }
            }}
            type="button"
          >
            📡 Data Collection
          </button>
          <button
            className="flex-1 rounded-lg px-3 py-2 text-xs font-semibold transition"
            style={{
              backgroundColor: activeTab === 'device-state-mapping' ? tabActiveBg : 'transparent',
              color: activeTab === 'device-state-mapping' ? tabActiveText : tabInactiveText,
              boxShadow: activeTab === 'device-state-mapping' ? '0 4px 6px -1px rgba(0, 0, 0, 0.1)' : 'none',
            }}
            onClick={() => setActiveTab('device-state-mapping')}
            onMouseEnter={(e) => {
              if (activeTab !== 'device-state-mapping') {
                e.currentTarget.style.backgroundColor = tabHoverBg;
                e.currentTarget.style.color = tabHoverText;
              }
            }}
            onMouseLeave={(e) => {
              if (activeTab !== 'device-state-mapping') {
                e.currentTarget.style.backgroundColor = 'transparent';
                e.currentTarget.style.color = tabInactiveText;
              }
            }}
            type="button"
          >
            ⚙️ Device State Mapping
          </button>
          <button
            className="flex-1 rounded-lg px-3 py-2 text-xs font-semibold transition"
            style={{
              backgroundColor: activeTab === 'asset-contracts' ? tabActiveBg : 'transparent',
              color: activeTab === 'asset-contracts' ? tabActiveText : tabInactiveText,
              boxShadow: activeTab === 'asset-contracts' ? '0 4px 6px -1px rgba(0, 0, 0, 0.1)' : 'none',
            }}
            onClick={() => setActiveTab('asset-contracts')}
            onMouseEnter={(e) => {
              if (activeTab !== 'asset-contracts') {
                e.currentTarget.style.backgroundColor = tabHoverBg;
                e.currentTarget.style.color = tabHoverText;
              }
            }}
            onMouseLeave={(e) => {
              if (activeTab !== 'asset-contracts') {
                e.currentTarget.style.backgroundColor = 'transparent';
                e.currentTarget.style.color = tabInactiveText;
              }
            }}
            type="button"
          >
            🧾 Asset Contracts
          </button>
          <button
            className="flex-1 rounded-lg px-3 py-2 text-xs font-semibold transition"
            style={{
              backgroundColor: activeTab === 'spare-management' ? tabActiveBg : 'transparent',
              color: activeTab === 'spare-management' ? tabActiveText : tabInactiveText,
              boxShadow: activeTab === 'spare-management' ? '0 4px 6px -1px rgba(0, 0, 0, 0.1)' : 'none',
            }}
            onClick={() => setActiveTab('spare-management')}
            onMouseEnter={(e) => {
              if (activeTab !== 'spare-management') {
                e.currentTarget.style.backgroundColor = tabHoverBg;
                e.currentTarget.style.color = tabHoverText;
              }
            }}
            onMouseLeave={(e) => {
              if (activeTab !== 'spare-management') {
                e.currentTarget.style.backgroundColor = 'transparent';
                e.currentTarget.style.color = tabInactiveText;
              }
            }}
            type="button"
          >
            🔧 Spare Management
          </button>
        </div>

        {/* Tab Content */}
        <div className="flex-1 overflow-auto">
          {activeTab === 'asset-list' && <AssetListTab />}
          {activeTab === 'device-list' && <DeviceListTab />}
          {activeTab === 'device-mapping' && <DeviceMappingTab />}
          {activeTab === 'pv-modules' && <PVModulesTab />}
          {activeTab === 'budget-values' && <BudgetValuesTab />}
          {activeTab === 'ic-budget' && <ICBudgetTab />}
          {activeTab === 'data-collection' && <DataCollectionTab />}
          {activeTab === 'device-state-mapping' && <DeviceStateMappingTab />}
          {activeTab === 'asset-contracts' && <AssetContractsTab />}
          {activeTab === 'spare-management' && <SpareManagementTab />}
        </div>
      </div>
    </div>
  );
}

