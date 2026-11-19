"""
Fix vercel.json: Move wc-ajax rule to beforeFiles rewrites so it fires before index.html is served.
Also remove the wc-ajax redirect (statusCode 410 is invalid for Vercel redirects).
"""
import json

with open("vercel.json", "r", encoding="utf-8") as f:
    vj = json.load(f)

# Remove invalid wc-ajax redirect (410 is not a valid Vercel redirect statusCode)
redirects = vj.get("redirects", [])
redirects = [
    r for r in redirects
    if not any(
        isinstance(h, dict) and h.get("key") == "wc-ajax"
        for h in r.get("has", [])
    )
]
vj["redirects"] = redirects
print(f"Cleaned redirects: {len(redirects)}")

# Current rewrites (afterFiles array)
current_rewrites = vj.get("rewrites", [])
# Separate wc-ajax rule out (it needs to be beforeFiles)
after_files = [r for r in current_rewrites
               if not any(isinstance(h, dict) and h.get("key") == "wc-ajax"
                         for h in r.get("has", []))]

# beforeFiles rewrite: wc-ajax query string -> /api/gone (which returns 410)
before_files = [
    {
        "source": "/",
        "has": [{"type": "query", "key": "wc-ajax"}],
        "destination": "/api/gone"
    }
]

# Replace rewrites with beforeFiles/afterFiles structure
vj["rewrites"] = {
    "beforeFiles": before_files,
    "afterFiles": after_files
}

print(f"beforeFiles rewrites: {len(before_files)}")
print(f"afterFiles rewrites: {len(after_files)}")

with open("vercel.json", "w", encoding="utf-8", newline="\n") as f:
    json.dump(vj, f, indent=2)

json.loads(open("vercel.json").read())
print("vercel.json is valid JSON")

# Show first redirect to confirm order
print(f"\nFirst 2 redirects:")
for r in vj["redirects"][:2]:
    print(f"  {r.get('source')} -> {r.get('destination')} [{r.get('statusCode')}]")
