/**
 * Hierarchical Filter Component
 * Cascading filter: Asset -> Inverter -> JB -> Strings
 */
import React, { useState, useEffect } from 'react';
import { pvHierarchyApi } from '../api/pvHierarchy';
import type { HierarchyAsset, HierarchyInverter, HierarchyJB } from '../api/pvHierarchy';
import { MultiSelectDropdown } from './MultiSelectDropdown';

interface HierarchicalFilterProps {
  onFilterChange: (filters: FilterState) => void;
}

export interface FilterState {
  asset_code?: string;
  inverter_ids?: string[];  // Changed to array for multi-select
  jb_ids?: string[];        // Changed to array for multi-select
  level: 'asset' | 'inverter' | 'jb' | 'string';
}

export const HierarchicalFilter: React.FC<HierarchicalFilterProps> = ({ onFilterChange }) => {
  const [assets, setAssets] = useState<HierarchyAsset[]>([]);
  const [inverters, setInverters] = useState<HierarchyInverter[]>([]);
  const [jbs, setJBs] = useState<HierarchyJB[]>([]);
  const [hasJBs, setHasJBs] = useState(false);
  const [loading, setLoading] = useState(false);

  const [selectedAsset, setSelectedAsset] = useState<string>('');
  const [selectedInverters, setSelectedInverters] = useState<string[]>([]);
  const [selectedJBs, setSelectedJBs] = useState<string[]>([]);
  const [assetSearch, setAssetSearch] = useState<string>('');

  // Load assets on mount
  useEffect(() => {
    loadAssets();
  }, []);

  const loadAssets = async () => {
    setLoading(true);
    try {
      const assetData = await pvHierarchyApi.getAssets();
      setAssets(assetData);
    } catch (error) {
      console.error('Failed to load assets:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAssetChange = async (assetCode: string) => {
    setSelectedAsset(assetCode);
    setSelectedInverters([]);
    setSelectedJBs([]);
    setInverters([]);
    setJBs([]);
    setHasJBs(false);

    if (!assetCode) {
      onFilterChange({ level: 'asset' });
      return;
    }

    setLoading(true);
    try {
      const { inverters: invData, has_jbs } = await pvHierarchyApi.getInverters(assetCode);
      setInverters(invData);
      setHasJBs(has_jbs);
      onFilterChange({ asset_code: assetCode, level: 'inverter' });
    } catch (error) {
      console.error('Failed to load inverters:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleInvertersChange = async (inverterIds: string[]) => {
    setSelectedInverters(inverterIds);
    setSelectedJBs([]);
    setJBs([]);

    if (inverterIds.length === 0) {
      onFilterChange({ asset_code: selectedAsset, level: 'inverter' });
      return;
    }

    // Fetch JBs for ALL selected inverters and combine
    setLoading(true);
    try {
      const allJBs: HierarchyJB[] = [];
      let foundJBs = false;
      
      // Fetch JBs for each selected inverter
      for (const inverterId of inverterIds) {
        const { jbs: jbData } = await pvHierarchyApi.getJBsOrStrings(selectedAsset, inverterId);
        if (jbData && jbData.length > 0) {
          allJBs.push(...jbData);
          foundJBs = true;
        }
      }
      
      if (foundJBs && allJBs.length > 0) {
        // Remove duplicates based on device_id
        const uniqueJBs = Array.from(
          new Map(allJBs.map(jb => [jb.device_id, jb])).values()
        );
        setJBs(uniqueJBs);
        onFilterChange({ asset_code: selectedAsset, inverter_ids: inverterIds, level: 'jb' });
      } else {
        // No JBs, show strings directly
        onFilterChange({ asset_code: selectedAsset, inverter_ids: inverterIds, level: 'string' });
      }
    } catch (error) {
      console.error('Failed to load JBs/strings:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleJBsChange = (jbIds: string[]) => {
    setSelectedJBs(jbIds);

    if (jbIds.length === 0) {
      onFilterChange({ asset_code: selectedAsset, inverter_ids: selectedInverters, level: 'jb' });
      return;
    }

    onFilterChange({ asset_code: selectedAsset, inverter_ids: selectedInverters, jb_ids: jbIds, level: 'string' });
  };

  // Filter assets based on search
  const filteredAssets = assets.filter((asset) =>
    assetSearch
      ? asset.asset_name.toLowerCase().includes(assetSearch.toLowerCase()) ||
        asset.asset_code.toLowerCase().includes(assetSearch.toLowerCase())
      : true
  );

  return (
    <div className="hierarchical-filter mb-4">
      <div className="row g-3">
        {/* Asset Filter with Search */}
        <div className="col-md-3">
          <label className="fw-medium text-dark mb-1 text-sm">1. Select Asset</label>
          <input
            type="text"
            className="form-control mb-2"
            placeholder="🔍 Search assets..."
            value={assetSearch}
            onChange={(e) => setAssetSearch(e.target.value)}
          />
          <select
            className="form-select"
            value={selectedAsset}
            onChange={(e) => handleAssetChange(e.target.value)}
            disabled={loading}
            size={5}
            style={{ minHeight: '120px' }}
          >
            <option value="">-- Select Asset --</option>
            {filteredAssets.map((asset) => (
              <option key={asset.asset_code} value={asset.asset_code}>
                {asset.asset_name} ({asset.asset_code})
              </option>
            ))}
          </select>
          {assetSearch && (
            <small className="text-muted">
              Showing {filteredAssets.length} of {assets.length} assets
            </small>
          )}
        </div>

        {/* Inverter Filter (Multi-Select) */}
        {selectedAsset && inverters.length > 0 && (
          <div className="col-md-3">
            <MultiSelectDropdown
              label="2. Select Inverter(s)"
              options={inverters.map((inv) => ({
                value: inv.device_id,
                label: inv.device_name,
              }))}
              selectedValues={selectedInverters}
              onChange={handleInvertersChange}
              placeholder="-- Select Inverter(s) --"
              disabled={loading}
            />
          </div>
        )}

        {/* JB Filter (Multi-Select) */}
        {selectedInverters.length > 0 && jbs.length > 0 && (
          <div className="col-md-3">
            <MultiSelectDropdown
              label="3. Select Junction Box(es)"
              options={jbs.map((jb) => ({
                value: jb.device_id,
                label: jb.device_name,
              }))}
              selectedValues={selectedJBs}
              onChange={handleJBsChange}
              placeholder="-- Select JB(s) --"
              disabled={loading}
            />
          </div>
        )}

        {/* Status Indicator */}
        {selectedAsset && (
          <div className="col-md-3">
            <label className="fw-medium text-dark mb-1 text-sm">Filter Status</label>
            <div className="form-control bg-light text-dark">
              {selectedInverters.length === 0 && '✓ Asset selected'}
              {selectedInverters.length > 0 && selectedJBs.length === 0 && jbs.length === 0 && `✓ ${selectedInverters.length} inverter(s)`}
              {selectedInverters.length > 0 && selectedJBs.length === 0 && jbs.length > 0 && '→ Select JB(s)'}
              {selectedJBs.length > 0 && `✓ ${selectedJBs.length} JB(s)`}
              {loading && '⏳ Loading...'}
            </div>
          </div>
        )}
      </div>

      {/* Info Banner */}
      {selectedAsset && (
        <div className="alert alert-info mb-0 mt-3">
          <small className="text-dark">
            <strong>Hierarchy:</strong> {selectedAsset}
            {selectedInverters.length > 0 && ` → ${selectedInverters.length} inverter(s)`}
            {selectedJBs.length > 0 && ` → ${selectedJBs.length} JB(s)`}
            {selectedInverters.length > 0 && !hasJBs && ' (No JBs in this site)'}
          </small>
        </div>
      )}
    </div>
  );
};

