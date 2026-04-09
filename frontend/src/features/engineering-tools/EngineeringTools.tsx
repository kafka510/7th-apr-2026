/**
 * Engineering Tools - React page component.
 * Hosts Solar Insight (with KMZ) and Solar Pre-Feasibility v1 (no KMZ).
 */
import { useState } from 'react';
import { MapPin, Calculator } from 'lucide-react';
import SolarInsightPage from './solar/SolarInsightPage';
import SolarPreFeasibilityPage from './solar/SolarPreFeasibilityPage';

type EngineeringToolTab = 'solar-insight' | 'solar-prefeasibility';

export function EngineeringTools() {
  const [activeTab, setActiveTab] = useState<EngineeringToolTab>('solar-insight');

  return (
    <div className="page-container">
      {/* Tab navigation — fully theme-aware via CSS custom properties */}
      <div
        className="flex items-center gap-1 px-4 py-3 border-b"
        style={{ borderColor: 'var(--border-color)', background: 'var(--card-bg)' }}
      >
        <button
          type="button"
          onClick={() => setActiveTab('solar-insight')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            activeTab === 'solar-insight'
              ? 'text-[var(--accent-primary)] bg-[var(--accent-primary)]/10'
              : 'text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)] hover:text-[var(--text-primary)]'
          }`}
        >
          <MapPin className="w-4 h-4" />
          Solar Insight (with KMZ)
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('solar-prefeasibility')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            activeTab === 'solar-prefeasibility'
              ? 'text-[var(--accent-primary)] bg-[var(--accent-primary)]/10'
              : 'text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)] hover:text-[var(--text-primary)]'
          }`}
        >
          <Calculator className="w-4 h-4" />
          Solar Pre-Feasibility v1
        </button>
      </div>

      {activeTab === 'solar-insight' && <SolarInsightPage />}
      {activeTab === 'solar-prefeasibility' && <SolarPreFeasibilityPage />}
    </div>
  );
}
