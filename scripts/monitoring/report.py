import json
import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

OUTPUT_DIR = Path("monitoring_output")
REPORT_FILE = OUTPUT_DIR / "monthly_report.md"
CITATIONS_FILE = Path("seo/authority/citations.csv")

def load_json(name):
    p = OUTPUT_DIR / name
    if p.exists():
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            return {"status": "ERROR", "error": f"Failed to load {name}: {e}"}
    return {"status": "ERROR", "error": f"{name} not found"}

def get_pending_citations():
    pending = []
    if CITATIONS_FILE.exists():
        with open(CITATIONS_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                st = row.get("status", "")
                if "PENDING" in st:
                    pending.append(f"{row.get('platform', '')} ({st})")
    return pending

def build_report():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    gsc = load_json("gsc_data.json")
    ga4 = load_json("ga4_data.json")
    psi = load_json("psi_data.json")
    bing = load_json("bing_data.json")
    health = load_json("site_health.json")
    recs = load_json("recommendations.json")
    
    now = datetime.now(timezone.utc)
    month_name = now.strftime("%B %Y")
    
    lines = []
    lines.append(f"# SEO Monthly Report – {month_name}")
    lines.append(f"**Generated at:** {now.strftime('%Y-%m-%d %H:%M:%S UTC')} | **Domain:** nagdevproducts.com\n")
    
    # ----------------------------------------------------
    # 1. Summary KPIs vs KPI Dashboard targets
    # ----------------------------------------------------
    lines.append("## 1. Summary KPIs vs Targets")
    
    # Extract actuals
    gsc_curr = gsc.get("summary", {}).get("current", {})
    gsc_prev = gsc.get("summary", {}).get("previous", {})
    clicks_curr = gsc_curr.get("clicks", 0)
    clicks_prev = gsc_prev.get("clicks", 0)
    imp_curr = gsc_curr.get("impressions", 0)
    imp_prev = gsc_prev.get("impressions", 0)
    ctr_curr = gsc_curr.get("ctr", 0.0)
    pos_curr = gsc_curr.get("position", 0.0)
    
    # GSC Indexed pages from inspections or summary
    inspections = gsc.get("url_inspections", [])
    indexed_count = sum(1 for i in inspections if i.get("verdict") == "PASS")
    
    # P1 rank count in top 10
    kw_ranks = gsc.get("keyword_rankings", [])
    p1_top_10 = sum(1 for k in kw_ranks if k.get("priority") == "P1" and 0 < k.get("position", 0) <= 10.0)
    local_top_3 = sum(1 for k in kw_ranks if k.get("cluster") == "Gujarat & local" and 0 < k.get("position", 0) <= 3.0)
    
    # GA4 Metrics
    org_sessions_curr = ga4.get("organic_sessions", {}).get("current", 0)
    org_sessions_prev = ga4.get("organic_sessions", {}).get("previous", 0)
    ai_sessions = ga4.get("ai_referral_sessions", {}).get("total", 0)
    key_events = ga4.get("key_events", {}).get("totals", {})
    leads_count = key_events.get("generate_lead", 0) + key_events.get("whatsapp_click", 0)
    sample_count = key_events.get("sample_request", 0)
    
    lines.append("| Metric | Latest Actual (28d) | M6 Target | M12 Target | Status |")
    lines.append("| :--- | :--- | :--- | :--- | :--- |")
    lines.append(f"| **Organic Impressions** | {imp_curr:,} (prev: {imp_prev:,}) | 5,000 | 25,000 | {'🟢 On Track' if imp_curr >= 5000 else '🟡 Progressing'} |")
    lines.append(f"| **Organic Clicks** | {clicks_curr:,} (prev: {clicks_prev:,}) | 150 | 800 | {'🟢 On Track' if clicks_curr >= 150 else '🟡 Progressing'} |")
    lines.append(f"| **Organic Sessions (GA4)** | {org_sessions_curr:,} (prev: {org_sessions_prev:,}) | — | — | Active |")
    lines.append(f"| **AI Referral Sessions** | {ai_sessions} | 10 | 60 | {'🟢 On Track' if ai_sessions >= 10 else '🟡 Building'} |")
    lines.append(f"| **P1 Keywords in Top 10** | {p1_top_10} | 5 | 12 | {'🟢 On Track' if p1_top_10 >= 5 else '🟡 Building'} |")
    lines.append(f"| **Local Terms in Top 3** | {local_top_3} | 3 | 6 | {'🟢 On Track' if local_top_3 >= 3 else '🟡 Building'} |")
    lines.append(f"| **Qualified RFQs / Leads** | {leads_count} | 8 | 25 | {'🟢 On Track' if leads_count >= 8 else '🟡 Building'} |")
    lines.append(f"| **Sample / TDS Requests** | {sample_count} | 10 | 30 | {'🟢 On Track' if sample_count >= 10 else '🟡 Building'} |")
    lines.append("")

    # ----------------------------------------------------
    # 2. Search (Google Search Console)
    # ----------------------------------------------------
    lines.append("## 2. Google Search Console Performance")
    if gsc.get("status") == "ERROR":
        lines.append(f"> ⚠️ **UNAVAILABLE:** {gsc.get('error')}\n")
    else:
        periods = gsc.get("periods", {})
        curr_p = periods.get("current_28d", {})
        prev_p = periods.get("previous_28d", {})
        lines.append(f"**Current Period:** {curr_p.get('start')} to {curr_p.get('end')} (28 days)")
        lines.append(f"**Previous Period:** {prev_p.get('start')} to {prev_p.get('end')} (28 days)\n")
        
        lines.append("| Metric | Current 28d | Previous 28d | Change |")
        lines.append("| :--- | :--- | :--- | :--- |")
        lines.append(f"| Clicks | {clicks_curr:,} | {clicks_prev:,} | {clicks_curr - clicks_prev:+d} |")
        lines.append(f"| Impressions | {imp_curr:,} | {imp_prev:,} | {imp_curr - imp_prev:+d} |")
        lines.append(f"| CTR | {ctr_curr}% | {gsc_prev.get('ctr', 0.0)}% | {ctr_curr - gsc_prev.get('ctr', 0.0):+.2f}% |")
        lines.append(f"| Average Position | {pos_curr} | {gsc_prev.get('position', 0.0)} | {pos_curr - gsc_prev.get('position', 0.0):+.1f} |")
        lines.append("")
        
        # Top Queries
        top_q = gsc.get("top_queries", [])
        lines.append("### Top 25 Queries")
        if top_q:
            lines.append("| # | Query | Clicks | Impressions | CTR | Position |")
            lines.append("| :- | :--- | :--- | :--- | :--- | :--- |")
            for idx, q in enumerate(top_q[:25], start=1):
                lines.append(f"| {idx} | `{q['query']}` | {q['clicks']} | {q['impressions']} | {q['ctr']}% | {q['position']} |")
        else:
            lines.append("_No query data available for this period._")
        lines.append("")

        # Top Pages
        top_p = gsc.get("top_pages", [])
        lines.append("### Top 25 Pages")
        if top_p:
            lines.append("| # | Page URL | Clicks | Impressions | CTR | Position |")
            lines.append("| :- | :--- | :--- | :--- | :--- | :--- |")
            for idx, p in enumerate(top_p[:25], start=1):
                clean_url = p['page'].replace("https://www.nagdevproducts.com", "") or "/"
                lines.append(f"| {idx} | `{clean_url}` | {p['clicks']} | {p['impressions']} | {p['ctr']}% | {p['position']} |")
        else:
            lines.append("_No page data available for this period._")
        lines.append("")

        # URL Inspection
        lines.append("### URL Inspection Coverage (15 Key Pages)")
        if inspections:
            lines.append("| Page | Verdict | Coverage State | Last Crawl Time |")
            lines.append("| :--- | :--- | :--- | :--- |")
            for insp in inspections:
                u_clean = insp['url'].replace("https://www.nagdevproducts.com", "") or "/"
                lines.append(f"| `{u_clean}` | {insp.get('verdict')} | {insp.get('coverage_state')} | {insp.get('last_crawl_time')} |")
        else:
            lines.append("_No URL inspection records._")
        lines.append("")

    # ----------------------------------------------------
    # 3. Bing Webmaster Tools
    # ----------------------------------------------------
    lines.append("## 3. Bing Webmaster Tools")
    if bing.get("status") == "UNABLE":
        lines.append(f"> ⚠️ **UNAVAILABLE:** {bing.get('error')}\n")
    else:
        q_stats = bing.get("query_stats", [])
        c_stats = bing.get("crawl_stats", [])
        b_summary = bing.get("summary", {})
        lines.append(f"- **Total Bing Clicks:** {b_summary.get('total_clicks', 0)}")
        lines.append(f"- **Total Bing Impressions:** {b_summary.get('total_impressions', 0)}")
        lines.append(f"- **Crawl Stats Recorded:** {len(c_stats)} periods")
        if q_stats:
            lines.append("\n| Query | Clicks | Impressions | Avg Position |")
            lines.append("| :--- | :--- | :--- | :--- |")
            for q in q_stats[:10]:
                lines.append(f"| `{q.get('Query', '')}` | {q.get('Clicks', 0)} | {q.get('Impressions', 0)} | {q.get('AvgImpressionPosition', 0.0)} |")
        lines.append("")

    # ----------------------------------------------------
    # 4. Traffic & AI Referrals (GA4)
    # ----------------------------------------------------
    lines.append("## 4. Traffic & AI Referrals (GA4)")
    if ga4.get("status") == "ERROR":
        lines.append(f"> ⚠️ **UNAVAILABLE:** {ga4.get('error')}\n")
    else:
        channels_curr = ga4.get("channel_groups", {}).get("current", {})
        channels_prev = ga4.get("channel_groups", {}).get("previous", {})
        lines.append("### Sessions by Default Channel Group")
        lines.append("| Channel Group | Current 28d | Previous 28d |")
        lines.append("| :--- | :--- | :--- |")
        for ch, count in sorted(channels_curr.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"| {ch} | {count:,} | {channels_prev.get(ch, 0):,} |")
        lines.append("")

        lines.append("### AI Referral Sessions")
        ai_ref = ga4.get("ai_referral_sessions", {})
        lines.append(f"- **Total AI Referrals:** {ai_ref.get('total', 0)} sessions")
        by_src = ai_ref.get("by_source", {})
        if by_src:
            lines.append("| AI Source | Sessions |")
            lines.append("| :--- | :--- |")
            for src, cnt in by_src.items():
                lines.append(f"| `{src}` | {cnt} |")
        else:
            lines.append("_No AI-referral sessions recorded in this period._")
        lines.append("")

        lines.append("### Top 10 Countries by Session")
        top_countries = ga4.get("top_countries", [])
        if top_countries:
            lines.append("| # | Country | Sessions |")
            lines.append("| :- | :--- | :--- |")
            for idx, c in enumerate(top_countries, start=1):
                lines.append(f"| {idx} | {c['country']} | {c['sessions']:,} |")
        else:
            lines.append("_No country data available._")
        lines.append("")

    # ----------------------------------------------------
    # 5. Leads by Product & Conversion
    # ----------------------------------------------------
    lines.append("## 5. Conversions & Leads by Landing Page")
    if ga4.get("status") == "ERROR":
        lines.append(f"> ⚠️ **UNAVAILABLE:** {ga4.get('error')}\n")
    else:
        events = ga4.get("key_events", {})
        totals = events.get("totals", {})
        lines.append(f"- **generate_lead:** {totals.get('generate_lead', 0)}")
        lines.append(f"- **sample_request:** {totals.get('sample_request', 0)}")
        lines.append(f"- **whatsapp_click:** {totals.get('whatsapp_click', 0)}")
        lines.append(f"- **tds_download:** {events.get('tds_downloads', {}).get('total', 0)}\n")

        by_page = events.get("by_landing_page", [])
        if by_page:
            lines.append("| Event | Landing Page | Count |")
            lines.append("| :--- | :--- | :--- |")
            for ev in by_page:
                lines.append(f"| `{ev['event_name']}` | `{ev['landing_page']}` | {ev['count']} |")
        else:
            lines.append("_No event conversions recorded on landing pages in this period._")
        lines.append("")

    # ----------------------------------------------------
    # 6. Keywords P1 Table
    # ----------------------------------------------------
    lines.append("## 6. Priority Keywords Tracker (P1)")
    p1_keywords = [k for k in gsc.get("keyword_rankings", []) if k.get("priority") == "P1"]
    if p1_keywords:
        lines.append("| Keyword | Cluster | Target URL | Impressions | Clicks | CTR | Position |")
        lines.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
        for k in p1_keywords:
            lines.append(f"| {k['keyword']} | {k['cluster']} | `{k['target_url']}` | {k['impressions']} | {k['clicks']} | {k['ctr']}% | {k['position']} |")
    else:
        lines.append("_No P1 keywords tracked or GSC rankings unavailable._")
    lines.append("")

    # ----------------------------------------------------
    # 7. Mobile Performance (PageSpeed Insights)
    # ----------------------------------------------------
    lines.append("## 7. Performance (PageSpeed Insights Mobile)")
    if psi.get("status") == "ERROR":
        lines.append(f"> ⚠️ **UNAVAILABLE:** {psi.get('error')}\n")
    else:
        psi_results = psi.get("results", [])
        lines.append("| Page Tested | Mobile Score (0-100) | FCP (ms) | LCP (ms) | CLS | TBT (ms) | Status |")
        lines.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
        for r in psi_results:
            if r.get("status") == "OK":
                s = r['median_score']
                badge = "🟢" if s >= 90 else ("🟡" if s >= 75 else "🔴")
                lines.append(f"| {r['name']} | {badge} **{s}** | {r['median_fcp_ms']:,} | {r['median_lcp_ms']:,} | {r['median_cls']} | {r['median_tbt_ms']:,} | PASS |")
            else:
                lines.append(f"| {r['name']} | — | — | — | — | — | ❌ ERROR |")
        lines.append("")

    # ----------------------------------------------------
    # 8. Site Health & Claims Gate
    # ----------------------------------------------------
    lines.append("## 8. Site Health & Claims Gate")
    s_chk = health.get("sitemap_check", {})
    l_chk = health.get("internal_links_check", {})
    c_chk = health.get("claims_lint", {})
    overall_health = health.get("status", "UNKNOWN")
    health_badge = "🟢 PASS" if overall_health == "PASS" else "🔴 FAIL"
    
    lines.append(f"**Overall Site Health Status:** {health_badge}\n")
    lines.append(f"- **Sitemap URLs Validated:** {s_chk.get('status_200_count', 0)} / {s_chk.get('total_urls', 0)} (All return HTTP 200: {'Yes' if not s_chk.get('non_200_urls') else 'No'})")
    lines.append(f"- **Redirect Chains:** {len(s_chk.get('redirect_chains', []))}")
    lines.append(f"- **Broken Internal Links:** {len(l_chk.get('broken_links', []))} (out of {l_chk.get('total_links_found', 0)} checked)")
    lines.append(f"- **Production Claims Linter:** {c_chk.get('status', 'N/A')} (Hard failures: {c_chk.get('hard_failures', 0)}, Warnings: {c_chk.get('warnings', 0)})\n")
    
    rule_fails = c_chk.get("rule_failures", {})
    if rule_fails:
        lines.append("| Rule | Rule Description | Failures |")
        lines.append("| :--- | :--- | :--- |")
        rule_desc = {
            "R1": "Plant capacity (50 TPD max)",
            "R2": "Forbidden equipment claims",
            "R3": "Forbidden accreditations (ISO/GMP/FSSC/REACH)",
            "R4": "Forbidden downstream specialties (sebacic/undecylenic)",
            "R5": "Purity claims (pure/100% pure)",
            "R6": "Sustainability/circularity claims",
            "R7": "Forbidden corporate structure claims",
            "R8": "Forbidden awards & historical longevity",
            "R9": "Forbidden lab capabilities & client lists",
            "R10": "Market data sources (Agmarknet/SEA)",
            "R11": "Oil content & processing parity claims",
            "R12": "Future-dated market reports",
            "R13": "Required HTML tracking & header/footer"
        }
        for r_code, count in rule_fails.items():
            lines.append(f"| `{r_code}` | {rule_desc.get(r_code, '')} | {count} |")
        lines.append("")

    # ----------------------------------------------------
    # 9. Recommendations
    # ----------------------------------------------------
    lines.append("## 9. Rule-Based Recommendations")
    rec_list = recs.get("recommendations", [])
    if rec_list:
        for idx, r in enumerate(rec_list, start=1):
            sev_badge = "🚨" if r["severity"] == "URGENT" else ("⚠️" if r["severity"] == "HIGH" else "💡")
            lines.append(f"{idx}. {sev_badge} **[{r['severity']}] {r['rule']}:** {r['message']}")
    else:
        lines.append("✅ _No critical issues detected. Site and search metrics are performing within expected baseline parameters._")
    lines.append("")

    # ----------------------------------------------------
    # 10. Owner Monthly Checklist (Section 5.5)
    # ----------------------------------------------------
    lines.append("## 10. Owner Monthly Checklist")
    lines.append("- [ ] **AI Visibility Check:** In ChatGPT (logged in, search on), Gemini and Perplexity, ask:")
    lines.append("  - \"Who is Nagdev Products?\"")
    lines.append("  - \"Castor oil manufacturer Deodar\"")
    lines.append("  - \"FSG castor oil manufacturer in Gujarat\"")
    lines.append("  - \"Hydrogenated castor oil manufacturer India\"")
    lines.append("  > *Comment on this Issue: platform → mentioned Y/N, cited Y/N.*")
    lines.append(f"- [ ] **Enquiry Response:** Reply to any new enquiries within 24 working hours (GA4 shows **{leads_count}** leads/events this month).")
    lines.append("- [ ] **Market Price Update:** Download the castor seed price CSV from [agmarknet.gov.in](https://agmarknet.gov.in) (Gujarat, markets Deesa / Palanpur / Tharad / Patan, previous month) and upload it to repo folder `seo/data/agmarknet/<YYYY-MM>/` via GitHub web upload.")
    
    pending_citations = get_pending_citations()
    lines.append(f"- [ ] **Pending Listings:** Review and complete pending authority citations:")
    if pending_citations:
        for p in pending_citations:
            lines.append(f"  - {p}")
    else:
        lines.append("  - None currently pending.")
    lines.append("")

    report_content = "\n".join(lines)
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(report_content)

    print(f"Monthly report written to {REPORT_FILE}")
    return report_content

if __name__ == "__main__":
    build_report()
