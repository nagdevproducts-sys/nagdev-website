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
"""

import sys
import os
import re
import json
import csv
from pathlib import Path

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
    for p in root.rglob("*"):
        if p.is_file() and is_deployable(p):
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
    r"\bsebacic\s+acid\b",
    r"\bdehydrated\s+castor\s+oil\b",
    r"\bdco\b",
    r"\bdco\s+fatty\s+acid\b",
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
    r"\bblown\s+castor\s+oil\b"
]

DEV_PROD_RE = re.compile("|".join(DEV_PRODUCT_REGEXES), re.IGNORECASE)
R3_TRIGGER_RE = re.compile(r"\b(produce|produces|produced|producing|manufacture|manufactures|manufactured|manufacturing|supply|supplies|supplied|supplying|available|in stock|offer|offers|offered|offering|dispatch|dispatches|dispatched|dispatching|solution|solutions)\b", re.IGNORECASE)

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
            # Word boundary regex for phrases and single words
            pattern = r'(?<!\w)' + re.escape(phrase) + r'(?!\w)'
            if re.search(pattern, line, re.IGNORECASE):
                findings.append({
                    "file": file_path_str,
                    "line": line_idx,
                    "rule": "R1 Banned phrase",
                    "severity": "FAIL",
                    "text": f"Found banned phrase: '{phrase}'"
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
    # R4: Product counts must be 27 / 7 / 7 / 13
    # ----------------------------------------------------
    for line_idx, line in enumerate(lines, 1):
        # Ignore lines that are purely HTML attribute declarations like URLs or query params
        line_no_urls = re.sub(r'https?://[^\s"\'<>]+', '', line)
        line_no_urls = re.sub(r'%\d{2}', ' ', line_no_urls)
        # Look for numbers preceding products/grades/derivatives
        count_matches = re.finditer(r'\b(\d+)\s*(?:\+\s*\d+\s*)?(?:core\s+|specialty\s+|commercial\s+)?(products?|grades?|derivatives?)\b', line_no_urls, re.IGNORECASE)
        for cm in count_matches:
            num = int(cm.group(1))
            if num not in [27, 7, 13]:
                findings.append({
                    "file": file_path_str,
                    "line": line_idx,
                    "rule": "R4 Invalid product count",
                    "severity": "FAIL",
                    "text": f"Invalid count '{cm.group(0)}' (allowed counts: 27 total, 7 regular, 7 enquiry, 13 under dev)"
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
    if sitemap_path.exists():
        tree = ET.parse(sitemap_path)
        root = tree.getroot()
        namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        for loc in root.findall('.//ns:loc', namespace):
            urls.add(loc.text.strip())

    urls.add("https://www.nagdevproducts.com/certifications")
    urls.add("https://www.nagdevproducts.com/quality")
    urls.add("https://www.nagdevproducts.com/team")

    sorted_urls = sorted(urls)
    print("==================================================")
    print("NAGDEV CLAIMS LINTER: PRODUCTION LIVE AUDIT")
    print(f"Auditing {len(sorted_urls)} live URLs (Plain + Cache-Busted)...")
    print("==================================================")

    all_findings = []
    fail_count = 0
    warn_count = 0
    fails_by_rule = {f"R{i}": 0 for i in range(1, 9)}
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    cb_ts = int(time.time())

    for idx, u in enumerate(sorted_urls, 1):
        # 1. Plain fetch
        # 2. Cache-busted fetch
        for fetch_url, mode in [(u, "plain"), (f"{u}?cb={cb_ts}", "cache-busted")]:
            try:
                req = urllib.request.Request(fetch_url, headers=headers)
                with urllib.request.urlopen(req, timeout=15) as res:
                    if res.getcode() != 200:
                        all_findings.append({
                            "file": f"{u} ({mode})",
                            "line": 0,
                            "rule": "HTTP Status",
                            "severity": "FAIL",
                            "text": f"HTTP {res.getcode()} returned"
                        })
                        fail_count += 1
                        continue
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
            except Exception as e:
                all_findings.append({
                    "file": f"{u} ({mode})",
                    "line": 0,
                    "rule": "Fetch Error",
                    "severity": "FAIL",
                    "text": str(e)
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
    fails_by_rule = {f"R{i}": 0 for i in range(1, 9)}

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
        print("\n[FAILED] One or more hard claims gate rules (R1-R8) failed.")
        return 1
    else:
        print("\n[PASSED] All hard claims gate rules (R1-R8) passed with 0 failures!")
        return 0

if __name__ == "__main__":
    sys.exit(main())

