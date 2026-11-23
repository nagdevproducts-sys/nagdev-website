import os
import sys
import json
import time
import csv
import statistics
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path

OUTPUT_DIR = Path("monitoring_output")
OUTPUT_FILE = OUTPUT_DIR / "psi_data.json"
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
IST = timezone(timedelta(hours=5, minutes=30))

API_ENDPOINT = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"

def get_latest_blog_post():
    cal_path = REPO_ROOT / "seo" / "blog" / "calendar.csv"
    now_ist = datetime.now(IST)
    eligible = []
    if cal_path.exists():
        with open(cal_path, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                pub_dt = datetime.fromisoformat(row["publish_date"])
                if pub_dt <= now_ist and row.get("written") == "Y":
                    eligible.append((pub_dt, row["slug"], row.get("title", "")))
    if eligible:
        eligible.sort(key=lambda x: x[0], reverse=True)
        return eligible[0][1], eligible[0][2]
    return "hydrogenated-castor-oil-in-lithium-grease-formulation", "Latest Blog Post"

def get_target_pages():
    latest_slug, latest_title = get_latest_blog_post()
    return [
        {"name": "Homepage (/)", "url": "https://www.nagdevproducts.com/"},
        {"name": "Products Catalog (/products)", "url": "https://www.nagdevproducts.com/products"},
        {"name": "FSG Castor Oil", "url": "https://www.nagdevproducts.com/products/first-special-grade-castor-oil"},
        {"name": "Commercial Castor Oil", "url": "https://www.nagdevproducts.com/products/commercial-castor-oil"},
        {"name": f"Latest Blog Post ({latest_slug})", "url": f"https://www.nagdevproducts.com/blog/{latest_slug}"}
    ]

def fetch_single_psi(url, strategy="mobile", api_key=None, max_retries=2):
    params = {
        "url": url,
        "strategy": strategy,
        "category": "performance"
    }
    if api_key:
        params["key"] = api_key
        
    for attempt in range(max_retries):
        try:
            resp = requests.get(API_ENDPOINT, params=params, timeout=45)
            if resp.status_code == 200:
                data = resp.json()
                lighthouse = data.get("lighthouseResult", {})
                categories = lighthouse.get("categories", {})
                perf = categories.get("performance", {})
                score = round(float(perf.get("score", 0)) * 100)
                
                audits = lighthouse.get("audits", {})
                fcp = audits.get("first-contentful-paint", {}).get("numericValue", 0)
                lcp = audits.get("largest-contentful-paint", {}).get("numericValue", 0)
                cls = audits.get("cumulative-layout-shift", {}).get("numericValue", 0)
                tbt = audits.get("total-blocking-time", {}).get("numericValue", 0)
                
                return {
                    "score": score,
                    "fcp_ms": round(fcp),
                    "lcp_ms": round(lcp),
                    "cls": round(cls, 3),
                    "tbt_ms": round(tbt),
                    "error": None
                }
            elif resp.status_code == 429:
                print(f"    [PSI Rate Limit] HTTP 429 on {strategy} for {url}. Backing off...")
                if attempt < max_retries - 1:
                    time.sleep(10)
                else:
                    return {"score": None, "error": f"Rate-limited (HTTP 429): {resp.text[:100]}", "is_monitor_error": True}
            elif resp.status_code in [500, 502, 503]:
                print(f"    [PSI Server Error] HTTP {resp.status_code}. Retrying...")
                time.sleep(5)
            else:
                return {"score": None, "error": f"HTTP {resp.status_code}: {resp.text[:100]}", "is_monitor_error": True}
        except Exception as e:
            if attempt == max_retries - 1:
                return {"score": None, "error": f"Network/Timeout error: {str(e)}", "is_monitor_error": True}
            time.sleep(5)
    return {"score": None, "error": "Max retries exceeded", "is_monitor_error": True}

def run_pull():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    api_key = os.environ.get("PSI_API_KEY", "").strip()
if not api_key:
    print("[NOTICE] PSI_API_KEY environment variable is not set. Skipping PageSpeed pull.")
    import sys; sys.exit(0)
    target_pages = get_target_pages()
    
    out_data = {
        "status": "SUCCESS",
        "pulled_at": datetime.now(timezone.utc).isoformat(),
        "sample_pages_count": len(target_pages),
        "strategies": ["mobile", "desktop"],
        "results": [],
        "monitor_errors": []
    }
    
    print(f"Starting Fixed-Sample PageSpeed Insights pull for {len(target_pages)} pages (mobile + desktop)...")
    for item in target_pages:
        name = item["name"]
        url = item["url"]
        print(f"\nTesting {name} -> {url}:")
        
        for strategy in ["mobile", "desktop"]:
            print(f"  [{strategy.upper()}] Querying PSI API...")
            res = fetch_single_psi(url, strategy=strategy, api_key=api_key)
            if res.get("error"):
                print(f"    Notice: {res['error']}")
                out_data["monitor_errors"].append({
                    "url": url,
                    "strategy": strategy,
                    "error": res["error"],
                    "is_monitor_error": res.get("is_monitor_error", True)
                })
            else:
                print(f"    Score: {res['score']}, LCP: {res['lcp_ms']}ms, FCP: {res['fcp_ms']}ms, CLS: {res['cls']}")
                out_data["results"].append({
                    "name": name,
                    "url": url,
                    "strategy": strategy,
                    "score": res["score"],
                    "median_score": res["score"],
                    "fcp_ms": res["fcp_ms"],
                    "lcp_ms": res["lcp_ms"],
                    "cls": res["cls"],
                    "tbt_ms": res["tbt_ms"],
                    "status": "OK"
                })
            time.sleep(3)  # Gentle spacing between calls to stay well within quota
            
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(out_data, f, indent=2)
        
    print(f"\nPageSpeed Insights pull finished. Saved to {OUTPUT_FILE}")
    print(f"Valid results: {len(out_data['results'])}, Monitor errors: {len(out_data['monitor_errors'])}")
    return out_data

if __name__ == "__main__":
    run_pull()
