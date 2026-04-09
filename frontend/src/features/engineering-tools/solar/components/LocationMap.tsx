import { useEffect, useRef, useState, type ChangeEvent, type KeyboardEvent } from 'react';
import { MapPin, Navigation, Type, ExternalLink } from 'lucide-react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import 'leaflet/dist/leaflet.css';

const LAT_MIN = -90;
const LAT_MAX = 90;
const LON_MIN = -180;
const LON_MAX = 180;
const DEFAULT_CENTER: [number, number] = [20.5937, 78.9629];

interface LocationMapProps {
  location: { lat: number; lng: number } | null;
  onLocationSelect: (lat: number, lng: number) => void;
}

export interface MapPanelProps {
  location: { lat: number; lng: number } | null;
  onLocationSelect: (lat: number, lng: number) => void;
  className?: string;
}

export function MapPanel({ location, onLocationSelect, className }: MapPanelProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<unknown>(null);
  const markerRef = useRef<unknown>(null);
  const [isMapReady, setIsMapReady] = useState(false);

  useEffect(() => {
    let mounted = true;
    const initMap = async () => {
      if (!mapContainerRef.current) return;
      const L = await import('leaflet');
      if (!mounted || !mapContainerRef.current) return;
      const defaultIcon = L.icon({
        iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
        iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
        shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
        iconSize: [25, 41],
        iconAnchor: [12, 41],
        popupAnchor: [1, -34],
        shadowSize: [41, 41],
      });
      const center = location ? ([location.lat, location.lng] as [number, number]) : DEFAULT_CENTER;
      const map = L.map(mapContainerRef.current).setView(center, location ? 10 : 5);
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      }).addTo(map);
      map.on('click', (e: { latlng: { lat: number; lng: number } }) => {
        const { lat, lng } = e.latlng;
        onLocationSelect(lat, lng);
        if (markerRef.current) {
          (markerRef.current as { setLatLng: (x: [number, number]) => void }).setLatLng([lat, lng]);
        } else {
          markerRef.current = L.marker([lat, lng], { icon: defaultIcon }).addTo(map);
        }
      });
      if (location) {
        markerRef.current = L.marker([location.lat, location.lng], { icon: defaultIcon }).addTo(map);
      }
      mapRef.current = map;
      setIsMapReady(true);
    };
    initMap();
    return () => {
      mounted = false;
      if (mapRef.current && typeof (mapRef.current as { remove: () => void }).remove === 'function') {
        (mapRef.current as { remove: () => void }).remove();
        mapRef.current = null;
        markerRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (!mapRef.current || !location) return;
    (mapRef.current as { flyTo: (c: [number, number], z: number, o: { duration: number }) => void }).flyTo(
      [location.lat, location.lng],
      10,
      { duration: 1 }
    );
    if (markerRef.current) {
      (markerRef.current as { setLatLng: (x: [number, number]) => void }).setLatLng([
        location.lat,
        location.lng,
      ]);
    }
  }, [location?.lat, location?.lng]);

  return (
    <div className={`relative ${className ?? 'h-[380px]'}`}>
      <div ref={mapContainerRef} className="h-full w-full rounded-lg" />
      {!isMapReady && (
        <div className="absolute inset-0 flex items-center justify-center bg-muted/50 rounded-lg">
          <span className="text-muted-foreground">Loading map...</span>
        </div>
      )}
    </div>
  );
}

const LocationMap = ({ location, onLocationSelect }: LocationMapProps) => {
  const [activeTab, setActiveTab] = useState('coordinates');
  const [inputLat, setInputLat] = useState('');
  const [inputLng, setInputLng] = useState('');
  const [coordError, setCoordError] = useState<string | null>(null);

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

  const applyCoordinates = () => {
    const coords = parseAndValidateCoordinates();
    if (!coords) return;
    onLocationSelect(coords.lat, coords.lng);
  };

  const openInSolarGIS = () => {
    const coords = location ? { lat: location.lat, lng: location.lng } : parseAndValidateCoordinates();
    if (!coords) {
      if (!location) setCoordError('Apply location first, or enter valid coordinates.');
      return;
    }
    const zoom = 10;
    const params = new URLSearchParams({
      c: `${coords.lat},${coords.lng},${zoom}`,
      s: `${coords.lat},${coords.lng}`,
    });
    window.open(`https://apps.solargis.com/prospect/map?${params.toString()}`, '_blank', 'noopener,noreferrer');
  };

  useEffect(() => {
    if (location) {
      setInputLat(location.lat.toString());
      setInputLng(location.lng.toString());
      setCoordError(null);
    }
  }, [location?.lat, location?.lng]);

  const contentPadding = 'px-4';
  return (
    <div className="input-section-card overflow-hidden">
      <div className={`${contentPadding} py-3 border-b border-border bg-gradient-to-r from-primary/5 to-accent/5`}>
        <div className="flex items-center gap-3 min-w-0">
          <div className="p-1.5 rounded-lg bg-primary/10 shrink-0">
            <MapPin className="w-4 h-4 text-primary" />
          </div>
          <div className="min-w-0">
            <h2 className="text-base font-semibold text-foreground leading-tight">Select Plant Location</h2>
            <p className="text-xs text-muted-foreground mt-0.5">
              Enter coordinates manually or pinpoint on the map
            </p>
          </div>
        </div>
      </div>
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <div className={`${contentPadding} pt-3 pb-1`}>
          <TabsList className="grid w-full grid-cols-2 h-9 max-w-sm">
            <TabsTrigger value="coordinates" className="text-sm"> <Type className="w-3.5 h-3.5 mr-1.5" /> Enter coordinates </TabsTrigger>
            <TabsTrigger value="map" className="text-sm"> <Navigation className="w-3.5 h-3.5 mr-1.5" /> Pin on map </TabsTrigger>
          </TabsList>
        </div>
        <TabsContent value="coordinates" className={`${contentPadding} py-3 space-y-3 m-0`}>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="lat" className="text-xs">Latitude (°)</Label>
              <Input
                id="lat"
                type="number"
                step="any"
                placeholder="e.g. 20.5937"
                min={LAT_MIN}
                max={LAT_MAX}
                value={inputLat}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setInputLat(e.target.value)}
                onKeyDown={(e: KeyboardEvent<HTMLInputElement>) => e.key === 'Enter' && applyCoordinates()}
                className="h-9"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="lng" className="text-xs">Longitude (°)</Label>
              <Input
                id="lng"
                type="number"
                step="any"
                placeholder="e.g. 78.9629"
                min={LON_MIN}
                max={LON_MAX}
                value={inputLng}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setInputLng(e.target.value)}
                onKeyDown={(e: KeyboardEvent<HTMLInputElement>) => e.key === 'Enter' && applyCoordinates()}
                className="h-9"
              />
            </div>
            <div className="flex items-end gap-2 sm:col-span-2 lg:col-span-2">
              <Button onClick={applyCoordinates} type="button" size="sm" className="h-9">Apply location</Button>
              <Button onClick={openInSolarGIS} type="button" variant="outline" size="sm" className="h-9 gap-1.5">
                <ExternalLink className="w-3.5 h-3.5" /> Open in SolarGIS
              </Button>
            </div>
          </div>
          {coordError && <p className="text-sm text-destructive -mt-1">{coordError}</p>}
          <p className="text-xs text-muted-foreground bg-muted/30 rounded-md py-2 pl-0 pr-4">
            Click &quot;Apply location&quot; first so &quot;Open in SolarGIS&quot; uses your coordinates. Download the CSV from Prospect, then upload it in Step 2.
          </p>
        </TabsContent>
        <TabsContent value="map" className={`m-0 ${contentPadding} pb-3`}>
          <p className="text-xs text-muted-foreground mb-2">Click on the map to set the plant location</p>
          {activeTab === 'map' && (
            <MapPanel location={location} onLocationSelect={onLocationSelect} />
          )}
        </TabsContent>
      </Tabs>
      {location && (
        <div className={`${contentPadding} py-2.5 bg-gradient-to-r from-success/5 to-primary/5 border-t border-border`}>
          <div className="flex items-center gap-4 flex-wrap text-sm">
            <span className="font-mono font-medium text-foreground">{location.lat.toFixed(6)}°</span>
            <span className="text-muted-foreground">×</span>
            <span className="font-mono font-medium text-foreground">{location.lng.toFixed(6)}°</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default LocationMap;
