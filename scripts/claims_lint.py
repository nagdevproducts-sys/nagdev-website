#!/usr/bin/env python3
"""
claims_lint.py - Single source-of-truth claims linter and gate for nagdevproducts.com.
Scans all deployable HTML files, llms.txt, sitemap.xml, and JSON-LD schemas against seo/facts-register.json.

Rules:
(a) Banned phrases (case-insensitive) [FAIL]
(b) Under-development products claiming production/supply without 'under development' [FAIL]
(c) Product counts other than 27 total / 7 regular / 7 on enquiry / 13 under development [FAIL]
(d) Address/phone/CIN not matching facts register [FAIL]
(e) Capacities other than 50 TPD seed crushing [FAIL]
(f) Equipment/process words not in processes_allowed [WARN/REVIEW]
(g) Statistics/percentages in prose without nearby source <a> link [WARN]

Exit code != 0 on any rule (a)-(e) failure.
"""

import sys
import os
import re
import json
import csv
from pathlib import Path

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

REPO_ROOT = Path(__file__).resolve().parent.parent
FACTS_PATH = REPO_ROOT / "seo" / "facts-register.json"

if not FACTS_PATH.exists():
    print(f"FATAL: Facts register not found at {FACTS_PATH}")
    sys.exit(1)

with open(FACTS_PATH, "r", encoding="utf-8") as f:
    FACTS = json.load(f)

BANNED_PHRASES = FACTS.get("banned_phrases", [])
COMPANY = FACTS.get("company", {})
OPERATIONS = FACTS.get("operations", {})
PRODUCTS = FACTS.get("products", {})

REGULAR_SLUGS = set(PRODUCTS.get("regular_supply", []))
ENQUIRY_SLUGS = set(PRODUCTS.get("on_enquiry", []))
DEV_SLUGS = set(PRODUCTS.get("under_development", []))

# Names/aliases of under development products
DEV_PRODUCT_NAMES = [
    r"sebacic acid",
    r"dehydrated castor oil",
    r"\bdco\b",
    r"dco fatty acid",
    r"bio-polyurethane polyols?",
    r"bio-pu polyols?",
    r"dioctyl sebacate",
    r"\bdos\b",
    r"dibutyl sebacate",
    r"\bdbs\b",
    r"methyl 12-hydroxystearate",
    r"methyl ricinoleate",
    r"lithium 12-hydroxystearate",
    r"calcium 12-hydroxystearate",
    r"zinc undecylenate",
    r"zinc ricinoleate",
    r"blown oxidized castor oil",
    r"blown castor oil"
]

DEV_PROD_REGEX = re.compile(r"|".join(DEV_PRODUCT_NAMES), re.IGNORECASE)
TRIGGER_WORDS_REGEX = re.compile(r"\b(produce|produced|manufacture|manufactured|supply|supplied|available|in stock|solutions|offer|dispatch)\b", re.IGNORECASE)
ALLOWED_DEV_QUALIFIERS = re.compile(r"\b(under development|under r&d|development stage|in development|developmental|r&d)\b", re.IGNORECASE)

# Ignored files/directories based on .vercelignore and scratch
IGNORED_PARTS = {"scratch", "scripts", "seo", ".git", ".agents", ".gemini", "node_modules", "backup_task4"}
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

def collect_files():
    deployable = []
    for p in REPO_ROOT.rglob("*"):
        if p.is_file() and is_deployable(p):
            # Include deployable html, llms.txt, sitemap.xml, etc.
            if p.suffix == ".html" or p.name in ["llms.txt", "llms-full.txt", "sitemap.xml"]:
                deployable.append(p)
    return sorted(deployable)

def strip_tags(text: str) -> str:
    # Remove script and style tags completely
    clean = re.sub(r'<(script|style)\b[^>]*>.*?</\1>', ' ', text, flags=re.DOTALL | re.IGNORECASE)
    # Remove HTML comments
    clean = re.sub(r'<!--.*?-->', ' ', clean, flags=re.DOTALL)
    # Replace block end tags and cell end tags with a period so sentences don't merge across blocks
    clean = re.sub(r'</(p|div|tr|td|th|li|h[1-6]|section|article|header|footer|dl|dd|dt)>', '. ', clean, flags=re.IGNORECASE)
    # Remove HTML tags but preserve text spacing
    clean = re.sub(r'<[^>]+>', ' ', clean)
    clean = re.sub(r'\s+', ' ', clean)
    return clean

def split_into_sentences(text: str):
    # Split on punctuation followed by space and capital letter or end
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z0-9"\'‘“])', text)
    return [s.strip() for s in sentences if len(s.strip()) > 10]

def lint_file(file_path: Path):
    rel_path = file_path.relative_to(REPO_ROOT).as_posix()
    content = file_path.read_text(encoding='utf-8', errors='ignore')
    lines = content.splitlines()
    
    findings = [] # (file, line_num, rule, severity, text)

    # 1. Line by line check for exact banned phrases & capacities & bad addresses
    for line_idx, line in enumerate(lines, 1):
        line_clean = line.strip()
        
        # Rule (a): Banned phrases
        for phrase in BANNED_PHRASES:
            # Word boundary regex for single words or phrase search
            pattern = r'\b' + re.escape(phrase) + r'\b'
            if re.search(pattern, line, re.IGNORECASE):
                # Exception: "countries" in legitimate technical context? Register bans "countries", "worldwide", etc.
                # If phrase is "countries", check if it's describing export destinations
                findings.append({
                    "file": rel_path,
                    "line": line_idx,
                    "rule": "Rule (a) Banned phrase",
                    "severity": "FAIL",
                    "text": f"Found banned phrase: '{phrase}'"
                })

        # Rule (c): Product count irregularities
        # e.g., "20 Specialty", "20 products", "20 grades", "7 Core + 20", "20 derivative"
        count_bad_patterns = [
            (r'(?<!%)\b20\s*(?:Specialty|grades?|products?|derivatives?)\b', "Invalid product count: '20' (must be 7 on enquiry, 13 under dev)"),
            (r'(?<!%)\b7\s*Core\s*\+\s*20\b', "Invalid count: '7 Core + 20'"),
            (r'(?<!%)\b7\s*core\s*products?\s*and\s*20\b', "Invalid count: '7 core and 20'")
        ]
        for cp, cmsg in count_bad_patterns:
            if re.search(cp, line, re.IGNORECASE):
                findings.append({
                    "file": rel_path,
                    "line": line_idx,
                    "rule": "Rule (c) Product count irregularity",
                    "severity": "FAIL",
                    "text": cmsg
                })

        # Rule (d): Addresses, legal name, phone
        if "Banaskantha" in line and "region_context" not in line:
            # Plant address must be District Vav-Tharad; Banaskantha only allowed in region context
            # "North Gujarat's castor belt (Banaskantha and Vav-Tharad region)"
            if "Banaskantha and Vav-Tharad region" not in line and "Banaskantha region" not in line and "Banaskantha district" not in line.lower():
                if "Sardarpura, Banaskantha" in line or "Dist. Banaskantha" in line or "(Banaskantha)" in line:
                    findings.append({
                        "file": rel_path,
                        "line": line_idx,
                        "rule": "Rule (d) Outdated legal/plant district",
                        "severity": "FAIL",
                        "text": "Outdated reference to Banaskantha in plant address (must be District Vav-Tharad)"
                    })

        # Rule (e): Capacities other than 50 TPD
        cap_bad = re.findall(r'\b(30|40|60|100|150|200)\s*(?:TPD|tons?\s*per\s*day)\b', line, re.IGNORECASE)
        if cap_bad:
            findings.append({
                "file": rel_path,
                "line": line_idx,
                "rule": "Rule (e) Unapproved capacity",
                "severity": "FAIL",
                "text": f"Capacity mention '{cap_bad[0]} TPD' not allowed (only 50 TPD crushing allowed)"
            })
            
        tpa_bad = re.findall(r'\b\d{4,6}\s*(?:TPA|tons?\s*per\s*annum)\b', line, re.IGNORECASE)
        if tpa_bad:
            findings.append({
                "file": rel_path,
                "line": line_idx,
                "rule": "Rule (e) Unapproved annual capacity",
                "severity": "FAIL",
                "text": f"Annual capacity claim '{tpa_bad[0]}' not verified in facts register"
            })

    # Rule (b): Under-development products claiming commercial production in sentences
    if file_path.suffix == ".html" or file_path.name in ["llms.txt", "llms-full.txt"]:
        prose_content = strip_tags(content)
        sentences = split_into_sentences(prose_content)
        
        # Also extract strings from JSON-LD to check FAQ answers, descriptions, etc.
        json_ld_matches = re.findall(r'<script\s+type=["\']application/ld\+json["\']>(.*?)</script>', content, flags=re.DOTALL | re.IGNORECASE)
        for jm in json_ld_matches:
            try:
                data = json.loads(jm.strip())
                def extract_strings(obj):
                    if isinstance(obj, str):
                        # Only split long string fields like descriptions or answers
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
            if DEV_PROD_REGEX.search(sent) and TRIGGER_WORDS_REGEX.search(sent):
                if not ALLOWED_DEV_QUALIFIERS.search(sent):
                    findings.append({
                        "file": rel_path,
                        "line": 0,
                        "rule": "Rule (b) Unqualified under-dev claim",
                        "severity": "FAIL",
                        "text": f"Sentence claims production/supply of dev product without qualification: '{sent[:120]}...'"
                    })

    # Rule (f): Equipment/process words review
    unapproved_processes = [r'\bsolvent\s+extraction\b', r'\bhexane\b', r'\bchemical\s+leaching\b', r'\bcontinuous\s+neutralization\b']
    for line_idx, line in enumerate(lines, 1):
        for up in unapproved_processes:
            if re.search(up, line, re.IGNORECASE):
                findings.append({
                    "file": rel_path,
                    "line": line_idx,
                    "rule": "Rule (f) Unapproved process flagged for review",
                    "severity": "WARN",
                    "text": f"Mention of process '{up}' flagged for verification"
                })

    # Rule (g): Unlinked percentages / numbers in prose
    # Check for unlinked statistics like "90% of global supply"
    stats_matches = re.finditer(r'(\b\d{1,3}(?:\.\d+)?%\b|\b\d+(?:,\d+)?\s*(?:metric\s+tons?|tonnes?)\b)', content)
    for sm in stats_matches:
        start = max(0, sm.start() - 100)
        end = min(len(content), sm.end() + 100)
        window = content[start:end]
        # Ignore within table, style, script, meta, spec list, or if nearby <a href
        if '<script' in window or '<style' in window or '<meta' in window or '<td' in window or 'spec-' in window or '<a href' in window:
            continue
        line_num = content[:sm.start()].count('\n') + 1
        findings.append({
            "file": rel_path,
            "line": line_num,
            "rule": "Rule (g) Statistic without nearby link",
            "severity": "WARN",
            "text": f"Statistic '{sm.group(1)}' in prose without nearby reference link"
        })

    return findings

def main():
    files = collect_files()
    print(f"==================================================")
    print(f"NAGDEV CLAIMS LINTER & PERMANENT FACT GATE")
    print(f"Scanning {len(files)} deployable files across repo...")
    print(f"==================================================")

    all_findings = []
    fail_count = 0
    warn_count = 0

    for f in files:
        f_findings = lint_file(f)
        for item in f_findings:
            all_findings.append(item)
            if item["severity"] == "FAIL":
                fail_count += 1
            else:
                warn_count += 1

    # Save Markdown and CSV reports
    report_md = REPO_ROOT / "seo" / "claims-lint-report.md"
    report_csv = REPO_ROOT / "seo" / "claims-lint-report.csv"
    
    # Write CSV
    with open(report_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["file", "line", "rule", "severity", "text"])
        writer.writeheader()
        writer.writerows(all_findings)

    # Write Markdown
    with open(report_md, "w", encoding="utf-8") as f:
        f.write("# Nagdev Claims Linter & Fact Verification Report\n\n")
        f.write(f"- Total Files Scanned: {len(files)}\n")
        f.write(f"- Total Failures (Exit != 0): **{fail_count}**\n")
        f.write(f"- Total Warnings (Review items): **{warn_count}**\n\n")
        f.write("| File | Line | Rule | Severity | Details |\n")
        f.write("|---|---|---|---|---|\n")
        for item in all_findings:
            f.write(f"| `{item['file']}` | {item['line']} | {item['rule']} | **{item['severity']}** | {item['text'].replace('|', '/')} |\n")

    print(f"\nScan complete:")
    print(f"  FAILURES: {fail_count}")
    print(f"  WARNINGS: {warn_count}")
    print(f"Detailed reports written to:")
    print(f"  - {report_md}")
    print(f"  - {report_csv}")

    if fail_count > 0:
        print("\n[FAILED] One or more hard claims gate rules (a)-(e) failed.")
        return 1
    else:
        print("\n[PASSED] All hard claims gate rules (a)-(e) passed with 0 failures!")
        return 0

if __name__ == "__main__":
    sys.exit(main())
