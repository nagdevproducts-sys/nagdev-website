#!/usr/bin/env python3
"""
fix_org_schema_16_1.py
Phase 16.1 — Fix Organization/LocalBusiness JSON-LD schema.

1. Pages index.html, contact.html, about.html: Full Organization+LocalBusiness block,
   preserving existing geo if present.
2. All other .html pages: Replace Org/LocalBusiness @graph node with reference-only:
   {"@type": "Organization", "@id": "https://www.nagdevproducts.com/#organization"}
"""

import os
import re
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
EXCLUDE_DIRS = {'.git', '.vercel', 'node_modules', 'dist', 'build', '.vscode', 'scratch'}

FULL_PAGES = {"index.html", "contact.html", "about.html"}

VERIFIED_SAMEAS = [
    "https://www.facebook.com/nagdevproducts",
    "https://www.instagram.com/nagdev.products/",
    "https://www.linkedin.com/company/nagdevproducts/"
]

def make_full_org_block(existing_geo=None):
    block = {
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
            "name": "Nagdev Products — Head Office",
            "address": {
                "@type": "PostalAddress",
                "streetAddress": "612, 6th Floor, Sharan Circle Hub, SP Ring Road, Zundal Circle, Zundal",
                "addressLocality": "Gandhinagar",
                "addressRegion": "Gujarat",
                "postalCode": "382421",
                "addressCountry": "IN"
            }
        }
    }
    if existing_geo:
        block["geo"] = existing_geo

    block.update({
        "sameAs": VERIFIED_SAMEAS,
        "logo": {
            "@type": "ImageObject",
            "url": "https://www.nagdevproducts.com/images/logo-dark.webp",
            "width": 165,
            "height": 48
        },
        "image": "https://www.nagdevproducts.com/images/og-share.jpg",
        "foundingDate": "2019",
        "identifier": {
            "@type": "PropertyValue",
            "propertyID": "CIN",
            "value": "U15400GJ2019PTC110518"
        },
        "contactPoint": {
            "@type": "ContactPoint",
            "telephone": "+91-6352098306",
            "contactType": "sales",
            "email": "nagdevproducts@gmail.com",
            "availableLanguage": ["English", "Hindi", "Gujarati"]
        },
        "openingHours": "Mo-Sa 09:00-18:00",
        "currenciesAccepted": "USD, INR"
    })
    return block

ORG_REF = {
    "@type": "Organization",
    "@id": "https://www.nagdevproducts.com/#organization"
}

SCRIPT_RE = re.compile(
    r'(<script\s+type=["\']application/ld\+json["\'][^>]*>)(.*?)(</script>)',
    re.DOTALL | re.IGNORECASE
)

def is_org_node(node):
    if not isinstance(node, dict):
        return False
    t = node.get("@type", "")
    if isinstance(t, list):
        return any(x in ("Organization", "LocalBusiness") for x in t)
    return "Organization" in str(t) or "LocalBusiness" in str(t)

def process_html(fpath, want_full):
    try:
        html = fpath.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return f"READ_ERROR: {e}", None

    matches = list(SCRIPT_RE.finditer(html))
    if not matches:
        return "NO_SCRIPT", html

    file_changed = False
    new_html = html
    offset = 0
    org_found = False

    for m in matches:
        raw_json = m.group(2).strip()
        try:
            obj = json.loads(raw_json)
        except json.JSONDecodeError as e:
            return f"PARSE_ERROR: {e}", html

        if not isinstance(obj, dict):
            continue

        script_changed = False
        graph = obj.get("@graph")

        if graph is not None and isinstance(graph, list):
            new_graph = []
            for node in graph:
                if is_org_node(node):
                    org_found = True
                    if want_full:
                        existing_geo = node.get("geo")
                        full_block = make_full_org_block(existing_geo)
                        new_graph.append(full_block)
                    else:
                        new_graph.append(dict(ORG_REF))
                    script_changed = True
                else:
                    new_graph.append(node)
            if script_changed:
                obj["@graph"] = new_graph
        else:
            if is_org_node(obj):
                org_found = True
                if want_full:
                    existing_geo = obj.get("geo")
                    obj = make_full_org_block(existing_geo)
                else:
                    obj = dict(ORG_REF)
                script_changed = True

        if script_changed:
            new_json = json.dumps(obj, indent=2, ensure_ascii=False)
            start = m.start(2) + offset
            end = m.end(2) + offset
            new_html = new_html[:start] + new_json + new_html[end:]
            offset += len(new_json) - len(m.group(2))
            file_changed = True

    if not org_found:
        return "NO_ORG_NODE", html

    if file_changed:
        fpath.write_text(new_html, encoding="utf-8", newline="")

    return "OK_FULL" if want_full else "OK_REF", new_html

def main():
    html_files = []
    for root, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for f in files:
            if f.endswith(".html"):
                html_files.append(Path(root) / f)

    full_count = 0
    ref_count = 0
    no_org_count = 0
    errors = []

    for fpath in sorted(html_files):
        rel = fpath.relative_to(ROOT).as_posix()
        want_full = rel in FULL_PAGES

        action, _ = process_html(fpath, want_full)

        if action == "OK_FULL":
            full_count += 1
            print(f"  OK_FULL: {rel}")
        elif action == "OK_REF":
            ref_count += 1
        elif action in ("NO_SCRIPT", "NO_ORG_NODE"):
            no_org_count += 1
        else:
            errors.append((rel, action))

    print(f"\n=== SUMMARY ===")
    print(f"Full Org block applied to: {full_count} pages (expected 3)")
    print(f"Org reference applied to: {ref_count} pages (expected ~100+)")
    print(f"Pages with no Org node: {no_org_count}")
    print(f"Errors: {len(errors)}")
    for rel, err in errors:
        print(f"  {rel}: {err}")

    # Spot checks
    print("\n--- Spot-check index.html ---")
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    for m in SCRIPT_RE.finditer(html):
        try:
            obj = json.loads(m.group(2).strip())
            for node in obj.get("@graph", []):
                if isinstance(node, dict) and is_org_node(node):
                    print(f"  legalName: {node.get('legalName')}")
                    print(f"  geo: {node.get('geo')}")
                    print(f"  sameAs: {node.get('sameAs')}")
                    print(f"  keys: {list(node.keys())}")
                    break
        except: pass

    print("\n--- Spot-check products/ricinoleic-acid.html ---")
    html = (ROOT / "products" / "ricinoleic-acid.html").read_text(encoding="utf-8")
    for m in SCRIPT_RE.finditer(html):
        try:
            obj = json.loads(m.group(2).strip())
            for node in obj.get("@graph", []):
                if isinstance(node, dict) and is_org_node(node):
                    print(f"  Org node: {json.dumps(node)}")
                    break
        except: pass

    print("\n--- Spot-check castor-oil-manufacturer-gujarat.html ---")
    html = (ROOT / "castor-oil-manufacturer-gujarat.html").read_text(encoding="utf-8")
    for m in SCRIPT_RE.finditer(html):
        try:
            obj = json.loads(m.group(2).strip())
            for node in obj.get("@graph", []):
                if isinstance(node, dict) and is_org_node(node):
                    print(f"  Org node: {json.dumps(node)}")
                    break
        except: pass

if __name__ == "__main__":
    main()
