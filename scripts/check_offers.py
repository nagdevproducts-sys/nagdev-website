import re, json
from pathlib import Path

PRODUCTS = Path("products")
SCRIPT_RE = re.compile(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', re.DOTALL|re.IGNORECASE)

pages = list(PRODUCTS.glob("*.html"))
has_offers = []
no_schema = []
no_offers = []
for f in sorted(pages):
    html = f.read_text(encoding="utf-8", errors="replace")
    found_product = False
    for m in SCRIPT_RE.finditer(html):
        try:
            obj = json.loads(m.group(1).strip())
            for node in obj.get("@graph", []):
                if isinstance(node, dict) and "Product" in str(node.get("@type", "")):
                    found_product = True
                    if "offers" in node:
                        has_offers.append(f.name)
                    else:
                        no_offers.append(f.name)
        except: pass
    if not found_product:
        no_schema.append(f.name)

print(f"Pages WITH offers remaining: {len(has_offers)}")
for f in has_offers:
    print(f"  {f}")
print(f"Pages WITHOUT offers (correct): {len(no_offers)}")
print(f"Pages with no Product schema: {len(no_schema)} -> {no_schema}")
