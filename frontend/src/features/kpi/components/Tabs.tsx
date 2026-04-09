import type { ReactNode } from 'react';
import { useTheme } from '../../../contexts/ThemeContext';

type Tab = {
  id: string;
  label: string;
  content: ReactNode;
};

type TabsProps = {
  tabs: Tab[];
  activeTab: string;
  onTabChange: (tabId: string) => void;
};

export const Tabs = ({ tabs, activeTab, onTabChange }: TabsProps) => {
  const { theme } = useTheme();
  
  const tabNavBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.5)' : 'rgba(241, 245, 249, 0.8)';
  const tabNavBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.3)' : 'rgba(203, 213, 225, 0.5)';
  const inactiveTabBg = theme === 'dark' ? 'rgba(30, 41, 59, 0.5)' : 'rgba(241, 245, 249, 0.8)';
  const inactiveTabText = theme === 'dark' ? '#94a3b8' : '#64748b';
  const inactiveTabHoverBg = theme === 'dark' ? 'rgba(51, 65, 85, 0.5)' : 'rgba(226, 232, 240, 0.8)';
  const inactiveTabHoverText = theme === 'dark' ? '#e2e8f0' : '#334155';
  const tabContentBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.7)' : 'rgba(255, 255, 255, 0.95)';
  const tabContentBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.3)' : 'rgba(203, 213, 225, 0.5)';

  return (
    <div className="w-full">
      {/* Tab Navigation */}
      <div 
        className="flex overflow-hidden rounded-t-lg border"
        style={{
          borderColor: tabNavBorder,
          backgroundColor: tabNavBg,
        }}
      >
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            className={`flex-1 border-r px-2 py-1 text-xs font-semibold transition-all duration-300 last:border-r-0 ${
              activeTab === tab.id
                ? 'bg-gradient-to-r from-blue-600 to-emerald-600 text-white shadow-lg'
                : ''
            }`}
            style={
              activeTab !== tab.id
                ? {
                    borderRightColor: tabNavBorder,
                    backgroundColor: inactiveTabBg,
                    color: inactiveTabText,
                  }
                : {}
            }
            onMouseEnter={(e) => {
              if (activeTab !== tab.id) {
                e.currentTarget.style.backgroundColor = inactiveTabHoverBg;
                e.currentTarget.style.color = inactiveTabHoverText;
              }
            }}
            onMouseLeave={(e) => {
              if (activeTab !== tab.id) {
                e.currentTarget.style.backgroundColor = inactiveTabBg;
                e.currentTarget.style.color = inactiveTabText;
              }
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div 
        className="rounded-b-lg border border-t-0"
        style={{
          borderColor: tabContentBorder,
          backgroundColor: tabContentBg,
        }}
      >
        {tabs.map((tab) => (
          <div
            key={tab.id}
            className={activeTab === tab.id ? 'block opacity-100 transition-opacity duration-300' : 'hidden opacity-0'}
          >
            {tab.content}
          </div>
        ))}
      </div>
    </div>
  );
};

