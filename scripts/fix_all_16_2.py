"""
Phase 16.2 — Comprehensive fix script.

Tasks:
1. Remove offers from ALL 15 active product pages (B2B, no visible price)
2. Fix status badges: IP, JP, Ph.Eur, USP-NF, Cosmetic Grade → Dev/enquiry
3. Add alias page redirects to vercel.json
4. Add generic trailing-slash redirect rule
5. Fix middleware.js matcher
6. Remove openingHours if not matching GBP (it matches, so keep)
7. Delete one-off fix scripts
"""
import re, json, shutil
from pathlib import Path

ROOT = Path(r"e:\APP BY DM\A_ANTIGRAVITY\10_NAGDEV")
PRODUCTS = ROOT / "products"

SCRIPT_RE = re.compile(
    r'(<script\s+type=["\']application/ld\+json["\'][^>]*>)(.*?)(</script>)',
    re.DOTALL | re.IGNORECASE
)

ORG_REF = {"@type": "Organization", "@id": "https://www.nagdevproducts.com/#organization"}

def is_product_node(node):
    t = node.get("@type", "")
    return "Product" in (t if isinstance(t, list) else [t])

def remove_offers(fpath):
    """Remove offers from the Product node in a page's @graph JSON-LD."""
    html = fpath.read_text(encoding="utf-8", errors="replace")
    matches = list(SCRIPT_RE.finditer(html))
    for m in matches:
        try:
            obj = json.loads(m.group(2).strip())
            if "@graph" not in obj:
                continue
            changed = False
            for i, node in enumerate(obj["@graph"]):
                if isinstance(node, dict) and is_product_node(node):
                    if "offers" in node:
                        del node["offers"]
                        changed = True
                    if "availability" in node:
                        del node["availability"]
                        changed = True
                    # Fix manufacturer ref
                    if "manufacturer" in node:
                        node["manufacturer"] = ORG_REF.copy()
                    obj["@graph"][i] = node
            if changed:
                new_json = json.dumps(obj, indent=2, ensure_ascii=False)
                new_html = html[:m.start()] + m.group(1) + "\n" + new_json + "\n" + m.group(3) + html[m.end():]
                fpath.write_text(new_html, encoding="utf-8")
                return "REMOVED_OFFERS"
            else:
                return "NO_OFFERS_TO_REMOVE"
        except json.JSONDecodeError:
            continue
    return "NO_GRAPH_FOUND"

# ─── TASK 1: Remove offers from all 15 active pages ───────────────────────────
ALL_ACTIVE = [
    "castor-cake.html","commercial-castor-oil.html","dco-fatty-acid.html",
    "dehydrated-castor-oil.html","first-special-grade-castor-oil.html","fpd-castor-oil.html",
    "hydrogenated-castor-oil.html","castor-oil-bp93.html","castor-oil-ip.html",
    "castor-oil-jp.html","castor-oil-ph-eur.html","castor-oil-usp-nf.html",
    "cold-pressed-castor-oil.html","cosmetic-grade-castor-oil.html","ppg-castor-oil.html"
]

print("=== TASK 1: Remove offers from active pages ===")
for fname in ALL_ACTIVE:
    result = remove_offers(PRODUCTS / fname)
    print(f"  {fname}: {result}")

# ─── TASK 2: Fix status badges for IP, JP, Ph.Eur, USP-NF, Cosmetic Grade ────
# These should become "Available on Enquiry" / dev status
DEV_FIX = {
    "castor-oil-ip.html": "Castor Oil IP",
    "castor-oil-jp.html": "Castor Oil JP",
    "castor-oil-ph-eur.html": "Castor Oil Ph. Eur.",
    "castor-oil-usp-nf.html": "Castor Oil USP-NF",
    "cosmetic-grade-castor-oil.html": "Cosmetic Grade Castor Oil",
}

print("\n=== TASK 2: Fix status badges → Available on Enquiry ===")
for fname, product_name in DEV_FIX.items():
    fpath = PRODUCTS / fname
    html = fpath.read_text(encoding="utf-8", errors="replace")

    # Change badge: is-regular or no-badge → is-dev with "Available on Enquiry"
    old_html = html
    # Replace status badge class and text
    html = re.sub(
        r'product-status-badge\s+is-regular["\'][^>]*>.*?</div>',
        'product-status-badge is-dev">Available on Enquiry</div>',
        html, flags=re.DOTALL | re.IGNORECASE
    )
    # Also update availability in schema (already removed offers, but update WebPage description if needed)
    # Update JSON-LD availability from InStock to PreOrder/OutOfStock
    for m in SCRIPT_RE.finditer(html):
        try:
            obj = json.loads(m.group(2).strip())
            if "@graph" not in obj:
                continue
            changed = False
            for i, node in enumerate(obj["@graph"]):
                if isinstance(node, dict) and is_product_node(node):
                    # Ensure no offers and no availability
                    for field in ["offers", "availability"]:
                        if field in node:
                            del node[field]
                            changed = True
                    obj["@graph"][i] = node
            if changed:
                new_json = json.dumps(obj, indent=2, ensure_ascii=False)
                html = html[:m.start()] + m.group(1) + "\n" + new_json + "\n" + m.group(3) + html[m.end():]
        except:
            pass

    if html != old_html:
        fpath.write_text(html, encoding="utf-8")
        print(f"  {fname}: badge updated")
    else:
        print(f"  {fname}: no badge change needed (may already be dev or badge pattern differs)")

# ─── TASK 3: Add alias page redirects to vercel.json ─────────────────────────
print("\n=== TASK 3: Alias page redirects ===")
vj_path = ROOT / "vercel.json"
with open(vj_path, "r", encoding="utf-8") as f:
    vj = json.load(f)

alias_redirects = [
    {"source": "/products/castor-cake-fertilizer", "destination": "/products/castor-cake", "statusCode": 301},
    {"source": "/products/castor-cake-fertilizer/", "destination": "/products/castor-cake", "statusCode": 301},
    {"source": "/products/de-oiled-cake-castor-meal", "destination": "/products/castor-cake", "statusCode": 301},
    {"source": "/products/de-oiled-cake-castor-meal/", "destination": "/products/castor-cake", "statusCode": 301},
]

existing_sources = {r.get("source") for r in vj.get("redirects", [])}
added = 0
for r in alias_redirects:
    if r["source"] not in existing_sources:
        vj["redirects"].append(r)
        added += 1
        print(f"  Added: {r['source']} → {r['destination']}")
print(f"  Total alias redirects added: {added}")

# ─── TASK 4: Generic trailing-slash redirect rule ─────────────────────────────
print("\n=== TASK 4: Generic trailing-slash redirect ===")
# Insert AFTER the specific 4 trailing-slash rules (our-farms, exhibitions, awards, photo-gallery)
# but BEFORE the host normalizer catch-all
generic_slash = {
    "source": "/:path+/",
    "destination": "/:path+",
    "statusCode": 301
}

# Find if already exists
has_generic = any(r.get("source") == "/:path+/" for r in vj.get("redirects", []))
if not has_generic:
    # Insert after the 4 specific trailing-slash rules (indices 0-3)
    # Find position of first non-trailing-slash specific rule (the host normalizer at index 4)
    insert_at = 4  # After our-farms/, exhibitions/, awards/, photo-gallery/ (0-3)
    vj["redirects"].insert(insert_at, generic_slash)
    print(f"  Added generic /:path+/ → /:path+ at position {insert_at}")
else:
    print("  Generic trailing-slash rule already exists")

# Save vercel.json
with open(vj_path, "w", encoding="utf-8", newline="\n") as f:
    json.dump(vj, f, indent=2)

# Validate JSON
json.loads(open(vj_path).read())
print(f"  vercel.json valid. Total redirects: {len(vj['redirects'])}")
print(f"  First 6 redirects:")
for r in vj["redirects"][:6]:
    print(f"    {r.get('source')} -> {r.get('destination')} [{r.get('statusCode')}]")

# ─── TASK 5: Fix middleware.js ────────────────────────────────────────────────
print("\n=== TASK 5: Fix middleware.js ===")
middleware_content = '''/**
 * Vercel Edge Middleware — fires before static files are served.
 * Returns HTTP 410 Gone ONLY for requests to "/" with a wc-ajax query parameter.
 * All other requests pass through untouched.
 */
export const config = {
  matcher: ['/'],
};

export default function middleware(request) {
  const url = new URL(request.url);

  // Return 410 Gone only when wc-ajax query key is present (WordPress legacy AJAX)
  if (url.pathname === '/' && url.searchParams.has('wc-ajax')) {
    return new Response('Gone', {
      status: 410,
      headers: {
        'Content-Type': 'text/plain',
        'Cache-Control': 'no-store',
      },
    });
  }

  // All other requests: pass through (return undefined = no-op)
  return undefined;
}
'''
(ROOT / "middleware.js").write_text(middleware_content, encoding="utf-8")
print("  middleware.js updated with explicit pathname='/' guard")

# ─── TASK 6: OpeningHours check ────────────────────────────────────────────────
print("\n=== TASK 6: OpeningHours ===")
print("  'Mo-Sa 09:00-18:00' matches GBP — keeping as-is")

# ─── TASK 7: Delete one-off fix scripts ───────────────────────────────────────
print("\n=== TASK 7: Delete one-off scripts ===")
to_delete = ["fix_vercel_v2.py", "fix_vercel_v3.py", "fix_vercel_v4.py"]
for fname in to_delete:
    p = ROOT / "scripts" / fname
    if p.exists():
        p.unlink()
        print(f"  Deleted: scripts/{fname}")
    else:
        print(f"  Not found: scripts/{fname}")

print("\n=== ALL TASKS COMPLETE ===")
