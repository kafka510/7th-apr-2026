import { useState, useEffect, type ChangeEvent, type KeyboardEvent } from 'react';
import { Type, Navigation, ExternalLink, FileSpreadsheet, Map, MapPin, ThermometerSun, MapPinned } from 'lucide-react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import FileUpload from './FileUpload';
import SolarGISMonthlyTable from './SolarGISMonthlyTable';
import { KpiSummaryCard } from './KpiSummaryCard';
import type { StepCompleteState } from './StepperHeader';

const LAT_MIN = -90;
const LAT_MAX = 90;
const LON_MIN = -180;
const LON_MAX = 180;

/** Minimal type compatible with SolarInsightPage's SolarGISMonthlyResponse. */
export interface SolarGISMonthlyResponse {
  location?: string | null;
  site_name?: string | null;
  lat: number;
  lng: number;
  data_type: string;
  records: Array<{ month: string; ghi: number; dni: number; dif: number; temp: number }>;
}

interface StepPanelProps {
  currentStep: number;
  location: { lat: number; lng: number } | null;
  onLocationSelect: (lat: number, lng: number) => void;
  csvFile: File | null;
  onCsvFileSelect: (file: File | null) => void;
  isParsingSolargis: boolean;
  solargisError: string | null;
  solargisPreview: SolarGISMonthlyResponse | null;
  kmlFile: File | null;
  onKmlFileSelect: (file: File | null) => void;
}

export function StepPanel({
  currentStep,
  location,
  onLocationSelect,
  csvFile,
  onCsvFileSelect,
  isParsingSolargis,
  solargisError,
  solargisPreview,
  kmlFile,
  onKmlFileSelect,
}: StepPanelProps) {
  const [inputLat, setInputLat] = useState('');
  const [inputLng, setInputLng] = useState('');
  const [coordError, setCoordError] = useState<string | null>(null);

  useEffect(() => {
    if (location) {
      setInputLat(location.lat.toString());
      setInputLng(location.lng.toString());
      setCoordError(null);
    }
  }, [location?.lat, location?.lng]);

  const parseAndValidateCoordinates = (): { lat: number; lng: number } | null => {
    setCoordError(null);
    const lat = parseFloat(inputLat);
    const lng = parseFloat(inputLng);
    if (Number.isNaN(lat) || Number.isNaN(lng)) {
      setCoordError('Enter valid numbers for latitude and longitude.');
      return null;
    }
    if (lat < LAT_MIN || lat > LAT_MAX) {
      setCoordError(`Latitude must be between ${LAT_MIN} and ${LAT_MAX}.`);
      return null;
    }
    if (lng < LON_MIN || lng > LON_MAX) {
      setCoordError(`Longitude must be between ${LON_MIN} and ${LON_MAX}.`);
      return null;
    }
    return { lat, lng };
  };

  const applyLocation = () => {
    const coords = parseAndValidateCoordinates();
    if (!coords) return;
    onLocationSelect(coords.lat, coords.lng);
  };

  const openInSolarGIS = () => {
    const coords = location
      ? { lat: location.lat, lng: location.lng }
      : parseAndValidateCoordinates();
    if (!coords) {
      if (!location) setCoordError('Confirm location first, or enter valid coordinates.');
      return;
    }
    const params = new URLSearchParams({
      c: `${coords.lat},${coords.lng},10`,
      s: `${coords.lat},${coords.lng}`,
    });
    window.open(`https://apps.solargis.com/prospect/map?${params.toString()}`, '_blank', 'noopener,noreferrer');
  };

  if (currentStep === 1) {
    return (
      <div className="flex flex-col gap-3">
        <h2 className="text-base font-semibold text-foreground">Select Project Location</h2>
        <Tabs defaultValue="coordinates" className="w-full">
          <TabsList className="grid w-full grid-cols-2 h-8 mb-2">
            <TabsTrigger value="coordinates" className="gap-1.5 text-sm">
              <Type className="w-3.5 h-3.5" />
              Enter Coordinates
            </TabsTrigger>
            <TabsTrigger value="map" className="gap-1.5 text-sm">
              <Navigation className="w-3.5 h-3.5" />
              Pin on Map
            </TabsTrigger>
          </TabsList>
          <TabsContent value="coordinates" className="m-0 space-y-2">
            <div className="space-y-2">
              <div className="space-y-1">
                <Label htmlFor="wizard-lat" className="text-xs">
                  Latitude (°)
                </Label>
                <Input
                  id="wizard-lat"
                  type="number"
                  step="any"
                  placeholder="e.g. 20.5937"
                  min={LAT_MIN}
                  max={LAT_MAX}
                  value={inputLat}
                  onChange={(e: ChangeEvent<HTMLInputElement>) => setInputLat(e.target.value)}
                  onKeyDown={(e: KeyboardEvent<HTMLInputElement>) => e.key === 'Enter' && applyLocation()}
                  className="text-sm h-8"
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="wizard-lng" className="text-xs">
                  Longitude (°)
                </Label>
                <Input
                  id="wizard-lng"
                  type="number"
                  step="any"
                  placeholder="e.g. 78.9629"
                  min={LON_MIN}
                  max={LON_MAX}
                  value={inputLng}
                  onChange={(e: ChangeEvent<HTMLInputElement>) => setInputLng(e.target.value)}
                  onKeyDown={(e: KeyboardEvent<HTMLInputElement>) => e.key === 'Enter' && applyLocation()}
                  className="text-sm h-8"
                />
              </div>
            </div>
            {coordError && <p className="text-xs text-destructive">{coordError}</p>}
            <div className="flex flex-wrap gap-2">
              <Button size="sm" onClick={applyLocation} className="bg-blue-600 hover:bg-blue-700 text-white h-8">
                Confirm Location
              </Button>
              <Button size="sm" type="button" variant="outline" onClick={openInSolarGIS} className="gap-1.5 h-8">
                <ExternalLink className="w-3.5 h-3.5" />
                Open in SolarGIS
              </Button>
            </div>
            <p className="text-xs text-muted-foreground leading-tight">
              Or click on the map to the left to set the location. After confirming, use &quot;Open in SolarGIS&quot; to download climate data, then upload the CSV in Step 2.
            </p>
          </TabsContent>
          <TabsContent value="map" className="m-0">
            <p className="text-xs text-muted-foreground">
              Click on the map to the left to set the plant location, then click &quot;Confirm Location&quot; above or continue to the next step.
            </p>
          </TabsContent>
        </Tabs>
      </div>
    );
  }

  if (currentStep === 2) {
    return (
      <div className="flex flex-col gap-2 overflow-auto">
        <h2 className="text-sm font-semibold text-foreground">Upload SolarGIS Prospect (PVsyst Monthly)</h2>
        <p className="text-xs text-muted-foreground leading-tight">
          Upload the SolarGIS Prospect CSV (Monthly PVsyst format) from SolarGIS Prospect. Max 5 MB.
        </p>
        <FileUpload
          title="SolarGIS Prospect CSV"
          description="PVsyst monthly format"
          acceptedType=".csv"
          file={csvFile}
          onFileSelect={onCsvFileSelect}
          icon={<FileSpreadsheet className="w-4 h-4 text-primary" />}
          maxSizeMb={5}
          compact
        />
        {isParsingSolargis && (
          <p className="text-xs text-muted-foreground">Validating and parsing SolarGIS CSV...</p>
        )}
        {solargisError && <p className="text-xs text-destructive">{solargisError}</p>}
        {solargisPreview && !solargisError && <SolarGISMonthlyTable data={solargisPreview} />}
      </div>
    );
  }

  if (currentStep === 3) {
    return (
      <div className="flex flex-col gap-2 overflow-auto">
        <h2 className="text-sm font-semibold text-foreground">Upload Site Boundary (KML)</h2>
        <p className="text-xs text-muted-foreground leading-tight">Upload your plant boundary or layout file in KML format.</p>
        <FileUpload
          title="Site Boundary KML"
          description="Plant boundary KML file"
          acceptedType=".kml"
          file={kmlFile}
          onFileSelect={onKmlFileSelect}
          icon={<Map className="w-4 h-4 text-primary" />}
          compact
        />
      </div>
    );
  }

  if (currentStep === 4) {
    return (
      <div className="flex flex-col gap-2 overflow-auto">
        <h2 className="text-sm font-semibold text-foreground">Review</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <KpiSummaryCard
            theme="blue"
            title="Location Summary"
            icon={<MapPin className="w-4 h-4" />}
          >
            {location ? (
              <p className="text-xs text-muted-foreground leading-tight">
                Lat {location.lat.toFixed(6)}°, Lng {location.lng.toFixed(6)}°
              </p>
            ) : (
              <p className="text-xs text-muted-foreground">Not set</p>
            )}
          </KpiSummaryCard>
          <KpiSummaryCard
            theme="amber"
            title="Climate Summary"
            icon={<ThermometerSun className="w-4 h-4" />}
          >
            {solargisPreview?.records?.length ? (
              <p className="text-xs text-muted-foreground leading-tight">
                {solargisPreview.records.length} monthly records loaded
                {solargisPreview.location ? ` · ${solargisPreview.location}` : ''}
              </p>
            ) : (
              <p className="text-xs text-muted-foreground">No climate data uploaded</p>
            )}
          </KpiSummaryCard>
          <KpiSummaryCard
            theme="emerald"
            title="Boundary Summary"
            icon={<MapPinned className="w-4 h-4" />}
          >
            {kmlFile ? (
              <p className="text-xs text-muted-foreground truncate">{kmlFile.name}</p>
            ) : (
              <p className="text-xs text-muted-foreground">No KML uploaded</p>
            )}
          </KpiSummaryCard>
        </div>
      </div>
    );
  }

  return null;
}

export function getStepComplete(
  location: { lat: number; lng: number } | null,
  solargisPreview: StepPanelProps['solargisPreview'],
  kmlFile: File | null
): StepCompleteState {
  return {
    location: !!location,
    climate: !!(solargisPreview?.records?.length),
    boundary: !!kmlFile,
  };
}
