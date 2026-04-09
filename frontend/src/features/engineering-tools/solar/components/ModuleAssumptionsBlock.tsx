/**
 * Block 2A — PV Module Assumptions.
 */
import { useState, useEffect, useCallback, type ChangeEvent } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { FormMultiSelect } from '@/components/ui/form-multi-select';
import { engineeringToolsFetch, solarApiUrl } from '../lib/api';

interface ModuleAssumptionsData {
  module_make: string;
  module_model: string;
  module_wp: number | null;
  module_length_mm: number | null;
  module_width_mm: number | null;
  module_efficiency_pct: number | null;
  degradation_pct_per_year: number | null;
  module_master_id?: number | null;
}

interface ModuleAssumptionsBlockProps {
  location: { lat: number; lng: number } | null;
  /** When true (e.g. in wizard), show content expanded and hide expand/collapse button */
  defaultExpanded?: boolean;
}

interface ModuleMasterRecord {
  id: number;
  make: string;
  model: string;
  watt_peak: number;
  height_m: number;
  width_m: number;
  efficiency_pct: number;
  voc_v: number;
  vmp_v: number;
  temp_coeff_pmax_pct: number;
  temp_coeff_voc_pct: number;
  bifaciality_factor: number;
}

export default function ModuleAssumptionsBlock({ location, defaultExpanded }: ModuleAssumptionsBlockProps) {
  const [projectId, setProjectId] = useState<number | null>(null);
  const [form, setForm] = useState({
    module_make: '',
    module_model: '',
    module_wp: '',
    module_length_m: '',
    module_width_m: '',
    module_efficiency_pct: '',
    degradation_pct_per_year: '',
  });
  const [moduleMaster, setModuleMaster] = useState<ModuleMasterRecord[]>([]);
  const [selectedMake, setSelectedMake] = useState('');
  const [selectedModel, setSelectedModel] = useState('');
  const [selectedModuleId, setSelectedModuleId] = useState<number | null>(null);
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

  const loadAssumptions = useCallback(async (pid: number) => {
    setLoading(true);
    setError(null);
    try {
      const res = await engineeringToolsFetch(solarApiUrl(`api/pre-feasibility/module-assumptions/${pid}/`));
      if (!res.ok) {
        if (res.status === 404) return;
        setError('Failed to load module assumptions');
        return;
      }
      const data = (await res.json()) as ModuleAssumptionsData;
      setForm({
        module_make: data.module_make ?? '',
        module_model: data.module_model ?? '',
        module_wp: data.module_wp != null ? String(data.module_wp) : '',
        module_length_m: data.module_length_mm != null ? String(data.module_length_mm / 1000) : '',
        module_width_m: data.module_width_mm != null ? String(data.module_width_mm / 1000) : '',
        module_efficiency_pct: data.module_efficiency_pct != null ? String(data.module_efficiency_pct) : '',
        degradation_pct_per_year:
          data.degradation_pct_per_year != null ? String(data.degradation_pct_per_year) : '',
      });
      setSelectedMake(data.module_make ?? '');
      setSelectedModel(data.module_model ?? '');
      setSelectedModuleId(data.module_master_id ?? null);
      setIsEditMode(false);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await engineeringToolsFetch(solarApiUrl('api/pre-feasibility/module-master/'));
        if (!res.ok) return;
        const data = (await res.json()) as ModuleMasterRecord[];
        if (!cancelled) setModuleMaster(data);
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
          await loadAssumptions(id);
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Failed to load project');
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [location, ensureProject, loadAssumptions]);

  const update = (key: keyof typeof form, value: string) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  const makeOptions = Array.from(new Set(moduleMaster.map((m) => m.make))).sort();
  const modelOptions = moduleMaster.filter((m) => m.make === selectedMake);
  const selectedModule =
    moduleMaster.find((m) => m.id === selectedModuleId) ||
    moduleMaster.find((m) => m.make === selectedMake && m.model === selectedModel) ||
    null;

  const handleSave = async () => {
    if (projectId == null) return;
    setSaving(true);
    setError(null);
    try {
      const payload = {
        module_make: form.module_make,
        module_model: form.module_model,
        module_wp: Number(form.module_wp),
        module_length_mm: Math.round(Number(form.module_length_m) * 1000),
        module_width_mm: Math.round(Number(form.module_width_m) * 1000),
        module_efficiency_pct: form.module_efficiency_pct ? Number(form.module_efficiency_pct) : null,
        degradation_pct_per_year: Number(form.degradation_pct_per_year),
        module_master_id: selectedModuleId,
      };
      const res = await engineeringToolsFetch(solarApiUrl(`api/pre-feasibility/module-assumptions/${projectId}/`), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setError((data.detail as string) || 'Failed to save module assumptions');
        return;
      }
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
        <CardTitle className="text-base">PV Module Assumptions</CardTitle>
        {!defaultExpanded && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => setOpen((prev) => !prev)}
            aria-label={open ? 'Collapse module assumptions' : 'Expand module assumptions'}
            className="text-lg leading-none px-2"
          >
            {open ? '˄' : '˅'}
          </Button>
        )}
      </CardHeader>
      {(open || defaultExpanded) && (
        <CardContent className="space-y-2 p-2 pt-0">
          {loading && <p className="text-sm text-muted-foreground">Loading module assumptions…</p>}
          {error && <p className="text-sm text-destructive">{error}</p>}
          <div className="grid grid-cols-1 gap-x-4 gap-y-2 sm:grid-cols-2 lg:grid-cols-3">
            <div className="space-y-1">
              <FormMultiSelect
                label="Module Make"
                options={makeOptions.map((m) => ({ value: m, label: m }))}
                selected={selectedMake ? [selectedMake] : []}
                onChange={(vals) => {
                  const value = vals[0] ?? '';
                  setSelectedMake(value);
                  setSelectedModel('');
                  update('module_make', value);
                  update('module_model', '');
                }}
                placeholder={makeOptions.length ? 'Select module make' : 'No module masters available'}
                disabled={!isEditMode}
                singleSelect
              />
            </div>
            <div className="space-y-1">
              <FormMultiSelect
                label="Module Model"
                options={modelOptions.map((m) => ({
                  value: m.model,
                  label: `${m.model} (${m.watt_peak} Wp)`,
                }))}
                selected={selectedModel ? [selectedModel] : []}
                onChange={(vals) => {
                  const value = vals[0] ?? '';
                  setSelectedModel(value);
                  update('module_model', value);
                  const selected = moduleMaster.find(
                    (m) => m.make === selectedMake && m.model === value
                  );
                  if (selected) {
                    setSelectedModuleId(selected.id);
                    update('module_wp', String(selected.watt_peak));
                    update('module_length_m', String(selected.height_m));
                    update('module_width_m', String(selected.width_m));
                    update(
                      'module_efficiency_pct',
                      selected.efficiency_pct != null ? String(selected.efficiency_pct) : ''
                    );
                  }
                }}
                placeholder={
                  selectedMake
                    ? modelOptions.length
                      ? 'Select module model'
                      : 'No models for this make'
                    : 'Select make first'
                }
                disabled={!selectedMake || !isEditMode}
                singleSelect
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="mod-wp">Module Power (Wp)</Label>
              <Input
                id="mod-wp"
                type="number"
                min={1}
                max={1000}
                value={form.module_wp}
                readOnly
                placeholder="e.g. 540"
                className="h-8 text-sm"
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="mod-len">Module Length (m)</Label>
              <Input
                id="mod-len"
                type="number"
                min={0.001}
                step={0.001}
                value={form.module_length_m}
                readOnly
                placeholder="e.g. 2.465"
                className="h-8 text-sm"
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="mod-wid">Module Width (m)</Label>
              <Input
                id="mod-wid"
                type="number"
                min={0.001}
                step={0.001}
                value={form.module_width_m}
                readOnly
                placeholder="e.g. 1.134"
                className="h-8 text-sm"
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="mod-eff">Module Efficiency (%)</Label>
              <Input
                id="mod-eff"
                type="number"
                min={0}
                max={30}
                step={0.1}
                value={form.module_efficiency_pct}
                readOnly
                placeholder="Optional"
                className="h-8 text-sm"
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="mod-deg">Annual Degradation (%/year)</Label>
              <Input
                id="mod-deg"
                type="number"
                min={0}
                max={2}
                step={0.01}
                value={form.degradation_pct_per_year}
                onChange={(e: ChangeEvent<HTMLInputElement>) =>
                  update('degradation_pct_per_year', e.target.value)
                }
                placeholder="e.g. 0.5"
                readOnly={!isEditMode}
                disabled={!isEditMode}
                className={!isEditMode ? 'h-8 text-sm bg-muted' : 'h-8 text-sm'}
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="mod-voc">Open-circuit Voltage Voc (V)</Label>
              <Input
                id="mod-voc"
                type="number"
                readOnly
                value={selectedModule ? String(selectedModule.voc_v) : ''}
                placeholder="Auto from module master"
                className="h-8 text-sm"
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="mod-vmp">Maximum Power Voltage Vmp (V)</Label>
              <Input
                id="mod-vmp"
                type="number"
                readOnly
                value={selectedModule ? String(selectedModule.vmp_v) : ''}
                placeholder="Auto from module master"
                className="h-8 text-sm"
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="mod-tc-pmax">Temperature Coefficient of Pmax (%/°C)</Label>
              <Input
                id="mod-tc-pmax"
                type="number"
                readOnly
                value={selectedModule ? String(selectedModule.temp_coeff_pmax_pct) : ''}
                placeholder="Auto from module master"
                className="h-8 text-sm"
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="mod-tc-voc">Temperature Coefficient of Voc (%/°C)</Label>
              <Input
                id="mod-tc-voc"
                type="number"
                readOnly
                value={selectedModule ? String(selectedModule.temp_coeff_voc_pct) : ''}
                placeholder="Auto from module master"
                className="h-8 text-sm"
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="mod-bifaciality">Bifaciality Factor</Label>
              <Input
                id="mod-bifaciality"
                type="number"
                step={0.01}
                readOnly
                value={selectedModule ? String(selectedModule.bifaciality_factor) : ''}
                placeholder="Auto from module master"
                className="h-8 text-sm"
              />
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2 mt-1">
            {isEditMode ? (
              <Button onClick={handleSave} disabled={saving} className="text-white">
                {saving ? 'Saving…' : 'Save Module Assumptions'}
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
