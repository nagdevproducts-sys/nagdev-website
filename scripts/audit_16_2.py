"""Phase 16.2 audit: offers, alias pages, untracked, openingHours."""
import re, json, subprocess
from pathlib import Path

ROOT = Path(r"e:\APP BY DM\A_ANTIGRAVITY\10_NAGDEV")
PRODUCTS = ROOT / "products"

ACTIVE = [
    "castor-cake.html","commercial-castor-oil.html","dco-fatty-acid.html",
    "dehydrated-castor-oil.html","first-special-grade-castor-oil.html","fpd-castor-oil.html",
    "hydrogenated-castor-oil.html","castor-oil-bp93.html","castor-oil-ip.html",
    "castor-oil-jp.html","castor-oil-ph-eur.html","castor-oil-usp-nf.html",
    "cold-pressed-castor-oil.html","cosmetic-grade-castor-oil.html","ppg-castor-oil.html"
]

SCRIPT_RE = re.compile(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', re.DOTALL|re.IGNORECASE)
VISIBLE_PRICE_RE = re.compile(r'\$\s*[\d,]+|\d+\.?\d*\s*(USD|INR|per\s*(MT|KG|ton|kg))', re.IGNORECASE)

print("=== OFFERS AUDIT (15 active product pages) ===")
print(f"{'File':<45} {'Badge':<10} {'HasOffers':^9} {'Price':^10} {'VisiblePrice':^12} {'Decision'}")
print("-"*110)

for fname in ACTIVE:
    fpath = PRODUCTS / fname
    html = fpath.read_text(encoding="utf-8", errors="replace")

    badge = ("Regular" if "is-regular" in html else
             "Dev" if "is-dev" in html else "None")

    # Extract Product JSON-LD
    has_offers = False
    offer_price = ""
    for m in SCRIPT_RE.finditer(html):
        try:
            obj = json.loads(m.group(1).strip())
            for node in obj.get("@graph", []):
                if isinstance(node, dict) and node.get("@type") == "Product":
                    if "offers" in node:
                        has_offers = True
                        offers = node["offers"]
                        offer_price = str(offers.get("price", offers.get("priceSpecification", {}).get("description", "")))
        except: pass

    # Visible price on page (strip scripts/styles first)
    body = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    body = re.sub(r'<style[^>]*>.*?</style>', '', body, flags=re.DOTALL)
    body_text = re.sub(r'<[^>]+>', ' ', body)
    visible_price = bool(VISIBLE_PRICE_RE.search(body_text))

    decision = "REMOVE" if not visible_price else "KEEP"
    print(f"{fname:<45} {badge:<10} {str(has_offers):^9} {offer_price[:10]:^10} {str(visible_price):^12} {decision}")

print("\n=== ALIAS PAGE CHECK ===")
for fname in ["castor-cake-fertilizer.html", "de-oiled-cake-castor-meal.html"]:
    fpath = PRODUCTS / fname
    if fpath.exists():
        html = fpath.read_text(encoding="utf-8", errors="replace")
        lines = len(html.splitlines())
        has_redirect = bool(re.search(r'http-equiv.*refresh|301|window\.location', html, re.IGNORECASE))
        has_content = lines > 200
        print(f"{fname}: {lines} lines, has_redirect={has_redirect}, has_content={has_content}")
    else:
        print(f"{fname}: NOT FOUND")

print("\n=== OPENINGHOURS CHECK ===")
index_html = (ROOT / "index.html").read_text(encoding="utf-8", errors="replace")
for m in SCRIPT_RE.finditer(index_html):
    try:
        obj = json.loads(m.group(1).strip())
        for node in obj.get("@graph", []):
            if isinstance(node, dict) and "Organization" in (node.get("@type") or []):
                oh = node.get("openingHours")
                print(f"index.html openingHours: '{oh}'")
    except: pass

print("\n=== GIT UNTRACKED HTML FILES ===")
result = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True)
untracked = [l[3:].strip() for l in result.stdout.splitlines()
             if l.startswith("??") and l.endswith(".html")]
print(f"Untracked HTML files: {len(untracked)}")
for f in sorted(untracked)[:30]:
    print(f"  {f}")

print("\n=== TRAILING SLASH TEST URLS ===")
for path in ["/about/","/contact/","/products/","/products/first-special-grade-castor-oil/","/blog/fsg-vs-ppg-castor-oil-specification-differences/"]:
    print(f"  https://www.nagdevproducts.com{path}")
