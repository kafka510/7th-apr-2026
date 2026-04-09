/**
 * Single-site onboarding wizard: Adapter → Asset → Data collection → Devices → PV modules → [optional] Budget.
 * Admin-only; no delete actions. Reuses existing site-onboarding APIs.
 */
import { useState, useEffect } from 'react';
import { useTheme } from '../../contexts/ThemeContext';
import { getGradientBg } from '../../utils/themeColors';
import {
  getDataCollectionAdapterIds,
  fusionSolarFetchPlants,
  fusionSolarFetchDevices,
  laplaceidTestConnection,
  laplaceidFetchDevicesForAssets,
  fetchAdapterRawSamples,
  fetchAssetAdapterConfig,
  fetchAdapterAccounts,
  getAllAssets,
} from './api';
import type { AssetList, DeviceList, AssetAdapterConfig, AdapterAccount } from './types';
import type { FusionSolarPlant } from './api';

const STEPS = [
  { id: 1, label: 'Adapter' },
  { id: 2, label: 'Asset' },
  { id: 3, label: 'Data collection' },
  { id: 4, label: 'Devices' },
  { id: 5, label: 'PV modules' },
  { id: 6, label: 'Budget (optional)' },
];

export function SiteOnboardingWizard() {
  const { theme } = useTheme();
  const bgGradient = getGradientBg(theme);
  const textPrimary = theme === 'dark' ? '#f1f5f9' : '#1a1a1a';
  const textSecondary = theme === 'dark' ? '#cbd5e1' : '#4a5568';
  const [step, setStep] = useState(1);
  const [adapterIds, setAdapterIds] = useState<string[]>([]);
  const [adapterId, setAdapterId] = useState<string>('fusion_solar');
  const [plantsLoading, setPlantsLoading] = useState(false);
  const [plantsError, setPlantsError] = useState<string | null>(null);
  const [laplaceTestInfo, setLaplaceTestInfo] = useState<{
    ok: boolean;
    meta?: { api_version?: string; instant_date?: string; instant_name?: string };
    nodes?: { node_id: string; name: string; setTime?: string; tags?: string[] }[];
  } | null>(null);
  const [assetAdapterId, setAssetAdapterId] = useState<string>('fusion_solar');
  const [assetAdapterAccounts, setAssetAdapterAccounts] = useState<AdapterAccount[]>([]);
  const [assetAdapterAccountsLoading, setAssetAdapterAccountsLoading] = useState(false);
  const [assetAdapterAccountsError, setAssetAdapterAccountsError] = useState<string | null>(null);
  const [assetAdapterAccountId, setAssetAdapterAccountId] = useState<number | ''>('');
  type WizardDeviceRow = Partial<DeviceList> & { source?: 'fusion' | 'gii' | 'laplace'; asset_code?: string };
  const [devices, setDevices] = useState<WizardDeviceRow[]>([]);
  const [devicesLoading, setDevicesLoading] = useState(false);
  const [devicesError, setDevicesError] = useState<string | null>(null);
  const [rawSamplesLoading, setRawSamplesLoading] = useState(false);
  const [saveMessage, setSaveMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [assetRows, setAssetRows] = useState<(Partial<AssetList> & { provider_asset_id?: string })[]>([]);
  const [allAssets, setAllAssets] = useState<AssetList[]>([]);
  const [dataCollectionConfigs, setDataCollectionConfigs] = useState<AssetAdapterConfig[]>([]);
  const [dataCollectionError, setDataCollectionError] = useState<string | null>(null);
  const [dataCollectionAccounts, setDataCollectionAccounts] = useState<AdapterAccount[]>([]);
  const [dataCollectionAccountsLoading, setDataCollectionAccountsLoading] = useState(false);
  const [dataCollectionAccountsError, setDataCollectionAccountsError] = useState<string | null>(null);
  const [dataCollectionAccountId, setDataCollectionAccountId] = useState<number | ''>('');
  const [adapterAccounts, setAdapterAccounts] = useState<AdapterAccount[]>([]);
  const [adapterAccountsLoading, setAdapterAccountsLoading] = useState(false);
  const [adapterAccountsError, setAdapterAccountsError] = useState<string | null>(null);
  const [deviceAdapterId, setDeviceAdapterId] = useState<string>('fusion_solar');
  const [deviceAdapterAccountId, setDeviceAdapterAccountId] = useState<number | ''>('');
  const [deviceAssets, setDeviceAssets] = useState<AssetList[]>([]);
  const [deviceAssetSelection, setDeviceAssetSelection] = useState<string[]>([]);
  const [deviceConfigsByAsset, setDeviceConfigsByAsset] = useState<Record<string, AssetAdapterConfig>>({});

  useEffect(() => {
    getDataCollectionAdapterIds()
      .then((ids) => {
        const safe = Array.isArray(ids) ? ids.filter(Boolean) : [];
        setAdapterIds(safe);
        if (safe.length && !safe.includes(adapterId)) {
          setAdapterId(safe[0]);
        }
        if (safe.length && !safe.includes(assetAdapterId)) {
          setAssetAdapterId(safe[0]);
        }
      })
      .catch(() => {
        setAdapterIds([]);
      });
  }, []);

  useEffect(() => {
    // Default the Asset step adapter to whatever was chosen in Step 1.
    // User can still change it in the Asset step.
    setAssetAdapterId(adapterId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [adapterId]);

  useEffect(() => {
    if (!assetAdapterId) {
      setAssetAdapterAccounts([]);
      setAssetAdapterAccountId('');
      return;
    }
    setAssetAdapterAccountsLoading(true);
    setAssetAdapterAccountsError(null);
    fetchAdapterAccounts(assetAdapterId)
      .then((res) => setAssetAdapterAccounts(res.data || []))
      .catch((err: any) => {
        setAssetAdapterAccountsError(err?.message || 'Failed to load adapter accounts');
        setAssetAdapterAccounts([]);
      })
      .finally(() => setAssetAdapterAccountsLoading(false));
  }, [assetAdapterId]);

  useEffect(() => {
    getAllAssets().then(setAllAssets).catch(() => {});
  }, []);

  const clearMessage = () => setSaveMessage(null);

  const buildAssetRowFromPlant = (p: FusionSolarPlant): Partial<AssetList> & { provider_asset_id?: string } => {
    const code = (p.plantCode ?? p.stationCode ?? p.stationId ?? '') as string;
    const name = (p.plantName ?? p.stationName ?? p.name ?? code) as string;
    const latRaw = (p as any).latitude;
    const lngRaw = (p as any).longitude;
    const parseCoord = (raw: unknown, fallback: number | undefined) => {
      if (raw === undefined || raw === null) return fallback ?? 0;
      const s = String(raw).trim();
      if (!s) return fallback ?? 0;
      const n = Number(s);
      return Number.isFinite(n) ? n : fallback ?? 0;
    };
    const codeKey = code.replace(/[^a-zA-Z0-9_-]/g, '_').slice(0, 50);
    return {
      asset_code: codeKey,
      asset_name: name,
      provider_asset_id: code,
      capacity: (p.capacity ?? p.installCapacity ?? 0) as number,
      address: ((p.plantAddress ?? p.stationAddr ?? p.address ?? p.stationAddress) as string) || '',
      country: ((p.country ?? p.countryCode) as string) || '',
      latitude: parseCoord(latRaw, undefined),
      longitude: parseCoord(lngRaw, undefined),
      contact_person: ((p as any).contactPerson as string) || '',
      contact_method: ((p as any).contactMethod as string) || '',
      grid_connection_date: ((p as any).gridConnectionDate as string) || '',
      asset_number: '',
      timezone: '',
      asset_name_oem: '',
      cod: '',
      operational_cod: '',
      portfolio: '',
      y1_degradation: null,
      anual_degradation: null,
      api_name: '',
      api_key: '',
      tilt_configs: null,
      altitude_m: null,
      albedo: null,
      pv_syst_pr: null,
      satellite_irradiance_source_asset_code: null,
    };
  };

  const toCsvValue = (value: unknown): string => {
    if (value === null || value === undefined) return '""';
    const s = String(value);
    const escaped = s.replace(/"/g, '""');
    return `"${escaped}"`;
  };

  const handleFetchPlants = async () => {
    if (!assetAdapterId) return;
    if (!assetAdapterAccountId) {
      setPlantsError('Please select an Adapter Account');
      setAssetRows([]);
      setLaplaceTestInfo(null);
      return;
    }
    if (assetAdapterId === 'laplaceid') {
      setPlantsLoading(true);
      setPlantsError(null);
      setAssetRows([]);
      const res = await laplaceidTestConnection({
        adapter_account_id: Number(assetAdapterAccountId),
      });
      setPlantsLoading(false);
      if (res.success) {
        setLaplaceTestInfo({ ok: true, meta: res.meta, nodes: res.nodes });
        setPlantsError(null);
      } else {
        setLaplaceTestInfo({ ok: false });
        setPlantsError(res.error);
      }
      return;
    }
    if (assetAdapterId !== 'fusion_solar') {
      setPlantsError(`Site list fetch is not implemented for adapter: ${assetAdapterId}`);
      setLaplaceTestInfo(null);
      setAssetRows([]);
      return;
    }
    setPlantsLoading(true);
    setPlantsError(null);
    setLaplaceTestInfo(null);
    const res = await fusionSolarFetchPlants({
      adapter_id: assetAdapterId,
      adapter_account_id: Number(assetAdapterAccountId),
    });
    setPlantsLoading(false);
    if (res.success) {
      setPlantsError(null);
      setAssetRows(res.plants.map((p) => buildAssetRowFromPlant(p)));
    } else {
      setPlantsError(res.error);
      setAssetRows([]);
    }
  };

  const downloadAssetCsv = () => {
    if (!assetRows.length) return;
    const headers = [
      'asset_code',
      'asset_name',
      'provider_asset_id',
      'capacity',
      'address',
      'country',
      'latitude',
      'longitude',
      'contact_person',
      'contact_method',
      'grid_connection_date',
      'asset_number',
      'timezone',
      'asset_name_oem',
      'cod',
      'operational_cod',
      'portfolio',
      'y1_degradation',
      'anual_degradation',
      'api_name',
      'api_key',
      'tilt_configs',
      'altitude_m',
      'albedo',
      'pv_syst_pr',
      'satellite_irradiance_source_asset_code',
    ];
    const lines = [
      headers.map(toCsvValue).join(','),
      ...assetRows.map((r) =>
        [
          r.asset_code ?? '',
          r.asset_name ?? '',
          r.provider_asset_id ?? '',
          r.capacity ?? '',
          r.address ?? '',
          r.country ?? '',
          r.latitude ?? '',
          r.longitude ?? '',
          r.contact_person ?? '',
          r.contact_method ?? '',
          r.grid_connection_date ?? '',
          r.asset_number ?? '',
          r.timezone ?? '',
          r.asset_name_oem ?? '',
          r.cod ?? '',
          r.operational_cod ?? '',
          r.portfolio ?? '',
          r.y1_degradation ?? '',
          r.anual_degradation ?? '',
          r.api_name ?? '',
          r.api_key ?? '',
          r.tilt_configs ? JSON.stringify(r.tilt_configs) : '',
          r.altitude_m ?? '',
          r.albedo ?? '',
          r.pv_syst_pr ?? '',
          r.satellite_irradiance_source_asset_code ?? '',
        ]
          .map(toCsvValue)
          .join(',')
      ),
    ];
    const blob = new Blob(['\uFEFF', lines.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'asset_list_wizard.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleLoadDataCollectionConfigs = async (selectedAdapterId: string, accountId: number | '') => {
    if (!selectedAdapterId || !accountId) {
      setDataCollectionConfigs([]);
      return;
    }
    setDataCollectionError(null);
    try {
      const res = await fetchAssetAdapterConfig(1, 1000, '', '', selectedAdapterId);
      const filtered = res.data.filter((cfg) => cfg.adapter_account_id === accountId);
      setDataCollectionConfigs(filtered);
    } catch (err: any) {
      setDataCollectionError(err?.message || 'Failed to load adapter configs');
      setDataCollectionConfigs([]);
    } finally {
      // no-op
    }
  };

  const handleLoadDeviceHelperContext = async () => {
    setAdapterAccountsLoading(true);
    setAdapterAccountsError(null);
    try {
      const accountsRes = await fetchAdapterAccounts(deviceAdapterId);
      setAdapterAccounts(accountsRes.data || []);
    } catch (err: any) {
      setAdapterAccountsError(err?.message || 'Failed to load adapter accounts');
      setAdapterAccounts([]);
    } finally {
      setAdapterAccountsLoading(false);
    }
  };

  useEffect(() => {
    if (!adapterId) {
      setDataCollectionAccounts([]);
      return;
    }
    setDataCollectionAccountsLoading(true);
    setDataCollectionAccountsError(null);
    fetchAdapterAccounts(adapterId)
      .then((res) => setDataCollectionAccounts(res.data || []))
      .catch((err: any) => {
        setDataCollectionAccountsError(err?.message || 'Failed to load adapter accounts');
        setDataCollectionAccounts([]);
      })
      .finally(() => setDataCollectionAccountsLoading(false));
  }, [adapterId]);

  useEffect(() => {
    handleLoadDataCollectionConfigs(adapterId, dataCollectionAccountId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [adapterId, dataCollectionAccountId]);

  useEffect(() => {
    handleLoadDeviceHelperContext();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [deviceAdapterId]);

  const handleLoadAssetsForSelectedAccount = async () => {
    if (!deviceAdapterAccountId) {
      setDeviceAssets([]);
      setDeviceConfigsByAsset({});
      return;
    }
    setDevicesError(null);
    setDevices([]);
    setDevicesLoading(true);
    try {
      const res = await fetchAssetAdapterConfig(1, 1000, '', '', deviceAdapterId);
      const byAsset: Record<string, AssetAdapterConfig> = {};
      const assetCodes: string[] = [];
      res.data
        .filter((cfg) => cfg.adapter_account_id === deviceAdapterAccountId)
        .forEach((cfg) => {
          byAsset[cfg.asset_code] = cfg;
          assetCodes.push(cfg.asset_code);
        });
      setDeviceConfigsByAsset(byAsset);
      const assetsForAccount = allAssets.filter((a) => assetCodes.includes(a.asset_code));
      setDeviceAssets(assetsForAccount);
      setDeviceAssetSelection(assetsForAccount.map((a) => a.asset_code));
    } catch (err: any) {
      setDevicesError(err?.message || 'Failed to load assets for adapter account');
      setDeviceAssets([]);
      setDeviceConfigsByAsset({});
    } finally {
      setDevicesLoading(false);
    }
  };

  const handleToggleDeviceAsset = (assetCode: string) => {
    setDeviceAssetSelection((prev) =>
      prev.includes(assetCode) ? prev.filter((c) => c !== assetCode) : [...prev, assetCode]
    );
  };

  const handleSelectAllDeviceAssets = () => {
    setDeviceAssetSelection(deviceAssets.map((a) => a.asset_code));
  };

  const handleDeselectAllDeviceAssets = () => {
    setDeviceAssetSelection([]);
  };

  const handleFetchDevices = async () => {
    if (!deviceAdapterAccountId || deviceAssetSelection.length === 0) return;
    setDevicesLoading(true);
    setDevicesError(null);
    try {
      const selectedAssets = deviceAssets.filter((a) => deviceAssetSelection.includes(a.asset_code));
      const allDeviceRows: WizardDeviceRow[] = [];
      const fetchErrors: string[] = [];
      const normalizeError = (value: unknown) => {
        if (typeof value === 'string' && value.trim()) return value;
        if (value instanceof Error && value.message) return value.message;
        if (value && typeof value === 'object') {
          const maybeMessage = (value as any).message || (value as any).error || (value as any).detail;
          if (typeof maybeMessage === 'string' && maybeMessage.trim()) return maybeMessage;
          try {
            return JSON.stringify(value);
          } catch {
            return String(value);
          }
        }
        return 'Unknown device fetch error';
      };

      if (deviceAdapterId === 'laplaceid') {
        const res = await laplaceidFetchDevicesForAssets({
          adapter_account_id: Number(deviceAdapterAccountId),
          asset_codes: selectedAssets.map((a) => a.asset_code),
          unit: 'minute',
          csv_api: 'hourly.php',
          types: ['pcs', 'string', 'battery', 'approvedmeter', 'wh'],
        });
        if (res.success) {
          res.devices.forEach((d) => {
            const row: WizardDeviceRow = {
              device_id: d.device_id,
              device_name: d.device_name,
              device_code: d.device_code,
              device_type_id: d.device_type_id,
              parent_code: d.parent_code,
              device_type: d.device_type,
              country: (d as any).country ?? '',
              device_source: (d as any).device_source ?? 'laplaceid',
              source:
                (d as any).device_source === 'gii'
                  ? 'gii'
                  : (d as any).device_source === 'laplaceid'
                    ? 'laplace'
                    : 'fusion',
              asset_code: d.parent_code,
            };
            allDeviceRows.push(row);
          });
        } else {
          fetchErrors.push(normalizeError(res.error || 'Laplace device fetch failed'));
        }
        if (fetchErrors.length > 0) {
          setDevicesError(fetchErrors.join(' | '));
        } else if (allDeviceRows.length === 0) {
          setDevicesError('No devices were returned for the selected assets.');
        }
        setDevices(allDeviceRows);
        return;
      }

      for (const assetItem of selectedAssets) {
        if (deviceAdapterId === 'fusion_solar') {
          const cfg = deviceConfigsByAsset[assetItem.asset_code];
          const plantId =
            (cfg?.config?.plant_id as string | undefined) ||
            (assetItem.provider_asset_id as string | undefined);
          const res = await fusionSolarFetchDevices({
            asset_code: assetItem.asset_code,
            plant_id: plantId,
            adapter_account_id: typeof deviceAdapterAccountId === 'number' ? deviceAdapterAccountId : undefined,
          });
          if (res.success) {
            res.devices.forEach((d) => {
              const row: WizardDeviceRow = {
                device_id: d.device_id,
                device_name: d.device_name,
                device_code: d.device_code,
                device_type_id: d.device_type_id,
                parent_code: d.parent_code ?? assetItem.asset_code,
                device_type: d.device_type,
                country: (d as any).country ?? assetItem.country,
                device_serial: (d as any).device_serial ?? '',
                device_model: (d as any).device_model ?? '',
                device_make: (d as any).device_make ?? '',
                latitude: (d as any).latitude ?? assetItem.latitude,
                longitude: (d as any).longitude ?? assetItem.longitude,
                optimizer_no: ((d as any).optimizer_no as number | null) ?? 0,
                software_version: (d as any).software_version ?? '',
                string_no: (d as any).string_no ?? '',
                connected_strings: (d as any).connected_strings ?? '',
                device_sub_group: (d as any).device_sub_group ?? '',
                dc_cap: (d as any).dc_cap ?? 0,
                device_source: '',
                ac_capacity: (d as any).ac_capacity ?? null,
                equipment_warranty_start_date: (d as any).equipment_warranty_start_date ?? null,
                equipment_warranty_expire_date: (d as any).equipment_warranty_expire_date ?? null,
                epc_warranty_start_date: (d as any).epc_warranty_start_date ?? null,
                epc_warranty_expire_date: (d as any).epc_warranty_expire_date ?? null,
                calibration_frequency: (d as any).calibration_frequency ?? '',
                pm_frequency: (d as any).pm_frequency ?? '',
                visual_inspection_frequency: (d as any).visual_inspection_frequency ?? '',
                bess_capacity: (d as any).bess_capacity ?? null,
                yom: (d as any).yom ?? '',
                nomenclature: (d as any).nomenclature ?? '',
                location: (d as any).location ?? '',
                module_datasheet_id: (d as any).module_datasheet_id ?? null,
                modules_in_series: (d as any).modules_in_series ?? null,
                installation_date: (d as any).installation_date ?? null,
                tilt_angle: (d as any).tilt_angle ?? null,
                azimuth_angle: (d as any).azimuth_angle ?? null,
                mounting_type: (d as any).mounting_type ?? null,
                expected_soiling_loss: (d as any).expected_soiling_loss ?? null,
                shading_factor: (d as any).shading_factor ?? null,
                measured_degradation_rate: (d as any).measured_degradation_rate ?? null,
                last_performance_test_date: (d as any).last_performance_test_date ?? null,
                operational_notes: (d as any).operational_notes ?? null,
                power_model_id: (d as any).power_model_id ?? null,
                power_model_config: (d as any).power_model_config ?? null,
                model_fallback_enabled: (d as any).model_fallback_enabled ?? null,
                weather_device_config: (d as any).weather_device_config ?? null,
                tilt_configs: (d as any).tilt_configs ?? null,
                source: (d as any).device_source === 'gii' ? 'gii' : 'fusion',
                asset_code: assetItem.asset_code,
              };
              allDeviceRows.push(row);
            });
          } else {
            fetchErrors.push(`${assetItem.asset_code}: ${normalizeError(res.error || 'Fusion device fetch failed')}`);
          }
        } else {
          fetchErrors.push(`Device fetch is not implemented for adapter: ${deviceAdapterId}`);
        }
      }

      if (fetchErrors.length > 0) {
        setDevicesError(fetchErrors.join(' | '));
      } else if (allDeviceRows.length === 0) {
        setDevicesError('No devices were returned for the selected assets.');
      }
      setDevices(allDeviceRows);
    } catch (err: any) {
      setDevicesError(err?.message || 'Failed to fetch devices');
      setDevices([]);
    } finally {
      setDevicesLoading(false);
    }
  };

  const triggerTextDownload = (filename: string, content: string, mime: string) => {
    const isCsv = /\.csv$/i.test(filename) || mime.toLowerCase().includes('text/csv');
    const payload = isCsv && !content.startsWith('\uFEFF') ? `\uFEFF${content}` : content;
    const blob = new Blob([payload], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.rel = 'noopener';
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  };

  const handleDownloadProviderRawSamples = async () => {
    if (!deviceAdapterId || deviceAssetSelection.length === 0) return;
    if (deviceAdapterId === 'laplaceid' && !deviceAdapterAccountId) {
      setDevicesError('Select an adapter account to download Laplace raw CSVs.');
      return;
    }
    setRawSamplesLoading(true);
    setDevicesError(null);
    try {
      const res = await fetchAdapterRawSamples({
        adapter_id: deviceAdapterId,
        adapter_account_id: typeof deviceAdapterAccountId === 'number' ? deviceAdapterAccountId : undefined,
        asset_codes: deviceAssetSelection,
        ...(deviceAdapterId === 'laplaceid'
          ? {
              unit: 'minute',
              csv_api: 'hourly.php',
              types: ['pcs', 'string', 'battery', 'approvedmeter', 'wh'],
            }
          : {}),
      });
      if (!res.success) {
        setDevicesError(res.error || 'Failed to fetch raw samples');
        return;
      }
      if (res.errors?.length) {
        const msg = res.errors.map((e) => `${e.asset_code}: ${e.detail}`).join('; ');
        setDevicesError((prev) => prev || `Some requests failed: ${msg}`);
      }
      if (!res.files?.length) {
        setDevicesError((prev) => prev || 'No files returned from server.');
        return;
      }
      for (let i = 0; i < res.files.length; i += 1) {
        const f = res.files[i];
        const mime = f.media_type || 'text/plain; charset=utf-8';
        triggerTextDownload(f.filename, f.content, mime);
        if (i < res.files.length - 1) {
          await new Promise((r) => setTimeout(r, 400));
        }
      }
    } catch (err: any) {
      setDevicesError(err?.message || 'Failed to download raw samples');
    } finally {
      setRawSamplesLoading(false);
    }
  };

  const handleDownloadLaplaceWhRawSamples = async () => {
    if (deviceAdapterId !== 'laplaceid') return;
    if (!deviceAdapterAccountId || deviceAssetSelection.length === 0) return;
    setRawSamplesLoading(true);
    setDevicesError(null);
    try {
      const res = await fetchAdapterRawSamples({
        adapter_id: 'laplaceid',
        adapter_account_id: Number(deviceAdapterAccountId),
        asset_codes: deviceAssetSelection,
        unit: 'halfhour',
        csv_api: 'daily.php',
        // Laplace WH export is provided via halfhour unit with type=pcs.
        types: ['pcs'],
      });
      if (!res.success) {
        setDevicesError(res.error || 'Failed to fetch Laplace WH raw samples');
        return;
      }
      if (!res.files?.length) {
        setDevicesError('No WH files returned from server.');
        return;
      }
      for (let i = 0; i < res.files.length; i += 1) {
        const f = res.files[i];
        const mime = f.media_type || 'text/csv; charset=utf-8';
        triggerTextDownload(f.filename, f.content, mime);
        if (i < res.files.length - 1) {
          await new Promise((r) => setTimeout(r, 400));
        }
      }
    } catch (err: any) {
      setDevicesError(err?.message || 'Failed to download Laplace WH raw samples');
    } finally {
      setRawSamplesLoading(false);
    }
  };

  const downloadDeviceCsv = (assetCode?: string) => {
    const rows = assetCode
      ? devices.filter((d) => (d.parent_code ?? d.asset_code ?? '') === assetCode)
      : devices;
    if (!rows.length) return;
    const headers = [
      'device_id',
      'device_name',
      'device_code',
      'device_type_id',
      'device_serial',
      'device_model',
      'device_make',
      'latitude',
      'longitude',
      'optimizer_no',
      'parent_code',
      'device_type',
      'software_version',
      'country',
      'string_no',
      'connected_strings',
      'device_sub_group',
      'dc_cap',
      'device_source',
      'ac_capacity',
      'equipment_warranty_start_date',
      'equipment_warranty_expire_date',
      'epc_warranty_start_date',
      'epc_warranty_expire_date',
      'calibration_frequency',
      'pm_frequency',
      'visual_inspection_frequency',
      'bess_capacity',
      'yom',
      'nomenclature',
      'location',
      'module_datasheet_id',
      'modules_in_series',
      'installation_date',
      'tilt_angle',
      'azimuth_angle',
      'mounting_type',
      'expected_soiling_loss',
      'shading_factor',
      'measured_degradation_rate',
      'last_performance_test_date',
      'operational_notes',
      'power_model_id',
      'power_model_config_json',
      'model_fallback_enabled',
      'weather_device_config_json',
      'tilt_configs_json',
    ];
    const toExcelTextIfNumeric = (value: unknown): string => {
      const raw = value == null ? '' : String(value).trim();
      if (!raw) return '';
      return /^\d+$/.test(raw) ? `'${raw}` : raw;
    };
    const lines = [
      headers.map(toCsvValue).join(','),
      ...rows.map((d) => [
        toExcelTextIfNumeric(d.device_id),
        d.device_name ?? '',
        toExcelTextIfNumeric(d.device_code),
        d.device_type_id ?? '',
        d.device_serial ?? '',
        d.device_model ?? '',
        d.device_make ?? '',
        d.latitude ?? '',
        d.longitude ?? '',
        d.optimizer_no ?? '',
        d.parent_code ?? d.asset_code ?? '',
        d.device_type ?? '',
        d.software_version ?? '',
        d.country ?? '',
        d.string_no ?? '',
        d.connected_strings ?? '',
        toExcelTextIfNumeric(d.device_sub_group),
        d.dc_cap ?? '',
        d.device_source ?? '',
        d.ac_capacity ?? '',
        d.equipment_warranty_start_date ?? '',
        d.equipment_warranty_expire_date ?? '',
        d.epc_warranty_start_date ?? '',
        d.epc_warranty_expire_date ?? '',
        d.calibration_frequency ?? '',
        d.pm_frequency ?? '',
        d.visual_inspection_frequency ?? '',
        d.bess_capacity ?? '',
        d.yom ?? '',
        d.nomenclature ?? '',
        d.location ?? '',
        d.module_datasheet_id ?? '',
        d.modules_in_series ?? '',
        d.installation_date ?? '',
        d.tilt_angle ?? '',
        d.azimuth_angle ?? '',
        d.mounting_type ?? '',
        d.expected_soiling_loss ?? '',
        d.shading_factor ?? '',
        d.measured_degradation_rate ?? '',
        d.last_performance_test_date ?? '',
        d.operational_notes ?? '',
        d.power_model_id ?? '',
        d.power_model_config ? JSON.stringify(d.power_model_config) : '',
        d.model_fallback_enabled ?? '',
        d.weather_device_config ? JSON.stringify(d.weather_device_config) : '',
        d.tilt_configs ? JSON.stringify(d.tilt_configs) : '',
      ].map(toCsvValue).join(',')),
    ];
    const blob = new Blob(['\uFEFF', lines.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = assetCode ? `device_list_wizard_${assetCode}.csv` : 'device_list_wizard.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex w-full flex-col p-4" style={{ background: bgGradient, minHeight: '100vh', color: textPrimary }}>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-xl font-bold">Single-Site Onboarding Wizard</h2>
        <a href="/site-onboarding/" className="rounded border px-3 py-1.5 text-sm" style={{ borderColor: theme === 'dark' ? '#475569' : '#cbd5e1', color: textPrimary }}>
          ← Back to Site Onboarding
        </a>
      </div>

      {/* Stepper */}
      <div className="mb-6 flex flex-wrap gap-2">
        {STEPS.map((s) => (
          <button
            key={s.id}
            type="button"
            onClick={() => setStep(s.id)}
            className="rounded-lg px-3 py-1.5 text-sm font-medium transition"
            style={{
              backgroundColor: step === s.id ? (theme === 'dark' ? 'rgba(56, 189, 248, 0.3)' : 'rgba(59, 130, 246, 0.2)') : 'transparent',
              border: `1px solid ${step === s.id ? (theme === 'dark' ? '#38bdf8' : '#2563eb') : theme === 'dark' ? '#334155' : '#e2e8f0'}`,
              color: textPrimary,
            }}
          >
            {s.id}. {s.label}
          </button>
        ))}
      </div>

      {saveMessage && (
        <div
          className="mb-4 rounded-lg border p-3"
          style={{
            borderColor: saveMessage.type === 'error' ? '#dc2626' : '#16a34a',
            backgroundColor: saveMessage.type === 'error' ? 'rgba(220, 38, 38, 0.1)' : 'rgba(22, 163, 74, 0.1)',
          }}
        >
          {saveMessage.text}
          <button type="button" onClick={clearMessage} className="ml-2 text-sm underline">Dismiss</button>
        </div>
      )}

      {/* Step 1: Adapter */}
      {step === 1 && (
        <div className="rounded-xl border p-6" style={{ borderColor: theme === 'dark' ? '#475569' : '#e2e8f0', maxWidth: 480 }}>
          <h3 className="mb-4 text-lg font-semibold">Select data source adapter</h3>
          <label className="block mb-2 text-sm">Adapter</label>
          <select
            value={adapterId}
            onChange={(e) => setAdapterId(e.target.value)}
            className="w-full rounded border bg-transparent px-3 py-2"
            style={{ borderColor: theme === 'dark' ? '#475569' : '#cbd5e1', color: textPrimary }}
          >
            {adapterIds.map((id) => (
              <option key={id} value={id}>{id === 'fusion_solar' ? 'Fusion Solar' : id === 'solargis' ? 'SolarGIS' : id}</option>
            ))}
          </select>
          <div className="mt-6 flex gap-2">
            <button type="button" onClick={() => setStep(2)} className="rounded bg-blue-600 px-4 py-2 text-white">Next →</button>
          </div>
        </div>
      )}

      {/* Step 2: Asset CSV helper (Provider sites → asset_list rows) */}
      {step === 2 && (
        <div className="rounded-xl border p-6" style={{ borderColor: theme === 'dark' ? '#475569' : '#e2e8f0', maxWidth: 720 }}>
          <h3 className="mb-4 text-lg font-semibold">Assets (generate asset_list CSV)</h3>
          <div className="mb-4 rounded border p-3" style={{ borderColor: theme === 'dark' ? '#475569' : '#e2e8f0' }}>
            <p className="mb-2 text-sm font-medium">Fetch sites from provider</p>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
              <div>
                <label className="block text-xs opacity-80">Adapter</label>
                <select
                  value={assetAdapterId}
                  onChange={(e) => {
                    const v = e.target.value;
                    setAssetAdapterId(v);
                    setAssetAdapterAccountId('');
                    setAssetRows([]);
                    setPlantsError(null);
                  }}
                  className="w-full rounded border bg-transparent px-2 py-1.5 text-sm"
                  style={{ borderColor: theme === 'dark' ? '#475569' : '#cbd5e1', color: textPrimary }}
                >
                  {adapterIds.length ? (
                    adapterIds.map((id) => (
                      <option key={id} value={id}>
                        {id}
                      </option>
                    ))
                  ) : (
                    <option value="fusion_solar">fusion_solar</option>
                  )}
                </select>
              </div>
              <div>
                <label className="block text-xs opacity-80">Adapter account</label>
                <select
                  value={assetAdapterAccountId === '' ? '' : String(assetAdapterAccountId)}
                  onChange={(e) => {
                    const v = e.target.value;
                    setAssetAdapterAccountId(v ? Number(v) : '');
                    setAssetRows([]);
                    setPlantsError(null);
                  }}
                  className="w-full rounded border bg-transparent px-2 py-1.5 text-sm"
                  style={{ borderColor: theme === 'dark' ? '#475569' : '#cbd5e1', color: textPrimary }}
                >
                  <option value="">Select account…</option>
                  {assetAdapterAccounts.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.name || `Account #${a.id}`}
                    </option>
                  ))}
                </select>
                {assetAdapterAccountsLoading && <p className="mt-1 text-xs opacity-70">Loading accounts…</p>}
                {assetAdapterAccountsError && <p className="mt-1 text-xs text-red-500">{assetAdapterAccountsError}</p>}
              </div>
              <div className="flex items-end">
                <button
                  type="button"
                  onClick={handleFetchPlants}
                  disabled={plantsLoading || !assetAdapterId || !assetAdapterAccountId}
                  className="w-full rounded bg-slate-600 px-3 py-1.5 text-sm text-white disabled:opacity-50"
                >
                  {plantsLoading ? 'Loading…' : 'Fetch sites'}
                </button>
              </div>
            </div>
            <div className="mt-2 text-xs opacity-80" style={{ color: textSecondary }}>
              Credentials are loaded from the selected adapter account.
            </div>
            {plantsError && <p className="mt-2 text-sm text-red-500">{plantsError}</p>}
          </div>
          {assetAdapterId === 'laplaceid' && laplaceTestInfo?.ok && (
            <div className="mb-4 rounded border p-3 text-sm" style={{ borderColor: theme === 'dark' ? '#16a34a' : '#16a34a', backgroundColor: theme === 'dark' ? 'rgba(22, 163, 74, 0.08)' : 'rgba(22, 163, 74, 0.08)' }}>
              <p className="mb-1 font-medium">Connection OK (LaplaceID)</p>
              <p className="mb-2 text-xs opacity-80" style={{ color: textSecondary }}>
                Note: This adapter does not provide an “asset list” API. We verify connectivity using `instant.php?unit=node&aliases=true` and you will onboard assets manually.
              </p>
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
                <div>
                  <div className="text-xs opacity-70">Group / site name</div>
                  <div className="text-sm">{laplaceTestInfo.meta?.instant_name || '—'}</div>
                </div>
                <div>
                  <div className="text-xs opacity-70">API time</div>
                  <div className="text-sm">{laplaceTestInfo.meta?.instant_date || '—'}</div>
                </div>
                <div>
                  <div className="text-xs opacity-70">Nodes returned</div>
                  <div className="text-sm">{laplaceTestInfo.nodes?.length ?? 0}</div>
                </div>
              </div>
              {Array.isArray(laplaceTestInfo.nodes) && laplaceTestInfo.nodes.length > 0 && (
                <div className="mt-3 max-h-40 overflow-auto rounded border p-2" style={{ borderColor: theme === 'dark' ? '#334155' : '#e2e8f0' }}>
                  <table className="w-full text-xs">
                    <thead>
                      <tr>
                        <th className="p-1 text-left">node_id</th>
                        <th className="p-1 text-left">name</th>
                        <th className="p-1 text-left">setTime</th>
                        <th className="p-1 text-left">tags</th>
                      </tr>
                    </thead>
                    <tbody>
                      {laplaceTestInfo.nodes.slice(0, 10).map((n) => (
                        <tr key={n.node_id}>
                          <td className="p-1">{n.node_id}</td>
                          <td className="p-1">{n.name}</td>
                          <td className="p-1">{n.setTime || '—'}</td>
                          <td className="p-1">{(n.tags || []).slice(0, 6).join(', ') || '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {laplaceTestInfo.nodes.length > 10 && (
                    <div className="mt-1 text-[11px] opacity-70">
                      Showing first 10 nodes.
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
          {assetRows.length > 0 && (
            <div className="mt-4">
              <p className="mb-2 text-sm font-medium">Generated asset rows (for asset_list CSV)</p>
              <div className="max-h-60 overflow-auto rounded border" style={{ borderColor: theme === 'dark' ? '#475569' : '#e2e8f0' }}>
                <table className="w-full text-xs sm:text-sm">
                  <thead>
                    <tr>
                      <th className="p-1 text-left">asset_code</th>
                      <th className="p-1 text-left">asset_name</th>
                      <th className="p-1 text-left">provider_asset_id</th>
                      <th className="p-1 text-left">capacity</th>
                      <th className="p-1 text-left">address</th>
                      <th className="p-1 text-left">country</th>
                      <th className="p-1 text-left">latitude</th>
                      <th className="p-1 text-left">longitude</th>
                    </tr>
                  </thead>
                  <tbody>
                    {assetRows.map((r, i) => (
                      <tr key={i}>
                        <td className="p-1">{r.asset_code}</td>
                        <td className="p-1">{r.asset_name}</td>
                        <td className="p-1">{r.provider_asset_id}</td>
                        <td className="p-1">{r.capacity}</td>
                        <td className="p-1">{r.address}</td>
                        <td className="p-1">{r.country}</td>
                        <td className="p-1">{r.latitude}</td>
                        <td className="p-1">{r.longitude}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
          <div className="mt-4 flex gap-2">
            <button type="button" onClick={() => setStep(1)} className="rounded border px-4 py-2" style={{ borderColor: theme === 'dark' ? '#475569' : '#cbd5e1' }}>Back</button>
            <button type="button" onClick={() => setStep(3)} className="rounded bg-blue-600 px-4 py-2 text-white">Next →</button>
            {assetRows.length > 0 && (
              <button type="button" onClick={downloadAssetCsv} className="rounded bg-green-600 px-4 py-2 text-white">
                Download asset CSV
              </button>
            )}
          </div>
        </div>
      )}

      {/* Step 3: Data collection config (read-only helper) */}
      {step === 3 && (
        <div className="rounded-xl border p-6" style={{ borderColor: theme === 'dark' ? '#475569' : '#e2e8f0', maxWidth: 560 }}>
          <h3 className="mb-4 text-lg font-semibold">Data collection (existing configs by account)</h3>
          <p className="mb-3 text-sm opacity-80">
            Select an adapter and adapter account to see all linked assets and their adapter configs.
            Use the main Data Collection UI to create or edit configs.
          </p>
          <div className="mb-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
            <div>
              <label className="block text-sm font-medium">Adapter</label>
              <select
                value={adapterId}
                onChange={(e) => setAdapterId(e.target.value)}
                className="w-full rounded border bg-transparent px-2 py-1.5 text-sm"
                style={{ borderColor: theme === 'dark' ? '#475569' : '#cbd5e1' }}
              >
                {adapterIds.map((id) => (
                  <option key={id} value={id}>
                    {id}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium">Adapter account</label>
              <select
                value={dataCollectionAccountId === '' ? '' : String(dataCollectionAccountId)}
                onChange={(e) => {
                  const v = e.target.value;
                  setDataCollectionAccountId(v ? Number(v) : '');
                }}
                className="w-full rounded border bg-transparent px-2 py-1.5 text-sm"
                style={{ borderColor: theme === 'dark' ? '#475569' : '#cbd5e1' }}
              >
                <option value="">Select account…</option>
                {dataCollectionAccounts.map((acc) => (
                  <option key={acc.id} value={acc.id}>
                    {acc.name || acc.id}
                  </option>
                ))}
              </select>
              {dataCollectionAccountsLoading && <p className="mt-1 text-xs opacity-70">Loading accounts…</p>}
              {dataCollectionAccountsError && <p className="mt-1 text-xs text-red-500">{dataCollectionAccountsError}</p>}
            </div>
          </div>
          {dataCollectionError && <p className="mb-3 text-sm text-red-500">{dataCollectionError}</p>}
          {dataCollectionConfigs.length > 0 && (
            <div className="mb-4 max-h-64 overflow-auto rounded border text-sm" style={{ borderColor: theme === 'dark' ? '#475569' : '#e2e8f0' }}>
              <table className="w-full text-xs sm:text-sm">
                <thead>
                  <tr>
                    <th className="p-2 text-left">asset_code</th>
                    <th className="p-2 text-left">asset_name</th>
                    <th className="p-2 text-left">adapter_id</th>
                    <th className="p-2 text-left">adapter_account</th>
                    <th className="p-2 text-left">acq_interval_min</th>
                    <th className="p-2 text-left">enabled</th>
                    <th className="p-2 text-left">config_summary</th>
                  </tr>
                </thead>
                <tbody>
                  {dataCollectionConfigs.map((cfg) => (
                    <tr key={cfg.id}>
                      <td className="p-2">{cfg.asset_code}</td>
                      <td className="p-2">
                        {allAssets.find((a) => a.asset_code === cfg.asset_code)?.asset_name || ''}
                      </td>
                      <td className="p-2">{cfg.adapter_id}</td>
                      <td className="p-2">{cfg.adapter_account_name || cfg.adapter_account_id}</td>
                      <td className="p-2">{cfg.acquisition_interval_minutes}</td>
                      <td className="p-2">{cfg.enabled ? 'yes' : 'no'}</td>
                      <td className="p-2">
                        {(cfg.config?.api_base_url || cfg.config?.api_url || cfg.config?.asset_id || cfg.config?.plant_id) ? (
                          <span>
                            {cfg.config.api_base_url || cfg.config.api_url || cfg.config.asset_id || cfg.config.plant_id}
                          </span>
                        ) : (
                          <span className="opacity-60">config JSON</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <div className="mt-2 mb-4 text-xs text-slate-500">
            You can open the full Data Collection UI from the main navigation to edit these configs.
          </div>
          <div className="mt-2 flex gap-2">
            <button type="button" onClick={() => setStep(2)} className="rounded border px-4 py-2" style={{ borderColor: theme === 'dark' ? '#475569' : '#cbd5e1' }}>Back</button>
            <button type="button" onClick={() => setStep(4)} className="rounded bg-blue-600 px-4 py-2 text-white">Next →</button>
          </div>
        </div>
      )}

      {/* Step 4: Devices */}
      {step === 4 && (
        <div className="rounded-xl border p-6" style={{ borderColor: theme === 'dark' ? '#475569' : '#e2e8f0', maxWidth: 720 }}>
          <h3 className="mb-4 text-lg font-semibold">Devices (CSV helper)</h3>
          <p className="mb-3 text-sm opacity-80">
            Select an adapter and account, choose one or more assets, then fetch devices (Fusion Solar, Laplace, etc.).
            Download <strong>provider raw samples</strong> to verify API payloads (multiple files when multiple assets
            or dataset types). The device table is read-only; use the CSV to adjust details offline and upload via the
            device_list tab.
          </p>
          <div className="mb-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
            <div>
              <label className="block text-sm font-medium">Adapter</label>
              <select
                value={deviceAdapterId}
                onChange={(e) => {
                  const v = e.target.value;
                  setDeviceAdapterId(v);
                  setDeviceAdapterAccountId('');
                  setDeviceAssets([]);
                  setDeviceAssetSelection([]);
                  setDeviceConfigsByAsset({});
                  setDevices([]);
                  setDevicesError(null);
                }}
                className="w-full rounded border bg-transparent px-2 py-1.5 text-sm"
                style={{ borderColor: theme === 'dark' ? '#475569' : '#cbd5e1' }}
              >
                {adapterIds.length ? (
                  adapterIds.map((id) => (
                    <option key={id} value={id}>
                      {id}
                    </option>
                  ))
                ) : (
                  <option value="fusion_solar">fusion_solar</option>
                )}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium">Adapter account</label>
              <select
                value={deviceAdapterAccountId === '' ? '' : String(deviceAdapterAccountId)}
                onChange={(e) => {
                  const v = e.target.value;
                  setDeviceAdapterAccountId(v ? Number(v) : '');
                }}
                className="w-full rounded border bg-transparent px-2 py-1.5 text-sm"
                style={{ borderColor: theme === 'dark' ? '#475569' : '#cbd5e1' }}
              >
                <option value="">Select account…</option>
                {adapterAccounts.map((acc) => (
                  <option key={acc.id} value={acc.id}>
                    {acc.name || acc.id}
                  </option>
                ))}
              </select>
              {adapterAccountsLoading && <p className="mt-1 text-xs opacity-70">Loading accounts…</p>}
              {adapterAccountsError && <p className="mt-1 text-xs text-red-500">{adapterAccountsError}</p>}
            </div>
            <div className="flex items-end">
              <button
                type="button"
                onClick={handleLoadAssetsForSelectedAccount}
                disabled={!deviceAdapterAccountId || devicesLoading}
                className="w-full rounded bg-slate-600 px-3 py-1.5 text-sm text-white disabled:opacity-50"
              >
                {devicesLoading ? 'Loading…' : 'Load assets'}
              </button>
            </div>
          </div>
          {deviceAssets.length > 0 && (
            <div className="mb-4 rounded border p-3 text-sm" style={{ borderColor: theme === 'dark' ? '#475569' : '#e2e8f0' }}>
              <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                <p className="text-sm font-medium">Assets with adapter config for this account</p>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={handleSelectAllDeviceAssets}
                    disabled={deviceAssets.length === 0 || deviceAssetSelection.length === deviceAssets.length}
                    className="rounded border border-blue-500 bg-white px-2 py-1 text-xs text-blue-600 disabled:opacity-50"
                  >
                    Select all
                  </button>
                  <button
                    type="button"
                    onClick={handleDeselectAllDeviceAssets}
                    disabled={deviceAssetSelection.length === 0}
                    className="rounded border border-slate-400 bg-white px-2 py-1 text-xs text-slate-600 disabled:opacity-50"
                  >
                    Deselect all
                  </button>
                </div>
              </div>
              <div className="max-h-40 space-y-1 overflow-auto">
                {deviceAssets.map((a) => (
                  <label key={a.asset_code} className="flex items-center gap-2 text-xs sm:text-sm">
                    <input
                      type="checkbox"
                      checked={deviceAssetSelection.includes(a.asset_code)}
                      onChange={() => handleToggleDeviceAsset(a.asset_code)}
                    />
                    <span>{a.asset_name} ({a.asset_code})</span>
                  </label>
                ))}
              </div>
            </div>
          )}
          {devicesError && (
            <div
              className="mb-3 rounded border border-red-300 bg-red-50 p-2 text-sm text-red-800 dark:border-red-900/60 dark:bg-red-950/40 dark:text-red-200"
              role="alert"
            >
              <strong>Device fetch error:</strong> {devicesError}
            </div>
          )}
          <div className="mb-3 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={handleFetchDevices}
              disabled={devicesLoading || !deviceAdapterAccountId || deviceAssetSelection.length === 0}
              className="rounded bg-slate-600 px-3 py-1.5 text-sm text-white disabled:opacity-50"
            >
              {devicesLoading ? 'Fetching devices…' : 'Fetch devices'}
            </button>
            <button
              type="button"
              onClick={handleDownloadProviderRawSamples}
              disabled={rawSamplesLoading || !deviceAdapterAccountId || deviceAssetSelection.length === 0}
              title="Downloads one or more files from the provider (CSV/XML) per asset and type where applicable."
              className="rounded border border-amber-600/80 bg-amber-50 px-3 py-1.5 text-sm text-amber-950 disabled:opacity-50 dark:bg-amber-950/40 dark:text-amber-100"
            >
              {rawSamplesLoading ? 'Preparing downloads…' : 'Download provider raw samples'}
            </button>
            {deviceAdapterId === 'laplaceid' && (
              <button
                type="button"
                onClick={handleDownloadLaplaceWhRawSamples}
                disabled={rawSamplesLoading || !deviceAdapterAccountId || deviceAssetSelection.length === 0}
                title="Downloads Laplace WH query raw CSV files."
                className="rounded border border-blue-600/80 bg-blue-50 px-3 py-1.5 text-sm text-blue-900 disabled:opacity-50 dark:bg-blue-950/40 dark:text-blue-100"
              >
                {rawSamplesLoading ? 'Preparing WH downloads…' : 'Download Laplace WH raw CSV'}
              </button>
            )}
          </div>
          {deviceAdapterId === 'solargis' && (
            <p className="mb-2 text-xs opacity-70">
              SolarGIS raw sample is the XML dataDelivery response (same request as ingestion). It does not increment the
              daily API counter in the app, but the provider may still bill the call.
            </p>
          )}
          {devices.length > 0 && (
            <div
              className="mb-4 max-h-60 overflow-auto rounded border"
              style={{ borderColor: theme === 'dark' ? '#475569' : '#e2e8f0' }}
            >
              <table className="w-full text-[11px] sm:text-xs">
                <thead>
                  <tr style={{ borderBottom: `1px solid ${theme === 'dark' ? '#475569' : '#e2e8f0'}` }}>
                    <th className="p-2 text-left">device_id</th>
                    <th className="p-2 text-left">device_name</th>
                    <th className="p-2 text-left">device_code</th>
                    <th className="p-2 text-left">device_type_id</th>
                    <th className="p-2 text-left">device_type</th>
                    <th className="p-2 text-left">parent_code</th>
                    <th className="p-2 text-left">country</th>
                    <th className="p-2 text-left">device_make</th>
                    <th className="p-2 text-left">device_model</th>
                    <th className="p-2 text-left">device_serial</th>
                    <th className="p-2 text-left">optimizer_no</th>
                    <th className="p-2 text-left">latitude</th>
                    <th className="p-2 text-left">longitude</th>
                    <th className="p-2 text-left">software_version</th>
                    <th className="p-2 text-left">device_source</th>
                    <th className="p-2 text-left">tilt_angle</th>
                    <th className="p-2 text-left">azimuth_angle</th>
                    <th className="p-2 text-left">type</th>
                  </tr>
                </thead>
                <tbody>
                  {devices.map((d, i) => (
                    <tr key={i} style={{ borderBottom: `1px solid ${theme === 'dark' ? '#334155' : '#f1f5f9'}` }}>
                      <td className="p-2">{d.device_id}</td>
                      <td className="p-2">{d.device_name}</td>
                      <td className="p-2">{d.device_code}</td>
                      <td className="p-2">{d.device_type_id}</td>
                      <td className="p-2">{d.device_type}</td>
                      <td className="p-2">{d.parent_code ?? d.asset_code}</td>
                      <td className="p-2">{d.country}</td>
                      <td className="p-2">{d.device_make}</td>
                      <td className="p-2">{d.device_model}</td>
                      <td className="p-2">{d.device_serial}</td>
                      <td className="p-2">{d.optimizer_no}</td>
                      <td className="p-2">{d.latitude}</td>
                      <td className="p-2">{d.longitude}</td>
                      <td className="p-2">{d.software_version}</td>
                      <td className="p-2">{d.device_source}</td>
                      <td className="p-2">{d.tilt_angle}</td>
                      <td className="p-2">{d.azimuth_angle}</td>
                      <td className="p-2">{d.source}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <div className="flex gap-2">
            {devices.length > 0 && (
              <button type="button" onClick={() => downloadDeviceCsv()} className="rounded bg-green-600 px-4 py-2 text-white">
                Download device CSV
              </button>
            )}
            {devices.length > 0 &&
              Array.from(
                new Set(
                  devices
                    .map((d) => (d.parent_code ?? d.asset_code ?? '').trim())
                    .filter((v) => !!v)
                )
              ).map((assetCode) => (
                <button
                  key={assetCode}
                  type="button"
                  onClick={() => downloadDeviceCsv(assetCode)}
                  className="rounded border border-emerald-600/80 bg-emerald-50 px-3 py-2 text-emerald-900 dark:bg-emerald-950/30 dark:text-emerald-100"
                >
                  Download {assetCode} CSV
                </button>
              ))}
            <button type="button" onClick={() => setStep(3)} className="rounded border px-4 py-2" style={{ borderColor: theme === 'dark' ? '#475569' : '#cbd5e1' }}>Back</button>
            <button type="button" onClick={() => setStep(5)} className="rounded bg-blue-600 px-4 py-2 text-white">Next →</button>
          </div>
        </div>
      )}

      {/* Step 5: PV modules */}
      {step === 5 && (
        <div className="rounded-xl border p-6" style={{ borderColor: theme === 'dark' ? '#475569' : '#e2e8f0', maxWidth: 560 }}>
          <h3 className="mb-4 text-lg font-semibold">PV modules</h3>
          <p className="mb-4 text-sm opacity-80">Link devices to module datasheets from the main <a href="/site-onboarding/" className="underline">Site Onboarding</a> → Device list / PV modules.</p>
          <div className="flex gap-2">
            <button type="button" onClick={() => setStep(4)} className="rounded border px-4 py-2" style={{ borderColor: theme === 'dark' ? '#475569' : '#cbd5e1' }}>Back</button>
            <button type="button" onClick={() => setStep(6)} className="rounded bg-blue-600 px-4 py-2 text-white">Next →</button>
          </div>
        </div>
      )}

      {/* Step 6: Budget (optional) */}
      {step === 6 && (
        <div className="rounded-xl border p-6" style={{ borderColor: theme === 'dark' ? '#475569' : '#e2e8f0', maxWidth: 560 }}>
          <h3 className="mb-4 text-lg font-semibold">Budget / IC budget (optional)</h3>
          <p className="mb-4 text-sm opacity-80">You can add budget values and IC budget from the main Site Onboarding → Budget values / IC budget. This step can be skipped.</p>
          <div className="flex gap-2">
            <button type="button" onClick={() => setStep(5)} className="rounded border px-4 py-2" style={{ borderColor: theme === 'dark' ? '#475569' : '#cbd5e1' }}>Back</button>
            <a href="/site-onboarding/" className="rounded bg-green-600 px-4 py-2 text-white">Finish and go to Site Onboarding</a>
          </div>
        </div>
      )}
    </div>
  );
}
