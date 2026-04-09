import { useState, useRef, useEffect } from 'react';
import { useTheme } from '../contexts/ThemeContext';

interface SettingsDropdownProps {
  username: string;
  userRole: string | null;
  logoutUrl: string;
}

export function SettingsDropdown({ username, userRole, logoutUrl }: SettingsDropdownProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [showContact, setShowContact] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const { theme, toggleTheme } = useTheme();

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
        setShowContact(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  const navigateWithIframeSupport = (url: string) => {
    // If inside an iframe, ask parent window to navigate
    if (window.self !== window.top) {
      try {
        window.parent.postMessage(
          {
            type: 'navigate_request',
            url,
            from: 'settings_dropdown',
          },
          '*',
        );
        return;
      } catch {
        // Fall through to direct navigation
      }
    }

    // Direct navigation if not in iframe or postMessage fails
    window.location.href = url;
  };

  const handleLogout = () => {
    navigateWithIframeSupport(logoutUrl);
  };

  const handleChangePassword = () => {
    // Use existing Django password reset/change flow
    navigateWithIframeSupport('/accounts/password-reset/');
    setIsOpen(false);
    setShowContact(false);
  };

  const displayRole = userRole 
    ? userRole.charAt(0).toUpperCase() + userRole.slice(1).replace(/_/g, ' ')
    : 'User';

  // Theme-aware styles - icon color should match header text color
  const isDark = theme === 'dark';
  // Icon color should match the header text color (light for dark theme, dark for light theme)
  const iconColor = isDark ? '#e2e8f0' : '#1a1a1a';
  // Dropdown menu colors respect theme
  const bgColor = isDark ? 'rgba(30, 41, 59, 0.98)' : 'rgba(255, 255, 255, 0.98)';
  const textColor = isDark ? '#e2e8f0' : '#1a1a1a';
  const borderColor = isDark ? 'rgba(51, 65, 85, 0.6)' : 'rgba(226, 232, 240, 0.9)';
  const hoverBg = isDark ? 'rgba(51, 65, 85, 0.9)' : 'rgba(241, 245, 249, 0.95)';

  return (
    <div ref={dropdownRef} style={{ position: 'relative', display: 'inline-block', zIndex: 1000 }}>
      {/* Settings Icon Button */}
      <button
        onClick={() => {
          setIsOpen(!isOpen);
          // When reopening dropdown, keep contact section collapsed by default
          if (isOpen) {
            setShowContact(false);
          }
        }}
        type="button"
        aria-label="Settings"
        aria-expanded={isOpen}
        style={{
          background: 'transparent',
          border: 'none',
          cursor: 'pointer',
          padding: '8px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          borderRadius: '6px',
          transition: 'background-color 0.2s',
          color: iconColor,
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.backgroundColor = isDark ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.05)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.backgroundColor = 'transparent';
        }}
      >
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
          <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
          <circle cx="12" cy="12" r="3" />
        </svg>
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div
          style={{
            position: 'absolute',
            top: '100%',
            right: 0,
            marginTop: '8px',
            minWidth: '220px',
            backgroundColor: bgColor,
            border: `1px solid ${borderColor}`,
            borderRadius: '8px',
            boxShadow: isDark 
              ? '0 10px 25px rgba(0, 0, 0, 0.5)' 
              : '0 10px 25px rgba(0, 0, 0, 0.15)',
            zIndex: 1000,
            overflow: 'hidden',
            color: textColor,
          }}
        >
          {/* User Info Section */}
          <div
            style={{
              padding: '16px',
              borderBottom: `1px solid ${borderColor}`,
            }}
          >
            <div
              style={{
                fontSize: '14px',
                fontWeight: 600,
                color: textColor,
                marginBottom: '4px',
              }}
            >
              {username}
            </div>
            <div
              style={{
                fontSize: '12px',
                color: isDark ? '#94a3b8' : '#64748b',
              }}
            >
              {displayRole}
            </div>
          </div>

          {/* Theme Toggle */}
          <button
            onClick={() => {
              toggleTheme();
              setIsOpen(false);
            }}
            type="button"
            style={{
              width: '100%',
              padding: '12px 16px',
              background: 'transparent',
              border: 'none',
              borderBottom: `1px solid ${borderColor}`,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              color: textColor,
              fontSize: '14px',
              transition: 'background-color 0.2s',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = hoverBg;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = 'transparent';
            }}
          >
            <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              {theme === 'light' ? (
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
                </svg>
              ) : (
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <circle cx="12" cy="12" r="5" />
                  <line x1="12" y1="1" x2="12" y2="3" />
                  <line x1="12" y1="21" x2="12" y2="23" />
                  <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
                  <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
                  <line x1="1" y1="12" x2="3" y2="12" />
                  <line x1="21" y1="12" x2="23" y2="12" />
                  <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
                  <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
                </svg>
              )}
              {theme === 'light' ? 'Dark Mode' : 'Light Mode'}
            </span>
          </button>

          {/* Contact Option */}
          <button
            type="button"
            onClick={() => setShowContact((prev) => !prev)}
            style={{
              width: '100%',
              padding: '10px 16px',
              background: 'transparent',
              border: 'none',
              borderBottom: `1px solid ${borderColor}`,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              color: textColor,
              fontSize: '14px',
              transition: 'background-color 0.2s',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = hoverBg;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = 'transparent';
            }}
          >
            <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              {/* Simple mail icon */}
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <rect x="3" y="5" width="18" height="14" rx="2" ry="2" />
                <polyline points="3 7 12 13 21 7" />
              </svg>
              Contact
            </span>
            <span
              style={{
                fontSize: '12px',
                color: isDark ? '#94a3b8' : '#64748b',
              }}
            >
              {showContact ? 'Hide' : 'Show'}
            </span>
          </button>

          {showContact && (
            <div
              style={{
                padding: '8px 16px 10px 16px',
                borderBottom: `1px solid ${borderColor}`,
                backgroundColor: isDark ? 'rgba(15,23,42,0.9)' : '#f9fafb',
              }}
            >
              <p
                style={{
                  margin: 0,
                  marginBottom: '6px',
                  fontSize: '12px',
                  color: isDark ? '#cbd5e1' : '#475569',
                  fontWeight: 500,
                }}
              >
                For support, contact:
              </p>
              <div
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '4px',
                  fontSize: '12px',
                  wordBreak: 'break-all',
                }}
              >
                <a href="mailto:noreply@peakpulse-dev.xyz" style={{ color: isDark ? '#93c5fd' : '#1d4ed8', textDecoration: 'none' }}>
                  noreply@peakpulse-dev.xyz
                </a>
                <a href="mailto:Poovarasu.Manickam@peakenergy.asia" style={{ color: isDark ? '#93c5fd' : '#1d4ed8', textDecoration: 'none' }}>
                  Poovarasu.Manickam@peakenergy.asia
                </a>
                <a href="mailto:jagadeshwar@peakenergy.asia" style={{ color: isDark ? '#93c5fd' : '#1d4ed8', textDecoration: 'none' }}>
                  jagadeshwar@peakenergy.asia
                </a>
              </div>
            </div>
          )}

          {/* Change Password */}
          <button
            type="button"
            onClick={handleChangePassword}
            style={{
              width: '100%',
              padding: '12px 16px',
              background: 'transparent',
              border: 'none',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              color: textColor,
              fontSize: '14px',
              transition: 'background-color 0.2s',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = hoverBg;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = 'transparent';
            }}
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M12 11c1.1 0 2-.9 2-2V5a2 2 0 0 0-4 0v4c0 1.1.9 2 2 2z" />
              <rect x="6" y="11" width="12" height="9" rx="2" />
            </svg>
            Change password
          </button>

          {/* Logout Button */}
          <button
            onClick={handleLogout}
            type="button"
            style={{
              width: '100%',
              padding: '12px 16px',
              background: 'transparent',
              border: 'none',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              color: isDark ? '#f87171' : '#dc2626',
              fontSize: '14px',
              fontWeight: 500,
              transition: 'background-color 0.2s',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = hoverBg;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = 'transparent';
            }}
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
              <polyline points="16 17 21 12 16 7" />
              <line x1="21" y1="12" x2="9" y2="12" />
            </svg>
            Logout
          </button>
        </div>
      )}
    </div>
  );
}

