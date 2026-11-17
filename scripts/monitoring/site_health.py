import os
import sys
import json
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse
import xml.etree.ElementTree as ET

OUTPUT_DIR = Path("monitoring_output")
OUTPUT_FILE = OUTPUT_DIR / "site_health.json"
SITEMAP_URL = "https://www.nagdevproducts.com/sitemap.xml"

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

try:
    from claims_lint import RULES
except ImportError:
    RULES = {}

def get_session():
    session = requests.Session()
    session.headers.update({"User-Agent": "NagdevSEOHealthMonitor/1.0"})
    retries = Retry(total=2, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries, pool_connections=8, pool_maxsize=8)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

def get_sitemap_urls(session):
    urls = []
    try:
        resp = session.get(SITEMAP_URL, timeout=15)
        if resp.status_code == 200:
            root = ET.fromstring(resp.content)
            for elem in root.iter():
                if elem.tag.endswith("loc") and elem.text:
                    u = elem.text.strip()
                    if u:
                        urls.append(u)
    except Exception as e:
        print(f"Error fetching live sitemap: {e}, falling back to local sitemap.xml", file=sys.stderr)
    
    if not urls:
        local_sitemap = Path("sitemap.xml")
        if local_sitemap.exists():
            root = ET.fromstring(local_sitemap.read_text(encoding="utf-8"))
            for elem in root.iter():
                if elem.tag.endswith("loc") and elem.text:
                    u = elem.text.strip()
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
        jsonld_errors = []
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
            
            for s in soup.find_all("script", type="application/ld+json"):
                if s.string:
                    try:
                        json.loads(s.string)
                    except Exception as je:
                        jsonld_errors.append(f"{u}: {je}")
                    
        return {
            "url": u,
            "status_code": resp.status_code,
            "chain": chain,
            "internal_links": internal_links,
            "jsonld_errors": jsonld_errors,
            "error": None
        }
    except Exception as e:
        return {
            "url": u,
            "status_code": None,
            "chain": [],
            "internal_links": set(),
            "jsonld_errors": [],
            "error": str(e)
        }

def check_single_internal_link(link, session):
    try:
        r = session.head(link, timeout=15, allow_redirects=True)
        if r.status_code >= 400:
            r_get = session.get(link, timeout=15, stream=True)
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
            "redirect_chains": [],
            "monitor_errors": []
        },
        "internal_links_check": {
            "total_links_found": 0,
            "unique_internal_links": 0,
            "broken_links": [],
            "monitor_errors": []
        },
        "jsonld_check": {
            "status": "PASS",
            "errors": []
        },
        "claims_lint": {
            "status": "PASS",
            "hard_failures": 0,
            "warnings": 0,
            "rule_metadata": RULES,
            "rule_failures": {f"R{i}": 0 for i in range(1, 26)}
        }
    }

    session = get_session()

    # 1. Check all sitemap URLs concurrently with concurrency 8
    sitemap_urls = get_sitemap_urls(session)
    out_data["sitemap_check"]["total_urls"] = len(sitemap_urls)
    print(f"Checking {len(sitemap_urls)} sitemap URLs concurrently (concurrency 8, 15s timeout, 2 retries)...")
    
    internal_links_to_test = set()
    all_jsonld_errors = []

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(check_single_sitemap_url, u, session): u for u in sitemap_urls}
        for future in as_completed(futures):
            res = future.result()
            if res["error"]:
                out_data["sitemap_check"]["monitor_errors"].append({
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
                
            if res.get("jsonld_errors"):
                all_jsonld_errors.extend(res["jsonld_errors"])

            internal_links_to_test.update(res["internal_links"])

    out_data["jsonld_check"]["errors"] = all_jsonld_errors
    if all_jsonld_errors:
        out_data["jsonld_check"]["status"] = "FAIL"

    out_data["internal_links_check"]["total_links_found"] = len(internal_links_to_test)
    out_data["internal_links_check"]["unique_internal_links"] = len(internal_links_to_test)
    print(f"Checking {len(internal_links_to_test)} unique internal links concurrently (concurrency 8)...")

    # 2. Check internal links concurrently for 404s with concurrency 8
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(check_single_internal_link, link, session): link for link in internal_links_to_test}
        for future in as_completed(futures):
            res = future.result()
            if res:
                if res.get("status_code") and res["status_code"] >= 400:
                    out_data["internal_links_check"]["broken_links"].append(res)
                elif res.get("error"):
                    out_data["internal_links_check"]["monitor_errors"].append(res)

    # 3. Claims linter execution
    print("Running production claims linter...")
    cmd = [sys.executable, "scripts/claims_lint.py", "--production"]
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    stdout = res.stdout
    
    # Parse rules R1-R25
    for i in range(1, 26):
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

    # Overall pass/fail condition: ONLY real site regressions mark the run as FAIL
    failures = []
    if out_data["sitemap_check"]["non_200_urls"]:
        failures.append(f"{len(out_data['sitemap_check']['non_200_urls'])} non-200 sitemap URLs")
    if out_data["sitemap_check"]["redirect_chains"]:
        failures.append(f"{len(out_data['sitemap_check']['redirect_chains'])} sitemap redirect chains")
    if out_data["internal_links_check"]["broken_links"]:
        failures.append(f"{len(out_data['internal_links_check']['broken_links'])} broken internal links")
    if out_data["claims_lint"]["status"] != "PASS":
        failures.append(f"{out_data['claims_lint']['hard_failures']} claims linter hard failures")
    if all_jsonld_errors:
        failures.append(f"{len(all_jsonld_errors)} broken JSON-LD schemas")

    if failures:
        out_data["status"] = "FAIL"
        out_data["failure_reasons"] = failures

    # 4. Spec basis check
    facts_p = Path("seo/facts-register.json")
    if facts_p.exists():
        try:
            facts = json.loads(facts_p.read_text(encoding="utf-8"))
            spec_basis = facts.get("spec_basis", "")
            out_data["spec_basis"] = spec_basis
            if spec_basis == "indicative trade values — no owner COA yet":
                out_data["spec_review_needed"] = True
                print("Notice: spec_basis indicates trade values pending owner COA.")
        except Exception as e:
            print(f"Error reading facts-register: {e}", file=sys.stderr)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(out_data, f, indent=2)

    print(f"Site health check finished with status {out_data['status']}, saved to {OUTPUT_FILE}")
    return out_data

if __name__ == "__main__":
    run_health_check()
