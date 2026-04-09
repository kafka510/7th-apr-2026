/**
 * Monthly Energy Generation Values and Losses — matches Excel formulas.
 * Ported from solar-insight `MonthlyEnergyGenerationTab` to Engineering Tools.
 */
import { useState, useEffect, useCallback, type ChangeEvent } from 'react';
import { Download } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { engineeringToolsFetch, solarApiUrl } from '../lib/api';
import { monthlyTiltedRadiation } from '../lib/tiltedRadiation';
import { translateGridName } from '../lib/gridTermTranslations';
import type { KpiResults } from './ExportLayoutKmlBlock';
import type { SystemConfigLayoutParams } from './SystemConfigurationBlock';

const DAYS_IN_MONTH = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
const MONTH_NAMES = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
];

interface SolarGISRecord {
  month: string;
  ghi: number;
  dni: number;
  dif: number;
  temp: number;
  albedo?: number | null;
}

interface SiteOrientationData {
  latitude: number;
  longitude: number;
  tilt_deg: number | null;
}

interface ModuleAssumptionsData {
  module_wp: number | null;
  module_length_mm: number | null;
  module_width_mm: number | null;
  module_efficiency_pct: number | null;
  module_master_id?: number | null;
}

interface ModuleMasterData {
  temp_coeff_pmax_pct: number | null;
  bifaciality_factor: number | null;
}

interface MonthlyEnergyGenerationTabProps {
  location: { lat: number; lng: number } | null;
  solargisRecords: SolarGISRecord[] | null;
  soilingLossPercent: number[] | null;
  totalModules: number | null;
  dcLossPct: number;
  acLossPct: number;
  shadowLossPct: number;
  /** Layout KPI results (from PV Layout export) — shown in Plant KPIs when available */
  kpiResults?: KpiResults | null;
  layoutParams?: SystemConfigLayoutParams | null;
  inverterRatedPowerKw?: number | null;
}

export default function MonthlyEnergyGenerationTab({
  location,
  solargisRecords,
  soilingLossPercent,
  totalModules,
  dcLossPct = 1.5,
  acLossPct = 2,
  shadowLossPct = 3,
  kpiResults,
  layoutParams,
  inverterRatedPowerKw,
}: MonthlyEnergyGenerationTabProps) {
  const [loading, setLoading] = useState(false);
  const [latitude, setLatitude] = useState<number>(25);
  const [tiltDeg, setTiltDeg] = useState<number>(25);
  const [moduleWp, setModuleWp] = useState<number>(600);
  const [moduleEffPct, setModuleEffPct] = useState<number>(21);
  const [moduleLengthMm, setModuleLengthMm] = useState<number>(2278);
  const [moduleWidthMm, setModuleWidthMm] = useState<number>(1134);
  const [tempCoeffPct, setTempCoeffPct] = useState<number>(-0.34);
  const [inverterEffPct] = useState<number>(98.5);
  const [bifacialGainPct, setBifacialGainPct] = useState<number>(0);
  const [otherGainPct] = useState<number>(0);
  const [, setProjectId] = useState<number | null>(null);
  /** Manual override when PV layout hasn't been exported yet */
  const [totalModulesOverride, setTotalModulesOverride] = useState<string>('');

  const ensureProject = useCallback(async (): Promise<number | null> => {
    if (!location) return null;
    const res = await engineeringToolsFetch(solarApiUrl('api/projects/'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ latitude: location.lat, longitude: location.lng }),
    });
    if (!res.ok) return null;
    const data = await res.json();
    return data.id as number;
  }, [location]);

  useEffect(() => {
    if (!location) return;
    let cancelled = false;
    (async () => {
      const pid = await ensureProject();
      if (!pid || cancelled) return;
      setProjectId(pid);
      setLoading(true);
      try {
        const [siteRes, modRes] = await Promise.all([
          engineeringToolsFetch(solarApiUrl(`api/pre-feasibility/site-orientation/${pid}/`)),
          engineeringToolsFetch(solarApiUrl(`api/pre-feasibility/module-assumptions/${pid}/`)),
        ]);
        if (cancelled) return;
        if (siteRes.ok) {
          const site = (await siteRes.json()) as SiteOrientationData;
          setLatitude(site.latitude ?? location.lat);
          setTiltDeg(site.tilt_deg ?? 25);
        } else {
          setLatitude(location.lat);
          setTiltDeg(25);
        }
        if (modRes.ok) {
          const mod = (await modRes.json()) as ModuleAssumptionsData;
          if (mod.module_wp != null) setModuleWp(mod.module_wp);
          if (mod.module_efficiency_pct != null)
            setModuleEffPct(mod.module_efficiency_pct);
          if (mod.module_length_mm != null)
            setModuleLengthMm(mod.module_length_mm);
          if (mod.module_width_mm != null)
            setModuleWidthMm(mod.module_width_mm);
          if (mod.module_master_id) {
            const mmRes = await engineeringToolsFetch(
              solarApiUrl('api/pre-feasibility/module-master/'),
            );
            if (mmRes.ok) {
              const list = (await mmRes.json()) as Array<{
                id: number;
                temp_coeff_pmax_pct?: number;
                bifaciality_factor?: number;
              }>;
              const mm = list.find(
                (m) => m.id === mod.module_master_id,
              ) as ModuleMasterData | undefined;
              if (mm?.temp_coeff_pmax_pct != null) {
                setTempCoeffPct(mm.temp_coeff_pmax_pct);
              }
              if (mm?.bifaciality_factor != null) {
                setBifacialGainPct(mm.bifaciality_factor * 5);
              }
            }
          }
        }
      } catch {
        // Keep defaults
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [location, ensureProject]);

  const gamma = tempCoeffPct / 100;
  const moduleEff = moduleEffPct / 100;
  const inverterEff = inverterEffPct / 100;
  const shadowLoss = shadowLossPct / 100;
  const dcLoss = dcLossPct / 100;
  const acLoss = acLossPct / 100;
  const bifacialGain = bifacialGainPct / 100;
  const otherGain = otherGainPct / 100;

  const modulesFromLayout = totalModules ?? 0;
  const modulesOverride = (() => {
    const s = totalModulesOverride.trim();
    if (!s) return null;
    const n = parseInt(s, 10);
    return Number.isNaN(n) || n < 0 ? null : n;
  })();
  const modules =
    modulesFromLayout > 0 ? modulesFromLayout : modulesOverride ?? 0;
  const moduleAreaM2 = (moduleLengthMm / 1000) * (moduleWidthMm / 1000);
  const totalPvAreaM2 = modules * moduleAreaM2;

  const ghi =
    solargisRecords?.slice(0, 12).map((r) => r.ghi ?? 0) ??
    Array(12).fill(0);
  const dif =
    solargisRecords?.slice(0, 12).map((r) => r.dif ?? 0) ??
    Array(12).fill(0);
  const temp =
    solargisRecords?.slice(0, 12).map((r) => r.temp ?? 0) ??
    Array(12).fill(0);
  const albedo =
    solargisRecords?.slice(0, 12).map((r) => r.albedo ?? 0.2) ??
    Array(12).fill(0.2);

  const tiltedRadiation = monthlyTiltedRadiation(
    ghi,
    dif,
    latitude,
    tiltDeg,
    albedo,
  );
  const soilingLossDec =
    soilingLossPercent?.slice(0, 12).map((p) => p / 100) ??
    Array(12).fill(0);

  // Excel: ROUNDUP(lat)<=20 → temp+46, else → T_cell = temp + GHI*0.032
  // Note: Excel G74 uses $D$86 (annual avg) but G75:G85 use $D75:$D85 (monthly) — matching that pattern
  const latRoundedUp = latitude >= 0 ? Math.ceil(latitude) : Math.floor(latitude);
  const useFixedOffset = latRoundedUp <= 20;
  const annualAvgTemp = temp.reduce((a, b) => a + b, 0) / 12;
  const tCell = temp.map((t, i) =>
    useFixedOffset
      ? t + 46
      : (i === 0 ? annualAvgTemp : t) + (ghi[i] ?? 0) * 0.032, // Jan: annual avg, Feb–Dec: monthly
  );
  const temperatureLossDec = tCell.map((tc) => gamma * (tc - 25));
  const temperatureLossPercent = temperatureLossDec.map((t) => t * 100);

  const monthlyEnergyMwh = tiltedRadiation.map((ht, i) => {
    const sl = soilingLossDec[i] ?? 0;
    const tl = temperatureLossDec[i] ?? 0;
    return (
      (ht *
        totalPvAreaM2 *
        moduleEff *
        inverterEff *
        (1 - shadowLoss) *
        (1 - dcLoss) *
        (1 - acLoss) *
        (1 - sl) *
        (1 - tl)) *
      (1 + bifacialGain) *
      (1 + otherGain) /
      1000
    );
  });

  // Excel uses SIMPLE AVERAGE for YEAR row (F86, G86): =AVERAGE(F74:F85), =AVERAGE(G74:G85)
  const annualAvgSoiling =
    (soilingLossDec.reduce((a, b) => a + b, 0) / 12) * 100;
  const annualAvgTempLoss =
    (temperatureLossDec.reduce((a, b) => a + b, 0) / 12) * 100;

  const totalDays = DAYS_IN_MONTH.reduce((a, b) => a + b, 0);
  const totalGhi = ghi.reduce((a, b) => a + b, 0);
  const annualAvgAlbedo = albedo.reduce((a, b) => a + b, 0) / 12;
  const annualTilted = tiltedRadiation.reduce((a, b) => a + b, 0);
  const annualEnergyMwh = monthlyEnergyMwh.reduce((a, b) => a + b, 0);

  // Excel: DC kWp = (modules * module_wp) / 1000 — prefer layout KPI when available
  const dcCapacityKw =
    kpiResults?.total_dc_kwp ??
    (modules > 0 ? (modules * moduleWp) / 1000 : 0);
  const dcCapacityMw = dcCapacityKw / 1000;
  // Specific Yield kWh/kWp/year = Annual MWh * 1000 / DC kWp
  const specificYieldKwhKwpYear =
    dcCapacityKw > 0 ? (annualEnergyMwh * 1000) / dcCapacityKw : 0;
  // PR = Annual Energy / Theoretical; Theoretical = annualTilted * (eff/100) * totalPvAreaM2 / 1000
  const theoreticalMwh =
    totalPvAreaM2 > 0
      ? (annualTilted * moduleEff * totalPvAreaM2) / 1000
      : 0;
  const performanceRatio =
    theoreticalMwh > 0 ? annualEnergyMwh / theoreticalMwh : 0;
  // CUF (%) = (Annual MWh / (DC_MW * 8760)) * 100
  const cufPct =
    dcCapacityMw > 0 ? (annualEnergyMwh / (dcCapacityMw * 8760)) * 100 : 0;

  const monthLabels =
    solargisRecords?.slice(0, 12).map((r) => r.month) ?? MONTH_NAMES;
  const headerBg = 'bg-slate-800 text-white uppercase text-xs tracking-wider font-semibold';

  if (!location) {
    return (
      <Card>
        <CardContent className="p-6">
          <p className="text-muted-foreground">
            Set coordinates in Site Inputs first.
          </p>
        </CardContent>
      </Card>
    );
  }

  const hasResults = modules > 0 && solargisRecords && solargisRecords.length >= 12;

  return (
    <div className="space-y-4">
      <Tabs defaultValue="monthly" className="space-y-6">
        <TabsList className="flex w-full border border-gray-200 bg-white rounded-lg p-1 shadow-sm">
          <TabsTrigger value="monthly" className="flex-1 data-[state=active]:bg-slate-800 data-[state=active]:text-white">
            Monthly Energy Generation Values and Losses
          </TabsTrigger>
          <TabsTrigger value="results" className="flex-1 data-[state=active]:bg-slate-800 data-[state=active]:text-white">
            Pre-Feasibility Results
          </TabsTrigger>
        </TabsList>

        <TabsContent value="monthly" className="m-0">
          <Card className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
            <CardContent className="pt-6 pr-6 pb-6 pl-0">
              <h2 className="text-xl font-semibold tracking-tight text-gray-900 mb-4">
                Monthly Energy Generation Values and Losses
              </h2>

          {loading && (
            <p className="text-sm text-muted-foreground mb-4">
              Loading parameters…
            </p>
          )}

          {(!solargisRecords || solargisRecords.length < 12) && (
            <p className="text-sm text-amber-600 dark:text-amber-400 mb-4">
              Upload SolarGIS CSV in Site Inputs. Complete Soiling Rate tab for
              soiling loss.
            </p>
          )}

          {(modulesFromLayout === 0 || totalModules == null) && (
            <div className="mb-4 p-3 rounded-lg border bg-amber-50/50 dark:bg-amber-950/20 border-amber-200 dark:border-amber-800">
              <Label
                htmlFor="total-modules-override"
                className="text-sm font-medium"
              >
                Total modules
              </Label>
              <p className="text-xs text-muted-foreground mb-2">
                Enter total module count when PV Layout export has not been run.
                Energy (MWh) requires a non-zero PV area.
              </p>
              <Input
                id="total-modules-override"
                type="number"
                min={1}
                placeholder="e.g. 15000"
                value={totalModulesOverride}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setTotalModulesOverride(e.target.value)}
                className="max-w-[200px]"
              />
            </div>
          )}

          <div className="overflow-x-auto rounded-xl border border-gray-200 overflow-hidden shadow-sm bg-white">
            <table className="w-full text-sm">
              <thead>
                <tr className={headerBg}>
                  <th className="px-4 py-3 text-left">
                    Month
                  </th>
                  <th className="px-4 py-3 text-right">
                    Days
                  </th>
                  <th className="px-4 py-3 text-right">GHI (kWh/m²)</th>
                  <th className="px-4 py-3 text-right">Temp (°C)</th>
                  <th className="px-4 py-3 text-right">Albedo</th>
                  <th className="px-4 py-3 text-right">Soiling Incl Snow (%)</th>
                  <th className="px-4 py-3 text-right">Temperature Loss (%)</th>
                  <th className="px-4 py-3 text-right">Tilted Radiation (kWh/m²)</th>
                  <th className="px-4 py-3 text-right">Energy (MWh)</th>
                </tr>
              </thead>
              <tbody>
                {monthLabels.map((month, i) => (
                  <tr
                    key={month}
                    className="border-t border-gray-200 even:bg-gray-50 hover:bg-emerald-50/50 transition-colors duration-150"
                  >
                    <td className="px-4 py-3 font-medium">{month}</td>
                    <td className="px-4 py-3 text-right font-mono">{DAYS_IN_MONTH[i]}</td>
                    <td className="px-4 py-3 text-right font-mono">{ghi[i]?.toFixed(2) ?? '—'}</td>
                    <td className="px-4 py-3 text-right font-mono">{temp[i]?.toFixed(1) ?? '—'}</td>
                    <td className="px-4 py-3 text-right font-mono">{albedo[i]?.toFixed(2) ?? '—'}</td>
                    <td className="px-4 py-3 text-right font-mono">{(soilingLossDec[i] * 100).toFixed(2)}</td>
                    <td className="px-4 py-3 text-right font-mono">{temperatureLossPercent[i]?.toFixed(2) ?? '—'}</td>
                    <td className="px-4 py-3 text-right font-mono">{tiltedRadiation[i]?.toFixed(2) ?? '—'}</td>
                    <td className="px-4 py-3 text-right font-mono font-semibold">{monthlyEnergyMwh[i]?.toFixed(4) ?? '—'}</td>
                  </tr>
                ))}
                <tr className="border-t-2 border-slate-800 bg-slate-900 text-white font-semibold">
                  <td className="px-4 py-3 font-medium">YEAR</td>
                  <td className="px-4 py-3 text-right font-mono">
                    {totalDays}
                  </td>
                  <td className="px-4 py-3 text-right font-mono">{totalGhi.toFixed(2)}</td>
                  <td className="px-4 py-3 text-right font-mono">{annualAvgTemp.toFixed(2)}</td>
                  <td className="px-4 py-3 text-right font-mono">{annualAvgAlbedo.toFixed(2)}</td>
                  <td className="px-4 py-3 text-right font-mono">{annualAvgSoiling.toFixed(2)}</td>
                  <td className="px-4 py-3 text-right font-mono">{annualAvgTempLoss.toFixed(2)}</td>
                  <td className="px-4 py-3 text-right font-mono">{annualTilted.toFixed(2)}</td>
                  <td className="px-4 py-3 text-right font-mono">{annualEnergyMwh.toFixed(4)}</td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* Download Energy table as CSV */}
          {solargisRecords && solargisRecords.length >= 12 && (
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="mt-6 bg-white hover:bg-gray-50 rounded-lg shadow-sm border-gray-200"
              onClick={() => {
                const headers = [
                  'Month',
                  'Days',
                  'GHI (kWh/m²)',
                  'Temp (°C)',
                  'Albedo',
                  'Soiling (%)',
                  'Temp Loss (%)',
                  'Tilted Radiation (kWh/m²)',
                  'Energy (MWh)',
                ];
                const rows = monthLabels.map((month, i) => [
                  month,
                  String(DAYS_IN_MONTH[i]),
                  ghi[i]?.toFixed(2) ?? '',
                  temp[i]?.toFixed(1) ?? '',
                  albedo[i]?.toFixed(2) ?? '',
                  (soilingLossDec[i] * 100).toFixed(2),
                  temperatureLossPercent[i]?.toFixed(2) ?? '',
                  tiltedRadiation[i]?.toFixed(2) ?? '',
                  monthlyEnergyMwh[i]?.toFixed(4) ?? '',
                ]);
                const yearRow = [
                  'YEAR',
                  String(totalDays),
                  totalGhi.toFixed(2),
                  annualAvgTemp.toFixed(2),
                  annualAvgAlbedo.toFixed(2),
                  annualAvgSoiling.toFixed(2),
                  annualAvgTempLoss.toFixed(2),
                  annualTilted.toFixed(2),
                  annualEnergyMwh.toFixed(4),
                ];
                const csv = [
                  headers.join(','),
                  ...rows.map((r) => r.join(',')),
                  yearRow.join(','),
                ].join('\n');
                const blob = new Blob(['\ufeff' + csv], {
                  type: 'text/csv;charset=utf-8',
                });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'Energy_Generation_Table.csv';
                a.click();
                URL.revokeObjectURL(url);
              }}
            >
              <Download className="w-4 h-4 mr-2" />
              Download Energy Table CSV
            </Button>
          )}

          <p className="text-xs text-muted-foreground mt-4">
            Parameters used: PV Area {totalPvAreaM2.toFixed(2)} m², Module eff{' '}
            {moduleEffPct}%, Inverter eff {inverterEffPct}%, DC loss {dcLossPct}
            %, AC loss {acLossPct}%, Shadow {shadowLossPct}%.
          </p>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="results" className="m-0 space-y-6">
          <div className="rounded-xl bg-slate-50 border border-gray-200/80 p-6 space-y-6">
            {!hasResults ? (
              <Card className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <p className="text-sm text-gray-500">
                  Complete the <strong>Monthly Energy Generation Values and Losses</strong> tab and ensure SolarGIS data is loaded to see Pre-Feasibility Results.
                </p>
              </Card>
            ) : (
              <>
                {/* Plant KPIs */}
                <Card className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                  <div className="bg-slate-800 text-white uppercase text-xs tracking-wider font-semibold px-6 py-3">
                    Plant KPIs
                  </div>
                  <CardContent className="p-6">
                    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-6 text-sm">
                      <div className="space-y-0.5">
                        <p className="text-sm text-gray-500">DC Capacity (kWp)</p>
                        <p className="font-semibold text-gray-800">{dcCapacityKw.toFixed(2)}</p>
                      </div>
                      <div className="space-y-0.5">
                        <p className="text-sm text-gray-500">Annual Energy (MWh/year)</p>
                        <p className="font-semibold text-gray-800">{annualEnergyMwh.toFixed(2)}</p>
                      </div>
                      <div className="space-y-0.5">
                        <p className="text-sm text-gray-500">Specific Yield (kWh/kWp/year)</p>
                        <p className="font-semibold text-gray-800">{specificYieldKwhKwpYear.toFixed(1)}</p>
                      </div>
                      <div className="space-y-0.5">
                        <p className="text-sm text-gray-500">Performance Ratio</p>
                        <p className="font-semibold text-gray-800">{(performanceRatio * 100).toFixed(2)}%</p>
                      </div>
                      <div className="space-y-0.5">
                        <p className="text-sm text-gray-500">CUF (%)</p>
                        <p className="font-semibold text-gray-800">{cufPct.toFixed(2)}%</p>
                      </div>
                      <div className="space-y-0.5">
                        <p className="text-sm text-gray-500">PV Area (m²)</p>
                        <p className="font-semibold text-gray-800">{totalPvAreaM2.toFixed(2)}</p>
                      </div>
                      <div className="space-y-0.5">
                        <p className="text-sm text-gray-500">PV Area (ha)</p>
                        <p className="font-semibold text-gray-800">{(totalPvAreaM2 / 10000).toFixed(4)}</p>
                      </div>
                      <div className="space-y-0.5">
                        <p className="text-sm text-gray-500">Total Modules</p>
                        <p className="font-semibold text-gray-800">{(kpiResults?.total_modules ?? modules).toLocaleString()}</p>
                      </div>
                      {kpiResults && (
                        <>
                          <div className="space-y-0.5">
                            <p className="text-sm text-gray-500">Land Area (m²)</p>
                            <p className="font-semibold text-gray-800">{kpiResults.land_area_m2.toLocaleString()}</p>
                          </div>
                          {kpiResults.interrow_spacing_m != null && (
                            <div className="space-y-0.5">
                              <p className="text-sm text-gray-500">Interrow/Row Spacing (m)</p>
                              <p className="font-semibold text-gray-800">{kpiResults.interrow_spacing_m.toFixed(2)}</p>
                            </div>
                          )}
                          <div className="space-y-0.5">
                            <p className="text-sm text-gray-500">Full / Half / Quarter Tables</p>
                            <p className="font-semibold text-gray-800">
                              {kpiResults.full_tables} / {kpiResults.half_tables} / {kpiResults.quarter_tables}
                            </p>
                          </div>
                        </>
                      )}
                    </div>
                  </CardContent>
                </Card>

                {/* AC / INVERTER */}
                {layoutParams && inverterRatedPowerKw != null && inverterRatedPowerKw > 0 && (
                  <Card className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                    <div className="bg-slate-800 text-white uppercase text-xs tracking-wider font-semibold px-6 py-3">
                      AC / INVERTER
                    </div>
                    <CardContent className="p-6">
                      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-6">
                        {(() => {
                          const dcAcRatioValue = parseFloat(layoutParams.dcAcRatio || '1.2') || 1.2;
                          const theoreticalAcKw = dcCapacityKw / dcAcRatioValue;
                          const requiredInverters = Math.ceil(theoreticalAcKw / inverterRatedPowerKw);
                          const finalAcKw = requiredInverters * inverterRatedPowerKw;
                          return (
                            <>
                              <div className="space-y-0.5">
                                <p className="text-sm text-gray-500">DC:AC Ratio</p>
                                <p className="font-semibold text-gray-800">{dcAcRatioValue}</p>
                              </div>
                              <div className="space-y-0.5">
                                <p className="text-sm text-gray-500">Theoretical AC (kW)</p>
                                <p className="font-semibold text-gray-800">{theoreticalAcKw.toFixed(2)}</p>
                              </div>
                              <div className="space-y-0.5">
                                <p className="text-sm text-gray-500">Inverter Rating</p>
                                <p className="font-semibold text-gray-800">{inverterRatedPowerKw} kW</p>
                              </div>
                              <div className="space-y-0.5">
                                <p className="text-sm text-gray-500">Required Inverters</p>
                                <p className="font-semibold text-gray-800">{requiredInverters}</p>
                              </div>
                              <div className="space-y-0.5">
                                <p className="text-sm text-gray-500">Final AC (kWac)</p>
                                <p className="font-semibold text-gray-800">{finalAcKw.toLocaleString()}</p>
                              </div>
                            </>
                          );
                        })()}
                      </div>
                    </CardContent>
                  </Card>
                )}

                {/* LOSS FACTORS & EFFICIENCY */}
                <Card className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                  <div className="bg-slate-800 text-white uppercase text-xs tracking-wider font-semibold px-6 py-3">
                    LOSS FACTORS & EFFICIENCY
                  </div>
                  <CardContent className="p-6">
                    <div className="flex flex-wrap gap-x-8 gap-y-2 text-sm">
                      <span className="text-gray-500">Module eff: <span className="font-semibold text-gray-800">{moduleEffPct}%</span></span>
                      <span className="text-gray-500">Inverter eff: <span className="font-semibold text-gray-800">{inverterEffPct}%</span></span>
                      <span className="text-gray-500">DC loss: <span className="font-semibold text-gray-800">{dcLossPct}%</span></span>
                      <span className="text-gray-500">AC loss: <span className="font-semibold text-gray-800">{acLossPct}%</span></span>
                      <span className="text-gray-500">Shadow: <span className="font-semibold text-gray-800">{shadowLossPct}%</span></span>
                    </div>
                  </CardContent>
                </Card>

                {/* Grid Connectivity (unavailable) */}
                {kpiResults?.grid_connectivity_error && (
                  <Card className="bg-white rounded-xl shadow-sm border border-amber-200 overflow-hidden">
                    <div className="bg-amber-100 text-amber-900 uppercase text-xs tracking-wider font-semibold px-6 py-3">
                      Grid Connectivity (unavailable)
                    </div>
                    <CardContent className="p-6">
                      <p className="text-sm text-amber-800">
                        {kpiResults.grid_connectivity_error}. Place KMZ files (e.g. <code className="text-xs bg-amber-50 px-1 rounded">japan.kmz</code>) in <code className="text-xs bg-amber-50 px-1 rounded">engineering_tools/grid_network/</code> or set <code className="text-xs bg-amber-50 px-1 rounded">GRID_NETWORK_DATA_ROOT</code> in .env.
                      </p>
                    </CardContent>
                  </Card>
                )}

                {/* Grid Connectivity */}
                {kpiResults?.nearest_tl_voltage_kv != null && (
                  <Card className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                    <div className="bg-slate-800 text-white uppercase text-xs tracking-wider font-semibold px-6 py-3">
                      Grid Connectivity
                    </div>
                    <CardContent className="p-6">
                      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 text-sm">
                        <div className="space-y-0.5">
                          <p className="text-sm text-gray-500">Nearest TL Voltage</p>
                          <p className="font-semibold text-gray-800">{kpiResults.nearest_tl_voltage_kv} kV</p>
                        </div>
                        <div className="space-y-0.5">
                          <p className="text-sm text-gray-500">Distance to Line</p>
                          <p className="font-semibold text-gray-800">{kpiResults.distance_to_line_m} m</p>
                        </div>
                        {kpiResults.substation_name && (
                          <div className="space-y-0.5">
                            <p className="text-sm text-gray-500">Substation</p>
                            <p className="font-semibold text-gray-800">{translateGridName(kpiResults.substation_name)}</p>
                          </div>
                        )}
                        {kpiResults.line_name && (
                          <div className="space-y-0.5">
                            <p className="text-sm text-gray-500">Line Name</p>
                            <p className="font-semibold text-gray-800">{translateGridName(kpiResults.line_name)}</p>
                          </div>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                )}

                {/* Download Pre-Feasibility Results in same format as KPI CSV */}
                <div className="pt-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="bg-white hover:bg-gray-50 rounded-lg shadow-sm border-gray-200"
                    onClick={() => {
                      const dcAcRatioValue = layoutParams ? parseFloat(layoutParams.dcAcRatio || '1.2') || 1.2 : 1.2;
                      const invKw = inverterRatedPowerKw ?? 0;
                      const theoreticalAcKw = dcCapacityKw / dcAcRatioValue;
                      const requiredInverters = invKw > 0 ? Math.ceil(theoreticalAcKw / invKw) : 0;
                      const finalAcKw = requiredInverters * invKw;

                      const rows: [string, string][] = [
                        ['Pre-Feasibility Results', ''],
                        ['DC Capacity (kWp)', dcCapacityKw.toFixed(2)],
                        ['Annual Energy (MWh/year)', annualEnergyMwh.toFixed(2)],
                        ['Specific Yield (kWh/kWp/year)', specificYieldKwhKwpYear.toFixed(1)],
                        ['Performance Ratio (%)', (performanceRatio * 100).toFixed(2)],
                        ['CUF (%)', cufPct.toFixed(2)],
                        ['PV Area (m²)', totalPvAreaM2.toFixed(2)],
                        ['PV Area (ha)', (totalPvAreaM2 / 10000).toFixed(4)],
                        ['Total Modules', String(kpiResults?.total_modules ?? modules)],
                        ...(kpiResults
                          ? ([
                              ['Land Area (m²)', String(kpiResults.land_area_m2)],
                              ['Interrow Spacing (m)', String(kpiResults.interrow_spacing_m ?? layoutParams?.interrowSpacingM ?? '')],
                              ['Full Tables', String(kpiResults.full_tables)],
                              ['Half Tables', String(kpiResults.half_tables)],
                              ['Quarter Tables', String(kpiResults.quarter_tables)],
                            ] as [string, string][])
                          : []),
                        ['Module eff (%)', String(moduleEffPct)],
                        ['Inverter eff (%)', String(inverterEffPct)],
                        ['DC loss (%)', String(dcLossPct)],
                        ['AC loss (%)', String(acLossPct)],
                        ['Shadow (%)', String(shadowLossPct)],
                        ...(layoutParams && invKw > 0
                          ? ([
                              ['DC:AC Ratio', String(dcAcRatioValue)],
                              ['Theoretical AC (kW)', theoreticalAcKw.toFixed(2)],
                              ['Inverter Rating (kW)', String(invKw)],
                              ['Required Inverters', String(requiredInverters)],
                              ['Final AC (kWac)', String(finalAcKw)],
                            ] as [string, string][])
                          : []),
                        ...(kpiResults?.nearest_tl_voltage_kv != null
                          ? ([
                              ['Nearest TL Voltage (kV)', String(kpiResults.nearest_tl_voltage_kv)],
                              ['Distance to Line (m)', String(kpiResults.distance_to_line_m ?? '')],
                              ['Substation', translateGridName(kpiResults.substation_name)],
                              ['Line Name', translateGridName(kpiResults.line_name)],
                            ] as [string, string][])
                          : []),
                      ];
                      const csv = rows.map((r) => r.map((c) => (c.includes(',') ? `"${c}"` : c)).join(',')).join('\n');
                      const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8' });
                      const url = URL.createObjectURL(blob);
                      const a = document.createElement('a');
                      a.href = url;
                      a.download = 'Pre_Feasibility_Results.csv';
                      a.click();
                      URL.revokeObjectURL(url);
                    }}
                  >
                    <Download className="w-4 h-4 mr-2" />
                    Download Pre-Feasibility Results CSV
                  </Button>
                </div>
              </>
            )}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}

