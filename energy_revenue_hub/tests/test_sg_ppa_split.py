from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from energy_revenue_hub.contract_profiles.sg_ppa import SgPpaProfile
from energy_revenue_hub.models import BillingSession, UtilityInvoice
from main.models import assets_contracts


class SgPpaDcSplitTests(TestCase):
    def setUp(self):
        self.session = BillingSession.objects.create(
            country="SG",
            portfolio="test",
            asset_list=[
                {"asset_name": "Alpha", "asset_code": "ASSET_A"},
                {"asset_name": "Beta", "asset_code": "ASSET_B"},
            ],
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
            status=BillingSession.Status.REVIEWED,
        )
        assets_contracts.objects.create(
            asset_number="UN-SGPPA-A",
            asset_code="ASSET_A",
            asset_name="Alpha",
            contract_type="sg_ppa",
            sp_account_no="ACC999",
            requires_utility_invoice=True,
            generation_based_ppa_rate=Decimal("0.10"),
        )
        assets_contracts.objects.create(
            asset_number="UN-SGPPA-B",
            asset_code="ASSET_B",
            asset_name="Beta",
            contract_type="sg_ppa",
            sp_account_no="ACC999",
            requires_utility_invoice=True,
            generation_based_ppa_rate=Decimal("0.10"),
        )
        UtilityInvoice.objects.create(
            billing_session=self.session,
            account_no="ACC999",
            export_energy=Decimal("1000.00"),
            period_start=date(2025, 1, 1),
            period_end=date(2025, 1, 31),
        )

    @patch("energy_revenue_hub.contract_profiles.sg_ppa.aggregate_asset_kwh")
    @patch("energy_revenue_hub.contract_profiles.sg_ppa.resolve_dc_capacity_kw")
    def test_two_assets_dc_weighted_export_split(self, mock_dc, mock_kpi):
        mock_kpi.return_value = Decimal("50.00")

        def dc_side_effect(asset_code: str):
            if asset_code == "ASSET_A":
                return Decimal("400"), None
            if asset_code == "ASSET_B":
                return Decimal("600"), None
            return None, "unexpected asset"

        mock_dc.side_effect = dc_side_effect

        profile = SgPpaProfile()
        out = profile.compute_line_items(
            {
                "session": self.session,
                "norm_assets": [
                    {"asset_name": "Alpha", "asset_code": "ASSET_A"},
                    {"asset_name": "Beta", "asset_code": "ASSET_B"},
                ],
                "export_kwh_fallback": Decimal("0"),
            }
        )
        self.assertTrue(out.get("success"), msg=out)
        lines = {row["asset_code"]: row for row in out["line_items"]}
        self.assertEqual(lines["ASSET_A"]["export_kwh"], Decimal("400.00"))
        self.assertEqual(lines["ASSET_B"]["export_kwh"], Decimal("600.00"))
        self.assertEqual(lines["ASSET_A"]["revenue"], Decimal("40.00"))
        self.assertEqual(lines["ASSET_B"]["revenue"], Decimal("60.00"))
