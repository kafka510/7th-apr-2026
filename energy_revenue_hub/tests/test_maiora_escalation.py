"""Tests for Maiora leasing-year split and MRE escalation helpers."""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

from django.test import SimpleTestCase

from energy_revenue_hub.services.maiora_escalation import (
    compute_mre_rate,
    inclusive_days,
    leasing_year_index,
    split_period_by_anniversaries,
)


class MaioraEscalationTests(SimpleTestCase):
    def test_inclusive_days(self):
        self.assertEqual(inclusive_days(date(2026, 1, 20), date(2026, 2, 19)), 31)

    def test_leasing_year_index(self):
        cod = date(2020, 1, 15)
        self.assertEqual(leasing_year_index(cod, date(2026, 1, 14)), 6)
        self.assertEqual(leasing_year_index(cod, date(2026, 1, 15)), 7)

    def test_split_single_segment_no_anniversary_inside(self):
        cod = date(2020, 1, 15)
        ps, pe = date(2026, 1, 20), date(2026, 2, 19)
        segs = split_period_by_anniversaries(cod, ps, pe)
        self.assertEqual(segs, [(ps, pe)])

    def test_split_two_segments_across_anniversary(self):
        cod = date(2020, 1, 15)
        ps, pe = date(2026, 1, 10), date(2026, 1, 20)
        segs = split_period_by_anniversaries(cod, ps, pe)
        self.assertEqual(segs, [(date(2026, 1, 10), date(2026, 1, 14)), (date(2026, 1, 15), date(2026, 1, 20))])

    def test_compute_mre_no_escalation(self):
        c = MagicMock()
        c.rooftop_self_consumption_rate = Decimal("0.1")
        c.escalation_condition = "no"
        self.assertEqual(compute_mre_rate(c, 5), Decimal("0.1"))

    def test_compute_mre_multiplicative(self):
        c = MagicMock()
        c.rooftop_self_consumption_rate = Decimal("100")
        c.escalation_condition = "yes"
        c.escalation_type = "multiplicative"
        c.escalation_grace_years = 3
        c.escalation_period = 2
        c.escalation_rate = Decimal("0.01")
        # Y=4: floor(max(0,1)/2)=0 -> 100
        self.assertEqual(compute_mre_rate(c, 4), Decimal("100"))
        # Y=5: floor(max(0,2)/2)=1 -> 100 * 1.01
        y5 = (Decimal("100") * (Decimal("1.01") ** 1)).quantize(Decimal("0.000001"))
        self.assertEqual(compute_mre_rate(c, 5), y5)
