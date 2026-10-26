import os
import sys
import csv
import re
from datetime import datetime, timezone
from pathlib import Path

AGMARKNET_DIR = Path("seo/data/agmarknet")
INSIGHTS_DIR = Path("insights")
SITEMAP_FILE = Path("sitemap.xml")
LLMS_FILE = Path("llms.txt")

VALID_GUJARAT_MARKETS = [
    "deesa", "palanpur", "tharad", "patan", "dhanera", "visnagar",
    "mehsana", "sidhpur", "bhabhar", "radhanpur", "harij", "panthawada", "diodar", "deodar"
]

def find_agmarknet_csvs():
    if not AGMARKNET_DIR.exists():
        return []
    return sorted(list(AGMARKNET_DIR.glob("**/*.csv")), key=lambda p: p.stat().st_mtime, reverse=True)

def validate_csv(csv_path):
    print(f"Validating Agmarknet export: {csv_path}")
    with open(csv_path, "r", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if not header:
            raise ValueError(f"Empty CSV file: {csv_path}")
            
        header_lower = [h.strip().lower() for h in header]
        
        # Check required columns
        def find_col(candidates):
            for idx, h in enumerate(header_lower):
                if any(c in h for c in candidates):
                    return idx
            return -1

        market_idx = find_col(["market", "mandi"])
        state_idx = find_col(["state"])
        min_idx = find_col(["min", "minimum"])
        max_idx = find_col(["max", "maximum"])
        modal_idx = find_col(["modal"])
        date_idx = find_col(["date", "reported", "arrival"])
        arrivals_idx = find_col(["arrival", "qty", "quantity", "tonnes"])

        if market_idx == -1 or modal_idx == -1 or date_idx == -1:
            raise ValueError(f"CSV missing mandatory columns (market, modal price, date): {header}")

        rows = []
        today = datetime.now(timezone.utc).date()
        
        for r_num, row in enumerate(reader, start=2):
            if not row or not any(row):
                continue
            mkt = row[market_idx].strip()
            
            # State validation if present
            if state_idx != -1 and len(row) > state_idx:
                state_val = row[state_idx].strip().lower()
                if state_val and "gujarat" not in state_val:
                    raise ValueError(f"Row {r_num}: State is '{row[state_idx]}', expected Gujarat")

            # Date validation: parse and ensure strictly <= today
            date_str = row[date_idx].strip()
            parsed_date = None
            for fmt in ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d-%b-%Y", "%d/%b/%Y", "%m/%d/%Y"]:
                try:
                    parsed_date = datetime.strptime(date_str, fmt).date()
                    break
                except ValueError:
                    continue
                    
            if not parsed_date:
                # Try finding date substring
                m = re.search(r"(\d{1,4}[-/]\d{1,2}[-/]\d{1,4})", date_str)
                if m:
                    for fmt in ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"]:
                        try:
                            parsed_date = datetime.strptime(m.group(1), fmt).date()
                            break
                        except ValueError:
                            continue

            if parsed_date and parsed_date > today:
                raise ValueError(f"Row {r_num}: Future-dated transaction {parsed_date} > {today}")

            # Prices
            def parse_price(idx):
                if idx != -1 and len(row) > idx:
                    val = re.sub(r"[^\d.]", "", row[idx])
                    try:
                        return float(val) if val else 0.0
                    except ValueError:
                        return 0.0
                return 0.0

            rows.append({
                "market": mkt,
                "date": date_str,
                "parsed_date": parsed_date,
                "min_price": parse_price(min_idx),
                "max_price": parse_price(max_idx),
                "modal_price": parse_price(modal_idx),
                "arrivals": row[arrivals_idx].strip() if arrivals_idx != -1 and len(row) > arrivals_idx else "—"
            })

        if not rows:
            raise ValueError(f"No valid data rows found in {csv_path}")

        return rows

def generate_page_for_csv(csv_path):
    rows = validate_csv(csv_path)
    
    # Extract Year-Month
    parent_dir = csv_path.parent.name # e.g. "2026-09"
    if re.match(r"^\d{4}-\d{2}$", parent_dir):
        yyyy_mm = parent_dir
    else:
        # Fallback to date from rows
        dates = [r["parsed_date"] for r in rows if r["parsed_date"]]
        if dates:
            yyyy_mm = dates[-1].strftime("%Y-%m")
        else:
            yyyy_mm = datetime.now(timezone.utc).strftime("%Y-%m")

    month_dt = datetime.strptime(yyyy_mm, "%Y-%m")
    month_title = month_dt.strftime("%B %Y")
    download_date = datetime.fromtimestamp(csv_path.stat().st_mtime, tz=timezone.utc).strftime("%d %B %Y")

    slug = f"castor-seed-prices-north-gujarat-{yyyy_mm.lower()}"
    target_html = INSIGHTS_DIR / f"{slug}.html"
    page_url = f"https://www.nagdevproducts.com/insights/{slug}"

    # Calculate statistics
    valid_modals = [r["modal_price"] for r in rows if r["modal_price"] > 0]
    avg_modal = round(sum(valid_modals) / len(valid_modals)) if valid_modals else 0
    min_overall = round(min([r["min_price"] for r in rows if r["min_price"] > 0] or [0]))
    max_overall = round(max([r["max_price"] for r in rows if r["max_price"] > 0] or [0]))

    # Neutral description (<= 150 words, strictly compliant)
    neutral_description = (
        f"Official mandi trading data for castor seed (Ricinus communis) reported across agricultural "
        f"produce market committees (APMC) in North Gujarat, covering Deesa, Palanpur, Tharad, and Patan "
        f"mandis during {month_title}. Prices reflect reported transactions per quintal (100 kg) recorded on "
        f"the national Agmarknet portal under the Directorate of Marketing & Inspection (DMI), Ministry of "
        f"Agriculture and Farmers Welfare, Government of India. Nagdev Products Private Limited monitors regional "
        f"farm-gate mandi arrivals and wholesale price movements to inform industrial crushing schedules and "
        f"feedstock procurement for its manufacturing facility in Deodar, Banaskantha District."
    )

    # Build table rows
    table_rows = []
    for r in rows:
        table_rows.append(
            f"<tr>\n"
            f"  <td><strong>{r['market']}</strong></td>\n"
            f"  <td>{r['date']}</td>\n"
            f"  <td>{r['arrivals']}</td>\n"
            f"  <td>₹{r['min_price']:,.0f}</td>\n"
            f"  <td>₹{r['max_price']:,.0f}</td>\n"
            f"  <td><strong>₹{r['modal_price']:,.0f}</strong></td>\n"
            f"</tr>"
        )
    table_html = "\n".join(table_rows)

    # Standard HTML structure compliant with R13
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>North Gujarat Castor Seed Mandi Prices ({month_title}) | Nagdev</title>
  <meta name="description" content="Official Agmarknet APMC mandi prices and arrival volumes for castor seed across Deesa, Palanpur, Tharad, and Patan for {month_title}.">
  <link rel="canonical" href="{page_url}">

  <!-- Open Graph -->
  <meta property="og:type" content="article">
  <meta property="og:url" content="{page_url}">
  <meta property="og:site_name" content="Nagdev Products Private Limited">
  <meta property="og:title" content="North Gujarat Castor Seed Mandi Prices ({month_title}) | Nagdev Products">
  <meta property="og:description" content="Official Agmarknet APMC mandi prices and arrival volumes for castor seed across Deesa, Palanpur, Tharad, and Patan for {month_title}.">
  <meta property="og:image" content="https://www.nagdevproducts.com/images/og-share.jpg">

  <!-- Fonts & Stylesheet -->
  <link rel="preload" href="/fonts/inter-latin.woff2" as="font" type="font/woff2" crossorigin>
  <link rel="stylesheet" href="/css/main.min.css?v=20261023c">
  <meta name="theme-color" content="#0b3d1e">
  <link rel="icon" href="/favicon.ico" sizes="32x32">
  <link rel="icon" href="/favicon-16x16.png" sizes="16x16" type="image/png">
  <link rel="icon" href="/favicon-32x32.png" sizes="32x32" type="image/png">
  <link rel="apple-touch-icon" href="/apple-touch-icon.png" sizes="180x180">
  <link rel="manifest" href="/site.webmanifest">
  <script src="/js/site-config.min.js" defer></script>

  <!-- Google tag (gtag.js) -->
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-HL3JQ3ZQKF"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){{dataLayer.push(arguments);}}
    gtag('js', new Date());
    gtag('consent', 'default', {{
      'analytics_storage': 'denied',
      'ad_storage': 'denied',
      'ad_user_data': 'denied',
      'ad_personalization': 'denied',
      'wait_for_update': 500
    }});
    gtag('config', 'G-HL3JQ3ZQKF');
  </script>
  <script>
    try {{
      var _c = localStorage.getItem('nagdev_consent');
      if (_c) {{
        var _p = JSON.parse(_c);
        if (_p && _p.timestamp && (Date.now() - _p.timestamp < 31536000000)) {{
          gtag('consent', 'update', {{
            'analytics_storage': _p.choice === 'granted' ? 'granted' : 'denied'
          }});
        }} else {{
          localStorage.removeItem('nagdev_consent');
        }}
      }}
    }} catch(e){{}}
  </script>
  <script defer src="/js/analytics.js"></script>
</head>
<body>
<a href="#main-content" class="skip-to-content">Skip to main content</a>

<!-- TOP INFO BAR -->
<div class="top-bar">
  <div class="container top-bar-inner">
    <div class="top-bar-left">
      <span>📍 Operational Castor Oil &amp; Derivatives Plant · North Gujarat</span>
      <span class="top-bar-ho"> · Head Office: Gandhinagar</span>
    </div>
    <div class="top-bar-right">
      <a href="tel:+916352098306" class="top-bar-link">📞 +91 63520 98306</a>
      <a href="mailto:nagdevproducts@gmail.com" class="top-bar-link top-bar-email">✉️ nagdevproducts@gmail.com</a>
      <a href="https://wa.me/916352098306?text=Hello%20Nagdev%20Products%2C%20I%20would%20like%20to%20enquire%20about%20castor%20procurement." class="top-bar-link top-bar-wa" target="_blank" rel="noopener">💬 WhatsApp</a>
    </div>
  </div>
</div>

<!-- SITE HEADER -->
<header class="site-header" id="site-header">
  <div class="container-wide">
    <div class="header-inner">
      <a href="/" class="header-logo" aria-label="Nagdev Products Home">
        <img src="/images/logo.png" alt="Nagdev Products Private Limited" width="180" height="53">
      </a>
      <nav class="header-nav" aria-label="Main navigation">
        <ul class="nav-list" role="list">
          <li><a href="/" class="nav-link">Home</a></li>
          <li><a href="/products" class="nav-link">Products</a></li>
          <li><a href="/castor-oil-derivatives" class="nav-link">Derivatives</a></li>
          <li><a href="/infrastructure" class="nav-link">Infrastructure</a></li>
          <li><a href="/about" class="nav-link">About</a></li>
          <li><a href="/contact" class="nav-link">Contact</a></li>
        </ul>
      </nav>
    </div>
  </div>
</header>

<main id="main-content">
  <div class="container py-8">
    <nav class="breadcrumb" aria-label="Breadcrumb">
      <ol>
        <li><a href="/">Home</a></li>
        <li><a href="/resources">Resources &amp; Insights</a></li>
        <li aria-current="page">North Gujarat Castor Seed Prices ({month_title})</li>
      </ol>
    </nav>

    <article class="article-body">
      <h1>North Gujarat Castor Seed Mandi Prices ({month_title})</h1>
      <p class="article-meta">Published: {download_date} | Primary Markets: Deesa, Palanpur, Tharad, Patan</p>
      
      <div class="summary-cards" style="display:grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap:1rem; margin: 1.5rem 0;">
        <div class="card" style="padding:1rem; background:#f4f9f4; border:1px solid #c2e0c2; border-radius:6px;">
          <div style="font-size:0.875rem; color:#4a704a;">Average Modal Price</div>
          <div style="font-size:1.5rem; font-weight:700; color:#0b3d1e;">₹{avg_modal:,.0f} / qtl</div>
        </div>
        <div class="card" style="padding:1rem; background:#f4f9f4; border:1px solid #c2e0c2; border-radius:6px;">
          <div style="font-size:0.875rem; color:#4a704a;">Price Range (Min - Max)</div>
          <div style="font-size:1.5rem; font-weight:700; color:#0b3d1e;">₹{min_overall:,.0f} - ₹{max_overall:,.0f}</div>
        </div>
      </div>

      <p>{neutral_description}</p>

      <h2>Reported Mandi Price Data</h2>
      <div class="table-responsive">
        <table class="data-table">
          <thead>
            <tr>
              <th>Market (Mandi)</th>
              <th>Reported Date</th>
              <th>Arrivals</th>
              <th>Min Price (₹/qtl)</th>
              <th>Max Price (₹/qtl)</th>
              <th>Modal Price (₹/qtl)</th>
            </tr>
          </thead>
          <tbody>
{table_html}
          </tbody>
        </table>
      </div>

      <p class="source-note" style="margin-top:1.5rem; font-size:0.875rem; color:#666;">
        <em>Source: Agmarknet, {download_date}, owner-downloaded export. Data reflects official agricultural market records under the Directorate of Marketing &amp; Inspection (DMI).</em>
      </p>
    </article>
  </div>
</main>

<!-- FOOTER -->
<footer class="site-footer">
  <div class="container">
    <div class="footer-bottom">
      <p>© {datetime.now().year} Nagdev Products Private Limited. All rights reserved. Registered Plant: Survey No. 40, Village Kotda, Taluka Deodar, District Banaskantha, Gujarat 385330.</p>
    </div>
  </div>
</footer>
</body>
</html>
"""
    INSIGHTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(target_html, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Generated market page: {target_html}")

    # Update sitemap.xml
    if SITEMAP_FILE.exists():
        sitemap_text = SITEMAP_FILE.read_text(encoding="utf-8")
        if page_url not in sitemap_text:
            new_entry = f"  <url>\n    <loc>{page_url}</loc>\n    <changefreq>monthly</changefreq>\n    <priority>0.7</priority>\n  </url>\n"
            sitemap_text = sitemap_text.replace("</urlset>", f"{new_entry}</urlset>")
            SITEMAP_FILE.write_text(sitemap_text, encoding="utf-8")
            print(f"Added {page_url} to sitemap.xml")

    # Update llms.txt
    if LLMS_FILE.exists():
        llms_text = LLMS_FILE.read_text(encoding="utf-8")
        if page_url not in llms_text:
            entry = f"- [North Gujarat Castor Seed Prices ({month_title})]({page_url}): Official Agmarknet mandi prices for {month_title} across Deesa, Palanpur, Tharad, and Patan.\n"
            llms_text += f"\n{entry}"
            LLMS_FILE.write_text(llms_text, encoding="utf-8")
            print(f"Added {page_url} to llms.txt")

    return {
        "slug": slug,
        "page_url": page_url,
        "month_title": month_title,
        "file_path": str(target_html)
    }

def main():
    csv_files = find_agmarknet_csvs()
    if not csv_files:
        print("No CSV files found in seo/data/agmarknet/**. Exiting cleanly.")
        return 0

    latest_csv = csv_files[0]
    result = generate_page_for_csv(latest_csv)
    print(f"Successfully processed {latest_csv.name} -> {result['page_url']}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
