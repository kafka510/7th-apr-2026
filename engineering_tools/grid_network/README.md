# Grid network data (TL calculation & KML marking)

This folder holds country-specific grid network KMZ files used by Engineering Tools for:

- **TL (transmission line) calculation**: Finding the nearest transmission line and substation to a solar site.
- **KML marking**: When exporting PV layout as KMZ, the export can include a "Grid Connectivity" folder with the nearest TL segment, connection line (site to TL), and nearest substation.

## Layout

- `japan/` – Place Japan grid network KMZ (e.g. `japan.kmz` or `TL Line Network Japan.kmz`).
- `korea/` – Place Korea grid network KMZ.
- `singapore/` – Place Singapore grid network KMZ (e.g. `sp_group_network.kmz`).

The app resolves files by:

1. `{country}/{region}.kmz` if region is provided
2. `{country}/{country}.kmz`
3. First `.kmz` file in the country folder

## Usage

When the Engineering Tools **Export PV Layout (KML)** flow is used with a **grid country** selected, the backend loads the corresponding KMZ from this folder, computes the nearest transmission line and substation to the site, and adds them to the exported KMZ and to the KPI summary (e.g. `nearest_tl_voltage_kv`, `distance_to_line_m`).

## Sharing data with solar-insight

To reuse the same KMZ files from solar-insight on the same machine, set in `.env`:

```
GRID_NETWORK_DATA_ROOT=C:\path\to\solar-insight\data\grid_network
```

The backend reads this and uses that folder instead of `engineering_tools/grid_network`.
