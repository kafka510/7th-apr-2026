/**
 * Soiling Rate Calculation — Environmental Loss Analytics Dashboard.
 * Tilt from Site Orientation, Site soiling rate with presets, Manual cleanings per month.
 * Ported from solar-insight `SoilingRateCalculationTab` to Engineering Tools.
 */
import { useState, useEffect, useCallback, useRef, type ChangeEvent, type MouseEvent } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { FormMultiSelect } from '@/components/ui/form-multi-select';
import { engineeringToolsFetch, solarApiUrl } from '../lib/api';

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

const SOILING_PRESETS = [
  { label: 'Standard: 0.6%', value: 0.6 },
  { label: 'Desert: 0.9%', value: 0.9 },
  { label: 'High Dust [Cement / Mines]: 2%', value: 2 },
] as const;

interface SolarGISMonthlyRecord {
  month: string;
  precipitation_mm?: number | null;
  snow_days?: number | null;
}

interface SiteOrientationData {
  tilt_deg: number | null;
}

interface SoilingRateCalculationTabProps {
  location: { lat: number; lng: number } | null;
  solargisRecords: SolarGISMonthlyRecord[] | null;
  /** Called when soiling-incl-snow loss percent [12] is computed, for Energy Generation tab */
  onSoilingLossChange?: (soilingLossPercent: number[]) => void;
}

export default function SoilingRateCalculationTab({
  location,
  solargisRecords,
  onSoilingLossChange,
}: SoilingRateCalculationTabProps) {
  const [tilt, setTilt] = useState<number>(25);
  const [siteSoilingRatePct, setSiteSoilingRatePct] = useState<number>(0.6);
  const [manualCleanings, setManualCleanings] = useState<number[]>([
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
  ]);
  const [loading, setLoading] = useState(false);
  const [isEditMode, setIsEditMode] = useState(true);
  const [saving, setSaving] = useState(false);
  const [projectId, setProjectId] = useState<number | null>(null);
  const [configOpen, setConfigOpen] = useState(false);
  const [chartOpen, setChartOpen] = useState(false);

  const STORAGE_KEY = (pid: number) => `soiling_calculation_${pid}`;

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
    if (!location) {
      setProjectId(null);
      return;
    }
    let cancelled = false;
    (async () => {
      const pid = await ensureProject();
      if (!pid || cancelled) return;
      setProjectId(pid);
      setLoading(true);
      try {
        const res = await engineeringToolsFetch(
          solarApiUrl(`api/pre-feasibility/site-orientation/${pid}/`),
        );
        if (!res.ok || cancelled) return;
        const data = (await res.json()) as SiteOrientationData;
        if (!cancelled && data.tilt_deg != null) {
          setTilt(data.tilt_deg);
        }
        const stored = localStorage.getItem(STORAGE_KEY(pid));
        if (!cancelled && stored) {
          try {
            const parsed = JSON.parse(stored) as {
              siteSoilingRatePct?: number;
              manualCleanings?: number[];
            };
            if (parsed.siteSoilingRatePct != null) {
              setSiteSoilingRatePct(parsed.siteSoilingRatePct);
            }
            if (
              Array.isArray(parsed.manualCleanings) &&
              parsed.manualCleanings.length === 12
            ) {
              setManualCleanings(parsed.manualCleanings);
            }
            setIsEditMode(false);
          } catch {
            // Ignore parse errors
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

  const handleSave = () => {
    if (projectId == null) return;
    setSaving(true);
    try {
      localStorage.setItem(
        STORAGE_KEY(projectId),
        JSON.stringify({ siteSoilingRatePct, manualCleanings }),
      );
      setIsEditMode(false);
    } finally {
      setTimeout(() => setSaving(false), 200);
    }
  };

  const rampRate = siteSoilingRatePct / 100 - (tilt / 90) * 0.0075;
  const snowConversionRatio = 0.4 + (25 - tilt) * 0.00666;

  const precipMm =
    solargisRecords?.slice(0, 12).map((r) => r.precipitation_mm ?? 0) ??
    Array(12).fill(0);
  const snowDays =
    solargisRecords?.slice(0, 12).map((r) => r.snow_days ?? 0) ??
    Array(12).fill(0);

  const rows = MONTH_NAMES.map((month, i) => {
    const days = DAYS_IN_MONTH[i];
    const precip = precipMm[i] ?? 0;
    const naturalCleaning = Math.min(Math.floor(precip / 20), days);
    const manual = manualCleanings[i] ?? 0;
    const snow = snowDays[i] ?? 0;
    const snowDayPct = days > 0 ? (snow / days) * 100 : 0;
    const cleaningInterval = Math.floor(days / (manual + naturalCleaning + 1));
    const monthlySoiling = cleaningInterval * rampRate * 100;
    const snowLoss = (snowDayPct / 100) * snowConversionRatio * 100;
    const totalLoss = monthlySoiling + snowLoss;
    return {
      month,
      days,
      precip,
      naturalCleaning,
      manual,
      snow,
      snowDayPct,
      cleaningInterval,
      monthlySoiling,
      snowLoss,
      totalLoss,
    };
  });

  const yearRow = {
    days: rows.reduce((s, r) => s + r.days, 0),
    precip: rows.reduce((s, r) => s + r.precip, 0),
    naturalCleaning: rows.reduce((s, r) => s + r.naturalCleaning, 0),
    manual: rows.reduce((s, r) => s + r.manual, 0),
    snow: rows.reduce((s, r) => s + r.snow, 0),
    snowDayPct:
      rows.reduce((s, r) => s + r.days, 0) > 0
        ? (rows.reduce((s, r) => s + r.snow, 0) /
            rows.reduce((s, r) => s + r.days, 0)) *
          100
        : 0,
    monthlySoiling:
      rows.reduce((s, r) => s + r.monthlySoiling, 0) / 12,
    snowLoss:
      rows.reduce((s, r) => s + r.days, 0) > 0
        ? (rows.reduce((s, r) => s + r.snow, 0) /
            rows.reduce((s, r) => s + r.days, 0)) *
          snowConversionRatio *
          100
        : 0,
    totalLoss: rows.reduce((s, r) => s + r.totalLoss, 0) / 12,
  };

  const lastEmitted = useRef<string>('');
  useEffect(() => {
    const arr = rows.map((r) => r.totalLoss);
    const key = arr.join(',');
    if (key !== lastEmitted.current) {
      lastEmitted.current = key;
      onSoilingLossChange?.(arr);
    }
  });

  const updateManualCleaning = (index: number, value: number) => {
    setManualCleanings((prev) => {
      const next = [...prev];
      next[index] = Math.max(0, value);
      return next;
    });
  };

  const avgCleaningInterval =
    rows.length > 0
      ? Math.round(
          rows.reduce((s, r) => s + r.cleaningInterval, 0) / rows.length
        )
      : 0;

  const inputBaseClass =
    'rounded-lg border-gray-300 shadow-sm focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500';

  if (!location) {
    return (
      <Card className="border-emerald-100">
        <CardContent className="p-6">
          <p className="text-muted-foreground">
            Set coordinates in Site Inputs tab first.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-3">
      {/* 1. KPI Summary Row - Compact */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
        <div className="rounded-lg border border-emerald-100 bg-emerald-50/50 px-3 py-2 shadow-sm">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-emerald-700/80">
            Annual Soiling
          </p>
          <p className="text-lg font-semibold text-emerald-800 leading-tight">
            {yearRow.monthlySoiling.toFixed(2)}%
          </p>
        </div>
        <div className="rounded-lg border border-emerald-100 bg-emerald-50/50 px-3 py-2 shadow-sm">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-emerald-700/80">
            Snow Loss
          </p>
          <p className="text-lg font-semibold text-emerald-800 leading-tight">
            {yearRow.snowLoss.toFixed(2)}%
          </p>
        </div>
        <div className="rounded-lg border border-emerald-100 bg-emerald-50/50 px-3 py-2 shadow-sm">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-emerald-700/80">
            Natural Cleaning Days
          </p>
          <p className="text-lg font-semibold text-emerald-800 leading-tight">
            {yearRow.naturalCleaning}
          </p>
        </div>
        <div className="rounded-lg border border-emerald-100 bg-emerald-50/50 px-3 py-2 shadow-sm">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-emerald-700/80">
            Avg Cleaning Interval
          </p>
          <p className="text-lg font-semibold text-emerald-800 leading-tight">
            {avgCleaningInterval} days
          </p>
        </div>
      </div>

      {/* 2. Configuration Panel (Collapsible) */}
      <Card className="border-emerald-100 shadow-sm">
        <button
          type="button"
          onClick={() => setConfigOpen((o) => !o)}
          className="flex w-full flex-row items-center justify-between p-2.5 text-left hover:bg-emerald-50/30 transition-colors rounded-t-lg"
        >
          <h2 className="text-sm font-semibold text-gray-800">
            Soiling Rate Calculation
          </h2>
          <div className="flex items-center gap-2">
            {isEditMode ? (
              <Button
                onClick={(e: MouseEvent<HTMLButtonElement>) => {
                  e.stopPropagation();
                  handleSave();
                }}
                disabled={saving}
                size="sm"
                className="h-7 text-xs bg-emerald-600 hover:bg-emerald-700 text-white"
              >
                {saving ? 'Saving…' : 'Save'}
              </Button>
            ) : (
              <>
                <Button
                  type="button"
                  disabled
                  size="sm"
                  className="h-7 text-xs bg-emerald-600 hover:bg-emerald-600 text-white"
                >
                  Saved
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={(e: MouseEvent<HTMLButtonElement>) => {
                    e.stopPropagation();
                    setIsEditMode(true);
                  }}
                  className="h-7 text-xs border-emerald-300 text-emerald-700 hover:bg-emerald-50"
                >
                  Edit
                </Button>
              </>
            )}
            {configOpen ? (
              <ChevronUp className="h-4 w-4 text-gray-500" />
            ) : (
              <ChevronDown className="h-4 w-4 text-gray-500" />
            )}
          </div>
        </button>
        {configOpen && (
          <CardContent className="p-2.5 pt-0 border-t border-emerald-50">
            {/* Row 1: All inputs in one compact row */}
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 pt-2">
              <div className="space-y-0.5">
                <Label className="text-[11px] font-medium text-gray-600">
                  Tilt (°)
                </Label>
                <div className="flex items-center gap-1.5">
                  <Input
                    type="number"
                    value={tilt}
                    onChange={(e: ChangeEvent<HTMLInputElement>) => setTilt(Number(e.target.value) || 25)}
                    min={0}
                    max={90}
                    step={1}
                    className={`h-7 text-xs ${inputBaseClass} ${!isEditMode ? 'bg-gray-50' : 'bg-white'}`}
                    readOnly={loading || !isEditMode}
                    disabled={!isEditMode}
                  />
                  <span className="shrink-0 inline-flex items-center rounded bg-emerald-100 px-1.5 py-0.5 text-[10px] font-medium text-emerald-700">
                    Site Orientation
                  </span>
                </div>
              </div>
              <div className="space-y-0.5">
                <Label className="text-[11px] font-medium text-gray-600">
                  Site soiling rate (%)
                </Label>
                <Input
                  type="number"
                  min={0}
                  max={10}
                  step={0.1}
                  value={siteSoilingRatePct}
                  onChange={(e: ChangeEvent<HTMLInputElement>) =>
                    setSiteSoilingRatePct(Number(e.target.value) || 0.6)
                  }
                  className={`h-7 text-xs w-full ${inputBaseClass} ${!isEditMode ? 'bg-gray-50' : 'bg-white'}`}
                  readOnly={!isEditMode}
                  disabled={!isEditMode}
                />
              </div>
              <div className="space-y-0.5">
                <FormMultiSelect
                  label="Preset"
                  options={[
                    ...SOILING_PRESETS.map((p) => ({
                      value: String(p.value),
                      label: p.label,
                    })),
                    { value: 'custom', label: 'Custom' },
                  ]}
                  selected={
                    SOILING_PRESETS.some((p) => p.value === siteSoilingRatePct)
                      ? [String(siteSoilingRatePct)]
                      : ['custom']
                  }
                  onChange={(vals) => {
                    const v = vals[0];
                    if (v && v !== 'custom') setSiteSoilingRatePct(Number(v));
                  }}
                  placeholder="Select preset"
                  disabled={!isEditMode}
                  singleSelect
                />
              </div>
              <div className="space-y-0.5">
                <Label className="text-[11px] font-medium text-gray-600">
                  Ramp Rate (%)
                </Label>
                <Input
                  type="text"
                  value={(rampRate * 100).toFixed(2)}
                  readOnly
                  className={`h-7 text-xs ${inputBaseClass} bg-gray-50`}
                />
              </div>
              <div className="space-y-0.5 sm:col-span-1">
                <Label className="text-[11px] font-medium text-gray-600">
                  Snow ratio (%)
                </Label>
                <Input
                  type="text"
                  value={(snowConversionRatio * 100).toFixed(2)}
                  readOnly
                  className={`h-7 text-xs ${inputBaseClass} bg-gray-50`}
                />
              </div>
            </div>
            {/* Row 2: Helper text */}
            <p className="mt-1.5 text-[10px] text-muted-foreground">
              Presets: Standard 0.6%, Desert 0.9%, High Dust 2%. Ramp Rate & Snow ratio are calculated.
            </p>

            {(!solargisRecords || solargisRecords.length < 12) && (
              <p className="mt-2 text-xs text-amber-600 dark:text-amber-400">
                Upload SolarGIS Prospect CSV in Site Inputs tab to populate precipitation and snow days.
              </p>
            )}
          </CardContent>
        )}
      </Card>

      {/* 3. Mini Bar Chart (Collapsible) */}
      <Card className="border-emerald-100 shadow-sm overflow-hidden">
        <button
          type="button"
          onClick={() => setChartOpen((o) => !o)}
          className="flex w-full flex-row items-center justify-between p-2.5 text-left hover:bg-emerald-50/30 transition-colors rounded-t-lg"
        >
          <p className="text-sm font-semibold text-gray-700">
            Monthly Soiling & Snow Loss Chart
          </p>
          {chartOpen ? (
            <ChevronUp className="h-4 w-4 text-gray-500" />
          ) : (
            <ChevronDown className="h-4 w-4 text-gray-500" />
          )}
        </button>
        {chartOpen && (
        <CardContent className="p-3 pt-0 border-t border-emerald-50">
          <div className="flex items-end gap-0.5 h-20">
            {rows.map((row) => {
              const total = row.monthlySoiling + row.snowLoss;
              const scale = 25;
              const barHeight = Math.min(100, total * scale);
              const soilingPct =
                total > 0 ? (row.monthlySoiling / total) * 100 : 0;
              const snowPct = total > 0 ? (row.snowLoss / total) * 100 : 0;
              return (
                <div
                  key={row.month}
                  className="flex-1 flex flex-col items-center gap-1 min-w-0"
                >
                  <div
                    className="w-full flex flex-col-reverse rounded-t overflow-hidden bg-gray-100"
                    style={{ height: 56 }}
                    title={`${row.month}: Soiling ${row.monthlySoiling.toFixed(2)}% | Snow ${row.snowLoss.toFixed(2)}%`}
                  >
                    <div
                      className="w-full flex flex-col transition-all hover:opacity-90"
                      style={{
                        height: `${barHeight}%`,
                        minHeight: total > 0 ? 6 : 0,
                      }}
                    >
                      <div
                        className="w-full bg-emerald-500/90 min-h-0 flex-shrink-0"
                        style={{
                          height: soilingPct > 0 ? `${soilingPct}%` : '0px',
                          minHeight: soilingPct > 0 ? 2 : 0,
                        }}
                      />
                      <div
                        className="w-full bg-sky-400/80 min-h-0 flex-shrink-0"
                        style={{
                          height: snowPct > 0 ? `${snowPct}%` : '0px',
                          minHeight: snowPct > 0 ? 2 : 0,
                        }}
                      />
                    </div>
                  </div>
                  <span className="text-[10px] text-gray-500 truncate w-full text-center">
                    {row.month.slice(0, 3)}
                  </span>
                </div>
              );
            })}
          </div>
          <div className="flex gap-3 mt-1.5 text-[10px] text-muted-foreground">
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded bg-emerald-500" />
              Soiling %
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded bg-sky-400" />
              Snow Loss %
            </span>
          </div>
        </CardContent>
        )}
      </Card>

      {/* 4. Monthly Loss Table - Compact */}
      <Card className="border-emerald-100 shadow-sm overflow-hidden">
        <div className="px-3 py-2 border-b border-emerald-100">
          <p className="text-xs font-semibold text-gray-700">
            Monthly Loss Detail
          </p>
        </div>
        <CardContent className="p-0">
          <div className="overflow-x-auto rounded-b-lg">
            <table className="w-full text-xs">
              <thead>
                <tr>
                  <th className="px-2 py-1.5 text-left font-semibold bg-emerald-600 text-white text-xs">
                    Months
                  </th>
                  <th className="px-2 py-1.5 text-right font-semibold bg-emerald-600 text-white text-xs">
                    # of Days
                  </th>
                  <th className="px-2 py-1.5 text-right font-semibold bg-emerald-600 text-white text-xs">
                    Precipitation [mm]
                  </th>
                  <th className="px-2 py-1.5 text-right font-semibold bg-emerald-600 text-white text-xs">
                    Natural Cleaning
                  </th>
                  <th className="px-2 py-1.5 text-right font-semibold bg-emerald-600 text-white text-xs">
                    Manual
                  </th>
                  <th className="px-2 py-1.5 text-right font-semibold bg-emerald-600 text-white text-xs">
                    Snow Days
                  </th>
                  <th className="px-2 py-1.5 text-right font-semibold bg-emerald-600 text-white text-xs">
                    % Snow
                  </th>
                  <th className="px-2 py-1.5 text-right font-semibold bg-emerald-600 text-white text-xs">
                    Interval
                  </th>
                  <th className="px-2 py-1.5 text-right font-semibold bg-emerald-600 text-white text-xs">
                    Soiling %
                  </th>
                  <th className="px-2 py-1.5 text-right font-semibold bg-emerald-600 text-white text-xs">
                    Snow %
                  </th>
                  <th className="px-2 py-1.5 text-right font-semibold bg-emerald-600 text-white text-xs">
                    Total %
                  </th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row, i) => (
                  <tr
                    key={row.month}
                    className={`border-t border-gray-100 transition-colors hover:bg-emerald-50 ${
                      i % 2 === 0 ? 'bg-white' : 'bg-gray-50/50'
                    }`}
                  >
                    <td className="px-2 py-1 font-medium text-gray-800">
                      {row.month}
                    </td>
                    <td className="px-2 py-1 text-right font-mono tabular-nums">
                      {row.days}
                    </td>
                    <td className="px-2 py-1 text-right font-mono tabular-nums">
                      {row.precip.toFixed(2)}
                    </td>
                    <td className="px-2 py-1 text-right font-mono tabular-nums">
                      {row.naturalCleaning}
                    </td>
                    <td className="px-2 py-1">
                      <Input
                        type="number"
                        min={0}
                        value={row.manual}
                        onChange={(e: ChangeEvent<HTMLInputElement>) =>
                          updateManualCleaning(
                            i,
                            parseInt(e.target.value, 10) || 0,
                          )
                        }
                        className={`h-6 w-12 text-right font-mono mx-auto text-xs ${inputBaseClass} ${
                          !isEditMode ? 'bg-gray-50' : 'bg-white'
                        }`}
                        readOnly={!isEditMode}
                        disabled={!isEditMode}
                      />
                    </td>
                    <td className="px-2 py-1 text-right font-mono tabular-nums">
                      {row.snow}
                    </td>
                    <td className="px-2 py-1 text-right font-mono tabular-nums">
                      {row.snowDayPct.toFixed(1)}%
                    </td>
                    <td className="px-2 py-1 text-right font-mono tabular-nums">
                      {row.cleaningInterval}
                    </td>
                    <td className="px-2 py-1 text-right font-mono tabular-nums font-semibold text-emerald-800">
                      {row.monthlySoiling.toFixed(2)}%
                    </td>
                    <td className="px-2 py-1 text-right font-mono tabular-nums font-semibold text-emerald-800">
                      {row.snowLoss.toFixed(2)}%
                    </td>
                    <td className="px-2 py-1 text-right font-mono tabular-nums font-semibold">
                      {row.totalLoss.toFixed(2)}%
                    </td>
                  </tr>
                ))}
                <tr className="border-t-2 border-emerald-600 bg-gray-900 text-white font-semibold">
                  <td className="px-2 py-1.5 font-semibold text-xs">YEAR</td>
                  <td className="px-2 py-1.5 text-right font-mono tabular-nums text-xs">
                    {yearRow.days}
                  </td>
                  <td className="px-2 py-1.5 text-right font-mono tabular-nums text-xs">
                    {yearRow.precip.toFixed(2)}
                  </td>
                  <td className="px-2 py-1.5 text-right font-mono tabular-nums text-xs">
                    {yearRow.naturalCleaning}
                  </td>
                  <td className="px-2 py-1.5 text-right font-mono tabular-nums text-xs">
                    {yearRow.manual}
                  </td>
                  <td className="px-2 py-1.5 text-right font-mono tabular-nums text-xs">
                    {yearRow.snow}
                  </td>
                  <td className="px-2 py-1.5 text-right font-mono tabular-nums text-xs">
                    {yearRow.snowDayPct.toFixed(2)}%
                  </td>
                  <td className="px-2 py-1.5 text-right text-xs">—</td>
                  <td className="px-2 py-1.5 text-right font-mono tabular-nums text-xs">
                    {yearRow.monthlySoiling.toFixed(2)}%
                  </td>
                  <td className="px-2 py-1.5 text-right font-mono tabular-nums text-xs">
                    {yearRow.snowLoss.toFixed(2)}%
                  </td>
                  <td className="px-2 py-1.5 text-right font-mono tabular-nums text-xs">
                    {yearRow.totalLoss.toFixed(2)}%
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

