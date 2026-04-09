/**
 * System Configuration — high-level array configuration.
 * Number of modules in series, array configuration (Landscape/Portrait), derived dimensions.
 */
import { useState, useEffect, useCallback, type ChangeEvent } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { FormMultiSelect } from '@/components/ui/form-multi-select';
import { engineeringToolsFetch, solarApiUrl } from '../lib/api';

interface ModuleAssumptionsData {
  module_length_mm: number | null;
  module_width_mm: number | null;
}

interface SiteOrientationData {
  tilt_deg: number | null;
}

interface StringConfigurationData {
  min_modules_in_series: number | null;
  max_modules_in_series: number | null;
}

/** Layout params derived from system config, reported to parent for PV Layout export */
export interface SystemConfigLayoutParams {
  arrayConfig: '' | 'landscape' | 'portrait';
  modulesInSeries: string;
  tableLengthM: string;
  arrayProjectionLengthM: string;
  interrowSpacingM: string;
  structureGapM: string;
  boundarySetbackM: string;
  dcAcRatio: string;
}

interface SystemConfigurationBlockProps {
  location: { lat: number; lng: number } | null;
  onLayoutParamsChange?: (params: SystemConfigLayoutParams) => void;
  /** When true (e.g. in wizard), show content expanded and hide expand/collapse button */
  defaultExpanded?: boolean;
}

export default function SystemConfigurationBlock({
  location,
  onLayoutParamsChange,
  defaultExpanded,
}: SystemConfigurationBlockProps) {
  const [open, setOpen] = useState(!!defaultExpanded);
  const [isEditMode, setIsEditMode] = useState(false);
  const [arrangement, setArrangement] = useState<'' | 'landscape' | 'portrait'>('landscape');
  const [modulesInSeries, setModulesInSeries] = useState<string>('24');
  const [, setProjectId] = useState<number | null>(null);
  const [moduleHeightM, setModuleHeightM] = useState<number | null>(null);
  const [moduleWidthM, setModuleWidthM] = useState<number | null>(null);
  const [tiltDeg, setTiltDeg] = useState<number | null>(null);
  const [distanceBetweenModulesM, setDistanceBetweenModulesM] = useState<string>('0.02');
  const [structureGapM, setStructureGapM] = useState<string>('0.2');
  const [interrowSpacingM, setInterrowSpacingM] = useState<string>('3.5');
  const [boundarySetbackM, setBoundarySetbackM] = useState<string>('1.5');
  const [dcAcRatio, setDcAcRatio] = useState<string>('1.2');
  const [minModulesInSeries, setMinModulesInSeries] = useState<number | null>(null);
  const [maxModulesInSeries, setMaxModulesInSeries] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);

  const ensureProject = useCallback(async (lat: number, lng: number): Promise<number | null> => {
    const res = await engineeringToolsFetch(solarApiUrl('api/projects/'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ latitude: lat, longitude: lng }),
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error((data.detail as string) || 'Failed to get or create project');
    }
    const data = await res.json();
    return data.id as number;
  }, []);

  const loadModuleDimensions = useCallback(async (pid: number) => {
    const res = await engineeringToolsFetch(solarApiUrl(`api/pre-feasibility/module-assumptions/${pid}/`));
    if (res.ok) {
      const data = (await res.json()) as ModuleAssumptionsData;
      if (data.module_length_mm != null) setModuleHeightM(data.module_length_mm / 1000);
      if (data.module_width_mm != null) setModuleWidthM(data.module_width_mm / 1000);
    }
    const resSite = await engineeringToolsFetch(solarApiUrl(`api/pre-feasibility/site-orientation/${pid}/`));
    if (resSite.ok) {
      const site = (await resSite.json()) as SiteOrientationData;
      if (site.tilt_deg != null) setTiltDeg(site.tilt_deg);
    }
    const resString = await engineeringToolsFetch(
      solarApiUrl(`api/pre-feasibility/string-configuration/${pid}/`)
    );
    if (resString.ok) {
      const stringCfg = (await resString.json()) as StringConfigurationData;
      setMinModulesInSeries(stringCfg.min_modules_in_series ?? null);
      setMaxModulesInSeries(stringCfg.max_modules_in_series ?? null);
    }
  }, []);

  useEffect(() => {
    if (!location) {
      setProjectId(null);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const id = await ensureProject(location.lat, location.lng);
        if (!cancelled && id != null) {
          setProjectId(id);
          await loadModuleDimensions(id);
        }
      } catch {
        /* ignore */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [location, ensureProject, loadModuleDimensions]);

  // When the block is opened (or reopened), refresh dimensions and constraints
  // from the latest saved assumptions & configs for this project.
  useEffect(() => {
    if (!location) return;
    if (!open) return;
    // We don't keep projectId in state, but ensureProject+loadModuleDimensions
    // will resolve the same project for the current coordinates.
    (async () => {
      try {
        const id = await ensureProject(location.lat, location.lng);
        if (id != null) {
          await loadModuleDimensions(id);
        }
      } catch {
        /* ignore */
      }
    })();
  }, [open, location, ensureProject, loadModuleDimensions]);

  const modulesVertical =
    arrangement === 'landscape' ? 4 : arrangement === 'portrait' ? 2 : '';

  let arrayLengthM = '';
  let arrayLengthValue: number | null = null;
  if (arrangement === 'portrait' && moduleHeightM != null) {
    arrayLengthValue = 2 * moduleHeightM + 0.02;
    arrayLengthM = arrayLengthValue.toFixed(3);
  } else if (arrangement === 'landscape' && moduleWidthM != null) {
    arrayLengthValue = 4 * moduleWidthM + 0.06;
    arrayLengthM = arrayLengthValue.toFixed(3);
  }

  let arrayProjectionLengthM = '';
  let arrayProjectionValue: number | null = null;
  if (arrayLengthValue != null && tiltDeg != null) {
    const rad = (tiltDeg * Math.PI) / 180;
    arrayProjectionValue = arrayLengthValue * Math.cos(rad);
    arrayProjectionLengthM = arrayProjectionValue.toFixed(3);
  }

  let installationPitchM = '';
  const interrow = parseFloat(interrowSpacingM);
  if (!Number.isNaN(interrow) && arrayProjectionValue != null) {
    installationPitchM = (interrow + arrayProjectionValue).toFixed(3);
  }

  let tableLengthM = '';
  const nSeries = parseInt(modulesInSeries, 10);
  const gapM = parseFloat(distanceBetweenModulesM);
  if (!Number.isNaN(nSeries) && nSeries >= 1 && !Number.isNaN(gapM) && gapM >= 0) {
    if (arrangement === 'portrait' && moduleWidthM != null) {
      tableLengthM = (nSeries * moduleWidthM + gapM * (nSeries - 1)).toFixed(3);
    } else if (arrangement === 'landscape' && moduleHeightM != null) {
      tableLengthM = ((nSeries / 2) * moduleHeightM + gapM * (nSeries - 1)).toFixed(3);
    }
  }

  useEffect(() => {
    if (!onLayoutParamsChange || !location) return;
    onLayoutParamsChange({
      arrayConfig: arrangement,
      modulesInSeries,
      tableLengthM,
      arrayProjectionLengthM,
      interrowSpacingM,
      structureGapM,
      boundarySetbackM,
      dcAcRatio,
    });
  }, [
    onLayoutParamsChange,
    location,
    arrangement,
    modulesInSeries,
    tableLengthM,
    arrayProjectionLengthM,
    interrowSpacingM,
    structureGapM,
    boundarySetbackM,
    dcAcRatio,
  ]);

  if (!location) return null;

  const handleSave = () => {
    setSaving(true);
    setTimeout(() => {
      setSaving(false);
      setIsEditMode(false);
    }, 200);
  };

  return (
    <Card className="border-0 shadow-none">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 p-2 pb-1">
        <CardTitle className="text-base">System Configuration</CardTitle>
        {!defaultExpanded && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => setOpen((prev) => !prev)}
            aria-label={open ? 'Collapse system configuration' : 'Expand system configuration'}
            className="text-lg leading-none px-2"
          >
            {open ? '˄' : '˅'}
          </Button>
        )}
      </CardHeader>
      {(open || defaultExpanded) && (
        <CardContent className="space-y-2 p-2 pt-0">
          <div className="grid grid-cols-1 gap-x-4 gap-y-2 sm:grid-cols-2 lg:grid-cols-3">
            <div className="space-y-1">
              <Label htmlFor="modules-series">
                Number of Modules in Series
                {minModulesInSeries != null && maxModulesInSeries != null && (
                  <span className="text-xs text-muted-foreground ml-2">
                    (Range: {minModulesInSeries} – {maxModulesInSeries})
                  </span>
                )}
              </Label>
              <Input
                id="modules-series"
                type="number"
                min={minModulesInSeries ?? 1}
                max={maxModulesInSeries ?? undefined}
                value={modulesInSeries}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setModulesInSeries(e.target.value)}
                placeholder={
                  minModulesInSeries != null && maxModulesInSeries != null
                    ? `${minModulesInSeries} – ${maxModulesInSeries}`
                    : 'Enter modules per string'
                }
                readOnly={!isEditMode}
                disabled={!isEditMode}
                className={
                  !isEditMode
                    ? 'h-8 text-sm bg-muted'
                    : modulesInSeries &&
                      ((minModulesInSeries != null &&
                        parseInt(modulesInSeries, 10) < minModulesInSeries) ||
                        (maxModulesInSeries != null &&
                          parseInt(modulesInSeries, 10) > maxModulesInSeries))
                    ? 'h-8 text-sm border-destructive'
                    : 'h-8 text-sm'
                }
              />
              {modulesInSeries &&
                minModulesInSeries != null &&
                parseInt(modulesInSeries, 10) < minModulesInSeries && (
                  <p className="text-xs text-destructive">
                    Value is below minimum ({minModulesInSeries})
                  </p>
                )}
              {modulesInSeries &&
                maxModulesInSeries != null &&
                parseInt(modulesInSeries, 10) > maxModulesInSeries && (
                  <p className="text-xs text-destructive">
                    Value exceeds maximum ({maxModulesInSeries})
                  </p>
                )}
            </div>
            <div className="space-y-1">
              <FormMultiSelect
                label="Array Configuration"
                options={[
                  { value: 'landscape', label: 'Landscape' },
                  { value: 'portrait', label: 'Portrait' },
                ]}
                selected={arrangement ? [arrangement] : []}
                onChange={(vals) => {
                  const v = vals[0];
                  setArrangement(
                    v === 'landscape' || v === 'portrait' ? v : ''
                  );
                }}
                placeholder="Select arrangement"
                disabled={!isEditMode}
                singleSelect
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="modules-vertical">Modules in Vertical</Label>
              <Input
                id="modules-vertical"
                type="number"
                readOnly
                value={modulesVertical !== '' ? String(modulesVertical) : ''}
                placeholder="Auto from array configuration"
                className="h-8 text-sm"
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="distance-between-modules">
                Distance between Adjacent Modules (m)
              </Label>
              <Input
                id="distance-between-modules"
                type="number"
                min={0}
                step={0.01}
                value={distanceBetweenModulesM}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setDistanceBetweenModulesM(e.target.value)}
                placeholder="User input"
                readOnly={!isEditMode}
                disabled={!isEditMode}
                className={!isEditMode ? 'h-8 text-sm bg-muted' : 'h-8 text-sm'}
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="structure-gap">Structure Gap (m)</Label>
              <Input
                id="structure-gap"
                type="number"
                min={0}
                step={0.01}
                value={structureGapM}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setStructureGapM(e.target.value)}
                placeholder="Default 0.2"
                readOnly={!isEditMode}
                disabled={!isEditMode}
                className={!isEditMode ? 'h-8 text-sm bg-muted' : 'h-8 text-sm'}
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="interrow-spacing">Interrow / Row Spacing (m)</Label>
              <Input
                id="interrow-spacing"
                type="number"
                min={0}
                step={0.01}
                value={interrowSpacingM}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setInterrowSpacingM(e.target.value)}
                placeholder="User input"
                readOnly={!isEditMode}
                disabled={!isEditMode}
                className={!isEditMode ? 'h-8 text-sm bg-muted' : 'h-8 text-sm'}
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="boundary-setback">Boundary Setback (m)</Label>
              <Input
                id="boundary-setback"
                type="number"
                min={0}
                step={0.1}
                value={boundarySetbackM}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setBoundarySetbackM(e.target.value)}
                placeholder="User input"
                readOnly={!isEditMode}
                disabled={!isEditMode}
                className={!isEditMode ? 'h-8 text-sm bg-muted' : 'h-8 text-sm'}
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="dc-ac-ratio">DC : AC Ratio</Label>
              <Input
                id="dc-ac-ratio"
                type="number"
                min={1}
                max={2}
                step={0.01}
                value={dcAcRatio}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setDcAcRatio(e.target.value)}
                placeholder="Default 1.2"
                readOnly={!isEditMode}
                disabled={!isEditMode}
                className={!isEditMode ? 'h-8 text-sm bg-muted' : 'h-8 text-sm'}
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="table-length">Table Length (m)</Label>
              <Input
                id="table-length"
                type="number"
                readOnly
                value={tableLengthM}
                placeholder={
                  arrangement && modulesInSeries && distanceBetweenModulesM !== ''
                    ? 'Auto from modules in series, config & module dimensions'
                    : 'Set modules in series, config & distance between modules'
                }
                className="h-8 text-sm"
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="array-length">Array Length (m)</Label>
              <Input
                id="array-length"
                type="number"
                readOnly
                value={arrayLengthM}
                placeholder={
                  arrangement && (moduleHeightM != null || moduleWidthM != null)
                    ? 'Auto from configuration & module dimensions'
                    : 'Select module + configuration'
                }
                className="h-8 text-sm"
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="array-projection">Array Projection Length (m)</Label>
              <Input
                id="array-projection"
                type="number"
                readOnly
                value={arrayProjectionLengthM}
                placeholder={
                  arrayLengthM && tiltDeg != null
                    ? 'Auto from array length & tilt'
                    : 'Requires array length and tilt'
                }
                className="h-8 text-sm"
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="installation-pitch">Installation Pitch (m)</Label>
              <Input
                id="installation-pitch"
                type="number"
                readOnly
                value={installationPitchM}
                placeholder={
                  arrayProjectionLengthM && interrowSpacingM
                    ? 'Auto from interrow spacing + projection'
                    : 'Requires interrow spacing & projection'
                }
                className="h-8 text-sm"
              />
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2 mt-1">
            {isEditMode ? (
              <Button onClick={handleSave} disabled={saving} className="text-white">
                {saving ? 'Saving…' : 'Save System Configuration'}
              </Button>
            ) : (
              <>
                <Button type="button" disabled className="bg-green-600 hover:bg-green-600 text-white">
                  Saved
                </Button>
                <Button type="button" variant="outline" onClick={() => setIsEditMode(true)}>
                  Edit
                </Button>
              </>
            )}
          </div>
        </CardContent>
      )}
    </Card>
  );
}
