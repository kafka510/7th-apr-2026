"""
Unit tests for per-asset solar window (data_collection.services.solar_window).
"""
from datetime import date, datetime

from django.test import TestCase
from django.utils import timezone

from data_collection.services.solar_window import (
    SUNRISE_BUFFER_HOURS,
    SUNSET_BUFFER_HOURS,
    _day_of_year,
    _parse_timezone_offset_minutes,
    _solar_declination_rad,
    get_sunrise_sunset_hours_local,
    is_time_in_solar_window,
    utc_to_local_hour,
)


class TestParseTimezoneOffset(TestCase):
    def test_utc_zero(self):
        self.assertEqual(_parse_timezone_offset_minutes("UTC"), 0)
        self.assertEqual(_parse_timezone_offset_minutes("Z"), 0)
        self.assertEqual(_parse_timezone_offset_minutes("+00:00"), 0)

    def test_positive_offset(self):
        self.assertEqual(_parse_timezone_offset_minutes("+05:30"), 5 * 60 + 30)
        self.assertEqual(_parse_timezone_offset_minutes("+08:00"), 8 * 60)

    def test_negative_offset(self):
        self.assertEqual(_parse_timezone_offset_minutes("-08:00"), -(8 * 60))
        self.assertEqual(_parse_timezone_offset_minutes("-05:30"), -(5 * 60 + 30))

    def test_invalid_returns_none(self):
        self.assertIsNone(_parse_timezone_offset_minutes(""))
        self.assertIsNone(_parse_timezone_offset_minutes(None))
        self.assertIsNone(_parse_timezone_offset_minutes("invalid"))


class TestDayOfYear(TestCase):
    def test_jan_1(self):
        self.assertEqual(_day_of_year(date(2025, 1, 1)), 1)

    def test_dec_31(self):
        self.assertEqual(_day_of_year(date(2025, 12, 31)), 365)

    def test_june_21(self):
        self.assertEqual(_day_of_year(date(2025, 6, 21)), 172)


class TestSolarDeclination(TestCase):
    def test_summer_solstice_positive(self):
        # ~June 21 northern summer
        n = _day_of_year(date(2025, 6, 21))
        decl = _solar_declination_rad(n)
        self.assertGreater(decl, 0)
        self.assertLess(decl, 0.5)

    def test_winter_solstice_negative(self):
        # ~Dec 21 northern winter
        n = _day_of_year(date(2025, 12, 21))
        decl = _solar_declination_rad(n)
        self.assertLess(decl, 0)
        self.assertGreater(decl, -0.5)


class TestSunriseSunsetHours(TestCase):
    def test_mid_latitudes_returns_bounds(self):
        # Roughly 40°N, 0° (e.g. Spain) on summer day
        result = get_sunrise_sunset_hours_local(40.0, 0.0, date(2025, 6, 21))
        self.assertIsNotNone(result)
        sunrise, sunset = result
        self.assertLess(sunrise, 12)
        self.assertGreater(sunset, 12)
        self.assertGreater(sunset - sunrise, 10)  # Long summer day

    def test_equator_roughly_12h_day(self):
        result = get_sunrise_sunset_hours_local(0.0, 0.0, date(2025, 3, 21))
        self.assertIsNotNone(result)
        sunrise, sunset = result
        self.assertAlmostEqual(sunrise, 6.0, delta=1.0)
        self.assertAlmostEqual(sunset, 18.0, delta=1.0)

    def test_invalid_latitude_returns_none(self):
        # Extreme or invalid
        result = get_sunrise_sunset_hours_local(None, 0.0, date(2025, 6, 21))  # type: ignore
        self.assertIsNone(result)


class TestIsTimeInSolarWindow(TestCase):
    def test_inside_window(self):
        # Sunrise 6, sunset 18 -> window 4.5 to 19.5
        self.assertTrue(is_time_in_solar_window(12.0, 6.0, 18.0))
        self.assertTrue(is_time_in_solar_window(5.0, 6.0, 18.0))  # 5 AM inside (4.5-19.5)
        self.assertTrue(is_time_in_solar_window(19.0, 6.0, 18.0))

    def test_outside_window(self):
        self.assertFalse(is_time_in_solar_window(2.0, 6.0, 18.0))  # Before 4.5
        self.assertFalse(is_time_in_solar_window(23.0, 6.0, 18.0))  # After 19.5

    def test_custom_buffers(self):
        # No buffer: window 6-18
        self.assertTrue(is_time_in_solar_window(7.0, 6.0, 18.0, 0, 0))
        self.assertFalse(is_time_in_solar_window(5.0, 6.0, 18.0, 0, 0))


class TestUtcToLocalHour(TestCase):
    def test_utc_plus_5_30(self):
        utc = datetime(2025, 6, 21, 6, 30, 0)  # 06:30 UTC
        local_hour = utc_to_local_hour(utc, 5 * 60 + 30)  # +05:30
        self.assertAlmostEqual(local_hour, 12.0, places=2)  # 12:00 local

    def test_utc_minus_8(self):
        utc = datetime(2025, 6, 21, 20, 0, 0)  # 20:00 UTC
        local_hour = utc_to_local_hour(utc, -(8 * 60))  # -08:00
        self.assertAlmostEqual(local_hour, 12.0, places=2)  # 12:00 local


class TestIsAssetInsideSolarWindow(TestCase):
    """Tests for is_asset_inside_solar_window require AssetList; integration-style."""

    def test_missing_asset_returns_true(self):
        from data_collection.services.solar_window import is_asset_inside_solar_window

        # Non-existent asset: default to True (allow write)
        result = is_asset_inside_solar_window("__nonexistent_asset__", now=timezone.now())
        self.assertTrue(result)
