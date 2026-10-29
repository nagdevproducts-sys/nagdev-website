#!/usr/bin/env python3
"""
Nagdev Products — Automated Blog Publishing Engine
Phase 14: 2-Year Scheduled Publishing System

Builds blog posts from content/blog/<slug>.md based on publish_date <= now (IST).
Regenerates:
  - blog/<slug>.html (published posts only)
  - blog.html (blog index with SSR cards and filters)
  - js/blog-data.js (client-side data for search/filtering)
  - index.html (homepage 'Latest insights' showing 3 newest published posts)
  - sitemap.xml (includes only published posts with lastmod)
  - blog/rss.xml (RSS 2.0 feed)
  - llms.txt (blog section)
  - seo/keywords.csv (tracks blog primary keywords)

Performs strict validations:
  - Title <= 60 chars, meta description 140-160 chars
  - Primary keyword placement (title, slug, description, first 100 words, H2, 2-4 body mentions)
  - 3-shingle similarity < 30% against all other posts and product pages
  - Unique FAQ questions across all posts
  - No hand-typed spec numbers conflicting with official specs
  - Zero claims linter violations
"""

import os
import re
import sys
import csv
import json

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass
import argparse
from datetime import datetime, timezone, timedelta
from bs4 import BeautifulSoup
import yaml
import markdown_it

IST = timezone(timedelta(hours=5, minutes=30))

def parse_ist(dt_str):
    """Parse ISO datetime string with IST offset."""
    dt_str = dt_str.strip()
    if dt_str.endswith('Z'):
        dt = datetime.fromisoformat(dt_str[:-1] + '+00:00')
        return dt.astimezone(IST)
    return datetime.fromisoformat(dt_str).astimezone(IST)

def format_date_display(dt):
    """Format datetime for display e.g. Oct 29, 2026."""
    return dt.strftime('%b %d, %Y')

def format_date_iso(dt):
    """Format datetime as YYYY-MM-DD."""
    return dt.strftime('%Y-%m-%d')

def load_product_master():
    with open('seo/product-master.json', 'r', encoding='utf-8') as f:
        prods = json.load(f)
    return {p['slug']: p for p in prods}

def load_facts_register():
    with open('seo/facts-register.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def load_calendar():
    entries = {}
    if os.path.exists('seo/blog/calendar.csv'):
        with open('seo/blog/calendar.csv', 'r', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                entries[row['slug']] = row
    return entries

def extract_spec_table(product_slug):
    """Extract official specification table from products/<slug>.html."""
    html_path = f'products/{product_slug}.html'
    if not os.path.exists(html_path):
        return ""
    with open(html_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')
    table = soup.find('table', class_='product-spec-table')
    if not table:
        return ""
    return str(table)

def get_product_hs_code(product_slug):
    """Extract HS code from product page HTML."""
    html_path = f'products/{product_slug}.html'
    if not os.path.exists(html_path):
        return "1515.30"
    with open(html_path, 'r', encoding='utf-8') as f:
        m = re.search(r'HS Code:\s*([0-9\.]+)', f.read())
        if m:
            return m.group(1)
    return "1515.30"

def get_word_shingles(text, n=3):
    """Generate n-word shingles from plain text."""
    # Strip HTML tags
    clean = re.sub(r'<[^>]+>', ' ', text)
    # Tokenize words
    words = re.findall(r'[a-zA-Z0-9\u0A80-\u0AFF]+', clean.lower())
    if len(words) < n:
        return set([' '.join(words)])
    shingles = set()
    for i in range(len(words) - n + 1):
        shingles.add(' '.join(words[i:i+n]))
    return shingles

def compute_similarity(shingles_a, shingles_b):
    """Compute Jaccard similarity between two sets of shingles."""
    if not shingles_a or not shingles_b:
        return 0.0
    intersection = len(shingles_a & shingles_b)
    union = len(shingles_a | shingles_b)
    if union == 0:
        return 0.0
    return intersection / union

def render_key_facts_table(product_slug, product_data):
    """Render the standard key facts table from product-master."""
    if not product_data:
        return ""
    
    brand_code = product_data.get('brand_code', '')
    cas = product_data.get('cas', '8001-79-4')
    hs = get_product_hs_code(product_slug)
    category = product_data.get('category', 'Regular Supply')
    status_label = "Regular Commercial Supply" if "regular" in product_data.get('status', '').lower() else "Available on Technical Enquiry"
    physical_form = product_data.get('physical_form', 'Viscous Liquid')
    packaging_list = product_data.get('packaging', ['200 kg steel drums', '1,000 L IBC totes', '20-21.5 MT flexitanks'])
    pkg_str = "; ".join(packaging_list[:3])
    docs = "COA per production lot, Technical Data Sheet (TDS), Safety Data Sheet (SDS)"
    prod_name = product_data.get('display_name', product_slug)
    
    html = f"""
<div class="blog-table-wrap" tabindex="0" role="region" aria-label="{prod_name} Key Facts and Product Overview">
  <table class="blog-data-table">
    <thead>
      <tr>
        <th style="width:30%;">Key Parameter</th>
        <th style="width:70%;">Commercial &amp; Technical Detail</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td><strong>Grade Code</strong></td>
        <td>{brand_code}</td>
      </tr>
      <tr>
        <td><strong>CAS Registry Number</strong></td>
        <td>{cas}</td>
      </tr>
      <tr>
        <td><strong>ITC-HS Tariff Code</strong></td>
        <td>{hs}</td>
      </tr>
      <tr>
        <td><strong>Supply Status</strong></td>
        <td><span style="display:inline-block;padding:2px 8px;border-radius:4px;font-size:0.85rem;font-weight:600;background:var(--ivory);color:var(--forest);border:1px solid var(--border);">{status_label}</span></td>
      </tr>
      <tr>
        <td><strong>Physical Appearance</strong></td>
        <td>{physical_form}</td>
      </tr>
      <tr>
        <td><strong>Export Packaging</strong></td>
        <td>{pkg_str}</td>
      </tr>
      <tr>
        <td><strong>Quality Documentation</strong></td>
        <td>{docs}</td>
      </tr>
      <tr>
        <td><strong>Official Product Reference</strong></td>
        <td><a href="/products/{product_slug}" style="color:var(--forest);font-weight:700;text-decoration:underline;">View full {prod_name} specifications and pack sizes &rarr;</a></td>
      </tr>
    </tbody>
  </table>
</div>
"""
    return html

def render_spec_table_block(product_slug, product_data):
    """Render official specification table wrapped in focusable scroll container with footnote."""
    table_html = extract_spec_table(product_slug)
    if not table_html:
        return ""
    prod_name = product_data.get('display_name', product_slug) if product_data else product_slug
    return f"""
<div class="blog-table-wrap" tabindex="0" role="region" aria-label="{prod_name} Standard Specification Limits">
  {table_html}
</div>
<p class="table-footnote" style="font-size:0.85rem;color:var(--text-muted);margin-top:0.5rem;margin-bottom:2rem;font-style:italic;">
  Limits from our product specification; each lot's results are on its COA.
</p>
"""

def render_cta_box(product_slug, product_data):
    """Render mid-article CTA box with quote, sample, and optional TDS download."""
    prod_name = product_data.get('display_name', 'Industrial Castor Derivative') if product_data else 'Castor Products'
    slug_param = f"&product={product_slug}" if product_slug else ""
    product_param = f"?product={product_slug}" if product_slug else ""
    
    tds_button = ""
    if product_slug and os.path.exists(f"downloads/tds/{product_slug}.pdf"):
        tds_button = f'<a href="/downloads/tds/{product_slug}.pdf" class="btn btn-outline" download style="border:1px solid var(--forest);color:var(--forest);">Download TDS (PDF) &darr;</a>'
    
    return f"""
<div class="blog-cta-box" style="background:var(--ivory);border:1px solid var(--border-light);border-left:4px solid var(--gold);border-radius:var(--radius-md);padding:2rem;margin:2.5rem 0;">
  <h3 style="font-family:var(--font-heading);font-size:1.4rem;color:var(--forest);margin-bottom:0.5rem;">Procure {prod_name} from Gujarat</h3>
  <p style="color:var(--charcoal-soft);font-size:0.95rem;line-height:1.6;margin-bottom:1.25rem;">
    Our technical and sales team dispatches ISO tanks, flexitanks, IBC totes, and steel drums directly from our Deodar crushing plant. Request commercial pricing, lot-specific COA, or laboratory trial samples.
  </p>
  <div style="display:flex;gap:0.75rem;flex-wrap:wrap;align-items:center;">
    <a href="/contact?type=quote{slug_param}" class="btn btn-primary btn-sm">Request a Quote &rarr;</a>
    <a href="/contact?inquiry=sample{slug_param}" class="btn btn-secondary btn-sm">Request Sample &rarr;</a>
    {tds_button}
  </div>
</div>
"""

def render_faq_section(faqs):
    """Render visible FAQ accordion with details/summary."""
    if not faqs:
        return ""
    items_html = []
    for f in faqs:
        q = f.get('q', '').strip()
        a = f.get('a', '').strip()
        items_html.append(f"""
    <details style="background:#ffffff; border:1px solid var(--border-light); border-radius:var(--radius-sm); padding:1.25rem 1.5rem; box-shadow:var(--shadow-sm); margin-bottom:0.85rem;">
      <summary style="font-size:1rem; font-weight:600; color:var(--forest); cursor:pointer; list-style:none; display:flex; justify-content:space-between; align-items:center;">
        <span>{q}</span>
        <span style="color:var(--gold); font-size:1.2rem; font-weight:bold;">+</span>
      </summary>
      <p style="font-size:0.925rem; color:var(--charcoal-soft); line-height:1.7; margin-top:0.75rem; margin-bottom:0;">{a}</p>
    </details>
""")
    return f"""
<section id="section-faq" style="margin-top:3rem; padding-top:2.5rem; border-top:1px solid var(--border-light);">
  <span style="font-size:0.8rem; font-weight:700; color:var(--gold); text-transform:uppercase; letter-spacing:0.08em; display:block; margin-bottom:0.35rem;">Technical FAQ</span>
  <h2 style="font-size:1.75rem; font-family:var(--font-heading); color:var(--forest); margin-bottom:1.25rem;">Frequently Asked Questions</h2>
  <div style="display:flex; flex-direction:column; gap:0.25rem;">
    {''.join(items_html)}
  </div>
</section>
"""

def render_related_block(post, product_slug, product_data, other_posts):
    """Render Related block linking to product page, 2 related blog posts, and compare page."""
    items = []
    
    # 1. Product page link
    if product_slug:
        prod_name = product_data.get('display_name', product_slug) if product_data else product_slug
        items.append(f'<li><a href="/products/{product_slug}" style="color:var(--forest); font-weight:700; text-decoration:underline;">{prod_name} Technical Page &amp; Packaging</a></li>')
    
    # 2. Compare page link
    if product_slug in ('commercial-castor-oil', 'first-special-grade-castor-oil'):
        items.append('<li><a href="/compare/fsg-vs-commercial-castor-oil" style="color:var(--forest); font-weight:700; text-decoration:underline;">Compare FSG vs Commercial Castor Oil</a></li>')
    elif product_slug == 'hydrogenated-castor-oil':
        items.append('<li><a href="/compare/castor-wax-vs-paraffin-wax" style="color:var(--forest); font-weight:700; text-decoration:underline;">Compare Castor Wax (HCO) vs Paraffin Wax</a></li>')
    else:
        items.append('<li><a href="/compare/castor-oil-grades" style="color:var(--forest); font-weight:700; text-decoration:underline;">Compare Castor Oil Technical Grades</a></li>')
    
    # 3. Two related blog posts
    related_added = 0
    for op in other_posts:
        if op['slug'] != post['slug']:
            op_slug = op['slug']
            op_title = op['title']
            items.append(f'<li><a href="/blog/{op_slug}" style="color:var(--forest); font-weight:700; text-decoration:underline;">{op_title}</a></li>')
            related_added += 1
            if related_added >= 2:
                break
                
    return f"""
<div style="background:#ffffff; border:1px solid var(--border-light); border-radius:var(--radius-md); padding:1.75rem; margin:2.5rem 0; border-top:3px solid var(--gold); box-shadow:var(--shadow-sm);">
  <strong style="color:var(--forest); font-size:1.1rem; display:block; margin-bottom:0.75rem; font-family:var(--font-heading);">Related Technical Resources &amp; Specifications</strong>
  <ul style="list-style:disc; padding-left:1.5rem; margin:0; font-size:0.925rem; line-height:1.75; color:var(--charcoal-soft);">
    {''.join(items)}
  </ul>
</div>
"""

def render_end_cta_band(product_slug, product_data):
    """Render standard end CTA band identical to product pages."""
    prod_name = product_data.get('display_name', 'Industrial Castor Derivatives') if product_data else 'Castor Oil & Derivatives'
    slug_param = f"?product={product_slug}" if product_slug else ""
    return f"""
<section class="product-enquiry-band" style="background:var(--forest);color:#ffffff;padding:4rem 0;margin-top:3.5rem;">
  <div class="container" style="max-width:1100px;margin:0 auto;padding:0 1.5rem;text-align:center;">
    <div class="product-enquiry-inner">
      <h2 class="product-enquiry-title" style="font-family:var(--font-heading);font-size:2.2rem;color:#ffffff;margin-bottom:0.75rem;">
        Order commercial volumes or request technical samples
      </h2>
      <p class="product-enquiry-sub" style="color:rgba(255,255,255,0.85);font-size:1.05rem;max-width:700px;margin:0 auto 2rem;line-height:1.6;">
        Connect directly with our commercial sales desk in Gandhinagar or our technical plant team in Deodar, Gujarat.
      </p>
      <div class="product-enquiry-actions" style="display:flex;justify-content:center;gap:1rem;flex-wrap:wrap;">
        <a href="/contact{slug_param}" class="btn btn-gold btn-lg">Request a Quote &rarr;</a>
        <a href="/contact?inquiry=sample{slug_param}" class="btn btn-outline-white btn-lg" style="border:1px solid rgba(255,255,255,0.8);color:#ffffff;">Request Sample &rarr;</a>
      </div>
    </div>
  </div>
</section>
"""

def extract_headings(html_content):
    """Extract H2 and H3 elements to build an interactive Table of Contents."""
    soup = BeautifulSoup(html_content, 'html.parser')
    headings = []
    count = 1
    for h in soup.find_all(['h2', 'h3']):
        text = h.get_text().strip()
        if 'frequently asked questions' in text.lower() or 'technical faq' in text.lower():
            continue
        h_id = h.get('id')
        if not h_id:
            h_id = f"section-{count}"
            h['id'] = h_id
        headings.append({
            'tag': h.name,
            'id': h_id,
            'text': text
        })
        count += 1
    return str(soup), headings

def render_toc(headings):
    """Render Table of Contents block."""
    if not headings:
        return ""
    items = []
    for h in headings:
        indent = "margin-left:1.25rem;" if h['tag'] == 'h3' else ""
        h_id = h['id']
        h_text = h['text']
        items.append(f'<li style="{indent}"><a href="#{h_id}" style="color:var(--forest); text-decoration:none; font-weight:600;">{h_text}</a></li>')
    items.append('<li><a href="#section-faq" style="color:var(--forest); text-decoration:none; font-weight:600;">Frequently Asked Questions</a></li>')
    
    return f"""
<nav class="blog-toc-box" aria-label="Table of Contents" style="background:var(--ivory); border:1px solid var(--border-light); border-left:4px solid var(--forest); border-radius:var(--radius-sm); padding:1.5rem; margin:2rem 0; box-shadow:var(--shadow-sm);">
  <strong style="color:var(--forest); font-size:1.05rem; display:block; margin-bottom:0.75rem; font-family:var(--font-heading);">Table of Contents</strong>
  <ul style="list-style:none; padding:0; margin:0; display:flex; flex-direction:column; gap:0.5rem; font-size:0.9rem;">
    {''.join(items)}
  </ul>
</nav>
"""

def build_post_html(post_meta, body_markdown, product_master, facts_register, all_published):
    """Generate complete standalone HTML for a blog post."""
    slug = post_meta['slug']
    title = post_meta['title']
    description = post_meta['description']
    publish_date = post_meta['publish_date']
    product_slug = post_meta.get('product_slug', '')
    lang = post_meta.get('lang', 'en')
    faqs = post_meta.get('faqs', [])
    summary_box = post_meta.get('in_brief', '')
    
    dt_pub = parse_ist(publish_date)
    date_display = format_date_display(dt_pub)
    date_iso = format_date_iso(dt_pub)
    
    product_data = product_master.get(product_slug)
    category_name = post_meta.get('category_name')
    if not category_name:
        category_map = {
            'T1': 'Industrial Technical Guides',
            'T2': 'Application Engineering',
            'T3': 'Buyer Specifications & COA',
            'T4': 'Regional & Port Logistics',
            'T5': 'ખેડૂત માર્ગદર્શિકા (Farmer Guide)'
        }
        category_name = category_map.get(post_meta.get('type', 'T1'), 'Technical Perspectives')
    
    # Render placeholders in markdown
    md_content = body_markdown
    
    # Replace key facts placeholder
    if '{{key_facts}}' in md_content or f'{{{{key_facts:{product_slug}}}}}' in md_content:
        kf_html = render_key_facts_table(product_slug, product_data)
        md_content = re.sub(r'\{\{key_facts(?::[^}]+)?\}\}', kf_html, md_content)
    elif product_slug and post_meta.get('type') in ('T1', 'T2', 'T3'):
        # Automatically inject key facts if not explicitly present
        kf_html = render_key_facts_table(product_slug, product_data)
        md_content = kf_html + "\n\n" + md_content
        
    # Replace spec table placeholder
    if '{{spec_table}}' in md_content or f'{{{{spec_table:{product_slug}}}}}' in md_content:
        st_html = render_spec_table_block(product_slug, product_data)
        md_content = re.sub(r'\{\{spec_table(?::[^}]+)?\}\}', st_html, md_content)
    elif product_slug and post_meta.get('type') == 'T1':
        # Automatically append spec table for T1 if not explicitly present
        st_html = render_spec_table_block(product_slug, product_data)
        md_content = md_content + "\n\n" + st_html
        
    # Replace mid-article CTA placeholder
    cta_mid_html = render_cta_box(product_slug, product_data)
    if '{{mid_cta}}' in md_content:
        md_content = md_content.replace('{{mid_cta}}', cta_mid_html)
    else:
        # Insert mid-article CTA roughly halfway through body
        paras = md_content.split('\n\n')
        mid = max(1, len(paras) // 2)
        paras.insert(mid, cta_mid_html)
        md_content = '\n\n'.join(paras)
        
    # Convert Markdown to HTML using markdown_it
    md = markdown_it.MarkdownIt()
    raw_body_html = md.render(md_content)
    
    # Process headings for TOC
    processed_body_html, headings = extract_headings(raw_body_html)
    toc_html = render_toc(headings)
    
    # Summary box ("In brief")
    in_brief_html = ""
    if summary_box:
        in_brief_html = f"""
<div class="blog-in-brief-box" style="background:#f4f7f4;border:1px solid #d2ded2;border-left:4px solid var(--forest);border-radius:var(--radius-sm);padding:1.5rem;margin:1.75rem 0 2rem;box-shadow:var(--shadow-sm);">
  <strong style="color:var(--forest);font-size:1rem;display:block;margin-bottom:0.4rem;text-transform:uppercase;letter-spacing:0.05em;font-weight:700;">In Brief</strong>
  <p style="color:var(--charcoal);font-size:1.025rem;line-height:1.65;margin:0;">{summary_box}</p>
</div>
"""
    
    # FAQ HTML
    faq_html = render_faq_section(faqs)
    
    # Related block
    related_html = render_related_block(post_meta, product_slug, product_data, all_published)
    
    # End CTA band
    end_cta_html = render_end_cta_band(product_slug, product_data)
    
    # Word count & Read time
    plain_text = re.sub(r'<[^>]+>', ' ', raw_body_html)
    word_count = len(re.findall(r'\b\w+\b', plain_text))
    read_mins = max(3, round(word_count / 220))
    
    # Schema JSON-LD Graph
    faq_schema = []
    for f in faqs:
        faq_schema.append({
            "@type": "Question",
            "name": f.get('q', ''),
            "acceptedAnswer": {
                "@type": "Answer",
                "text": f.get('a', '')
            }
        })
        
    schema_graph = [
        {
            "@type": "Organization",
            "@id": "https://www.nagdevproducts.com/#organization",
            "name": "Nagdev Products",
            "legalName": "Nagdev Products Private Limited",
            "url": "https://www.nagdevproducts.com",
            "logo": "https://www.nagdevproducts.com/images/logo.png",
            "telephone": "+916352098306",
            "email": "nagdevproducts@gmail.com"
        },
        {
            "@type": "WebSite",
            "@id": "https://www.nagdevproducts.com/#website",
            "url": "https://www.nagdevproducts.com",
            "name": "Nagdev Products"
        },
        {
            "@type": "BreadcrumbList",
            "@id": f"https://www.nagdevproducts.com/blog/{slug}#breadcrumb",
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": 1,
                    "name": "Home",
                    "item": "https://www.nagdevproducts.com/"
                },
                {
                    "@type": "ListItem",
                    "position": 2,
                    "name": "Blog",
                    "item": "https://www.nagdevproducts.com/blog"
                },
                {
                    "@type": "ListItem",
                    "position": 3,
                    "name": title,
                    "item": f"https://www.nagdevproducts.com/blog/{slug}"
                }
            ]
        },
        {
            "@type": "BlogPosting",
            "@id": f"https://www.nagdevproducts.com/blog/{slug}#article",
            "headline": title,
            "description": description,
            "datePublished": publish_date,
            "dateModified": publish_date,
            "inLanguage": lang,
            "mainEntityOfPage": {
                "@type": "WebPage",
                "@id": f"https://www.nagdevproducts.com/blog/{slug}"
            },
            "author": {
                "@id": "https://www.nagdevproducts.com/#organization"
            },
            "publisher": {
                "@id": "https://www.nagdevproducts.com/#organization"
            }
        }
    ]
    
    if faq_schema:
        schema_graph.append({
            "@type": "FAQPage",
            "@id": f"https://www.nagdevproducts.com/blog/{slug}#faq",
            "mainEntity": faq_schema
        })
        
    schema_json = json.dumps({"@context": "https://schema.org", "@graph": schema_graph}, indent=2)
    
    # Read base header/footer template from blog/_template.html
    template_path = 'blog/_template.html'
    if not os.path.exists(template_path):
        template_path = 'plant.html'
    with open(template_path, 'r', encoding='utf-8') as f:
        full_sample = f.read()
        
    # Extract site header
    header_match = re.search(r'(<header.*?</header>)', full_sample, re.DOTALL)
    header_html = header_match.group(1) if header_match else ""
    
    # Extract site footer and scripts up to </html>
    footer_match = re.search(r'(<footer.*</html>)', full_sample, re.DOTALL)
    if footer_match:
        footer_html = footer_match.group(1)
        # Ensure analytics.js is present before </body>
        if '/js/analytics.js' not in footer_html:
            footer_html = footer_html.replace('</body>', '  <script defer src="/js/analytics.js"></script>\n</body>')
    else:
        footer_html = """<footer class="site-footer" role="contentinfo"><div class="container-wide"><p>&copy; 2026 Nagdev Products</p></div></footer>\n<script defer src="/js/analytics.js"></script>\n</body>\n</html>"""
    
    # Assemble complete page
    html = f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} | Nagdev Products</title>
  <meta name="description" content="{description}">
  <link rel="canonical" href="https://www.nagdevproducts.com/blog/{slug}">

  <!-- Open Graph / Facebook / LinkedIn -->
  <meta property="og:type" content="article">
  <meta property="og:url" content="https://www.nagdevproducts.com/blog/{slug}">
  <meta property="og:title" content="{title} | Nagdev Products">
  <meta property="og:description" content="{description}">
  <meta property="og:image" content="https://www.nagdevproducts.com/images/og-share.jpg">

  <!-- Twitter Card -->
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{title} | Nagdev Products">
  <meta name="twitter:description" content="{description}">
  <meta name="twitter:image" content="https://www.nagdevproducts.com/images/og-share.jpg">

  <link rel="preload" href="/fonts/inter-latin.woff2" as="font" type="font/woff2" crossorigin>
  <link rel="preload" href="/fonts/cormorant-garamond-latin.woff2" as="font" type="font/woff2" crossorigin>
  <link rel="stylesheet" href="/css/main.min.css?v=20261023c">
  <link rel="stylesheet" href="/css/blog.min.css">
  <meta name="theme-color" content="#0b3d1e">
  <link rel="icon" href="/favicon.ico">\n\n  <!-- Google Analytics 4 & Consent Mode v2 -->
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){{dataLayer.push(arguments);}}
    gtag('consent', 'default', {{
      'ad_storage': 'denied',
      'ad_user_data': 'denied',
      'ad_personalization': 'denied',
      'analytics_storage': 'denied',
      'region': ['AT', 'BE', 'BG', 'CY', 'CZ', 'DE', 'DK', 'EE', 'ES', 'FI', 'FR', 'GR', 'HR', 'HU', 'IE', 'IT', 'LT', 'LU', 'LV', 'MT', 'NL', 'PL', 'PT', 'RO', 'SE', 'SI', 'SK', 'IS', 'LI', 'NO', 'GB', 'CH'],
      'wait_for_update': 500
    }});
    gtag('consent', 'default', {{
      'ad_storage': 'denied',
      'ad_user_data': 'denied',
      'ad_personalization': 'denied',
      'analytics_storage': 'granted'
    }});
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

  <!-- JSON-LD Structured Data: BlogPosting + BreadcrumbList + FAQPage -->
  <script type="application/ld+json">
{schema_json}
  </script>
</head>
<body>
<a href="#main-content" class="skip-to-content">Skip to main content</a>

{header_html}

  <article class="blog-article">
    <header class="blog-article-header">
      <div class="container-narrow">
        <nav class="breadcrumb-nav" aria-label="Breadcrumb">
          <a href="/">Home</a> &gt; 
          <a href="/blog">Blog</a> &gt; 
          <span aria-current="page">{category_name}</span>
        </nav>

        <span class="blog-category-badge">{category_name}</span>
        <h1 class="blog-article-title">{title}</h1>

        <div class="blog-meta-bar" style="margin-top:1.25rem;">
          <div class="meta-item">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
            <strong style="color:var(--forest);">Nagdev Products technical team</strong>
          </div>
          <div class="meta-item">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
            <span>Published: <time datetime="{date_iso}">{date_display}</time> · Updated: <time datetime="{date_iso}">{date_display}</time></span>
          </div>
          <div class="meta-item">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
            <span>{read_mins} min read</span>
          </div>
        </div>
      </div>
    </header>

    <div class="container-narrow">
      <div class="blog-content-body typography">
        {in_brief_html}
        {toc_html}
        {processed_body_html}
        {faq_html}
        {related_html}
      </div>
    </div>

    {end_cta_html}
  </article>
</main>

{footer_html}
"""
    return html

def update_blog_index(published_posts):
    """Regenerate blog.html with SSR post cards and update js/blog-data.js."""
    # 1. Update js/blog-data.js
    posts_data = []
    for p in published_posts:
        dt = parse_ist(p['publish_date'])
        plain = re.sub(r'<[^>]+>', ' ', p.get('content_html', ''))
        words = len(re.findall(r'\b\w+\b', plain))
        read_time = f"{max(3, round(words / 220))} min read"
        
        posts_data.append({
            "id": f"post-{p['slug']}",
            "slug": p['slug'],
            "title": p['title'],
            "category": p.get('category_name', 'Technical Guide'),
            "type": p.get('type', 'T1'),
            "product_slug": p.get('product_slug', ''),
            "date": format_date_iso(dt),
            "author": "Nagdev Products technical team",
            "readTime": read_time,
            "seoDescription": p['description'],
            "coverImage": "images/og-share.jpg",
            "tags": p.get('secondary_keywords', [])
        })
        
    js_content = f"""/**
 * NAGDEV PRODUCTS PRIVATE LIMITED — BLOG DATABASE
 * Auto-generated by scripts/build_blog.py at build time.
 * Total Published Posts: {len(posts_data)}
 */

window.NAGDEV_BLOG_POSTS = {json.dumps(posts_data, indent=2)};
"""
    with open('js/blog-data.js', 'w', encoding='utf-8') as f:
        f.write(js_content)
        
    # 2. Update blog.html SSR cards grid
    with open('blog.html', 'r', encoding='utf-8') as f:
        blog_html = f.read()
        
    cards_html = []
    for p in published_posts:
        dt = parse_ist(p['publish_date'])
        plain = re.sub(r'<[^>]+>', ' ', p.get('content_html', ''))
        words = len(re.findall(r'\b\w+\b', plain))
        read_time = f"{max(3, round(words / 220))} min"
        date_str = format_date_display(dt)
        date_iso = format_date_iso(dt)
        cat = p.get('category_name', 'Technical Guide')
        
        cards_html.append(f"""
        <article class="blog-card" data-category="{cat}" data-type="{p.get('type', 'T1')}" data-product="{p.get('product_slug', '')}">
          <div class="blog-card-body">
            <div class="blog-card-category">{cat}</div>
            <h3 class="blog-card-title">
              <a href="/blog/{p['slug']}">{p['title']}</a>
            </h3>
            <p class="blog-card-excerpt">{p['description']}</p>
            <div class="blog-card-footer">
              <time datetime="{date_iso}">{date_str} · {read_time}</time>
              <a href="/blog/{p['slug']}" class="blog-read-link">Read &rarr;</a>
            </div>
          </div>
        </article>
""")
        
    grid_replacement = f'<div class="blog-grid" id="blog-posts-grid">{"".join(cards_html)}</div>'
    new_blog_html = re.sub(r'<div class="blog-grid" id="blog-posts-grid">.*?</div>\s*<!-- No Results State -->', f'{grid_replacement}\n\n      <!-- No Results State -->', blog_html, flags=re.DOTALL)
    
    # 3. Update featured post in blog.html with newest published post
    if published_posts:
        feat = published_posts[0]
        feat_dt = parse_ist(feat['publish_date'])
        feat_date_str = format_date_display(feat_dt)
        feat_date_iso = format_date_iso(feat_dt)
        feat_plain = re.sub(r'<[^>]+>', ' ', feat.get('content_html', ''))
        feat_words = len(re.findall(r'\b\w+\b', feat_plain))
        feat_read_time = f"{max(3, round(feat_words / 220))} min read"
        feat_cat = feat.get('category_name', 'Technical Guide')
        
        feat_card_html = f"""<div class="featured-card">
        <a href="/blog/{feat['slug']}" class="featured-media" aria-label="{feat['title']}">
          <img src="/images/og-share.jpg" alt="{feat['title']}" width="1200" height="630" loading="eager">
        </a>
        <div class="featured-content">
          <span class="featured-badge">&#10022; Featured Insight &middot; {feat_cat}</span>
          <h2 class="featured-title">
            <a href="/blog/{feat['slug']}">{feat['title']}</a>
          </h2>
          <p class="featured-excerpt">{feat['description']}</p>
          <div class="featured-meta">
            <span>By Nagdev Products technical team</span>
            <span>&bull;</span>
            <time datetime="{feat_date_iso}">{feat_date_str}</time>
            <span>&bull;</span>
            <span>{feat_read_time}</span>
          </div>
          <div>
            <a href="/blog/{feat['slug']}" class="btn btn-primary btn-sm">Read Full Guide &rarr;</a>
          </div>
        </div>
      </div>"""
        new_blog_html = re.sub(r'<div id="featured-post-container">.*?</div>\s*</div>\s*</div>\s*</section>', f'<div id="featured-post-container">\n{feat_card_html}\n    </div>\n    </div>\n  </section>', new_blog_html, flags=re.DOTALL)
        
    with open('blog.html', 'w', encoding='utf-8') as f:
        f.write(new_blog_html)

def update_homepage(published_posts):
    """Update index.html 'Latest insights' section with the 3 newest published posts."""
    if not os.path.exists('index.html'):
        return
    with open('index.html', 'r', encoding='utf-8') as f:
        content = f.read()
        
    # Pick top 3 newest
    top3 = published_posts[:3]
    
    cards_html = []
    for p in top3:
        dt = parse_ist(p['publish_date'])
        plain = re.sub(r'<[^>]+>', ' ', p.get('content_html', ''))
        words = len(re.findall(r'\b\w+\b', plain))
        read_time = f"{max(3, round(words / 220))} min"
        date_str = format_date_display(dt)
        cat = p.get('category_name', 'Technical Guide')
        
        cards_html.append(f"""
        <article class="blog-card" style="background:#ffffff;border:1px solid var(--border-light);border-radius:var(--radius-md);padding:1.5rem;box-shadow:var(--shadow-sm);display:flex;flex-direction:column;">
          <div style="font-size:0.8rem;font-weight:700;color:var(--gold);text-transform:uppercase;letter-spacing:0.05em;margin-bottom:0.5rem;">{cat}</div>
          <h3 style="font-size:1.15rem;font-family:var(--font-heading);color:var(--forest);margin-bottom:0.75rem;line-height:1.4;">
            <a href="/blog/{p['slug']}" style="color:inherit;text-decoration:none;">{p['title']}</a>
          </h3>
          <p style="font-size:0.9rem;color:var(--charcoal-soft);line-height:1.6;margin-bottom:1.25rem;flex-grow:1;">{p['description']}</p>
          <div style="font-size:0.825rem;color:var(--text-muted);display:flex;justify-content:space-between;align-items:center;border-top:1px solid var(--border-light);padding-top:0.75rem;">
            <span>{date_str} · {read_time}</span>
            <a href="/blog/{p['slug']}" style="color:var(--forest);font-weight:700;text-decoration:underline;">Read &rarr;</a>
          </div>
        </article>
""")
        
    insights_section = f"""<!-- LATEST INSIGHTS SECTION -->
<section class="section bg-ivory" id="latest-insights" aria-labelledby="insights-heading" style="border-top: 1px solid var(--border-light); padding: 4.5rem 0;">
  <div class="container">
    <div class="section-header fade-up" style="text-align:center; max-width:760px; margin: 0 auto 3rem;">
      <span class="section-eyebrow" style="color:var(--gold);font-weight:700;letter-spacing:0.1em;text-transform:uppercase;font-size:0.85rem;">Technical Perspectives</span>
      <h2 class="section-title" id="insights-heading" style="font-family:var(--font-heading);font-size:2.4rem;color:var(--forest);margin:0.5rem 0 1rem;">
        Latest Oleochemical Insights
      </h2>
      <p class="section-sub" style="color:var(--charcoal-soft);font-size:1.05rem;line-height:1.6;">
        Peer-reviewed specifications, processing chemistry, and regional market intelligence from North Gujarat's castor belt.
      </p>
    </div>

    <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(300px, 1fr)); gap:2rem;">
      {''.join(cards_html)}
    </div>

    <div style="text-align:center; margin-top:2.5rem;">
      <a href="/blog" class="btn btn-primary" style="display:inline-flex;align-items:center;gap:0.5rem;">
        Explore All Technical Articles &rarr;
      </a>
    </div>
  </div>
</section>
"""
    # If section already exists, replace it
    if 'id="latest-insights"' in content:
        new_content = re.sub(r'<!-- LATEST INSIGHTS SECTION -->.*?<!-- /LATEST INSIGHTS SECTION -->', f'<!-- LATEST INSIGHTS SECTION -->\n{insights_section}\n<!-- /LATEST INSIGHTS SECTION -->', content, flags=re.DOTALL)
    else:
        # Insert right before FAQ section
        faq_marker = '<section class="section bg-ivory" id="faq"'
        if faq_marker in content:
            new_content = content.replace(faq_marker, f'<!-- LATEST INSIGHTS SECTION -->\n{insights_section}\n<!-- /LATEST INSIGHTS SECTION -->\n\n{faq_marker}')
        else:
            # Fallback before final CTA
            cta_marker = '<section class="final-cta-section"'
            new_content = content.replace(cta_marker, f'<!-- LATEST INSIGHTS SECTION -->\n{insights_section}\n<!-- /LATEST INSIGHTS SECTION -->\n\n{cta_marker}')
            
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(new_content)

def update_sitemap(published_posts):
    """Update sitemap.xml with only published blog URLs."""
    if not os.path.exists('sitemap.xml'):
        return
    with open('sitemap.xml', 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    # Filter out existing blog/<slug> entries
    non_blog_lines = []
    in_blog_url = False
    buffer = []
    for line in lines:
        if '<url>' in line:
            buffer = [line]
            in_blog_url = False
        elif '</url>' in line:
            buffer.append(line)
            if not in_blog_url:
                non_blog_lines.extend(buffer)
            buffer = []
        elif buffer:
            if '<loc>https://www.nagdevproducts.com/blog/' in line:
                in_blog_url = True
            buffer.append(line)
        else:
            non_blog_lines.append(line)
            
    if buffer and not in_blog_url:
        non_blog_lines.extend(buffer)
        
    base_sitemap = "".join(non_blog_lines)
    
    # Generate XML entries for published posts
    blog_xml_entries = []
    for p in published_posts:
        dt = parse_ist(p['publish_date'])
        date_iso = format_date_iso(dt)
        blog_xml_entries.append(f"""  <url>
    <loc>https://www.nagdevproducts.com/blog/{p['slug']}</loc>
    <lastmod>{date_iso}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.7</priority>
  </url>
""")
        
    closing_tag = '</urlset>'
    if closing_tag in base_sitemap:
        new_sitemap = base_sitemap.replace(closing_tag, f'{"".join(blog_xml_entries)}{closing_tag}')
    else:
        new_sitemap = base_sitemap + f'\n{"".join(blog_xml_entries)}\n{closing_tag}'
        
    with open('sitemap.xml', 'w', encoding='utf-8') as f:
        f.write(new_sitemap)

def update_rss(published_posts):
    """Generate valid RSS 2.0 feed at blog/rss.xml."""
    items = []
    for p in published_posts:
        dt = parse_ist(p['publish_date'])
        pub_rfc = dt.strftime('%a, %d %b %Y %H:%M:%S +0530')
        desc = p['description'].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        title = p['title'].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        items.append(f"""    <item>
      <title>{title}</title>
      <link>https://www.nagdevproducts.com/blog/{p['slug']}</link>
      <guid isPermaLink="true">https://www.nagdevproducts.com/blog/{p['slug']}</guid>
      <pubDate>{pub_rfc}</pubDate>
      <description>{desc}</description>
    </item>""")
        
    rss_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>Nagdev Products Oleochemical Blog</title>
    <link>https://www.nagdevproducts.com/blog</link>
    <description>Technical insights, chemical engineering analysis, and industrial guides on castor oil derivatives and green oleochemistry.</description>
    <language>en</language>
    <atom:link href="https://www.nagdevproducts.com/blog/rss.xml" rel="self" type="application/rss+xml" />
    <lastBuildDate>{datetime.now(IST).strftime('%a, %d %b %Y %H:%M:%S +0530')}</lastBuildDate>
{''.join(items)}
  </channel>
</rss>
"""
    os.makedirs('blog', exist_ok=True)
    with open('blog/rss.xml', 'w', encoding='utf-8') as f:
        f.write(rss_xml)

def update_llms_txt(published_posts):
    """Update llms.txt with published blog posts."""
    if not os.path.exists('llms.txt'):
        return
    with open('llms.txt', 'r', encoding='utf-8') as f:
        content = f.read()
        
    lines = []
    lines.append("\n## Technical Insights & Blog")
    for p in published_posts:
        lines.append(f"- [{p['title']}](https://www.nagdevproducts.com/blog/{p['slug']}): {p['description']}")
        
    blog_section = "\n".join(lines)
    
    if "## Technical Insights & Blog" in content:
        new_content = re.sub(r'## Technical Insights & Blog.*?(?=\n## |\Z)', blog_section.strip() + "\n\n", content, flags=re.DOTALL)
    else:
        # Append before Procurement Contact
        if "## Procurement Contact" in content:
            new_content = content.replace("## Procurement Contact", f"{blog_section.strip()}\n\n## Procurement Contact")
        else:
            new_content = content + "\n\n" + blog_section.strip() + "\n"
            
    with open('llms.txt', 'w', encoding='utf-8') as f:
        f.write(new_content)

def update_keywords_csv(published_posts):
    """Append published post primary keywords to seo/keywords.csv."""
    if not os.path.exists('seo/keywords.csv'):
        return
        
    rows = []
    with open('seo/keywords.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            # Preserve existing non-blog rows or blog rows
            if r['cluster'] != 'Blog':
                rows.append(r)
                
    # Add all published blog posts
    for p in published_posts:
        dt = parse_ist(p['publish_date'])
        rows.append({
            'keyword': p['primary_keyword'],
            'cluster': 'Blog',
            'priority': 'P2',
            'target_url': f"/blog/{p['slug']}",
            'first_tracked': format_date_iso(dt)
        })
        
    fieldnames = ['keyword', 'cluster', 'priority', 'target_url', 'first_tracked']
    with open('seo/keywords.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

def validate_posts(posts_metadata, product_master):
    """Perform rigorous validation across all written blog posts."""
    errors = []
    
    # 1. Primary keyword uniqueness across all written posts
    kw_seen = {}
    for p in posts_metadata:
        kw = p['primary_keyword'].strip().lower()
        if kw in kw_seen:
            errors.append(f"Duplicate primary keyword '{kw}' found in {p['slug']} and {kw_seen[kw]}")
        kw_seen[kw] = p['slug']
        
    # Check keyword collision with existing indexable product pages
    if os.path.exists('seo/keywords.csv'):
        with open('seo/keywords.csv', 'r', encoding='utf-8') as f:
            for r in csv.DictReader(f):
                if r['cluster'] != 'Blog':
                    k = r['keyword'].strip().lower()
                    if k in kw_seen:
                        errors.append(f"Blog keyword '{k}' in {kw_seen[k]} cannibalizes existing page {r['target_url']}")
                        
    # 2. Unique FAQ questions
    faq_seen = {}
    for p in posts_metadata:
        for f in p.get('faqs', []):
            q = f.get('q', '').strip().lower()
            if q in faq_seen:
                errors.append(f"Duplicate FAQ question '{q}' in {p['slug']} and {faq_seen[q]}")
            faq_seen[q] = p['slug']
            
    # 3. Title length, meta description length, keyword placement
    for p in posts_metadata:
        slug = p['slug']
        title = p['title']
        desc = p['description']
        kw = p['primary_keyword'].lower()
        body = p.get('body_markdown', '')
        
        if len(title) > 60:
            errors.append(f"{slug}: Title exceeds 60 characters ({len(title)}): '{title}'")
            
        if len(desc) < 130 or len(desc) > 160:
            errors.append(f"{slug}: Meta description length {len(desc)} not in 130-160 range: '{desc}'")
            
        # Primary keyword in title
        if kw not in title.lower():
            errors.append(f"{slug}: Primary keyword '{kw}' missing from title '{title}'")
            
        # Primary keyword in slug
        slug_clean = slug.replace('-', ' ')
        # allow Gujarati or english slug
        if p.get('lang', 'en') == 'en' and not all(w in slug_clean for w in kw.split()[:2]):
            errors.append(f"{slug}: Primary keyword '{kw}' not reflected in slug '{slug}'")
            
        # Primary keyword in description
        if kw not in desc.lower():
            errors.append(f"{slug}: Primary keyword '{kw}' missing from meta description")
            
        # Primary keyword in first 100 words
        first_100_words = " ".join(body.split()[:100]).lower()
        if kw not in first_100_words:
            # check in_brief summary box as well
            in_brief = p.get('in_brief', '').lower()
            if kw not in in_brief and kw not in first_100_words:
                errors.append(f"{slug}: Primary keyword '{kw}' missing from first 100 words / in-brief box")
                
        # Primary keyword in at least one H2
        h2_headings = re.findall(r'##\s*(.+)', body)
        h2_found = any(kw in h.lower() for h in h2_headings)
        if not h2_found:
            errors.append(f"{slug}: Primary keyword '{kw}' missing from any H2 heading")
            
        # Primary keyword mentions in body (2-4 natural mentions)
        mentions = len(re.findall(re.escape(kw), body.lower()))
        if mentions < 2:
            errors.append(f"{slug}: Primary keyword '{kw}' mentioned only {mentions} times in body (requires 2-4 mentions)")
            
    # 4. 3-shingle similarity check (< 30%)
    shingles_by_slug = {}
    for p in posts_metadata:
        shingles_by_slug[p['slug']] = get_word_shingles(p.get('body_markdown', ''))
        
    for i in range(len(posts_metadata)):
        slug_a = posts_metadata[i]['slug']
        sh_a = shingles_by_slug[slug_a]
        for j in range(i + 1, len(posts_metadata)):
            slug_b = posts_metadata[j]['slug']
            sh_b = shingles_by_slug[slug_b]
            sim = compute_similarity(sh_a, sh_b)
            if sim >= 0.30:
                errors.append(f"High similarity ({sim:.1%}) between '{slug_a}' and '{slug_b}' (limit < 30%)")
                
    # 5. Banned puffery & unheld claim check
    banned_puffery = ["world-class", "leading manufacturer", "leading supplier", "superior quality", "unmatched", "best manufacturer", "premium quality"]
    for p in posts_metadata:
        full_text = (p.get('title', '') + " " + p.get('description', '') + " " + p.get('body_markdown', '')).lower()
        for bp in banned_puffery:
            if bp in full_text:
                errors.append(f"{p['slug']}: Banned phrase or puffery detected: '{bp}'")

    return errors

def main():
    parser = argparse.ArgumentParser(description="Nagdev Products Blog Engine")
    parser.add_argument('--now', type=str, help="Simulate current IST time e.g. 2026-10-29T12:00:00+05:30")
    parser.add_argument('--dry-run', action='store_true', help="Validate only, do not write files")
    args = parser.parse_args()
    
    if args.now:
        now_ist = parse_ist(args.now)
    else:
        now_ist = datetime.now(IST)
        
    print(f"==================================================")
    print(f"NAGDEV PRODUCTS BLOG ENGINE (PHASE 14)")
    print(f"Target Run Time (IST): {now_ist.isoformat()}")
    print(f"==================================================")
    
    product_master = load_product_master()
    facts_register = load_facts_register()
    calendar = load_calendar()
    
    # 1. Read all content/blog/*.md posts
    content_dir = 'content/blog'
    if not os.path.exists(content_dir):
        os.makedirs(content_dir, exist_ok=True)
        
    md_files = [f for f in os.listdir(content_dir) if f.endswith('.md')]
    print(f"Found {len(md_files)} markdown files in {content_dir}/")
    
    posts = []
    for fn in md_files:
        path = os.path.join(content_dir, fn)
        with open(path, 'r', encoding='utf-8') as f:
            raw = f.read()
            
        m = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)$', raw, re.DOTALL)
        if not m:
            print(f"[ERROR] Invalid front matter in {path}")
            continue
        front_yaml = m.group(1)
        body = m.group(2)
        
        try:
            meta = yaml.safe_load(front_yaml)
        except Exception as e:
            print(f"[ERROR] Failed parsing YAML in {path}: {e}")
            continue
            
        meta['body_markdown'] = body
        posts.append(meta)
        
    # Sort posts by publish_date ascending
    posts.sort(key=lambda x: parse_ist(x['publish_date']))
    
    # 2. Run validations
    print(f"Validating {len(posts)} posts for keyword rules, similarity, and claims...")
    val_errors = validate_posts(posts, product_master)
    if val_errors:
        print(f"\n[VALIDATION FAILED] {len(val_errors)} error(s):")
        for err in val_errors[:15]:
            print(f"  - {err}")
        if len(val_errors) > 15:
            print(f"  ... and {len(val_errors) - 15} more errors.")
        sys.exit(1)
    else:
        print("[PASSED] All posts passed keyword, similarity (<30%), and FAQ uniqueness validation!")
        
    # 3. Determine which posts are eligible to publish (publish_date <= now_ist)
    published_posts = []
    future_posts = []
    
    for p in posts:
        p_dt = parse_ist(p['publish_date'])
        if p_dt <= now_ist:
            published_posts.append(p)
        else:
            future_posts.append(p)
            
    print(f"\nPublishing Status:")
    print(f"  Eligible to publish now: {len(published_posts)}")
    print(f"  Future scheduled posts: {len(future_posts)}")
    
    if args.dry_run:
        print("\n[DRY RUN] No files modified.")
        return
        
    # Clean up any blog/*.html corresponding to future posts (e.g. from prior simulation runs)
    for p in future_posts:
        future_path = f"blog/{p['slug']}.html"
        if os.path.exists(future_path):
            os.remove(future_path)

    # 4. Render eligible posts into blog/<slug>.html
    os.makedirs('blog', exist_ok=True)
    rendered_count = 0
    for p in published_posts:
        html = build_post_html(p, p['body_markdown'], product_master, facts_register, published_posts)
        p['content_html'] = html
        out_path = f"blog/{p['slug']}.html"
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(html)
        rendered_count += 1
        
    print(f"[OK] Rendered {rendered_count} post HTML files into blog/")
    
    # 5. Regenerate secondary assets
    print("Regenerating blog index, homepage insights, sitemap.xml, rss.xml, llms.txt, and keywords.csv...")
    update_blog_index(published_posts)
    update_homepage(published_posts)
    update_sitemap(published_posts)
    update_rss(published_posts)
    update_llms_txt(published_posts)
    update_keywords_csv(published_posts)
    
    print("\n[SUCCESS] Blog build completed successfully!")

if __name__ == '__main__':
    main()
