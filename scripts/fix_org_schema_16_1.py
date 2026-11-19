"""
Phase 16.1 — Fix Organization/LocalBusiness JSON-LD schema.

Pages index.html, contact.html, about.html: Full Organization+LocalBusiness block.
All other .html pages: Replace Org/LocalBusiness @graph node with reference-only.
"""
import re, json
from pathlib import Path

ROOT = Path(__file__).parent.parent

FULL_PAGES = {"index.html", "contact.html", "about.html"}

VERIFIED_SAMEAS = [
    "https://www.facebook.com/nagdevproducts",
    "https://www.instagram.com/nagdev.products/",
    "https://www.linkedin.com/company/nagdevproducts/"
]

FULL_ORG_BLOCK = {
    "@type": ["Organization", "LocalBusiness"],
    "@id": "https://www.nagdevproducts.com/#organization",
    "name": "Nagdev Products",
    "legalName": "Nagdev Products Private Limited",
    "url": "https://www.nagdevproducts.com/",
    "telephone": "+91-6352098306",
    "email": "nagdevproducts@gmail.com",
    "address": {
        "@type": "PostalAddress",
        "streetAddress": "Survey No. 301 P-2, Jada-Kotarwada Rd, Village Sardarpura, Post Ravel, Taluka Deodar, Dist. Vav-Tharad",
        "addressLocality": "Deodar",
        "addressRegion": "Gujarat",
        "postalCode": "385330",
        "addressCountry": "IN"
    },
    "department": {
        "@type": "Place",
        "name": "Nagdev Products \u2014 Head Office",
        "address": {
            "@type": "PostalAddress",
            "streetAddress": "612, 6th Floor, Sharan Circle Hub, SP Ring Road, Zundal Circle, Zundal",
            "addressLocality": "Gandhinagar",
            "addressRegion": "Gujarat",
            "postalCode": "382421",
            "addressCountry": "IN"
        }
    },
    "geo": {
        "@type": "GeoCoordinates",
        "latitude": 24.1817,
        "longitude": 71.8311
    },
    "sameAs": VERIFIED_SAMEAS,
    "logo": {
        "@type": "ImageObject",
        "url": "https://www.nagdevproducts.com/images/logo-dark.webp",
        "width": 165,
        "height": 48
    },
    "image": "https://www.nagdevproducts.com/images/og-share.jpg",
    "foundingDate": "2019",
    "numberOfEmployees": {"@type": "QuantitativeValue", "minValue": 20, "maxValue": 50},
    "identifier": {"@type": "PropertyValue", "propertyID": "CIN", "value": "U15400GJ2019PTC110518"},
    "contactPoint": {
        "@type": "ContactPoint",
        "telephone": "+91-6352098306",
        "contactType": "sales",
        "email": "nagdevproducts@gmail.com",
        "availableLanguage": ["English", "Hindi", "Gujarati"]
    },
    "openingHours": "Mo-Sa 09:00-18:00",
    "currenciesAccepted": "USD, INR",
    "priceRange": "$$"
}

ORG_REF = {
    "@type": "Organization",
    "@id": "https://www.nagdevproducts.com/#organization"
}

SCRIPT_RE = re.compile(
    r'(<script\s+type=["\']application/ld\+json["\'][^>]*>)(.*?)(</script>)',
    re.DOTALL | re.IGNORECASE
)

def is_org_node(node):
    """Return True if node is an Organization or LocalBusiness node."""
    if not isinstance(node, dict):
        return False
    t = node.get("@type", "")
    if isinstance(t, list):
        return "Organization" in t or "LocalBusiness" in t
    return t in ("Organization", "LocalBusiness")

def process_html(fpath, want_full):
    html = fpath.read_text(encoding="utf-8", errors="replace")
    matches = list(SCRIPT_RE.finditer(html))
    if not matches:
        return "NO_SCRIPT", html

    # Find block with @graph containing an Org node
    target_match = None
    for m in matches:
        try:
            obj = json.loads(m.group(2).strip())
            if "@graph" in obj and any(is_org_node(n) for n in obj["@graph"]):
                target_match = m
                break
        except:
            continue

    if not target_match:
        return "NO_ORG_NODE", html

    obj = json.loads(target_match.group(2).strip())
    graph = obj["@graph"]

    # Replace the org node
    new_graph = []
    replaced = False
    for node in graph:
        if isinstance(node, dict) and is_org_node(node) and not replaced:
            if want_full:
                new_graph.append(FULL_ORG_BLOCK)
            else:
                new_graph.append(ORG_REF)
            replaced = True
        else:
            new_graph.append(node)

    if not replaced:
        return "NO_ORG_REPLACED", html

    obj["@graph"] = new_graph
    new_json = json.dumps(obj, indent=2, ensure_ascii=False)
    new_html = (html[:target_match.start()] +
                target_match.group(1) + "\n" + new_json + "\n" + target_match.group(3) +
                html[target_match.end():])
    return "OK_FULL" if want_full else "OK_REF", new_html

# Collect all HTML files
html_files = []
for f in ROOT.glob("*.html"):
    html_files.append(f)
for f in ROOT.glob("**/*.html"):
    if f not in html_files:
        html_files.append(f)

# Deduplicate
html_files = list(set(html_files))

results = []
full_count = 0
ref_count = 0
errors = []

for fpath in sorted(html_files):
    fname = fpath.name
    # Relative path for display
    try:
        rel = fpath.relative_to(ROOT)
    except:
        rel = fpath

    want_full = fname in FULL_PAGES
    action, new_html = process_html(fpath, want_full)

    if action.startswith("OK"):
        fpath.write_text(new_html, encoding="utf-8")
        if want_full:
            full_count += 1
        else:
            ref_count += 1
        results.append((str(rel), action))
    else:
        errors.append((str(rel), action))

print(f"\nFull Org block applied to {full_count} pages")
print(f"Org reference applied to {ref_count} pages")
print(f"Errors/skipped: {len(errors)}")

if errors:
    print("\nErrors/skipped:")
    for rel, action in errors:
        print(f"  {rel}: {action}")

print("\nFull-block pages:")
for rel, action in results:
    if action == "OK_FULL":
        print(f"  {rel}: {action}")

# Spot-check: verify index.html has full block
print("\n--- Spot-check index.html ---")
html = (ROOT / "index.html").read_text(encoding="utf-8")
for m in SCRIPT_RE.finditer(html):
    try:
        obj = json.loads(m.group(2).strip())
        for node in obj.get("@graph", []):
            if isinstance(node, dict) and is_org_node(node):
                print(f"  legalName: {node.get('legalName')}")
                print(f"  department: {node.get('department', {}).get('name')}")
                print(f"  sameAs: {node.get('sameAs')}")
                break
    except: pass

# Spot-check: verify a product page has only reference
print("\n--- Spot-check products/ricinoleic-acid.html ---")
html = (ROOT / "products" / "ricinoleic-acid.html").read_text(encoding="utf-8")
for m in SCRIPT_RE.finditer(html):
    try:
        obj = json.loads(m.group(2).strip())
        for node in obj.get("@graph", []):
            if isinstance(node, dict) and is_org_node(node):
                keys = list(node.keys())
                print(f"  Org node keys: {keys}")
                break
    except: pass
