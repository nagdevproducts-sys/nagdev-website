#!/usr/bin/env python3
"""
Cache Busting Automation for Nagdev Products.
Adds ?v=<git-short-sha> to every local CSS/JS asset referenced in all HTML files.
"""

import glob
import os
import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

def get_build_version():
    try:
        sha = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'], cwd=REPO_ROOT).decode().strip()
        if sha:
            return sha
    except Exception:
        pass
    return "20261029d"

def cache_bust_file(path, version):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    orig = content

    # 1. Strip deleted blog-storage.js
    content = re.sub(r'<script[^>]*src=["\'](?:/js/|js/)blog-storage\.js["\'][^>]*></script>\s*', '', content)

    # 2. Update CSS links: href="(...css)(?:\?v=[^"']*)?"
    def update_css(match):
        pre = match.group(1)
        url = match.group(2)
        post = match.group(3)
        if url.startswith(('http://', 'https://', '//')):
            return match.group(0)
        clean = url.split('?')[0]
        return f'{pre}{clean}?v={version}{post}'

    content = re.sub(r'(<link[^>]+href=["\'])([^"\']+\.css(?:\?[^"\']*)?)(["\'])', update_css, content)

    # 3. Update JS scripts: src="(...js)(?:\?v=[^"']*)?"
    def update_js(match):
        pre = match.group(1)
        url = match.group(2)
        post = match.group(3)
        if url.startswith(('http://', 'https://', '//')):
            return match.group(0)
        clean = url.split('?')[0]
        return f'{pre}{clean}?v={version}{post}'

    content = re.sub(r'(<script[^>]+src=["\'])([^"\']+\.js(?:\?[^"\']*)?)(["\'])', update_js, content)

    if content != orig:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def main():
    version = get_build_version()
    print(f"Applying cache busting with build version: {version}")

    patterns = [
        '*.html',
        'templates/*.html',
        'products/*.html',
        'applications/*.html',
        'blog/*.html',
        'compare/*.html',
        'markets/*.html',
        'grades/*.html'
    ]

    all_files = []
    for pat in patterns:
        all_files.extend(glob.glob(str(REPO_ROOT / pat)))

    updated_count = 0
    for file_path in all_files:
        if cache_bust_file(file_path, version):
            updated_count += 1

    print(f"Processed {len(all_files)} HTML files. Updated cache bust query on {updated_count} files.")

if __name__ == '__main__':
    main()
