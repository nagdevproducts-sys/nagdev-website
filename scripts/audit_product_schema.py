"""
Phase 16.1 — Audit all 34 product HTML files for Product JSON-LD offers blocks.
Outputs a table: file, has_product_schema, has_offers, price_value, is_under_dev, decision, reason
"""
import os, json, re
from pathlib import Path

PRODUCTS_DIR = Path(__file__).parent.parent / "products"

UNDER_DEV_PATTERNS = re.compile(
    r"under\s+development|development\s+pipeline|coming\s+soon|not\s+yet\s+available|"
    r"product\s+is\s+currently\s+under|being\s+developed|will\s+be\s+available",
    re.IGNORECASE
)

def extract_jsonld(html: str):
    """Return list of parsed JSON-LD dicts from <script type=application/ld+json> tags."""
    scripts = re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html, re.DOTALL | re.IGNORECASE
    )
    result = []
    for s in scripts:
        try:
            result.append(json.loads(s.strip()))
        except Exception as e:
            result.append({"_parse_error": str(e), "_raw": s[:200]})
    return result

def find_product_schema(blocks):
    for b in blocks:
        if isinstance(b, dict):
            types = b.get("@type", "")
            if isinstance(types, list):
                if "Product" in types:
                    return b
            elif types == "Product":
                return b
    return None

def get_price(offers):
    if not offers:
        return None
    if isinstance(offers, list):
        offers = offers[0]
    return str(offers.get("price", "")).strip()

results = []

for f in sorted(PRODUCTS_DIR.glob("*.html")):
    html = f.read_text(encoding="utf-8", errors="replace")
    
    # Strip script/style for body-text search
    body = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    body = re.sub(r'<style[^>]*>.*?</style>', '', body, flags=re.DOTALL)
    body_text = re.sub(r'<[^>]+>', ' ', body)

    is_under_dev = bool(UNDER_DEV_PATTERNS.search(body_text))
    
    blocks = extract_jsonld(html)
    product = find_product_schema(blocks)
    has_product = product is not None
    has_parse_error = any("_parse_error" in b for b in blocks if isinstance(b, dict))
    
    has_offers = False
    price_val = ""
    if product:
        offers = product.get("offers")
        has_offers = offers is not None
        price_val = get_price(offers) if has_offers else ""
    
    # Decision logic
    if not has_product:
        decision = "MISSING_SCHEMA"
        reason = "No Product JSON-LD found"
    elif is_under_dev:
        decision = "REMOVE_OFFERS"
        reason = "Page content says 'under development'"
    elif has_offers and price_val in ("0", "0.0", "", "null", "None"):
        decision = "REMOVE_OFFERS"
        reason = f"Price is '{price_val}' — placeholder/zero"
    elif has_offers and price_val == "":
        decision = "REMOVE_OFFERS"
        reason = "Price missing/empty"
    elif has_offers:
        decision = "KEEP_OFFERS"
        reason = f"Has valid price: '{price_val}'"
    else:
        decision = "NO_OFFERS"
        reason = "Schema has no offers block already"
    
    results.append({
        "file": f.name,
        "has_product": has_product,
        "has_offers": has_offers,
        "price": price_val,
        "is_under_dev": is_under_dev,
        "decision": decision,
        "reason": reason,
        "parse_error": has_parse_error,
    })

# Print table
print(f"{'File':<45} {'Schema':^6} {'Offers':^6} {'Price':<8} {'UnderDev':^8} {'Decision':<15} {'Reason'}")
print("-"*140)
for r in results:
    print(
        f"{r['file']:<45} {str(r['has_product']):^6} {str(r['has_offers']):^6} "
        f"{r['price']:<8} {str(r['is_under_dev']):^8} {r['decision']:<15} {r['reason']}"
    )

# Save JSON for the fix script
import pathlib
out = pathlib.Path(__file__).parent / "audit_results_16_1.json"
with open(out, "w") as fh:
    json.dump(results, fh, indent=2)
print(f"\nAudit results saved to: {out}")
