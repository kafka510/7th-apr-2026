/**
 * PV Device Hierarchy API
 * Handles hierarchical filtering: Asset -> Inverter -> JB -> String
 */

const API_BASE = '/api/site-onboarding';

export interface HierarchyAsset {
  asset_code: string;
  asset_name: string;
  country: string | null;
}

export interface HierarchyInverter {
  device_id: string;
  device_name: string;
  device_sub_group: string;
}

export interface HierarchyJB {
  device_id: string;
  device_name: string;
  device_sub_group: string;
}

export interface HierarchyString {
  device_id: string;
  device_name: string;
  device_sub_group: string;
  module_datasheet_id: number | null;
  modules_in_series: number | null;
}

export interface HierarchyResponse {
  assets?: HierarchyAsset[];
  inverters?: HierarchyInverter[];
  jbs?: HierarchyJB[];
  strings?: HierarchyString[];
  has_jbs?: boolean;
  inverter_group?: string;
  jb_group?: string;
}

export const pvHierarchyApi = {
  /**
   * Get assets with string devices
   */
  async getAssets(): Promise<HierarchyAsset[]> {
    const response = await fetch(`${API_BASE}/pv-hierarchy/`);
    if (!response.ok) {
      throw new Error(`Failed to fetch assets: ${response.statusText}`);
    }
    const data: HierarchyResponse = await response.json();
    return data.assets || [];
  },

  /**
   * Get inverters under an asset
   */
  async getInverters(assetCode: string): Promise<{ inverters: HierarchyInverter[]; has_jbs: boolean }> {
    const response = await fetch(`${API_BASE}/pv-hierarchy/?asset_code=${encodeURIComponent(assetCode)}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch inverters: ${response.statusText}`);
    }
    const data: HierarchyResponse = await response.json();
    return {
      inverters: data.inverters || [],
      has_jbs: data.has_jbs || false,
    };
  },

  /**
   * Get JBs under an inverter (or strings if no JBs)
   */
  async getJBsOrStrings(
    assetCode: string,
    inverterId: string
  ): Promise<{ jbs?: HierarchyJB[]; strings?: HierarchyString[] }> {
    const response = await fetch(
      `${API_BASE}/pv-hierarchy/?asset_code=${encodeURIComponent(assetCode)}&inverter_id=${encodeURIComponent(
        inverterId
      )}`
    );
    if (!response.ok) {
      throw new Error(`Failed to fetch JBs/strings: ${response.statusText}`);
    }
    const data: HierarchyResponse = await response.json();
    return {
      jbs: data.jbs,
      strings: data.strings,
    };
  },

  /**
   * Get strings under a JB
   */
  async getStrings(assetCode: string, jbId: string): Promise<HierarchyString[]> {
    const response = await fetch(
      `${API_BASE}/pv-hierarchy/?asset_code=${encodeURIComponent(assetCode)}&jb_id=${encodeURIComponent(jbId)}`
    );
    if (!response.ok) {
      throw new Error(`Failed to fetch strings: ${response.statusText}`);
    }
    const data: HierarchyResponse = await response.json();
    return data.strings || [];
  },
};



