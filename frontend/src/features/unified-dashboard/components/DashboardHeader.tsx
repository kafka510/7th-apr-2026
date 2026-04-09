 
import type { UserInfo, DashboardMenu } from '../types';
import { DownloadImageButton } from '../../../components/DownloadImageButton';
import { SettingsDropdown } from '../../../components/SettingsDropdown';
import { useTheme } from '../../../contexts/ThemeContext';

interface DashboardHeaderProps {
  user: UserInfo;
  sidebarOpen: boolean;
  onToggleSidebar: () => void;
  activeTab: string | null;
  menu: DashboardMenu;
}

export function DashboardHeader({
  user,
  sidebarOpen,
  onToggleSidebar,
  activeTab,
  menu,
}: DashboardHeaderProps) {
  const { theme } = useTheme();
  
  const getPageTitle = () => {
    if (!activeTab) return '';
    
    for (const section of menu.sections) {
      if (section.type === 'single') {
        const item = section.items.find(item => item.tabId === activeTab);
        if (item) return item.label;
      }
      if (section.type === 'group') {
        const item = section.group.items.find(item => item.tabId === activeTab);
        if (item) return item.label;
      }
    }
    return '';
  };



  // Theme-aware colors for header
  const headerBg = theme === 'dark' 
    ? 'rgba(2, 22, 43, 0.92)' 
    : 'rgba(255, 255, 255, 0.95)';
  const headerText = theme === 'dark' ? '#ffffff' : '#1a1a1a';
  const headerShadow = theme === 'dark' 
    ? '0 2px 8px rgba(0,0,0,0.3)' 
    : '0 2px 8px rgba(0,0,0,0.1)';
  const buttonText = theme === 'dark' ? '#ffffff' : '#1a1a1a';

  return (
    <header
      className="topbar"
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        height: '50px',
        background: headerBg,
        color: headerText,
        zIndex: 1100,
        display: 'flex',
        alignItems: 'center',
        padding: '0 16px',
        boxShadow: headerShadow,
        width: '100%',
        maxWidth: '100vw',
        boxSizing: 'border-box',
        transition: 'background-color 0.3s ease, color 0.3s ease, box-shadow 0.3s ease',
        backdropFilter: 'blur(10px)',
      }}
    >
      <div style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <button
            onClick={onToggleSidebar}
            style={{
              background: 'transparent',
              color: buttonText,
              border: 'none',
              padding: '2px 6px',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '14px',
              transition: 'color 0.2s ease',
            }}
            title="Menu"
            aria-label="Toggle Sidebar"
            onMouseEnter={(e) => {
              e.currentTarget.style.color = '#0072ce';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.color = buttonText;
            }}
          >
            <span>{sidebarOpen ? '✕' : '☰'}</span>
          </button>
          <div>
            <img
              src="/static/PEAK_LOGO.jpg"
              alt="Peak Energy Logo"
              style={{ height: '32px', width: 'auto', borderRadius: '6px' }}
            />
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flex: '1', justifyContent: 'flex-end', minWidth: 0 }}>
          <div
            style={{
              position: 'absolute',
              left: '50%',
              top: '50%',
              transform: 'translate(-50%, -50%)',
              color: headerText,
              fontWeight: 700,
              fontSize: '14px',
              whiteSpace: 'nowrap',
              textOverflow: 'ellipsis',
              overflow: 'hidden',
              maxWidth: '60vw',
              textAlign: 'center',
              pointerEvents: 'none',
              transition: 'color 0.3s ease',
            }}
          >
            {getPageTitle()}
          </div>
          <DownloadImageButton />
          <SettingsDropdown
            username={user.username || user.full_name}
            userRole={user.role}
            logoutUrl="/accounts/logout/"
          />
        </div>
      </div>
    </header>
  );
}

