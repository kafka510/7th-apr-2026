from django.test import SimpleTestCase

from energy_revenue_hub.contract_profiles import get_profile, normalize_contract_type_key
from energy_revenue_hub.contract_profiles.sg_ppa import _norm_account
from energy_revenue_hub.services.billing_service import _normalize_assets, _unique_asset_codes


class NormalizeContractTypeTests(SimpleTestCase):
    def test_sg_ppa_aliases(self):
        self.assertEqual(normalize_contract_type_key("SG PPA"), "sg_ppa")
        self.assertEqual(normalize_contract_type_key("sg-ppa"), "sg_ppa")
        self.assertIsNotNone(get_profile("SG PPA"))

    def test_norm_account_strips_spaces(self):
        self.assertEqual(_norm_account("12 345 678"), _norm_account("12345678"))


class NormalizeAssetsTests(SimpleTestCase):
    def test_plain_strings_are_asset_codes(self):
        """Create session stores asset_list as code strings; billing must resolve them."""
        norm = _normalize_assets(["ASSET_A", "ASSET_B"])
        self.assertEqual(_unique_asset_codes(norm), ["ASSET_A", "ASSET_B"])

    def test_dict_entries_unchanged(self):
        norm = _normalize_assets([{"asset_name": "X", "asset_code": "C1"}])
        self.assertEqual(_unique_asset_codes(norm), ["C1"])
