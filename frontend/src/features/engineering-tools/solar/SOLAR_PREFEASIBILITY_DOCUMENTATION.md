# Solar Pre-Feasibility — How It Works

This document describes the **Solar Pre-Feasibility** feature: user inputs, calculation flow, formulas (aligned with the Excel tool *JP_Project Name_Pre-Feasibility Yield Tool_V0 1.xlsm*), and one worked example.

---

## 1. Overview

- **Purpose:** Manual DC yield simulation for one or more sites **without** KMZ/layout. Each site is defined by location, DC capacity, tilt, and optional module/inverter and loss assumptions.
- **Modes:**
  - **Backend:** When the API `POST /api/manual-dc-yield/` is available, the app sends site + system + 12-month weather and receives annual energy, specific yield, capacity factor, and summary (modules, PV area, land area, etc.).
  - **Client fallback:** If the API fails or is unavailable, the same formulas are run in the browser using **typical** (latitude-based) monthly GHI, diffuse, and temperature — results are indicative, not site-specific.
- **Weather data:**
  - **With SolarGIS CSV:** User can upload a SolarGIS Prospect monthly CSV per row; if valid (≥12 monthly records), that weather is sent to the backend (or used in the same formulas) for that site.
  - **Without SolarGIS:** App uses **typical** monthly values derived from latitude only (see §4).

---

## 2. User Inputs (per site row)

| Input | Description | Validation / Default |
|-------|-------------|----------------------|
| **Site name** | Optional label | Any text |
| **Lat** | Latitude (°) | −90 to 90, required |
| **Long** | Longitude (°) | −180 to 180, required |
| **DC (kWp)** | DC capacity | Positive number, required |
| **Tilt (°)** | Panel tilt | 0–90; default 25 |
| **Module** | From module master (Wp, dimensions) | Optional; used for total modules, PV area, land area when backend is used |
| **Inverter** | From inverter master (AC kW, efficiency) | Optional; used for AC capacity, number of inverters, DC/AC ratio |
| **Array config** | Landscape / Portrait | Display/config only in current flow |
| **Modules in series** | String length | Optional; default 24 when module selected; used for total strings |
| **Soiling loss (%)** | Soiling loss | 0–100; default 0 |
| **Solargis** | Optional: open Solargis map, or upload SolarGIS monthly CSV | CSV overrides typical weather when valid |

**Fixed/default values** (not exposed per row in UI):

- Azimuth = 0°, Albedo = 0.2  
- Performance ratio (PR) = 85%  
- Inverter efficiency = 98.5% (or from selected inverter)  
- Temp coefficient = −0.4 %/°C (or from selected module)  
- Mismatch, wiring, snow, degradation, additional loss = 0%  
- GCR (ground coverage ratio) = 58.78% (backend summary)

---

## 3. Calculation Flow

1. **Validate rows:** For each row, `parseRow()` checks Lat, Long, DC capacity; clamps Tilt and Soiling.
2. **Per site:**
   - Build **monthly_data** (12 months):
     - If the row has **SolarGIS CSV** loaded → use GHI, diffuse fraction, temperature from CSV.
     - Else → use **typical** monthly data from `buildTypicalMonthlyData(latitude)`.
   - **Try backend:** `POST /api/manual-dc-yield/` with JSON body (latitude, longitude, tilt, azimuth, albedo, dc_capacity_kwp, performance_ratio, inverter_efficiency, temp_coefficient, soiling_loss, monthly_data, optional module_wp, module_length_m, module_width_m, modules_in_series, inverter_capacity_kw, grid_country). If response is OK, use API result (annual energy, specific yield, capacity factor, summary, and optionally grid voltage/substation).
   - **Else client fallback:** Call `computePreFeasibility()` in the frontend with the same inputs; result has no summary (total modules, land area, etc.) unless backend is used.
3. **Aggregate:** Collect one result per site and show in the Results table; user can export to CSV.

---

## 4. Typical Weather (no SolarGIS)

When no SolarGIS CSV is used, monthly GHI, diffuse, and temperature are derived from **latitude only** (synthetic pattern).

- **Monthly GHI (kWh/m²) — total per month**  
  - Annual daily average (kWh/m²/day): `max(2.8, 5.2 − 0.06×|lat|)`, lat capped to 55°.  
  - Monthly factors (northern): `[0.75, 0.82, 1.02, 1.15, 1.22, 1.18, 1.2, 1.18, 1.08, 0.95, 0.82, 0.72]`, scaled so they sum to 12.  
  - For southern hemisphere, months are shifted by 6.  
  - **Monthly GHI** = monthly factor × annual daily average × days in month.

- **Diffuse fraction:** 0.4 for all months.

- **Monthly temperature (°C):**  
  - Annual average: `25 − 0.4×|lat|`.  
  - Monthly factors applied to get per-month values.

---

## 5. Formulas (Excel-aligned)

References: *Summary of Simulation* sheet, cells B18, B21, B26, B50, B54–B56, H74, I74, etc.

### 5.1 POA (Plane of Array) irradiance — H74

**Formula:**

```
POA = GHI × ( (1 − Albedo)×beam_geom + Albedo×(1 + cos(Tilt))/2 + diffuse_fraction×(1 − cos(Tilt))/2 )
```

- **beam_geom** = cos(lat − tilt)×cos(azimuth) / cos(lat) (simplified beam geometry).  
- **diffuse_fraction** = diffuse/GHI (0–1); from monthly data or typical 0.4.  
- Albedo = 0.2, Tilt and azimuth in radians.

### 5.2 Net performance ratio (loss stack) — B18, B54, B32, B33, F86

**Formula:**

```
Net_PR = (PR/100) × (1 − Degradation) × (1 − Mismatch) × (1 − Wiring) × (1 − Soiling) × (1 − Snow)
```

- PR = 85% (B18), other losses in % (0–100).  
- Soiling comes from user input; mismatch, wiring, snow, degradation are 0 in the app.

### 5.3 Temperature loss — B56 (single annual value)

**Formula:**

- If **latitude ≤ 20°:**  
  `temp_loss = (temp_coeff/100) × (annual_avg_temp + 46 − 25)`
- Else:  
  `temp_loss = (temp_coeff/100) × (annual_avg_temp + annual_total_GHI×0.032 − 25)`

- **annual_avg_temp** = average of 12 monthly temperatures.  
- **annual_total_GHI** = sum of 12 monthly GHI (kWh/m²).  
- temp_coeff = −0.4 %/°C (or from selected module).  
- This gives a **factor** (e.g. −0.10); applied as `(1 + temp_loss)` in the energy formula.

### 5.4 Monthly energy — I74

**Formula:**

```
Energy_month (MWh) = ( POA × DC_kWp × Net_PR × Inv_eff × (1 + other_adj) × (1 + temp_loss) ) / 1000
```

- **other_adj** = additional_loss/100 (0 in the app).  
- **Inv_eff** = inverter efficiency/100 (e.g. 0.985).  
- Sum of 12 months = **annual_energy_mwh**.

### 5.5 Annual and derived outputs

- **Annual energy (MWh):** Sum of monthly energy.  
- **Specific yield (kWh/kWp/year):** `annual_energy_mwh × 1000 / DC_kWp`.  
- **AC capacity (kW):** From inverter selection: `num_inverters × inverter_capacity_kw`, or if no inverter: `ceil(DC_kWp / 1.25)` (target from DC/AC 1.25).  
- **DC/AC ratio:** `DC_kWp / AC_kW`.  
- **Capacity factor / CUF (%):** `(annual_energy_mwh × 1000) / (AC_kW × 8760) × 100`.

### 5.6 Summary (when backend + module/inverter are used)

- **Total modules:** `round(DC_kWp × 1000 / module_Wp)`.  
- **Total strings:** `total_modules / modules_in_series` (integer division).  
- **PV area (m²):** `total_modules × module_length_m × module_width_m`.  
- **Land area (m²):** `PV_area_m² / (GCR/100)`; GCR default 58.78%.  
- **Land area (ha):** `land_area_m² / 10_000`.  
- **Number of inverters:** `ceil(AC_target / inverter_capacity_kw)`.

---

## 6. Worked Example (client-side typical weather)

**Inputs (one site):**

| Input | Value |
|-------|--------|
| Lat | 35.0 |
| Long | 139.0 |
| DC (kWp) | 1000 |
| Tilt (°) | 25 |
| Soiling loss | 0% |
| PR | 85% |
| Inverter efficiency | 98.5% |
| Temp coefficient | −0.4 %/°C |

**Typical weather (latitude 35°):**

- Annual daily average GHI ≈ max(2.8, 5.2 − 0.06×35) = 3.1 kWh/m²/day.  
- After monthly factors and days/month, **annual total GHI** ≈ 1130 kWh/m² (order of magnitude).  
- **Annual avg temp** from typical monthly temps ≈ 17–18 °C (latitude 35).

**Steps:**

1. **POA** for each month: GHI × (beam + ground + diffuse). For 25° tilt, azimuth 0, albedo 0.2, diffuse 0.4, beam_geom and (1±cos(tilt))/2 terms give monthly POA values; **annual POA** ≈ 1400–1500 kWh/m² (example range).
2. **Net PR** = 0.85 × (1−0) × (1−0) × (1−0) × (1−0) × (1−0) = **0.85**.
3. **Temp loss (B56):** lat 35 > 20 → temp_loss = (−0.4/100) × (17.5 + 1130×0.032 − 25) ≈ (−0.004)×(17.5 + 36.16 − 25) ≈ **−0.114** (about −11.4%).
4. **Monthly energy (MWh):**  
   `Energy = (POA × 1000 × 0.85 × 0.985 × (1 − 0.114)) / 1000`  
   For one month with POA = 120 kWh/m²:  
   `Energy = (120 × 1000 × 0.85 × 0.985 × 0.886) / 1000 ≈ 89.2 MWh`.  
   Sum over 12 months → **annual_energy_mwh** (e.g. ~1180–1200 MWh depending on exact POA).
5. **Specific yield** = annual_energy_mwh × 1000 / 1000 = **~1180–1200 kWh/kWp/year**.
6. **AC capacity** (no inverter selected): 1000/1.25 = **800 kW**.  
   **CUF** = (annual_MWh × 1000) / (800 × 8760) × 100 ≈ **16.8–17.1%**.

Exact numbers in the app will match the actual typical GHI/temp curves and rounding; the above illustrates the formula chain.

---

## 7. References in code

- **Frontend:**  
  - `SolarPreFeasibilityPage.tsx` — UI, validation, API call, client fallback.  
  - `lib/preFeasibilityCalculator.ts` — `computePreFeasibility()`, `typicalMonthlyGhiKwhM2()`, `buildTypicalMonthlyData()`, POA, Net PR, temp loss (B56), monthly energy.
- **Backend:**  
  - `engineering_tools/api_views.py` — `ManualDCYieldView` (POST `/api/manual-dc-yield/`).  
  - `engineering_tools/solar_services/yield_engine.py` — `calculate_yield()`, POA, temp loss, net PR, summary (total modules, PV area, land area, GCR, AC, inverters, DC/AC, PR %).

Excel reference: *JP_Project Name_Pre-Feasibility Yield Tool_V0 1.xlsm*, Summary of Simulation sheet (B48–B65, H74, I74, B56, etc.).
