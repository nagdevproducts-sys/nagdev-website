import json

with open("vercel.json", "r", encoding="utf-8") as f:
    vj = json.load(f)

redirects = vj["redirects"]

priority = [
    {"source": "/our-farms/", "destination": "/plant", "statusCode": 301},
    {"source": "/exhibitions/", "destination": "/about", "statusCode": 301},
    {"source": "/awards/", "destination": "/about", "statusCode": 301},
    {"source": "/photo-gallery/", "destination": "/about", "statusCode": 301},
]

priority_sources = {r["source"] for r in priority}
redirects = [r for r in redirects if r.get("source") not in priority_sources]
redirects = priority + redirects
vj["redirects"] = redirects

with open("vercel.json", "w", encoding="utf-8", newline="\n") as f:
    json.dump(vj, f, indent=2)

print(f"Done. Total redirects: {len(redirects)}")
print("First 6 redirects:")
for r in redirects[:6]:
    print(f"  {r.get('source')} -> {r.get('destination')} [{r.get('statusCode')}]")
