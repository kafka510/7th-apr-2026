from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

from django.test import SimpleTestCase

from energy_revenue_hub.services.invoice_snapshot import build_invoice_snapshot_json


class InvoiceSnapshotTests(SimpleTestCase):
    def _make_session(self, contract_type: str = "sg_ppa_maiora"):
        session = MagicMock()
        session.id = "550e8400-e29b-41d4-a716-446655440000"
        session.country = "SG"
        session.portfolio = "P1"
        session.start_date = date(2026, 1, 1)
        session.end_date = date(2026, 1, 31)
        session.invoice_template_id = "maiora_escalated"
        session.asset_list = []
        session.billing_contract_type = contract_type
        session.billing_month = date(2026, 1, 1)
        session.session_label = "sg_ppa_maiora · Jan 2026"
        session.billing_extras_json = {"gst_rate": "0.09"}
        return session

    def _make_line(
        self,
        *,
        asset_code: str,
        asset_name: str,
        line_kind: str,
        segment_index: int | None,
        leasing_year_label: str,
        period_start: date,
        period_end: date,
        invoice_kwh: str,
        ppa_rate: str,
        revenue: str,
    ):
        li = MagicMock()
        li.asset_code = asset_code
        li.asset_name = asset_name
        li.actual_kwh = Decimal(invoice_kwh)
        li.export_kwh = Decimal("0.00")
        li.invoice_kwh = Decimal(invoice_kwh)
        li.ppa_rate = Decimal(ppa_rate)
        li.revenue = Decimal(revenue)
        li.line_kind = line_kind
        li.sort_order = 0
        li.segment_index = segment_index
        li.period_start = period_start
        li.period_end = period_end
        li.leasing_year_label = leasing_year_label
        li.amount_excl_gst = Decimal(revenue)
        li.line_extras_json = {}
        return li

    def test_build_snapshot_totals_and_lines(self):
        session = self._make_session(contract_type="")

        li = MagicMock()
        li.asset_code = "A1"
        li.asset_name = "Site A"
        li.actual_kwh = Decimal("10.00")
        li.export_kwh = Decimal("100.00")
        li.invoice_kwh = Decimal("100.00")
        li.ppa_rate = Decimal("0.12")
        li.revenue = Decimal("12.00")
        li.line_kind = ""
        li.sort_order = 0
        li.segment_index = None
        li.period_start = None
        li.period_end = None
        li.leasing_year_label = ""
        li.amount_excl_gst = None
        li.line_extras_json = {}

        snap = build_invoice_snapshot_json(session, [li], version=2, utility_rows=[])
        self.assertEqual(snap["generated_version"], 2)
        self.assertEqual(snap["schema_version"], 2)
        self.assertEqual(snap["totals"]["invoice_kwh"], "100.00")
        self.assertEqual(snap["totals"]["revenue"], "12.00")
        self.assertEqual(len(snap["lines"]), 1)
        self.assertEqual(snap["lines"][0]["asset_code"], "A1")
        self.assertIn("combined_leasing_year_label", snap["lines"][0])
        self.assertIn("period_display", snap["lines"][0])
        self.assertEqual(snap["lines"][0]["invoice_kwh_display"], "100.00")
        self.assertEqual(snap["lines"][0]["ppa_rate_display"], "0.120000")
        self.assertEqual(snap["lines"][0]["revenue_display"], "12.00")

    def test_split_year_combined_label_and_period_display(self):
        session = self._make_session()
        c1 = self._make_line(
            asset_code="A1",
            asset_name="Site A",
            line_kind="consumption",
            segment_index=0,
            leasing_year_label="YR6",
            period_start=date(2026, 1, 10),
            period_end=date(2026, 1, 14),
            invoice_kwh="50.00",
            ppa_rate="0.100000",
            revenue="5.00",
        )
        c2 = self._make_line(
            asset_code="A1",
            asset_name="Site A",
            line_kind="consumption",
            segment_index=1,
            leasing_year_label="YR7",
            period_start=date(2026, 1, 15),
            period_end=date(2026, 1, 20),
            invoice_kwh="60.00",
            ppa_rate="0.110000",
            revenue="6.60",
        )
        snap = build_invoice_snapshot_json(session, [c1, c2], version=3, utility_rows=[])
        self.assertEqual(len(snap["lines"]), 2)
        self.assertEqual(snap["lines"][0]["combined_leasing_year_label"], "YR6/YR7")
        self.assertEqual(snap["lines"][1]["combined_leasing_year_label"], "YR6/YR7")
        self.assertEqual(snap["lines"][0]["period_display"], "10/01/2026 - 14/01/2026")
        self.assertEqual(snap["lines"][1]["period_display"], "15/01/2026 - 20/01/2026")

    def test_multi_asset_totals_and_gst_summary(self):
        session = self._make_session()
        a1 = self._make_line(
            asset_code="A1",
            asset_name="Site A",
            line_kind="consumption",
            segment_index=0,
            leasing_year_label="YR6",
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
            invoice_kwh="100.00",
            ppa_rate="0.120000",
            revenue="12.00",
        )
        a2 = self._make_line(
            asset_code="A2",
            asset_name="Site B",
            line_kind="consumption",
            segment_index=0,
            leasing_year_label="YR4",
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
            invoice_kwh="200.00",
            ppa_rate="0.150000",
            revenue="30.00",
        )
        snap = build_invoice_snapshot_json(session, [a1, a2], version=4, utility_rows=[])
        self.assertEqual(snap["totals"]["invoice_kwh"], "300.00")
        self.assertEqual(snap["totals"]["revenue"], "42.00")
        self.assertEqual(snap["totals"]["subtotal_excl_gst"], "42.00")
        self.assertEqual(snap["totals"]["gst_amount"], "3.78")
        self.assertEqual(snap["totals"]["total_incl_gst"], "45.78")

    def test_utility_snapshot_is_asset_scoped_for_single_generated_invoice(self):
        session = self._make_session()
        c = self._make_line(
            asset_code="A1",
            asset_name="Site A",
            line_kind="consumption",
            segment_index=0,
            leasing_year_label="YR5",
            period_start=date(2026, 1, 20),
            period_end=date(2026, 2, 19),
            invoice_kwh="80021.16",
            ppa_rate="0.120000",
            revenue="9602.54",
        )
        ex = self._make_line(
            asset_code="A1",
            asset_name="Site A",
            line_kind="export_excess",
            segment_index=0,
            leasing_year_label="YR5",
            period_start=date(2026, 1, 20),
            period_end=date(2026, 2, 19),
            invoice_kwh="38611.37",
            ppa_rate="0.096752",
            revenue="3735.74",
        )
        u = MagicMock()
        u.id = "u-1"
        u.account_no = "9311761309"
        u.invoice_number = "5406342649"
        u.invoice_date = date(2026, 3, 6)
        u.period_start = date(2026, 1, 20)
        u.period_end = date(2026, 2, 19)
        u.export_energy = Decimal("53796.61")
        u.export_energy_cost = Decimal("5317.97")
        u.recurring_charges_dollars = Decimal("113.02")
        u.net_unit_rate = "0.096752"
        u.unit_rate = Decimal("0.000000")
        u.currency_code = "SGD"
        snap = build_invoice_snapshot_json(session, [c, ex], version=5, utility_rows=[u])
        self.assertEqual(len(snap["utility_invoices"]), 1)
        uu = snap["utility_invoices"][0]
        self.assertEqual(uu["export_energy"], "38611.37")
        self.assertEqual(uu["export_payment"], "3735.74")
        self.assertEqual(uu["export_energy_cost"], "3816.86")
        self.assertEqual(uu["recurring_charges_dollars"], "81.12")
