"""
Tests for write policy: should_write_reading, get_last_written, record_written_reading.
"""
from datetime import datetime
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from data_collection.services.write_policy import (
    get_last_written,
    record_written_reading,
    should_write_reading,
)


class WritePolicyTests(TestCase):
    def test_get_last_written_empty(self):
        self.assertIsNone(
            get_last_written("A1", "adapter1", series_key="default", interval_minutes=5)
        )

    def test_record_and_get_last_written(self):
        ts = timezone.now()
        record_written_reading(
            "A1", "adapter1", value="42.0", ts=ts, series_key="default", interval_minutes=5
        )
        out = get_last_written("A1", "adapter1", series_key="default", interval_minutes=5)
        self.assertIsNotNone(out)
        value, t = out
        self.assertEqual(value, "42.0")
        self.assertEqual(t, ts)

    def test_should_write_inside_solar_window(self):
        with patch("data_collection.services.write_policy.is_asset_inside_solar_window", return_value=True):
            write, reason = should_write_reading(
                "A1", "adapter1", current_value=100.0, interval_minutes=5
            )
        self.assertTrue(write)
        self.assertEqual(reason, "inside_solar_window")

    def test_should_write_outside_first_reading(self):
        with patch("data_collection.services.write_policy.is_asset_inside_solar_window", return_value=False):
            write, reason = should_write_reading(
                "A1", "adapter1", current_value=0.0, interval_minutes=5
            )
        self.assertTrue(write)
        self.assertEqual(reason, "outside_first_reading")

    def test_should_write_outside_value_changed(self):
        record_written_reading(
            "A2", "adapter1", value="0.0", ts=timezone.now(),
            series_key="default", interval_minutes=5
        )
        with patch("data_collection.services.write_policy.is_asset_inside_solar_window", return_value=False):
            write, reason = should_write_reading(
                "A2", "adapter1", current_value=1.0, interval_minutes=5
            )
        self.assertTrue(write)
        self.assertEqual(reason, "outside_value_changed")

    def test_should_write_outside_unchanged(self):
        record_written_reading(
            "A3", "adapter1", value="0.0", ts=timezone.now(),
            series_key="default", interval_minutes=5
        )
        with patch("data_collection.services.write_policy.is_asset_inside_solar_window", return_value=False):
            write, reason = should_write_reading(
                "A3", "adapter1", current_value="0.0", interval_minutes=5
            )
        self.assertFalse(write)
        self.assertEqual(reason, "outside_unchanged")
