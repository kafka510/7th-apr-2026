from decimal import Decimal
from types import SimpleNamespace

from django.test import SimpleTestCase

from energy_revenue_hub.services.kpi_billing_aggregate import daily_kwh_from_kpi_row


class KpiBillingAggregateUnitTests(SimpleTestCase):
    def test_prefers_positive_daily_max_min(self):
        row = SimpleNamespace(daily_max_min=12.25, oem_daily_product_kwh=50.0)
        self.assertEqual(daily_kwh_from_kpi_row(row), Decimal("12.25"))

    def test_falls_back_to_oem_when_daily_max_min_zero(self):
        row = SimpleNamespace(daily_max_min=0.0, oem_daily_product_kwh=7.5)
        self.assertEqual(daily_kwh_from_kpi_row(row), Decimal("7.5"))

    def test_falls_back_to_oem_when_daily_max_min_negative(self):
        row = SimpleNamespace(daily_max_min=-1.0, oem_daily_product_kwh=3.0)
        self.assertEqual(daily_kwh_from_kpi_row(row), Decimal("3.0"))

    def test_zero_when_both_missing(self):
        row = SimpleNamespace(daily_max_min=None, oem_daily_product_kwh=None)
        self.assertEqual(daily_kwh_from_kpi_row(row), Decimal("0"))
