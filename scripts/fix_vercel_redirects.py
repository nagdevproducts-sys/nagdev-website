import json

with open('vercel.json') as f:
    v = json.load(f)

# Fix 1: Replace permanent:true with statusCode:301 on all redirects
for r in v['redirects']:
    if r.get('permanent') is True:
        del r['permanent']
        r['statusCode'] = 301

# Fix 2: Remove trailing-slash duplicates from rewrites
# (Vercel's trailingSlash:false normalises before rewrites run, so /product/rye/ → 308 then rewrite)
rewrites = v.get('rewrites', [])
cleaned = []
for r in rewrites:
    src = r.get('source', '')
    # Remove specific trailing-slash entries (not wildcards)
    # Wildcards like /product/:slug* are fine
    if src.endswith('/') and '/:slug*' not in src and ':slug*' not in src and src != '/':
        pass  # skip trailing-slash specific entries
    else:
        cleaned.append(r)

v['rewrites'] = cleaned

with open('vercel.json', 'w') as f:
    json.dump(v, f, indent=2)

print("Redirects:", len(v['redirects']))
print("Rewrites:", len(cleaned))
# Check sample
for r in v['redirects']:
    if 'our-farms' in r.get('source', ''):
        print("our-farms redirect:", r)
        break
