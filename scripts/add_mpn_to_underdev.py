#!/usr/bin/env python3
"""Add 'mpn' field to under-development product JSON-LD schemas."""
import re
from pathlib import Path

HS_MAP = {
    'ricinoleic-acid': '2918.19',
    '12-hydroxystearic-acid': '2918.19',
    'sebacic-acid': '2917.13',
    'high-protein-castor-meal': '2306.90',
    'crude-glycerin': '1520.00',
    'refined-glycerin': '2905.45',
    'bio-polyurethane-polyols': '3907.29',
    'sodium-sulphate-anhydrous': '2833.11',
    'dioctyl-sebacate': '2917.13',
    'dibutyl-sebacate': '2917.13',
    'methyl-12-hydroxystearate': '2918.19',
    'methyl-ricinoleate': '2918.19',
    'lithium-12-hydroxystearate': '2918.19',
    'calcium-12-hydroxystearate': '2918.19',
    'zinc-undecylenate': '2918.19',
    'zinc-ricinoleate': '2918.19',
    'blown-oxidized-castor-oil': '1518.00',
}

prod_dir = Path(__file__).resolve().parent.parent / 'products'
fixed = []
failed = []

for slug, hs in HS_MAP.items():
    p = prod_dir / f'{slug}.html'
    if not p.exists():
        failed.append(f'{slug}: FILE NOT FOUND')
        continue
    text = p.read_text(encoding='utf-8')

    # Check if mpn already exists
    if '"mpn"' in text:
        print(f'{slug}: mpn already present')
        continue

    # Insert after "sku": "..." in JSON-LD
    new_text = re.sub(
        r'("sku"\s*:\s*"[^"]+")(\s*[,\n])',
        lambda m: m.group(1) + ',\n        "mpn": "' + hs + '"' + m.group(2),
        text,
        count=1
    )
    if new_text == text:
        # Fallback: insert before "name" in Product block
        new_text = re.sub(
            r'("@type"\s*:\s*"Product"\s*,\s*)',
            r'\1"mpn": "' + hs + '",\n        ',
            text,
            count=1
        )

    if new_text != text:
        p.write_text(new_text, encoding='utf-8')
        fixed.append(slug)
        print(f'{slug}: FIXED (HS {hs})')
    else:
        failed.append(f'{slug}: could not find insertion point')
        print(f'{slug}: FAILED to insert')

print(f'\nFixed {len(fixed)} pages')
if failed:
    print(f'Failed: {failed}')
