import os
import sys
import json
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

OUTPUT_DIR = Path("monitoring_output")
OUTPUT_FILE = OUTPUT_DIR / "site_health.json"
SITEMAP_URL = "https://www.nagdevproducts.com/sitemap.xml"

def get_sitemap_urls():
    urls = []
    try:
        resp = requests.get(SITEMAP_URL, timeout=15)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.content, "xml")
            for loc in soup.find_all("loc"):
                u = loc.text.strip()
                if u:
                    urls.append(u)
    except Exception as e:
        print(f"Error fetching live sitemap: {e}, falling back to local sitemap.xml", file=sys.stderr)
    
    if not urls:
        local_sitemap = Path("sitemap.xml")
        if local_sitemap.exists():
            soup = BeautifulSoup(local_sitemap.read_text(encoding="utf-8"), "xml")
            for loc in soup.find_all("loc"):
                u = loc.text.strip()
                if u:
                    urls.append(u)
    return urls

def normalize_url(url):
    parsed = urlparse(url)
    path = parsed.path.rstrip("/")
    if not path:
        path = "/"
    return f"{parsed.scheme}://{parsed.netloc}{path}"

def check_single_sitemap_url(u, session):
    try:
        resp = session.get(u, timeout=15, allow_redirects=True)
        chain = []
        if resp.history:
            chain = [r.url for r in resp.history] + [resp.url]
        
        internal_links = set()
        if resp.status_code == 200 and "text/html" in resp.headers.get("Content-Type", ""):
            soup = BeautifulSoup(resp.content, "html.parser")
            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                if not href or href.startswith(("#", "tel:", "mailto:", "javascript:")):
                    continue
                full_url = urljoin(u, href)
                p = urlparse(full_url)
                if p.netloc in ["nagdevproducts.com", "www.nagdevproducts.com", ""]:
                    norm = normalize_url(full_url)
                    internal_links.add(norm)
                    
        return {
            "url": u,
            "status_code": resp.status_code,
            "chain": chain,
            "internal_links": internal_links,
            "error": None
        }
    except Exception as e:
        return {
            "url": u,
            "status_code": None,
            "chain": [],
            "internal_links": set(),
            "error": str(e)
        }

def check_single_internal_link(link, session):
    try:
        r = session.head(link, timeout=10, allow_redirects=True)
        if r.status_code >= 400:
            r_get = session.get(link, timeout=10, stream=True)
            if r_get.status_code >= 400:
                return {"url": link, "status_code": r_get.status_code, "error": None}
        return None
    except Exception as e:
        return {"url": link, "status_code": None, "error": str(e)}

def run_health_check():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_data = {
        "status": "PASS",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "sitemap_check": {
            "total_urls": 0,
            "status_200_count": 0,
            "non_200_urls": [],
            "redirect_chains": []
        },
        "internal_links_check": {
            "total_links_found": 0,
            "unique_internal_links": 0,
            "broken_links": []
        },
        "claims_lint": {
            "status": "PASS",
            "hard_failures": 0,
            "warnings": 0,
            "rule_failures": {f"R{i}": 0 for i in range(1, 14)}
        }
    }

    # 1. Check all sitemap URLs concurrently
    sitemap_urls = get_sitemap_urls()
    out_data["sitemap_check"]["total_urls"] = len(sitemap_urls)
    print(f"Checking {len(sitemap_urls)} sitemap URLs concurrently...")
    
    internal_links_to_test = set()
    session = requests.Session()
    session.headers.update({"User-Agent": "NagdevSEOHealthMonitor/1.0"})

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(check_single_sitemap_url, u, session): u for u in sitemap_urls}
        for future in as_completed(futures):
            res = future.result()
            if res["error"]:
                out_data["sitemap_check"]["non_200_urls"].append({
                    "url": res["url"],
                    "error": res["error"]
                })
            elif res["chain"]:
                out_data["sitemap_check"]["redirect_chains"].append({
                    "url": res["url"],
                    "chain": res["chain"],
                    "final_status": res["status_code"]
                })
            elif res["status_code"] != 200:
                out_data["sitemap_check"]["non_200_urls"].append({
                    "url": res["url"],
                    "status_code": res["status_code"]
                })
            else:
                out_data["sitemap_check"]["status_200_count"] += 1
                
            internal_links_to_test.update(res["internal_links"])

    out_data["internal_links_check"]["total_links_found"] = len(internal_links_to_test)
    out_data["internal_links_check"]["unique_internal_links"] = len(internal_links_to_test)
    print(f"Checking {len(internal_links_to_test)} unique internal links concurrently...")

    # 2. Check internal links concurrently for 404s
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(check_single_internal_link, link, session): link for link in internal_links_to_test}
        for future in as_completed(futures):
            res = future.result()
            if res:
                out_data["internal_links_check"]["broken_links"].append(res)

    # 3. Claims linter execution
    print("Running production claims linter...")
    cmd = [sys.executable, "scripts/claims_lint.py", "--production"]
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    stdout = res.stdout
    
    # Parse rules R1-R13
    for i in range(1, 14):
        rule_key = f"R{i}"
        match = re.search(rf"\b{rule_key}:\s*(\d+)", stdout)
        if match:
            out_data["claims_lint"]["rule_failures"][rule_key] = int(match.group(1))

    # Parse hard failures and warnings
    hard_match = re.search(r"Production Hard Failures:\s*(\d+)", stdout)
    if hard_match:
        out_data["claims_lint"]["hard_failures"] = int(hard_match.group(1))
    warn_match = re.search(r"Production Warnings:\s*(\d+)", stdout)
    if warn_match:
        out_data["claims_lint"]["warnings"] = int(warn_match.group(1))

    if out_data["claims_lint"]["hard_failures"] > 0 or res.returncode != 0:
        out_data["claims_lint"]["status"] = "FAIL"

    # Overall pass/fail condition
    failures = []
    if out_data["sitemap_check"]["non_200_urls"]:
        failures.append(f"{len(out_data['sitemap_check']['non_200_urls'])} non-200 sitemap URLs")
    if out_data["sitemap_check"]["redirect_chains"]:
        failures.append(f"{len(out_data['sitemap_check']['redirect_chains'])} sitemap redirect chains")
    if out_data["internal_links_check"]["broken_links"]:
        failures.append(f"{len(out_data['internal_links_check']['broken_links'])} broken internal links")
    if out_data["claims_lint"]["status"] != "PASS":
        failures.append(f"{out_data['claims_lint']['hard_failures']} claims linter hard failures")

    if failures:
        out_data["status"] = "FAIL"
        out_data["failure_reasons"] = failures

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(out_data, f, indent=2)

    print(f"Site health check finished with status {out_data['status']}, saved to {OUTPUT_FILE}")
    return out_data

if __name__ == "__main__":
    run_health_check()
