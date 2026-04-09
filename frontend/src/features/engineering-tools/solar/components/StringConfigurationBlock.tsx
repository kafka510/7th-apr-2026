/**
 * Block 2B — DC String Configuration.
 * Modules per string, strings per inverter, optional DC/AC ratio and max system voltage.
 */
import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { FormMultiSelect } from '@/components/ui/form-multi-select';
import { engineeringToolsFetch, solarApiUrl } from '../lib/api';

interface StringConfigurationData {
  module_master_id: number | null;
  inverter_master_id: number | null;
  inverter_make: string | null;
  inverter_model: string | null;
  min_modules_in_series: number | null;
  max_modules_in_series: number | null;
  design_modules_in_series: number | null;
  strings_per_inverter: number | null;
  dc_ac_ratio: number | null;
}

interface StringConfigurationBlockProps {
  location: { lat: number; lng: number } | null;
  onInverterRatedPowerChange?: (kw: number | null) => void;
  /** When true (e.g. in wizard), show content expanded and hide expand/collapse button */
  defaultExpanded?: boolean;
}

interface InverterMasterRecord {
  id: number;
  make: string;
  model: string;
  ac_capacity_kw: number;
  efficiency_pct: number;
  mppt_min_v: number;
  mppt_max_v: number;
  pcs_nameplate: string;
}

export default function StringConfigurationBlock({
  location,
  onInverterRatedPowerChange,
  defaultExpanded,
}: StringConfigurationBlockProps) {
  const [projectId, setProjectId] = useState<number | null>(null);
  const [form, setForm] = useState({
    design_modules_in_series: '',
    strings_per_inverter: '',
    dc_ac_ratio: '',
  });
  const [inverterMaster, setInverterMaster] = useState<InverterMasterRecord[]>([]);
  const [selectedInverterMake, setSelectedInverterMake] = useState('');
  const [selectedInverterModel, setSelectedInverterModel] = useState('');
  const [selectedInverterId, setSelectedInverterId] = useState<number | null>(null);
  const [minModules, setMinModules] = useState<number | null>(null);
  const [maxModules, setMaxModules] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState(!!defaultExpanded);
  const [isEditMode, setIsEditMode] = useState(true);

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

  const loadConfiguration = useCallback(async (pid: number) => {
    setLoading(true);
    setError(null);
    try {
      const res = await engineeringToolsFetch(solarApiUrl(`api/pre-feasibility/string-configuration/${pid}/`));
      if (!res.ok) {
        if (res.status === 404) return;
        setError('Failed to load string configuration');
        return;
      }
      const data = (await res.json()) as StringConfigurationData;
      setForm({
        design_modules_in_series:
          data.design_modules_in_series != null ? String(data.design_modules_in_series) : '',
        strings_per_inverter:
          data.strings_per_inverter != null ? String(data.strings_per_inverter) : '',
        dc_ac_ratio: data.dc_ac_ratio != null ? String(data.dc_ac_ratio) : '',
      });
      setSelectedInverterId(data.inverter_master_id ?? null);
      setSelectedInverterMake(data.inverter_make ?? '');
      setSelectedInverterModel(data.inverter_model ?? '');
      setMinModules(data.min_modules_in_series ?? null);
      setMaxModules(data.max_modules_in_series ?? null);
      setIsEditMode(false);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await engineeringToolsFetch(solarApiUrl('api/pre-feasibility/inverter-master/'));
        if (!res.ok) return;
        const data = (await res.json()) as InverterMasterRecord[];
        if (!cancelled) setInverterMaster(data);
      } catch {
        /* ignore */
      }
    })();
    return () => {
      cancelled = true;
    };
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
          await loadConfiguration(id);
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Failed to load project');
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [location, ensureProject, loadConfiguration]);

  const inverterMakeOptions = Array.from(new Set(inverterMaster.map((i) => i.make))).sort();
  const inverterModelOptions = inverterMaster.filter((i) => i.make === selectedInverterMake);
  const selectedInverter =
    inverterMaster.find((i) => i.id === selectedInverterId) ||
    inverterMaster.find(
      (i) => i.make === selectedInverterMake && i.model === selectedInverterModel
    ) ||
    null;

  useEffect(() => {
    onInverterRatedPowerChange?.(selectedInverter?.ac_capacity_kw ?? null);
  }, [selectedInverter, onInverterRatedPowerChange]);

  // When user selects an inverter, fetch min/max from backend (no save required) so they appear immediately
  useEffect(() => {
    if (projectId == null || selectedInverterId == null) return;
    let cancelled = false;
    (async () => {
      try {
        const res = await engineeringToolsFetch(
          solarApiUrl(
            `api/pre-feasibility/string-configuration/${projectId}/?inverter_master_id=${selectedInverterId}`
          )
        );
        if (!res.ok || cancelled) return;
        const data = (await res.json()) as StringConfigurationData;
        if (!cancelled && data.min_modules_in_series != null && data.max_modules_in_series != null) {
          setMinModules(data.min_modules_in_series);
          setMaxModules(data.max_modules_in_series);
        }
      } catch {
        /* ignore */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [projectId, selectedInverterId]);

  const handleSave = async () => {
    if (projectId == null) return;
    if (selectedInverterId == null) {
      setError('Select an inverter make and model from the list above.');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const payload = {
        design_modules_in_series: form.design_modules_in_series
          ? Number(form.design_modules_in_series)
          : null,
        strings_per_inverter: form.strings_per_inverter
          ? Number(form.strings_per_inverter)
          : null,
        dc_ac_ratio: form.dc_ac_ratio ? Number(form.dc_ac_ratio) : null,
        inverter_master_id: selectedInverterId,
      };
      const res = await engineeringToolsFetch(
        solarApiUrl(`api/pre-feasibility/string-configuration/${projectId}/`),
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        }
      );
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setError((data.detail as string) || 'Failed to save string configuration');
        return;
      }
      const cfg = data as StringConfigurationData;
      setMinModules(cfg.min_modules_in_series ?? null);
      setMaxModules(cfg.max_modules_in_series ?? null);
      setForm((prev) => ({
        ...prev,
        design_modules_in_series:
          cfg.design_modules_in_series != null
            ? String(cfg.design_modules_in_series)
            : prev.design_modules_in_series,
        strings_per_inverter:
          cfg.strings_per_inverter != null
            ? String(cfg.strings_per_inverter)
            : prev.strings_per_inverter,
        dc_ac_ratio: cfg.dc_ac_ratio != null ? String(cfg.dc_ac_ratio) : prev.dc_ac_ratio,
      }));
      setIsEditMode(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Request failed');
    } finally {
      setSaving(false);
    }
  };

  if (!location) return null;

  return (
    <Card className="border-0 shadow-none">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 p-2 pb-1">
        <CardTitle className="text-base">DC String Configuration</CardTitle>
        {!defaultExpanded && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => setOpen((prev) => !prev)}
            aria-label={open ? 'Collapse string configuration' : 'Expand string configuration'}
            className="text-lg leading-none px-2"
          >
            {open ? '˄' : '˅'}
          </Button>
        )}
      </CardHeader>
      {(open || defaultExpanded) && (
        <CardContent className="space-y-2 p-2 pt-0">
          {loading && (
            <p className="text-sm text-muted-foreground">Loading string configuration…</p>
          )}
          {error && <p className="text-sm text-destructive">{error}</p>}
          <div className="grid grid-cols-1 gap-x-4 gap-y-2 sm:grid-cols-2 lg:grid-cols-3">
            <div className="space-y-1">
              <FormMultiSelect
                label="Inverter Make"
                options={inverterMakeOptions.map((m) => ({ value: m, label: m }))}
                selected={selectedInverterMake ? [selectedInverterMake] : []}
                onChange={(vals) => {
                  const value = vals[0] ?? '';
                  setSelectedInverterMake(value);
                  setSelectedInverterModel('');
                  setSelectedInverterId(null);
                }}
                placeholder={
                  inverterMakeOptions.length
                    ? 'Select inverter make'
                    : 'No inverter masters available'
                }
                disabled={!isEditMode}
                singleSelect
              />
            </div>
            <div className="space-y-1">
              <FormMultiSelect
                label="Inverter Model"
                options={inverterModelOptions.map((inv) => ({
                  value: inv.model,
                  label: `${inv.model} (${inv.ac_capacity_kw} kW)`,
                }))}
                selected={selectedInverterModel ? [selectedInverterModel] : []}
                onChange={(vals) => {
                  const value = vals[0] ?? '';
                  setSelectedInverterModel(value);
                  const inv = inverterMaster.find(
                    (i) => i.make === selectedInverterMake && i.model === value
                  );
                  setSelectedInverterId(inv ? inv.id : null);
                }}
                placeholder={
                  selectedInverterMake
                    ? inverterModelOptions.length
                      ? 'Select inverter model'
                      : 'No models for this make'
                    : 'Select make first'
                }
                disabled={!selectedInverterMake || !isEditMode}
                singleSelect
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="min-modules">Min Modules in Series</Label>
              <Input
                id="min-modules"
                type="number"
                readOnly
                value={minModules != null ? String(minModules) : ''}
                placeholder="Auto-calculated"
                className="h-8 text-sm"
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="max-modules">Max Modules in Series</Label>
              <Input
                id="max-modules"
                type="number"
                readOnly
                value={maxModules != null ? String(maxModules) : ''}
                placeholder="Auto-calculated"
                className="h-8 text-sm"
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="inverter-rated-power">Inverter Rated Power (kW)</Label>
              <Input
                id="inverter-rated-power"
                type="number"
                readOnly
                value={selectedInverter != null ? String(selectedInverter.ac_capacity_kw) : ''}
                placeholder="Select inverter make & model (from inverter master)"
                className="h-8 text-sm"
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="mppt-min-v">Minimum input Voltage (MPPT) (V)</Label>
              <Input
                id="mppt-min-v"
                type="number"
                readOnly
                value={selectedInverter ? String(selectedInverter.mppt_min_v) : ''}
                placeholder="Auto from inverter master"
                className="h-8 text-sm"
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="mppt-max-v">Maximum input Voltage (MPPT) (V)</Label>
              <Input
                id="mppt-max-v"
                type="number"
                readOnly
                value={selectedInverter ? String(selectedInverter.mppt_max_v) : ''}
                placeholder="Auto from inverter master"
                className="h-8 text-sm"
              />
            </div>
          </div>
          {!selectedInverterId && isEditMode && (
            <p className="text-sm text-muted-foreground">
              Save Module Assumptions first (with a module selected from the list), then select an inverter make and model above. Min/Max modules in series will appear automatically.
            </p>
          )}
          <div className="flex flex-wrap items-center gap-2 mt-1">
            {isEditMode ? (
              <Button
                onClick={handleSave}
                disabled={saving || selectedInverterId == null}
                className="text-white"
              >
                {saving ? 'Saving…' : 'Save String Configuration'}
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
