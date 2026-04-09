/**
 * Monthly tilted radiation — matches Excel Pre-Feasibility Yield Tool formula.
 */
const RAD = Math.PI / 180;

export function monthlyTiltedRadiation(
  ghi: number[],
  _dif: number[],
  latitude: number,
  tiltDeg: number,
  albedo: number[],
  azimuthDeg: number = 0
): number[] {
  const latRad = latitude * RAD;
  const tiltRad = tiltDeg * RAD;
  const azimuthRad = azimuthDeg * RAD;
  const cosTilt = Math.cos(tiltRad);
  const cosLat = Math.cos(latRad);
  const k = 0.36;
  const beamFactor =
    cosLat !== 0
      ? (Math.cos(latRad - tiltRad) * Math.cos(azimuthRad)) / cosLat
      : 1;
  const result: number[] = [];
  for (let i = 0; i < 12; i++) {
    const H = ghi[i] ?? 0;
    const rho = albedo[i] ?? 0.2;
    const Ht =
      H *
      ((1 - k) * beamFactor +
        (k * (1 + cosTilt)) / 2 +
        (rho * (1 - cosTilt)) / 2);
    result.push(Math.max(0, Ht));
  }
  return result;
}
