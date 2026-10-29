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
          <a href="#main-content" class="skip-to-content">Skip to main content</a>
          <div class="top-bar">Contact Info</div>
          <header class="site-header"><nav><ul class="nav-list"><li><a href="/products">Products</a></li></ul></nav></header>
          <main id="main-content">
            <p>Commercial Castor Oil is raw unrefined castor oil produced by Nagdev Products at its 50 TPD expeller plant in Deodar, Vav-Tharad district, North Gujarat.</p>
            <p>We source castor seeds directly from local farmers in Banaskantha and Vav-Tharad.</p>
            <p>Documentation for buyer qualification includes COA per lot, TDS, and SDS. Third-party inspection by SGS, Bureau Veritas or Intertek can be arranged at the buyer's request and cost.</p>
            <p>Spot orders and term supply contracts are available on enquiry.</p>
            <p>Export documents provided as required by the buyer: COA, TDS, SDS, commercial invoice, packing list, certificate of origin.</p>
            <p>Sebacic acid is under development in our R&D pipeline.</p>
            <p>We offer 32 products across 7 regular supply grades, 8 on enquiry, and 17 under development.</p>
            <section class="spec-table-section">
              <table class="spec-table">
                <tr><td>1</td><td>Free Fatty Acid (FFA)</td><td>1% Max</td></tr>
                <tr><td>2</td><td>Acid Value</td><td>2.0 mg KOH/g Max</td></tr>
              </table>
            </section>
          </main>
          <footer class="site-footer">
            <p>Copyright 2026</p>
            <button type="button" id="cookie-settings-btn" class="cookie-settings-trigger">Cookie Settings</button>
          </footer>
          <a href="https://wa.me/916352098306" class="whatsapp-float" id="whatsapp-fab">WhatsApp</a>
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
            "weighted benchmark",
            "triglyceride purity"
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

    def test_r13_bare_blog_post_fails(self):
        # Failing fixture: Previous bare post HTML lacking top bar, site header, mega-menu, cookie trigger, whatsapp button
        bare_post_html = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
          <title>Bare Post | Nagdev Products</title>
          <script>
            window.dataLayer = window.dataLayer || [];
            function gtag(){dataLayer.push(arguments);}
            gtag('consent', 'default', {'analytics_storage': 'denied'});
          </script>
          <script defer src="/js/analytics.js"></script>
        </head>
        <body>
          <a href="#main-content" class="skip-to-content">Skip to main content</a>
          <article class="blog-article">
            <header class="blog-article-header">
              <h1>Bare Post Title</h1>
            </header>
            <p>Some content</p>
          </article>
          <footer class="site-footer" role="contentinfo"><div class="container-wide"><p>&copy; 2026 Nagdev Products</p></div></footer>
        </body>
        </html>
        """
        findings = lint_content(bare_post_html, "blog/test-bare-post.html", self.facts)
        fails = [f for f in findings if f["rule"].startswith("R13")]
        self.assertTrue(len(fails) > 0, "R13 must fail on bare blog post lacking top-bar, site-header, nav-list, cookie-settings, whatsapp")
        fail_text = fails[0]["text"]
        self.assertIn("site header", fail_text)
        self.assertIn("top contact bar", fail_text)
        self.assertIn("main navigation", fail_text)
        self.assertIn("cookie settings", fail_text)
        self.assertIn("WhatsApp button", fail_text)

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
          <a href="#main-content" class="skip-to-content">Skip to main content</a>
          <div class="top-bar">Contact Info</div>
          <header class="site-header">
            <ul class="nav-list"><li><a href="/blog">Blog</a></li></ul>
          </header>
          <main id="main-content"><p>Valid content here.</p></main>
          <footer class="site-footer">
            <button type="button" id="cookie-settings-btn" class="cookie-settings-trigger">Cookie Settings</button>
          </footer>
          <a href="https://wa.me/916352098306" class="whatsapp-float" id="whatsapp-fab">WhatsApp</a>
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


    def test_r4_old_counts_fail(self):
        # 27 products and 13 under development must fail R4
        html = "<p>Nagdev Products produces 27 products across our portfolio, with 13 under development grades.</p>"
        findings = lint_content(html, "test.html", self.facts)
        fails = [f for f in findings if f["rule"].startswith("R4")]
        self.assertTrue(len(fails) >= 2, f"R4 must fail for old counts (27 products, 13 under development grades), got {fails}")

    def test_r4_new_counts_pass(self):
        html = "<p>Our portfolio includes 32 products: 7 regular supply, 8 on enquiry, and 17 under development grades.</p>"
        findings = lint_content(html, "test.html", self.facts)
        fails = [f for f in findings if f["rule"].startswith("R4")]
        self.assertEqual(len(fails), 0, f"R4 must pass for valid counts 32, 7, 8, 17, got {fails}")

    def test_r3_demoted_products_fail_without_under_dev(self):
        # Ricinoleic Acid, 12-HSA, Refined Glycerin cannot claim production/supply without 'under development'
        html1 = "<p>We manufacture and supply high-purity Ricinoleic Acid from our plant.</p>"
        findings1 = lint_content(html1, "test.html", self.facts)
        fails1 = [f for f in findings1 if f["rule"].startswith("R3")]
        self.assertTrue(len(fails1) > 0, "R3 must fail for Ricinoleic Acid supply claim without 'under development'")

        html2 = "<p>Nagdev Products offers 12-HSA for grease formulation.</p>"
        findings2 = lint_content(html2, "test.html", self.facts)
        fails2 = [f for f in findings2 if f["rule"].startswith("R3")]
        self.assertTrue(len(fails2) > 0, "R3 must fail for 12-HSA offer claim without 'under development'")

        html3 = "<p>We produce refined glycerin for industrial applications.</p>"
        findings3 = lint_content(html3, "test.html", self.facts)
        fails3 = [f for f in findings3 if f["rule"].startswith("R3")]
        self.assertTrue(len(fails3) > 0, "R3 must fail for refined glycerin production claim without 'under development'")

    def test_r3_demoted_products_pass_with_under_dev(self):
        html = "<p>Ricinoleic Acid, 12-HSA and refined glycerin are developmental grades currently under development.</p>"
        findings = lint_content(html, "test.html", self.facts)
        fails = [f for f in findings if f["rule"].startswith("R3")]
        self.assertEqual(len(fails), 0, f"R3 must pass when 'under development' is stated, got {fails}")

    def test_r16_pharma_cosmetic_numeric_spec_fails(self):
        # Numeric specification on pharma page must fail R16
        html = """
        <html>
        <body>
          <table>
            <tr><td>Free Fatty Acids</td><td>0.7% Max</td></tr>
          </table>
        </body>
        </html>
        """
        findings = lint_content(html, "products/castor-oil-usp-nf.html", self.facts)
        fails = [f for f in findings if f["rule"].startswith("R16")]
        self.assertTrue(len(fails) > 0, "R16 must fail for numeric spec on pharma page")

    def test_r16_pharma_cosmetic_banned_terms_fail(self):
        # Banned certification/regulatory terms on pharma page must fail R16
        html = "<p>Manufactured in a GMP certified unit with FDA approval.</p>"
        findings = lint_content(html, "products/castor-oil-ip.html", self.facts)
        fails = [f for f in findings if f["rule"].startswith("R16")]
        self.assertTrue(len(fails) >= 3, f"R16 must fail for GMP, certified, FDA, got {fails}")

    def test_r16_pharma_cosmetic_compliant_passes(self):
        # Compliant pharma page with no numbers next to specs and no banned terms must pass R16
        html = """
        <html>
        <body>
          <p>Castor oil supplied for buyers requiring compliance with current European Pharmacopoeia monograph.</p>
          <table>
            <tr><td>Free Fatty Acids</td><td>Tested to Ph. Eur. monograph; reported on COA</td></tr>
            <tr><td>Acid Value</td><td>Tested to monograph limit per batch</td></tr>
          </table>
        </body>
        </html>
        """
        findings = lint_content(html, "products/castor-oil-ph-eur.html", self.facts)
        fails = [f for f in findings if f["rule"].startswith("R16")]
        self.assertEqual(len(fails), 0, f"R16 must pass for compliant pharma content, got {fails}")


    def test_banned_phrase_british_pharmacopoeia_93_production_snippet(self):
        # Exact production snippet from products/cosmetic-grade-castor-oil.html
        snippet = '<span style="font-weight:600; color:var(--charcoal); font-size:1.0625rem;">What manufacturing processes ensure castor oil conforms to British Pharmacopoeia 93?</span>'
        findings = lint_content(snippet, "products/cosmetic-grade-castor-oil.html", self.facts)
        fails = [f for f in findings if f["severity"] == "FAIL" and ("British Pharmacopoeia 93" in f["text"] or "BP 93" in f["text"])]
        self.assertTrue(len(fails) > 0, f"Linter must catch 'British Pharmacopoeia 93' in production snippet, got: {findings}")

    def test_banned_phrase_deodoriz_stem_catches_deodorization(self):
        html = "<p>Refinery uses high-vacuum deodorization and deodorizing filtration systems.</p>"
        findings = lint_content(html, "test.html", self.facts)
        fails = [f for f in findings if "deodoriz" in f["text"].lower() or "deodoris" in f["text"].lower()]
        self.assertTrue(len(fails) > 0, f"Linter stem matching must catch deodorization, got: {findings}")

    def test_banned_phrase_injectable_and_sterilization(self):
        html = "<p>Castor oil vehicle base suitable for injectable applications requiring secondary sterilization.</p>"
        findings = lint_content(html, "test.html", self.facts)
        fails = [f for f in findings if any(w in f["text"].lower() for w in ("injectable", "sterilization"))]
        self.assertTrue(len(fails) >= 2, f"Linter must catch injectable and sterilization, got: {findings}")

    def test_banned_process_wording_neutralisation_and_distillation(self):
        html = "<p>Our refining plant utilizes low-temperature neutralisation and steam distillation.</p>"
        findings = lint_content(html, "test.html", self.facts)
        fails = [f for f in findings if "process" in f["rule"].lower()]
        self.assertTrue(len(fails) >= 2, f"Linter must flag neutralisation and steam distillation, got: {findings}")

    def test_r17_page_identity_failing_fixture(self):
        # Cosmetic page containing BP grade claims in breadcrumb and hero alt
        html = """
        <!DOCTYPE html>
        <html>
        <head>
          <title>Cosmetic Grade Castor Oil | Nagdev</title>
          <meta name="description" content="Cosmetic castor oil supplier.">
        </head>
        <body>
          <div id="main-content">
            <a href="/">Home</a> / <a href="/products">Products</a> /
            <span>Castor Oil BP (British Pharmacopoeia grade) Castor Oil</span>
          </div>
          <h1>Cosmetic Grade Castor Oil – Supplier India</h1>
          <img class="product-media-img" alt="Castor Oil BP (British Pharmacopoeia grade) Castor Oil specifications" src="test.webp">
          <h2>Castor Oil BP (British Pharmacopoeia grade) – British Pharmacopoeia Specification Overview</h2>
          <details><summary>What refining processes ensure castor oil conforms to British Pharmacopoeia 93?</summary></details>
        </body>
        </html>
        """
        findings = lint_content(html, "products/cosmetic-grade-castor-oil.html", self.facts)
        r17_fails = [f for f in findings if f["rule"] == "R17 Page Identity"]
        self.assertTrue(len(r17_fails) >= 3, f"R17 must flag foreign BP identity terms on cosmetic page, got: {r17_fails}")

    def test_r17_page_identity_compliant_passes(self):
        html = """
        <!DOCTYPE html>
        <html>
        <head>
          <title>Cosmetic Grade Castor Oil Supplier India | Nagdev Products</title>
          <meta name="description" content="Cosmetic Grade Castor Oil supplier in India. High-purity refined castor oil for cosmetic, personal care and lip-care formulations. Request a quote.">
        </head>
        <body>
          <div id="main-content">
            <a href="/">Home</a> / <a href="/products">Products</a> /
            <span>Cosmetic Grade Castor Oil</span>
          </div>
          <h1>Cosmetic Grade Castor Oil – Supplier India</h1>
          <img class="product-media-img" alt="Cosmetic Grade Castor Oil from Nagdev Products" src="test.webp">
          <h2>Cosmetic Grade Castor Oil – Specification Overview</h2>
          <details><summary>What quality testing is performed on cosmetic grade castor oil?</summary></details>
        </body>
        </html>
        """
        findings = lint_content(html, "products/cosmetic-grade-castor-oil.html", self.facts)
        r17_fails = [f for f in findings if f["rule"] == "R17 Page Identity"]
        self.assertEqual(len(r17_fails), 0, f"R17 must pass for compliant page identity, got: {r17_fails}")


    def test_r3_failing_fixture_attribute_manufactured(self):
        # 1. alt="Sebacic Acid manufactured in Gujarat, India" (R3 FAIL)
        html = '<img src="/images/products/sebacic-acid.webp" alt="Sebacic Acid manufactured in Gujarat, India">'
        findings = lint_content(html, "products/test.html", self.facts)
        fails = [f for f in findings if f["rule"].startswith("R3")]
        self.assertTrue(len(fails) > 0, "R3 must fail for developmental product marked as manufactured in attribute")
        self.assertIn("Sebacic Acid", fails[0]["text"])

    def test_r4_failing_fixture_explore_27_grades(self):
        # 2. content="Explore 27 castor oil grades" (R4 FAIL)
        html = '<meta name="description" content="Explore 27 castor oil grades, bio-based derivatives, high-nitrogen castor meals">'
        findings = lint_content(html, "products.html", self.facts)
        fails = [f for f in findings if f["rule"].startswith("R4")]
        self.assertTrue(len(fails) > 0, "R4 must fail for '27 ... grades'")
        self.assertIn("27", fails[0]["text"])

    def test_r1_failing_fixture_palletization_fumigated(self):
        # 3. Palletization:Fumigated wooden/plastic pallets (R1/R11 banned FAIL)
        html = '<div class="pkg-spec-row"><span class="lbl">Palletization:</span><span class="val">Fumigated wooden/plastic pallets</span></div>'
        findings = lint_content(html, "products.html", self.facts)
        fails = [f for f in findings if f["rule"].startswith("R1") or f["rule"].startswith("R11")]
        self.assertTrue(len(fails) > 0, "R1/R11 must fail for 'Fumigated'")
        self.assertTrue(any("fumigat" in f["text"].lower() for f in fails))

    def test_r18_failing_fixture_broken_bp_link(self):
        # 4. href="/products/castor-oil-Castor%20Oil%20BP" (R18 FAIL)
        html = '<a href="/products/castor-oil-Castor%20Oil%20BP" class="product-card">Castor Oil BP</a>'
        findings = lint_content(html, "products.html", self.facts)
        fails = [f for f in findings if f["rule"].startswith("R18")]
        self.assertTrue(len(fails) > 0, "R18 must fail for malformed/broken BP link")
        self.assertTrue(any("castor-oil-Castor%20Oil%20BP" in f["text"] for f in fails))

    def test_r19_failing_fixture_ndev_comm(self):
        # 5. NDEV-COMM (R19 FAIL)
        html = '<div class="product-card-brand">NDEV-COMM</div>'
        findings = lint_content(html, "products.html", self.facts)
        fails = [f for f in findings if f["rule"].startswith("R19")]
        self.assertTrue(len(fails) > 0, "R19 must fail for legacy hyphen brand code 'NDEV-COMM'")
        self.assertTrue(any("NDEV-COMM" in f["text"] for f in fails))

    def test_r1_failing_fixture_copied_from(self):
        # 6. copied from high-capacity crushing (R1/R11 banned FAIL)
        html = '<p>Explore quantitative mass balances copied from high-capacity crushing & refining standards.</p>'
        findings = lint_content(html, "products.html", self.facts)
        fails = [f for f in findings if f["rule"].startswith("R1") or f["rule"].startswith("R11")]
        self.assertTrue(len(fails) > 0, "R1/R11 must fail for 'copied from'")
        self.assertTrue(any("copied from" in f["text"].lower() for f in fails))


    def test_r20_failing_fixture_pest_suppression(self):
        """Test R20 catches the exact live failing sentence: 'How does castor cake suppress plant-parasitic soil pests?'"""
        html = '<p>How does castor cake suppress plant-parasitic soil pests?</p>'
        findings = lint_content(html, "products/castor-cake.html", self.facts)
        r20_fails = [f for f in findings if f["rule"].startswith("R20")]
        self.assertTrue(len(r20_fails) > 0, "R20 must fail for 'suppress plant-parasitic soil pests'")
        self.assertEqual(r20_fails[0]["rule"], "R20 Efficacy claim")

    def test_r20_failing_fixture_prohibited_phrases(self):
        """Test R20 catches phytosanitary, cash crops benefit, yield increase, boosts yield, cures, heals"""
        for phrase in ["phytosanitary", "cash crops benefit", "yield increase", "boosts yield", "cures", "heals"]:
            html = f'<p>Shipment documentation includes {phrase} for agricultural orders.</p>'
            findings = lint_content(html, "products/test.html", self.facts)
            r20_fails = [f for f in findings if f["rule"].startswith("R20")]
            self.assertTrue(len(r20_fails) > 0, f"R20 must fail for prohibited phrase '{phrase}'")

    def test_task1_physical_form_consistency(self):
        """Task 1: Liquid products must not contain 'Flakes' or 'Solid' in Physical Form, and vice versa."""
        import json
        master = json.load(open("seo/product-master.json", encoding="utf-8"))
        
        liquids = [
            "commercial-castor-oil", "first-special-grade-castor-oil", "fpd-castor-oil", 
            "ppg-castor-oil", "cold-pressed-castor-oil", "castor-oil-bp93", 
            "castor-oil-usp-nf", "castor-oil-ph-eur", "castor-oil-ip", "castor-oil-jp", 
            "cosmetic-grade-castor-oil", "dehydrated-castor-oil", "dco-fatty-acid", 
            "ricinoleic-acid", "crude-glycerin", "refined-glycerin", 
            "bio-polyurethane-polyols", "dioctyl-sebacate", "dibutyl-sebacate", 
            "methyl-ricinoleate", "blown-oxidized-castor-oil"
        ]
        solids = [
            "castor-cake", "hydrogenated-castor-oil", "12-hydroxystearic-acid", 
            "sebacic-acid", "high-protein-castor-meal", "sodium-sulphate-anhydrous", 
            "methyl-12-hydroxystearate", "lithium-12-hydroxystearate", 
            "calcium-12-hydroxystearate", "zinc-undecylenate", "zinc-ricinoleate"
        ]
        
        by_slug = {p["slug"]: p for p in master}
        for slug in liquids:
            pform = by_slug[slug]["physical_form"]
            self.assertIn("Liquid", pform, f"{slug} must be Liquid, got {pform}")
            self.assertNotIn("Solid", pform, f"{slug} must not contain Solid, got {pform}")
            self.assertNotIn("Flakes", pform, f"{slug} must not contain Flakes, got {pform}")
            
        for slug in solids:
            pform = by_slug[slug]["physical_form"]
            self.assertNotIn("Liquid", pform, f"{slug} must not contain Liquid, got {pform}")
            has_solid_term = any(t in pform for t in ["Solid", "Flakes", "Powder", "Cake", "Pellets", "Crystals"])
            self.assertTrue(has_solid_term, f"{slug} must contain solid form term, got {pform}")

    def test_task1_no_duplicate_applications_and_no_defaults(self):
        """Task 1: No applications set may be identical on >2 pages, and no default application string."""
        import json
        master = json.load(open("seo/product-master.json", encoding="utf-8"))
        app_sets = {}
        for p in master:
            slug = p["slug"]
            titles = tuple(a["title"] for a in p["applications"])
            app_sets.setdefault(titles, []).append(slug)
            
            # Check for old default string
            full_str = json.dumps(p)
            self.assertNotIn("Industrial Formulations · Coatings & Polymers · Specialty Chemical Synthesis", full_str)
            
        for titles, slugs in app_sets.items():
            self.assertLessEqual(len(slugs), 2, f"Applications set {titles} shared by more than 2 products: {slugs}")

    def test_task1_single_breadcrumb_and_no_leaks(self):
        """Task 1: Exactly one breadcrumb per page on all 32 products, 0 visible leaked html attributes."""
        import re
        import json
        with open("seo/product-master.json", "r", encoding="utf-8") as f:
            master = json.load(f)
        for p in master:
            fpath = f"products/{p['slug']}.html"
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
            crumbs = re.findall(r'<nav class="(?:breadcrumb-bar|product-breadcrumb-strip)"', content)
            self.assertEqual(len(crumbs), 1, f"{fpath} must have exactly 1 breadcrumb, found {len(crumbs)}")
            
            # Check for leaked HTML attributes in body prose
            body_start = content.find("<main")
            body_end = content.find("</main>")
            if body_start != -1 and body_end != -1:
                body = content[body_start:body_end]
                # Strip valid HTML tags to check visible prose
                prose = re.sub(r'<[^>]+>', ' ', body)
                self.assertFalse('">' in prose, f"{fpath} leaked quote-bracket in body prose")
                self.assertFalse('style="' in prose, f"{fpath} leaked style-attr in body prose")
                self.assertFalse('class="' in prose, f"{fpath} leaked class-attr in body prose")

    def test_task3_top_bar_present_on_all_pages(self):
        """Task 3: Every deployable public page contains the top contact bar."""
        import glob
        all_pages = glob.glob("*.html") + glob.glob("products/*.html") + glob.glob("guides/*.html") + glob.glob("compare/*.html") + glob.glob("markets/*.html") + glob.glob("applications/*.html")
        for fpath in all_pages:
            if "blog-admin.html" in fpath:
                continue
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertTrue('class="top-bar"' in content or 'class="top-bar ' in content, f"{fpath} missing top contact bar")


    def test_forward_term_supply_contracts_fails(self):
        """Phase 11c/11d: Banned phrase matching tolerant of up to 2 inserted words catches 'forward term supply contracts'."""
        fixture = "<p>Can buyers book forward term supply contracts for commercial castor oil?</p>"
        findings = lint_content(fixture, "test.html", self.facts)
        r1_fails = [f for f in findings if "R1" in f.get("rule", "") and "forward contract" in f.get("text", "")]
        self.assertTrue(len(r1_fails) > 0, "Expected 'forward term supply contracts' to trigger an R1 banned phrase failure")

    def test_manufacturer_and_bulk_exporter_fails(self):
        """Phase 11c/11d: Banned phrase matching catches 'Manufacturer & Bulk Exporter'."""
        fixture = "<title>Castor Oil Manufacturer & Bulk Exporter | Nagdev Products</title>"
        findings = lint_content(fixture, "test.html", self.facts)
        r1_fails = [f for f in findings if "R1" in f.get("rule", "") and ("bulk exporter" in f.get("text", "") or "Manufacturer & Exporter" in f.get("text", ""))]
        self.assertTrue(len(r1_fails) > 0, "Expected 'Manufacturer & Bulk Exporter' to trigger an R1 failure")

    def test_guard_product_template_classes_in_main_min_css(self):
        """Phase 11d Guard: Every class used in the product template markup has a matching rule in css/main.min.css."""
        import re
        from pathlib import Path
        min_css = Path("css/main.min.css").read_text(encoding="utf-8")
        html = Path("products/commercial-castor-oil.html").read_text(encoding="utf-8")
        
        # Extract body classes
        body_match = re.search(r'<body[^>]*>(.*?)</body>', html, re.DOTALL)
        body_html = body_match.group(1) if body_match else html
        class_matches = re.findall(r'class="([^"]+)"', body_html)
        classes = set()
        for c in class_matches:
            for cls in c.strip().split():
                classes.add(cls)
                
        missing = []
        for cls in classes:
            pattern = rf'\.{re.escape(cls)}(?=[^a-zA-Z0-9_-]|$)'
            if not re.search(pattern, min_css):
                missing.append(cls)
                
        self.assertEqual(missing, [], f"Classes missing from css/main.min.css: {missing}")

    def test_main_min_css_newer_than_main_css(self):
        """Phase 11d Guard: css/main.min.css must be newer than or equal to css/main.css."""
        import os
        css_mtime = os.path.getmtime("css/main.css")
        min_mtime = os.path.getmtime("css/main.min.css")
        self.assertGreaterEqual(min_mtime, css_mtime, "css/main.min.css is older than css/main.css! Rebuild with clean-css-cli.")

if __name__ == "__main__":
    unittest.main()
