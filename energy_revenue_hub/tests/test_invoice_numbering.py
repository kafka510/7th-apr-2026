from __future__ import annotations

import os
from unittest.mock import patch

from django.test import TestCase

from energy_revenue_hub.models import BillingSession, GeneratedInvoice
from energy_revenue_hub.services.invoice_numbering import (
    build_output_invoice_number,
    compute_invoice_dates,
    format_global_seq,
    get_or_allocate_output_invoice_number,
    parse_live_ledger_contract_types,
    parse_live_sequence_allowed,
    parse_test_ledger_contract_types,
    resolve_invoice_sequence_ledger,
)


class InvoiceNumberingTests(TestCase):
    def test_parse_live_sequence_allowed_strict_true_only(self):
        with patch.dict(os.environ, {"ERH_INVOICE_LIVE_SEQUENCE_ALLOWED": "true"}, clear=False):
            self.assertTrue(parse_live_sequence_allowed())
        with patch.dict(os.environ, {"ERH_INVOICE_LIVE_SEQUENCE_ALLOWED": "True"}, clear=False):
            self.assertFalse(parse_live_sequence_allowed())
        with patch.dict(os.environ, {"ERH_INVOICE_LIVE_SEQUENCE_ALLOWED": "1"}, clear=False):
            self.assertFalse(parse_live_sequence_allowed())
        with patch.dict(os.environ, {"ERH_INVOICE_LIVE_SEQUENCE_ALLOWED": ""}, clear=False):
            self.assertFalse(parse_live_sequence_allowed())

    def test_parse_test_ledger_contract_types_is_normalized(self):
        with patch.dict(
            os.environ,
            {"ERH_INVOICE_TEST_LEDGER_CONTRACT_TYPES": "SG_PPA_MAIORA, future_contract"},
            clear=False,
        ):
            values = parse_test_ledger_contract_types()
        self.assertIn("sg_ppa_maiora", values)
        self.assertIn("future_contract", values)

    def test_parse_live_ledger_contract_types_is_normalized(self):
        with patch.dict(
            os.environ,
            {"ERH_INVOICE_LIVE_LEDGER_CONTRACT_TYPES": "SG_PPA_MAIORA, released_contract"},
            clear=False,
        ):
            values = parse_live_ledger_contract_types()
        self.assertIn("sg_ppa_maiora", values)
        self.assertIn("released_contract", values)

    def test_resolve_invoice_sequence_ledger_prefers_test_when_live_not_allowed(self):
        with patch.dict(os.environ, {"ERH_INVOICE_LIVE_SEQUENCE_ALLOWED": "false"}, clear=False):
            self.assertEqual(resolve_invoice_sequence_ledger("sg_ppa"), "test")

    def test_resolve_invoice_sequence_ledger_is_fail_closed_when_live_allowlist_empty(self):
        with patch.dict(
            os.environ,
            {
                "ERH_INVOICE_LIVE_SEQUENCE_ALLOWED": "true",
                "ERH_INVOICE_TEST_LEDGER_CONTRACT_TYPES": "sg_ppa_maiora",
                "ERH_INVOICE_LIVE_LEDGER_CONTRACT_TYPES": "",
            },
            clear=False,
        ):
            self.assertEqual(resolve_invoice_sequence_ledger("sg_ppa_maiora"), "test")
            self.assertEqual(resolve_invoice_sequence_ledger("sg_ppa"), "test")

    def test_resolve_invoice_sequence_ledger_uses_live_allowlist_when_present(self):
        with patch.dict(
            os.environ,
            {
                "ERH_INVOICE_LIVE_SEQUENCE_ALLOWED": "true",
                "ERH_INVOICE_LIVE_LEDGER_CONTRACT_TYPES": "sg_ppa, released_contract",
                "ERH_INVOICE_TEST_LEDGER_CONTRACT_TYPES": "sg_ppa_maiora",
            },
            clear=False,
        ):
            self.assertEqual(resolve_invoice_sequence_ledger("sg_ppa"), "production")
            self.assertEqual(resolve_invoice_sequence_ledger("released_contract"), "production")
            self.assertEqual(resolve_invoice_sequence_ledger("sg_ppa_maiora"), "test")

    def test_format_and_build_number(self):
        self.assertEqual(format_global_seq(1), "001")
        self.assertEqual(format_global_seq(1000), "1000")
        self.assertEqual(build_output_invoice_number("SG", "202601", 12, "production"), "SG-202601-012")
        self.assertEqual(build_output_invoice_number("SG", "202601", 12, "test"), "TEST-SG-202601-012")

    def test_reuses_existing_output_invoice_number(self):
        session = BillingSession.objects.create(
            country="SG",
            portfolio="P1",
            asset_list=["A1"],
            billing_contract_type="sg_ppa_maiora",
        )
        GeneratedInvoice.objects.create(
            billing_session=session,
            file_path="invoices/sample.pdf",
            version=1,
            output_invoice_number="TEST-SG-202601-123",
            invoice_asset_code="A1",
            billing_contract_type="sg_ppa_maiora",
            invoice_sequence_ledger="test",
        )
        output_number, ledger, contract_key = get_or_allocate_output_invoice_number(
            session=session,
            asset_code="A1",
            country="SG",
            yyyymm="202601",
        )
        self.assertEqual(output_number, "TEST-SG-202601-123")
        self.assertEqual(ledger, "test")
        self.assertEqual(contract_key, "sg_ppa_maiora")

    def test_does_not_reuse_when_existing_ledger_differs(self):
        session = BillingSession.objects.create(
            country="SG",
            portfolio="P1",
            asset_list=["A1"],
            billing_contract_type="sg_ppa_maiora",
        )
        GeneratedInvoice.objects.create(
            billing_session=session,
            file_path="invoices/sample.pdf",
            version=1,
            output_invoice_number="SG-202601-008",
            invoice_asset_code="A1",
            billing_contract_type="sg_ppa_maiora",
            invoice_sequence_ledger="production",
        )
        with (
            patch.dict(
                os.environ,
                {
                    "ERH_INVOICE_LIVE_SEQUENCE_ALLOWED": "true",
                    "ERH_INVOICE_LIVE_LEDGER_CONTRACT_TYPES": "",
                },
                clear=False,
            ),
            patch("energy_revenue_hub.services.invoice_numbering.next_sequence_value", return_value=9),
        ):
            output_number, ledger, contract_key = get_or_allocate_output_invoice_number(
                session=session,
                asset_code="A1",
                country="SG",
                yyyymm="202601",
            )
        self.assertEqual(output_number, "TEST-SG-202601-009")
        self.assertEqual(ledger, "test")
        self.assertEqual(contract_key, "sg_ppa_maiora")

    def test_missing_contract_type_raises_value_error(self):
        session = BillingSession.objects.create(
            country="SG",
            portfolio="P1",
            asset_list=["A1"],
            billing_contract_type="",
        )
        with self.assertRaises(ValueError):
            get_or_allocate_output_invoice_number(
                session=session,
                asset_code="A1",
                country="SG",
                yyyymm="202601",
            )

    def test_compute_invoice_dates_warns_when_timezone_invalid(self):
        with patch("energy_revenue_hub.services.invoice_numbering.AssetList") as mock_asset_list:
            mock_asset = type("MockAsset", (), {"timezone": ""})()
            mock_asset_list.objects.filter.return_value.only.return_value.first.return_value = mock_asset
            invoice_date, due_date, warnings = compute_invoice_dates("A1", "sg_ppa")
            self.assertEqual(invoice_date, "")
            self.assertEqual(due_date, "")
            self.assertTrue(warnings)

    def test_compute_invoice_dates_warns_when_due_days_missing(self):
        with (
            patch("energy_revenue_hub.services.invoice_numbering.AssetList") as mock_asset_list,
            patch("energy_revenue_hub.services.invoice_numbering.assets_contracts") as mock_contracts,
        ):
            mock_asset = type("MockAsset", (), {"timezone": "+05:30"})()
            mock_asset_list.objects.filter.return_value.only.return_value.first.return_value = mock_asset
            mock_contract = type("MockContract", (), {"due_days": None})()
            mock_contracts.objects.filter.return_value.first.return_value = mock_contract
            invoice_date, due_date, warnings = compute_invoice_dates("A1", "sg_ppa")
            self.assertNotEqual(invoice_date, "")
            self.assertEqual(invoice_date, due_date)
            self.assertTrue(any("due_days" in w for w in warnings))
