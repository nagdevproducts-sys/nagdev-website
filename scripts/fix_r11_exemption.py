"""
Fix: add 'neutralisation' key to phrase_path_exemptions so R11 banned_proc_patterns
exemption works for glossary/acid-value.html (proc_name.split('/')[0] = 'neutralisation').
"""
import json
from pathlib import Path

fr_path = Path('seo/facts-register.json')
fr = json.loads(fr_path.read_text(encoding='utf-8'))

ppe = fr.setdefault('phrase_path_exemptions', {})

# Add 'neutralisation' (the split key the linter uses from proc_name 'neutralisation/neutralization')
# for both glossary/acid-value.html and the blog
if 'neutralisation' not in ppe:
    ppe['neutralisation'] = [
        "glossary/acid-value.html",
        "blog/hydrogenated-castor-oil-in-lithium-grease-formulation.html"
    ]
    print("[OK] Added 'neutralisation' exemption key")
else:
    print("[SKIP] 'neutralisation' already present")

# Also ensure 'neutralise' is covered (R11_BANNED_PHRASES may also catch it via check_r11_banned_phrases)
if 'neutralise' not in ppe:
    ppe['neutralise'] = ["glossary/acid-value.html"]
    print("[OK] Added 'neutralise' exemption key")
else:
    print("[SKIP] 'neutralise' already present")

fr_path.write_text(json.dumps(fr, indent=2, ensure_ascii=False), encoding='utf-8')
print("[OK] facts-register.json updated")
