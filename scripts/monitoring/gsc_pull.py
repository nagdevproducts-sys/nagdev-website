import os
import sys
import json
import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SITE_URL = "sc-domain:nagdevproducts.com"
OUTPUT_DIR = Path("monitoring_output")
OUTPUT_FILE = OUTPUT_DIR / "gsc_data.json"
KEYWORDS_FILE = Path("seo/keywords.csv")

TOP_15_URLS = [
    "https://www.nagdevproducts.com/",
    "https://www.nagdevproducts.com/products",
    "https://www.nagdevproducts.com/about",
    "https://www.nagdevproducts.com/contact",
    "https://www.nagdevproducts.com/castor-oil-manufacturer-gujarat",
    "https://www.nagdevproducts.com/castor-oil-exporter-india",
    "https://www.nagdevproducts.com/castor-oil-derivatives",
    "https://www.nagdevproducts.com/bulk-castor-oil-supply",
    "https://www.nagdevproducts.com/products/fsg-castor-oil",
    "https://www.nagdevproducts.com/products/commercial-castor-oil",
    "https://www.nagdevproducts.com/products/hydrogenated-castor-oil",
    "https://www.nagdevproducts.com/products/12-hydroxystearic-acid",
    "https://www.nagdevproducts.com/products/castor-cake",
    "https://www.nagdevproducts.com/chemistry-tree",
    "https://www.nagdevproducts.com/infrastructure"
]

def get_service():
    sa_json = os.environ.get("GOOGLE_SA_JSON")
    if not sa_json:
        raise ValueError("Environment variable GOOGLE_SA_JSON is not set.")
    try:
        sa_info = json.loads(sa_json)
    except Exception as e:
        raise ValueError(f"Failed to parse GOOGLE_SA_JSON: {e}")
    
    credentials = service_account.Credentials.from_service_account_info(
        sa_info,
        scopes=["https://www.googleapis.com/auth/webmasters.readonly"]
    )
    return build("searchconsole", "v1", credentials=credentials, cache_discovery=False)

def query_search_analytics(service, start_date, end_date, dimensions=None, row_limit=25):
    request_body = {
        "startDate": start_date,
        "endDate": end_date,
        "rowLimit": row_limit
    }
    if dimensions:
        request_body["dimensions"] = dimensions
    try:
        response = service.searchanalytics().query(siteUrl=SITE_URL, body=request_body).execute()
        return response.get("rows", [])
    except HttpError as e:
        print(f"Error querying searchanalytics ({dimensions}): {e}", file=sys.stderr)
        return []

def inspect_url(service, url):
    try:
        body = {
            "inspectionUrl": url,
            "siteUrl": SITE_URL
        }
        res = service.urlInspection().index().inspect(body=body).execute()
        result = res.get("inspectionResult", {})
        index_status = result.get("indexStatusResult", {})
        return {
            "url": url,
            "verdict": index_status.get("verdict", "UNKNOWN"),
            "coverage_state": index_status.get("coverageState", "UNKNOWN"),
            "last_crawl_time": index_status.get("lastCrawlTime", "UNKNOWN"),
            "page_fetch_state": index_status.get("pageFetchState", "UNKNOWN"),
            "indexing_state": index_status.get("indexingState", "UNKNOWN")
        }
    except Exception as e:
        return {
            "url": url,
            "verdict": "ERROR",
            "coverage_state": str(e),
            "last_crawl_time": "N/A"
        }

def run_pull():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_data = {
        "status": "SUCCESS",
        "pulled_at": datetime.now(timezone.utc).isoformat(),
        "property": SITE_URL,
        "periods": {},
        "summary": {},
        "top_queries": [],
        "top_pages": [],
        "keyword_rankings": [],
        "url_inspections": []
    }
    
    try:
        service = get_service()
    except Exception as e:
        out_data["status"] = "ERROR"
        out_data["error"] = str(e)
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(out_data, f, indent=2)
        print(f"GSC pull failed to initialize: {e}")
        return out_data

    # GSC data has a 3-day latency
    today = datetime.now(timezone.utc).date()
    end_curr = today - timedelta(days=3)
    start_curr = end_curr - timedelta(days=27)
    
    end_prev = start_curr - timedelta(days=1)
    start_prev = end_prev - timedelta(days=27)
    
    curr_start_str = start_curr.isoformat()
    curr_end_str = end_curr.isoformat()
    prev_start_str = start_prev.isoformat()
    prev_end_str = end_prev.isoformat()
    
    out_data["periods"] = {
        "current_28d": {"start": curr_start_str, "end": curr_end_str},
        "previous_28d": {"start": prev_start_str, "end": prev_end_str}
    }
    
    print(f"GSC Pulling current: {curr_start_str} to {curr_end_str}")
    print(f"GSC Pulling previous: {prev_start_str} to {prev_end_str}")
    
    # Overall summary
    curr_summary_rows = query_search_analytics(service, curr_start_str, curr_end_str)
    prev_summary_rows = query_search_analytics(service, prev_start_str, prev_end_str)
    
    def parse_summary_row(rows):
        if not rows:
            return {"clicks": 0, "impressions": 0, "ctr": 0.0, "position": 0.0}
        r = rows[0]
        return {
            "clicks": int(r.get("clicks", 0)),
            "impressions": int(r.get("impressions", 0)),
            "ctr": round(float(r.get("ctr", 0.0)) * 100, 2),
            "position": round(float(r.get("position", 0.0)), 1)
        }
        
    curr_summary = parse_summary_row(curr_summary_rows)
    prev_summary = parse_summary_row(prev_summary_rows)
    out_data["summary"] = {
        "current": curr_summary,
        "previous": prev_summary
    }
    
    # Top 25 queries
    query_rows = query_search_analytics(service, curr_start_str, curr_end_str, dimensions=["query"], row_limit=25)
    for r in query_rows:
        out_data["top_queries"].append({
            "query": r["keys"][0],
            "clicks": int(r.get("clicks", 0)),
            "impressions": int(r.get("impressions", 0)),
            "ctr": round(float(r.get("ctr", 0.0)) * 100, 2),
            "position": round(float(r.get("position", 0.0)), 1)
        })
        
    # Top 25 pages
    page_rows = query_search_analytics(service, curr_start_str, curr_end_str, dimensions=["page"], row_limit=25)
    for r in page_rows:
        out_data["top_pages"].append({
            "page": r["keys"][0],
            "clicks": int(r.get("clicks", 0)),
            "impressions": int(r.get("impressions", 0)),
            "ctr": round(float(r.get("ctr", 0.0)) * 100, 2),
            "position": round(float(r.get("position", 0.0)), 1)
        })

    # Track keywords from seo/keywords.csv
    # First fetch all queries in current 28d up to 1000
    all_queries = query_search_analytics(service, curr_start_str, curr_end_str, dimensions=["query"], row_limit=1000)
    query_map = {r["keys"][0].lower().strip(): r for r in all_queries}
    
    keywords_list = []
    if KEYWORDS_FILE.exists():
        with open(KEYWORDS_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                keywords_list.append(row)
                
    for kw_entry in keywords_list:
        kw = kw_entry.get("keyword", "")
        kw_lower = kw.lower().strip()
        matched = query_map.get(kw_lower)
        if matched:
            out_data["keyword_rankings"].append({
                "keyword": kw,
                "cluster": kw_entry.get("cluster", ""),
                "priority": kw_entry.get("priority", ""),
                "target_url": kw_entry.get("target_url", ""),
                "clicks": int(matched.get("clicks", 0)),
                "impressions": int(matched.get("impressions", 0)),
                "ctr": round(float(matched.get("ctr", 0.0)) * 100, 2),
                "position": round(float(matched.get("position", 0.0)), 1),
                "status": "RANKING"
            })
        else:
            out_data["keyword_rankings"].append({
                "keyword": kw,
                "cluster": kw_entry.get("cluster", ""),
                "priority": kw_entry.get("priority", ""),
                "target_url": kw_entry.get("target_url", ""),
                "clicks": 0,
                "impressions": 0,
                "ctr": 0.0,
                "position": 0.0,
                "status": "NO_IMPRESSIONS"
            })

    # Top 15 URL Inspections
    print("Inspecting 15 priority URLs via URL Inspection API...")
    for u in TOP_15_URLS:
        insp = inspect_url(service, u)
        out_data["url_inspections"].append(insp)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(out_data, f, indent=2)

    print(f"GSC data successfully saved to {OUTPUT_FILE}")
    return out_data

if __name__ == "__main__":
    run_pull()
