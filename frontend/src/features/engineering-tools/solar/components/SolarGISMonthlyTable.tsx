interface SolarGISMonthlyRecord {
  month: string;
  ghi: number;
  dni: number;
  dif: number;
  temp: number;
  albedo?: number | null;
  wind_speed_ms?: number | null;
  relative_humidity_percent?: number | null;
  precipitable_water_kg_m2?: number | null;
  precipitation_mm?: number | null;
  snow_days?: number | null;
  cooling_degree_days?: number | null;
  heating_degree_days?: number | null;
}

interface SolarGISMonthlyResponse {
  location?: string | null;
  site_name?: string | null;
  lat: number;
  lng: number;
  data_type: string;
  records: SolarGISMonthlyRecord[];
}

interface SolarGISMonthlyTableProps {
  data: SolarGISMonthlyResponse;
}

const SolarGISMonthlyTable = ({ data }: SolarGISMonthlyTableProps) => {
  const records = Array.isArray(data?.records) ? data.records : [];
  return (
    <div className="input-section-card overflow-visible">
      <div className="p-4 border-b border-border bg-gradient-to-r from-primary/5 via-accent/5 to-primary/5 flex flex-col md:flex-row md:items-center md:justify-between gap-3">
        <div>
          <h3 className="text-base font-semibold text-foreground">SolarGIS monthly climate data</h3>
          <p className="text-xs text-muted-foreground mt-1">
            Source: SolarGIS Prospect CSV (PVsyst monthly LTA). Values vary by location.
          </p>
        </div>
        <div className="text-xs text-muted-foreground/80 text-left md:text-right space-y-0.5">
          <div>
            <span className="font-mono">{Number(data?.lat ?? 0).toFixed(4)}°</span>,{' '}
            <span className="font-mono">{Number(data?.lng ?? 0).toFixed(4)}°</span>
          </div>
          {(data?.location ?? data?.site_name) && (
            <div className="truncate max-w-xs md:max-w-sm font-medium text-foreground/90">
              {data.location ?? data.site_name}
            </div>
          )}
        </div>
      </div>
      <div className="overflow-x-auto min-h-[200px]">
        {records.length === 0 ? (
          <p className="p-4 text-sm text-muted-foreground">No monthly records to display.</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-muted/60">
              <tr>
                <th className="px-4 py-2 text-left font-medium text-xs text-muted-foreground uppercase tracking-wide">Month</th>
                <th className="px-4 py-2 text-right font-medium text-xs text-muted-foreground uppercase tracking-wide">GHI (kWh/m²)</th>
                <th className="px-4 py-2 text-right font-medium text-xs text-muted-foreground uppercase tracking-wide">DNI (kWh/m²)</th>
                <th className="px-4 py-2 text-right font-medium text-xs text-muted-foreground uppercase tracking-wide">DIF (kWh/m²)</th>
                <th className="px-4 py-2 text-right font-medium text-xs text-muted-foreground uppercase tracking-wide">Temp (°C)</th>
                <th className="px-4 py-2 text-right font-medium text-xs text-muted-foreground uppercase tracking-wide">Albedo (-)</th>
                <th className="px-4 py-2 text-right font-medium text-xs text-muted-foreground uppercase tracking-wide">Wind (m/s)</th>
                <th className="px-4 py-2 text-right font-medium text-xs text-muted-foreground uppercase tracking-wide">RH (%)</th>
                <th className="px-4 py-2 text-right font-medium text-xs text-muted-foreground uppercase tracking-wide">PWAT (kg/m²)</th>
                <th className="px-4 py-2 text-right font-medium text-xs text-muted-foreground uppercase tracking-wide">PREC (mm)</th>
                <th className="px-4 py-2 text-right font-medium text-xs text-muted-foreground uppercase tracking-wide">Snow (days)</th>
                <th className="px-4 py-2 text-right font-medium text-xs text-muted-foreground uppercase tracking-wide">CDD</th>
                <th className="px-4 py-2 text-right font-medium text-xs text-muted-foreground uppercase tracking-wide">HDD</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/60">
              {records.map((row) => (
                <tr key={row.month}>
                  <td className="px-4 py-2 whitespace-nowrap text-foreground">{row.month}</td>
                  <td className="px-4 py-2 text-right font-mono text-xs text-foreground">{Number(row.ghi ?? 0).toFixed(1)}</td>
                  <td className="px-4 py-2 text-right font-mono text-xs text-foreground">{Number(row.dni ?? 0).toFixed(1)}</td>
                  <td className="px-4 py-2 text-right font-mono text-xs text-foreground">{Number(row.dif ?? 0).toFixed(1)}</td>
                  <td className="px-4 py-2 text-right font-mono text-xs text-foreground">{Number(row.temp ?? 0).toFixed(1)}</td>
                  <td className="px-4 py-2 text-right font-mono text-xs text-foreground">
                    {row.albedo !== undefined && row.albedo !== null ? row.albedo.toFixed(2) : '-'}
                  </td>
                  <td className="px-4 py-2 text-right font-mono text-xs text-foreground">
                    {row.wind_speed_ms !== undefined && row.wind_speed_ms !== null ? row.wind_speed_ms.toFixed(1) : '-'}
                  </td>
                  <td className="px-4 py-2 text-right font-mono text-xs text-foreground">
                    {row.relative_humidity_percent != null ? row.relative_humidity_percent.toFixed(0) : '-'}
                  </td>
                  <td className="px-4 py-2 text-right font-mono text-xs text-foreground">
                    {row.precipitable_water_kg_m2 != null ? row.precipitable_water_kg_m2.toFixed(0) : '-'}
                  </td>
                  <td className="px-4 py-2 text-right font-mono text-xs text-foreground">
                    {row.precipitation_mm != null ? row.precipitation_mm.toFixed(1) : '-'}
                  </td>
                  <td className="px-4 py-2 text-right font-mono text-xs text-foreground">
                    {row.snow_days != null ? row.snow_days.toFixed(0) : '-'}
                  </td>
                  <td className="px-4 py-2 text-right font-mono text-xs text-foreground">
                    {row.cooling_degree_days != null ? row.cooling_degree_days.toFixed(0) : '-'}
                  </td>
                  <td className="px-4 py-2 text-right font-mono text-xs text-foreground">
                    {row.heating_degree_days != null ? row.heating_degree_days.toFixed(0) : '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};

export default SolarGISMonthlyTable;
