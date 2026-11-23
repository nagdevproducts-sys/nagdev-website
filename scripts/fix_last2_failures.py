"""Fix last 2 linter failures:
1. R2: castor-oil-exporter-india.html L720 'Global Reach' -> 'Global Markets'
2. R13: 404.html missing cookie-settings-btn, consent snippet, gtag loader, analytics.js
"""
import re

# ── Fix 1: castor-oil-exporter-india.html ──────────────────────────────────
path1 = 'castor-oil-exporter-india.html'
t1 = open(path1, encoding='utf-8').read()
orig = '<span class="section-eyebrow">Global Reach</span>'
repl = '<span class="section-eyebrow">Global Markets</span>'
if orig in t1:
    t1 = t1.replace(orig, repl, 1)
    open(path1, 'w', encoding='utf-8', newline='\r\n').write(t1)
    print(f"[OK] Fixed R2 in {path1}: 'Global Reach' -> 'Global Markets'")
else:
    print(f"[WARN] Pattern not found in {path1} — may already be fixed")

# ── Fix 2: 404.html — add standard template components ────────────────────
path2 = '404.html'
t2 = open(path2, encoding='utf-8').read()

# Check what's missing
missing = []
if 'cookie-settings-btn' not in t2:
    missing.append('cookie-settings-btn')
if 'gtag' not in t2:
    missing.append('gtag')
if '/js/analytics.js' not in t2:
    missing.append('/js/analytics.js')

print(f"Missing from 404.html: {missing}")

# 2a. Add consent snippet + analytics.js before </head>
consent_block = """  <!-- Consent Mode v2 -->
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){dataLayer.push(arguments);}
    gtag('consent', 'default', {
      'ad_storage': 'denied',
      'ad_user_data': 'denied',
      'ad_personalization': 'denied',
      'analytics_storage': 'denied'
    });
    try {
      var _c = localStorage.getItem('nagdev_consent');
      if (_c) {
        var _p = JSON.parse(_c);
        if (_p && _p.timestamp && (Date.now() - _p.timestamp < 31536000000)) {
          gtag('consent', 'update', {
            'analytics_storage': _p.choice === 'granted' ? 'granted' : 'denied'
          });
        } else {
          localStorage.removeItem('nagdev_consent');
        }
      }
    } catch(e){}
  </script>
  <script defer src="/js/analytics.js?v=9256f71"></script>
</head>"""

if 'gtag' not in t2:
    t2 = t2.replace('</head>', consent_block, 1)
    print("[OK] Added consent snippet + analytics.js to 404.html head")
else:
    print("[SKIP] gtag already present in 404.html")

# 2b. Add cookie-settings button to footer-bottom-links
if 'cookie-settings-btn' not in t2:
    old_footer_links = '''        <div class="footer-bottom-links">
          <a href="/products" class="footer-bottom-link">Products (32)</a>
          <a href="/contact" class="footer-bottom-link">Enquiries</a>
          <a href="/privacy" class="footer-bottom-link">Privacy Policy</a>
        </div>'''
    new_footer_links = '''        <div class="footer-bottom-links">
          <a href="/products" class="footer-bottom-link">Products (32)</a>
          <a href="/contact" class="footer-bottom-link">Enquiries</a>
          <a href="/privacy" class="footer-bottom-link">Privacy Policy</a>
          <button type="button" id="cookie-settings-btn" class="footer-bottom-link cookie-settings-trigger" style="background:none;border:none;padding:0;font:inherit;color:inherit;cursor:pointer;">Cookie Settings</button>
        </div>'''
    if old_footer_links in t2:
        t2 = t2.replace(old_footer_links, new_footer_links, 1)
        print("[OK] Added cookie-settings-btn to 404.html footer")
    else:
        # Try a looser replacement
        t2 = t2.replace(
            '<a href="/privacy" class="footer-bottom-link">Privacy Policy</a>\n        </div>',
            '<a href="/privacy" class="footer-bottom-link">Privacy Policy</a>\n          <button type="button" id="cookie-settings-btn" class="footer-bottom-link cookie-settings-trigger" style="background:none;border:none;padding:0;font:inherit;color:inherit;cursor:pointer;">Cookie Settings</button>\n        </div>',
            1
        )
        print("[OK] Added cookie-settings-btn (fallback match) to 404.html footer")
else:
    print("[SKIP] cookie-settings-btn already present in 404.html")

open(path2, 'w', encoding='utf-8', newline='\r\n').write(t2)
print(f"[DONE] 404.html written.")
print("All fixes applied.")
