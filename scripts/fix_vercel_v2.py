"""
Fix two issues in vercel.json:
1. Move wc-ajax rule from rewrites to redirects (fires before static files)
2. Remove trailingSlash: false so our explicit /our-farms/ redirect fires
"""
import json

with open("vercel.json", "r", encoding="utf-8") as f:
    vj = json.load(f)

# Fix 1: Remove trailingSlash: false
if "trailingSlash" in vj:
    removed_ts = vj.pop("trailingSlash")
    print(f"Removed trailingSlash: {removed_ts}")
else:
    print("trailingSlash not found (already removed)")

# Fix 2: Move wc-ajax rule from rewrites to redirects with statusCode 410
# Remove from rewrites
old_rewrites = vj.get("rewrites", [])
wc_ajax_rewrite = None
new_rewrites = []
for r in old_rewrites:
    has = r.get("has", [])
    is_wc_ajax = any(
        isinstance(h, dict) and h.get("type") == "query" and h.get("key") == "wc-ajax"
        for h in has
    )
    if is_wc_ajax:
        wc_ajax_rewrite = r
        print(f"Found wc-ajax rewrite: {r}")
    else:
        new_rewrites.append(r)

vj["rewrites"] = new_rewrites

# Add to redirects as first entry (before our trailing-slash redirects)
# Use source "/" with has query key, destination /api/gone, statusCode 410
wc_ajax_redirect = {
    "source": "/",
    "has": [{"type": "query", "key": "wc-ajax"}],
    "destination": "/api/gone",
    "statusCode": 410
}

# Check if already exists in redirects
existing_wc_redirects = [
    r for r in vj.get("redirects", [])
    if any(isinstance(h, dict) and h.get("key") == "wc-ajax"
           for h in r.get("has", []))
]
if not existing_wc_redirects:
    vj["redirects"] = [wc_ajax_redirect] + vj.get("redirects", [])
    print("Added wc-ajax to redirects with statusCode 410")
else:
    print(f"wc-ajax already in redirects: {existing_wc_redirects[0]}")
    # Update statusCode if needed
    for r in vj["redirects"]:
        if any(isinstance(h, dict) and h.get("key") == "wc-ajax"
               for h in r.get("has", [])):
            r["statusCode"] = 410
    print("Ensured statusCode=410 on wc-ajax redirect")

with open("vercel.json", "w", encoding="utf-8", newline="\n") as f:
    json.dump(vj, f, indent=2)

print(f"\nDone. trailingSlash removed, wc-ajax moved to redirects with 410")
print(f"Total redirects: {len(vj.get('redirects', []))}")
print(f"Total rewrites: {len(vj.get('rewrites', []))}")

# Validate
json.loads(open("vercel.json").read())
print("vercel.json is valid JSON")
