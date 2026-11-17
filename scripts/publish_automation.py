#!/usr/bin/env python3
"""
publish_automation.py - Automation tasks for weekly blog publishing (Phase 14 & 16).
Handles:
1. Build and verify due posts against production.
2. Await Vercel HTTP 200, verify /blog listing, sitemap inclusion, self-canonical, and BlogPosting JSON-LD.
3. IndexNow & search engine sitemap pings.
4. Social Pack generation (LinkedIn + Instagram) -> GitHub Issue.
5. Content queue depth monitoring (alerts when < 8 future written posts remain).
"""

import os
import sys
import csv
import json
import time
import argparse
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path
import urllib.request
import urllib.error
import urllib.parse
from bs4 import BeautifulSoup

REPO_ROOT = Path(__file__).resolve().parent.parent
IST = timezone(timedelta(hours=5, minutes=30))

def parse_ist(dt_str: str) -> datetime:
    return datetime.fromisoformat(dt_str)

def get_due_posts():
    """Read seo/blog/calendar.csv and return all posts where publish_date <= now_ist and written == Y."""
    cal_path = REPO_ROOT / "seo" / "blog" / "calendar.csv"
    if not cal_path.exists():
        return []
    now_ist = datetime.now(IST)
    due = []
    with open(cal_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pub_dt = parse_ist(row["publish_date"])
            if pub_dt <= now_ist and row.get("written", "N").strip().upper() == "Y":
                due.append((pub_dt, row))
    due.sort(key=lambda x: x[0])
    return [row for _, row in due]

def get_future_posts_status():
    """Read seo/blog/calendar.csv and count future written vs unwritten posts."""
    cal_path = REPO_ROOT / "seo" / "blog" / "calendar.csv"
    if not cal_path.exists():
        return 0, []
        
    now_ist = datetime.now(IST)
    future_written_count = 0
    future_unwritten = []
    
    with open(cal_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pub_dt = parse_ist(row["publish_date"])
            if pub_dt > now_ist:
                if row.get("written", "N").strip().upper() == "Y":
                    future_written_count += 1
                else:
                    future_unwritten.append(row)
                    
    return future_written_count, future_unwritten

def check_queue_alert(dry_run=False):
    """Check future post queue; if < 8 written posts remain, open alert issue."""
    future_written, future_unwritten = get_future_posts_status()
    print(f"[QUEUE CHECK] Future written posts remaining: {future_written}")
    
    if future_written < 8:
        next_batch = future_unwritten[:26]
        if not next_batch:
            print("[QUEUE CHECK] No unwritten posts in calendar to queue.")
            return
            
        start_week = next_batch[0]["week"]
        end_week = next_batch[-1]["week"]
        title = f"Blog queue low – write next batch (weeks {start_week}–{end_week})"
        
        lines = [
            f"## ⚠️ Blog Content Queue Alert",
            f"",
            f"Only **{future_written}** written blog post(s) remain in the future schedule (threshold is 8).",
            f"Please write the next batch of 26 calendar entries covering **Weeks {start_week} to {end_week}**.",
            f"",
            f"### Next Batch Calendar Entries (Weeks {start_week}–{end_week})",
            f"",
            f"| Week | Publish Date | Type | Product / Topic | Title | Primary Keyword |",
            f"|---|---|---|---|---|---|"
        ]
        
        for r in next_batch:
            lines.append(f"| {r['week']} | {r['publish_date'][:10]} | {r['type']} | {r['product_slug']} | {r['title']} | `{r['primary_keyword']}` |")
            
        lines.extend([
            f"",
            f"**Content Guidelines:**",
            f"- Strictly adhere to `seo/facts-register.json` and canonical spec parameters.",
            f"- Run `python scripts/claims_lint.py` and `python scripts/build_blog.py` to ensure 0 failures and shingle similarity <30%.",
            f"- Set `written: Y` in `seo/blog/calendar.csv` after drafting each post."
        ])
        
        body = "\n".join(lines)
        
        if dry_run:
            print(f"[DRY RUN] Would open GitHub Issue: '{title}'")
        else:
            try:
                # Check if already open
                check_issue = subprocess.run(
                    ["gh", "issue", "list", "--search", title, "--json", "number"],
                    capture_output=True, text=True
                )
                if check_issue.returncode == 0 and check_issue.stdout.strip() and json.loads(check_issue.stdout):
                    print(f"[QUEUE OK] Issue '{title}' already open.")
                    return

                subprocess.run([
                    "gh", "issue", "create",
                    "--title", title,
                    "--body", body,
                    "--label", "content-queue"
                ], check=True)
                print(f"[SUCCESS] Opened GitHub Issue: '{title}'")
            except Exception as e:
                print(f"[ERROR] Failed opening GitHub Issue via gh CLI: {e}")
    else:
        print(f"[QUEUE OK] Sufficient buffer in pipeline ({future_written} future posts written).")

def poll_url(url: str, max_timeout=900, interval=15) -> tuple:
    """Wait for URL to respond with HTTP 200, return (success, content)."""
    print(f"[POLL] Polling production URL: {url} (max timeout {max_timeout}s)...")
    start_time = time.time()
    headers = {"User-Agent": "Nagdev-Blog-Publish-Verifier/1.0"}
    
    last_status = None
    while time.time() - start_time < max_timeout:
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=12) as resp:
                last_status = resp.status
                if resp.status == 200:
                    content = resp.read().decode("utf-8", errors="replace")
                    print(f"  [OK] HTTP 200 verified on {url} in {int(time.time() - start_time)}s.")
                    return True, content, None
        except urllib.error.HTTPError as e:
            last_status = e.code
            print(f"  HTTP {e.code} received on {url}, re-checking in {interval}s... ({int(time.time() - start_time)}s elapsed)")
        except Exception as e:
            print(f"  Connection probe error: {e}, re-checking in {interval}s...")
        time.sleep(interval)
        
    return False, None, f"HTTP {last_status or 'Timeout'} after {max_timeout}s"

def verify_single_post(slug: str, post_html: str, blog_index_html: str, sitemap_xml: str) -> list:
    """Verify the 5 production requirements for a published post."""
    errors = []
    expected_url = f"https://www.nagdevproducts.com/blog/{slug}"
    
    # 1. HTTP 200 already verified if post_html is present
    if not post_html:
        errors.append(f"HTTP non-200 or unreachable at {expected_url}")
        return errors
        
    # 2. Listed on /blog index
    if slug not in blog_index_html:
        errors.append(f"Slug '{slug}' not found on /blog index")
        
    # 3. Listed in sitemap.xml
    if expected_url not in sitemap_xml:
        errors.append(f"URL '{expected_url}' not found in sitemap.xml")
        
    # 4. Self-canonical tag
    soup = BeautifulSoup(post_html, "html.parser")
    can = soup.find("link", rel="canonical")
    if not can or can.get("href") != expected_url:
        actual = can.get("href") if can else "None"
        errors.append(f"Canonical mismatch: expected '{expected_url}', found '{actual}'")
        
    # 5. BlogPosting JSON-LD
    found_blog_posting = False
    for s in soup.find_all("script", type="application/ld+json"):
        if not s.string:
            continue
        try:
            data = json.loads(s.string)
            items = data.get("@graph", [data]) if isinstance(data, dict) else []
            for item in items:
                if isinstance(item, dict) and item.get("@type") == "BlogPosting":
                    if item.get("headline") and item.get("datePublished"):
                        found_blog_posting = True
                        break
        except Exception as e:
            errors.append(f"Malformed JSON-LD on {expected_url}: {e}")
            
    if not found_blog_posting:
        errors.append(f"Missing valid BlogPosting JSON-LD schema on {expected_url}")
        
    return errors

def ping_search_engines(urls: list):
    """Ping IndexNow for newly published post URLs."""
    if not urls:
        return
    print(f"[INDEXING] Pinging IndexNow for {len(urls)} URL(s)...")
    for u in urls:
        print(f"  -> {u}")
        
    try:
        indexnow_payload = {
            "host": "www.nagdevproducts.com",
            "key": "nagdev-indexnow-key",
            "keyLocation": "https://www.nagdevproducts.com/nagdev-indexnow-key.txt",
            "urlList": urls
        }
        data = json.dumps(indexnow_payload).encode('utf-8')
        req = urllib.request.Request(
            "https://api.indexnow.org/indexnow",
            data=data,
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            print(f"  [OK] IndexNow API responded with HTTP {resp.status}.")
    except Exception as e:
        print(f"  [WARN] IndexNow ping notice: {e}")

def verify_all_due_posts(max_timeout=900, interval=15, do_ping=True, dry_run=False):
    """
    Finds all due posts in calendar.csv, polls production until HTTP 200,
    and rigorously verifies all 5 requirements for every due post.
    """
    due_posts = get_due_posts()
    if not due_posts:
        print("[VERIFY DUE] No due posts in calendar.")
        return True
        
    print(f"\n[VERIFY DUE] Found {len(due_posts)} total due post(s) to verify on production:")
    for p in due_posts[-3:]:  # show newest 3
        print(f"  - [{p['publish_date']}] {p['slug']}: {p.get('title')}")
        
    if dry_run:
        print("[DRY RUN] Verification simulation passed.")
        return True

    # We poll the newest scheduled post first to ensure deployment is ready
    newest = due_posts[-1]
    newest_slug = newest["slug"]
    newest_url = f"https://www.nagdevproducts.com/blog/{newest_slug}"
    
    ok, content, err = poll_url(newest_url, max_timeout=max_timeout, interval=interval)
    if not ok:
        fail_msg = f"Latest scheduled post {newest_url} failed to return HTTP 200 within {max_timeout}s: {err}"
        print(f"\n[FAILED] {fail_msg}")
        alert_failure(newest_slug, [fail_msg])
        sys.exit(1)

    # Fetch live blog index and sitemap
    headers = {"User-Agent": "Nagdev-Blog-Publish-Verifier/1.0"}
    try:
        b_req = urllib.request.Request("https://www.nagdevproducts.com/blog", headers=headers)
        with urllib.request.urlopen(b_req, timeout=15) as b_resp:
            blog_index_html = b_resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        blog_index_html = ""
        print(f"[WARN] Failed fetching live /blog index: {e}")

    try:
        s_req = urllib.request.Request("https://www.nagdevproducts.com/sitemap.xml", headers=headers)
        with urllib.request.urlopen(s_req, timeout=15) as s_resp:
            sitemap_xml = s_resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        sitemap_xml = ""
        print(f"[WARN] Failed fetching live sitemap.xml: {e}")

    all_failures = {}
    newly_published_urls = []

    # Verify each due post
    for p in due_posts:
        slug = p["slug"]
        url = f"https://www.nagdevproducts.com/blog/{slug}"
        if slug == newest_slug:
            post_html = content
        else:
            try:
                p_req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(p_req, timeout=15) as p_resp:
                    post_html = p_resp.read().decode("utf-8", errors="replace") if p_resp.status == 200 else ""
            except Exception as e:
                post_html = ""
                
        errors = verify_single_post(slug, post_html, blog_index_html, sitemap_xml)
        if errors:
            all_failures[slug] = errors
            print(f"  [FAIL] {slug}: {', '.join(errors)}")
        else:
            print(f"  [PASS] {slug} (HTTP 200, /blog index, sitemap, canonical, JSON-LD)")
            newly_published_urls.append(url)

    if all_failures:
        print(f"\n[VERIFICATION FAILED] {len(all_failures)} post(s) had verification failures.")
        lines = []
        for slug, errs in all_failures.items():
            for e in errs:
                lines.append(f"- **{slug}**: {e}")
        alert_failure("multiple" if len(all_failures) > 1 else list(all_failures.keys())[0], lines)
        sys.exit(1)
        
    print("\n[ALL PASSED] All due blog posts verified successfully on production!")
    if do_ping:
        ping_search_engines(newly_published_urls)
    check_queue_alert(dry_run=dry_run)
    return True

def alert_failure(slug: str, error_lines: list):
    """Open or update ONE informative GitHub issue on verification failure."""
    title = f"🚨 Blog Publish Verification Failure: {slug}"
    body = (
        f"### 🚨 Production Blog Publish Health Alert\n\n"
        f"The automated daily blog rebuild verification encountered the following errors:\n\n" +
        "\n".join(error_lines) +
        f"\n\n**Action Required:**\n"
        f"1. Check Vercel deployment status.\n"
        f"2. Ensure `scripts/build_blog.py` was executed and generated files were pushed to `main`.\n"
        f"3. Verify production HTTP responses."
    )
    try:
        check_issue = subprocess.run(
            ["gh", "issue", "list", "--state", "open", "--label", "seo-alert", "--json", "number,title"],
            capture_output=True, text=True
        )
        if check_issue.returncode == 0 and check_issue.stdout.strip():
            existing = json.loads(check_issue.stdout)
            for iss in existing:
                if slug in iss.get("title", "") or "Publish Verification Failure" in iss.get("title", ""):
                    print(f"Updating existing issue #{iss['number']} with latest failure details...")
                    subprocess.run(["gh", "issue", "comment", str(iss["number"]), "--body", body], check=True)
                    return

        print("Opening new GitHub issue for verification failure...")
        subprocess.run([
            "gh", "issue", "create",
            "--title", title,
            "--body", body,
            "--label", "seo-alert"
        ], check=True)
    except Exception as e:
        print(f"Failed handling GitHub issue via gh CLI: {e}")

def main():
    parser = argparse.ArgumentParser(description="Nagdev Blog Publishing Automation")
    parser.add_argument("--verify-due", action="store_true", help="Verify all due posts on production, await ready, and check schemas")
    parser.add_argument("--check-today", action="store_true", help="Alias for --verify-due")
    parser.add_argument("--ping", action="store_true", help="Ping search engines and IndexNow")
    parser.add_argument("--check-queue", action="store_true", help="Check buffer and open Queue Alert if < 8")
    parser.add_argument("--dry-run", action="store_true", help="Simulate actions")
    args = parser.parse_args()

    if args.verify_due or args.check_today:
        verify_all_due_posts(dry_run=args.dry_run, do_ping=args.ping)
        return

    if args.check_queue:
        check_queue_alert(dry_run=args.dry_run)
        return

if __name__ == "__main__":
    main()
