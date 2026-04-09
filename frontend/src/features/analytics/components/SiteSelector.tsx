/**
 * Site Selector Component
 */
 
import type { Asset } from '../types';

interface SiteSelectorProps {
  assets: Asset[];
  selectedAssetCode: string | null;
  onAssetChange: (assetCode: string | null, timezone: string | null) => void;
}

export function SiteSelector({ assets, selectedAssetCode, onAssetChange }: SiteSelectorProps) {
  const selectedAsset = assets.find((a) => a.asset_code === selectedAssetCode);

  return (
    <div className="mb-4">
      <label htmlFor="siteSelect" className="mb-2 block text-sm font-bold text-slate-900">Select Site</label>
      <select
        id="siteSelect"
        className="w-full rounded-lg border-2 border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-900 focus:border-purple-500 focus:outline-none focus:ring-2 focus:ring-purple-200"
        value={selectedAssetCode || ''}
        onChange={(e) => {
          const assetCode = e.target.value || null;
          const asset = assets.find((a) => a.asset_code === assetCode);
          onAssetChange(assetCode, asset?.timezone || null);
        }}
      >
        <option value="" className="text-slate-600">-- Select a site --</option>
        {assets.map((asset) => (
          <option key={asset.asset_code} value={asset.asset_code} className="text-slate-900">
            {asset.asset_name} ({asset.asset_code})
          </option>
        ))}
      </select>
      {selectedAsset && (
        <small className="mt-1 block font-medium text-slate-700">Timezone: {selectedAsset.timezone}</small>
      )}
    </div>
  );
}

