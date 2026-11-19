import os
import json
import re

ORG_NODE = {
  "@type": ["Organization", "LocalBusiness"],
  "@id": "https://www.nagdevproducts.com/#organization",
  "name": "Nagdev Products Private Limited",
  "legalName": "Nagdev Products Private Limited",
  "url": "https://www.nagdevproducts.com/",
  "logo": {
    "@type": "ImageObject",
    "url": "https://www.nagdevproducts.com/images/logo-dark.webp",
    "width": 165,
    "height": 48
  },
  "image": "https://www.nagdevproducts.com/images/og-share.jpg",
  "description": "Castor oil manufacturer and exporter in North Gujarat, India. 50 TPD expeller plant in Deodar, Vav-Tharad supplying FSG, PPG, HCO, DCO and derivatives worldwide.",
  "telephone": "+91-6352098306",
  "email": "nagdevproducts@gmail.com",
  "address": {
    "@type": "PostalAddress",
    "streetAddress": "Survey No. 301 P-2, Sardarpura",
    "addressLocality": "Deodar",
    "addressRegion": "Gujarat",
    "postalCode": "385330",
    "addressCountry": "IN"
  },
  "geo": {
    "@type": "GeoCoordinates",
    "latitude": 24.1817,
    "longitude": 71.8311
  },
  "sameAs": [
    "https://www.facebook.com/nagdevproducts",
    "https://www.instagram.com/nagdev.products",
    "https://www.linkedin.com/company/nagdevproducts"
  ],
  "contactPoint": {
    "@type": "ContactPoint",
    "telephone": "+91-6352098306",
    "contactType": "sales",
    "email": "nagdevproducts@gmail.com",
    "availableLanguage": ["English", "Hindi", "Gujarati"]
  },
  "foundingDate": "2019",
  "numberOfEmployees": {
    "@type": "QuantitativeValue",
    "minValue": 20,
    "maxValue": 50
  },
  "currenciesAccepted": "USD, INR",
  "openingHours": "Mo-Sa 09:00-18:00",
  "priceRange": "$$"
}

# Product data map for the 17 dev products and any others
def get_product_node(slug, html_content):
    # Extract name from H1 or Title
    h1_m = re.search(r'<h1[^>]*>(.*?)</h1>', html_content, re.DOTALL)
    title_m = re.search(r'<title>(.*?)</title>', html_content)
    desc_m = re.search(r'<meta name="description" content="(.*?)">', html_content)
    
    name = h1_m.group(1).strip() if h1_m else (title_m.group(1).split('|')[0].strip() if title_m else slug)
    name = re.sub(r'<[^>]+>', '', name).strip()
    
    desc = desc_m.group(1).strip() if desc_m else f"{name} manufactured and supplied by Nagdev Products from Gujarat, India."
    
    return {
      "@type": "Product",
      "@id": f"https://www.nagdevproducts.com/products/{slug}#product",
      "name": name,
      "description": desc,
      "brand": {
        "@type": "Brand",
        "name": "Nagdev Products"
      },
      "manufacturer": {
        "@type": "Organization",
        "name": "Nagdev Products Private Limited"
      },
      "offers": {
        "@type": "Offer",
        "availability": "https://schema.org/InStock",
        "url": f"https://www.nagdevproducts.com/products/{slug}",
        "seller": {
          "@type": "Organization",
          "name": "Nagdev Products Private Limited"
        },
        "priceCurrency": "USD",
        "priceSpecification": {
          "@type": "PriceSpecification",
          "priceCurrency": "USD",
          "description": "Price on request"
        }
      }
    }

def update_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Skip 404, redirect stubs, templates, admin
    basename = os.path.basename(file_path)
    if basename in ['404.html', 'blog-admin.html', 'castor-cake-fertilizer.html', 'de-oiled-cake-castor-meal.html', 'site_footer.html', 'site_header.html']:
        return False, "Skipped special file"

    is_product_page = 'products' in file_path.replace('\\', '/').split('/')
    slug = os.path.splitext(basename)[0]

    # Find JSON-LD scripts
    matches = list(re.finditer(r'<script type=["\']application/ld\+json["\']>(.*?)</script>', content, re.DOTALL))
    
    changed = False

    if not matches:
        # No JSON-LD in this page yet, inject into <head>
        new_data = {
            "@context": "https://schema.org",
            "@graph": [dict(ORG_NODE)]
        }
        if is_product_page:
            new_data["@graph"].append(get_product_node(slug, content))
        
        json_str = json.dumps(new_data, indent=2, ensure_ascii=False)
        tag = f'\n  <script type="application/ld+json">\n{json_str}\n  </script>'
        if '</head>' in content:
            content = content.replace('</head>', f'{tag}\n</head>')
            changed = True
    else:
        # Update existing JSON-LD
        # Usually there's one primary application/ld+json script with @graph
        # Let's parse all JSON-LD blocks
        for m in matches:
            raw_json = m.group(1).strip()
            try:
                data = json.loads(raw_json)
            except Exception as e:
                print(f"Error parsing JSON in {file_path}: {e}")
                continue

            has_graph = "@graph" in data
            items = data.get("@graph", [data])
            
            # Check for Organization node
            org_indices = [i for i, x in enumerate(items) if x.get("@type") == "Organization" or (isinstance(x.get("@type"), list) and "Organization" in x.get("@type")) or x.get("@id", "").endswith("#organization")]
            
            if org_indices:
                for idx in org_indices:
                    # Update fields while preserving specific custom properties if any
                    existing = items[idx]
                    merged = dict(ORG_NODE)
                    # Preserve identifier if existing has it
                    if "identifier" in existing:
                        merged["identifier"] = existing["identifier"]
                    items[idx] = merged
                    changed = True
            else:
                # Add organization node to graph if this is the main ld+json script
                if has_graph:
                    items.insert(0, dict(ORG_NODE))
                    changed = True

            # If product page, check for Product node
            if is_product_page:
                prod_indices = [i for i, x in enumerate(items) if x.get("@type") == "Product"]
                if not prod_indices:
                    # Add Product node
                    prod_node = get_product_node(slug, content)
                    items.append(prod_node)
                    changed = True
                    # Also check if WebPage node had mpn incorrectly
                    for item in items:
                        if item.get("@type") == "WebPage" and "mpn" in item:
                            del item["mpn"]
                else:
                    # Validate existing product offers
                    p = items[prod_indices[0]]
                    offers = p.get("offers")
                    if not offers:
                        p["offers"] = {
                            "@type": "Offer",
                            "availability": "https://schema.org/InStock",
                            "url": f"https://www.nagdevproducts.com/products/{slug}",
                            "seller": {
                              "@type": "Organization",
                              "name": "Nagdev Products Private Limited"
                            },
                            "priceCurrency": "USD",
                            "priceSpecification": {
                              "@type": "PriceSpecification",
                              "priceCurrency": "USD",
                              "description": "Price on request"
                            }
                        }
                        changed = True
                    else:
                        # Ensure seller & priceSpecification are valid
                        if offers.get("price") in [0, "0"]:
                            del offers["price"]
                            offers["priceSpecification"] = {
                              "@type": "PriceSpecification",
                              "priceCurrency": "USD",
                              "description": "Price on request"
                            }
                            changed = True

            if has_graph:
                data["@graph"] = items
            else:
                if len(items) == 1:
                    data = items[0]
                else:
                    data = {"@context": "https://schema.org", "@graph": items}

            new_json_str = json.dumps(data, indent=2, ensure_ascii=False)
            content = content[:m.start(1)] + "\n" + new_json_str + "\n" + content[m.end(1):]
            break

    if changed:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True, "Updated"
    return False, "No change"

if __name__ == '__main__':
    html_files = []
    for root, dirs, files in os.walk('.'):
        if any(p in root for p in ['node_modules', '.vercel', 'scratch', '.git']):
            continue
        for f in files:
            if f.endswith('.html'):
                html_files.append(os.path.normpath(os.path.join(root, f)))

    updated_count = 0
    for f in sorted(html_files):
        success, msg = update_file(f)
        if success:
            updated_count += 1
            print(f"Updated: {f}")

    print(f"\nDone! Total files updated: {updated_count} / {len(html_files)}")
