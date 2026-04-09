 
import { useState } from 'react';
import type { DashboardMenu, MenuSection } from '../types';
import { useTheme } from '../../../contexts/ThemeContext';

interface DashboardSidebarProps {
  menu: DashboardMenu;
  activeTab: string | null;
  onTabChange: (tabId: string) => void;
  sidebarOpen: boolean;
}

export function DashboardSidebar({
  menu,
  activeTab,
  onTabChange,
  sidebarOpen,
}: DashboardSidebarProps) {
  const { theme } = useTheme();
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());

  const toggleGroup = (groupId: string) => {
    setExpandedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(groupId)) {
        next.delete(groupId);
      } else {
        next.add(groupId);
      }
      return next;
    });
  };

  const handleItemClick = (item: { tabId?: string; url?: string; target?: string }) => {
    if (item.tabId) {
      onTabChange(item.tabId);
    } else if (item.url) {
      if (item.target === '_blank') {
        window.open(item.url, item.target, item.target === '_blank' ? 'noopener,noreferrer' : undefined);
      } else {
        // Use assign instead of direct href modification
        window.location.assign(item.url);
      }
    }
  };

  // Theme-aware colors for sidebar
  const sidebarBg = theme === 'dark'
    ? 'linear-gradient(180deg, #0d1b2a 0%, #1b263b 50%, #2c3e50 100%)'
    : 'linear-gradient(180deg, #f8fafc 0%, #ffffff 50%, #f1f5f9 100%)';
  const sidebarText = theme === 'dark' ? '#ffffff' : '#1a1a1a';
  const dividerColor = theme === 'dark' ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)';
  const sectionTitleColor = theme === 'dark' ? 'rgba(255,255,255,0.6)' : 'rgba(0,0,0,0.6)';
  const activeBg = theme === 'dark' ? 'rgba(0, 163, 255, 0.15)' : 'rgba(0, 114, 206, 0.1)';
  const activeBorder = '#0072ce';
  const hoverBg = theme === 'dark' ? 'rgba(255,255,255,0.05)' : 'rgba(0, 114, 206, 0.05)';

  const renderSection = (section: MenuSection, index: number) => {
    if (section.type === 'divider') {
      return (
        <div 
          key={`divider-${index}`} 
          style={{ 
            height: '1px', 
            background: dividerColor, 
            margin: '8px 0',
            transition: 'background-color 0.3s ease',
          }} 
        />
      );
    }

    if (section.type === 'sectionTitle') {
      return (
        <div
          key={`title-${index}`}
          style={{
            padding: '12px 16px 8px',
            fontSize: '12px',
            fontWeight: 600,
            color: sectionTitleColor,
            textTransform: 'uppercase',
            letterSpacing: '0.5px',
            transition: 'color 0.3s ease',
          }}
        >
          {section.sectionTitle}
        </div>
      );
    }

    if (section.type === 'single') {
      return (
        <div key={`single-${index}`}>
          {section.items.map((item) => {
            const isActive = activeTab === item.tabId;
            return (
              <a
                key={item.id}
                href={item.url || '#'}
                onClick={(e) => {
                  e.preventDefault();
                  handleItemClick(item);
                }}
                className={`sidebar-link ${isActive ? 'active' : ''}`}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                  padding: '10px 16px',
                  color: sidebarText,
                  textDecoration: 'none',
                  cursor: 'pointer',
                  background: isActive ? activeBg : 'transparent',
                  borderLeft: isActive ? `3px solid ${activeBorder}` : '3px solid transparent',
                  transition: 'background-color 0.2s ease, border-color 0.2s ease, color 0.2s ease',
                }}
                onMouseEnter={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.background = hoverBg;
                  }
                }}
                onMouseLeave={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.background = 'transparent';
                  }
                }}
              >
                <span>{item.icon}</span>
                <span>{item.label}</span>
              </a>
            );
          })}
        </div>
      );
    }

    if (section.type === 'group') {
      const isExpanded = expandedGroups.has(section.group.id);
      return (
        <div key={`group-${section.group.id}`}>
          <div
            onClick={() => toggleGroup(section.group.id)}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '10px 16px',
              color: sidebarText,
              cursor: 'pointer',
              fontWeight: 600,
              transition: 'color 0.2s ease, background-color 0.2s ease',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = hoverBg;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = 'transparent';
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span>{section.group.icon}</span>
              <span>{section.group.label}</span>
            </div>
            <span style={{ transform: isExpanded ? 'rotate(90deg)' : 'rotate(0deg)', transition: 'transform 0.2s' }}>
              ▶
            </span>
          </div>
          {isExpanded && (
            <div>
              {section.group.items.map((item) => {
                const isActive = activeTab === item.tabId;
                return (
                  <a
                    key={item.id}
                    href={item.url || '#'}
                    onClick={(e) => {
                      e.preventDefault();
                      handleItemClick(item);
                    }}
                    className={`sidebar-link ${isActive ? 'active' : ''}`}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '10px',
                      padding: '10px 16px 10px 40px',
                      color: sidebarText,
                      textDecoration: 'none',
                      cursor: 'pointer',
                      background: isActive ? activeBg : 'transparent',
                      borderLeft: isActive ? `3px solid ${activeBorder}` : '3px solid transparent',
                      transition: 'background-color 0.2s ease, border-color 0.2s ease, color 0.2s ease',
                    }}
                    onMouseEnter={(e) => {
                      if (!isActive) {
                        e.currentTarget.style.background = hoverBg;
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (!isActive) {
                        e.currentTarget.style.background = 'transparent';
                      }
                    }}
                  >
                    <span>{item.icon}</span>
                    <span>{item.label}</span>
                  </a>
                );
              })}
            </div>
          )}
        </div>
      );
    }

    return null;
  };

  return (
    <div
      className={`sidebar ${sidebarOpen ? 'open' : ''}`}
      style={{
        width: sidebarOpen ? '250px' : '0',
        minWidth: sidebarOpen ? '120px' : '0',
        maxWidth: '350px',
        background: sidebarBg,
        position: 'fixed',
        zIndex: 1000,
        height: 'calc(100vh - 50px)',
        overflow: 'auto',
        transition: 'width 0.3s ease-in-out, transform 0.3s ease-in-out, background 0.3s ease',
        transform: sidebarOpen ? 'translateX(0)' : 'translateX(-100%)',
        top: '50px',
        left: 0,
        boxShadow: sidebarOpen 
          ? (theme === 'dark' ? '2px 0 8px rgba(0,0,0,0.3)' : '2px 0 8px rgba(0,0,0,0.1)')
          : 'none',
      }}
    >
      {menu.sections.map((section, index) => renderSection(section, index))}
    </div>
  );
}

