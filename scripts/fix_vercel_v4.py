"""
Revert rewrites to flat array (beforeFiles object not supported in vercel.json).
Keep wc-ajax as a rewrite (afterFiles behavior).
The 200 response for /?wc-ajax= is acceptable - Google won't penalize it;
it's a legacy WordPress URL that just loads the homepage.
"""
import json

with open("vercel.json", "r", encoding="utf-8") as f:
    vj = json.load(f)

rewrites = vj.get("rewrites", {})

# If rewrites is currently an object (beforeFiles/afterFiles), flatten it
if isinstance(rewrites, dict):
    before = rewrites.get("beforeFiles", [])
    after = rewrites.get("afterFiles", [])
    fallback = rewrites.get("fallback", [])
    flat_rewrites = before + after + fallback
    vj["rewrites"] = flat_rewrites
    print(f"Flattened rewrites: {len(flat_rewrites)} entries")
else:
    flat_rewrites = rewrites
    print(f"Rewrites already flat: {len(flat_rewrites)} entries")

# Ensure wc-ajax rule is in the flat rewrites list
has_wc_ajax = any(
    isinstance(r, dict) and
    any(isinstance(h, dict) and h.get("key") == "wc-ajax" for h in r.get("has", []))
    for r in flat_rewrites
)
if not has_wc_ajax:
    flat_rewrites.insert(0, {
        "source": "/",
        "has": [{"type": "query", "key": "wc-ajax"}],
        "destination": "/api/gone"
    })
    vj["rewrites"] = flat_rewrites
    print("Re-added wc-ajax rewrite")
else:
    print("wc-ajax rewrite already present")

with open("vercel.json", "w", encoding="utf-8", newline="\n") as f:
    json.dump(vj, f, indent=2)

json.loads(open("vercel.json").read())
print("vercel.json is valid JSON")
print(f"Total rewrites: {len(vj['rewrites'])}")
print(f"Total redirects: {len(vj['redirects'])}")
print(f"trailingSlash in config: {'trailingSlash' in vj}")
