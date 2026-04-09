from django.test import SimpleTestCase

from energy_revenue_hub.parsers.sp_singapore_parser import (
    SPSingaporeParser,
    detect_current_charges_excl_gst_from_text,
)


class SPSingaporeParserTests(SimpleTestCase):
    def test_detect_current_charges_excl_gst_from_text(self):
        txt = "Current Charges Exclusive of GST 113.02"
        self.assertEqual(detect_current_charges_excl_gst_from_text(txt), 113.02)

    def test_parse_sets_current_charges_excl_gst(self):
        txt = (
            "Account No 9311761309 Invoice No 5406342649 Bill Dated 06 Mar 2026 "
            "Export of Electricity (Net kWh) 53,796.61 kWh 0.0989 5,317.97 "
            "Current Charges Exclusive of GST 113.02"
        )
        parser = SPSingaporeParser()
        out = parser.parse(text=txt, words=None, tables=None)
        self.assertEqual(out.get("current_charges_excl_gst"), 113.02)
        self.assertEqual(out.get("recurring_charges"), 113.02)

