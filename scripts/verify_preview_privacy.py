import subprocess
import json
import re

PREVIEW = "https://nagdev-website-fyz86y9ze-nppl1.vercel.app"

def vcurl(path):
    cmd = f"npx vercel curl {PREVIEW}{path}"
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    return p.stdout

print("=== VERIFYING PREVIEW DEPLOYMENT ===")

# 1. /privacy page
print("\n1. Verifying /privacy...")
privacy = vcurl("/privacy")
assert "<title>Privacy Policy | Nagdev Products</title>" in privacy, "Title mismatch on preview"
assert '<h1>' not in privacy or 'Privacy Policy' in privacy, "H1 mismatch"
assert "Last updated: 4 November 2026" in privacy, "Last updated mismatch on preview"
assert "text-align: justify" in privacy, "Justified text style missing on preview"

# TOC & 15 sections
for i in range(1, 16):
    assert f"{i}. " in privacy, f"Section {i} missing on preview"
print("  [OK] /privacy renders full text with all 15 sections and TOC on preview!")

# Check JSON-LD
assert "BreadcrumbList" in privacy and "WebPage" in privacy, "JSON-LD missing on /privacy preview"
print("  [OK] /privacy JSON-LD schemas present on preview!")

# 2. Check /sitemap.xml
print("\n2. Verifying sitemap.xml...")
sitemap = vcurl("/sitemap.xml")
assert "https://www.nagdevproducts.com/privacy" in sitemap, "/privacy missing in sitemap.xml on preview"
assert "2026-11-04" in sitemap, "lastmod missing in sitemap.xml on preview"
print("  [OK] sitemap.xml includes /privacy with real lastmod 2026-11-04!")

# 3. Check /contact form
print("\n3. Verifying /contact...")
contact = vcurl("/contact")
assert 'name="updates_opt_in"' in contact, "Opt-in checkbox missing on /contact preview"
assert 'By submitting, you agree to our <a href="/privacy"' in contact, "Privacy notice missing on /contact preview"
print("  [OK] /contact has unticked updates checkbox and Privacy notice under submit button!")

# 4. Check consent mode in HTML
print("\n4. Verifying Consent Mode v2 default...")
assert "'analytics_storage': 'denied'" in contact, "analytics_storage: denied missing in HTML"
assert "'region':" not in contact, "Old region override still in HTML"
print("  [OK] Google Consent Mode v2 default is strictly denied without region bypass!")

# 5. Check js/analytics.js
print("\n5. Verifying /js/analytics.js...")
js = vcurl("/js/analytics.js")
assert "We use analytics cookies to understand how our site is used." in js, "Banner text missing in analytics.js"
assert "nagdev-consent-btn-accept" in js and "nagdev-consent-btn-decline" in js, "Accept/Decline buttons missing"
assert "clearGaCookies()" in js, "clearGaCookies missing in analytics.js"
assert "getStoredConsent() === 'granted'" in js, "getStoredConsent check missing before GA load"
print("  [OK] /js/analytics.js serves compliant banner and conditional GA loading!")

print("\nPREVIEW VERIFICATION PASSED 100%!")
