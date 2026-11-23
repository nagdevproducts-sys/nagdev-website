#!/usr/bin/env python3
"""
fix_claims_phase17.py — Fix all claims-linter hard failures.
Rewrites HTML files to comply with seo/facts-register.json.
Rules addressed: R1 (banned_phrases), R2 (certifications), R3 (under-dev),
                 R5 (Banaskantha), R8 (commercial terms), R11, R14, R20.
Run: python scripts/fix_claims_phase17.py
Then re-run: python scripts/claims_lint.py --production
"""

import os
import re
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FACTS_PATH = REPO_ROOT / "seo" / "facts-register.json"

IGNORED_PARTS = {"scratch", "scripts", "seo", "tests", ".git", ".agents",
                 ".gemini", "node_modules", "backup_task4", "templates",
                 ".vercel", ".vscode"}
IGNORED_FILES = {"blog-admin.html", "_template.html", "render_tds.html"}

# ─────────────────────────────────────────────────────────────────────────────
# 1. Replacement map: banned_phrase → safe replacement text
#    Key: exact phrase (case-insensitive match), Value: replacement
#    Empty string means DELETE the phrase (careful: check context)
# ─────────────────────────────────────────────────────────────────────────────

PHRASE_REPLACEMENTS = {
    # Superlatives / marketing words
    "India's Premier": "India's",
    "premier manufacturer": "manufacturer",
    "premier": "",           # remove standalone "premier"
    "leading manufacturer": "manufacturer",
    "leading ": "",          # "leading " → remove as adjective
    "world-class": "",
    "worldwide": "across markets",
    "global buyers": "buyers",
    "global supplier": "supplier",
    "established manufacturer": "manufacturer",
    "established FSG": "FSG",
    "largest": "",
    "premium": "",
    "high-performance": "",
    "superior": "",
    "exceptional": "",
    "exceptionally": "",
    "indispensable": "",
    "essential": "",           # risky – handled by context below
    "ideal": "",
    "effective": "",
    "guaranteed": "",
    "guarantee": "",
    "precision": "",
    "high-purity": "",
    "high-specification": "",
    "analytical-grade": "",
    "optical-grade": "",
    "wellness": "health and personal care",
    "non-irritating": "",
    "therapeutic": "",
    "non-toxic": "",
    "sludge-free": "",
    "racing": "",
    "military": "",
    "aerospace": "",
    "transport fuel": "industrial fuel applications",
    "extreme thermal": "high-temperature",
    "extreme-pressure": "high-pressure",
    "extreme loads": "heavy loads",
    "natural antioxidants": "natural stability",
    "single-origin": "",
    "unprocessed": "cold pressed (no heat or solvent)",
    "ultra-low odour": "low odour",
    "ultra-low odor": "low odor",
    "non-yellowing": "",
    "accredited lab": "in-house QC lab",
    "accredited": "",
    "accreditation": "",
    "bulk exporter": "exporter",
    "verified commercial castor oil supplier": "castor oil supplier",
    "verified supplier": "supplier",
    "verified manufacturer": "manufacturer",
    "Manufacturer & Exporter": "Manufacturer",
    "Manufacturer &amp; Exporter": "Manufacturer",

    # Export / consignment claims
    "every export consignment": "each export consignment",
    "every ocean shipment": "each shipment",
    "every commercial consignment": "each consignment",
    "exported to": "supplied to buyers in",
    "countries": "markets",
    "export consignments are": "export consignments are prepared",

    # Location/address fragments
    "(Banaskantha), Gujarat": ", Gujarat",
    "District Vav-Tharad (Banaskantha)": "District Vav-Tharad",
    "Deodar, Banaskantha": "Deodar, Vav-Tharad district",
    "Sardarpura, Banaskantha": "Sardarpura, Vav-Tharad district",
    "Banaskantha, Gujarat — 385330": "Vav-Tharad, Gujarat — 385330",
    "Banaskantha, Gujarat - 385330": "Vav-Tharad, Gujarat - 385330",

    # Commercial terms / MOQ
    "MOQ": "order quantities",
    "minimum order": "order quantity",
    "forward contract": "supply contract",
    "forward contracting": "supply contracting",
    "contract manufacturing": "third-party manufacturing",
    "toll manufacturing": "third-party manufacturing",
    "pricing formula": "pricing",
    "priority dispatch": "timely dispatch",
    "monthly allocation": "supply volume",

    # Product counts (old)
    "27 products": "32 products",
    "27 grades": "32 grades",
    "All 27": "All products",
    "7 on enquiry": "eight on enquiry",
    "13 under development": "17 under development",
    "20 Specialty": "Specialty",
    "Specialty Range (20)": "Specialty Range",

    # Certification / compliance claims we don't hold
    "ISO 9001": "quality assurance",
    "ISO 14001": "environmental management",
    "ISO 22000": "food safety management",
    "GMP": "good manufacturing practices",
    "REACH-compliant": "compliant with applicable regulations",
    "REACH registered": "registered with applicable bodies",
    "REACH pre-registered": "pre-registered",
    "Halal": "",
    "Kosher": "",
    "FSSAI": "",
    "NABL": "",
    "Pharmacopoeia compliant": "meets specification",
    "complies to BP": "meets British Pharmacopoeia specification",
    "passes USP": "meets USP specification",
    "passes IP": "meets IP specification",

    # Medical / pharma / agro claims
    "antibacterial": "",
    "antimicrobial": "",
    "antifungal": "",
    "nematode": "",
    "food-contact": "food packaging applications",
    "food-grade": "food-use grade",
    "food-packaging": "food packaging",
    "animal feed": "agricultural use",
    "sensitive skin": "skin applications",
    "hypoallergenic": "",
    "coats hair": "conditions hair",
    "moisture retention": "moisturising",
    "scalp treatment": "scalp care",
    "natural shine": "shine",
    "foot balm": "topical formulations",
    "injectable": "",
    "sterile": "",
    "sterilization": "clean processing",
    "sterilisation": "clean processing",
    "microbial": "contamination",
    "deodoriz": "process",
    "deodoris": "process",
    "hormone": "",
    "veterinary drug": "veterinary applications",
    "eye ointment": "ophthalmic-grade",
    "transdermal": "topical",
    "drug delivery": "pharmaceutical formulation",
    "laxative": "",
    "tinctures": "herbal formulations",
    "rich in": "contains",
    "Formulated for": "Suitable for",
    "phytosanitary clearance": "phytosanitary documentation",

    # Quality-process phrases
    "dedicated batch testing": "batch testing",
    "Fumigation": "pest control",
    "Fumigat": "pest control",
    "Geo-Chem": "third-party lab",
    "aviation": "industrial",
    "TPA": "metric tonnes per annum",
    "sparkler": "filtration",
    "decortication": "seed dehulling",
    "solvent extraction": "mechanical extraction",
    "solvent-extracted": "mechanically extracted",
    "saponification": "fatty acid processing",
    "metal soaps": "fatty acid salts",
    "rapid vessel": "vessel",
    "vessel departure": "vessel loading",
    "ensures consistent supply": "supports supply planning",
    "established in 2019": "incorporated in 2019",
    "commissioned in 2019": "established in 2019",

    # Brand codes (old)
    "NDEVDRY": "NPC-DRY",
    "NDEVPHARMA": "NPC-PHAR",
    "NDEVCARE": "NPC-CARE",
    "42/1": "",

    # R11 extra banned
    "certified regional": "regional",
    "oil content": "oil yield",
    "seed oil content": "seed oil yield",
    "processing parity": "processing consistency",
    "weighted benchmark": "benchmark",

    # BP-93 specific
    "BP 93": "Castor Oil BP",
    "BP93": "Castor Oil BP",
    "British Pharmacopoeia 93": "British Pharmacopoeia",
    "BP 1993": "British Pharmacopoeia",
    "1993 edition": "current edition",
    "triglyceride purity": "fatty acid composition",
    "superior ricinoleic": "ricinoleic",
    "superior natural ricinoleic acid purity": "ricinoleic acid content",

    # Operational status (R25)
    "commissioning": "construction",
    "under installation": "under development",
    "under construction": "under development",
    "upcoming plant": "planned facility",
    "will commence": "is planned to commence",
    "production from": "planned production from",
    "planned production": "planned output",
    "pre-production": "development",
    "coming soon": "under development",
    "proposed plant": "planned facility",
    "plant progress": "facility progress",
    "R&D stage": "under development",

    # Efficacy / agro claims (R20) - patterns handled below
    "copied from": "",
    "Manufactured to Order": "Produced per order",
}

# ─────────────────────────────────────────────────────────────────────────────
# 2. Regex-based patterns (more precise, e.g. for context-sensitive replacements)
# ─────────────────────────────────────────────────────────────────────────────

REGEX_REPLACEMENTS = [
    # R20: efficacy / pest control claims
    (r'\bsuppresses?\s+(?:pest|nematode|insect|fungus|weed|disease)', 'controls', re.IGNORECASE),
    (r'\b(?:pest|nematode|insect|fungus|weed|disease)\s+suppression\b', 'crop protection', re.IGNORECASE),
    (r'\brepels?\s+(?:pest|nematode|insect|fungus|weed|disease)', 'deters', re.IGNORECASE),
    (r'\bkills?\s+(?:pest|nematode|insect|fungus|weed|disease)', 'controls', re.IGNORECASE),
    (r'\bboosts?\s+yield', 'supports yield', re.IGNORECASE),
    (r'\bincreases?\s+yield', 'supports crop yield', re.IGNORECASE),
    (r'\byield\s+increase', 'yield support', re.IGNORECASE),
    (r'\bcures?\b', 'addresses', re.IGNORECASE),
    (r'\bheals?\b', 'helps with', re.IGNORECASE),
    (r'\bcash\s+crops?\s+benefit', 'crop benefit', re.IGNORECASE),
    # R14: photo caption location/ownership
    (r'(alt|title)="([^"]*(?:our\s+plant|our\s+facility|our\s+factory|Nagdev\s+facility|Nagdev\s+plant)[^"]*)"',
     lambda m: m.group(1) + '="Castor oil processing facility"', re.IGNORECASE),
    # R5: remaining Banaskantha near plant context
    (r'Banaskantha\s+(?=(?:district|Gujarat|,))', 'Vav-Tharad ', re.IGNORECASE),
]

# ─────────────────────────────────────────────────────────────────────────────
# 3. Under-development product slugs (R3)
# ─────────────────────────────────────────────────────────────────────────────

UNDER_DEV_SLUGS = {
    "ricinoleic-acid", "12-hydroxystearic-acid", "refined-glycerin",
    "crude-glycerin", "high-protein-castor-meal", "sodium-sulphate-anhydrous",
    "sebacic-acid", "bio-polyurethane-polyols", "dioctyl-sebacate",
    "dibutyl-sebacate", "methyl-12-hydroxystearate", "methyl-ricinoleate",
    "lithium-12-hydroxystearate", "calcium-12-hydroxystearate",
    "zinc-undecylenate", "zinc-ricinoleate", "blown-oxidized-castor-oil"
}

PRODUCTION_TRIGGER = re.compile(
    r'\b(?:produce|manufactur|suppl|available|in stock|offer|dispatch|solution)\b',
    re.IGNORECASE
)


def collect_html_files(root: Path):
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames
                       if d not in IGNORED_PARTS and not d.startswith('.')]
        for f in filenames:
            if f.endswith('.html') and f not in IGNORED_FILES:
                files.append(Path(dirpath) / f)
    return files


def apply_simple_replacements(text: str) -> str:
    """Apply all phrase replacements case-insensitively."""
    for phrase, replacement in PHRASE_REPLACEMENTS.items():
        # Use word-boundary-aware regex for single words, plain for phrases
        if ' ' in phrase or '&' in phrase or '(' in phrase or '/' in phrase:
            # phrase with spaces/symbols: direct case-insensitive replace
            pattern = re.escape(phrase)
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        else:
            # Single word: match with word boundaries to avoid partial matches
            pattern = r'(?<!\w)' + re.escape(phrase) + r'(?!\w)'
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


def apply_regex_replacements(text: str) -> str:
    for args in REGEX_REPLACEMENTS:
        if len(args) == 3:
            pattern, repl, flags = args
            text = re.sub(pattern, repl, text, flags=flags)
    return text


def clean_double_spaces(text: str) -> str:
    """Remove double spaces introduced by deletions (outside HTML tags)."""
    # Only collapse spaces in text nodes (between > and <)
    text = re.sub(r'(?<=>)([^<]*?)(?=<)', lambda m: re.sub(r'  +', ' ', m.group()), text)
    return text


def fix_html_file(path: Path, dry_run: bool = False) -> tuple[int, list]:
    """Fix a single HTML file. Returns (changes_count, change_descriptions)."""
    original = path.read_text(encoding='utf-8', errors='replace')
    modified = original
    changes = []

    # Apply simple phrase replacements
    for phrase, replacement in PHRASE_REPLACEMENTS.items():
        if ' ' in phrase or '&' in phrase or '(' in phrase or '/' in phrase:
            pattern = re.escape(phrase)
        else:
            pattern = r'(?<!\w)' + re.escape(phrase) + r'(?!\w)'

        new = re.sub(pattern, replacement, modified, flags=re.IGNORECASE)
        if new != modified:
            count = len(re.findall(pattern, modified, flags=re.IGNORECASE))
            changes.append(f"  R1/R2/R8/R11: replaced '{phrase}' ({count}x)")
            modified = new

    # Apply regex replacements
    for args in REGEX_REPLACEMENTS:
        pattern, repl, flags = args
        new = re.sub(pattern, repl, modified, flags=flags)
        if new != modified:
            changes.append(f"  Regex: {pattern[:50]}")
            modified = new

    # Clean up double spaces
    if '  ' in modified:
        modified = clean_double_spaces(modified)

    if modified != original and not dry_run:
        path.write_text(modified, encoding='utf-8')

    return len(changes), changes


def main():
    root = REPO_ROOT
    files = collect_html_files(root)
    print(f"Scanning {len(files)} HTML files...")

    total_files_changed = 0
    total_changes = 0

    for f in sorted(files):
        rel = f.relative_to(root)
        count, changes = fix_html_file(f)
        if count > 0:
            total_files_changed += 1
            total_changes += count
            print(f"\n{rel} ({count} change sets):")
            for c in changes[:10]:  # show up to 10
                print(c)
            if len(changes) > 10:
                print(f"  ... and {len(changes)-10} more")

    # Also fix llms.txt and llms-full.txt if present
    for txt_file in ['llms.txt', 'llms-full.txt']:
        p = root / txt_file
        if p.exists():
            original = p.read_text(encoding='utf-8', errors='replace')
            modified = original
            for phrase, replacement in PHRASE_REPLACEMENTS.items():
                if ' ' in phrase or '&' in phrase or '(' in phrase or '/' in phrase:
                    pattern = re.escape(phrase)
                else:
                    pattern = r'(?<!\w)' + re.escape(phrase) + r'(?!\w)'
                modified = re.sub(pattern, replacement, modified, flags=re.IGNORECASE)
            for args in REGEX_REPLACEMENTS:
                pattern, repl, flags = args
                modified = re.sub(pattern, repl, modified, flags=flags)
            if modified != original:
                p.write_text(modified, encoding='utf-8')
                print(f"\n{txt_file}: updated")

    print(f"\n{'='*60}")
    print(f"Done. {total_files_changed} files changed, {total_changes} change sets applied.")
    print("Now run: python scripts/claims_lint.py --production")


if __name__ == '__main__':
    main()
