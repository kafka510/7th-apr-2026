/**
 * PV Modules Tab Component
 * 
 * Main tab for managing PV module datasheets and device configurations
 * Integrated into the Site Onboarding page
 */
import React, { useState } from 'react';
import { PVModulesList } from './PVModulesList';
import { DevicePVConfigTable } from './DevicePVConfigTable';
import { useTheme } from '../../../contexts/ThemeContext';

export const PVModulesTab: React.FC = () => {
  const { theme } = useTheme();
  const [activeSection, setActiveSection] = useState<'modules' | 'devices'>('modules');
  const [selectedAsset, setSelectedAsset] = useState<string>('');
  const [refreshKey, setRefreshKey] = useState(0);

  const handleRefresh = () => {
    setRefreshKey(prev => prev + 1);
  };

  // Theme-aware colors
  const bgColor = theme === 'dark' ? 'rgba(30, 41, 59, 0.5)' : '#ffffff';
  const textColor = theme === 'dark' ? '#f1f5f9' : '#1a1a1a';
  const borderColor = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : '#dee2e6';
  const sectionBg = theme === 'dark' ? 'rgba(15, 23, 42, 0.8)' : '#f8f9fa';
  const dividerBorder = theme === 'dark' ? 'rgba(51, 65, 85, 0.7)' : '#e5e7eb';

  return (
    <div className="p-5" style={{ backgroundColor: bgColor }}>
      <div className="mb-8 rounded border p-4" style={{ backgroundColor: sectionBg, borderColor: borderColor }}>
        <h2 className="fw-bold mb-2 text-2xl" style={{ color: textColor }}>☀️ PV Module Configuration</h2>
        <p className="mb-0" style={{ color: textColor }}>
          Manage PV module datasheets and configure string devices for accurate loss calculations
        </p>
      </div>

      {/* Section Selector */}
      <div className="mb-6 pb-4" style={{ borderBottom: `2px solid ${dividerBorder}` }}>
        <div className="btn-group" role="group">
          <button
            type="button"
            className={`rounded-l-md border px-6 py-2 ${activeSection === 'modules' ? 'btn-primary text-white' : 'btn-outline-secondary'}`}
            onClick={() => setActiveSection('modules')}
          >
            📚 Module Library
          </button>
          <button
            type="button"
            className={`rounded-r-md border-y border-r px-6 py-2 ${activeSection === 'devices' ? 'btn-primary text-white' : 'btn-outline-secondary'}`}
            onClick={() => setActiveSection('devices')}
          >
            ⚙️ Device Configuration
          </button>
        </div>
      </div>

      {/* Content Sections */}
      {activeSection === 'modules' && (
        <div className="module-library-section">
          <div className="border-start border-primary mb-4 rounded border-4 p-4" style={{ backgroundColor: sectionBg, borderColor: borderColor }}>
            <h4 className="fw-semibold mb-2 text-lg" style={{ color: textColor }}>📚 Module Datasheet Library</h4>
            <p className="mb-0 text-sm" style={{ color: textColor }}>
              Manage your library of PV module specifications. Each module type is stored once
              and can be reused across multiple sites and devices.
            </p>
          </div>
          <PVModulesList key={`modules-${refreshKey}`} onModuleChange={handleRefresh} />
        </div>
      )}

      {activeSection === 'devices' && (
        <div className="device-config-section">
          <div className="border-start border-primary mb-4 rounded border-4 p-4" style={{ backgroundColor: sectionBg, borderColor: borderColor }}>
            <h4 className="fw-semibold mb-2 text-lg" style={{ color: textColor }}>⚙️ Device PV Configuration</h4>
            <p className="mb-0 text-sm" style={{ color: textColor }}>
              Assign PV modules to string devices and configure installation-specific parameters
              (tilt, azimuth, soiling, shading, etc.).
            </p>
          </div>
          <DevicePVConfigTable
            key={`devices-${refreshKey}`}
            selectedAsset={selectedAsset}
            onAssetChange={setSelectedAsset}
            onConfigChange={handleRefresh}
          />
        </div>
      )}
    </div>
  );
};

