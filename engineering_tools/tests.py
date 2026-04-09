"""
Tests for Engineering Tools — Manual DC yield engine.
"""
from django.test import TestCase

from engineering_tools.solar_services.yield_engine import (
    MonthlySolarData,
    ManualDCInput,
    calculate_poa,
    calculate_temp_loss,
    calculate_net_pr,
    calculate_yield,
)


class YieldEngineTest(TestCase):
    """Unit tests for Manual DC yield engine."""

    def test_calculate_poa_basic(self):
        """POA is non-negative and scales with GHI."""
        poa = calculate_poa(100, 0.4, 35, 25, 0, 0.2)
        self.assertGreaterEqual(poa, 0)
        self.assertLess(poa, 100 * 2)

    def test_calculate_temp_loss_low_lat(self):
        """Lat <= 20: TempLoss = (TC/100) * (Temp + 46 - 25)."""
        loss = calculate_temp_loss(15, 30, 150, -0.4)
        self.assertAlmostEqual(loss, (-0.4 / 100) * (30 + 46 - 25), places=5)

    def test_calculate_temp_loss_mid_lat(self):
        """Lat > 20: TempLoss = (TC/100) * ((Temp + GHI*0.032) - 25)."""
        loss = calculate_temp_loss(35, 25, 200, -0.4)
        expected = (-0.4 / 100) * (25 + 200 * 0.032 - 25)
        self.assertAlmostEqual(loss, expected, places=5)

    def test_calculate_net_pr(self):
        """Net PR from Excel: (B18/100)*(1-B54)*(1-B32)*(1-B33)*(1-F86)."""
        net = calculate_net_pr(85, 1, 2, 3, 0, 0)  # pr, mismatch, wiring, soiling, snow, degradation
        expected = (85 / 100) * 0.99 * 0.98 * 0.97
        self.assertAlmostEqual(net, expected, places=5)

    def test_calculate_yield_returns_12_months(self):
        """Yield output has 12 monthly values."""
        monthly = [
            MonthlySolarData(month=f"Month{i}", ghi=100, diffuse=0.4, temperature=25)
            for i in range(12)
        ]
        inp = ManualDCInput(
            latitude=35,
            longitude=139,
            tilt=25,
            azimuth=0,
            albedo=0.2,
            dc_capacity_kwp=1000,
            performance_ratio=85,
            inverter_efficiency=98.5,
            temp_coefficient=-0.4,
            mismatch_loss=0,
            wiring_loss=0,
            soiling_loss=0,
            snow_loss=0,
            degradation=0,
            additional_loss=0,
            monthly_data=monthly,
        )
        out = calculate_yield(inp)
        self.assertEqual(len(out.monthly_energy_mwh), 12)
        self.assertGreater(out.annual_energy_mwh, 0)
        self.assertGreater(out.specific_yield_kwh_per_kwp, 0)
        self.assertGreater(out.capacity_factor_percent, 0)
        self.assertLess(out.capacity_factor_percent, 100)

    def test_calculate_yield_zero_dc(self):
        """Zero DC capacity gives zero specific yield and capacity factor."""
        monthly = [
            MonthlySolarData(month=f"Month{i}", ghi=100, diffuse=0.4, temperature=25)
            for i in range(12)
        ]
        inp = ManualDCInput(
            latitude=35,
            longitude=139,
            tilt=25,
            azimuth=0,
            albedo=0.2,
            dc_capacity_kwp=0,
            performance_ratio=85,
            inverter_efficiency=98.5,
            temp_coefficient=-0.4,
            mismatch_loss=0,
            wiring_loss=0,
            soiling_loss=0,
            snow_loss=0,
            degradation=0,
            additional_loss=0,
            monthly_data=monthly,
        )
        out = calculate_yield(inp)
        self.assertEqual(out.specific_yield_kwh_per_kwp, 0)
        self.assertEqual(out.capacity_factor_percent, 0)
        self.assertEqual(out.annual_energy_mwh, 0)

    def test_calculate_yield_summary_output(self):
        """With module/inverter params, summary has total_modules, pv_area_m2, ac_capacity_kw, dc_ac_ratio."""
        monthly = [
            MonthlySolarData(month=f"Month{i}", ghi=100, diffuse=0.4, temperature=25)
            for i in range(12)
        ]
        inp = ManualDCInput(
            latitude=35,
            longitude=139,
            tilt=25,
            azimuth=0,
            albedo=0.2,
            dc_capacity_kwp=2000,
            performance_ratio=85,
            inverter_efficiency=98.5,
            temp_coefficient=-0.4,
            mismatch_loss=0,
            wiring_loss=0,
            soiling_loss=0,
            snow_loss=0,
            degradation=0,
            additional_loss=0,
            monthly_data=monthly,
            module_wp=500,
            module_length_m=2.0,
            module_width_m=1.0,
            modules_in_series=24,
            inverter_capacity_kw=125,
        )
        out = calculate_yield(inp)
        self.assertGreater(out.total_modules, 0)
        self.assertEqual(out.total_modules, 2000 * 1000 / 500)  # 4000 modules
        self.assertGreater(out.total_strings, 0)
        self.assertGreater(out.pv_area_m2, 0)
        self.assertGreater(out.land_area_m2, 0)
        self.assertGreater(out.ac_capacity_kw, 0)
        self.assertGreater(out.num_inverters, 0)
        self.assertGreater(out.dc_ac_ratio, 0)
        self.assertGreater(out.performance_ratio_pct, 0)
