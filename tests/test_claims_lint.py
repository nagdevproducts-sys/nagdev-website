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
        <!DOCTYPE html>
        <html>
        <head>
          <meta name="description" content="Commercial Castor Oil supplied by Nagdev Products from Deodar, Vav-Tharad district.">
          <script>
            window.dataLayer = window.dataLayer || [];
            function gtag(){dataLayer.push(arguments);}
            gtag('consent', 'default', {'analytics_storage': 'denied'});
          </script>
          <script defer src="/js/analytics.js"></script>
        </head>
        <body>
          <header class="site-header"><nav>Menu</nav></header>
          <main>
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
          </main>
          <footer class="site-footer"><p>Copyright 2026</p></footer>
        </body>
        </html>
        """
        findings = lint_content(clean_html, "products/commercial-castor-oil.html", self.facts)
        fails = [f for f in findings if f["severity"] == "FAIL"]
        self.assertEqual(len(fails), 0, f"Clean fixture should have 0 failures, got: {fails}")

    def test_r10_table_source_missing_raw_data_fails(self):
        html = """
        <html>
        <body>
          <h3>Market Price Benchmark (Source: Agmarknet)</h3>
          <table>
            <tr><th>Market</th><th>Price</th></tr>
            <tr><td>Deodar</td><td>₹6,200</td></tr>
          </table>
        </body>
        </html>
        """
        findings = lint_content(html, "insights/market-test.html", self.facts)
        fails = [f for f in findings if f["rule"].startswith("R10")]
        self.assertTrue(len(fails) > 0, "R10 must fail when table cites Agmarknet without raw data/generator")

    def test_r11_banned_phrases_fail(self):
        banned = [
            "certified regional",
            "oil content",
            "seed oil content",
            "processing parity",
            "weighted benchmark"
        ]
        for phrase in banned:
            html = f"<p>This report evaluates {phrase} across North Gujarat markets.</p>"
            findings = lint_content(html, "test.html", self.facts)
            fails = [f for f in findings if f["rule"].startswith("R11")]
            self.assertTrue(len(fails) > 0, f"R11 must fail for banned phrase '{phrase}'")

    def test_r12_period_after_publish_date_fails(self):
        # Case A: 4 completed October weeks on 26 October
        html_a = """
        <html>
        <head>
          <meta name="publish-date" content="2026-10-26">
        </head>
        <body>
          <p>We review 4 completed October weeks of arrivals across Gujarat mandis.</p>
        </body>
        </html>
        """
        findings_a = lint_content(html_a, "insights/test.html", self.facts)
        fails_a = [f for f in findings_a if f["rule"].startswith("R12")]
        self.assertTrue(len(fails_a) > 0, "R12 must fail for '4 completed October weeks' on 26 October")

        # Case B: Period ending October 31, 2026 published on 2026-10-26
        html_b = """
        <html>
        <head>
          <meta name="publish-date" content="2026-10-26">
        </head>
        <body>
          <h2>Castor Seed Price Range: October 1–31, 2026</h2>
        </body>
        </html>
        """
        findings_b = lint_content(html_b, "insights/test.html", self.facts)
        fails_b = [f for f in findings_b if f["rule"].startswith("R12")]
        self.assertTrue(len(fails_b) > 0, "R12 must fail for date range ending Oct 31 when published Oct 26")

    def test_r13_missing_standard_components_fails(self):
        # Missing header, footer, consent, analytics
        bare_html = "<html><head><title>Test</title></head><body><h1>Content</h1></body></html>"
        findings = lint_content(bare_html, "test-page.html", self.facts)
        fails = [f for f in findings if f["rule"].startswith("R13")]
        self.assertTrue(len(fails) > 0, "R13 must fail when standard template components are missing")
        self.assertIn("site header", fails[0]["text"])
        self.assertIn("site footer", fails[0]["text"])
        self.assertIn("analytics script", fails[0]["text"])

    def test_r13_clean_standard_page_passes(self):
        standard_html = """
        <!DOCTYPE html>
        <html>
        <head>
          <title>Test Clean Page</title>
          <script>
            window.dataLayer = window.dataLayer || [];
            function gtag(){dataLayer.push(arguments);}
            gtag('consent', 'default', {'analytics_storage': 'denied'});
          </script>
          <script defer src="/js/analytics.js"></script>
        </head>
        <body>
          <header class="site-header"><nav>Menu</nav></header>
          <main><p>Valid content here.</p></main>
          <footer class="site-footer"><p>Copyright 2026</p></footer>
        </body>
        </html>
        """
        findings = lint_content(standard_html, "clean-test.html", self.facts)
        fails = [f for f in findings if f["rule"].startswith("R13")]
        self.assertEqual(len(fails), 0, f"R13 should pass for standard compliant page, got: {fails}")


    def test_r14_failing_fixture_location_and_facility(self):
        # Failing fixture: Image under /images/crop/ with location and plant facility claims
        failing_html = """
        <html>
        <body>
          <figure>
            <img src="/images/crop/castor-crop-field-rows-960w.webp" alt="Castor crop in North Gujarat">
            <figcaption>Cleaned castor seeds prepared for transport at our plant in Deodar</figcaption>
          </figure>
        </body>
        </html>
        """
        findings = lint_content(failing_html, "test-crop-fail.html", self.facts)
        fails = [f for f in findings if f["rule"].startswith("R14")]
        self.assertTrue(len(fails) >= 3, f"R14 must catch multiple forbidden terms, got: {fails}")
        reasons = [f["text"] for f in fails]
        self.assertTrue(any("North Gujarat" in r for r in reasons))
        self.assertTrue(any("cleaned" in r for r in reasons))
        self.assertTrue(any("prepared for" in r for r in reasons))
        self.assertTrue(any("our" in r for r in reasons))

    def test_r14_failing_fixture_video_missing_illustrative(self):
        # Failing fixture: Video under /media/video/ without 'illustrative' in caption
        failing_video_html = """
        <html>
        <body>
          <div>
            <video src="/media/video/castor-crop-to-seed.mp4"></video>
            <figcaption>Real footage of castor seeds arriving from APMC mandi.</figcaption>
          </div>
        </body>
        </html>
        """
        findings = lint_content(failing_video_html, "test-video-fail.html", self.facts)
        fails = [f for f in findings if f["rule"].startswith("R14")]
        self.assertTrue(len(fails) > 0, "R14 must fail when video caption lacks 'illustrative'")
        reasons = [f["text"] for f in fails]
        self.assertTrue(any("must contain the word 'illustrative'" in r for r in reasons))
        self.assertTrue(any("APMC" in r for r in reasons))
        self.assertTrue(any("mandi" in r for r in reasons))

    def test_r14_failing_fixture_gujarati_banned_terms(self):
        # Failing fixture: Gujarati banned terms in caption
        failing_gu_html = """
        <html>
        <body>
          <figure>
            <img src="/images/crop/castor-seeds-jute-sack-960w.webp" alt="એરંડાના બીજ">
            <figcaption>અમારા પ્લાન્ટ ખાતે બનાસકાંઠાના એરંડા</figcaption>
          </figure>
        </body>
        </html>
        """
        findings = lint_content(failing_gu_html, "test-gu-fail.html", self.facts)
        fails = [f for f in findings if f["rule"].startswith("R14")]
        self.assertTrue(len(fails) >= 2, "R14 must fail for Gujarati banned terms")
        reasons = [f["text"] for f in fails]
        self.assertTrue(any("અમારા" in r for r in reasons))
        self.assertTrue(any("પ્લાન્ટ" in r for r in reasons))
        self.assertTrue(any("બનાસકાંઠા" in r for r in reasons))

    def test_r14_clean_crop_and_video_passes(self):
        # Passing fixture: Neutral alt and figcaptions, video with 'illustrative'
        passing_html = """
        <html>
        <body>
          <figure>
            <img src="/images/crop/castor-crop-field-rows-960w.webp" alt="Castor crop growing in rows in an open field">
            <figcaption>Castor crop growing in rows in an open field.</figcaption>
          </figure>
          <div>
            <video src="/media/video/castor-crop-to-seed.mp4" aria-label="Illustrative footage of castor crop"></video>
            <figcaption>Castor crop to seed — illustrative footage.</figcaption>
          </div>
        </body>
        </html>
        """
        findings = lint_content(passing_html, "test-clean-crop.html", self.facts)
        fails = [f for f in findings if f["rule"].startswith("R14")]
        self.assertEqual(len(fails), 0, f"R14 should pass for completely honest captions, got: {fails}")


    def test_production_audit_homepage_included_and_validated(self):
        # 1. Verify https://www.nagdevproducts.com/ is explicitly guaranteed in audit set
        import xml.etree.ElementTree as ET
        sitemap_path = Path(__file__).resolve().parent.parent / "sitemap.xml"
        urls = set()
        urls.add("https://www.nagdevproducts.com/")
        if sitemap_path.exists():
            tree = ET.parse(sitemap_path)
            root = tree.getroot()
            namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            for loc in root.findall('.//ns:loc', namespace):
                urls.add(loc.text.strip())
        self.assertIn("https://www.nagdevproducts.com/", urls)

        # 2. Verify that homepage HTML with banned claims fails R1
        dirty_homepage = "<html><body><div class='trust-item'>India's Premier Castor Region</div></body></html>"
        findings = lint_content(dirty_homepage, "https://www.nagdevproducts.com/ (cache-busted)", self.facts)
        fails = [f for f in findings if f["severity"] == "FAIL"]
        self.assertTrue(any("premier" in f["text"].lower() for f in fails), "Homepage with 'India\'s Premier' must trigger R1 failure")

        # 3. Verify clean homepage passes R1-R14
        clean_homepage = (Path(__file__).resolve().parent.parent / "index.html").read_text(encoding="utf-8")
        clean_findings = lint_content(clean_homepage, "index.html", self.facts)
        clean_fails = [f for f in clean_findings if f["severity"] == "FAIL"]
        self.assertEqual(len(clean_fails), 0, f"Clean index.html must have 0 failures, got: {clean_fails}")


    def test_r15_cross_page_spec_mismatch_fails(self):
        # Failing fixture: table with outdated FSG Lovibond and Ricinoleic Acid AV
        dirty_html = """
        <html>
        <body>
          <table>
            <tr>
              <td>First Special Grade (FSG)</td>
              <td>Lovibond Y+5R < 2.5</td>
            </tr>
            <tr>
              <td>Ricinoleic Acid</td>
              <td>Acid Value 175–185</td>
            </tr>
          </table>
        </body>
        </html>
        """
        findings = lint_content(dirty_html, "test-specs.html", self.facts)
        fails = [f for f in findings if f["rule"].startswith("R15")]
        self.assertTrue(len(fails) >= 2, f"R15 must fail for both FSG Lovibond and Ricinoleic Acid AV, got: {fails}")

    def test_r15_clean_cross_page_specs_passes(self):
        # Passing fixture: canonical specs
        clean_html = """
        <html>
        <body>
          <table>
            <tr>
              <td>First Special Grade (FSG)</td>
              <td>FFA: 1% Max · Lovibond (5¼"): Max 20Y + 2R</td>
            </tr>
            <tr>
              <td>Ricinoleic Acid</td>
              <td>Purity: ≥ 85.0% · Acid Value: 175 Min</td>
            </tr>
          </table>
        </body>
        </html>
        """
        findings = lint_content(clean_html, "test-specs.html", self.facts)
        fails = [f for f in findings if f["rule"].startswith("R15")]
        self.assertEqual(len(fails), 0, f"R15 must pass for canonical specs, got: {fails}")

if __name__ == "__main__":
    unittest.main()
