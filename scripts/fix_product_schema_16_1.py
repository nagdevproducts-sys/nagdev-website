"""
Phase 16.1 — Fix Product JSON-LD schemas in all 34 product HTML files.

UNDER-DEV pages (17): REMOVE the offers block from Product node in @graph.
ACTIVE pages (15):    KEEP offers. Fix manufacturer to reference by @id.
NO-SCHEMA pages (2):  castor-cake-fertilizer.html, de-oiled-cake-castor-meal.html — skip.
"""
import re, json
from pathlib import Path

PRODUCTS_DIR = Path(__file__).parent.parent / "products"

UNDER_DEV = {
    "12-hydroxystearic-acid.html",
    "bio-polyurethane-polyols.html",
    "blown-oxidized-castor-oil.html",
    "calcium-12-hydroxystearate.html",
    "crude-glycerin.html",
    "dibutyl-sebacate.html",
    "dioctyl-sebacate.html",
    "high-protein-castor-meal.html",
    "lithium-12-hydroxystearate.html",
    "methyl-12-hydroxystearate.html",
    "methyl-ricinoleate.html",
    "refined-glycerin.html",
    "ricinoleic-acid.html",
    "sebacic-acid.html",
    "sodium-sulphate-anhydrous.html",
    "zinc-ricinoleate.html",
    "zinc-undecylenate.html",
}

ACTIVE = {
    "castor-cake.html",
    "commercial-castor-oil.html",
    "dco-fatty-acid.html",
    "dehydrated-castor-oil.html",
    "first-special-grade-castor-oil.html",
    "fpd-castor-oil.html",
    "hydrogenated-castor-oil.html",
    "castor-oil-bp93.html",
    "castor-oil-ip.html",
    "castor-oil-jp.html",
    "castor-oil-ph-eur.html",
    "castor-oil-usp-nf.html",
    "cold-pressed-castor-oil.html",
    "cosmetic-grade-castor-oil.html",
    "ppg-castor-oil.html",
}

NO_SCHEMA = {
    "castor-cake-fertilizer.html",
    "de-oiled-cake-castor-meal.html",
}

ORG_ID_REF = {"@type": "Organization", "@id": "https://www.nagdevproducts.com/#organization"}

SCRIPT_RE = re.compile(
    r'(<script\s+type=["\']application/ld\+json["\'][^>]*>)(.*?)(</script>)',
    re.DOTALL | re.IGNORECASE
)

def is_product_node(node):
    t = node.get("@type", "")
    if isinstance(t, list):
        return "Product" in t
    return t == "Product"

def fix_product_node(node, is_dev):
    """Remove offers for dev products; fix manufacturer ref for all."""
    if "manufacturer" in node:
        node["manufacturer"] = ORG_ID_REF.copy()
    if "brand" not in node:
        node["brand"] = {"@type": "Brand", "name": "Nagdev Products"}
    if is_dev:
        node.pop("offers", None)
        node.pop("availability", None)
    return node

results = []

for f in sorted(PRODUCTS_DIR.glob("*.html")):
    fname = f.name

    if fname in NO_SCHEMA:
        results.append((fname, "SKIPPED", "No schema page - skipped"))
        continue

    is_dev = fname in UNDER_DEV
    is_active = fname in ACTIVE

    if not is_dev and not is_active:
        results.append((fname, "UNKNOWN", f"File not in any list - skipped"))
        continue

    html = f.read_text(encoding="utf-8", errors="replace")

    matches = list(SCRIPT_RE.finditer(html))
    if not matches:
        results.append((fname, "ERROR", "No ld+json script tag found"))
        continue

    target_match = None
    for m in matches:
        try:
            obj = json.loads(m.group(2).strip())
            if "@graph" in obj:
                target_match = m
                break
        except:
            continue

    if not target_match:
        results.append((fname, "ERROR", "No parseable ld+json with @graph found"))
        continue

    try:
        obj = json.loads(target_match.group(2).strip())
    except json.JSONDecodeError as e:
        results.append((fname, "PARSE_ERROR", str(e)))
        continue

    graph = obj.get("@graph", [])
    if not graph:
        results.append((fname, "ERROR", "@graph is empty"))
        continue

    modified = False
    for i, node in enumerate(graph):
        if isinstance(node, dict) and is_product_node(node):
            had_offers = "offers" in node
            graph[i] = fix_product_node(node, is_dev)
            if is_dev and had_offers:
                action = "REMOVE_OFFERS"
            elif not is_dev:
                action = "KEEP_OFFERS+FIX_MFR"
            else:
                action = "FIX_MFR_ONLY"
            modified = True
            break

    if not modified:
        results.append((fname, "NO_PRODUCT_NODE", "Product node not found in @graph"))
        continue

    obj["@graph"] = graph
    new_json = json.dumps(obj, indent=2, ensure_ascii=False)

    new_html = (html[:target_match.start()] +
                target_match.group(1) + "\n" + new_json + "\n" + target_match.group(3) +
                html[target_match.end():])

    f.write_text(new_html, encoding="utf-8")
    results.append((fname, action, "OK"))

print(f"\n{'File':<45} {'Action':<25} {'Result'}")
print("-" * 85)
for fname, action, result in results:
    print(f"{fname:<45} {action:<25} {result}")

counts = {}
for _, action, _ in results:
    counts[action] = counts.get(action, 0) + 1
print(f"\nSummary: {counts}")

# Spot-check
print("\n--- Verifying ricinoleic-acid.html (should have NO offers) ---")
html = (PRODUCTS_DIR / "ricinoleic-acid.html").read_text(encoding="utf-8")
for m in SCRIPT_RE.finditer(html):
    try:
        obj = json.loads(m.group(2).strip())
        for node in obj.get("@graph", []):
            if isinstance(node, dict) and is_product_node(node):
                print(f"  offers present: {'offers' in node}")
                print(f"  manufacturer: {node.get('manufacturer')}")
    except: pass

print("\n--- Verifying first-special-grade-castor-oil.html (should KEEP offers) ---")
html = (PRODUCTS_DIR / "first-special-grade-castor-oil.html").read_text(encoding="utf-8")
for m in SCRIPT_RE.finditer(html):
    try:
        obj = json.loads(m.group(2).strip())
        for node in obj.get("@graph", []):
            if isinstance(node, dict) and is_product_node(node):
                print(f"  offers present: {'offers' in node}")
                print(f"  manufacturer: {node.get('manufacturer')}")
    except: pass
