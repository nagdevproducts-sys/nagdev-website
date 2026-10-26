#!/usr/bin/env python3
"""
scripts/monitoring/phase6_baseline.py - Phase 6 Task 2 PSI Baseline & Diagnostic Analyzer.
Runs 3 mobile PSI iterations per page with spacing, computes median metrics,
and extracts deep LCP diagnostics (element, phases, render-blocking, main-thread work, bytes, 3rd party).
"""

import os
import sys
import json
import time
import statistics
import requests
from datetime import datetime, timezone
from pathlib import Path

API_KEY = os.environ.get("PSI_API_KEY", "").strip() or "AIzaSyBirne_HTYNjeUjV69T1rvMzl8fijzyvcY"
API_ENDPOINT = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
OUTPUT_FILE = Path("monitoring_output/phase6_task2_baseline.json")

PAGES = [
    # SLOW GROUP
    {"group": "SLOW", "name": "Homepage (/)", "url": "https://www.nagdevproducts.com/"},
    {"group": "SLOW", "name": "Catalog (/products)", "url": "https://www.nagdevproducts.com/products"},
    {"group": "SLOW", "name": "FSG Castor Oil", "url": "https://www.nagdevproducts.com/products/first-special-grade-castor-oil"},
    {"group": "SLOW", "name": "12-HSA", "url": "https://www.nagdevproducts.com/products/12-hydroxystearic-acid"},
    {"group": "SLOW", "name": "Derivatives (/castor-oil-derivatives)", "url": "https://www.nagdevproducts.com/castor-oil-derivatives"},
    {"group": "SLOW", "name": "Hub 1: Gujarat (/castor-oil-manufacturer-gujarat)", "url": "https://www.nagdevproducts.com/castor-oil-manufacturer-gujarat"},
    # FAST GROUP
    {"group": "FAST", "name": "Hub 2: Exporter (/castor-oil-exporter-india)", "url": "https://www.nagdevproducts.com/castor-oil-exporter-india"},
    {"group": "FAST", "name": "Hub 4: Bulk Supply (/bulk-castor-oil-supply)", "url": "https://www.nagdevproducts.com/bulk-castor-oil-supply"}
]

def fetch_psi(url, attempt_idx=0, max_retries=3):
    params = {
        "url": url,
        "strategy": "mobile",
        "category": "performance",
        "key": API_KEY
    }
    for attempt in range(max_retries):
        try:
            resp = requests.get(API_ENDPOINT, params=params, timeout=75)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code in [429, 500, 503]:
                wait = 5 * (2 ** attempt)
                print(f"      [Retry] HTTP {resp.status_code}. Backing off {wait}s...")
                time.sleep(wait)
            else:
                print(f"      [Error] HTTP {resp.status_code}: {resp.text[:150]}")
                return None
        except Exception as e:
            wait = 5 * (2 ** attempt)
            print(f"      [Exception] {e}. Backing off {wait}s...")
            time.sleep(wait)
    return None

def extract_run_data(raw_json):
    if not raw_json:
        return None
    lh = raw_json.get("lighthouseResult", {})
    audits = lh.get("audits", {})
    categories = lh.get("categories", {})
    
    perf = categories.get("performance", {})
    score = round(float(perf.get("score", 0)) * 100)
    
    fcp = audits.get("first-contentful-paint", {}).get("numericValue", 0)
    lcp = audits.get("largest-contentful-paint", {}).get("numericValue", 0)
    cls = audits.get("cumulative-layout-shift", {}).get("numericValue", 0)
    tbt = audits.get("total-blocking-time", {}).get("numericValue", 0)
    
    # LCP Element & Phases
    lcp_breakdown = audits.get("lcp-breakdown-insight", {}).get("details", {}).get("items", [])
    lcp_phases = {}
    lcp_node = {}
    for item in lcp_breakdown:
        if item.get("type") == "table":
            for sub in item.get("items", []):
                lcp_phases[sub.get("subpart")] = round(float(sub.get("duration", 0)), 1)
        elif item.get("type") == "node":
            lcp_node = {
                "selector": item.get("selector", ""),
                "snippet": item.get("snippet", ""),
                "nodeLabel": item.get("nodeLabel", "")
            }
            
    # LCP Discovery / Resource
    lcp_discovery = audits.get("lcp-discovery-insight", {})
    lcp_resource_url = None
    if lcp_discovery.get("details", {}).get("items"):
        lcp_resource_url = lcp_discovery["details"]["items"][0].get("url")

    # Render blocking
    rb_items = audits.get("render-blocking-resources", {}).get("details", {}).get("items", [])
    render_blocking = [{"url": r.get("url"), "bytes": r.get("totalBytes"), "wastedMs": r.get("wastedMs")} for r in rb_items]
    
    # Main thread work
    mt_items = audits.get("mainthread-work-breakdown", {}).get("details", {}).get("items", [])
    main_thread = [{"group": m.get("groupLabel"), "durationMs": round(m.get("duration", 0), 1)} for m in mt_items]
    
    # Total byte weight
    byte_weight = audits.get("total-byte-weight", {}).get("displayValue", "")
    byte_weight_num = audits.get("total-byte-weight", {}).get("numericValue", 0)
    
    # Third party summary
    tp_items = audits.get("third-party-summary", {}).get("details", {}).get("items", [])
    third_party = [{"entity": t.get("entity", {}).get("text"), "transferBytes": t.get("transferSize"), "blockingMs": t.get("blockingTime")} for t in tp_items]
    
    return {
        "score": score,
        "fcp_ms": round(fcp),
        "lcp_ms": round(lcp),
        "cls": round(cls, 3),
        "tbt_ms": round(tbt),
        "lcp_node": lcp_node,
        "lcp_resource_url": lcp_resource_url,
        "lcp_phases": lcp_phases,
        "render_blocking": render_blocking,
        "main_thread": main_thread,
        "total_byte_weight": byte_weight,
        "total_byte_weight_num": byte_weight_num,
        "third_party": third_party
    }

def run():
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    all_results = []
    
    print(f"Starting Phase 6 Task 2 Baseline for {len(PAGES)} pages (3 mobile runs each)...")
    for page_idx, page in enumerate(PAGES, 1):
        name = page["name"]
        url = page["url"]
        group = page["group"]
        print(f"\n[{page_idx}/{len(PAGES)}] [{group}] {name} -> {url}")
        
        runs = []
        for r_idx in range(1, 4):
            print(f"    Run {r_idx}/3...")
            raw = fetch_psi(url)
            parsed = extract_run_data(raw)
            if parsed:
                runs.append(parsed)
                print(f"      Run {r_idx} result: Score {parsed['score']}, LCP {parsed['lcp_ms']}ms, FCP {parsed['fcp_ms']}ms, TBT {parsed['tbt_ms']}ms")
            else:
                print(f"      Run {r_idx} failed.")
            if r_idx < 3:
                time.sleep(15)
                
        if runs:
            median_score = round(statistics.median([r["score"] for r in runs]))
            median_lcp = round(statistics.median([r["lcp_ms"] for r in runs]))
            median_fcp = round(statistics.median([r["fcp_ms"] for r in runs]))
            median_cls = round(statistics.median([r["cls"] for r in runs]), 3)
            median_tbt = round(statistics.median([r["tbt_ms"] for r in runs]))
            
            # Use the run closest to median LCP for detailed breakdowns
            best_run = min(runs, key=lambda r: abs(r["lcp_ms"] - median_lcp))
            
            summary = {
                "group": group,
                "name": name,
                "url": url,
                "median_score": median_score,
                "median_lcp_ms": median_lcp,
                "median_fcp_ms": median_fcp,
                "median_cls": median_cls,
                "median_tbt_ms": median_tbt,
                "diagnostics": {
                    "lcp_node": best_run["lcp_node"],
                    "lcp_resource_url": best_run["lcp_resource_url"],
                    "lcp_phases": best_run["lcp_phases"],
                    "render_blocking": best_run["render_blocking"],
                    "main_thread": best_run["main_thread"],
                    "total_byte_weight": best_run["total_byte_weight"],
                    "third_party": best_run["third_party"]
                },
                "all_runs": runs
            }
            all_results.append(summary)
            print(f"  ==> MEDIAN: Score {median_score} | LCP {median_lcp}ms | FCP {median_fcp}ms | CLS {median_cls} | TBT {median_tbt}ms")
        else:
            all_results.append({
                "group": group,
                "name": name,
                "url": url,
                "status": "ERROR"
            })
            print(f"  ==> FAILED all 3 runs.")
            
        time.sleep(15)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nAll baseline results saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    run()
