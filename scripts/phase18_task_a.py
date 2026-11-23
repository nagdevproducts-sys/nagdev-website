"""
Phase 18 — Task A: Restore chemistry terminology and add path-based exemptions.

Strategy:
1. Add phrase_path_exemptions to seo/facts-register.json
2. Patch scripts/claims_lint.py to honor those exemptions in R1 and R11 checks
3. Restore the original text in glossary and blog pages
"""
import json, re
from pathlib import Path

REPO = Path('.')

# ── 1. Add phrase_path_exemptions to facts-register.json ───────────────────
fr_path = REPO / 'seo' / 'facts-register.json'
fr = json.loads(fr_path.read_text(encoding='utf-8'))

fr['phrase_path_exemptions'] = {
    "saponification": [
        "glossary/saponification-value.html",
        "blog/hydrogenated-castor-oil-in-lithium-grease-formulation.html"
    ],
    "neutralise": [
        "glossary/acid-value.html"
    ],
    "neutralization": [
        "blog/hydrogenated-castor-oil-in-lithium-grease-formulation.html"
    ],
    "neutralisation": [
        "blog/hydrogenated-castor-oil-in-lithium-grease-formulation.html"
    ]
}
fr_path.write_text(json.dumps(fr, indent=2, ensure_ascii=False), encoding='utf-8')
print("[OK] phrase_path_exemptions added to facts-register.json")

# ── 2. Patch the linter ─────────────────────────────────────────────────────
lint_path = REPO / 'scripts' / 'claims_lint.py'
lint = lint_path.read_text(encoding='utf-8')

# 2a. R1 banned_phrases loop — add exemption check
OLD_R1 = '''    for line_idx, line in enumerate(lines, 1):

        for phrase in banned_phrases:

            phrase_clean = phrase.strip().lower()

            if phrase_clean == "complies to bp" and "castor-oil-bp93.html" in file_path_str.replace("\\\\", "/"):

                continue

            pat = get_compiled_banned_pattern(phrase)

            if pat.search(line):

                findings.append({

                    "file": file_path_str,

                    "line": line_idx,

                    "rule": "R1 Banned phrase",

                    "severity": "FAIL",

                    "text": f"Found banned phrase: \'{phrase}\'"

                })'''

NEW_R1 = '''    _phrase_exemptions = facts.get("phrase_path_exemptions", {})
    _norm_path = file_path_str.replace("\\\\", "/").lower()

    for line_idx, line in enumerate(lines, 1):

        for phrase in banned_phrases:

            phrase_clean = phrase.strip().lower()

            if phrase_clean == "complies to bp" and "castor-oil-bp93.html" in _norm_path:

                continue

            # Check path-based exemptions from facts-register.json
            _exempt_paths = _phrase_exemptions.get(phrase_clean, [])
            if any(_norm_path.endswith(ep.lower().replace("\\\\", "/")) for ep in _exempt_paths):
                continue

            pat = get_compiled_banned_pattern(phrase)

            if pat.search(line):

                findings.append({

                    "file": file_path_str,

                    "line": line_idx,

                    "rule": "R1 Banned phrase",

                    "severity": "FAIL",

                    "text": f"Found banned phrase: \'{phrase}\'"

                })'''

if OLD_R1 in lint:
    lint = lint.replace(OLD_R1, NEW_R1, 1)
    print("[OK] R1 banned_phrases loop patched with path exemptions")
else:
    print("[WARN] R1 loop not found — trying looser match")
    # Try to find just the inner continue block and add exemption before pattern check
    OLD_R1_ALT = '            if phrase_clean == "complies to bp" and "castor-oil-bp93.html" in file_path_str.replace("\\\\", "/"):\n\n                continue\n\n            pat = get_compiled_banned_pattern(phrase)\n\n            if pat.search(line):'
    NEW_R1_ALT = '''            if phrase_clean == "complies to bp" and "castor-oil-bp93.html" in file_path_str.replace("\\\\", "/").lower():

                continue

            # Path-based exemptions from facts-register phrase_path_exemptions
            _phrase_exempt = facts.get("phrase_path_exemptions", {}).get(phrase_clean, [])
            _fpath_norm = file_path_str.replace("\\\\", "/").lower()
            if any(_fpath_norm.endswith(ep.lower().replace("\\\\", "/")) for ep in _phrase_exempt):
                continue

            pat = get_compiled_banned_pattern(phrase)

            if pat.search(line):'''
    if OLD_R1_ALT in lint:
        lint = lint.replace(OLD_R1_ALT, NEW_R1_ALT, 1)
        print("[OK] R1 loop patched (alt match)")
    else:
        print("[ERROR] Could not patch R1 loop")

# 2b. R11 banned_proc_patterns loop — add exemption check for neutralization
OLD_R11_PROC = '''    for line_idx, line in enumerate(lines, 1):

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

                        "text": f"Found process claim \'{proc_name}\' not listed in processes_allowed"

                    })'''

NEW_R11_PROC = '''    _r11_phrase_exemptions = facts.get("phrase_path_exemptions", {})
    _r11_norm_path = file_path_str.replace("\\\\", "/").lower()

    for line_idx, line in enumerate(lines, 1):

        if "<script" in line.lower() or "</script>" in line.lower() or "<style" in line.lower():

            continue

        for pat, proc_name in banned_proc_patterns:

            if re.search(pat, line, re.IGNORECASE):

                if not any(proc_name.lower() in p or p in proc_name.lower() for p in allowed_procs):

                    # Check path-based exemptions
                    _proc_key = proc_name.split("/")[0].strip().lower()
                    _r11_exempt = _r11_phrase_exemptions.get(_proc_key, [])
                    if any(_r11_norm_path.endswith(ep.lower().replace("\\\\", "/")) for ep in _r11_exempt):
                        continue

                    findings.append({

                        "file": file_path_str,

                        "line": line_idx,

                        "rule": "R11 Restricted process claim",

                        "severity": "FAIL",

                        "text": f"Found process claim \'{proc_name}\' not listed in processes_allowed"

                    })'''

if OLD_R11_PROC in lint:
    lint = lint.replace(OLD_R11_PROC, NEW_R11_PROC, 1)
    print("[OK] R11 banned_proc_patterns loop patched with path exemptions")
else:
    print("[WARN] R11 proc loop exact match not found")

# 2c. check_r11_banned_phrases function — add file_path_str and exemptions support
# The function signature is: def check_r11_banned_phrases(lines: list, file_path_str: str):
OLD_R11_FUNC_BODY = '''    findings = []

    for line_idx, line in enumerate(lines, 1):

        for phrase in R11_BANNED_PHRASES:

            pattern = get_banned_phrase_pattern(phrase)

            if re.search(pattern, line, re.IGNORECASE):

                findings.append({

                    "file": file_path_str,

                    "line": line_idx,

                    "rule": "R11 Banned phrase",

                    "severity": "FAIL",

                    "text": f"Found R11 banned phrase: \'{phrase}\'"

                })

    return findings'''

NEW_R11_FUNC_BODY = '''    findings = []

    _r11b_exemptions = (exemptions or {})
    _r11b_norm = file_path_str.replace("\\\\", "/").lower()

    for line_idx, line in enumerate(lines, 1):

        for phrase in R11_BANNED_PHRASES:

            pattern = get_banned_phrase_pattern(phrase)

            if re.search(pattern, line, re.IGNORECASE):

                _ex_paths = _r11b_exemptions.get(phrase.lower(), [])
                if any(_r11b_norm.endswith(ep.lower().replace("\\\\", "/")) for ep in _ex_paths):
                    continue

                findings.append({

                    "file": file_path_str,

                    "line": line_idx,

                    "rule": "R11 Banned phrase",

                    "severity": "FAIL",

                    "text": f"Found R11 banned phrase: \'{phrase}\'"

                })

    return findings'''

if OLD_R11_FUNC_BODY in lint:
    lint = lint.replace(OLD_R11_FUNC_BODY, NEW_R11_FUNC_BODY, 1)
    # Also update the function signature to accept exemptions
    lint = lint.replace(
        'def check_r11_banned_phrases(lines: list, file_path_str: str):',
        'def check_r11_banned_phrases(lines: list, file_path_str: str, exemptions: dict = None):',
        1
    )
    print("[OK] check_r11_banned_phrases function patched with exemptions support")
else:
    print("[WARN] check_r11_banned_phrases body not found exactly")

# Also update the call site to pass exemptions
# Find where check_r11_banned_phrases is called
OLD_CALL = 'check_r11_banned_phrases(lines, file_path_str)'
NEW_CALL = 'check_r11_banned_phrases(lines, file_path_str, exemptions=facts.get("phrase_path_exemptions", {}))'
if OLD_CALL in lint:
    lint = lint.replace(OLD_CALL, NEW_CALL)
    print(f"[OK] Updated check_r11_banned_phrases call site(s)")
else:
    print("[WARN] check_r11_banned_phrases call site not found")

lint_path.write_text(lint, encoding='utf-8')
print("[OK] Linter patched and saved")

# ── 3. Restore glossary/acid-value.html ─────────────────────────────────────
acid_path = REPO / 'glossary' / 'acid-value.html'
acid = acid_path.read_text(encoding='utf-8')
# Restore "neutralise" (was changed to "react with" in Phase 17)
if 'react with the free fatty acids' in acid:
    acid = acid.replace(
        'react with the free fatty acids in 1 g of sample',
        'neutralise the free fatty acids in 1 g of sample'
    )
    acid_path.write_text(acid, encoding='utf-8', newline='\r\n')
    print("[OK] glossary/acid-value.html: restored 'neutralise'")
elif 'neutralise the free fatty acids' in acid:
    print("[SKIP] acid-value.html already has 'neutralise'")
else:
    # Find and restore any form
    t2 = acid.replace('react with', 'neutralise', 1)
    acid_path.write_text(t2, encoding='utf-8', newline='\r\n')
    print("[OK] acid-value.html: replaced 'react with' -> 'neutralise' (generic)")

# ── 4. Restore glossary/saponification-value.html ───────────────────────────
sap_path = REPO / 'glossary' / 'saponification-value.html'
sap = sap_path.read_text(encoding='utf-8')
if 'fully hydrolyse one gram' in sap:
    sap = sap.replace('fully hydrolyse one gram', 'saponify one gram')
    sap_path.write_text(sap, encoding='utf-8', newline='\r\n')
    print("[OK] glossary/saponification-value.html: restored 'saponify one gram'")
elif 'saponify one gram' in sap:
    print("[SKIP] saponification-value.html already has 'saponify one gram'")
else:
    print("[WARN] Neither phrase found in saponification-value.html")

# ── 5. Restore blog/hydrogenated-castor-oil blog terms ──────────────────────
blog_path = REPO / 'blog' / 'hydrogenated-castor-oil-in-lithium-grease-formulation.html'
blog = blog_path.read_text(encoding='utf-8')

# 5a. Restore "saponification" in chemistry/test method contexts
# Phase 17 changed:
#   "react to form lithium 12-hydroxystearate" (was: saponification reactions)
#   "in-situ soap formation" (was: in-situ saponification)
#   "ester hydrolysis" (was: standalone saponification)
#   "acid-base reaction" (was: neutralization)
#   "soap-forming reaction" (was: neutralization reaction)

replacements = [
    # JSON-LD FAQ answer - restore "saponification" reactions
    (
        'react to form lithium 12-hydroxystearate, whose secondary hydroxyl groups form hydrogen-bonded fibril matrices',
        'saponification reactions yield lithium 12-hydroxystearate, whose secondary hydroxyl groups form hydrogen-bonded fibril matrices'
    ),
    # "in-situ soap formation" -> "in-situ saponification"
    ('in-situ soap formation (yielding glycerin', 'in-situ saponification (yielding glycerin'),
    # "soap-forming reaction" -> "saponification" / "neutralization"
    ('direct soap-forming reaction without byproduct glycerin', 'direct saponification without byproduct glycerin'),
    # "acid-base reaction" -> "neutralization" in body text
    ('acid-base reaction/', 'neutralization/'),
    ('acid-base reaction (', 'neutralization ('),
    # "ester hydrolysis" -> "saponification" in body text context
    ('standalone ester hydrolysis', 'standalone saponification'),
]

restored = 0
for old, new in replacements:
    if old in blog:
        blog = blog.replace(old, new)
        restored += 1
        print(f"[OK] Blog: restored '{new[:60]}'")

if restored == 0:
    # Try alternate forms that may have been used
    # Check for "soap formation" references
    for phrase in ['soap formation', 'acid-base reaction', 'ester hydrolysis']:
        count = blog.count(phrase)
        if count:
            print(f"  Found '{phrase}' x{count} in blog (may need manual review)")

blog_path.write_text(blog, encoding='utf-8', newline='\r\n')
print(f"[OK] Blog file saved ({restored} restorations)")

print("\nTask A complete.")
