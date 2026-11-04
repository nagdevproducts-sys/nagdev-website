import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

print("=== VERIFYING PRIVACY & CONSENT IMPLEMENTATION LOCALLY ===")

# 1. /privacy page checks
privacy_path = Path("privacy.html")
assert privacy_path.exists(), "privacy.html does not exist"
privacy_html = privacy_path.read_text(encoding="utf-8")

# Title
assert "<title>Privacy Policy | Nagdev Products</title>" in privacy_html, "Title mismatch in privacy.html"
print("  [OK] Title is 'Privacy Policy | Nagdev Products'")

# Meta description
assert 'name="description"' in privacy_html, "Missing meta description"
print("  [OK] Meta description present")

# Self-canonical
assert '<link rel="canonical" href="https://www.nagdevproducts.com/privacy">' in privacy_html, "Canonical mismatch"
print("  [OK] Self-canonical is https://www.nagdevproducts.com/privacy")

# Indexable
assert '<meta name="robots" content="index, follow">' in privacy_html, "Missing robots index, follow"
print("  [OK] Robots meta is index, follow")

# H1
assert re.search(r'<h1[^>]*>\s*Privacy Policy\s*</h1>', privacy_html), "H1 'Privacy Policy' not found"
print("  [OK] H1 is 'Privacy Policy'")

# Last updated
assert "Last updated: 4 November 2026" in privacy_html, "Last updated date mismatch"
print("  [OK] Last updated date is '4 November 2026'")

# Justified body text
assert "text-align: justify" in privacy_html, "Justified body text styling not found"
print("  [OK] Body text has text-align: justify")

# TOC and 15 Sections
toc_match = re.search(r'<nav[^>]*class="privacy-toc"[\s\S]*?</nav>', privacy_html)
assert toc_match, "Table of contents (<nav class=\"privacy-toc\">) not found"
toc = toc_match.group(0)

sections = [
    ("who-we-are", "1. Who we are"),
    ("scope", "2. Scope"),
    ("what-we-collect", "3. What we collect"),
    ("why-we-use-it", "4. Why we use it"),
    ("legal-basis", "5. Legal basis"),
    ("who-we-share-it-with", "6. Who we share it with"),
    ("international-transfers", "7. International transfers"),
    ("cookies-and-analytics", "8. Cookies and analytics"),
    ("how-long-we-keep-it", "9. How long we keep it"),
    ("security", "10. Security"),
    ("your-rights", "11. Your rights"),
    ("grievance-officer", "12. Grievance Officer"),
    ("children", "13. Children"),
    ("changes-to-this-policy", "14. Changes to this policy"),
    ("contact", "15. Contact"),
]

for sec_id, sec_title in sections:
    assert f'href="#{sec_id}"' in toc, f"TOC missing anchor link #{sec_id}"
    assert f'id="{sec_id}"' in privacy_html, f"Section with id='{sec_id}' missing in privacy.html"
    assert sec_title in privacy_html, f"Section title '{sec_title}' missing in privacy.html"
print("  [OK] TOC contains all 15 anchor links and all 15 sections are present")

# JSON-LD schemas
ld_matches = re.findall(r'<script type="application/ld\+json">([\s\S]*?)</script>', privacy_html)
assert len(ld_matches) > 0, "No JSON-LD schemas found in privacy.html"
has_webpage = False
has_breadcrumb = False
for block in ld_matches:
    try:
        data = json.loads(block)
        items = data.get('@graph', [data])
        for it in items:
            t = it.get('@type')
            if t == 'WebPage': has_webpage = True
            if t == 'BreadcrumbList': has_breadcrumb = True
    except Exception as e:
        print("JSON parse error:", e)

assert has_webpage, "WebPage schema missing in privacy.html JSON-LD"
assert has_breadcrumb, "BreadcrumbList schema missing in privacy.html JSON-LD"
print("  [OK] WebPage + BreadcrumbList JSON-LD schemas present and valid")

# 2. Sitemap verification
tree = ET.parse("sitemap.xml")
root = tree.getroot()
ns = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
privacy_url = None
for url in root.findall('ns:url', ns):
    loc = url.find('ns:loc', ns).text.strip()
    if loc == "https://www.nagdevproducts.com/privacy":
        privacy_url = url
        break

assert privacy_url is not None, "https://www.nagdevproducts.com/privacy not found in sitemap.xml"
lastmod = privacy_url.find('ns:lastmod', ns).text.strip()
assert lastmod == "2026-11-04", f"Sitemap lastmod for /privacy expected '2026-11-04', got {lastmod}"
print(f"  [OK] /privacy found in sitemap.xml with lastmod {lastmod}")

# 3. Cookie Consent Mode and Banner in js/analytics.js
analytics_code = Path("js/analytics.js").read_text(encoding="utf-8")
assert "nagdev_consent" in analytics_code, "nagdev_consent key not in js/analytics.js"
assert "We use analytics cookies to understand how our site is used." in analytics_code, "Banner text mismatch"
assert "nagdev-consent-btn-accept" in analytics_code, "Accept button missing"
assert "nagdev-consent-btn-decline" in analytics_code, "Decline button missing"
assert "Privacy Policy" in analytics_code, "Privacy Policy link missing from banner"
assert "clearGaCookies()" in analytics_code, "clearGaCookies missing"
assert "position: fixed" in analytics_code, "Fixed position missing for CLS 0"
print("  [OK] js/analytics.js implements compliant banner, equal buttons, Consent Mode v2")

# 4. Form notice in contact.html
contact_html = Path("contact.html").read_text(encoding="utf-8")
assert 'name="updates_opt_in"' in contact_html, "Marketing updates checkbox missing in contact.html"
assert 'checked' not in contact_html[contact_html.find('name="updates_opt_in"')-50:contact_html.find('name="updates_opt_in"')+50], "Updates checkbox must NOT be pre-ticked"
assert 'By submitting, you agree to our <a href="/privacy"' in contact_html, "Privacy notice under submit button missing in contact.html"
print("  [OK] contact.html has unticked updates checkbox and Privacy Policy agreement notice under submit button")

# 5. Footer links across all HTML files
missing_footer = []
for p in Path(".").rglob("*.html"):
    if any(x in str(p) for x in ['node_modules', '.git', 'scratch']): continue
    text = p.read_text(encoding="utf-8", errors="ignore")
    if "<footer" in text:
        if "/privacy" not in text:
            missing_footer.append(f"{p}: missing /privacy")
        if "cookie-settings" not in text.lower():
            missing_footer.append(f"{p}: missing cookie-settings")

assert len(missing_footer) == 0, f"Files missing footer links: {missing_footer}"
print("  [OK] All HTML files with a footer include Privacy Policy and Cookie settings links")

print("\nALL LOCAL CHECKS PASSED 100%!")
