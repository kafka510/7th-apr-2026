/**
 * Solar Pre-Feasibility calculator — Manual DC Mode (no KMZ).
 * Formulas from JP_Project Name_Pre-Feasibility Yield Tool_V0 1.xlsm:
 * - POA H74: GHI*((1-Albedo)*beam_geom + Albedo*(1+cos(Tilt))/2 + E74*(1-cos(Tilt))/2)
 * - Energy I74: ((H74*B50*(B18/100))*(B26/100)*(1-B54)*(1-B32)*(1-B33)*(1-F86))*(1+B55)*(1+B56)/1000
 * - B56: single temp loss from annual avg temp and annual total GHI
 *
 * WEATHER DATA SOURCE (no SolarGIS upload):
 * In Solar Insight (with KMZ), the Excel tool uses real weather from the SolarGIS sheet (C74:C85=GHI,
 * D74:D85=temp, E74:E85=diffuse from SolarGIS Prospect CSV). In Pre-Feasibility v1 there is no upload:
 * we use synthetic "typical" monthly values derived only from latitude — same yield formulas, different
 * inputs. So results are indicative only, not site-specific. See typicalMonthlyGhiKwhM2, typicalDiffuseFraction,
 * typicalMonthlyTempC and buildTypicalMonthlyData.
 */
const RAD = Math.PI / 180;
const DAYS_IN_MONTH = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
const MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

/**
 * Typical monthly GHI (kWh/m²) — total per month, synthetic pattern from latitude only.
 * Used when no SolarGIS weather is uploaded (Pre-Feasibility v1). Not site-specific.
 */
export function typicalMonthlyGhiKwhM2(latitude: number): number[] {
  const absLat = Math.min(Math.abs(latitude), 55);
  const annualDailyAvg = Math.max(2.8, 5.2 - 0.06 * absLat);
  const monthlyFactor = [
    0.75, 0.82, 1.02, 1.15, 1.22, 1.18, 1.2, 1.18, 1.08, 0.95, 0.82, 0.72,
  ];
  const sumFactor = monthlyFactor.reduce((a, b) => a + b, 0);
  const scale = 12 / sumFactor;
  const northern = monthlyFactor.map((f) => f * scale);
  const monthlyDaily = latitude >= 0 ? northern : [...northern.slice(6), ...northern.slice(0, 6)];
  return monthlyDaily.map((fac, i) => fac * annualDailyAvg * (DAYS_IN_MONTH[i] ?? 30));
}

/** Typical diffuse fraction per month (0–1). */
function typicalDiffuseFraction(): number[] {
  return Array(12).fill(0.4);
}

/** Typical monthly ambient temperature (°C) by latitude (simplified). */
function typicalMonthlyTempC(latitude: number): number[] {
  const absLat = Math.min(Math.abs(latitude), 55);
  const annualAvg = 25 - 0.4 * absLat;
  const monthlyFactor = [
    0.85, 0.9, 1.0, 1.08, 1.12, 1.1, 1.1, 1.08, 1.02, 0.98, 0.92, 0.88,
  ];
  return monthlyFactor.map((f) => annualAvg * f);
}

/** POA (kWh/m²) — from Excel H74. Diffuse as fraction 0–1; diffuse term uses (1-cos(Tilt))/2. */
function calculatePoa(
  ghi: number,
  diffuseFraction: number,
  lat: number,
  tilt: number,
  azimuth: number,
  albedo: number
): number {
  const latR = lat * RAD;
  const tiltR = tilt * RAD;
  const azR = azimuth * RAD;
  const cosLat = Math.cos(latR);
  const cosTilt = Math.cos(tiltR);
  const beamGeom = cosLat !== 0 ? (Math.cos(latR - tiltR) * Math.cos(azR)) / cosLat : 0;
  const beam = (1 - albedo) * beamGeom;
  const ground = albedo * (1 + cosTilt) / 2;
  const diffuse = diffuseFraction * (1 - cosTilt) / 2;
  return Math.max(0, ghi * (beam + ground + diffuse));
}

/** Excel B56: single temp loss from annual avg temp and annual total GHI (applied to all months). */
function calculateTempLossExcel(
  lat: number,
  annualAvgTemp: number,
  annualTotalGhi: number,
  tempCoeff: number
): number {
  if (lat <= 20) {
    return (tempCoeff / 100) * (annualAvgTemp + 46 - 25);
  }
  return (tempCoeff / 100) * (annualAvgTemp + annualTotalGhi * 0.032 - 25);
}

/** Net PR from Excel I74: (B18/100)*(1-B54)*(1-B32)*(1-B33)*(1-F86). B55 applied separately. */
function calculateNetPr(
  pr: number,
  degradation: number,
  mismatch: number,
  wiring: number,
  soiling: number,
  snow: number
): number {
  return (
    (pr / 100) *
    (1 - degradation / 100) *
    (1 - mismatch / 100) *
    (1 - wiring / 100) *
    (1 - soiling / 100) *
    (1 - snow / 100)
  );
}

export interface PreFeasibilityInputs {
  latitude: number;
  longitude: number;
  dcCapacityKw: number;
  tiltDeg?: number;
  azimuthDeg?: number;
  albedo?: number;
  /** Aggregate system loss % (used only when full loss stack not provided). */
  totalLossPercent?: number;
  inverterEfficiencyPercent?: number;
  dcAcRatio?: number;
  /** Full Manual DC stack (overrides totalLossPercent when set). */
  performanceRatio?: number;
  tempCoefficient?: number;
  mismatchLoss?: number;
  wiringLoss?: number;
  soilingLoss?: number;
  snowLoss?: number;
  degradation?: number;
  additionalLoss?: number;
}

/** Summary Output Data (Excel B48–B65). */
export interface SummaryOutputData {
  total_modules: number;
  total_strings: number;
  pv_area_m2: number;
  land_area_m2: number;
  land_area_ha: number;
  gcr_pct: number;
  shadow_loss_pct: number;
  bifacial_gain_pct: number;
  temperature_loss_pct: number;
  dc_capacity_kwp: number;
  ac_capacity_kw: number;
  num_inverters: number;
  dc_ac_ratio: number;
  annual_energy_mwh: number;
  specific_yield_kwh_per_kwp: number;
  performance_ratio_pct: number;
}

export interface PreFeasibilityResult {
  dcCapacityKw: number;
  acCapacityKw: number;
  annualEnergyMwh: number;
  specificYieldKwhPerKwp: number;
  capacityFactorPercent: number;
  monthlyTiltedKwhM2: number[];
  monthlyEnergyMwh: number[];
  annualGhiKwhM2: number;
  summary?: SummaryOutputData;
  /** Optional grid connectivity details (from backend when available). */
  gridVoltageKv?: number | null;
  gridSubstationName?: string | null;
}

const DEFAULT_TILT = 25;
const DEFAULT_AZIMUTH = 0;
const DEFAULT_ALBEDO = 0.2;
const DEFAULT_TOTAL_LOSS = 18;
const DEFAULT_INV_EFF = 98.5;
const DEFAULT_DC_AC_RATIO = 1.25;
const DEFAULT_PR = 85;
const DEFAULT_TEMP_COEFF = -0.4;

export function computePreFeasibility(inputs: PreFeasibilityInputs): PreFeasibilityResult | null {
  const {
    latitude,
    dcCapacityKw,
    tiltDeg = DEFAULT_TILT,
    azimuthDeg = DEFAULT_AZIMUTH,
    albedo = DEFAULT_ALBEDO,
    totalLossPercent = DEFAULT_TOTAL_LOSS,
    inverterEfficiencyPercent = DEFAULT_INV_EFF,
    dcAcRatio = DEFAULT_DC_AC_RATIO,
    performanceRatio = DEFAULT_PR,
    tempCoefficient = DEFAULT_TEMP_COEFF,
    mismatchLoss = 0,
    wiringLoss = 0,
    soilingLoss = 0,
    snowLoss = 0,
    degradation = 0,
    additionalLoss = 0,
  } = inputs;

  if (dcCapacityKw <= 0) return null;

  const monthlyGhi = typicalMonthlyGhiKwhM2(latitude);
  const diffuseFrac = typicalDiffuseFraction();
  const monthlyTemp = typicalMonthlyTempC(latitude);

  const useFullStack =
    performanceRatio != null ||
    mismatchLoss != null ||
    wiringLoss != null ||
    soilingLoss != null ||
    snowLoss != null ||
    degradation != null ||
    additionalLoss != null;

  const netPr = useFullStack
    ? calculateNetPr(
        performanceRatio ?? DEFAULT_PR,
        degradation ?? 0,
        mismatchLoss ?? 0,
        wiringLoss ?? 0,
        soilingLoss ?? 0,
        snowLoss ?? 0
      )
    : 1 - totalLossPercent / 100;

  const invEff = inverterEfficiencyPercent / 100;
  const annualAvgTemp = monthlyTemp.reduce((a, b) => a + b, 0) / 12;
  const annualTotalGhi = monthlyGhi.reduce((a, b) => a + b, 0);
  const tempLossB56 = useFullStack
    ? calculateTempLossExcel(
        latitude,
        annualAvgTemp,
        annualTotalGhi,
        tempCoefficient ?? DEFAULT_TEMP_COEFF
      )
    : 0;
  const otherAdjB55 = (additionalLoss ?? 0) / 100;

  const monthlyTiltedKwhM2: number[] = [];
  const monthlyEnergyMwh: number[] = [];

  for (let i = 0; i < 12; i++) {
    const ghi = monthlyGhi[i] ?? 0;
    const poa = calculatePoa(
      ghi,
      diffuseFrac[i] ?? 0.4,
      latitude,
      tiltDeg,
      azimuthDeg,
      albedo
    );
    monthlyTiltedKwhM2.push(poa);

    if (useFullStack) {
      const energy =
        (poa * dcCapacityKw * netPr * invEff * (1 + otherAdjB55) * (1 + tempLossB56)) / 1000;
      monthlyEnergyMwh.push(Math.max(0, energy));
    } else {
      monthlyEnergyMwh.push(0);
    }
  }

  const annualPoaKwhM2 = monthlyTiltedKwhM2.reduce((a, b) => a + b, 0);
  const annualGhiKwhM2 = monthlyGhi.reduce((a, b) => a + b, 0);

  let annualEnergyMwh: number;
  if (useFullStack) {
    annualEnergyMwh = monthlyEnergyMwh.reduce((a, b) => a + b, 0);
  } else {
    annualEnergyMwh = (annualPoaKwhM2 * dcCapacityKw * netPr * invEff) / 1000;
    const poaSum = annualPoaKwhM2 || 1;
    for (let i = 0; i < 12; i++) {
      monthlyEnergyMwh[i] = (annualEnergyMwh * (monthlyTiltedKwhM2[i] ?? 0)) / poaSum;
    }
  }

  const acCapacityKw = dcCapacityKw / dcAcRatio;
  const specificYieldKwhPerKwp = (annualEnergyMwh * 1000) / dcCapacityKw;
  const capacityFactorPercent =
    acCapacityKw > 0 ? ((annualEnergyMwh * 1000) / (acCapacityKw * 8760)) * 100 : 0;

  return {
    dcCapacityKw,
    acCapacityKw: Math.round(acCapacityKw * 10) / 10,
    annualEnergyMwh: Math.round(annualEnergyMwh * 100) / 100,
    specificYieldKwhPerKwp: Math.round(specificYieldKwhPerKwp * 10) / 10,
    capacityFactorPercent: Math.round(capacityFactorPercent * 100) / 100,
    monthlyTiltedKwhM2,
    monthlyEnergyMwh,
    annualGhiKwhM2: Math.round(annualGhiKwhM2 * 10) / 10,
  };
}

/** Build 12-month typical data for Manual DC API (same logic as calculator). */
export function buildTypicalMonthlyData(latitude: number): Array<{ month: string; ghi: number; diffuse: number; temperature: number }> {
  const ghi = typicalMonthlyGhiKwhM2(latitude);
  const diffuseFrac = typicalDiffuseFraction();
  const temp = typicalMonthlyTempC(latitude);
  return MONTH_NAMES.map((month, i) => ({
    month,
    ghi: ghi[i] ?? 0,
    diffuse: diffuseFrac[i] ?? 0.4,
    temperature: temp[i] ?? 25,
  }));
}
