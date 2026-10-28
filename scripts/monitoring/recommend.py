import json
import sys
from pathlib import Path

OUTPUT_DIR = Path("monitoring_output")
OUTPUT_FILE = OUTPUT_DIR / "recommendations.json"

def load_json(filename):
    p = OUTPUT_DIR / filename
    if p.exists():
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None

def generate_recommendations():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    gsc = load_json("gsc_data.json") or {}
    ga4 = load_json("ga4_data.json") or {}
    psi = load_json("psi_data.json") or {}
    health = load_json("site_health.json") or {}
    
    recs = []

    # Rule 1: URGENT: any linter FAIL or non-200 or broken links
    claims = health.get("claims_lint", {})
    if claims.get("hard_failures", 0) > 0:
        hard = claims.get("hard_failures")
        rule_fails = [f"{k}={v}" for k, v in claims.get("rule_failures", {}).items() if v > 0]
        recs.append({
            "severity": "URGENT",
            "rule": "Linter Hard Failure",
            "message": f"URGENT: Claims linter failed with {hard} hard failure(s) ({', '.join(rule_fails)}). Fix immediately before publishing."
        })
        
    sitemap_chk = health.get("sitemap_check", {})
    if sitemap_chk.get("non_200_urls"):
        count = len(sitemap_chk["non_200_urls"])
        urls_str = ", ".join([u.get("url", "") for u in sitemap_chk["non_200_urls"][:3]])
        recs.append({
            "severity": "URGENT",
            "rule": "Non-200 Sitemap URL",
            "message": f"URGENT: {count} sitemap URL(s) returned non-200 status ({urls_str}). Restore HTTP 200 immediately."
        })

    if sitemap_chk.get("redirect_chains"):
        count = len(sitemap_chk["redirect_chains"])
        urls_str = ", ".join([u.get("url", "") for u in sitemap_chk["redirect_chains"][:3]])
        recs.append({
            "severity": "URGENT",
            "rule": "Redirect Chain",
            "message": f"URGENT: {count} sitemap URL(s) have redirect chains ({urls_str}). Ensure sitemap points directly to canonical 200 URLs."
        })

    internal_chk = health.get("internal_links_check", {})
    if internal_chk.get("broken_links"):
        count = len(internal_chk["broken_links"])
        urls_str = ", ".join([b.get("url", "") for b in internal_chk["broken_links"][:3]])
        recs.append({
            "severity": "URGENT",
            "rule": "Broken Internal Link",
            "message": f"URGENT: Found {count} broken internal link(s) ({urls_str}). Fix or remove broken hrefs."
        })

    # Rule 2: Query with >= 50 impressions at position 8-20 -> Strengthen <page> for <query>
    top_queries = gsc.get("top_queries", [])
    top_pages = gsc.get("top_pages", [])
    primary_page = top_pages[0]["page"] if top_pages else "/"
    for q in top_queries:
        imp = q.get("impressions", 0)
        pos = q.get("position", 0.0)
        query_text = q.get("query", "")
        if imp >= 50 and 8.0 <= pos <= 20.0:
            recs.append({
                "severity": "HIGH",
                "rule": "Striking Distance Query",
                "message": f"Strengthen {primary_page} for \"{query_text}\" (internal links/section): observed {imp} impressions at average position {pos}."
            })

    # Load sitemap URLs for legacy URL check
    sitemap_urls = set()
    sitemap_path = Path("sitemap.xml")
    if sitemap_path.exists():
        import xml.etree.ElementTree as ET
        try:
            tree = ET.parse(sitemap_path)
            ns = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            for loc in tree.getroot().findall('.//ns:loc', ns):
                sitemap_urls.add(loc.text.strip())
        except Exception:
            pass

    # Rule 3: Page with >= 200 impressions and CTR < 1% -> Review title/meta of <page>
    for p in top_pages:
        imp = p.get("impressions", 0)
        ctr = p.get("ctr", 0.0)
        page_url = p.get("page", "")
        if imp >= 200 and ctr < 1.0:
            recs.append({
                "severity": "MEDIUM",
                "rule": "Low CTR Page",
                "message": f"Review title/meta of {page_url}: observed {imp} impressions with CTR {ctr}% (< 1.0% threshold)."
            })

    # Rule 3b: Legacy URL (not in sitemap) with >= 20 impressions -> Consider 308 redirect
    import requests
    for p in top_pages:
        page_url = p.get("page", "")
        imp = p.get("impressions", 0)
        full_url = page_url if page_url.startswith("http") else f"https://www.nagdevproducts.com{page_url}"
        norm_url = full_url.rstrip("/")
        in_sm = full_url in sitemap_urls or norm_url in sitemap_urls or (norm_url + "/") in sitemap_urls
        if not in_sm and imp >= 20:
            # Check live status before suggesting: exclude URLs that already return 3xx, 410, or 404
            status_code = None
            try:
                chk_resp = requests.head(full_url, allow_redirects=False, timeout=5)
                status_code = chk_resp.status_code
            except Exception:
                pass

            if status_code is not None and (300 <= status_code < 400 or status_code in [404, 410]):
                continue  # Already properly redirected (3xx) or designated dead (404/410)

            recs.append({
                "severity": "MEDIUM",
                "rule": "Legacy URL Impressions",
                "message": f"Legacy URL {page_url} (not in sitemap) received {imp} impressions in last 28 days. Consider a 308 to the closest relevant live page, or leave as 404."
            })

    # Rule 4: P1 keyword with no impressions -> Check targeting only if tracked >= 90 days
    from datetime import datetime, date
    today = date.today()
    keyword_rankings = gsc.get("keyword_rankings", [])
    if not keyword_rankings:
        kw_file = Path("seo/keywords.csv")
        if kw_file.exists():
            import csv
            with open(kw_file, "r", encoding="utf-8") as f:
                keyword_rankings = list(csv.DictReader(f))

    p1_no_impressions = [k for k in keyword_rankings if k.get("priority") == "P1" and int(k.get("impressions", 0)) == 0]
    
    not_yet_ranking = []
    for k in p1_no_impressions:
        kw = k.get("keyword", "")
        t_url = k.get("target_url", "")
        ft_str = k.get("first_tracked") or "2026-10-26"
        try:
            ft_date = datetime.strptime(ft_str, "%Y-%m-%d").date()
            days_tracked = (today - ft_date).days
        except Exception:
            days_tracked = 0

        if days_tracked >= 90:
            recs.append({
                "severity": "MEDIUM",
                "rule": "P1 Keyword Zero Impressions",
                "message": f"Check targeting of {t_url} for P1 keyword \"{kw}\": observed 0 impressions after {days_tracked} days of tracking (>=90d threshold)."
            })
        else:
            not_yet_ranking.append({
                "keyword": kw,
                "cluster": k.get("cluster", ""),
                "target_url": t_url,
                "first_tracked": ft_str,
                "days_tracked": days_tracked
            })

    # Rule 5: Performance Regression (fires only when score drops > 10 points vs previous stored run)
    psi_prev = load_json("psi_previous.json") or load_json("psi_data_previous.json") or {}
    prev_results = {p.get("url"): p for p in psi_prev.get("results", [])}

    psi_results = psi.get("results", [])
    for pr in psi_results:
        score = pr.get("median_score")
        lcp = pr.get("median_lcp_ms")
        name = pr.get("name", "")
        url = pr.get("url", "")

        # Only fires if score drops > 10 vs previous stored run
        prev_score = pr.get("previous_score")
        if prev_score is None and url in prev_results:
            prev_score = prev_results[url].get("median_score")

        if score is not None and prev_score is not None and (prev_score - score) > 10:
            recs.append({
                "severity": "HIGH",
                "rule": "Performance Regression",
                "message": f"Performance regression on {name} ({url}): score dropped {prev_score - score} points (from {prev_score} to {score}/100)."
            })

        # Separate absolute threshold rule: Below target: LCP > 2.5 s on <page> (lab estimate based on median of 3 cache-busted runs)
        if lcp is not None and lcp > 2500:
            recs.append({
                "severity": "MEDIUM",
                "rule": f"Below target: LCP > 2.5 s on {name} (lab estimate)",
                "message": f"Below target: LCP > 2.5 s on {name} ({url}): median LCP is {round(lcp / 1000.0, 2)}s ({lcp}ms) [lab estimate from 3 cache-busted runs], exceeding the 2.5 s threshold."
            })

    # Rule 6: Leads = 0 for 30 days while organic sessions > 100 -> Review CTAs/contact form
    organic_sessions = ga4.get("organic_sessions", {}).get("current", 0)
    lead_totals = ga4.get("key_events", {}).get("totals", {})
    total_leads = lead_totals.get("generate_lead", 0) + lead_totals.get("sample_request", 0)
    if organic_sessions > 100 and total_leads == 0:
        recs.append({
            "severity": "HIGH",
            "rule": "Zero Conversion with High Traffic",
            "message": f"Review CTAs/contact form: observed {organic_sessions} organic sessions but 0 leads generated over the last 28 days."
        })

    out_data = {
        "status": "SUCCESS",
        "total_recommendations": len(recs),
        "recommendations": recs,
        "not_yet_ranking": not_yet_ranking
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(out_data, f, indent=2)

    print(f"Generated {len(recs)} rule-based recommendations and {len(not_yet_ranking)} not-yet-ranking items, saved to {OUTPUT_FILE}")
    return out_data

if __name__ == "__main__":
    generate_recommendations()
