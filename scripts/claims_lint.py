#!/usr/bin/env python3
"""
claims_lint.py - Single source-of-truth claims linter and gate for nagdevproducts.com.
Scans deployable HTML files, llms.txt, llms-full.txt, sitemap.xml, and JSON-LD schemas
against seo/facts-register.json.

Enforces rules:
R1: banned_phrases (case-insensitive, whole-site: HTML text, meta, JSON-LD, llms*.txt) -> FAIL
R2: any certification name not in certifications_held (ISO, GMP, REACH, Halal, Kosher, FSSAI, BIS licence, NABL, etc.) -> FAIL
R3: under-development product in a sentence with produce/manufacture/supply/available/in stock/offer/dispatch/solution -> FAIL unless sentence contains "under development"
R4: product counts must be 27 / 7 / 7 / 13; any other count next to products/grades -> FAIL
R5: plant address/district must match register; "Banaskantha" next to Deodar, Sardarpura, 385330 or "district" -> FAIL
    ("Banaskantha" allowed ONLY inside exact region_context or in farmer/seed-sourcing context, never as plant's district)
R6: capacity: any TPD/TPA/MT per day value other than "50 TPD" seed crushing -> FAIL
R7: SPEC CONSISTENCY (per product page): parse page's spec table (parameter -> limit).
    Every mention of parameter in key-facts, intro, FAQ, meta, JSON-LD additionalProperty and TDS text must match number & unit.
    A different colour scale (Gardner vs Lovibond) not present in table -> FAIL.
R8: commercial terms: MOQ, lead time, delivery days, price, payment terms, monthly allocation -> FAIL unless in register
R9: percentages/numbers in prose that are not spec values and have no <a href> source in the same paragraph -> WARN
R10: Any table whose caption, heading or nearby text cites a data source (Agmarknet, SEA, DGCIS, government, "official") must have a matching raw data file in seo/data/<source>/<YYYY-MM-DD>/ and a generator script in scripts/ that reproduces the table exactly -> FAIL
R11: Banned additions to the register's banned_phrases: "certified regional", "oil content", "seed oil content", "processing parity", "weighted benchmark" -> FAIL
R12: Any page claiming data for a period that ends after its own publish date -> FAIL
R13: Every deployable HTML page must contain the standard site header, the footer, the consent snippet, gtag loader and /js/analytics.js (compare against index.html) -> FAIL
"""

import sys
import os
import re
import json
import csv
import datetime
from pathlib import Path
from bs4 import BeautifulSoup

# Ensure UTF-8 output
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

REPO_ROOT = Path(__file__).resolve().parent.parent

def load_facts(facts_path: Path = None):
    if facts_path is None:
        facts_path = REPO_ROOT / "seo" / "facts-register.json"
    if not facts_path.exists():
        raise FileNotFoundError(f"Facts register not found at {facts_path}")
    with open(facts_path, "r", encoding="utf-8") as f:
        return json.load(f)

# Linter Rule Definitions (Single Source of Truth)
RULES = {
    "R1": "banned_phrases (case-insensitive, whole-site: HTML text, meta, JSON-LD, llms*.txt)",
    "R2": "any certification name not in certifications_held (ISO, GMP, REACH, Halal, Kosher, FSSAI, BIS licence, NABL, etc.)",
    "R3": "under-development product in a sentence with produce/manufacture/supply/available/in stock/offer/dispatch/solution unless marked 'under development'",
    "R4": "product counts must match facts register (32 total, 7 regular, 8 enquiry, 17 under dev)",
    "R5": "plant address/district must match register; 'Banaskantha' next to Deodar, Sardarpura, 385330 or 'district' forbidden",
    "R6": "capacity: any TPD/TPA/MT per day value other than '50 TPD' seed crushing",
    "R7": "SPEC CONSISTENCY: spec table limits must match across key-facts, intro, FAQ, meta, JSON-LD and TDS text",
    "R8": "commercial terms: MOQ, lead time, delivery days, price, payment terms, monthly allocation unless in register",
    "R9": "percentages/numbers in prose that are not spec values and have no reference link in paragraph (WARN)",
    "R10": "Any table citing a data source (Agmarknet, SEA, DGCIS, official) must have matching raw data file and generator script",
    "R11": "Banned additions to register's banned phrases (certified regional, oil content, processing parity, etc.)",
    "R12": "Any page claiming data for a period that ends after its own publish date",
    "R13": "Required standard site template components (header, footer, consent snippet, gtag loader, /js/analytics.js)",
    "R14": "Crop and video media captions/alts must not contain location/ownership/facility claims and video must include 'illustrative'",
    "R15": "Cross-page specification consistency against canonical product pages",
    "R16": "Pharmacopoeia and cosmetic grade pages must contain NO numeric specification values and NO certification/regulatory claims",
    "R17": "PAGE IDENTITY: on each /products/<slug> page, H1, breadcrumb last item, hero img alt, H2/H3, meta title/description, FAQ questions must refer ONLY to that page's product. Cross-product contamination -> FAIL (related-products block exempt)",
    "R18": "INTERNAL LINKS: all internal links must resolve to valid local files and contain no malformed percent encodings",
    "R19": "BRAND CODES: brand codes must strictly match canonical codes from seo/product-master.json; no legacy NDEV- hyphens or 'Specialty Range'",
    "R20": "EFFICACY & AGRONOMIC/HEALTH CLAIMS: no efficacy claims (pest/nematode/insect/fungus/weed/disease within 6 words of suppress/repel/control/kill/prevent/protect/resist), phytosanitary, cash crops benefit, yield increase, boosts yield, cures, heals"
}

# Ignored paths
IGNORED_PARTS = {"scratch", "scripts", "seo", "tests", ".git", ".agents", ".gemini", "node_modules", "backup_task4"}
IGNORED_FILES = {"blog-admin.html", "_template.html", "render_tds.html"}

def is_deployable(path: Path) -> bool:
    for part in path.parts:
        if part in IGNORED_PARTS:
            return False
    if path.name in IGNORED_FILES:
        return False
    if path.suffix in [".html", ".txt", ".xml", ".json"]:
        return True
    return False

def collect_files(root: Path = None):
    if root is None:
        root = REPO_ROOT
    deployable = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORED_PARTS and not d.startswith('.')]
        for f in filenames:
            p = Path(dirpath) / f
            if is_deployable(p):
                if p.suffix == ".html" or p.name in ["llms.txt", "llms-full.txt", "sitemap.xml"]:
                    deployable.append(p)
    return sorted(deployable)

def strip_tags(text: str) -> str:
    # Remove script and style tags completely
    clean = re.sub(r'<(script|style)\b[^>]*>.*?</\1>', ' ', text, flags=re.DOTALL | re.IGNORECASE)
    # Remove HTML comments
    clean = re.sub(r'<!--.*?-->', ' ', clean, flags=re.DOTALL)
    # Replace closing tags and newlines with periods so sentences don't merge across elements or lines
    clean = re.sub(r'</[a-zA-Z0-9:_-]+>', '. ', clean)
    clean = re.sub(r'[\r\n]+', '. ', clean)
    # Remove remaining HTML/XML tags
    clean = re.sub(r'<[^>]+>', ' ', clean)
    clean = re.sub(r'\s+', ' ', clean)
    return clean

def split_into_sentences(text: str):
    # Split text into distinct sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)
    cleaned = []
    for s in sentences:
        s_str = s.strip()
        if len(s_str) > 5:
            cleaned.append(s_str)
    return cleaned

DEV_PRODUCT_REGEXES = [
    r"\bricinoleic\s+acid\b",
    r"\b12[- ]hydroxystearic\s+acid\b",
    r"\b12[- ]hsa\b",
    r"\brefined\s+glycerin\b",
    r"\brefined\s+glycerine\b",
    r"\bcrude\s+glycerin\b",
    r"\bcrude\s+glycerine\b",
    r"\bhigh[- ]protein\s+castor\s+meal\b",
    r"\bcastor\s+meal\b",
    r"\bsodium\s+sulphate\s+anhydrous\b",
    r"\bsodium\s+sulfate\s+anhydrous\b",
    r"\bsodium\s+sulphate\b",
    r"\bsodium\s+sulfate\b",
    r"\bsebacic\s+acid\b",
    r"\bbio[- ]polyurethane\s+polyols?\b",
    r"\bbio[- ]pu\s+polyols?\b",
    r"\bdioctyl\s+sebacate\b",
    r"\bdos\b",
    r"\bdibutyl\s+sebacate\b",
    r"\bdbs\b",
    r"\bmethyl\s+12[- ]hydroxystearate\b",
    r"\bmethyl\s+ricinoleate\b",
    r"\blithium\s+12[- ]hydroxystearate\b",
    r"\bcalcium\s+12[- ]hydroxystearate\b",
    r"\bzinc\s+undecylenate\b",
    r"\bzinc\s+ricinoleate\b",
    r"\bblown\s+oxidized\s+castor\s+oil\b",
    r"\bblown\s+oxidised\s+castor\s+oil\b",
    r"\bblown\s+castor\s+oil\b"
]

DEV_PROD_RE = re.compile("|".join(DEV_PRODUCT_REGEXES), re.IGNORECASE)
R3_TRIGGER_RE = re.compile(r"\b(produce|produces|produced|producing|manufacture|manufactures|manufactured|manufacturing|supply|supplies|supplied|supplying|available|in stock|offer|offers|offered|offering|dispatch|dispatches|dispatched|dispatching|solution|solutions|regular|regularly)\b", re.IGNORECASE)

CERT_PATTERNS = [
    (r"\bISO\s*[-]?\s*(?:9001|14001|22000|\d{4,5})\b", "ISO"),
    (r"\bISO\s+certified\b", "ISO certified"),
    (r"\bGMP\b", "GMP"),
    (r"\bREACH\b", "REACH"),
    (r"\bHalal\b", "Halal"),
    (r"\bKosher\b", "Kosher"),
    (r"\bFSSAI\b", "FSSAI"),
    (r"\bBIS\s+(?:licen[sc]e|certified)\b", "BIS licence"),
    (r"\bNABL\b", "NABL")
]

COMMERCIAL_TERMS_RE = re.compile(
    r"\b(MOQ|minimum\s+order\s+quantity|minimum\s+order|lead\s+time|delivery\s+days|payment\s+terms|monthly\s+allocation|pricing\s+formula)\b",
    re.IGNORECASE
)

def parse_spec_table(html_content: str):
    """
    Parses analytical parameters from spec-table-section or table with TEST PARAMETER / SR NO.
    Returns dict mapping parameter key -> parsed value details.
    """
    # Specifically target the analytical table in spec-table-section or containing TEST PARAMETER
    table_match = re.search(r'<section[^>]*class=["\'][^"\']*spec-table-section[^"\']*["\'][^>]*>.*?<table[^>]*>(.*?)</table>', html_content, re.DOTALL | re.IGNORECASE)
    if not table_match:
        tables = re.findall(r'<table[^>]*>(.*?)</table>', html_content, re.DOTALL | re.IGNORECASE)
        for t in tables:
            if "TEST PARAMETER" in t.upper() and ("SPECIFICATIONS" in t.upper() or "SR NO" in t.upper()):
                table_match = re.search(r'(.*)', t, re.DOTALL)
                break
    
    if not table_match:
        return {}

    table_html = table_match.group(1)
    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table_html, re.DOTALL | re.IGNORECASE)
    specs = {
        "color_scale": set(),
        "params": {}
    }

    for row in rows:
        cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL | re.IGNORECASE)
        if len(cells) < 2:
            continue
        param_cell = cells[1] if len(cells) >= 3 else cells[0]
        val_cell = cells[2] if len(cells) >= 3 else cells[1]
        
        param_text = re.sub(r'<[^>]+>', ' ', param_cell).strip().lower()
        val_text = re.sub(r'<[^>]+>', ' ', val_cell).strip()
        val_clean = val_text.replace('&le;', '≤').replace('&ge;', '≥').replace('&deg;', '°').strip()

        # Track color scale in table
        if "lovibond" in param_text or "lovibond" in val_clean.lower():
            specs["color_scale"].add("lovibond")
        if "gardner" in param_text or "gardner" in val_clean.lower():
            specs["color_scale"].add("gardner")

        # Map parameters
        if "free fatty acid" in param_text or param_text == "ffa" or "(ffa)" in param_text:
            specs["params"]["ffa"] = val_clean
        elif "acid value" in param_text:
            specs["params"]["acid_value"] = val_clean
        elif "hydroxyl" in param_text:
            specs["params"]["hydroxyl"] = val_clean
        elif "iodine" in param_text:
            specs["params"]["iodine"] = val_clean
        elif "saponification" in param_text:
            specs["params"]["saponification"] = val_clean
        elif "ricinoleic" in param_text:
            specs["params"]["ricinoleic"] = val_clean
        elif "moisture" in param_text:
            specs["params"]["moisture"] = val_clean
        elif "melting point" in param_text:
            specs["params"]["melting_point"] = val_clean
        elif "purity" in param_text or "assay" in param_text:
            specs["params"]["purity"] = val_clean

    return specs

def extract_numeric_val(text: str):
    m = re.search(r'(\d+(?:\.\d+)?)', text)
    return float(m.group(1)) if m else None

R11_BANNED_PHRASES = [
    "certified regional",
    "oil content",
    "seed oil content",
    "processing parity",
    "weighted benchmark",
    "triglyceride purity",
    "injectable",
    "sterile",
    "sterilization",
    "sterilisation",
    "microbial",
    "deodoriz",
    "deodoris",
    "hormone",
    "veterinary drug",
    "eye ointment",
    "transdermal",
    "drug delivery",
    "laxative",
    "nematode",
    "non-yellowing",
    "ultra-low odour",
    "ultra-low odor",
    "dedicated batch testing",
    "British Pharmacopoeia 93",
    "solvent extraction",
    "solvent-extracted",
    "saponification",
    "copied from",
    "metal soaps",
    "Fumigat"
]

def get_banned_phrase_pattern(phrase: str) -> str:
    phrase_lower = phrase.strip().lower()
    if phrase_lower in ("deodoriz", "deodoris"):
        return r'(?<!\w)' + re.escape(phrase_lower)
    elif phrase_lower == "fumigat":
        return r'(?<![a-zA-Z])fumigat[a-zA-Z]*'
    elif phrase_lower == "saponification":
        return r'(?<![a-zA-Z])saponif[a-zA-Z]*(?!(?:[\s\-_]+value))(?![a-zA-Z])'
    elif phrase_lower in ("solvent extraction", "solvent-extracted"):
        return r'(?<![a-zA-Z])solvent[\s\-]extract(?:ion|ed)\b'
    elif phrase_lower == "metal soaps":
        return r'(?<![a-zA-Z])metal(?:lic)?\s+soaps?(?![a-zA-Z])'
    elif phrase_lower == "copied from":
        return r'(?<![a-zA-Z])copied\s+from\b'
    elif phrase_lower in ("injectable", "sterile", "hormone", "transdermal", "laxative", "nematode", "eye ointment"):
        return r'(?<!\w)' + re.escape(phrase_lower) + r'(?:s)?(?!\w)'
    elif phrase_lower in ("bp 93", "british pharmacopoeia 93"):
        return r'(?<!castor-oil-)(?<!\w)(?:BP[\s\-]+93|British\s+Pharmacopoeia\s*(?:19)?93)(?!\w)'
    else:
        words = phrase.strip().split()
        flex = r'\s+'.join(re.escape(w) for w in words)
        return r'(?<!\w)' + flex + r'(?!\w)'

MONTH_MAP = {
    "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
    "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7,
    "august": 8, "aug": 8, "september": 9, "sep": 9, "october": 10, "oct": 10,
    "november": 11, "nov": 11, "december": 12, "dec": 12
}

def parse_date_str(s: str):
    if not s:
        return None
    s = s.strip()
    m = re.match(r'^(\d{4})-(\d{1,2})-(\d{1,2})', s)
    if m:
        try:
            return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass
    m = re.match(r'^(\d{1,2})\s+([a-zA-Z]+)\s+(\d{4})', s)
    if m and m.group(2).lower() in MONTH_MAP:
        try:
            return datetime.date(int(m.group(3)), MONTH_MAP[m.group(2).lower()], int(m.group(1)))
        except ValueError:
            pass
    m = re.match(r'^([a-zA-Z]+)\s+(\d{1,2}),?\s+(\d{4})', s)
    if m and m.group(1).lower() in MONTH_MAP:
        try:
            return datetime.date(int(m.group(3)), MONTH_MAP[m.group(1).lower()], int(m.group(2)))
        except ValueError:
            pass
    return None

def check_r10_table_sources(content: str, file_path_str: str, repo_root: Path = REPO_ROOT):
    findings = []
    if not (file_path_str.endswith(".html") or "<table" in content.lower()):
        return findings

    table_pattern = re.compile(r'<table\b[^>]*>(.*?)</table>', re.DOTALL | re.IGNORECASE)
    tables = list(table_pattern.finditer(content))
    if not tables:
        return findings

    data_sources = [
        ("agmarknet", r'\bagmarknet(?:\.gov\.in)?\b'),
        ("sea", r'\b(?:SEA|Solvent\s+Extractors[\'’]?\s+Association)\b'),
        ("dgcis", r'\b(?:DGCIS|DGCI&S|Directorate\s+General\s+of\s+Commercial\s+Intelligence)\b'),
        ("government", r'\b(?:government|govt|ministry\s+of\s+agriculture)\b'),
        ("official", r'\b(?:official\s+(?:data|figures?|statistics?|reports?|rates?|prices?|benchmark|source))\b')
    ]

    for t_idx, t_match in enumerate(tables, 1):
        t_content = t_match.group(1)
        start_pos = t_match.start()
        preceding_text = content[max(0, start_pos - 600):start_pos]
        combined_text = preceding_text + " " + t_content

        for src_name, src_regex in data_sources:
            if re.search(src_regex, combined_text, re.IGNORECASE):
                data_dir = repo_root / "seo" / "data" / src_name
                has_raw_file = False
                if data_dir.exists():
                    for date_dir in data_dir.iterdir():
                        if date_dir.is_dir() and re.match(r'^\d{4}-\d{2}-\d{2}$', date_dir.name):
                            files = [f for f in date_dir.iterdir() if f.is_file() and f.stat().st_size > 0]
                            if files:
                                has_raw_file = True
                                break

                scripts_dir = repo_root / "scripts"
                has_generator = False
                if scripts_dir.exists():
                    gen_files = list(scripts_dir.glob(f"*{src_name}*.py")) + list(scripts_dir.glob("generate_*.py")) + list(scripts_dir.glob("build_*.py"))
                    if gen_files:
                        has_generator = True

                missing = []
                if not has_raw_file:
                    missing.append(f"raw data file in seo/data/{src_name}/<YYYY-MM-DD>/")
                if not has_generator:
                    missing.append(f"generator script in scripts/ (e.g., generate_{src_name}_table.py)")

                if missing:
                    line_num = content[:start_pos].count('\n') + 1
                    findings.append({
                        "file": file_path_str,
                        "line": line_num,
                        "rule": "R10 Missing raw data or generator",
                        "severity": "FAIL",
                        "text": f"Table cites data source '{src_name}', but missing: {', '.join(missing)}"
                    })
    return findings

def check_r11_banned_phrases(lines: list, file_path_str: str):
    findings = []
    for line_idx, line in enumerate(lines, 1):
        for phrase in R11_BANNED_PHRASES:
            pattern = get_banned_phrase_pattern(phrase)
            if re.search(pattern, line, re.IGNORECASE):
                findings.append({
                    "file": file_path_str,
                    "line": line_idx,
                    "rule": "R11 Banned phrase",
                    "severity": "FAIL",
                    "text": f"Found R11 banned phrase: '{phrase}'"
                })
    return findings

def check_r12_period_after_publish(content: str, file_path_str: str):
    findings = []
    pub_date = None
    m = re.search(r'<meta\s+name=["\'](?:publish-date|date|article:published_time)["\']\s+content=["\']([^"\']+)["\']', content, re.I)
    if not m:
        m = re.search(r'<meta\s+property=["\']article:published_time["\']\s+content=["\']([^"\']+)["\']', content, re.I)
    if m:
        pub_date = parse_date_str(m.group(1))

    if not pub_date:
        m_json = re.search(r'"datePublished"\s*:\s*"([^"]+)"', content)
        if m_json:
            pub_date = parse_date_str(m_json.group(1))

    if not pub_date:
        m_txt = re.search(r'(?:Published|Updated|Date)\s*:\s*([A-Za-z0-9, ]{8,25})', content, re.I)
        if m_txt:
            pub_date = parse_date_str(m_txt.group(1))

    if not pub_date:
        return findings

    week_end_matches = re.finditer(r'week\s+ending\s+([A-Za-z]+)\s+(\d{1,2}),?\s*(\d{4})', content, re.I)
    for wem in week_end_matches:
        month_name = wem.group(1).lower()
        if month_name in MONTH_MAP:
            try:
                claimed_end = datetime.date(int(wem.group(3)), MONTH_MAP[month_name], int(wem.group(2)))
                if claimed_end > pub_date:
                    findings.append({
                        "file": file_path_str,
                        "line": content[:wem.start()].count('\n') + 1,
                        "rule": "R12 Claimed period after publish date",
                        "severity": "FAIL",
                        "text": f"Claimed period '{wem.group(0)}' ends on {claimed_end}, after publish date {pub_date}"
                    })
            except ValueError:
                pass

    range_matches = re.finditer(r'(?:([A-Za-z]+)\s+(\d{1,2})\s*[-–—to]+\s*(?:([A-Za-z]+)\s+)?(\d{1,2}),?\s*(\d{4}))', content, re.I)
    for rm in range_matches:
        end_month_str = rm.group(3) or rm.group(1)
        end_month_str = end_month_str.lower()
        if end_month_str in MONTH_MAP:
            try:
                claimed_end = datetime.date(int(rm.group(5)), MONTH_MAP[end_month_str], int(rm.group(4)))
                if claimed_end > pub_date:
                    findings.append({
                        "file": file_path_str,
                        "line": content[:rm.start()].count('\n') + 1,
                        "rule": "R12 Claimed period after publish date",
                        "severity": "FAIL",
                        "text": f"Claimed period '{rm.group(0)}' ends on {claimed_end}, after publish date {pub_date}"
                    })
            except ValueError:
                pass

    completed_weeks = re.finditer(r'(\d+)\s+completed\s+([A-Za-z]+)\s+weeks', content, re.I)
    for cwm in completed_weeks:
        num_weeks = int(cwm.group(1))
        month_str = cwm.group(2).lower()
        if month_str in MONTH_MAP:
            month_num = MONTH_MAP[month_str]
            if pub_date.month == month_num:
                required_days = num_weeks * 7
                if required_days > pub_date.day:
                    findings.append({
                        "file": file_path_str,
                        "line": content[:cwm.start()].count('\n') + 1,
                        "rule": "R12 Claimed period after publish date",
                        "severity": "FAIL",
                        "text": f"Claimed '{cwm.group(0)}' requires {required_days} completed days, but page was published on day {pub_date.day}"
                    })

    return findings

def check_r13_standard_template(content: str, file_path_str: str):
    findings = []
    if not (file_path_str.endswith(".html") or ".html" in file_path_str):
        return findings

    # Skip meta-refresh redirect stubs
    if re.search(r'<meta\s+http-equiv=["\']refresh["\']', content, re.I):
        return findings

    missing = []
    if '<header' not in content:
        missing.append("site header (<header>)")
    if '<footer' not in content:
        missing.append("site footer (<footer>)")
    if 'gtag(\'consent\'' not in content and 'gtag("consent"' not in content:
        missing.append("consent snippet (gtag consent default)")
    if 'function gtag()' not in content and 'googletagmanager.com/gtag/js' not in content and 'dataLayer' not in content:
        missing.append("gtag loader")
    if '/js/analytics.js' not in content and 'js/analytics.js' not in content:
        missing.append("analytics script (/js/analytics.js)")

    if missing:
        findings.append({
            "file": file_path_str,
            "line": 1,
            "rule": "R13 Missing standard site template components",
            "severity": "FAIL",
            "text": f"Deployable HTML page is missing standard components: {', '.join(missing)}"
        })

    return findings


def check_r14_crop_media_captions(content: str, file_path_str: str):
    findings = []
    if not (file_path_str.endswith(".html") or ".html" in file_path_str or "<html" in content.lower()):
        return findings

    # Only inspect files referencing /images/crop/ or /media/video/
    if "/images/crop/" not in content and "/media/video/" not in content:
        return findings

    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(content, "html.parser")
    except Exception:
        return findings

    # Banned terms and regexes for R14
    banned_patterns = [
        (r'\bNorth\s+Gujarat\b', "North Gujarat"),
        (r'\bGujarat\b', "Gujarat"),
        (r'\bBanaskantha\b', "Banaskantha"),
        (r'\bVav\s*[-/]?\s*Tharad\b', "Vav-Tharad"),
        (r'\bDeodar\b', "Deodar"),
        (r'\bSardarpura\b', "Sardarpura"),
        (r'\bour\b', "our"),
        (r'\bNagdev\b', "Nagdev"),
        (r'\b(?:our\s+plant|Nagdev\s+plant|at\s+(?:the|our)\s+plant|(?:crushing|manufacturing|processing|extraction|refining|solvent)\s+plant|plant\s+(?:facility|facilities|equipment|premises|site|operations|setup|floor))\b', "plant (as a facility)"),
        (r'\bfarms?\s+of\b', "farm of"),
        (r'\bcleaned\b', "cleaned"),
        (r'\bprocessing\b', "processing"),
        (r'\bprocessed\b', "processed"),
        (r'\bprepared\s+for\b', "prepared for"),
        (r'\btransport\b', "transport"),
        (r'\bmandi\b', "mandi"),
        (r'\bAPMC\b', "APMC"),
        (r'\bprocured\b', "procured"),
        # Gujarati equivalents
        (r'ગુજરાત', "ગુજરાત"),
        (r'બનાસકાંઠા', "બનાસકાંઠા"),
        (r'દિયોદર', "દિયોદર"),
        (r'અમારા', "અમારા"),
        (r'અમારી', "અમારી"),
        (r'પ્લાન્ટ', "પ્લાન્ટ (plant)")
    ]

    elements = soup.find_all(['img', 'source', 'video'])
    checked_elements = set()

    for el in elements:
        src = el.get('src', '') or ''
        srcset = el.get('srcset', '') or ''
        data_src = el.get('data-src', '') or ''
        poster = el.get('poster', '') or ''

        combined_src = f"{src} {srcset} {data_src} {poster}"
        if not ('/images/crop/' in combined_src or '/media/video/' in combined_src):
            continue

        alt = el.get('alt', '')
        aria_label = el.get('aria-label', '')

        # Enclosing or associated figcaption
        fig = el.find_parent('figure')
        figcaption_text = ""
        if fig and fig.find('figcaption'):
            figcaption_text = fig.find('figcaption').get_text(strip=True)
        else:
            # Climb up parent containers
            curr = el.parent
            for _ in range(4):
                if curr:
                    fc = curr.find('figcaption')
                    if fc:
                        figcaption_text = fc.get_text(strip=True)
                        break
                    curr = curr.parent

        elem_id = (el.name, alt, aria_label, figcaption_text)
        if elem_id in checked_elements:
            continue
        checked_elements.add(elem_id)

        line_num = 1
        # Check forbidden words across alt, aria-label, figcaption
        checks = [
            ("alt text", alt),
            ("aria-label", aria_label),
            ("figcaption", figcaption_text)
        ]

        for label, text_val in checks:
            if not text_val:
                continue
            for pattern, name in banned_patterns:
                if re.search(pattern, text_val, re.IGNORECASE):
                    findings.append({
                        "file": file_path_str,
                        "line": line_num,
                        "rule": "R14 Crop/video caption honesty",
                        "severity": "FAIL",
                        "text": f"Found forbidden {label} term '{name}' in crop/video media element: \"{text_val}\""
                    })

        # Video must contain 'illustrative' in figcaption
        is_video = (el.name == 'video') or ('/media/video/' in combined_src)
        if is_video:
            if not figcaption_text or not re.search(r'\billustrative\b', figcaption_text, re.IGNORECASE):
                findings.append({
                    "file": file_path_str,
                    "line": line_num,
                    "rule": "R14 Crop/video caption honesty",
                    "severity": "FAIL",
                    "text": f"Video caption must contain the word 'illustrative'. Found: \"{figcaption_text}\""
                })

    return findings


def check_r15_cross_page_specs(content: str, file_path_str: str) -> list:
    """
    R15: Cross-page specification consistency.
    Any page (/castor-oil-manufacturer-gujarat, /bulk-castor-oil-supply,
    /castor-oil-exporter-india, /about, /process-flow, etc.) that quotes
    spec parameters/limits for any product must match canonical product specs.
    A different limit or unit -> FAIL.
    """
    findings = []
    norm = content.replace('&lt;', '<').replace('&gt;', '>').replace('&le;', '≤').replace('&ge;', '≥').replace('&ndash;', '–')

    # 1. FSG Lovibond mismatch: Lovibond Y+5R < 2.5 is forbidden; must be Max 20Y + 2R
    if re.search(r'first\s+special\s+grade|FSG', norm, re.IGNORECASE):
        if re.search(r'Lovibond\s*(?:Y\s*\+\s*5R|\(Y\+5R\))\s*<\s*2\.5', norm, re.IGNORECASE):
            findings.append({
                "file": file_path_str,
                "line": 0,
                "rule": "R15 Cross-page spec consistency",
                "severity": "FAIL",
                "text": "FSG spec mismatch: found outdated Lovibond Y+5R < 2.5; canonical spec is Lovibond: Max 20Y + 2R"
            })

    # 2. Ricinoleic Acid Acid Value mismatch: 175–185 is forbidden; must be 175 Min
    if re.search(r'ricinoleic\s+acid', norm, re.IGNORECASE):
        rows = re.findall(r'<tr\b[^>]*>(.*?)</tr>', norm, re.DOTALL | re.IGNORECASE)
        found_ra_av = False
        for row in rows:
            if re.search(r'ricinoleic\s+acid', row, re.IGNORECASE) and not re.search(r'12-hydroxy', row, re.IGNORECASE):
                if re.search(r'Acid\s+Value[^\w\r\n]{1,10}175\s*[–—\-]\s*185', row, re.IGNORECASE):
                    found_ra_av = True
                    break
        if not found_ra_av and not rows:
            if re.search(r'Acid\s+Value[^\w\r\n]{1,10}175\s*[–—\-]\s*185', norm, re.IGNORECASE):
                found_ra_av = True

        if found_ra_av:
            findings.append({
                "file": file_path_str,
                "line": 0,
                "rule": "R15 Cross-page spec consistency",
                "severity": "FAIL",
                "text": "Ricinoleic Acid spec mismatch: found Acid Value 175–185; canonical spec is Acid Value: 175 Min"
            })

    # 3. 12-HSA Melting Point mismatch: 74–77°C is forbidden; must be 75°C–78°C
    if re.search(r'12-hydroxystearic|12-HSA', norm, re.IGNORECASE):
        if re.search(r'Melting\s+Point[^\w\r\n]{1,10}74\s*[–—\-]\s*77', norm, re.IGNORECASE):
            findings.append({
                "file": file_path_str,
                "line": 0,
                "rule": "R15 Cross-page spec consistency",
                "severity": "FAIL",
                "text": "12-HSA spec mismatch: found Melting Point 74–77°C; canonical spec is Melting Point: 75°C–78°C"
            })

    # 4. HCO Iodine Value mismatch: IV < 3.0 is forbidden; must be ≤ 4.0
    if re.search(r'hydrogenated\s+castor|HCO', norm, re.IGNORECASE):
        if re.search(r'(?:IV|Iodine\s+Value)\s*<\s*3\.0', norm, re.IGNORECASE):
            findings.append({
                "file": file_path_str,
                "line": 0,
                "rule": "R15 Cross-page spec consistency",
                "severity": "FAIL",
                "text": "HCO spec mismatch: found IV < 3.0; canonical spec is Iodine Value: ≤ 4.0"
            })

    return findings

def check_r16_pharma_cosmetic(content: str, file_path_str: str) -> list:
    """
    R16: Pharmacopoeia and cosmetic grade pages restrictions.
    Must contain NO numeric specification values and must NOT contain:
    GMP, certified, approved, drug licence, excipient manufacturer, FDA, CEP, DMF.
    """
    findings = []
    pharma_cosmetic_slugs = [
        "castor-oil-bp93",
        "castor-oil-usp-nf",
        "castor-oil-ph-eur",
        "castor-oil-ip",
        "castor-oil-jp",
        "cosmetic-grade-castor-oil"
    ]
    is_pharma_cosmetic = any(slug in file_path_str.lower() for slug in pharma_cosmetic_slugs)
    if not is_pharma_cosmetic:
        return findings

    lines = content.splitlines()

    # 1. Banned certification / regulatory claims
    r16_banned_terms = [
        (r"\bGMP\b", "GMP"),
        (r"\bcertified\b", "certified"),
        (r"\bapproved\b", "approved"),
        (r"\bdrug\s+licen[sc]e\b", "drug licence"),
        (r"\bexcipient\s+manufacturer\b", "excipient manufacturer"),
        (r"\bFDA\b", "FDA"),
        (r"\bCEP\b", "CEP"),
        (r"\bDMF\b", "DMF")
    ]
    for line_idx, line in enumerate(lines, 1):
        for pattern, term_name in r16_banned_terms:
            if re.search(pattern, line, re.IGNORECASE):
                findings.append({
                    "file": file_path_str,
                    "line": line_idx,
                    "rule": "R16 Pharma/Cosmetic banned claim",
                    "severity": "FAIL",
                    "text": f"Pharmacopoeia/cosmetic page contains forbidden term '{term_name}' on line {line_idx}: '{line.strip()[:100]}'"
                })

    # 2. NO numeric specification values (no numbers next to spec parameter names)
    spec_param_re = re.compile(
        r'\b(free\s+fatty\s+acids?|ffa|acid\s+value|saponification\s+value|sap\s+value|iodine\s+value|hydroxyl\s+value|moisture(?:\s+and\s+volatile\s+matter)?|relative\s+density|specific\s+gravity|refractive\s+index|optical\s+rotation|viscosity|colour|color|lovibond|gardner|heavy\s+metals?|peroxide\s+value|unsaponifiable\s+matter|ash)\b',
        re.IGNORECASE
    )
    spec_val_re = re.compile(
        r'(?:[:=≤≥<>–\-]\s*\d+(?:\.\d+)?|\b\d+(?:\.\d+)?\s*(?:%|mg\b|ppm\b|cst\b|poise\b|°c\b|max\b|min\b)|\b(?:max|min)\b\s*\d+(?:\.\d+)?|\b\d+\.\d+\b)',
        re.IGNORECASE
    )
    for line_idx, line in enumerate(lines, 1):
        if "<script" in line.lower() or "</script>" in line.lower() or "<style" in line.lower() or "href=" in line or "src=" in line:
            continue
        plain = re.sub(r'<[^>]+>', ' ', line)
        for m in spec_param_re.finditer(plain):
            start = max(0, m.start() - 35)
            end = min(len(plain), m.end() + 45)
            window = plain[start:end]
            num_match = spec_val_re.search(window)
            if num_match:
                findings.append({
                    "file": file_path_str,
                    "line": line_idx,
                    "rule": "R16 Numeric spec on pharma/cosmetic page",
                    "severity": "FAIL",
                    "text": f"Pharmacopoeia/cosmetic page contains numeric specification near '{m.group(0)}' on line {line_idx}: '{window.strip()[:100]}'"
                })

    return findings


def check_r17_page_identity(content: str, file_path_str: str) -> list:
    norm_path = file_path_str.replace('\\', '/').lower()
    if not ('products/' in norm_path and norm_path.endswith('.html')):
        return []
    filename = norm_path.split('products/')[-1]
    if filename in ('index.html', 'castor-cake-fertilizer.html', 'de-oiled-cake-castor-meal.html'):
        return []
    slug = filename.replace('.html', '')

    PRODUCT_DISTINCTIVE_TERMS = {
        "commercial-castor-oil": [("Commercial Grade Castor Oil", r'\bcommercial\s+(?:grade\s+)?castor\s+oil\b')],
        "first-special-grade-castor-oil": [("First Special Grade", r'\bfirst\s+special\s+grade\b'), ("FSG", r'\bFSG\b'), ("BSS", r'\bBSS\b')],
        "fpd-castor-oil": [("First Pressed Degummed", r'\bfirst\s+pressed\s+degummed\b'), ("FPD", r'\bFPD\b')],
        "castor-cake": [("Castor Cake", r'\bcastor\s+cake\b'), ("Expeller Cake", r'\bexpeller\s+cake\b')],
        "hydrogenated-castor-oil": [("Hydrogenated Castor Oil", r'\bhydrogenated\s+castor\s+oil\b'), ("HCO", r'\bHCO\b'), ("Castor Wax", r'\bcastor\s+wax\b')],
        "dehydrated-castor-oil": [("Dehydrated Castor Oil", r'\bdehydrated\s+castor\s+oil\b(?![\s\-]*fatty)'), ("DCO", r'\bDCO\b(?![\s\-]*fa\b|[\s\-]*fatty)')],
        "dco-fatty-acid": [("DCO Fatty Acid", r'\b(?:dco[\s\-]*fa|dco\s+fatty\s+acid|dehydrated\s+castor\s+oil\s+fatty\s+acid)\b')],
        "ppg-castor-oil": [("Pale Pressed Grade", r'\bpale\s+pressed\b'), ("PPG", r'\bPPG\b')],
        "cold-pressed-castor-oil": [("Cold Pressed", r'\bcold[\s\-]pressed\b')],
        "castor-oil-bp93": [("British Pharmacopoeia", r'\bbritish\s+pharmacop[oe]+ia\b'), ("BP", r'\bBP\b(?![\s\-]*93\b)'), ("BP 93", r'\bBP[\s\-]*93\b')],
        "castor-oil-usp-nf": [("United States Pharmacopeia", r'\bunited\s+states\s+pharmacop[oe]+ia\b'), ("USP", r'\bUSP\b'), ("USP-NF", r'\bUSP[\s\-\/]*NF\b')],
        "castor-oil-ph-eur": [("European Pharmacopoeia", r'\beuropean\s+pharmacop[oe]+ia\b'), ("Ph. Eur.", r'\bph\.?\s*eur\.?\b'), ("EP", r'\bEP\b')],
        "castor-oil-ip": [("Indian Pharmacopoeia", r'\bindian\s+pharmacop[oe]+ia\b'), ("IP", r'\bIP\b')],
        "castor-oil-jp": [("Japanese Pharmacopoeia", r'\bjapanese\s+pharmacop[oe]+ia\b'), ("JP", r'\bJP\b')],
        "cosmetic-grade-castor-oil": [("Cosmetic Grade", r'\bcosmetic\s+grade\b')],
        "ricinoleic-acid": [("Ricinoleic Acid", r'\bricinoleic\s+acid\b')],
        "12-hydroxystearic-acid": [("12-Hydroxystearic Acid", r'\b12[\s\-]hydroxy\s*stearic\b'), ("12-HSA", r'(?<!calcium )(?<!calcium-)(?<!lithium )(?<!lithium-)(?<!methyl )(?<!methyl-)\b12[\s\-]*HSA\b')],
        "sebacic-acid": [("Sebacic Acid", r'\bsebacic\s+acid\b')],
        "high-protein-castor-meal": [("High-Protein Castor Meal", r'\bhigh[\s\-]protein\s+castor\s+meal\b'), ("Castor Meal", r'\bcastor\s+meal\b')],
        "crude-glycerin": [("Crude Glycerin", r'\bcrude\s+glycerin[e]?\b')],
        "refined-glycerin": [("Refined Glycerin", r'\brefined\s+glycerin[e]?\b')],
        "bio-polyurethane-polyols": [("Bio-Polyurethane Polyols", r'\bbio[\s\-]polyurethane\b'), ("Bio-PU Polyols", r'\bbio[\s\-]pu\b')],
        "sodium-sulphate-anhydrous": [("Sodium Sulphate Anhydrous", r'\bsodium\s+sul(?:ph|f)ate\b')],
        "dioctyl-sebacate": [("Dioctyl Sebacate", r'\bdioctyl\s+sebacate\b'), ("DOS", r'\bDOS\b')],
        "dibutyl-sebacate": [("Dibutyl Sebacate", r'\bdibutyl\s+sebacate\b'), ("DBS", r'\bDBS\b')],
        "methyl-12-hydroxystearate": [("Methyl 12-Hydroxystearate", r'\bmethyl\s+12[\s\-]hydroxy\b'), ("Methyl 12-HSA", r'\bmethyl\s+12[\s\-]*hsa\b')],
        "methyl-ricinoleate": [("Methyl Ricinoleate", r'\bmethyl\s+ricinoleate\b')],
        "lithium-12-hydroxystearate": [("Lithium 12-Hydroxystearate", r'\blithium\s+12[\s\-]hydroxy\b'), ("Lithium 12-HSA", r'\blithium\s+12[\s\-]*hsa\b')],
        "calcium-12-hydroxystearate": [("Calcium 12-Hydroxystearate", r'\bcalcium\s+12[\s\-]hydroxy\b'), ("Calcium 12-HSA", r'\bcalcium\s+12[\s\-]*hsa\b')],
        "zinc-undecylenate": [("Zinc Undecylenate", r'\bzinc\s+undecylenate\b')],
        "zinc-ricinoleate": [("Zinc Ricinoleate", r'\bzinc\s+ricinoleate\b')],
        "blown-oxidized-castor-oil": [("Blown Castor Oil", r'\bblown\s+castor\s+oil\b'), ("Oxidized Castor Oil", r'\boxidi[sz]ed\s+castor\s+oil\b')]
    }

    if slug not in PRODUCT_DISTINCTIVE_TERMS:
        return []

    soup = BeautifulSoup(content, 'html.parser')
    findings = []

    # 1. H1
    h1 = soup.find('h1')
    h1_text = h1.get_text(' ', strip=True) if h1 else ""

    # 2. Breadcrumb last item
    bc_text = ""
    bc_div = soup.find('div', id='main-content')
    if bc_div:
        spans = bc_div.find_all('span')
        if spans:
            bc_text = spans[-1].get_text(' ', strip=True)
            if bc_text == '/':
                links = bc_div.find_all(['a', 'span'])
                if links:
                    bc_text = links[-1].get_text(' ', strip=True)
    if not bc_text:
        for s in soup.find_all('script', type='application/ld+json'):
            if 'BreadcrumbList' in (s.string or ''):
                m = re.findall(r'"name"\s*:\s*"([^"]+)"', s.string)
                if m:
                    bc_text = m[-1]

    # 3. Hero image alt
    hero_alt = ""
    hero_img = soup.find('img', class_=re.compile(r'product-media|hero', re.I))
    if hero_img and hero_img.get('alt'):
        hero_alt = hero_img.get('alt')
    else:
        img = soup.find('img')
        if img and img.get('alt'):
            hero_alt = img.get('alt')

    # 4. H2s and H3s outside related-products
    headings = []
    for tag in soup.find_all(['h2', 'h3']):
        if tag.find_parent(class_=re.compile(r'related', re.I)) or tag.find_parent(id=re.compile(r'related', re.I)):
            continue
        txt = tag.get_text(' ', strip=True)
        if re.search(r'related\s+products', txt, re.I):
            continue
        headings.append(txt)

    # 5. Title
    title = soup.title.string if soup.title else ""

    # 6. Meta description
    meta_desc = ""
    md = soup.find('meta', attrs={'name': 'description'})
    if md and md.get('content'):
        meta_desc = md.get('content')

    # 7. FAQ questions
    faq_questions = []
    for sum_tag in soup.find_all('summary'):
        if sum_tag.find_parent('nav') or sum_tag.find_parent(class_=re.compile(r'mobile-nav|menu', re.I)):
            continue
        txt = sum_tag.get_text(' ', strip=True)
        if txt.startswith('Products ('):
            continue
        faq_questions.append(txt)
    for s in soup.find_all('script', type='application/ld+json'):
        if 'Question' in (s.string or '') or 'FAQPage' in (s.string or ''):
            qs = re.findall(r'"name"\s*:\s*"([^"]+\?)"', s.string)
            for q in qs:
                if q not in faq_questions:
                    faq_questions.append(q)

    # Check for foreign terms in each zone
    for other_slug, terms in PRODUCT_DISTINCTIVE_TERMS.items():
        if other_slug == slug:
            continue
        for term_name, pat in terms:
            if re.search(pat, h1_text, re.I):
                findings.append({
                    "file": file_path_str,
                    "line": 0,
                    "rule": "R17 Page Identity",
                    "severity": "FAIL",
                    "text": f"Page '{slug}' H1 contains foreign product term '{term_name}' from '{other_slug}': '{h1_text}'"
                })
            if re.search(pat, bc_text, re.I):
                findings.append({
                    "file": file_path_str,
                    "line": 0,
                    "rule": "R17 Page Identity",
                    "severity": "FAIL",
                    "text": f"Page '{slug}' breadcrumb contains foreign product term '{term_name}' from '{other_slug}': '{bc_text}'"
                })
            if re.search(pat, hero_alt, re.I):
                findings.append({
                    "file": file_path_str,
                    "line": 0,
                    "rule": "R17 Page Identity",
                    "severity": "FAIL",
                    "text": f"Page '{slug}' hero alt contains foreign product term '{term_name}' from '{other_slug}': '{hero_alt}'"
                })
            if re.search(pat, title, re.I):
                findings.append({
                    "file": file_path_str,
                    "line": 0,
                    "rule": "R17 Page Identity",
                    "severity": "FAIL",
                    "text": f"Page '{slug}' title contains foreign product term '{term_name}' from '{other_slug}': '{title}'"
                })
            if re.search(pat, meta_desc, re.I):
                findings.append({
                    "file": file_path_str,
                    "line": 0,
                    "rule": "R17 Page Identity",
                    "severity": "FAIL",
                    "text": f"Page '{slug}' meta description contains foreign product term '{term_name}' from '{other_slug}': '{meta_desc}'"
                })
            for h in headings:
                if re.search(pat, h, re.I):
                    findings.append({
                        "file": file_path_str,
                        "line": 0,
                        "rule": "R17 Page Identity",
                        "severity": "FAIL",
                        "text": f"Page '{slug}' heading contains foreign product term '{term_name}' from '{other_slug}': '{h}'"
                    })
            for q in faq_questions:
                if re.search(pat, q, re.I):
                    findings.append({
                        "file": file_path_str,
                        "line": 0,
                        "rule": "R17 Page Identity",
                        "severity": "FAIL",
                        "text": f"Page '{slug}' FAQ question contains foreign product term '{term_name}' from '{other_slug}': '{q}'"
                    })

    return findings


def load_product_master(repo_root: Path = REPO_ROOT):
    master_path = repo_root / "seo" / "product-master.json"
    if master_path.exists():
        try:
            with open(master_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def check_r18_internal_links(content: str, file_path_str: str, repo_root: Path = REPO_ROOT):
    findings = []
    if not file_path_str.endswith(".html"):
        return findings

    # Find all href in a and link tags
    # Remove script and style tags before checking HTML links
    no_scripts = re.sub(r'<(?:script|style)\b[^>]*>.*?</(?:script|style)>', ' ', content, flags=re.DOTALL | re.IGNORECASE)
    hrefs = re.finditer(r"""<(?:a|link)\b[^>]*\bhref=["']([^"']+)["']""", no_scripts, re.IGNORECASE)
    for hm in hrefs:
        href = hm.group(1).strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:", "data:", "${")):
            continue
        if "${" in href or "{{" in href:
            continue
            continue
        if href.startswith(("http://", "https://")):
            # If it's an internal nagdev URL, extract the path
            if "nagdevproducts.com" in href:
                href = re.sub(r'^https?://(?:www\.)?nagdevproducts\.com', '', href)
            else:
                continue

        # Check for malformed or un-normalized URL encodings
        if "%20" in href or " " in href:
            findings.append({
                "file": file_path_str,
                "line": content[:hm.start()].count('\n') + 1,
                "rule": "R18 Malformed internal link URL",
                "severity": "FAIL",
                "text": f"Internal link has un-normalized percent encoding or space: '{href}'"
            })
            continue

        clean_path = href.split("?")[0].split("#")[0]
        if not clean_path or clean_path == "/":
            continue

        rel = clean_path.lstrip("/")
        # Verify target existence locally
        target_file = repo_root / rel
        target_html = repo_root / (rel + ".html")
        target_idx = repo_root / rel / "index.html"

        if not (target_file.exists() or target_html.exists() or target_idx.exists()):
            findings.append({
                "file": file_path_str,
                "line": content[:hm.start()].count('\n') + 1,
                "rule": "R18 Broken internal link",
                "severity": "FAIL",
                "text": f"Internal link '{href}' does not resolve to an existing file in repo"
            })
    return findings

def check_r19_brand_codes(content: str, file_path_str: str, repo_root: Path = REPO_ROOT):
    findings = []
    lines = content.splitlines()

    master = load_product_master(repo_root)
    canonical_codes = set(p.get("brand_code", "") for p in master if "brand_code" in p)

    legacy_hyphen_re = re.compile(r'\bNDEV-[A-Z0-9\-]+\b')
    specialty_range_re = re.compile(r'\bSpecialty\s+Range\b', re.IGNORECASE)
    ndev_brand_re = re.compile(r'\bNDEV[A-Z]+(?:\u2122|™)\s+[A-Z0-9\-]+')

    for line_idx, line in enumerate(lines, 1):
        # 1. Check legacy hyphens
        for m in legacy_hyphen_re.finditer(line):
            findings.append({
                "file": file_path_str,
                "line": line_idx,
                "rule": "R19 Legacy brand code",
                "severity": "FAIL",
                "text": f"Found legacy hyphenated brand code: '{m.group(0)}' (must use canonical code from product-master.json)"
            })

        # 2. Check Specialty Range
        for m in specialty_range_re.finditer(line):
            findings.append({
                "file": file_path_str,
                "line": line_idx,
                "rule": "R19 Banned Specialty Range label",
                "severity": "FAIL",
                "text": f"Found banned label '{m.group(0)}' (must use 'Under development')"
            })

        # 3. Check trademarked NDEV brand codes against canonical set
        for m in ndev_brand_re.finditer(line):
            code_found = m.group(0).replace('\u2122', '™')
            if canonical_codes and code_found not in canonical_codes:
                findings.append({
                    "file": file_path_str,
                    "line": line_idx,
                    "rule": "R19 Non-canonical brand code",
                    "severity": "FAIL",
                    "text": f"Brand code '{code_found}' does not match canonical codes in product-master.json"
                })

    return findings


def check_r20_efficacy_claims(content: str, file_path_str: str) -> list:
    findings = []
    lines = content.splitlines()

    pests = r'\b(pest|nematod|insect|fung|weed|disease)\w*'
    actions = r'\b(suppress|repel|control|kill|prevent|protect|resist)\w*'
    p1 = rf'{pests}(?:\s+\S+){{0,5}}\s+{actions}'
    p2 = rf'{actions}(?:\s+\S+){{0,5}}\s+{pests}'
    efficacy_re = re.compile(rf'({p1}|{p2})', re.IGNORECASE)

    direct_phrases = [
        "phytosanitary",
        "cash crops benefit",
        "yield increase",
        "boosts yield",
        "cures",
        "heals"
    ]
    direct_re = re.compile(r'\b(' + '|'.join(re.escape(p) for p in direct_phrases) + r')\b', re.IGNORECASE)

    for line_idx, line in enumerate(lines, 1):
        m_eff = efficacy_re.search(line)
        if m_eff:
            findings.append({
                "file": file_path_str,
                "line": line_idx,
                "rule": "R20 Efficacy claim",
                "severity": "FAIL",
                "text": f"Found prohibited efficacy claim: '{m_eff.group(0)}'"
            })
        m_dir = direct_re.search(line)
        if m_dir:
            findings.append({
                "file": file_path_str,
                "line": line_idx,
                "rule": "R20 Prohibited claim phrase",
                "severity": "FAIL",
                "text": f"Found prohibited agricultural/health claim phrase: '{m_dir.group(0)}'"
            })

    return findings

def lint_content(content: str, file_path_str: str, facts: dict):
    findings = []
    lines = content.splitlines()

    banned_phrases = facts.get("banned_phrases", [])
    certifications_held = set(facts.get("certifications_held", []))
    region_context = facts.get("company", {}).get("region_context", "")
    
    # ----------------------------------------------------
    # R1: Banned phrases (case-insensitive)
    # ----------------------------------------------------
    for line_idx, line in enumerate(lines, 1):
        for phrase in banned_phrases:
            pattern = get_banned_phrase_pattern(phrase)
            if re.search(pattern, line, re.IGNORECASE):
                findings.append({
                    "file": file_path_str,
                    "line": line_idx,
                    "rule": "R1 Banned phrase",
                    "severity": "FAIL",
                    "text": f"Found banned phrase: '{phrase}'"
                })

    # ----------------------------------------------------
    # Process wording restriction (processes_allowed)
    # ----------------------------------------------------
    allowed_procs = set(p.lower() for p in (facts.get("operations", {}).get("processes_allowed") or facts.get("processes_allowed", [])))
    banned_proc_patterns = [
        (r'\bneutrali[sz]ation\b|\bneutrali[sz]e\b|\bneutrali[sz]ing\b|\bneutrali[sz]ed\b', "neutralisation/neutralization"),
        (r'\bdeodori[sz]ation\b|\bdeodori[sz]e\b|\bdeodori[sz]ing\b|\bdeodori[sz]ed\b', "deodorisation/deodorization"),
        (r'\bsteam\s+distillation\b', "steam distillation"),
        (r'\bwinteri[sz]ation\b|\bwinteri[sz]e\b|\bwinteri[sz]ing\b', "winterisation/winterization"),
    ]
    for line_idx, line in enumerate(lines, 1):
        if "<script" in line.lower() or "</script>" in line.lower() or "<style" in line.lower():
            continue
        for pat, proc_name in banned_proc_patterns:
            if re.search(pat, line, re.IGNORECASE):
                if not any(proc_name.lower() in p or p in proc_name.lower() for p in allowed_procs):
                    findings.append({
                        "file": file_path_str,
                        "line": line_idx,
                        "rule": "R11 Restricted process claim",
                        "severity": "FAIL",
                        "text": f"Found process claim '{proc_name}' not listed in processes_allowed"
                    })

    # ----------------------------------------------------
    # R2: Certifications held
    # ----------------------------------------------------
    for line_idx, line in enumerate(lines, 1):
        for pattern, cert_name in CERT_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                # Check if cert_name is in certifications_held
                is_held = any(c.lower() in cert_name.lower() or cert_name.lower() in c.lower() for c in certifications_held)
                if not is_held:
                    # Make sure it's not already reported as R1 banned phrase on same line
                    # But report as R2 certification violation
                    findings.append({
                        "file": file_path_str,
                        "line": line_idx,
                        "rule": "R2 Unheld certification",
                        "severity": "FAIL",
                        "text": f"Certification claim '{cert_name}' not held in facts register"
                    })

    # ----------------------------------------------------
    # R3: Under-development products claiming commercial production
    # ----------------------------------------------------
    prose = strip_tags(content)
    sentences = split_into_sentences(prose)

    # Also check JSON-LD strings
    json_ld_matches = re.findall(r'<script\s+type=["\']application/ld\+json["\']>(.*?)</script>', content, flags=re.DOTALL | re.IGNORECASE)
    for jm in json_ld_matches:
        try:
            data = json.loads(jm.strip())
            def extract_strings(obj):
                if isinstance(obj, str):
                    if len(obj) > 30 and ' ' in obj:
                        sentences.extend(split_into_sentences(obj))
                elif isinstance(obj, dict):
                    for k, v in obj.items():
                        if k not in ["@context", "@type", "@id", "url", "image", "logo"]:
                            extract_strings(v)
                elif isinstance(obj, list):
                    for item in obj:
                        extract_strings(item)
            extract_strings(data)
        except Exception:
            pass

    # Also collect raw HTML attributes (alt, title, aria-label, meta content)
    attr_matches = re.finditer(r"""(?:alt|title|aria-label|content)=["']([^"']+)["']""", content, re.IGNORECASE)
    for am in attr_matches:
        val = am.group(1).strip()
        if len(val) > 10:
            sentences.append(val)

    for sent in sentences:
        if DEV_PROD_RE.search(sent) and R3_TRIGGER_RE.search(sent):
            if "under development" not in sent.lower():
                findings.append({
                    "file": file_path_str,
                    "line": 0,
                    "rule": "R3 Unqualified under-dev claim",
                    "severity": "FAIL",
                    "text": f"Sentence claims production/supply of developmental product without 'under development': '{sent[:120]}...'"
                })

    # ----------------------------------------------------
    # R4: Product counts must match facts register
    # ----------------------------------------------------
    reg_count = len(facts.get("products", {}).get("regular_supply", []))
    enq_count = len(facts.get("products", {}).get("on_enquiry", []))
    dev_count = len(facts.get("products", {}).get("under_development", []))
    total_count = reg_count + enq_count + dev_count
    allowed_counts = {total_count, reg_count, enq_count, dev_count}

    for line_idx, line in enumerate(lines, 1):
        # Ignore lines that are purely HTML attribute declarations like URLs or query params
        line_no_urls = re.sub(r'https?://[^\s"\'<>]+', '', line)
        line_no_urls = re.sub(r'%\d{2}', ' ', line_no_urls)
        # Look for numbers preceding products/grades/derivatives
        # Remove decimal numbers like 21.5 MT so '5' is not extracted
        line_no_urls = re.sub(r'\d+\.\d+', ' ', line_no_urls)
        # Remove NLGI Grade mentions
        line_no_urls = re.sub(r'NLGI\s+Grade\s+\d+', ' ', line_no_urls, flags=re.IGNORECASE)
        # Remove 12-Hydroxystearic or 12-HSA
        line_no_urls = re.sub(r'12[- ](?:Hydroxystearic|HSA)', ' ', line_no_urls, flags=re.IGNORECASE)
        # Remove question counts
        line_no_urls = re.sub(r'\b\d+\s+critical\s+questions?\b', ' ', line_no_urls, flags=re.IGNORECASE)
        count_matches = re.finditer(r'\b(\d+)\s*(?:\+\s*\d+\s*)?(?:core\s+|specialty\s+|commercial\s+|under[- ]development\s+|developmental\s+|on[- ]enquiry\s+|regular[- ]supply\s+|advanced\s+|castor(?:\s+oil)?\s+)?(products?|grades?|derivatives?)\b', line_no_urls, re.IGNORECASE)
        for cm in count_matches:
            num = int(cm.group(1))
            if num not in allowed_counts:
                findings.append({
                    "file": file_path_str,
                    "line": line_idx,
                    "rule": "R4 Invalid product count",
                    "severity": "FAIL",
                    "text": f"Invalid count '{cm.group(0)}' (allowed counts: {total_count} total, {reg_count} regular, {enq_count} enquiry, {dev_count} under dev)"
                })

    # ----------------------------------------------------
    # R5: Plant address/district must match register
    # "Banaskantha" next to Deodar, Sardarpura, 385330 or "district" -> FAIL
    # "Banaskantha" allowed ONLY inside exact region_context or in farmer/seed-sourcing context
    # ----------------------------------------------------
    for line_idx, line in enumerate(lines, 1):
        if "banaskantha" in line.lower():
            # Check if line is within exact region_context
            line_has_region_context = region_context.lower() in line.lower()
            # Check if line is farmer/seed-sourcing context
            line_has_farmer_context = bool(re.search(r'\b(farmers?|seed\s+sourc(?:ing|ed)|cultivat(?:ion|ed)|harvest(?:ing|ed)|mandi|procuring|APMC)\b', line, re.IGNORECASE))
            
            # Check violations: Banaskantha next to Deodar, Sardarpura, 385330 or district
            has_plant_proximity = bool(re.search(r'\b(deodar|sardarpura|385330|district|dist\.)\b.*?\bbanaskantha\b|\bbanaskantha\b.*?\b(deodar|sardarpura|385330|district|dist\.)\b', line, re.IGNORECASE))
            
            if has_plant_proximity:
                findings.append({
                    "file": file_path_str,
                    "line": line_idx,
                    "rule": "R5 Banaskantha in plant district",
                    "severity": "FAIL",
                    "text": f"Plant district incorrectly references Banaskantha instead of District Vav-Tharad: '{line.strip()[:120]}'"
                })
            elif not line_has_region_context and not line_has_farmer_context:
                findings.append({
                    "file": file_path_str,
                    "line": line_idx,
                    "rule": "R5 Unapproved Banaskantha mention",
                    "severity": "FAIL",
                    "text": f"Banaskantha mentioned outside region_context or farmer/seed-sourcing context: '{line.strip()[:120]}'"
                })

    # ----------------------------------------------------
    # R6: Capacity: any TPD/TPA/MT per day other than "50 TPD" seed crushing -> FAIL
    # ----------------------------------------------------
    for line_idx, line in enumerate(lines, 1):
        # Look for TPD mentions
        tpd_matches = re.finditer(r'\b(\d+(?:,\d+)?)\s*TPD\b', line, re.IGNORECASE)
        for tm in tpd_matches:
            val = tm.group(1).replace(',', '')
            if val != "50":
                findings.append({
                    "file": file_path_str,
                    "line": line_idx,
                    "rule": "R6 Unapproved capacity",
                    "severity": "FAIL",
                    "text": f"Capacity '{tm.group(0)}' not approved (only 50 TPD seed crushing allowed)"
                })
        
        # Look for any TPA mentions
        tpa_matches = re.finditer(r'\b(\d+(?:,\d+)?)\s*TPA\b', line, re.IGNORECASE)
        for tm in tpa_matches:
            findings.append({
                "file": file_path_str,
                "line": line_idx,
                "rule": "R6 Unapproved annual capacity (TPA)",
                "severity": "FAIL",
                "text": f"Annual capacity claim '{tm.group(0)}' not approved"
            })

        # Look for MT per day
        mt_matches = re.finditer(r'\b(\d+(?:,\d+)?)\s*(?:MT|metric\s+tons?|tonnes?)\s*(?:per|\/)\s*day\b', line, re.IGNORECASE)
        for mm in mt_matches:
            val = mm.group(1).replace(',', '')
            if val != "50":
                findings.append({
                    "file": file_path_str,
                    "line": line_idx,
                    "rule": "R6 Unapproved capacity",
                    "severity": "FAIL",
                    "text": f"Daily capacity claim '{mm.group(0)}' not approved"
                })

    # ----------------------------------------------------
    # R7: SPEC CONSISTENCY (per product page)
    # ----------------------------------------------------
    if "/products/" in file_path_str.replace("\\", "/") or file_path_str.startswith("products/"):
        specs = parse_spec_table(content)
        table_params = specs.get("params", {})
        table_color_scales = specs.get("color_scale", set())

        if table_params:
            norm_content = content.replace('&le;', '≤').replace('&ge;', '≥').replace('&deg;', '°')

            # Check for color scale discrepancy across the page
            has_gardner = bool(re.search(r'\bgardner\b', norm_content, re.IGNORECASE))
            has_lovibond = bool(re.search(r'\blovibond\b', norm_content, re.IGNORECASE))

            if has_gardner and "gardner" not in table_color_scales:
                findings.append({
                    "file": file_path_str,
                    "line": 0,
                    "rule": "R7 Spec consistency (Colour scale)",
                    "severity": "FAIL",
                    "text": f"Page mentions 'Gardner' color scale, but analytical spec table only defines Lovibond"
                })
            if has_lovibond and "lovibond" not in table_color_scales:
                findings.append({
                    "file": file_path_str,
                    "line": 0,
                    "rule": "R7 Spec consistency (Colour scale)",
                    "severity": "FAIL",
                    "text": f"Page mentions 'Lovibond' color scale, but analytical spec table does not define it"
                })

            # Check Free Fatty Acid (FFA)
            if "ffa" in table_params:
                table_ffa_num = extract_numeric_val(table_params["ffa"])
                ffa_mentions = re.finditer(r'\b(?:FFA|Free\s+Fatty\s+Acids?)\b[^\w\n]{1,20}([≤<]?\s*\d+(?:\.\d+)?\s*%)', norm_content, re.IGNORECASE)
                for fm in ffa_mentions:
                    val_num = extract_numeric_val(fm.group(1))
                    if val_num is not None and table_ffa_num is not None:
                        if abs(val_num - table_ffa_num) > 0.01:
                            match_pos = fm.start()
                            table_pos = norm_content.find("class=\"spec-table\"")
                            if table_pos != -1 and abs(match_pos - table_pos) < 500 and "tbody" in norm_content[table_pos:match_pos+200]:
                                continue
                            findings.append({
                                "file": file_path_str,
                                "line": norm_content[:match_pos].count('\n') + 1,
                                "rule": "R7 Spec consistency (FFA)",
                                "severity": "FAIL",
                                "text": f"FFA mention '{fm.group(0)}' conflicts with analytical spec table value '{table_params['ffa']}'"
                            })

            # Check Acid Value
            if "acid_value" in table_params:
                table_av_num = extract_numeric_val(table_params["acid_value"])
                av_mentions = re.finditer(r'\bAcid\s+Value\b[^\w\n]{1,20}([≤<]?\s*\d+(?:\.\d+)?)', norm_content, re.IGNORECASE)
                for am in av_mentions:
                    val_num = extract_numeric_val(am.group(1))
                    if val_num is not None and table_av_num is not None:
                        if abs(val_num - table_av_num) > 0.01:
                            match_pos = am.start()
                            table_pos = norm_content.find("class=\"spec-table\"")
                            if table_pos != -1 and abs(match_pos - table_pos) < 500 and "tbody" in norm_content[table_pos:match_pos+200]:
                                continue
                            findings.append({
                                "file": file_path_str,
                                "line": norm_content[:match_pos].count('\n') + 1,
                                "rule": "R7 Spec consistency (Acid Value)",
                                "severity": "FAIL",
                                "text": f"Acid Value mention '{am.group(0)}' conflicts with analytical spec table value '{table_params['acid_value']}'"
                            })

            # Check Moisture
            if "moisture" in table_params:
                table_m_num = extract_numeric_val(table_params["moisture"])
                m_mentions = re.finditer(r'\bMoisture\b[^\w\n]{1,15}([≤<]?\s*\d+(?:\.\d+)?\s*%)', norm_content, re.IGNORECASE)
                for mm in m_mentions:
                    val_num = extract_numeric_val(mm.group(1))
                    if val_num is not None and table_m_num is not None:
                        if abs(val_num - table_m_num) > 0.01:
                            match_pos = mm.start()
                            table_pos = norm_content.find("class=\"spec-table\"")
                            if table_pos != -1 and abs(match_pos - table_pos) < 500 and "tbody" in norm_content[table_pos:match_pos+200]:
                                continue
                            findings.append({
                                "file": file_path_str,
                                "line": norm_content[:match_pos].count('\n') + 1,
                                "rule": "R7 Spec consistency (Moisture)",
                                "severity": "FAIL",
                                "text": f"Moisture mention '{mm.group(0)}' conflicts with analytical spec table value '{table_params['moisture']}'"
                            })

            # Check Ricinoleic Acid Content
            if "ricinoleic" in table_params:
                table_r_num = extract_numeric_val(table_params["ricinoleic"])
                r_mentions = re.finditer(r'\bRicinoleic(?:\s+Acid)?(?:\s+Content)?\b[^\w\n]{1,15}([≥>]?\s*\d+(?:\.\d+)?\s*%)', norm_content, re.IGNORECASE)
                for rm in r_mentions:
                    val_num = extract_numeric_val(rm.group(1))
                    if val_num is not None and table_r_num is not None:
                        if abs(val_num - table_r_num) > 0.01:
                            match_pos = rm.start()
                            table_pos = norm_content.find("class=\"spec-table\"")
                            if table_pos != -1 and abs(match_pos - table_pos) < 500 and "tbody" in norm_content[table_pos:match_pos+200]:
                                continue
                            findings.append({
                                "file": file_path_str,
                                "line": norm_content[:match_pos].count('\n') + 1,
                                "rule": "R7 Spec consistency (Ricinoleic)",
                                "severity": "FAIL",
                                "text": f"Ricinoleic content mention '{rm.group(0)}' conflicts with analytical spec table value '{table_params['ricinoleic']}'"
                            })
            if "moisture" in table_params:
                table_m_num = extract_numeric_val(table_params["moisture"])
                m_mentions = re.finditer(r'\bMoisture\b[^\w\n]{1,15}([≤<]?\s*\d+(?:\.\d+)?\s*%)', content, re.IGNORECASE)
                for mm in m_mentions:
                    val_num = extract_numeric_val(mm.group(1))
                    if val_num is not None and table_m_num is not None:
                        if abs(val_num - table_m_num) > 0.01:
                            match_pos = mm.start()
                            findings.append({
                                "file": file_path_str,
                                "line": content[:match_pos].count('\n') + 1,
                                "rule": "R7 Spec consistency (Moisture)",
                                "severity": "FAIL",
                                "text": f"Moisture mention '{mm.group(0)}' conflicts with analytical spec table value '{table_params['moisture']}'"
                            })

            # Check Ricinoleic Acid Content
            if "ricinoleic" in table_params:
                table_r_num = extract_numeric_val(table_params["ricinoleic"])
                r_mentions = re.finditer(r'\bRicinoleic(?:\s+Acid)?(?:\s+Content)?\b[^\w\n]{1,15}([≥>]?\s*\d+(?:\.\d+)?\s*%)', content, re.IGNORECASE)
                for rm in r_mentions:
                    val_num = extract_numeric_val(rm.group(1))
                    if val_num is not None and table_r_num is not None:
                        if abs(val_num - table_r_num) > 0.01:
                            match_pos = rm.start()
                            findings.append({
                                "file": file_path_str,
                                "line": content[:match_pos].count('\n') + 1,
                                "rule": "R7 Spec consistency (Ricinoleic)",
                                "severity": "FAIL",
                                "text": f"Ricinoleic content mention '{rm.group(0)}' conflicts with analytical spec table value '{table_params['ricinoleic']}'"
                            })

    # ----------------------------------------------------
    # R8: Commercial terms (MOQ, lead time, delivery days, price, etc.)
    # ----------------------------------------------------
    for line_idx, line in enumerate(lines, 1):
        ct_match = COMMERCIAL_TERMS_RE.search(line)
        if ct_match:
            findings.append({
                "file": file_path_str,
                "line": line_idx,
                "rule": "R8 Commercial terms",
                "severity": "FAIL",
                "text": f"Commercial term '{ct_match.group(0)}' found (not authorized in register)"
            })

    # ----------------------------------------------------
    # R9: Unlinked percentages/numbers in prose (WARN)
    # ----------------------------------------------------
    paragraphs = re.findall(r'<p\b[^>]*>(.*?)</p>', content, flags=re.DOTALL | re.IGNORECASE)
    for p in paragraphs:
        # Check for unlinked statistics like "90% of global supply"
        stats_matches = re.finditer(r'(\b\d{1,3}(?:\.\d+)?%\b|\b\d+(?:,\d+)?\s*(?:metric\s+tons?|tonnes?)\b)', p)
        for sm in stats_matches:
            # If paragraph has <a href, it's considered sourced
            if '<a ' not in p:
                findings.append({
                    "file": file_path_str,
                    "line": 0,
                    "rule": "R9 Statistic without nearby link",
                    "severity": "WARN",
                    "text": f"Statistic '{sm.group(1)}' in prose without nearby reference link in paragraph"
                })

    # ----------------------------------------------------
    # R10: Table data sources must have matching raw data & generator script
    # ----------------------------------------------------
    findings.extend(check_r10_table_sources(content, file_path_str))

    # ----------------------------------------------------
    # R11: Banned additions to register's banned phrases
    # ----------------------------------------------------
    findings.extend(check_r11_banned_phrases(lines, file_path_str))

    # ----------------------------------------------------
    # R12: Claimed data period after publish date
    # ----------------------------------------------------
    findings.extend(check_r12_period_after_publish(content, file_path_str))

    # ----------------------------------------------------
    # R13: Standard site template components
    # ----------------------------------------------------
    findings.extend(check_r13_standard_template(content, file_path_str))

    # ----------------------------------------------------
    # R14: Crop & Video Media Captions / Alt Honesty
    # ----------------------------------------------------
    findings.extend(check_r14_crop_media_captions(content, file_path_str))
    findings.extend(check_r15_cross_page_specs(content, file_path_str))
    findings.extend(check_r16_pharma_cosmetic(content, file_path_str))
    findings.extend(check_r17_page_identity(content, file_path_str))
    findings.extend(check_r18_internal_links(content, file_path_str))
    findings.extend(check_r19_brand_codes(content, file_path_str))
    findings.extend(check_r20_efficacy_claims(content, file_path_str))

    return findings

def lint_file(file_path: Path, facts: dict = None):
    if facts is None:
        facts = load_facts()
    try:
        rel_path = file_path.resolve().relative_to(REPO_ROOT).as_posix()
    except Exception:
        rel_path = file_path.as_posix()
    content = file_path.read_text(encoding='utf-8', errors='ignore')
    return lint_content(content, rel_path, facts)

def run_production_audit(facts: dict):
    import xml.etree.ElementTree as ET
    import urllib.request
    import time

    sitemap_path = REPO_ROOT / "sitemap.xml"
    urls = set()
    # Explicitly ensure root homepage is audited
    urls.add("https://www.nagdevproducts.com/")
    if sitemap_path.exists():
        tree = ET.parse(sitemap_path)
        root = tree.getroot()
        namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        for loc in root.findall('.//ns:loc', namespace):
            urls.add(loc.text.strip())

    urls.add("https://www.nagdevproducts.com/certifications")
    urls.add("https://www.nagdevproducts.com/quality")
    urls.add("https://www.nagdevproducts.com/team")

    assert "https://www.nagdevproducts.com/" in urls, "CRITICAL: Homepage '/' missing from production audit URLs list!"
    sorted_urls = sorted(urls)
    print("==================================================")
    print("NAGDEV CLAIMS LINTER: PRODUCTION LIVE AUDIT")
    print(f"Auditing {len(sorted_urls)} live URLs (Plain + Cache-Busted)...")
    print("==================================================")

    all_findings = []
    fail_count = 0
    warn_count = 0
    fails_by_rule = {f"R{i}": 0 for i in range(1, 21)}
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    cb_ts = int(time.time())

    for idx, u in enumerate(sorted_urls, 1):
        # 1. Plain fetch
        # 2. Cache-busted fetch
        for fetch_url, mode in [(u, "plain"), (f"{u}?cb={cb_ts}", "cache-busted")]:
            success = False
            last_err = None
            for attempt in range(3):
                try:
                    req = urllib.request.Request(fetch_url, headers=headers)
                    with urllib.request.urlopen(req, timeout=20) as res:
                        if res.getcode() != 200:
                            all_findings.append({
                                "file": f"{u} ({mode})",
                                "line": 0,
                                "rule": "HTTP Status",
                                "severity": "FAIL",
                                "text": f"HTTP {res.getcode()} returned"
                            })
                            fail_count += 1
                            success = True
                            break
                        html = res.read().decode('utf-8', errors='ignore')
                        res_findings = lint_content(html, f"{u} ({mode})", facts)
                        for item in res_findings:
                            all_findings.append(item)
                            if item["severity"] == "FAIL":
                                fail_count += 1
                                for r_key in fails_by_rule:
                                    if item["rule"].startswith(r_key):
                                        fails_by_rule[r_key] += 1
                            else:
                                warn_count += 1
                        success = True
                        break
                except Exception as e:
                    last_err = e
                    time.sleep(1)

            if not success:
                all_findings.append({
                    "file": f"{u} ({mode})",
                    "line": 0,
                    "rule": "Fetch Error",
                    "severity": "FAIL",
                    "text": str(last_err)
                })
                fail_count += 1

    print("\n==================================================")
    print("PRODUCTION CLAIMS LINTER AUDIT SUMMARY")
    print(f"Total Live URLs Scanned: {len(sorted_urls)} (tested plain and cache-busted)")
    print(f"Production Hard Failures: {fail_count}")
    print(f"Production Warnings: {warn_count}")
    print("Failures by Rule:")
    for r_k, r_c in sorted(fails_by_rule.items()):
        print(f"  {r_k}: {r_c}")
    print("==================================================")

    if fail_count > 0:
        print(f"\n[FAILED] Production claims gate audit failed with {fail_count} failures!")
        for f in all_findings:
            if f["severity"] == "FAIL":
                print(f"  FAIL: {f['file']} [{f['rule']}] -> {f['text']}")
        return 1
    else:
        print("\n[SUCCESS] PRODUCTION LINTER PASSED WITH 0 FAILURES!")
        return 0

def main():
    facts = load_facts()
    if "--production" in sys.argv or "--prod" in sys.argv:
        return run_production_audit(facts)

    files = collect_files()
    print("==================================================")
    print("NAGDEV CLAIMS LINTER & PERMANENT FACT GATE (PHASE 3b)")
    print(f"Scanning {len(files)} deployable files across repo...")
    print("==================================================")

    all_findings = []
    fail_count = 0
    warn_count = 0
    fails_by_rule = {f"R{i}": 0 for i in range(1, 21)}

    for f in files:
        f_findings = lint_file(f, facts)
        for item in f_findings:
            all_findings.append(item)
            if item["severity"] == "FAIL":
                fail_count += 1
                for r_key in fails_by_rule:
                    if item["rule"].startswith(r_key):
                        fails_by_rule[r_key] += 1
            else:
                warn_count += 1

    # Save Markdown and CSV reports
    report_md = REPO_ROOT / "seo" / "claims-lint-report.md"
    report_csv = REPO_ROOT / "seo" / "claims-lint-report.csv"
    
    with open(report_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["file", "line", "rule", "severity", "text"])
        writer.writeheader()
        writer.writerows(all_findings)

    with open(report_md, "w", encoding="utf-8") as f:
        f.write("# Nagdev Claims Linter & Fact Verification Report\n\n")
        f.write(f"- Total Files Scanned: {len(files)}\n")
        f.write(f"- Total Failures (Exit != 0): **{fail_count}**\n")
        f.write(f"- Total Warnings (Review items): **{warn_count}**\n\n")
        f.write("### Failures by Rule\n")
        for r_k, r_c in fails_by_rule.items():
            f.write(f"- **{r_k}**: {r_c}\n")
        f.write("\n| File | Line | Rule | Severity | Details |\n")
        f.write("|---|---|---|---|---|\n")
        for item in all_findings:
            f.write(f"| `{item['file']}` | {item['line']} | {item['rule']} | **{item['severity']}** | {item['text'].replace('|', '/')} |\n")

    print("\nScan complete:")
    print(f"  FAILURES: {fail_count}")
    for r_k, r_c in fails_by_rule.items():
        print(f"    {r_k}: {r_c}")
    print(f"  WARNINGS: {warn_count}")
    print("Detailed reports written to:")
    print(f"  - {report_md}")
    print(f"  - {report_csv}")

    if fail_count > 0:
        print("\n[FAILED] One or more hard claims gate rules (R1-R14) failed.")
        return 1
    else:
        print("\n[PASSED] All hard claims gate rules (R1-R14) passed with 0 failures!")
        return 0

if __name__ == "__main__":
    sys.exit(main())

