/**
 * Block 1 — Site & Orientation (Plant Orientation & Geometry).
 */
import { useState, useEffect, useCallback, type ChangeEvent } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { engineeringToolsFetch, solarApiUrl } from '../lib/api';

const TILT_DEFAULT = 25;
const AZIMUTH_DEFAULT = 180;
const SOILING_DEFAULT = 3;

export interface SiteOrientationData {
  latitude: number;
  longitude: number;
  tilt_deg: number | null;
  azimuth_deg: number | null;
  structure_height_m: number | null;
  soiling_rate_pct: number | null;
}

interface SiteOrientationBlockProps {
  location: { lat: number; lng: number } | null;
  /** When true (e.g. in wizard), show content expanded and hide expand/collapse button */
  defaultExpanded?: boolean;
}

export default function SiteOrientationBlock({ location, defaultExpanded }: SiteOrientationBlockProps) {
  const [projectId, setProjectId] = useState<number | null>(null);
  const [tilt, setTilt] = useState<string>(String(TILT_DEFAULT));
  const [azimuth, setAzimuth] = useState<string>(String(AZIMUTH_DEFAULT));
  const [structureHeight, setStructureHeight] = useState<string>('');
  const [soiling, setSoiling] = useState<string>(String(SOILING_DEFAULT));
  const [saving, setSaving] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
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

  const loadOrientation = useCallback(async (pid: number) => {
    setLoadError(null);
    const res = await engineeringToolsFetch(solarApiUrl(`api/pre-feasibility/site-orientation/${pid}/`));
    if (!res.ok) {
      if (res.status === 404) return;
      setLoadError('Failed to load orientation');
      return;
    }
    const data = (await res.json()) as SiteOrientationData;
    if (data.tilt_deg != null) setTilt(String(data.tilt_deg));
    if (data.azimuth_deg != null) setAzimuth(String(data.azimuth_deg));
    if (data.structure_height_m != null)
      setStructureHeight(String(data.structure_height_m));
    if (data.soiling_rate_pct != null) setSoiling(String(data.soiling_rate_pct));
    setIsEditMode(false);
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
          await loadOrientation(id);
        }
      } catch (e) {
        if (!cancelled) setLoadError(e instanceof Error ? e.message : 'Failed to load project');
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [location, ensureProject, loadOrientation]);

  const handleSave = async () => {
    if (projectId == null || !location) return;
    setSaving(true);
    setSaveError(null);
    try {
      const payload = {
        latitude: location.lat,
        longitude: location.lng,
        tilt_deg: Number(tilt),
        azimuth_deg: Number(azimuth),
        structure_height_m: structureHeight.trim() === '' ? null : Number(structureHeight),
        soiling_rate_pct: Number(soiling),
      };
      const res = await engineeringToolsFetch(solarApiUrl(`api/pre-feasibility/site-orientation/${projectId}/`), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setSaveError((data.detail as string) || 'Failed to save orientation');
        return;
      }
      setSaveError(null);
      setIsEditMode(false);
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : 'Request failed');
    } finally {
      setSaving(false);
    }
  };

  if (!location) {
    return (
      <Card className="border-0 shadow-none">
        <CardHeader className="p-2 pb-1">
          <CardTitle className="text-base">Plant Orientation & Geometry</CardTitle>
        </CardHeader>
        <CardContent className="p-2 pt-0">
          <p className="text-sm text-muted-foreground">
            Select a location in Step 1 to enter orientation and geometry.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-0 shadow-none">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 p-2 pb-1">
        <CardTitle className="text-base">Plant Orientation & Geometry</CardTitle>
        {!defaultExpanded && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => setOpen((prev) => !prev)}
            aria-label={open ? 'Collapse plant orientation' : 'Expand plant orientation'}
            className="text-lg leading-none px-2"
          >
            {open ? '˄' : '˅'}
          </Button>
        )}
      </CardHeader>
      {(open || defaultExpanded) && (
        <CardContent className="space-y-2 p-2 pt-0">
          {loadError && <p className="text-sm text-destructive">{loadError}</p>}
          <div className="grid grid-cols-1 gap-x-4 gap-y-2 sm:grid-cols-2 lg:grid-cols-3">
            <div className="space-y-1">
              <Label htmlFor="site-lat">Latitude (°)</Label>
              <Input id="site-lat" type="text" value={location.lat} readOnly disabled className="h-8 text-sm bg-muted" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="site-lng">Longitude (°)</Label>
              <Input id="site-lng" type="text" value={location.lng} readOnly disabled className="h-8 text-sm bg-muted" />
            </div>
            <div className="space-y-1">
              <Label htmlFor="site-tilt">Tilt (°)</Label>
              <Input
                id="site-tilt"
                type="number"
                min={5}
                max={40}
                step={0.5}
                value={tilt}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setTilt(e.target.value)}
                placeholder="5–40"
                readOnly={!isEditMode}
                disabled={!isEditMode}
                className={!isEditMode ? 'h-8 text-sm bg-muted' : 'h-8 text-sm'}
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="site-azimuth">Azimuth (°)</Label>
              <Input
                id="site-azimuth"
                type="number"
                min={0}
                max={360}
                step={1}
                value={azimuth}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setAzimuth(e.target.value)}
                placeholder="0–360"
                readOnly={!isEditMode}
                disabled={!isEditMode}
                className={!isEditMode ? 'h-8 text-sm bg-muted' : 'h-8 text-sm'}
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="site-height">Structure Height (m)</Label>
              <Input
                id="site-height"
                type="number"
                min={0}
                step={0.1}
                value={structureHeight}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setStructureHeight(e.target.value)}
                placeholder="Optional"
                readOnly={!isEditMode}
                disabled={!isEditMode}
                className={!isEditMode ? 'h-8 text-sm bg-muted' : 'h-8 text-sm'}
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="site-soiling">Soiling Rate (%)</Label>
              <Input
                id="site-soiling"
                type="number"
                min={0}
                max={10}
                step={0.1}
                value={soiling}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setSoiling(e.target.value)}
                placeholder="0–10"
                readOnly={!isEditMode}
                disabled={!isEditMode}
                className={!isEditMode ? 'h-8 text-sm bg-muted' : 'h-8 text-sm'}
              />
            </div>
          </div>
          {saveError && <p className="text-sm text-destructive">{saveError}</p>}
          <div className="flex flex-wrap items-center gap-2 mt-1">
            {isEditMode ? (
              <Button onClick={handleSave} disabled={saving} className="text-white">
                {saving ? 'Saving…' : 'Save Orientation'}
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
