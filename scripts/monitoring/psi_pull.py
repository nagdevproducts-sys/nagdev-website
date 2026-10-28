import os
import sys
import json
import time
import statistics
import requests
from datetime import datetime, timezone
from pathlib import Path

OUTPUT_DIR = Path("monitoring_output")
OUTPUT_FILE = OUTPUT_DIR / "psi_data.json"

TARGET_PAGES = [
    {"name": "Homepage (/)", "url": "https://www.nagdevproducts.com/"},
    {"name": "Products Catalog (/products)", "url": "https://www.nagdevproducts.com/products"},
    {"name": "FSG Castor Oil", "url": "https://www.nagdevproducts.com/products/first-special-grade-castor-oil"},
    {"name": "Commercial Castor Oil", "url": "https://www.nagdevproducts.com/products/commercial-castor-oil"},
    {"name": "Hydrogenated Castor Oil (HCO)", "url": "https://www.nagdevproducts.com/products/hydrogenated-castor-oil"},
    {"name": "12-HSA", "url": "https://www.nagdevproducts.com/products/12-hydroxystearic-acid"},
    {"name": "Contact (/contact)", "url": "https://www.nagdevproducts.com/contact"},
    {"name": "Hub 1: Gujarat Manufacturer", "url": "https://www.nagdevproducts.com/castor-oil-manufacturer-gujarat"},
    {"name": "Hub 2: Exporter India", "url": "https://www.nagdevproducts.com/castor-oil-exporter-india"},
    {"name": "Hub 3: Castor Oil Derivatives", "url": "https://www.nagdevproducts.com/castor-oil-derivatives"},
    {"name": "Hub 4: Bulk Supply", "url": "https://www.nagdevproducts.com/bulk-castor-oil-supply"}
]

API_ENDPOINT = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"

def fetch_single_psi(url, api_key=None, max_retries=3):
    params = {
        "url": url,
        "strategy": "mobile",
        "category": "performance"
    }
    if api_key:
        params["key"] = api_key
        
    for attempt in range(max_retries):
        try:
            resp = requests.get(API_ENDPOINT, params=params, timeout=60)
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
                    "tbt_ms": round(tbt)
                }
            elif resp.status_code in [429, 500, 503]:
                backoff = 5 * (2 ** attempt)
                print(f"    [PSI Retry] HTTP {resp.status_code}. Backing off {backoff}s...")
                time.sleep(backoff)
            else:
                return {"error": f"HTTP {resp.status_code}: {resp.text[:200]}"}
        except Exception as e:
            if attempt == max_retries - 1:
                return {"error": str(e)}
            backoff = 5 * (2 ** attempt)
            print(f"    [PSI Retry] Exception {e}. Backing off {backoff}s...")
            time.sleep(backoff)
    return {"error": "Max retries exceeded"}

def run_pull():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    api_key = os.environ.get("PSI_API_KEY", "").strip() or "AIzaSyBirne_HTYNjeUjV69T1rvMzl8fijzyvcY"
    
    out_data = {
        "status": "SUCCESS",
        "pulled_at": datetime.now(timezone.utc).isoformat(),
        "strategy": "mobile",
        "runs_per_page": 3,
        "results": []
    }
    
    print(f"Starting Mobile PageSpeed Insights pull for {len(TARGET_PAGES)} pages (3 runs each, median)...")
    for item in TARGET_PAGES:
        name = item["name"]
        url = item["url"]
        print(f"Testing {name} -> {url}...")
        
        scores = []
        fcps = []
        lcps = []
        clss = []
        tbts = []
        errors = []
        runs_detail = []
        
        for run_idx in range(3):
            # Cache-busting query to guarantee runs are independent
            ts = int(time.time())
            cache_bust = f"?psi={ts}-{run_idx + 1}"
            run_url = f"{url}{cache_bust}"
            print(f"  [Run {run_idx + 1}/3] Querying {run_url}...")
            res = fetch_single_psi(run_url, api_key=api_key)
            if "error" in res:
                errors.append(res["error"])
                runs_detail.append({"run": run_idx + 1, "url": run_url, "error": res["error"]})
                print(f"    Run {run_idx + 1} Error: {res['error']}")
            else:
                scores.append(res["score"])
                fcps.append(res["fcp_ms"])
                lcps.append(res["lcp_ms"])
                clss.append(res["cls"])
                tbts.append(res["tbt_ms"])
                runs_detail.append({
                    "run": run_idx + 1,
                    "url": run_url,
                    "score": res["score"],
                    "fcp_ms": res["fcp_ms"],
                    "lcp_ms": res["lcp_ms"],
                    "cls": res["cls"],
                    "tbt_ms": res["tbt_ms"]
                })
                print(f"    Run {run_idx + 1}: Score={res['score']}, LCP={res['lcp_ms']}ms, FCP={res['fcp_ms']}ms")
            time.sleep(15)  # 15s spacing between calls to respect rate limits
            
        if scores:
            median_score = round(statistics.median(scores))
            median_fcp = round(statistics.median(fcps))
            median_lcp = round(statistics.median(lcps))
            median_cls = round(statistics.median(clss), 3)
            median_tbt = round(statistics.median(tbts))
            
            out_data["results"].append({
                "name": name,
                "url": url,
                "median_score": median_score,
                "median_fcp_ms": median_fcp,
                "median_lcp_ms": median_lcp,
                "median_cls": median_cls,
                "median_tbt_ms": median_tbt,
                "all_scores": scores,
                "all_lcps": lcps,
                "all_fcps": fcps,
                "runs": runs_detail,
                "status": "OK"
            })
            print(f"  -> Median: Score: {median_score} (FCP: {median_fcp}ms, LCP: {median_lcp}ms, CLS: {median_cls}, TBT: {median_tbt}ms)")
        else:
            out_data["results"].append({
                "name": name,
                "url": url,
                "status": "ERROR",
                "errors": errors,
                "runs": runs_detail
            })
            print(f"  -> FAILED: {errors}")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(out_data, f, indent=2)

    print(f"PSI pull completed and saved to {OUTPUT_FILE}")
    return out_data

if __name__ == "__main__":
    run_pull()
