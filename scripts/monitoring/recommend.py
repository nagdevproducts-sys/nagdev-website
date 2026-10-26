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

    # Rule 4: P1 keyword with no impressions -> Check targeting of <url>
    keyword_rankings = gsc.get("keyword_rankings", [])
    p1_no_impressions = [k for k in keyword_rankings if k.get("priority") == "P1" and k.get("impressions", 0) == 0]
    for k in p1_no_impressions[:5]: # Cap at top 5 to keep actionable
        kw = k.get("keyword", "")
        t_url = k.get("target_url", "")
        recs.append({
            "severity": "MEDIUM",
            "rule": "P1 Keyword Zero Impressions",
            "message": f"Check targeting of {t_url} for P1 keyword \"{kw}\": observed 0 impressions in last 28 days."
        })

    # Rule 5: PSI drop > 10 points or score < 80 -> Performance regression on <page>
    psi_results = psi.get("results", [])
    for pr in psi_results:
        score = pr.get("median_score")
        name = pr.get("name", "")
        url = pr.get("url", "")
        if score is not None and score < 80:
            recs.append({
                "severity": "MEDIUM",
                "rule": "Performance Regression",
                "message": f"Performance regression on {name} ({url}): median mobile score is {score}/100 (FCP: {pr.get('median_fcp_ms')}ms, LCP: {pr.get('median_lcp_ms')}ms, CLS: {pr.get('median_cls')})."
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
        "recommendations": recs
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(out_data, f, indent=2)

    print(f"Generated {len(recs)} rule-based recommendations, saved to {OUTPUT_FILE}")
    return out_data

if __name__ == "__main__":
    generate_recommendations()
