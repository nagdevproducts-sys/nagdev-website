# -*- coding: utf-8 -*-
"""
Phase 14 Blog Programme Automated Regression & Guard Tests.
Validates:
  1. Drafts isolation (.vercelignore content/ exclusion).
  2. Future posts isolation (future dates never published in sitemap, index, RSS).
  3. All 15 T1 pillar posts rendered and published.
  4. Calendar integrity (104 rows, 41 written, 63 planned with outlines, 0 duplicate keywords).
  5. Keyword cannibalization & duplicate keyword validation failure test.
  6. High shingle similarity (>= 30%) validation failure test.
  7. Banned phrases & claims compliance validation.
  8. Schema.org JSON-LD validity on published HTML posts.
"""
import csv
import json
import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

def test_drafts_not_in_deploy():
    """Verify that content/ is excluded via .vercelignore so drafts never reach production."""
    vercelignore_path = REPO_ROOT / ".vercelignore"
    assert vercelignore_path.exists(), ".vercelignore must exist"
    lines = [line.strip() for line in vercelignore_path.read_text(encoding="utf-8").splitlines()]
    assert "content/" in lines, ".vercelignore must explicitly contain 'content/'"

def test_future_posts_not_published():
    """Verify that future scheduled posts (Weeks 1-26) are not published in production assets."""
    # Read sitemap
    sitemap_path = REPO_ROOT / "sitemap.xml"
    sitemap_text = sitemap_path.read_text(encoding="utf-8")
    
    # Read rss
    rss_path = REPO_ROOT / "blog" / "rss.xml"
    rss_text = rss_path.read_text(encoding="utf-8")
    
    # Read blog-data.js
    blog_data_path = REPO_ROOT / "js" / "blog-data.js"
    blog_data_text = blog_data_path.read_text(encoding="utf-8")
    
    # Check all future written posts
    future_sample_slugs = [
        "commercial-castor-oil-for-industrial-lubricants",
        "fsg-vs-ppg-castor-oil-specification-differences",
        "hydrogenated-castor-oil-in-lithium-grease-formulation",
        "north-gujarat-castor-belt-banaskantha-and-vav-tharad",
        "buying-dehydrated-castor-oil-in-bulk-packaging-coa",
        "castor-seed-harvest-drying-storage-gujarat",
        "selling-castor-seed-to-crushing-plant-deodar"
    ]
    
    for slug in future_sample_slugs:
        # Must NOT exist as HTML in blog/
        html_file = REPO_ROOT / "blog" / f"{slug}.html"
        assert not html_file.exists(), f"Future post {slug}.html should NOT be rendered in blog/"
        
        # Must NOT appear in sitemap.xml
        assert f"/blog/{slug}" not in sitemap_text, f"Future post {slug} must NOT appear in sitemap.xml"
        
        # Must NOT appear in blog/rss.xml
        assert f"/blog/{slug}" not in rss_text, f"Future post {slug} must NOT appear in blog/rss.xml"
        
        # Must NOT appear in js/blog-data.js
        assert f'"{slug}"' not in blog_data_text, f"Future post {slug} must NOT appear in js/blog-data.js"

def test_all_15_t1_posts_published():
    """Verify that all 15 T1 pillar posts are rendered and present across all index assets."""
    t1_slugs = [
        "commercial-castor-oil-supplier-gujarat",
        "fsg-castor-oil-specifications-bulk-supply",
        "first-pressed-degummed-castor-oil-guide",
        "castor-cake-fertilizer-bulk-supply-gujarat",
        "hydrogenated-castor-oil-bulk-supply-gujarat",
        "dehydrated-castor-oil-technical-guide",
        "dco-fatty-acid-specifications-guide",
        "pale-pressed-grade-castor-oil-buyer-guide",
        "cold-pressed-castor-oil-bulk-procurement",
        "castor-oil-bp-monograph-buyer-guide",
        "castor-oil-usp-nf-buyer-qualification",
        "castor-oil-ph-eur-compliance-guide",
        "castor-oil-ip-buyer-qualification-guide",
        "castor-oil-jp-import-specifications",
        "cosmetic-grade-castor-oil-bulk-supply-guide"
    ]
    
    sitemap_text = (REPO_ROOT / "sitemap.xml").read_text(encoding="utf-8")
    rss_text = (REPO_ROOT / "blog" / "rss.xml").read_text(encoding="utf-8")
    blog_data_text = (REPO_ROOT / "js" / "blog-data.js").read_text(encoding="utf-8")
    
    for slug in t1_slugs:
        html_file = REPO_ROOT / "blog" / f"{slug}.html"
        assert html_file.exists(), f"Published HTML file missing: {html_file}"
        assert f"/blog/{slug}" in sitemap_text, f"Slug {slug} missing from sitemap.xml"
        assert f"/blog/{slug}" in rss_text, f"Slug {slug} missing from blog/rss.xml"
        assert f'"{slug}"' in blog_data_text, f"Slug {slug} missing from js/blog-data.js"

def test_calendar_104_posts_complete():
    """Verify that calendar.csv contains 104 posts with 41 written and 63 scheduled."""
    cal_path = REPO_ROOT / "seo" / "blog" / "calendar.csv"
    assert cal_path.exists(), "calendar.csv must exist"
    
    with open(cal_path, "r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
        
    assert len(reader) == 104, f"Expected exactly 104 calendar rows, found {len(reader)}"
    
    written_count = sum(1 for r in reader if r.get("written") == "Y")
    unwritten_count = sum(1 for r in reader if r.get("written") == "N")
    
    assert written_count == 41, f"Expected 41 written posts, found {written_count}"
    assert unwritten_count == 63, f"Expected 63 unwritten posts, found {unwritten_count}"
    
    # Check that all unwritten posts have non-empty outlines or notes
    for r in reader:
        if r.get("written") == "N":
            notes = r.get("outline_notes", "") or r.get("secondary_keywords", "")
            assert len(notes.strip()) > 0, f"Week {r.get('week')} unwritten post missing outline notes"
            
    # Verify unique primary keywords in calendar
    keywords = [r["primary_keyword"].strip().lower() for r in reader if r.get("primary_keyword")]
    assert len(keywords) == len(set(keywords)), "Duplicate primary keywords found in calendar.csv"

def test_duplicate_primary_keywords_fails():
    """Verify that build_blog validator catches duplicate primary keywords."""
    from scripts.build_blog import validate_posts
    
    product_master = json.loads((REPO_ROOT / "seo" / "product-master.json").read_text(encoding="utf-8"))
    
    mock_posts = [
        {
            "slug": "post-a",
            "title": "Commercial Castor Oil Supplier in Gujarat",
            "description": "Commercial castor oil supplier in Gujarat test description for validation testing.",
            "primary_keyword": "commercial castor oil supplier in Gujarat",
            "publish_date": "2026-10-29T12:00:00+05:30",
            "body_markdown": "## Commercial Castor Oil Supplier in Gujarat\nBody text."
        },
        {
            "slug": "post-b",
            "title": "Commercial Castor Oil Supplier in Gujarat Review",
            "description": "Commercial castor oil supplier in Gujarat test description for duplicate testing.",
            "primary_keyword": "commercial castor oil supplier in Gujarat",
            "publish_date": "2026-10-29T12:01:00+05:30",
            "body_markdown": "## Commercial Castor Oil Supplier in Gujarat\nBody text 2."
        }
    ]
    errors = validate_posts(mock_posts, product_master)
    assert any("Duplicate primary keyword" in e for e in errors), "Validator should flag duplicate primary keyword"

def test_high_similarity_fails():
    """Verify that build_blog validator catches 3-shingle similarity >= 30%."""
    from scripts.build_blog import validate_posts
    
    product_master = json.loads((REPO_ROOT / "seo" / "product-master.json").read_text(encoding="utf-8"))
    
    shared_text = "This is a long repetitive technical paragraph detailing the exact mechanical screw pressing operations followed by caustic neutralization and vacuum dehydration at the facility." * 10
    
    mock_posts = [
        {
            "slug": "post-one",
            "title": "First Unique Test Guide on Industrial Castor Oil",
            "description": "First unique test guide on industrial castor oil for similarity testing in Deodar.",
            "primary_keyword": "first unique test guide",
            "publish_date": "2026-10-29T12:00:00+05:30",
            "body_markdown": f"## First Unique Test Guide\n{shared_text}"
        },
        {
            "slug": "post-two",
            "title": "Second Unique Test Guide on Industrial Castor Oil",
            "description": "Second unique test guide on industrial castor oil for similarity testing in Deodar.",
            "primary_keyword": "second unique test guide",
            "publish_date": "2026-10-29T12:01:00+05:30",
            "body_markdown": f"## Second Unique Test Guide\n{shared_text}"
        }
    ]
    errors = validate_posts(mock_posts, product_master)
    assert any("High similarity" in e for e in errors), "Validator should flag high shingle similarity"

def test_banned_phrase_fails():
    """Verify that claims linter and validator detect banned puffery phrases."""
    from scripts.build_blog import validate_posts
    
    product_master = json.loads((REPO_ROOT / "seo" / "product-master.json").read_text(encoding="utf-8"))
    
    mock_post = [{
        "slug": "test-puffery",
        "title": "Best World-Class Castor Oil Manufacturer in India",
        "description": "Best world-class castor oil manufacturer in India supplying superior products from Deodar.",
        "primary_keyword": "best world-class castor oil",
        "publish_date": "2026-10-29T12:00:00+05:30",
        "body_markdown": "## Best World-Class Castor Oil\nWe are the world-class leading supplier with unmatched quality."
    }]
    errors = validate_posts(mock_post, product_master)
    assert any("Banned phrase" in e for e in errors), "Validator should flag banned puffery"

def test_blog_schema_markup():
    """Verify JSON-LD schema validity (BlogPosting, BreadcrumbList, FAQPage) in published posts."""
    blog_files = list((REPO_ROOT / "blog").glob("*.html"))
    # Exclude templates
    posts = [f for f in blog_files if not f.name.startswith("_")]
    assert len(posts) == 15, f"Expected 15 published posts, found {len(posts)}"
    
    for post_file in posts:
        text = post_file.read_text(encoding="utf-8")
        
        # Check for JSON-LD schema block
        scripts = re.findall(r'<script type="application/ld\+json">(.*?)</script>', text, re.DOTALL)
        assert len(scripts) > 0, f"Missing JSON-LD in {post_file.name}"
        
        found_types = set()
        for s in scripts:
            try:
                data = json.loads(s.strip())
                if isinstance(data, dict):
                    if "@graph" in data:
                        for item in data["@graph"]:
                            found_types.add(item.get("@type"))
                    else:
                        found_types.add(data.get("@type"))
            except Exception as e:
                pytest.fail(f"Invalid JSON-LD in {post_file.name}: {e}")
                
        assert "BlogPosting" in found_types, f"Missing BlogPosting schema in {post_file.name}"
        assert "BreadcrumbList" in found_types, f"Missing BreadcrumbList schema in {post_file.name}"
        assert "FAQPage" in found_types, f"Missing FAQPage schema in {post_file.name}"
