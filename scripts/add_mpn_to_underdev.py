"""
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
    new_mpn = f'"mpn": "{brand_code}"\'
    pat = re.compile(r'"mpn"\s*:\s*"[^"]+"\')
    if pat.search(t):
        new_t = pat.sub(new_mpn, t, count=1)
        if new_t != t:
            html_path.write_text(new_t, encoding="utf-8", newline="\r\n")
            updated += 1
            print(f"[OK] {slug}: mpn = {brand_code}")
    else:
        print(f"[WARN] {slug}: no mpn field found")

print(f"Done. Updated {updated} pages.")
