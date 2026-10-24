import unittest
import sys
from pathlib import Path

# Add repo root to sys.path so we can import claims_lint
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from scripts.claims_lint import lint_content, load_facts

class TestClaimsLint(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.facts = load_facts()

    def test_r1_banned_phrase_every_ocean_shipment(self):
        html = "<p>Nagdev Products provides COA for every ocean shipment leaving Kandla port.</p>"
        findings = lint_content(html, "test.html", self.facts)
        fails = [f for f in findings if f["rule"].startswith("R1")]
        self.assertTrue(len(fails) > 0, "R1 must fail for 'every ocean shipment'")
        self.assertIn("every ocean shipment", fails[0]["text"])

    def test_r2_unheld_certification_iso(self):
        html = "<p>Our crushing facility is ISO 9001:2015 certified for quality management.</p>"
        findings = lint_content(html, "test.html", self.facts)
        fails = [f for f in findings if f["rule"].startswith("R2")]
        self.assertTrue(len(fails) > 0, "R2 must fail for 'ISO 9001:2015 certified'")

    def test_r3_under_dev_unqualified(self):
        html = "<p>We produce and supply high-purity sebacic acid to global polymers manufacturers.</p>"
        findings = lint_content(html, "test.html", self.facts)
        fails = [f for f in findings if f["rule"].startswith("R3")]
        self.assertTrue(len(fails) > 0, "R3 must fail when under-dev product is claimed to be supplied without qualification")

    def test_r4_invalid_product_count(self):
        html = "<p>Browse our catalog of 20 products and specialized oleochemicals.</p>"
        findings = lint_content(html, "test.html", self.facts)
        fails = [f for f in findings if f["rule"].startswith("R4")]
        self.assertTrue(len(fails) > 0, "R4 must fail for '20 products'")

    def test_r5_plant_district_banaskantha(self):
        html = "<p>Our manufacturing plant is located at Deodar, Banaskantha, Gujarat.</p>"
        findings = lint_content(html, "test.html", self.facts)
        fails = [f for f in findings if f["rule"].startswith("R5")]
        self.assertTrue(len(fails) > 0, "R5 must fail for 'Deodar, Banaskantha'")

    def test_r6_capacity_tpa_claim(self):
        html = "<p>Our plant operates at an annual seed crushing capacity of 15,000 TPA.</p>"
        findings = lint_content(html, "test.html", self.facts)
        fails = [f for f in findings if f["rule"].startswith("R6")]
        self.assertTrue(len(fails) > 0, "R6 must fail for '15,000 TPA'")

    def test_r7_spec_consistency_ffa_mismatch(self):
        html = """
        <html>
        <body>
          <div class="key-facts-wrapper">
            <p>Key Specifications: FFA: ≤ 0.50% · Acid Value: ≤ 1.0</p>
          </div>
          <section class="spec-table-section">
            <table class="spec-table">
              <tr><td>1</td><td>Free Fatty Acid (FFA)</td><td>1% Max</td></tr>
              <tr><td>2</td><td>Acid Value</td><td>2.0 mg KOH/g Max</td></tr>
            </table>
          </section>
        </body>
        </html>
        """
        findings = lint_content(html, "products/first-special-grade-castor-oil.html", self.facts)
        fails = [f for f in findings if f["rule"].startswith("R7")]
        self.assertTrue(len(fails) > 0, "R7 must fail when FFA ≤ 0.50% conflicts with table 1% Max")

    def test_r8_commercial_terms_moq(self):
        html = "<tr><td>Minimum Order (MOQ)</td><td>1 FCL (16–21.5 MT)</td></tr>"
        findings = lint_content(html, "test.html", self.facts)
        fails = [f for f in findings if f["rule"].startswith("R8")]
        self.assertTrue(len(fails) > 0, "R8 must fail for 'MOQ: 1 FCL'")

    def test_fixtures_must_pass(self):
        clean_html = """
        <html>
        <head>
          <meta name="description" content="Commercial Castor Oil supplied by Nagdev Products from Deodar, Vav-Tharad district.">
        </head>
        <body>
          <p>Commercial Castor Oil is raw unrefined castor oil produced by Nagdev Products at its 50 TPD expeller plant in Deodar, Vav-Tharad district, North Gujarat.</p>
          <p>We source castor seeds directly from local farmers in Banaskantha and Vav-Tharad.</p>
          <p>Documentation for buyer qualification includes COA per lot, TDS, and SDS. Third-party inspection by SGS, Bureau Veritas or Intertek can be arranged at the buyer's request and cost.</p>
          <p>Spot orders and term supply contracts are available on enquiry.</p>
          <p>Export documents provided as required by the buyer: COA, TDS, SDS, commercial invoice, packing list, certificate of origin.</p>
          <p>Sebacic acid is under development in our R&D pipeline.</p>
          <p>We offer 27 products across 7 regular supply grades, 7 on enquiry, and 13 under development.</p>
          <section class="spec-table-section">
            <table class="spec-table">
              <tr><td>1</td><td>Free Fatty Acid (FFA)</td><td>1% Max</td></tr>
              <tr><td>2</td><td>Acid Value</td><td>2.0 mg KOH/g Max</td></tr>
            </table>
          </section>
        </body>
        </html>
        """
        findings = lint_content(clean_html, "products/commercial-castor-oil.html", self.facts)
        fails = [f for f in findings if f["severity"] == "FAIL"]
        self.assertEqual(len(fails), 0, f"Clean fixture should have 0 failures, got: {fails}")

if __name__ == "__main__":
    unittest.main()
