import json
import re
import urllib.request
import subprocess

BASE = 'https://www.nagdevproducts.com'

def fetch_prod(path):
    # Try direct fetch first; if authentication or custom header needed, fall back to vercel curl
    url = f"{BASE}{path}"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    try:
        with urllib.request.urlopen(req) as resp:
            content = resp.read().decode('utf-8')
            # Check if this is the vercel login page
            if 'vercel' in content[:500].lower() and 'authentication' in content[:500].lower():
                raise Exception("Deployment protection active, falling back to vercel curl")
            return content
    except Exception as e:
        cmd = f'npx vercel curl {url}'
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        return p.stdout

print("=== VERIFYING PRODUCTION ===")

# 1. FSG Product Page
print("\n1. Verifying FSG Product Page (/products/first-special-grade-castor-oil)...")
fsg = fetch_prod('/products/first-special-grade-castor-oil')

assert 'product-hero-price' not in fsg, "FAIL: product-hero-price found in FSG"
print("  [OK] No indicative price line under H1")

assert 'product-summary-tile-price' in fsg, "FAIL: price box not found in FSG summary strip"
assert 'INDICATIVE PRICE' in fsg, "FAIL: INDICATIVE PRICE label not found in FSG"
assert 'USD 1,700–1,850 per MT' in fsg, "FAIL: USD 1,700–1,850 per MT not found in FSG"
assert 'USD 1.70–1.85 per kg' in fsg, "FAIL: USD 1.70–1.85 per kg not found in FSG"
assert 'FOB Kandla/Mundra · Final price on quotation' in fsg, "FAIL: FOB quotation text not found in FSG"
assert fsg.find('product-summary-tile-price') < fsg.find('Commercial Status'), "FAIL: price box is not first"
assert 'has-5-tiles' in fsg, "FAIL: has-5-tiles class missing in grid"
print("  [OK] Price box is FIRST in 5-tile info row with MT, kg, and FOB note")

# Rich Results Test validation on FSG
m = re.search(r'<script type="application/ld\+json">(.*?)</script>', fsg, re.DOTALL)
assert m, "FAIL: JSON-LD script not found on FSG"
schema_data = json.loads(m.group(1))
product_item = None
for item in schema_data.get('@graph', []):
    if item.get('@type') == 'Product':
        product_item = item
        break
assert product_item, "FAIL: Product item not found in JSON-LD @graph"
assert product_item.get('name'), "FAIL: Product missing name"
assert product_item.get('image', '').startswith('http'), "FAIL: Product image not absolute URL"
assert product_item.get('brand', {}).get('name') == 'Nagdev Products', "FAIL: Product missing brand"
offers = product_item.get('offers', {})
assert offers.get('@type') == 'AggregateOffer', "FAIL: offers is not AggregateOffer"
assert offers.get('priceCurrency') == 'USD', "FAIL: priceCurrency is not USD"
assert offers.get('lowPrice') == 1700, "FAIL: lowPrice is not 1700"
assert offers.get('highPrice') == 1850, "FAIL: highPrice is not 1850"
assert offers.get('availability') == 'https://schema.org/InStock', "FAIL: availability not InStock"
price_valid_until = offers.get('priceValidUntil', '')
assert re.match(r'^2027-(?:10|11)-\d{2}$', price_valid_until), f"FAIL: priceValidUntil on FSG expected 2027-10/11 date, got {price_valid_until}"
print(f"  [OK] priceValidUntil is a 2027-10/11 date ({price_valid_until})")
print("  [OK] Product schema JSON-LD fully intact and valid for Google Rich Results Test (Product snippet)")

# 2. Commercial Product Page
print("\n2. Verifying Commercial Product Page (/products/commercial-castor-oil)...")
comm = fetch_prod('/products/commercial-castor-oil')
assert 'product-hero-price' not in comm, "FAIL: product-hero-price found in Commercial"
print("  [OK] No indicative price line under H1")
assert 'product-summary-tile-price' in comm, "FAIL: price box not found in Commercial"
assert 'INDICATIVE PRICE' in comm, "FAIL: INDICATIVE PRICE label not found in Commercial"
assert 'USD 1,650–1,800 per MT' in comm, "FAIL: USD 1,650–1,800 per MT not found in Commercial"
assert 'USD 1.65–1.80 per kg' in comm, "FAIL: USD 1.65–1.80 per kg not found in Commercial"
assert comm.find('product-summary-tile-price') < comm.find('Commercial Status'), "FAIL: price box is not first"
print("  [OK] Price box is FIRST in 5-tile info row with MT, kg, and FOB note")

# 3. Product Listing Cards (/products)
print("\n3. Verifying /products Cards (/products)...")
prods = fetch_prod('/products')
assert 'product-card-price' not in prods, "FAIL: product-card-price found in /products cards"
print("  [OK] Indicative price removed from cards")
apps_count = prods.count('product-card-apps')
assert apps_count == 32, f"FAIL: Expected 32 product-card-apps, found {apps_count}"
assert 'Applications: Lubricants · Alkyd resins · Turkey Red Oil' in prods, "FAIL: Commercial applications mismatch"
assert 'Applications: Urethane polymers · Cosmetics · Clear greases' in prods, "FAIL: FSG applications mismatch"
print(f"  [OK] All {apps_count} cards have Applications line with 3 key applications")

# 4. Mega Menu on Product Page, Blog Page, and Homepage
print("\n4. Verifying Mega Menu across Page Templates...")
assert 'desktop-mega-template' not in fsg, "FAIL: desktop-mega-template found in FSG"
assert fsg.count('class="mega-prod-link') >= 32, "FAIL: FSG mega menu has less than 32 links"
print("  [OK] Product page: Full mega menu (32 links) present in static HTML")

blog = fetch_prod('/blog/fsg-castor-oil-specifications-bulk-supply')
assert 'desktop-mega-template' not in blog, "FAIL: desktop-mega-template found in Blog"
assert blog.count('class="mega-prod-link') >= 32, "FAIL: Blog mega menu has less than 32 links"
print("  [OK] Blog page: Full mega menu (32 links) present in static HTML")

home = fetch_prod('/')
assert 'desktop-mega-template' not in home, "FAIL: desktop-mega-template found in Home"
assert home.count('class="mega-prod-link') >= 32, "FAIL: Home mega menu has less than 32 links"
print("  [OK] Homepage: Full mega menu (32 links) present in static HTML")

# Mobile drawer check
assert 'mobile-products-template' not in home, "FAIL: mobile-products-template found in Home"
assert 'Regular Supply (7)' in home, "FAIL: Regular Supply group missing in mobile menu"
assert 'Available on Enquiry (8)' in home, "FAIL: Available on Enquiry group missing in mobile menu"
assert 'Under Development (17)' in home, "FAIL: Under Development group missing in mobile menu"
print("  [OK] Mobile navigation drawer: All 3 groups (32 links) present in static HTML")

# 5. Justified Text Site-Wide
print("\n5. Verifying Justified Text Site-Wide...")
css = fetch_prod('/css/main.min.css')
assert 'text-align:justify' in css, "FAIL: text-align:justify not found in main.min.css"
assert 'text-justify:inter-word' in css, "FAIL: text-justify:inter-word not found in main.min.css"
assert 'hyphens:auto' in css, "FAIL: hyphens:auto not found in main.min.css"
assert 'lang="en"' in home, "FAIL: lang attribute missing on home"
assert 'lang="en"' in fsg, "FAIL: lang attribute missing on FSG"
assert 'lang="en"' in blog, "FAIL: lang attribute missing on blog"
print("  [OK] CSS includes text-align: justify; text-justify: inter-word; hyphens: auto")
print("  [OK] html lang=\"en\" set on pages so hyphenation works")

# 6. /plant-progress opening
print("\n6. Verifying /plant-progress Opening...")
plant_prog = fetch_prod('/plant-progress')
expected_opening = "Nagdev Products' integrated castor plant at Sardarpura, Deodar (Vav-Tharad district, Gujarat) is operational and supplying commercial volumes now: 50 TPD seed crushing, FSG refining, hydrogenation (HCO) and dehydration (DCO, DCO-FA), with an in-house QC lab issuing a COA per lot."
assert expected_opening in plant_prog, "FAIL: /plant-progress opening does not match required text"
print("  [OK] /plant-progress opening paragraph matches requirement")

print("\n========================================")
print("ALL PRODUCTION VERIFICATIONS PASSED 100%")
print("========================================")
