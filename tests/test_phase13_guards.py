import glob
import json
import re
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

def test_guard_cta_whitelist():
    """Verify that quote and sample CTAs conform to the strict approved whitelist."""
    banned_variants = [
        "Request Commercial Quote",
        "Request Laboratory Sample",
        "Request Commercial Evaluation Sample",
        "Order Evaluation Sample",
        "Request Technical Sample",
        "Order Lab Sample",
        "Request Overseas Lab Sample",
        "Order Technical Sample",
        "Request Product Samples",
        "Request Product Sample",
        "Request Price Quote",
        "Request Bulk Price Quote",
        "Request International Export Quote",
        "Request Factory Quote"
    ]
    for path in REPO_ROOT.glob("**/*.html"):
        if any(part in str(path) for part in ["node_modules", ".git", "scratch", "tests"]):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for bv in banned_variants:
            assert bv not in text, f"Found unstandardized CTA '{bv}' in {path.name}"

def test_guard_packshot_aspect_ratio_and_object_fit():
    """Verify packshot cards have 4:3 aspect ratio and object-fit: contain."""
    css = (REPO_ROOT / "css" / "main.css").read_text(encoding="utf-8")
    assert "aspect-ratio: 4 / 3" in css or "aspect-ratio:4/3" in css, "Missing 4:3 aspect ratio on product cards"
    assert "object-fit: contain" in css or "object-fit:contain" in css, "Missing object-fit: contain on product images"

def test_guard_enquiry_api_endpoint_and_zero_formsubmit():
    """Verify contact form uses /api/enquiry and zero formsubmit references exist across site."""
    contact_html = (REPO_ROOT / "contact.html").read_text(encoding="utf-8")
    assert 'action="/api/enquiry"' in contact_html
    assert "formsubmit" not in contact_html.lower()

    site_js = (REPO_ROOT / "js" / "site.js").read_text(encoding="utf-8")
    assert "/api/enquiry" in site_js
    assert "formsubmit" not in site_js.lower()

    privacy_html = (REPO_ROOT / "privacy.html").read_text(encoding="utf-8")
    assert "formsubmit" not in privacy_html.lower()
    assert "via Resend" in privacy_html
    assert "Google Sheets" in privacy_html

def test_guard_mobile_drawer_hidden():
    """Verify off-canvas mobile drawer is hidden when closed to prevent scrollWidth expansion."""
    css = (REPO_ROOT / "css" / "main.css").read_text(encoding="utf-8")
    assert ".mobile-drawer:not(.open)" in css
    assert "display: none !important" in css

def test_guard_contrast_tokens():
    """Verify WCAG 2.2 AA compliant contrast tokens are declared in :root."""
    css = (REPO_ROOT / "css" / "main.css").read_text(encoding="utf-8")
    assert "--gold-text:" in css
    assert "#6B5628" in css
    assert "--gold-on-dark:" in css
    assert "#DFC07A" in css
    assert "--text-muted:" in css

def test_guard_product_pages_aria_lists():
    """Verify all 32 canonical product pages have role='list' on related products grid."""
    master = json.loads((REPO_ROOT / "seo" / "product-master.json").read_text(encoding="utf-8"))
    products = master if isinstance(master, list) else master.get("products", [])
    assert len(products) == 32
    for p in products:
        path = REPO_ROOT / "products" / f"{p['slug']}.html"
        assert path.exists(), f"Missing product page for {p['slug']}"
        text = path.read_text(encoding="utf-8")
        assert 'class="product-related-grid" role="list"' in text or "role=\"list\"" in text, f"Missing role='list' in {p['slug']}"

def test_guard_product_pages_scrollable_tables():
    """Verify all 32 canonical specification tables have tabindex='0' and role='region'."""
    master = json.loads((REPO_ROOT / "seo" / "product-master.json").read_text(encoding="utf-8"))
    products = master if isinstance(master, list) else master.get("products", [])
    assert len(products) == 32
    for p in products:
        path = REPO_ROOT / "products" / f"{p['slug']}.html"
        text = path.read_text(encoding="utf-8")
        assert 'tabindex="0" role="region"' in text, f"Missing scrollable region attributes in {p['slug']}"
