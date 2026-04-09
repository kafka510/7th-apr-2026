from decimal import Decimal

from django.test import SimpleTestCase

from energy_revenue_hub.services.utility_invoice_rates import (
    build_anomaly_flag_json,
    compute_calculated_unit_rate,
)


class UtilityInvoiceRateTests(SimpleTestCase):
    def test_calculated_rate_not_quantized(self):
        out = compute_calculated_unit_rate(Decimal("3"), Decimal("1"))
        self.assertTrue(out.startswith("0.3333333333"))

    def test_anomaly_when_4dp_mismatch(self):
        calc = compute_calculated_unit_rate(Decimal("100"), Decimal("12.35"))
        payload = build_anomaly_flag_json(Decimal("0.1234"), calc)
        self.assertIn("unit_rate_4dp_mismatch", payload)

