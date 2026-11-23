"""
Phase 18 — Task B: Fix mpn field.

The test requires mpn = HS code currently. We need to:
1. Update test to check mpn = brand_code
2. Update all 32 product page JSON-LD: mpn -> brand_code
3. Keep HS code only in additionalProperty (already there)
4. Update scripts/add_mpn_to_underdev.py
"""
import json, re
from pathlib import Path

REPO = Path('.')

# Load product master for brand codes
master = json.loads((REPO / 'seo' / 'product-master.json').read_text(encoding='utf-8'))
brand_codes = {p['slug']: p['brand_code'] for p in master if p.get('brand_code')}

print(f"Loaded {len(brand_codes)} brand codes from product-master.json")

# ── 1. Update all 32 product HTML pages ─────────────────────────────────────
products_dir = REPO / 'products'
updated_pages = []
failed_pages = []

for slug, brand_code in brand_codes.items():
    html_path = products_dir / f'{slug}.html'
    if not html_path.exists():
        print(f"[SKIP] {slug}.html not found")
        continue

    t = html_path.read_text(encoding='utf-8')

    # Pattern: "mpn": "1515.30" or similar HS code — replace with brand_code
    # Must match the existing JSON-LD mpn field
    new_mpn_line = f'"mpn": "{brand_code}"'
    mpn_pattern = re.compile(r'"mpn"\s*:\s*"[^"]+"')

    if mpn_pattern.search(t):
        new_t = mpn_pattern.sub(new_mpn_line, t, count=1)
        html_path.write_text(new_t, encoding='utf-8', newline='\r\n')
        m = re.search(r'"mpn"\s*:\s*"([^"]+)"', new_t)
        updated_pages.append(slug)
        print(f"[OK] {slug}: mpn -> '{brand_code}'")
    else:
        # mpn not present — add it after "sku" field in JSON-LD
        # Find Product JSON-LD and add mpn after sku
        sku_pattern = re.compile(r'("sku"\s*:\s*"[^"]+")(\s*,?\s*\n)')
        if sku_pattern.search(t):
            new_t = sku_pattern.sub(
                lambda m: m.group(1) + ',\n      ' + new_mpn_line + m.group(2)[1:],
                t, count=1
            )
            html_path.write_text(new_t, encoding='utf-8', newline='\r\n')
            updated_pages.append(slug)
            print(f"[OK] {slug}: added mpn '{brand_code}' after sku")
        else:
            failed_pages.append(slug)
            print(f"[WARN] {slug}: could not find mpn or sku field to update")

print(f"\nUpdated: {len(updated_pages)} pages")
if failed_pages:
    print(f"Failed: {failed_pages}")

# ── 2. Update the test file ──────────────────────────────────────────────────
test_path = REPO / 'tests' / 'test_hs_and_spec_consistency.py'
test = test_path.read_text(encoding='utf-8')

# Build EXPECTED_BRAND_CODES dict as a string to insert
brand_dict_lines = ["EXPECTED_BRAND_CODES = {"]
for slug, brand in brand_codes.items():
    brand_dict_lines.append(f"    '{slug}': '{brand}',")
brand_dict_lines.append("}")
brand_dict_str = "\n".join(brand_dict_lines)

# Add EXPECTED_BRAND_CODES after EXPECTED_CANONICAL_HS dict
if 'EXPECTED_BRAND_CODES' not in test:
    # Insert after the closing } of EXPECTED_CANONICAL_HS
    insert_after = "}\n\n@pytest.fixture"
    if insert_after in test:
        test = test.replace(insert_after, f"}}\n\n{brand_dict_str}\n\n@pytest.fixture", 1)
        print("[OK] Added EXPECTED_BRAND_CODES to test file")
    else:
        print("[WARN] Could not find insertion point for EXPECTED_BRAND_CODES")
else:
    print("[SKIP] EXPECTED_BRAND_CODES already in test file")

# Update test_active_15_products_hs_code_consistency to check mpn == brand_code
OLD_MPN_CHECK_ACTIVE = '''        m_mpn = re.search(r\'\"mpn\"\\s*:\\s*\"([^\"]+)\"\', html_text)
        assert m_mpn is not None, f"Missing JSON-LD mpn in {slug}.html"
        assert m_mpn.group(1) == expected_hs, f"JSON-LD mpn mismatch in {slug}.html: {m_mpn.group(1)} != {expected_hs}"'''

NEW_MPN_CHECK_ACTIVE = '''        m_mpn = re.search(r\'\"mpn\"\\s*:\\s*\"([^\"]+)\"\', html_text)
        assert m_mpn is not None, f"Missing JSON-LD mpn in {slug}.html"
        expected_mpn = EXPECTED_BRAND_CODES.get(slug, "")
        assert m_mpn.group(1) == expected_mpn, f"JSON-LD mpn mismatch in {slug}.html: {m_mpn.group(1)!r} != {expected_mpn!r} (mpn must be brand_code, not HS code)"'''

if OLD_MPN_CHECK_ACTIVE in test:
    test = test.replace(OLD_MPN_CHECK_ACTIVE, NEW_MPN_CHECK_ACTIVE, 1)
    print("[OK] Updated active products mpn check to use brand_code")
else:
    print("[WARN] Active products mpn check not found exactly")

# Update test_planned_17_products_hs_code_consistency to check mpn == brand_code
OLD_MPN_CHECK_PLANNED = '''        m_mpn = re.search(r\'\"mpn\"\\s*:\\s*\"([^\"]+)\"\', html_text)
        assert m_mpn is not None and m_mpn.group(1) == expected_hs'''

NEW_MPN_CHECK_PLANNED = '''        m_mpn = re.search(r\'\"mpn\"\\s*:\\s*\"([^\"]+)\"\', html_text)
        expected_brand = EXPECTED_BRAND_CODES.get(slug, "")
        assert m_mpn is not None and m_mpn.group(1) == expected_brand, (
            f"mpn for {slug} should be brand_code {expected_brand!r}, got {m_mpn.group(1) if m_mpn else None!r}"
        )'''

if OLD_MPN_CHECK_PLANNED in test:
    test = test.replace(OLD_MPN_CHECK_PLANNED, NEW_MPN_CHECK_PLANNED, 1)
    print("[OK] Updated planned products mpn check to use brand_code")
else:
    print("[WARN] Planned products mpn check not found exactly")

test_path.write_text(test, encoding='utf-8', newline='\r\n')
print("[OK] Test file saved")

# ── 3. Update scripts/add_mpn_to_underdev.py ────────────────────────────────
script_path = REPO / 'scripts' / 'add_mpn_to_underdev.py'
new_script = '''"""
Phase 18 revised: Set mpn = brand_code (manufacturer part number) for all product pages.
HS codes stay in additionalProperty only.
Run: python scripts/add_mpn_to_underdev.py
"""
import json, re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
master = json.loads((REPO / "seo" / "product-master.json").read_text(encoding="utf-8"))
brand_codes = {p["slug"]: p["brand_code"] for p in master if p.get("brand_code")}

products_dir = REPO / "products"
updated = 0
for slug, brand_code in brand_codes.items():
    html_path = products_dir / f"{slug}.html"
    if not html_path.exists():
        continue
    t = html_path.read_text(encoding="utf-8")
    new_mpn = f\'"mpn": "{brand_code}"\\'
    pat = re.compile(r\'"mpn"\\s*:\\s*"[^"]+"\\')
    if pat.search(t):
        new_t = pat.sub(new_mpn, t, count=1)
        if new_t != t:
            html_path.write_text(new_t, encoding="utf-8", newline="\\r\\n")
            updated += 1
            print(f"[OK] {slug}: mpn = {brand_code}")
    else:
        print(f"[WARN] {slug}: no mpn field found")

print(f"Done. Updated {updated} pages.")
'''
script_path.write_text(new_script, encoding='utf-8', newline='\r\n')
print("[OK] scripts/add_mpn_to_underdev.py updated")
print("\nTask B complete.")
