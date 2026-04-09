/**
 * Solar Pre-Feasibility v1 — Manual DC mode (no KMZ).
 * One row per site: Site name, Lat, Long, DC (kWp), Tilt, Module, Inverter, Soiling loss.
 * Uses backend /api/manual-dc-yield/ when available; falls back to client-side yield engine.
 */
import { useState, useCallback, useEffect, type ChangeEvent } from 'react';
import {
  Plus,
  Trash2,
  Download,
  Zap,
  Loader2,
  AlertTriangle,
  X,
} from 'lucide-react';
import {
  computePreFeasibility,
  buildTypicalMonthlyData,
  typicalMonthlyGhiKwhM2,
  type PreFeasibilityResult,
} from './lib/preFeasibilityCalculator';
import { engineeringToolsFetch, solarApiUrl, solargisApiUrl } from './lib/api';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { FormMultiSelect } from '@/components/ui/form-multi-select';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { translateGridName } from './lib/gridTermTranslations';

const LAT_MIN = -90;
const LAT_MAX = 90;
const LON_MIN = -180;
const LON_MAX = 180;

const GRID_COUNTRY = 'japan';

/** Row ids on LAN HTTP (non-secure origins): `crypto.randomUUID` is undefined. */
function newClientRowId(): string {
  const c = typeof globalThis !== 'undefined' ? globalThis.crypto : undefined;
  if (c && typeof c.randomUUID === 'function') {
    return c.randomUUID();
  }
  return `row-${Date.now()}-${Math.random().toString(36).slice(2, 11)}`;
}

function formatOneDecimal(value: number): string {
  if (!Number.isFinite(value)) return '0.0';
  return value.toFixed(1);
}

function validLatLng(lat: string, lng: string): boolean {
  const la = parseFloat(lat);
  const ln = parseFloat(lng);
  return !Number.isNaN(la) && !Number.isNaN(ln) && la >= LAT_MIN && la <= LAT_MAX && ln >= LON_MIN && ln <= LON_MAX;
}

function formatSubstationName(name: string | null | undefined): string {
  if (!name) return '';
  // Apply shared JP→EN translations first
  const translated = translateGridName(name) || name;
  // Normalize whitespace (remove newlines, collapse spaces) but keep full text
  return translated.replace(/[\r\n]+/g, ' ').replace(/\s+/g, ' ').trim();
}

/** Solargis monthly record (from POST solargis-monthly). */
interface SolargisRecord {
  month: string;
  ghi: number;
  dif: number;
  temp: number;
}

/** Module master record from API (pre-feasibility module-master). */
export interface ModuleMasterRecord {
  id: number;
  make: string;
  model: string;
  watt_peak: number;
  height_m?: number;
  width_m?: number;
  efficiency_pct: number;
  temp_coeff_pmax_pct: number;
}

/** Inverter master record from API (pre-feasibility inverter-master). */
export interface InverterMasterRecord {
  id: number;
  make: string;
  model: string;
  ac_capacity_kw: number;
  efficiency_pct: number;
}

export type ArrayConfig = '' | 'landscape' | 'portrait';

export interface SiteRow {
  id: string;
  siteName: string;
  lat: string;
  lng: string;
  dcCapacityKw: string;
  tiltDeg: string;
  moduleId: string;
  inverterId: string;
  arrayConfig: ArrayConfig;
  modulesInSeries: string;
  soilingLoss: string;
}

export interface SiteResult {
  siteName: string;
  lat: number;
  lng: number;
  result: PreFeasibilityResult;
  /** True when Solargis CSV was loaded for this row (display-only). */
  hasSolargis?: boolean;
}

function Badge({
  children,
  color,
}: {
  children: React.ReactNode;
  color: 'green' | 'amber' | 'red' | 'blue' | 'slate';
}) {
  const colors = {
    green: 'bg-emerald-100 text-emerald-700 border-emerald-200',
    amber: 'bg-amber-100 text-amber-700 border-amber-200',
    red: 'bg-red-100 text-red-700 border-red-200',
    blue: 'bg-blue-100 text-blue-700 border-blue-200',
    slate: 'bg-slate-100 text-slate-600 border-slate-200',
  };
  return (
    <span
      className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium border ${colors[color] ?? colors.slate}`}
    >
      {children}
    </span>
  );
}

function newSiteRow(id?: string): SiteRow {
  return {
    id: id ?? newClientRowId(),
    siteName: '',
    lat: '',
    lng: '',
    dcCapacityKw: '',
    tiltDeg: '25',
    moduleId: '',
    inverterId: '',
    arrayConfig: 'landscape',
    modulesInSeries: '',
    soilingLoss: '',
  };
}

function parseRow(row: SiteRow): {
  lat: number;
  lng: number;
  dcCapacityKw: number;
  tiltDeg: number;
  soilingLoss: number;
} | null {
  const lat = parseFloat(row.lat);
  const lng = parseFloat(row.lng);
  const dc = parseFloat(row.dcCapacityKw);
  const tilt = parseFloat(row.tiltDeg);
  const soiling = parseFloat(row.soilingLoss);
  if (Number.isNaN(lat) || Number.isNaN(lng) || Number.isNaN(dc) || dc <= 0) return null;
  if (lat < LAT_MIN || lat > LAT_MAX || lng < LON_MIN || lng > LON_MAX) return null;
  return {
    lat,
    lng,
    dcCapacityKw: dc,
    tiltDeg: Number.isNaN(tilt) ? 25 : Math.max(0, Math.min(90, tilt)),
    soilingLoss: Number.isNaN(soiling) || soiling < 0 ? 0 : Math.min(100, soiling),
  };
}

const SUMMARY_CSV_HEADERS = [
  'Total modules',
  'Total strings',
  'PV area (m²)',
  'Land area (m²)',
  'Land area (ha)',
  'GCR (%)',
  'Shadow loss (%)',
  'Bifacial gain (%)',
  'Temperature loss (%)',
  'No of Inverter/PCS',
  'DC/AC Ratio',
  'Annual Energy (MWh/year)',
  'Specific Yield (kWh/kWp/year)',
  'PR (%)',
] as const;

const SUMMARY_HEADER_TOOLTIPS: Record<(typeof SUMMARY_CSV_HEADERS)[number], string> = {
  'Total modules':
    'Number of PV modules: DC capacity (kWp) × 1000 ÷ module Wp (rounded to whole modules). Example: 1000 kWp × 1000 ÷ 550 Wp ≈ 1818 modules.',
  'Total strings':
    'Total modules divided by modules in series (string length). Example: 1818 modules ÷ 24 modules/string ≈ 76 strings.',
  'PV area (m²)':
    'Total module area = total modules × module length (m) × module width (m). Example: 1818 × 2.27 m × 1.13 m ≈ 4676 m².',
  'Land area (m²)':
    'PV area divided by Ground Coverage Ratio (GCR). Example: 4676 m² ÷ (40% ÷ 100) ≈ 11,690 m².',
  'Land area (ha)':
    'Land area (m²) ÷ 10,000. Example: 11,690 m² ÷ 10,000 ≈ 1.17 ha.',
  'GCR (%)':
    'Ground Coverage Ratio used when converting PV area to land area. Example: 4676 m² ÷ 11,690 m² ≈ 40%.',
  'Shadow loss (%)':
    'Near-shading + interrow shading loss applied on energy (Excel B54). Example: 3% shadow loss → annual energy × (1 − 0.03).',
  'Bifacial gain (%)':
    'Additional gain from bifacial modules (0% for monofacial). Example: 2% bifacial gain → annual energy × (1 + 0.02).',
  'Temperature loss (%)':
    'Loss from cell temperature using annual avg temp and GHI (Excel B56). Example: −10% temperature loss → annual energy × (1 − 0.10).',
  'No of Inverter/PCS':
    'Number of inverters = AC capacity ÷ inverter rating, rounded to whole units. Example: 800 kW ÷ 100 kW/inverter = 8 inverters.',
  'DC/AC Ratio':
    'Ratio of DC capacity (kWp) to AC capacity (kW). Example: 1000 kWp ÷ 800 kW = 1.25.',
  'Annual Energy (MWh/year)':
    'Sum of 12 monthly energies from the Manual DC yield engine. Example: (120 + 130 + … + 115) MWh ≈ 1500 MWh/year.',
  'Specific Yield (kWh/kWp/year)':
    'Annual energy (kWh) divided by DC capacity (kWp). Example: 1,500,000 kWh ÷ 1000 kWp = 1500 kWh/kWp/year.',
  'PR (%)':
    'Net PR after all loss factors (PR, mismatch, wiring, soiling, snow, etc.). Example: 0.85 × (1 − 0.03 shadow) × (1 − 0.02 wiring) × … ≈ 82%.',
};

function exportResultsToCsv(results: SiteResult[]): void {
  if (results.length === 0) return;
  const headers = [
    'Site Name',
    'Latitude',
    'Longitude',
    'DC Capacity (kWp)',
    'AC Capacity (kWac)',
    'Annual Energy (MWh)',
    'Specific Yield (kWh/kWp)',
    'Capacity Factor (%)',
    'Typical Annual GHI (kWh/m²)',
    ...SUMMARY_CSV_HEADERS,
    'TL Voltage (kV)',
    'Substation',
  ];
  const escapeCsv = (v: string | number): string => {
    const s = String(v);
    if (s.includes(',') || s.includes('"') || s.includes('\n') || s.includes('\r')) {
      return `"${s.replace(/"/g, '""')}"`;
    }
    return s;
  };
  const summaryToCells = (s: PreFeasibilityResult['summary']): (string | number)[] => {
    if (!s) return SUMMARY_CSV_HEADERS.map(() => '');
    return [
      s.total_modules,
      s.total_strings,
      s.pv_area_m2,
      s.land_area_m2,
      s.land_area_ha,
      s.gcr_pct,
      s.shadow_loss_pct,
      s.bifacial_gain_pct,
      s.temperature_loss_pct,
      s.num_inverters,
      s.dc_ac_ratio,
      s.annual_energy_mwh,
      s.specific_yield_kwh_per_kwp,
      s.performance_ratio_pct,
    ];
  };
  const rows = results.map((r) => {
    const base = [
      escapeCsv(r.siteName || `Site ${r.lat.toFixed(4)}, ${r.lng.toFixed(4)}`),
      r.lat,
      r.lng,
      r.result.dcCapacityKw,
      r.result.acCapacityKw,
      r.result.annualEnergyMwh,
      r.result.specificYieldKwhPerKwp,
      r.result.capacityFactorPercent,
      r.result.annualGhiKwhM2,
      ...summaryToCells(r.result.summary).map((v) => (v === '' ? '' : escapeCsv(v))),
    ];
    const tl = r.result.gridVoltageKv != null ? formatOneDecimal(r.result.gridVoltageKv) : '';
    const sub = r.result.gridSubstationName ? formatSubstationName(r.result.gridSubstationName) : '';
    return [...base, tl, sub ? escapeCsv(sub) : ''];
  });
  const csvContent = [headers.join(','), ...rows.map((row) => row.join(','))].join('\r\n');
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `solar-prefeasibility-results-${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

const DC_AC_RATIO = 1.25;

/** Defaults when module/inverter not selected (Manual DC spec). */
const DEFAULT_PR = 85;
const DEFAULT_INV_EFF = 98.5;
const DEFAULT_TEMP_COEFF = -0.4;

export default function SolarPreFeasibilityPage() {
  const [rows, setRows] = useState<SiteRow[]>(() => [newSiteRow()]);
  const [results, setResults] = useState<SiteResult[] | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [calculating, setCalculating] = useState(false);
  const [moduleMaster, setModuleMaster] = useState<ModuleMasterRecord[]>([]);
  const [inverterMaster, setInverterMaster] = useState<InverterMasterRecord[]>([]);
  const [mastersLoading, setMastersLoading] = useState(true);
  /** Per-row Solargis CSV data (rowId -> { records }). When set, calculations use this instead of typical weather. */
  const [rowSolargis, setRowSolargis] = useState<Record<string, { records: SolargisRecord[] } | null>>({});
  const [uploadingSolargisRowId, setUploadingSolargisRowId] = useState<string | null>(null);

  // Same pattern as Solar Insight (with KMZ) ModuleAssumptionsBlock: fetch module/inverter master
  useEffect(() => {
    let cancelled = false;
    setMastersLoading(true);
    (async () => {
      try {
        const [modRes, invRes] = await Promise.all([
          engineeringToolsFetch(solarApiUrl('api/pre-feasibility/module-master/')),
          engineeringToolsFetch(solarApiUrl('api/pre-feasibility/inverter-master/')),
        ]);
        if (!cancelled && modRes.ok) {
          const data = (await modRes.json()) as ModuleMasterRecord[];
          setModuleMaster(Array.isArray(data) ? data : []);
        }
        if (!cancelled && invRes.ok) {
          const data = (await invRes.json()) as InverterMasterRecord[];
          setInverterMaster(Array.isArray(data) ? data : []);
        }
      } catch {
        /* ignore */
      } finally {
        if (!cancelled) setMastersLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const addRow = useCallback(() => {
    setRows((prev) => [...prev, newSiteRow()]);
    setValidationError(null);
  }, []);

  const removeRow = useCallback((id: string) => {
    setRows((prev) => {
      const next = prev.filter((r) => r.id !== id);
      return next.length > 0 ? next : [newSiteRow()];
    });
    setRowSolargis((prev) => {
      const next = { ...prev };
      delete next[id];
      return next;
    });
    setValidationError(null);
    setResults(null);
  }, []);

  const handleSolargisUpload = useCallback(
    async (rowId: string, file: File | null, lat: number, lng: number) => {
      if (!file) return;
      setUploadingSolargisRowId(rowId);
      try {
        const formData = new FormData();
        formData.append('latitude', String(lat));
        formData.append('longitude', String(lng));
        formData.append('location', `${lat.toFixed(4)}, ${lng.toFixed(4)}`);
        formData.append('solargis_csv', file);
        const res = await engineeringToolsFetch(solargisApiUrl('solargis-monthly/'), { method: 'POST', body: formData });
        const data = await res.json().catch(() => null);
        if (res.ok && data?.records?.length >= 12) {
          setRowSolargis((prev) => ({ ...prev, [rowId]: { records: data.records.slice(0, 12) } }));
        } else {
          setValidationError(data?.detail || 'Invalid SolarGIS CSV or fewer than 12 monthly records.');
        }
      } catch (e) {
        setValidationError(e instanceof Error ? e.message : 'Failed to parse SolarGIS CSV.');
      } finally {
        setUploadingSolargisRowId(null);
      }
    },
    []
  );

  const openSolargisForRow = useCallback((lat: number, lng: number) => {
    const params = new URLSearchParams({
      center: `${lat},${lng},10`,
      location: `${lat},${lng}`,
    });
    window.open(`https://apps.solargis.com/prospect/map?${params.toString()}`, '_blank', 'noopener,noreferrer');
  }, []);

  const updateRow = useCallback((id: string, field: keyof SiteRow, value: string) => {
    setRows((prev) =>
      prev.map((r) => (r.id === id ? { ...r, [field]: value } : r))
    );
    setValidationError(null);
    setResults(null);
  }, []);

  const handleConfirmAndCalculate = useCallback(async () => {
    setValidationError(null);
    const parsed: {
      row: SiteRow;
      data: { lat: number; lng: number; dcCapacityKw: number; tiltDeg: number; soilingLoss: number };
    }[] = [];
    for (const row of rows) {
      const data = parseRow(row);
      if (!data) {
        setValidationError(
          `Invalid or incomplete data in one or more rows. Check Latitude (-90 to 90), Longitude (-180 to 180), and DC capacity (positive number).`
        );
        return;
      }
      parsed.push({ row, data });
    }

    setCalculating(true);
    const siteResults: SiteResult[] = [];

    for (const { row, data } of parsed) {
      const moduleId = row.moduleId ? parseInt(row.moduleId, 10) : 0;
      const inverterId = row.inverterId ? parseInt(row.inverterId, 10) : 0;
      const module = moduleMaster.find((m) => m.id === moduleId);
      const inverter = inverterMaster.find((i) => i.id === inverterId);
      const inverterEfficiency = inverter?.efficiency_pct ?? DEFAULT_INV_EFF;
      const tempCoefficient = module?.temp_coeff_pmax_pct ?? DEFAULT_TEMP_COEFF;

      const solargis = rowSolargis[row.id]?.records;
      const monthlyData =
        solargis && solargis.length >= 12
          ? solargis.slice(0, 12).map((r) => ({
              month: r.month,
              ghi: r.ghi,
              diffuse: r.ghi > 0 ? r.dif / r.ghi : 0.4,
              temperature: r.temp,
            }))
          : buildTypicalMonthlyData(data.lat);
      const modulesInSeries = row.modulesInSeries ? Math.max(1, parseInt(row.modulesInSeries, 10) || 0) : 0;
      const payload: Record<string, unknown> = {
        latitude: data.lat,
        longitude: data.lng,
        tilt: data.tiltDeg,
        azimuth: 0,
        albedo: 0.2,
        dc_capacity_kwp: data.dcCapacityKw,
        performance_ratio: DEFAULT_PR,
        inverter_efficiency: inverterEfficiency,
        temp_coefficient: tempCoefficient,
        mismatch_loss: 0,
        wiring_loss: 0,
        soiling_loss: data.soilingLoss,
        snow_loss: 0,
        degradation: 0,
        additional_loss: 0,
        monthly_data: monthlyData,
        grid_country: GRID_COUNTRY,
      };
      if (module?.watt_peak && module?.height_m != null && module?.width_m != null) {
        payload.module_wp = module.watt_peak;
        payload.module_length_m = module.height_m;
        payload.module_width_m = module.width_m;
        payload.modules_in_series = modulesInSeries || 24;
      }
      if (inverter?.ac_capacity_kw) {
        payload.inverter_capacity_kw = inverter.ac_capacity_kw;
      }

      try {
        const res = await engineeringToolsFetch(solarApiUrl('api/manual-dc-yield/'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        if (res.ok) {
          const apiResult = await res.json();
          const annualGhi = typicalMonthlyGhiKwhM2(data.lat).reduce(
            (a: number, b: number) => a + b,
            0
          );
          const summary = apiResult.summary as PreFeasibilityResult['summary'] | undefined;
          const gridVoltageKv =
            typeof apiResult.nearest_tl_voltage_kv === 'number'
              ? apiResult.nearest_tl_voltage_kv
              : apiResult.nearest_tl_voltage_kv != null
              ? Number(apiResult.nearest_tl_voltage_kv)
              : null;
          const gridSubstationName =
            typeof apiResult.substation_name === 'string' ? apiResult.substation_name : null;
          const result: PreFeasibilityResult = {
            dcCapacityKw: data.dcCapacityKw,
            acCapacityKw: summary?.ac_capacity_kw ?? Math.round((data.dcCapacityKw / DC_AC_RATIO) * 10) / 10,
            annualEnergyMwh: apiResult.annual_energy_mwh,
            specificYieldKwhPerKwp: apiResult.specific_yield_kwh_per_kwp,
            capacityFactorPercent: apiResult.capacity_factor_percent,
            monthlyTiltedKwhM2: [],
            monthlyEnergyMwh: apiResult.monthly_energy_mwh ?? [],
            annualGhiKwhM2: Math.round(annualGhi * 10) / 10,
            summary,
            gridVoltageKv: Number.isFinite(gridVoltageKv as number) ? (gridVoltageKv as number) : null,
            gridSubstationName,
          };
          siteResults.push({
            siteName: row.siteName.trim() || `Site ${data.lat.toFixed(4)}, ${data.lng.toFixed(4)}`,
            lat: data.lat,
            lng: data.lng,
            result,
            hasSolargis: !!rowSolargis[row.id]?.records,
          });
          continue;
        }
      } catch {
        // Fall through to client-side
      }

      const result = computePreFeasibility({
        latitude: data.lat,
        longitude: data.lng,
        dcCapacityKw: data.dcCapacityKw,
        tiltDeg: data.tiltDeg,
        azimuthDeg: 0,
        albedo: 0.2,
        performanceRatio: DEFAULT_PR,
        inverterEfficiencyPercent: inverterEfficiency,
        tempCoefficient,
        mismatchLoss: 0,
        wiringLoss: 0,
        soilingLoss: data.soilingLoss,
        snowLoss: 0,
        degradation: 0,
        additionalLoss: 0,
      });
      if (!result) {
        setValidationError('Calculation failed for one or more sites.');
        setCalculating(false);
        return;
      }
      siteResults.push({
        siteName: row.siteName.trim() || `Site ${data.lat.toFixed(4)}, ${data.lng.toFixed(4)}`,
        lat: data.lat,
        lng: data.lng,
        result,
        hasSolargis: !!rowSolargis[row.id]?.records,
      });
    }

    setCalculating(false);
    setResults(siteResults);
  }, [rows, moduleMaster, inverterMaster, rowSolargis]);

  const handleExportCsv = useCallback(() => {
    if (results && results.length > 0) exportResultsToCsv(results);
  }, [results]);

  return (
    <div
      data-solar-prefeasibility="v2"
      style={{ fontFamily: "'DM Sans', system-ui, sans-serif" }}
      className="bg-slate-50 min-h-screen p-4 md:p-5 flex flex-col"
    >
      <link
        href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap"
        rel="stylesheet"
      />

      {/* Page header — compact */}
      <div className="mb-4 flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-blue-600 to-sky-500 flex items-center justify-center shadow-sm shrink-0">
            <Zap className="w-3.5 h-3.5 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-slate-900 tracking-tight leading-tight">
              Solar Pre-Feasibility
            </h1>
            <p className="text-xs text-slate-500 leading-tight">
              Manual DC yield simulation — backend + client fallback
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Badge color="blue">v2 Enterprise</Badge>
          <Badge color="green">Backend + Client fallback</Badge>
        </div>
      </div>

      {/* Global error — dismissible */}
      {validationError && (
        <div
          role="alert"
          className="flex items-start gap-3 border border-red-300 bg-red-50 text-red-800 rounded-xl px-4 py-2.5 text-sm mb-4"
        >
          <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
          <span className="flex-1">{validationError}</span>
          <button
            type="button"
            onClick={() => setValidationError(null)}
            className="hover:opacity-70 transition-opacity"
            aria-label="Dismiss"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      <main className="flex-1 min-w-0">
        <div className="relative overflow-hidden bg-white rounded-2xl border border-slate-200 shadow-sm mb-4">
          <div className="absolute inset-x-0 top-0 h-[3px] bg-gradient-to-r from-blue-600 via-blue-500 to-sky-400 rounded-t-2xl" />
          <div className="p-4 pt-5 flex flex-col gap-4">
            <div className="flex items-center justify-between gap-2 flex-wrap pb-2 border-b border-slate-100">
              <div className="flex items-center gap-3">
                <div className="h-5 w-1 bg-blue-600 rounded-full" />
                <span className="text-base font-semibold text-slate-800">Sites</span>
                <span className="text-xs text-slate-400">
                  {rows.length} site{rows.length !== 1 ? 's' : ''}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <Button type="button" variant="outline" size="sm" onClick={addRow}>
                  <Plus className="h-4 w-4 mr-1" />
                  Add site
                </Button>
                <Button
                  type="button"
                  onClick={handleConfirmAndCalculate}
                  disabled={calculating}
                  aria-busy={calculating}
                  size="sm"
                  className="h-8 rounded-lg bg-gradient-to-r from-blue-600 to-blue-500 text-white text-sm font-semibold shadow-md hover:shadow-lg transition-all duration-200 flex items-center justify-center gap-1.5 px-4 whitespace-nowrap"
                >
                  {calculating ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      <span>Running…</span>
                    </>
                  ) : (
                    <>
                      <Zap className="h-4 w-4" />
                      <span>Run Yield Simulation</span>
                    </>
                  )}
                </Button>
              </div>
            </div>

              <div className="overflow-x-auto scrollbar-thin scrollbar-thumb-slate-300 scrollbar-track-transparent relative">
                <div className="pointer-events-none absolute inset-y-0 left-0 w-6 bg-gradient-to-r from-white to-transparent" />
                <div className="pointer-events-none absolute inset-y-0 right-0 w-6 bg-gradient-to-l from-white to-transparent" />
                <table className="w-full text-xs border-collapse">
                  <thead className="bg-slate-100 sticky top-0 z-10">
                    <tr className="text-[11px] uppercase tracking-wide text-slate-700 font-semibold">
                      <th className="text-left px-2 py-2 whitespace-nowrap border border-slate-300">Site name</th>
                      <th className="text-left px-2 py-2 whitespace-nowrap border border-slate-300">Lat</th>
                      <th className="text-left px-2 py-2 whitespace-nowrap border border-slate-300">Long</th>
                      <th className="text-left px-2 py-2 whitespace-nowrap border border-slate-300">DC (kWp)</th>
                      <th className="text-left px-2 py-2 whitespace-nowrap border border-slate-300">Tilt (°)</th>
                      <th className="text-left px-2 py-2 whitespace-nowrap border border-slate-300">Module</th>
                      <th className="text-left px-2 py-2 whitespace-nowrap border border-slate-300">Inverter</th>
                      <th className="text-left px-2 py-2 whitespace-nowrap border border-slate-300">Array config</th>
                      <th className="text-left px-2 py-2 whitespace-nowrap border border-slate-300">Modules in series</th>
                      <th className="text-left px-2 py-2 whitespace-nowrap border border-slate-300">Soiling loss (%)</th>
                      <th className="text-left px-2 py-2 whitespace-nowrap border border-slate-300">Solargis</th>
                      <th className="w-10 px-2 py-2 border border-slate-300" />
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((row) => (
                      <tr
                        key={row.id}
                        className="bg-white even:bg-slate-50 hover:bg-blue-50 transition-colors duration-200"
                      >
                        <td className="border border-slate-300 px-2 py-2">
                          <Input
                            placeholder="Optional"
                            value={row.siteName}
                            onChange={(e: ChangeEvent<HTMLInputElement>) => updateRow(row.id, 'siteName', e.target.value)}
                            className="h-8 rounded-lg border border-slate-300 px-2 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition min-w-[120px]"
                          />
                        </td>
                        <td className="border border-slate-300 px-2 py-2">
                          <Input
                            type="number"
                            step="any"
                            placeholder="e.g. 35.68"
                            value={row.lat}
                            onChange={(e: ChangeEvent<HTMLInputElement>) => updateRow(row.id, 'lat', e.target.value)}
                            className="h-8 rounded-lg border border-slate-300 px-2 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition w-24"
                          />
                        </td>
                        <td className="border border-slate-300 px-2 py-2">
                          <Input
                            type="number"
                            step="any"
                            placeholder="e.g. 139.69"
                            value={row.lng}
                            onChange={(e: ChangeEvent<HTMLInputElement>) => updateRow(row.id, 'lng', e.target.value)}
                            className="h-8 rounded-lg border border-slate-300 px-2 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition w-24"
                          />
                        </td>
                        <td className="border border-slate-300 px-2 py-2">
                          <Input
                            type="number"
                            min="0"
                            step="0.1"
                            placeholder="e.g. 1000"
                            value={row.dcCapacityKw}
                            onChange={(e: ChangeEvent<HTMLInputElement>) => updateRow(row.id, 'dcCapacityKw', e.target.value)}
                            className="h-8 rounded-lg border border-slate-300 px-2 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition w-24"
                          />
                        </td>
                        <td className="border border-slate-300 px-2 py-2">
                          <Input
                            type="number"
                            min="0"
                            max="90"
                            value={row.tiltDeg}
                            onChange={(e: ChangeEvent<HTMLInputElement>) => updateRow(row.id, 'tiltDeg', e.target.value)}
                            className="h-8 rounded-lg border border-slate-300 px-2 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition w-16"
                          />
                        </td>
                        <td className="border border-slate-300 px-2 py-2 min-w-[200px]">
                          <FormMultiSelect
                            label=""
                            options={
                              mastersLoading || moduleMaster.length === 0
                                ? []
                                : [
                                    { value: '', label: '— Select module —' },
                                    ...moduleMaster.map((m) => ({
                                      value: String(m.id),
                                      label: `${m.make} — ${m.model} (${m.watt_peak} Wp)`,
                                    })),
                                  ]
                            }
                            selected={row.moduleId ? [row.moduleId] : []}
                            onChange={(vals) => updateRow(row.id, 'moduleId', vals[0] ?? '')}
                            placeholder={mastersLoading ? 'Loading…' : moduleMaster.length === 0 ? 'No modules available' : 'Select module'}
                            disabled={mastersLoading}
                            singleSelect
                            className="gap-0 [&>label]:hidden text-xs"
                          />
                        </td>
                        <td className="border border-slate-300 px-2 py-2 min-w-[200px]">
                          <FormMultiSelect
                            label=""
                            options={
                              mastersLoading || inverterMaster.length === 0
                                ? []
                                : [
                                    { value: '', label: '— Select inverter —' },
                                    ...inverterMaster.map((i) => ({
                                      value: String(i.id),
                                      label: `${i.make} — ${i.model} (${i.ac_capacity_kw} kW)`,
                                    })),
                                  ]
                            }
                            selected={row.inverterId ? [row.inverterId] : []}
                            onChange={(vals) => updateRow(row.id, 'inverterId', vals[0] ?? '')}
                            placeholder={mastersLoading ? 'Loading…' : inverterMaster.length === 0 ? 'No inverters available' : 'Select inverter'}
                            disabled={mastersLoading}
                            singleSelect
                            className="gap-0 [&>label]:hidden text-xs"
                          />
                        </td>
                        <td className="border border-slate-300 px-2 py-2">
                          <FormMultiSelect
                            label=""
                            options={[
                              { value: 'landscape', label: 'Landscape' },
                              { value: 'portrait', label: 'Portrait' },
                            ]}
                            selected={row.arrayConfig ? [row.arrayConfig] : ['landscape']}
                            onChange={(vals) =>
                              updateRow(row.id, 'arrayConfig', vals[0] === 'portrait' ? 'portrait' : 'landscape')
                            }
                            placeholder="Array config"
                            singleSelect
                            className="gap-0 [&>label]:hidden text-xs"
                          />
                        </td>
                        <td className="border border-slate-300 px-2 py-2">
                          <Input
                            type="number"
                            min="1"
                            step="1"
                            placeholder="e.g. 24"
                            value={row.modulesInSeries ?? ''}
                            onChange={(e: ChangeEvent<HTMLInputElement>) => updateRow(row.id, 'modulesInSeries', e.target.value)}
                            className="h-8 rounded-lg border border-slate-300 px-2 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition w-20"
                          />
                        </td>
                        <td className="border border-slate-300 px-2 py-2">
                          <Input
                            type="number"
                            min="0"
                            max="100"
                            step="0.1"
                            placeholder="0"
                            value={row.soilingLoss}
                            onChange={(e: ChangeEvent<HTMLInputElement>) => updateRow(row.id, 'soilingLoss', e.target.value)}
                            className="h-8 rounded-lg border border-slate-300 px-2 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition w-20"
                          />
                        </td>
                        <td className="border border-slate-300 px-2 py-2 align-top">
                          <div className="flex flex-col gap-1">
                            {validLatLng(row.lat, row.lng) ? (
                              <Button
                                type="button"
                                variant="link"
                                className="h-auto p-0 text-xs font-medium text-blue-600"
                                onClick={() => openSolargisForRow(Number(row.lat), Number(row.lng))}
                              >
                                Open Solargis
                              </Button>
                            ) : (
                              <span className="text-xs text-slate-500">Enter lat/long</span>
                            )}
                            <label className="flex items-center gap-1 cursor-pointer text-xs text-slate-600">
                              <input
                                type="file"
                                accept=".csv"
                                className="text-xs w-32 file:mr-1 file:rounded-lg file:border file:border-slate-300 file:bg-slate-50 file:px-2 file:py-1 file:text-xs file:text-slate-700 hover:file:bg-slate-100"
                                disabled={!validLatLng(row.lat, row.lng) || uploadingSolargisRowId === row.id}
                                onChange={(e: ChangeEvent<HTMLInputElement>) => {
                                  const f = e.target.files?.[0];
                                  if (f && validLatLng(row.lat, row.lng))
                                    handleSolargisUpload(row.id, f, Number(row.lat), Number(row.lng));
                                  e.target.value = '';
                                }}
                              />
                              <span className="text-xs text-slate-500">
                                {uploadingSolargisRowId === row.id ? 'Uploading…' : rowSolargis[row.id] ? '✓ CSV loaded' : 'Upload CSV'}
                              </span>
                            </label>
                          </div>
                        </td>
                        <td className="border border-slate-300 px-2 py-2">
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 text-slate-400 hover:text-red-600"
                            onClick={() => removeRow(row.id)}
                            title="Remove row"
                            aria-label={row.siteName ? `Remove ${row.siteName}` : 'Remove row'}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          {results && results.length > 0 && (
            <div
              className="relative overflow-hidden bg-white rounded-2xl border border-slate-200 shadow-sm mb-4"
              style={{ animation: 'fadeSlideUp 0.3s ease' }}
            >
              <style>{`@keyframes fadeSlideUp { from { opacity:0; transform:translateY(8px) } to { opacity:1; transform:translateY(0) } }`}</style>
              <div className="absolute inset-x-0 top-0 h-[3px] bg-gradient-to-r from-emerald-500 via-green-500 to-teal-400 rounded-t-2xl" />
              <div className="p-4 pt-5 flex flex-col gap-4">
                <div className="flex items-center justify-between gap-2 flex-wrap pb-2 border-b border-slate-100">
                  <div className="flex items-center gap-3">
                    <div className="h-5 w-1 bg-emerald-500 rounded-full" />
                    <span className="text-base font-semibold text-slate-800">Results</span>
                    <span className="text-xs text-slate-400">
                      {results.length} site{results.length !== 1 ? 's' : ''}
                    </span>
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={handleExportCsv}
                    aria-label="Export results to CSV"
                  >
                    <Download className="h-4 w-4 mr-1" />
                    Export CSV
                  </Button>
                </div>

                <TooltipProvider>
                  <div className="overflow-x-auto scrollbar-thin scrollbar-thumb-slate-300 scrollbar-track-transparent relative">
                    <div className="pointer-events-none absolute inset-y-0 left-0 w-6 bg-gradient-to-r from-white to-transparent" />
                    <div className="pointer-events-none absolute inset-y-0 right-0 w-6 bg-gradient-to-l from-white to-transparent" />
                    <table className="w-full text-xs border-collapse">
                      <thead className="bg-slate-100 sticky top-0 z-10">
                        <tr className="text-[11px] uppercase tracking-wide text-slate-700 font-semibold">
                          <th className="text-left px-2 py-2 whitespace-nowrap sticky left-0 bg-white z-10 border border-slate-300">
                            Site
                          </th>
                          <th className="text-right px-2 py-2 whitespace-nowrap border border-slate-300">DC (kWp)</th>
                          <th className="text-right px-2 py-2 whitespace-nowrap border border-slate-300">AC (kWac)</th>
                          <th className="text-right px-2 py-2 whitespace-nowrap border border-slate-300">Annual (MWh)</th>
                          <th className="text-right px-2 py-2 whitespace-nowrap border border-slate-300">Yield (kWh/kWp)</th>
                          <th className="text-right px-2 py-2 whitespace-nowrap border border-slate-300">CUF (%)</th>
                          <th className="text-right px-2 py-2 whitespace-nowrap border border-slate-300">GHI (kWh/m²)</th>
                          {SUMMARY_CSV_HEADERS.map((h) => {
                            const tip = SUMMARY_HEADER_TOOLTIPS[h];
                            return (
                              <th
                                key={h}
                                className="text-right px-2 py-2 whitespace-nowrap border border-slate-300"
                              >
                                {tip ? (
                                  <Tooltip>
                                    <TooltipTrigger className="cursor-help underline decoration-dotted underline-offset-2">
                                      {h}
                                    </TooltipTrigger>
                                    <TooltipContent className="max-w-md text-left whitespace-normal break-words">
                                      {tip}
                                    </TooltipContent>
                                  </Tooltip>
                                ) : (
                                  h
                                )}
                              </th>
                            );
                          })}
                          <th className="text-right px-2 py-2 whitespace-nowrap border border-slate-300">
                            TL Voltage (kV)
                          </th>
                          <th className="text-left px-2 py-2 whitespace-nowrap border border-slate-300 min-w-[180px]">
                            Substation
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {results.map((r, idx) => {
                          const s = r.result.summary;
                          const cuf = r.result.capacityFactorPercent;
                          const pr = s?.performance_ratio_pct ?? null;
                          const dcAc = s?.dc_ac_ratio ?? null;
                          const tempLoss = s?.temperature_loss_pct ?? null;

                          const formattedSubstation = r.result.gridSubstationName
                            ? formatSubstationName(r.result.gridSubstationName) ||
                              r.result.gridSubstationName
                            : '';

                          return (
                            <tr
                              key={`${r.siteName}-${r.lat}-${r.lng}-${idx}`}
                              className="bg-white even:bg-slate-50 hover:bg-blue-50 transition-colors duration-200"
                            >
                              <td className="px-2 py-2 border border-slate-200 font-medium sticky left-0 z-10 bg-inherit">
                                <div className="flex items-center gap-1.5">
                                  {r.siteName}
                                  {r.hasSolargis && <Badge color="blue">SolarGIS</Badge>}
                                </div>
                              </td>
                              <td className="px-2 py-2 border border-slate-200 text-right tabular-nums">
                                {r.result.dcCapacityKw.toLocaleString()}
                              </td>
                              <td className="px-2 py-2 border border-slate-200 text-right tabular-nums">
                                {r.result.acCapacityKw.toLocaleString()}
                              </td>
                              <td className="px-2 py-2 border border-slate-200 text-right tabular-nums font-medium">
                                {formatOneDecimal(r.result.annualEnergyMwh)}
                              </td>
                              <td className="px-2 py-2 border border-slate-200 text-right tabular-nums">
                                {formatOneDecimal(r.result.specificYieldKwhPerKwp)}
                              </td>
                              <td className="px-2 py-2 border border-slate-200 text-right tabular-nums">
                                <span
                                  className={
                                    cuf > 18
                                      ? 'text-emerald-600 font-semibold'
                                      : 'text-slate-700'
                                  }
                                  aria-label={cuf > 18 ? `CUF ${formatOneDecimal(cuf)}% — above target` : undefined}
                                >
                                  {formatOneDecimal(cuf)}
                                </span>
                              </td>
                              <td className="px-2 py-2 border border-slate-200 text-right tabular-nums">
                                {formatOneDecimal(r.result.annualGhiKwhM2)}
                              </td>
                              <td className="px-2 py-2 border border-slate-300 text-right tabular-nums">
                                {s?.total_modules != null ? s.total_modules.toLocaleString() : '—'}
                              </td>
                              <td className="px-2 py-2 border border-slate-300 text-right tabular-nums">
                                {s?.total_strings != null ? s.total_strings.toLocaleString() : '—'}
                              </td>
                              <td className="px-2 py-2 border border-slate-300 text-right tabular-nums">
                                {s?.pv_area_m2 != null ? s.pv_area_m2.toLocaleString() : '—'}
                              </td>
                              <td className="px-2 py-2 border border-slate-300 text-right tabular-nums">
                                {s?.land_area_m2 != null ? s.land_area_m2.toLocaleString() : '—'}
                              </td>
                              <td className="px-2 py-2 border border-slate-300 text-right tabular-nums">
                                {s?.land_area_ha != null ? s.land_area_ha.toLocaleString() : '—'}
                              </td>
                              <td className="px-2 py-2 border border-slate-300 text-right tabular-nums">
                                {s?.gcr_pct != null ? `${formatOneDecimal(s.gcr_pct)}%` : '—'}
                              </td>
                              <td className="px-2 py-2 border border-slate-300 text-right tabular-nums">
                                {s?.shadow_loss_pct != null ? `${s.shadow_loss_pct}%` : '—'}
                              </td>
                              <td className="px-2 py-2 border border-slate-300 text-right tabular-nums">
                                {s?.bifacial_gain_pct != null ? `${s.bifacial_gain_pct}%` : '—'}
                              </td>
                              <td className="px-2 py-2 border border-slate-300 text-right tabular-nums">
                                {tempLoss != null ? (
                                  <span
                                    className={
                                      tempLoss < -12 ? 'text-red-600 font-medium' : ''
                                    }
                                  >
                                    {`${formatOneDecimal(tempLoss)}%`}
                                  </span>
                                ) : (
                                  '—'
                                )}
                              </td>
                              <td className="px-2 py-2 border border-slate-300 text-right tabular-nums">
                                {s?.num_inverters != null ? s.num_inverters.toLocaleString() : '—'}
                              </td>
                              <td className="px-2 py-2 border border-slate-300 text-right tabular-nums">
                                {dcAc != null ? (
                                  <span
                                    className={
                                      dcAc > 1.35 ? 'text-amber-600 font-medium' : ''
                                    }
                                    aria-label={
                                      dcAc > 1.35
                                        ? `DC/AC ${formatOneDecimal(dcAc)} — high`
                                        : undefined
                                    }
                                  >
                                    {formatOneDecimal(dcAc)}
                                  </span>
                                ) : (
                                  '—'
                                )}
                              </td>
                              <td className="px-2 py-2 border border-slate-300 text-right tabular-nums">
                                {s?.annual_energy_mwh != null
                                  ? formatOneDecimal(s.annual_energy_mwh)
                                  : '—'}
                              </td>
                              <td className="px-2 py-2 border border-slate-300 text-right tabular-nums">
                                {s?.specific_yield_kwh_per_kwp != null
                                  ? formatOneDecimal(s.specific_yield_kwh_per_kwp)
                                  : '—'}
                              </td>
                              <td className="px-2 py-2 border border-slate-300 text-right tabular-nums">
                                {pr != null ? (
                                  <span
                                    className={
                                      pr > 82
                                        ? 'text-emerald-600 font-semibold'
                                        : 'text-slate-700'
                                    }
                                    aria-label={
                                      pr > 82
                                        ? `PR ${formatOneDecimal(pr)}% — above target`
                                        : undefined
                                    }
                                  >
                                    {`${formatOneDecimal(pr)}%`}
                                  </span>
                                ) : (
                                  '—'
                                )}
                              </td>
                              <td className="px-2 py-2 border border-slate-200 text-right tabular-nums">
                                {r.result.gridVoltageKv != null
                                  ? formatOneDecimal(r.result.gridVoltageKv)
                                  : '—'}
                              </td>
                              <td className="px-2 py-2 border border-slate-200 text-left text-slate-700 max-w-[180px] truncate">
                                {formattedSubstation || '—'}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </TooltipProvider>

                {/* Colour legend */}
                <div className="flex items-center gap-4 pt-1 text-xs text-slate-500 flex-wrap">
                  <span className="font-medium text-slate-700">Colour legend:</span>
                  <span className="flex items-center gap-1.5">
                    <span className="w-3 h-3 rounded-sm bg-emerald-100 border border-emerald-300 inline-block" />{' '}
                    Good (CUF &gt;18%, PR &gt;82%)
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span className="w-3 h-3 rounded-sm bg-amber-100 border border-amber-300 inline-block" />{' '}
                    Warning (DC/AC &gt;1.35)
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span className="w-3 h-3 rounded-sm bg-red-100 border border-red-300 inline-block" />{' '}
                    High temp loss (&lt;−12%)
                  </span>
                </div>
              </div>
            </div>
          )}
        </main>
    </div>
  );
}
