/**
 * Export PV Array Layout KML — uses parameters from Engineering tab
 * and boundary KML from File Upload tab. Table Width = Array Projection Length (m).
 */
import { useState, useCallback, type ChangeEvent } from 'react';
import { Download, ArrowRight } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { engineeringToolsFetch, solarApiUrl } from '../lib/api';
import { translateGridName } from '../lib/gridTermTranslations';
import type { SystemConfigLayoutParams } from './SystemConfigurationBlock';

interface ExportLayoutKmlBlockProps {
  location: { lat: number; lng: number } | null;
  boundaryKmlFile: File | null;
  layoutParams: SystemConfigLayoutParams | null;
  inverterRatedPowerKw?: number | null;
  onKpiResultsChange?: (kpi: KpiResults) => void;
}

export interface KpiResults {
  full_tables: number;
  half_tables: number;
  quarter_tables: number;
  full_dc_kwp: number;
  half_dc_kwp: number;
  quarter_dc_kwp: number;
  total_dc_kwp: number;
  total_modules: number;
  table_count: number;
  land_area_m2: number;
  interrow_spacing_m?: number;
  nearest_tl_voltage_kv?: number;
  distance_to_line_m?: number;
  substation_name?: string;
  line_name?: string;
  distance_to_substation_m?: number;
  grid_connectivity?: Record<string, unknown>;
  grid_connectivity_error?: string;
}

export default function ExportLayoutKmlBlock({
  location,
  boundaryKmlFile,
  layoutParams,
  inverterRatedPowerKw: inverterRatedPowerKwProp,
  onKpiResultsChange,
}: ExportLayoutKmlBlockProps) {
  const effectiveBoundaryFile = boundaryKmlFile;
  const [open, setOpen] = useState(true);
  const [loading, setLoading] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const [kpiResults, setKpiResults] = useState<KpiResults | null>(null);
  const [country, setCountry] = useState<string>('japan');

  const ensureProject = useCallback(async (): Promise<number | null> => {
    if (!location) return null;
    const res = await engineeringToolsFetch(solarApiUrl('api/projects/'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ latitude: location.lat, longitude: location.lng }),
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error((data.detail as string) || 'Failed to get or create project');
    }
    const data = await res.json();
    return data.id as number;
  }, [location]);

  const canExport = ((): boolean => {
    if (!effectiveBoundaryFile || !location || !layoutParams) return false;
    if (!layoutParams.arrayConfig) return false;
    const n = parseInt(layoutParams.modulesInSeries, 10);
    if (Number.isNaN(n) || n < 1) return false;
    if (!layoutParams.tableLengthM || layoutParams.tableLengthM.trim() === '') return false;
    if (!layoutParams.arrayProjectionLengthM || layoutParams.arrayProjectionLengthM.trim() === '')
      return false;
    const row = parseFloat(layoutParams.interrowSpacingM);
    if (Number.isNaN(row) || row < 0) return false;
    const gap = parseFloat(layoutParams.structureGapM);
    if (Number.isNaN(gap) || gap < 0) return false;
    return true;
  })();

  const handleExport = async () => {
    setExportError(null);
    if (!effectiveBoundaryFile) {
      setExportError('Please upload a boundary KML file in the Site Inputs tab first.');
      return;
    }
    if (!layoutParams || !layoutParams.arrayConfig) {
      setExportError('Complete System Configuration in the Engineering tab.');
      return;
    }

    const pid = await ensureProject();
    if (pid == null) {
      setExportError('Could not get or create project for this location.');
      return;
    }

    const modulesInSeriesNum = parseInt(layoutParams.modulesInSeries, 10);
    const rowsPerTable =
      layoutParams.arrayConfig === 'portrait'
        ? 2
        : layoutParams.arrayConfig === 'landscape'
          ? 4
          : 1;
    const modulesPerFullTable =
      Number.isNaN(modulesInSeriesNum) || modulesInSeriesNum < 1
        ? layoutParams.modulesInSeries.trim()
        : String(modulesInSeriesNum * rowsPerTable);

    const form = new FormData();
    form.append('boundary_kml', effectiveBoundaryFile);
    form.append('project_id', String(pid));
    form.append('array_config', layoutParams.arrayConfig);
    form.append('modules_per_table', modulesPerFullTable);
    form.append('table_length_m', layoutParams.tableLengthM.trim());
    form.append('table_width_m', layoutParams.arrayProjectionLengthM.trim());
    form.append('row_spacing_m', layoutParams.interrowSpacingM.trim());
    form.append('structure_gap_m', layoutParams.structureGapM.trim());
    form.append(
      'boundary_offset_m',
      layoutParams.boundarySetbackM.trim() === '' ? '0' : layoutParams.boundarySetbackM.trim()
    );
    if (country.trim()) {
      form.append('country', country.trim().toLowerCase());
    }

    setLoading(true);
    try {
      const res = await engineeringToolsFetch(solarApiUrl('api/pre-feasibility/export-layout-kml/'), {
        method: 'POST',
        body: form,
      });

      if (!res.ok) {
        const text = await res.text();
        let msg = text;
        try {
          const j = JSON.parse(text) as { detail?: string };
          if (j.detail) msg = j.detail;
        } catch {
          /* use text */
        }
        setExportError(msg);
        return;
      }

      const summaryHeader = res.headers.get('X-Export-Summary');
      if (summaryHeader) {
        try {
          const summary = JSON.parse(summaryHeader) as KpiResults;
          setKpiResults(summary);
          onKpiResultsChange?.(summary);
        } catch {
          /* ignore */
        }
      }

      const blob = await res.blob();
      const name =
        res.headers.get('Content-Disposition')?.match(/filename="?([^";]+)"?/)?.[1] ||
        'PV_Array_Layout.kmz';
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = name;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setExportError(e instanceof Error ? e.message : 'Export failed');
    } finally {
      setLoading(false);
    }
  };

  const hasBoundary = !!effectiveBoundaryFile;
  const hasEngineeringConfig = !!(layoutParams && layoutParams.arrayConfig);
  const hasGridSelected = country.trim() !== '';

  return (
    <div className="rounded-xl bg-slate-50 border border-gray-200/80 overflow-hidden">
      <Card className="border-0 bg-transparent shadow-none">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 py-2 px-4">
          <CardTitle className="text-sm font-semibold tracking-tight text-gray-900">
            Export PV Array Layout (KML)
          </CardTitle>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => setOpen((prev) => !prev)}
            aria-label={open ? 'Collapse export section' : 'Expand export section'}
            className="text-lg leading-none px-2"
          >
            {open ? '˄' : '˅'}
          </Button>
        </CardHeader>
        {open && (
          <CardContent className="space-y-4 pt-2 px-4 pb-4">
            {/* Status indicators */}
            <div className="flex flex-wrap gap-2">
              <span
                className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium ${
                  hasBoundary ? 'bg-emerald-100 text-emerald-800' : 'bg-gray-100 text-gray-500'
                }`}
              >
                {hasBoundary ? '✔' : '○'} Boundary Loaded
              </span>
              <span
                className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium ${
                  hasEngineeringConfig ? 'bg-emerald-100 text-emerald-800' : 'bg-gray-100 text-gray-500'
                }`}
              >
                {hasEngineeringConfig ? '✔' : '○'} Engineering Config Available
              </span>
              <span
                className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium ${
                  hasGridSelected ? 'bg-emerald-100 text-emerald-800' : 'bg-gray-100 text-gray-500'
                }`}
              >
                {hasGridSelected ? '✔' : '○'} Grid Network Selected
              </span>
            </div>

            {/* Configuration + Parameters Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Grid Connectivity card */}
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
                <h3 className="text-sm font-semibold text-gray-900 mb-3">🗺 Grid Connectivity</h3>
                <Label htmlFor="grid-country" className="text-sm text-gray-500">
                  Grid network (for nearest TL & substation)
                </Label>
                <select
                  id="grid-country"
                  value={country}
                  onChange={(e: ChangeEvent<HTMLSelectElement>) => setCountry(e.target.value)}
                  className="mt-2 flex h-9 w-full max-w-[240px] rounded-md border border-gray-200 bg-white px-3 py-1 text-sm shadow-sm"
                >
                  <option value="">Skip grid analysis</option>
                  <option value="japan">Japan</option>
                  <option value="korea">Korea</option>
                  <option value="singapore">Singapore</option>
                </select>
                <p className="mt-3 text-sm text-gray-500">
                  When selected, the export KMZ includes the nearest transmission line and substation,
                  and KPI results show voltage level and line length. Requires KMZ files in{' '}
                  <code className="text-xs">engineering_tools/grid_network/{'{country}'}/</code>. Set{' '}
                  <code className="text-xs">GRID_NETWORK_DATA_ROOT</code> in .env to point to
                  solar-insight&apos;s data folder if sharing.
                </p>
              </div>

              {/* Parameters from Engineering card */}
              {layoutParams && layoutParams.arrayConfig && (
                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
                  <h3 className="text-sm font-semibold text-gray-900 mb-3">
                    Parameters from Engineering
                  </h3>
                  <div className="grid grid-cols-2 gap-x-4 gap-y-3 space-y-0">
                    <div className="space-y-0.5">
                      <p className="text-sm text-gray-500">Array configuration</p>
                      <p className="font-semibold text-gray-800">{layoutParams.arrayConfig}</p>
                    </div>
                    <div className="space-y-0.5">
                      <p className="text-sm text-gray-500">Modules in series</p>
                      <p className="font-semibold text-gray-800">{layoutParams.modulesInSeries || '—'}</p>
                    </div>
                    <div className="space-y-0.5">
                      <p className="text-sm text-gray-500">Table length (m)</p>
                      <p className="font-semibold text-gray-800">{layoutParams.tableLengthM || '—'}</p>
                    </div>
                    <div className="space-y-0.5">
                      <p className="text-sm text-gray-500">Table width (m)</p>
                      <p className="font-semibold text-gray-800">{layoutParams.arrayProjectionLengthM || '—'}</p>
                    </div>
                    <div className="space-y-0.5">
                      <p className="text-sm text-gray-500">Interrow spacing (m)</p>
                      <p className="font-semibold text-gray-800">{layoutParams.interrowSpacingM || '—'}</p>
                    </div>
                    <div className="space-y-0.5">
                      <p className="text-sm text-gray-500">Structure gap (m)</p>
                      <p className="font-semibold text-gray-800">{layoutParams.structureGapM || '—'}</p>
                    </div>
                    <div className="space-y-0.5">
                      <p className="text-sm text-gray-500">Boundary setback (m)</p>
                      <p className="font-semibold text-gray-800">{layoutParams.boundarySetbackM || '0'}</p>
                    </div>
                    <div className="space-y-0.5">
                      <p className="text-sm text-gray-500">DC : AC ratio</p>
                      <p className="font-semibold text-gray-800">{layoutParams.dcAcRatio || '1.2'}</p>
                    </div>
                    <div className="col-span-2 space-y-0.5">
                      <p className="text-sm text-gray-500">Inverter rated power (kW)</p>
                      <p className="font-semibold text-gray-800">
                        {inverterRatedPowerKwProp != null
                          ? inverterRatedPowerKwProp
                          : '— (select inverter in DC String Configuration)'}
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {(!layoutParams || !layoutParams.arrayConfig) && (
              <p className="text-sm text-amber-600 dark:text-amber-400">
                Fill in the <strong>System Configuration</strong> block in the Engineering tab so
                layout parameters are available here.
              </p>
            )}

            {exportError && <p className="text-sm text-destructive">{exportError}</p>}
            {kpiResults?.grid_connectivity_error && (
              <p className="text-sm text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-3">
                Grid connectivity unavailable: {kpiResults.grid_connectivity_error}. Place KMZ files
                (e.g. <code>japan.kmz</code>) in <code>engineering_tools/grid_network/{country}/</code> or set{' '}
                <code>GRID_NETWORK_DATA_ROOT</code> in .env.
              </p>
            )}

            {/* Export Action Panel */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
              <div>
                <h3 className="text-sm font-semibold text-gray-900">Export Layout to Google Earth (KMZ)</h3>
                <p className="text-sm text-gray-500 mt-1">Includes boundary + PV tables</p>
              </div>
              <Button
                type="button"
                onClick={handleExport}
                disabled={loading || !canExport}
                className="bg-blue-600 hover:bg-blue-700 text-white rounded-lg shadow-sm px-6 py-3 font-medium transition-colors duration-150 shrink-0 flex items-center gap-2"
              >
                {loading ? 'Exporting…' : (
                  <>
                    Export KMZ <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </Button>
            </div>

            {kpiResults && (
            <div className="mt-4 bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden p-4">
              <h3 className="text-sm font-semibold text-gray-900 mb-3">KPI Results</h3>
              <div className="rounded-xl border border-gray-200 overflow-hidden bg-white shadow-sm">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-slate-800 text-white uppercase text-xs tracking-wider font-semibold">
                      <th className="text-left px-4 py-3">Category</th>
                      <th className="text-center px-4 py-3">Quantity</th>
                      <th className="text-right px-4 py-3">DC Capacity (kWp)</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr className="border-t border-gray-200 even:bg-gray-50 hover:bg-emerald-50 transition-colors duration-150">
                      <td className="px-4 py-3">Full Tables</td>
                      <td className="text-center px-4 py-3">{kpiResults.full_tables}</td>
                      <td className="text-right px-4 py-3 font-semibold text-gray-800">{kpiResults.full_dc_kwp.toLocaleString()}</td>
                    </tr>
                    <tr className="border-t border-gray-200 even:bg-gray-50 hover:bg-emerald-50 transition-colors duration-150">
                      <td className="px-4 py-3">Half Tables</td>
                      <td className="text-center px-4 py-3">{kpiResults.half_tables}</td>
                      <td className="text-right px-4 py-3 font-semibold text-gray-800">{kpiResults.half_dc_kwp.toLocaleString()}</td>
                    </tr>
                    <tr className="border-t border-gray-200 even:bg-gray-50 hover:bg-emerald-50 transition-colors duration-150">
                      <td className="px-4 py-3">Quarter Tables</td>
                      <td className="text-center px-4 py-3">{kpiResults.quarter_tables}</td>
                      <td className="text-right px-4 py-3 font-semibold text-gray-800">{kpiResults.quarter_dc_kwp.toLocaleString()}</td>
                    </tr>
                    <tr className="border-t border-gray-200 bg-slate-900 text-white font-semibold">
                      <td className="px-4 py-3">Total</td>
                      <td className="text-center px-4 py-3">{kpiResults.table_count}</td>
                      <td className="text-right px-4 py-3">{kpiResults.total_dc_kwp.toLocaleString()}</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <Button
                type="button"
                variant="outline"
                size="sm"
                className="mt-6"
                onClick={() => {
                  if (!kpiResults) return;
                  const dcKw = kpiResults.total_dc_kwp;
                  const dcAcRatio =
                    layoutParams ? parseFloat(layoutParams.dcAcRatio || '1.2') || 1.2 : 1.2;
                  const invKw = inverterRatedPowerKwProp ?? 0;
                  const invCount = invKw > 0 ? Math.ceil(dcKw / dcAcRatio / invKw) : 0;
                  const acKw = invCount * (inverterRatedPowerKwProp ?? 0);
                  const rows = [
                    ['KPI Results', ''],
                    ['Full Tables', String(kpiResults.full_tables)],
                    ['Half Tables', String(kpiResults.half_tables)],
                    ['Quarter Tables', String(kpiResults.quarter_tables)],
                    ['Total Tables', String(kpiResults.table_count)],
                    ['Total Modules', String(kpiResults.total_modules)],
                    ['DC Capacity (kWp)', String(kpiResults.total_dc_kwp)],
                    ['AC Capacity (kWac)', String(acKw)],
                    ['DC:AC Ratio', String(dcAcRatio)],
                    ['Land Area (m²)', String(kpiResults.land_area_m2)],
                    [
                      'Interrow Spacing (m)',
                      String(
                        kpiResults.interrow_spacing_m ?? layoutParams?.interrowSpacingM ?? ''
                      ),
                    ],
                    ...(kpiResults.nearest_tl_voltage_kv != null
                      ? [
                          ['Nearest TL Voltage (kV)', String(kpiResults.nearest_tl_voltage_kv)],
                          ['Distance to Line (m)', String(kpiResults.distance_to_line_m ?? '')],
                          ['Substation', translateGridName(kpiResults.substation_name)],
                          ['Line Name', translateGridName(kpiResults.line_name)],
                        ]
                      : []),
                  ];
                  const csv = rows.map((r) => r.join(',')).join('\n');
                  const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8' });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url;
                  a.download = 'KPI_Results.csv';
                  a.click();
                  URL.revokeObjectURL(url);
                }}
              >
                <Download className="w-4 h-4 mr-2" />
                Download KPI CSV
              </Button>
            </div>
          )}
        </CardContent>
      )}
    </Card>
    </div>
  );
}
