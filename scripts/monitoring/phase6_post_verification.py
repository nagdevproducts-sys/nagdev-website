import json
import os
import statistics
import time
import urllib.request
import urllib.parse

API_KEY = os.environ.get("PSI_API_KEY", "AIzaSyBirne_HTYNjeUjV69T1rvMzl8fijzyvcY")

PAGES = [
    {"name": "Homepage", "url": "https://www.nagdevproducts.com/"},
    {"name": "Products Catalog", "url": "https://www.nagdevproducts.com/products"},
    {"name": "FSG Castor Oil", "url": "https://www.nagdevproducts.com/products/first-special-grade-castor-oil"},
    {"name": "12-HSA", "url": "https://www.nagdevproducts.com/products/12-hydroxystearic-acid"},
    {"name": "Derivatives", "url": "https://www.nagdevproducts.com/castor-oil-derivatives"},
    {"name": "Gujarat Hub", "url": "https://www.nagdevproducts.com/castor-oil-manufacturer-gujarat"},
    {"name": "Exporter Hub", "url": "https://www.nagdevproducts.com/castor-oil-exporter-india"},
    {"name": "Bulk Supply Hub", "url": "https://www.nagdevproducts.com/bulk-castor-oil-supply"},
    {"name": "Contact", "url": "https://www.nagdevproducts.com/contact"},
    {"name": "Commercial Castor Oil", "url": "https://www.nagdevproducts.com/products/commercial-castor-oil"}
]

def run_psi_single(target_url):
    query = urllib.parse.urlencode({
        "url": target_url,
        "strategy": "mobile",
        "category": "performance",
        "key": API_KEY
    })
    api_endpoint = f"https://www.googleapis.com/pagespeedonline/v5/runPagespeed?{query}"
    req = urllib.request.Request(api_endpoint, headers={"User-Agent": "NagdevPerfRunner/6.0"})
    
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                lighthouse = data.get("lighthouseResult", {})
                cats = lighthouse.get("categories", {})
                audits = lighthouse.get("audits", {})
                
                perf_score = int(round((cats.get("performance", {}).get("score", 0) or 0) * 100))
                fcp = audits.get("first-contentful-paint", {}).get("numericValue", 0) or 0
                lcp = audits.get("largest-contentful-paint", {}).get("numericValue", 0) or 0
                cls = audits.get("cumulative-layout-shift", {}).get("numericValue", 0) or 0
                tbt = audits.get("total-blocking-time", {}).get("numericValue", 0) or 0
                
                return {
                    "score": perf_score,
                    "fcp_ms": round(fcp, 1),
                    "lcp_ms": round(lcp, 1),
                    "cls": round(cls, 3),
                    "tbt_ms": round(tbt, 1)
                }
        except Exception as e:
            print(f"    [Attempt {attempt+1}] Error querying PSI: {e}")
            time.sleep(5)
    raise RuntimeError(f"Failed to fetch PSI for {target_url}")

def main():
    print("=" * 70)
    print("PHASE 6 POST-DEPLOY VERIFICATION (PSI API, Mobile, 3 Runs, Median)")
    print("=" * 70)
    
    results = []
    
    for page in PAGES:
        url = page["url"]
        name = page["name"]
        print(f"\nEvaluating: {name} ({url})")
        
        runs = []
        for r in range(1, 4):
            print(f"  Run {r}/3...", end=" ", flush=True)
            res = run_psi_single(url)
            runs.append(res)
            print(f"Score: {res['score']} | LCP: {res['lcp_ms']}ms | FCP: {res['fcp_ms']}ms | TBT: {res['tbt_ms']}ms")
            if r < 3:
                time.sleep(3)
        
        scores = [r["score"] for r in runs]
        lcps = [r["lcp_ms"] for r in runs]
        fcps = [r["fcp_ms"] for r in runs]
        clss = [r["cls"] for r in runs]
        tbts = [r["tbt_ms"] for r in runs]
        
        med_score = int(round(statistics.median(scores)))
        med_lcp = round(statistics.median(lcps), 1)
        med_fcp = round(statistics.median(fcps), 1)
        med_cls = round(statistics.median(clss), 3)
        med_tbt = round(statistics.median(tbts), 1)
        
        res_summary = {
            "name": name,
            "url": url,
            "median_score": med_score,
            "median_lcp_ms": med_lcp,
            "median_fcp_ms": med_fcp,
            "median_cls": med_cls,
            "median_tbt_ms": med_tbt,
            "all_runs": runs
        }
        results.append(res_summary)
        print(f"  => MEDIAN: Score: {med_score} | LCP: {med_lcp}ms | FCP: {med_fcp}ms | CLS: {med_cls} | TBT: {med_tbt}ms")
        time.sleep(3)
        
    os.makedirs("monitoring_output", exist_ok=True)
    with open("monitoring_output/phase6_post_verification.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\nSaved full verification data to monitoring_output/phase6_post_verification.json")

if __name__ == "__main__":
    main()
