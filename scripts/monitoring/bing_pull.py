import os
import sys
import json
import requests
from datetime import datetime, timezone
from pathlib import Path

OUTPUT_DIR = Path("monitoring_output")
OUTPUT_FILE = OUTPUT_DIR / "bing_data.json"
SITE_URL = "https://www.nagdevproducts.com"
BING_API_BASE = "https://ssl.bing.com/webmaster/api.svc/json"

def run_pull():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    api_key = os.environ.get("BING_API_KEY", "").strip()
    
    out_data = {
        "status": "SUCCESS",
        "pulled_at": datetime.now(timezone.utc).isoformat(),
        "site_url": SITE_URL,
        "query_stats": [],
        "crawl_stats": [],
        "summary": {}
    }
    
    if not api_key:
        out_data["status"] = "UNABLE"
        out_data["error"] = "BING_API_KEY environment variable is not set."
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(out_data, f, indent=2)
        print("Bing pull UNABLE: BING_API_KEY not set.")
        return out_data

    # 1. GetQueryStats
    try:
        url_queries = f"{BING_API_BASE}/GetQueryStats?siteUrl={SITE_URL}&apikey={api_key}"
        resp_q = requests.get(url_queries, timeout=30)
        if resp_q.status_code == 200:
            q_json = resp_q.json()
            # q_json usually has format {"d": [...]}
            rows = q_json.get("d", []) if isinstance(q_json, dict) else q_json
            out_data["query_stats"] = rows
            total_clicks = sum(r.get("Clicks", 0) for r in rows if isinstance(r, dict))
            total_impressions = sum(r.get("Impressions", 0) for r in rows if isinstance(r, dict))
            out_data["summary"]["total_clicks"] = total_clicks
            out_data["summary"]["total_impressions"] = total_impressions
        else:
            out_data["query_stats_error"] = f"HTTP {resp_q.status_code}: {resp_q.text[:300]}"
    except Exception as e:
        out_data["query_stats_error"] = str(e)

    # 2. GetCrawlStats
    try:
        url_crawl = f"{BING_API_BASE}/GetCrawlStats?siteUrl={SITE_URL}&apikey={api_key}"
        resp_c = requests.get(url_crawl, timeout=30)
        if resp_c.status_code == 200:
            c_json = resp_c.json()
            rows = c_json.get("d", []) if isinstance(c_json, dict) else c_json
            out_data["crawl_stats"] = rows
        else:
            out_data["crawl_stats_error"] = f"HTTP {resp_c.status_code}: {resp_c.text[:300]}"
    except Exception as e:
        out_data["crawl_stats_error"] = str(e)

    if "query_stats_error" in out_data and "crawl_stats_error" in out_data:
        out_data["status"] = "UNABLE"
        out_data["error"] = f"Query: {out_data['query_stats_error']}; Crawl: {out_data['crawl_stats_error']}"

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(out_data, f, indent=2)

    print(f"Bing pull finished with status {out_data['status']}, saved to {OUTPUT_FILE}")
    return out_data

if __name__ == "__main__":
    run_pull()
