"""
Phase 18 — Task C: Security clean-up.

1. Remove hard-coded AIza key from monitoring scripts (read from env only)
2. Remove client-side PIN from site.js, blog-admin.js, site.min.js
3. Add server-side HTTP Basic Auth in middleware.js for /blog-admin routes
"""
import re
from pathlib import Path

REPO = Path('.')

# ── 1. Remove AIza key from monitoring scripts ───────────────────────────────
API_KEY_RE = re.compile(r'(os\.environ\.get\("PSI_API_KEY"[^)]*\))\s*(?:or\s*"AIza[^"]+"|,\s*"AIza[^"]+")')

for rel in [
    'scripts/monitoring/phase6_baseline.py',
    'scripts/monitoring/phase6_post_verification.py',
    'scripts/monitoring/psi_pull.py',
]:
    path = REPO / rel
    if not path.exists():
        print(f"[SKIP] {rel} not found")
        continue

    t = path.read_text(encoding='utf-8')

    # Replace patterns like:
    #   os.environ.get("PSI_API_KEY", "").strip() or "AIzaSy..."
    #   os.environ.get("PSI_API_KEY", "AIzaSy...")
    t2 = re.sub(
        r'os\.environ\.get\("PSI_API_KEY",\s*"AIza[^"]+"\)',
        'os.environ.get("PSI_API_KEY", "").strip()',
        t
    )
    # Pattern: .strip() or "AIza..."
    t2 = re.sub(
        r'(os\.environ\.get\("PSI_API_KEY",\s*""\)(?:\.strip\(\))?)\s*or\s*"AIza[^"]+"',
        r'os.environ.get("PSI_API_KEY", "").strip()',
        t2
    )

    # Add graceful exit if key is missing (after the api_key assignment)
    # Find the api_key assignment line and add check after it
    t2 = re.sub(
        r'(api_key\s*=\s*os\.environ\.get\("PSI_API_KEY",\s*""\)\.strip\(\))\n',
        r'''\1
if not api_key:
    print("[NOTICE] PSI_API_KEY environment variable is not set. Skipping PageSpeed pull.")
    import sys; sys.exit(0)
''',
        t2, count=1
    )

    if t2 != t:
        path.write_text(t2, encoding='utf-8', newline='\r\n')
        print(f"[OK] {rel}: removed hard-coded API key, added graceful exit")
    else:
        print(f"[WARN] {rel}: pattern not matched — check manually")
        # Also check AIza is still present
        if 'AIza' in t2:
            print(f"  [ERROR] AIza still present in {rel}")
        else:
            print(f"  [OK] No AIza found (may already be clean)")

# Also check scratch/ and tds-generator.js for exposed keys
for rel in ['js/tds-generator.js']:
    path = REPO / rel
    if not path.exists():
        continue
    t = path.read_text(encoding='utf-8')
    # tds-generator may use it for PSI calls too
    if 'AIza' in t:
        t2 = re.sub(r'"AIza[^"]+"', '"" /* key removed — use PSI_API_KEY env var */', t)
        path.write_text(t2, encoding='utf-8', newline='\r\n')
        print(f"[OK] js/tds-generator.js: removed hard-coded API key")

# ── 2. Remove client-side PIN from JS files ──────────────────────────────────

# --- site.js: Remove PIN/ID from admin trigger, redirect directly to /blog-admin ---
site_js_path = REPO / 'js' / 'site.js'
site_js = site_js_path.read_text(encoding='utf-8')

# Replace the entire VALID_ID/VALID_PIN auth block:
# The admin trigger already only runs on localhost (if (!isLocal) return;)
# Replace showAdminModal() to just redirect directly to /blog-admin — server handles auth
OLD_ADMIN_CONSTS = """  const AUTH_KEY = 'nagdev_admin_auth';
  const VALID_ID = 'admin';
  const VALID_PIN = '230893';"""

NEW_ADMIN_CONSTS = "  // Authentication is handled server-side via HTTP Basic Auth on /blog-admin"

if OLD_ADMIN_CONSTS in site_js:
    site_js = site_js.replace(OLD_ADMIN_CONSTS, NEW_ADMIN_CONSTS, 1)
    print("[OK] site.js: removed VALID_ID/VALID_PIN constants")
else:
    # Try to remove just the PIN line
    site_js = re.sub(r"\s*const VALID_(?:ID|PIN)\s*=\s*'[^']*';\n", '\n', site_js)
    print("[WARN] site.js: used regex to remove VALID_ID/VALID_PIN")

# Replace the form submit handler that checks VALID_ID/VALID_PIN
# The form should just redirect to /blog-admin directly
OLD_FORM_SUBMIT = """      const form = modal.querySelector('#admin-trigger-form');
      form.addEventListener('submit', (e) => {
        e.preventDefault();
        const idVal = (modal.querySelector('#trigger-login-id').value || '').trim().toLowerCase();
        const pinVal = (modal.querySelector('#trigger-login-pin').value || '').trim();
        const errEl = modal.querySelector('#trigger-error');

        if (idVal === VALID_ID && pinVal === VALID_PIN) {
          sessionStorage.setItem(AUTH_KEY, 'true');
          errEl.style.display = 'none';
          if (window.showToast) window.showToast('Credentials verified. Redirecting to Blog Studio…');
          setTimeout(() => {
            window.location.href = getAdminUrl();
          }, 350);
        } else {
          errEl.style.display = 'block';
        }
      });"""

NEW_FORM_SUBMIT = """      const form = modal.querySelector('#admin-trigger-form');
      form.addEventListener('submit', (e) => {
        e.preventDefault();
        // Redirect to /blog-admin — HTTP Basic Auth handled server-side
        if (window.showToast) window.showToast('Redirecting to Blog Studio…');
        setTimeout(() => { window.location.href = getAdminUrl(); }, 200);
      });"""

if OLD_FORM_SUBMIT in site_js:
    site_js = site_js.replace(OLD_FORM_SUBMIT, NEW_FORM_SUBMIT, 1)
    print("[OK] site.js: form submit handler simplified (no client-side auth check)")
else:
    # Remove inline PIN checks with regex
    site_js = re.sub(
        r'if\s*\(idVal\s*===\s*VALID_ID\s*&&\s*pinVal\s*===\s*VALID_PIN\)\s*\{[^}]+\}\s*else\s*\{[^}]+\}',
        "window.location.href = getAdminUrl();",
        site_js, flags=re.DOTALL
    )
    print("[WARN] site.js: regex-replaced PIN check")

# Also fix the already-authenticated branch to remove sessionStorage
OLD_ALREADY_AUTH = """      if (sessionStorage.getItem(AUTH_KEY) === 'true') {
        if (window.showToast) window.showToast('Opening Admin Studio…');
        setTimeout(() => {
          window.location.href = getAdminUrl();
        }, 200);
      } else {
        showAdminModal();
      }"""

NEW_ALREADY_AUTH = """      // Server-side auth — just navigate
      if (window.showToast) window.showToast('Opening Admin Studio…');
      setTimeout(() => { window.location.href = getAdminUrl(); }, 200);"""

if OLD_ALREADY_AUTH in site_js:
    site_js = site_js.replace(OLD_ALREADY_AUTH, NEW_ALREADY_AUTH, 1)
    print("[OK] site.js: removed sessionStorage auth check")

site_js_path.write_text(site_js, encoding='utf-8', newline='\r\n')
print("[OK] site.js saved")

# --- blog-admin.js: Remove VALID_ID/VALID_PIN, make checkAuth always pass ---
blog_admin_path = REPO / 'js' / 'blog-admin.js'
blog_admin = blog_admin_path.read_text(encoding='utf-8')

OLD_BA_CONSTS = """  const AUTH_KEY = 'nagdev_admin_auth';
  const VALID_ID = 'admin';
  const VALID_PIN = '230893';"""

NEW_BA_CONSTS = "  // Client-side auth removed; HTTP Basic Auth is enforced server-side"

if OLD_BA_CONSTS in blog_admin:
    blog_admin = blog_admin.replace(OLD_BA_CONSTS, NEW_BA_CONSTS, 1)
    print("[OK] blog-admin.js: removed VALID_ID/VALID_PIN constants")
else:
    blog_admin = re.sub(r"\s*const VALID_(?:ID|PIN)\s*=\s*'[^']*';\n", '\n', blog_admin)
    print("[WARN] blog-admin.js: regex-removed VALID_ID/VALID_PIN")

# Replace checkAuth function: since server handles auth, page is only served to authed users
OLD_CHECK_AUTH = """  function checkAuth() {
    const isAuth = sessionStorage.getItem(AUTH_KEY) === 'true';
    if (isAuth) {
      loginGate.style.display = 'none';
      adminApp.style.display = 'block';
      initAdminDashboard();
    } else {
      loginGate.style.display = 'flex';
      adminApp.style.display = 'none';
      if (loginIdInput) loginIdInput.focus();
    }
  }"""

NEW_CHECK_AUTH = """  function checkAuth() {
    // Server-side HTTP Basic Auth ensures only authenticated users reach this page
    if (loginGate) loginGate.style.display = 'none';
    if (adminApp) adminApp.style.display = 'block';
    initAdminDashboard();
  }"""

if OLD_CHECK_AUTH in blog_admin:
    blog_admin = blog_admin.replace(OLD_CHECK_AUTH, NEW_CHECK_AUTH, 1)
    print("[OK] blog-admin.js: checkAuth simplified (server handles auth)")
else:
    print("[WARN] blog-admin.js: checkAuth not found exactly")

# Remove the form submit handler that validates PIN
OLD_BA_SUBMIT = """  if (loginForm) {
    loginForm.addEventListener('submit', function (e) {
      e.preventDefault();
      const enteredId = (loginIdInput.value || '').trim().toLowerCase();
      const enteredPin = (loginPinInput.value || '').trim();

      if (enteredId === VALID_ID && enteredPin === VALID_PIN) {
        sessionStorage.setItem(AUTH_KEY, 'true');
        loginError.style.display = 'none';
        window.showToast('Welcome, Administra"""

if OLD_BA_SUBMIT in blog_admin:
    # Find the full block end
    start_idx = blog_admin.find(OLD_BA_SUBMIT)
    # Find the closing of this if block
    block_end = blog_admin.find('\n  }\n', start_idx + len(OLD_BA_SUBMIT))
    if block_end > 0:
        blog_admin = blog_admin[:start_idx] + '  // Login form removed — authentication is handled server-side\n' + blog_admin[block_end+5:]
        print("[OK] blog-admin.js: removed login form submit handler")
else:
    # Regex remove the PIN comparison
    blog_admin = re.sub(
        r'if\s*\(enteredId\s*===\s*VALID_ID\s*&&\s*enteredPin\s*===\s*VALID_PIN\)\s*\{.*?\}\s*else\s*\{.*?\}',
        '',
        blog_admin, flags=re.DOTALL
    )
    print("[WARN] blog-admin.js: regex-removed PIN comparison")

blog_admin_path.write_text(blog_admin, encoding='utf-8', newline='\r\n')
print("[OK] blog-admin.js saved")

# --- site.min.js: Remove PIN from minified version ---
site_min_path = REPO / 'js' / 'site.min.js'
if site_min_path.exists():
    site_min = site_min_path.read_text(encoding='utf-8')
    # Remove the VALID_ID and VALID_PIN constants from minified JS
    site_min = re.sub(r"const VALID_ID\s*=\s*'[^']*'\s*;?\s*", '', site_min)
    site_min = re.sub(r"const VALID_PIN\s*=\s*'[^']*'\s*;?\s*", '', site_min)
    # Remove the if (idVal===VALID_ID&&pinVal===VALID_PIN) check
    site_min = re.sub(
        r'if\s*\(idVal\s*===\s*VALID_ID\s*&&\s*pinVal\s*===\s*VALID_PIN\)\s*\{[^}]+\}\s*else\s*\{[^}]+\}',
        'window.location.href=getAdminUrl();',
        site_min
    )
    site_min_path.write_text(site_min, encoding='utf-8', newline='\r\n')
    if 'VALID_PIN' not in site_min and 'AIza' not in site_min:
        print("[OK] site.min.js: PIN removed")
    else:
        if 'VALID_PIN' in site_min:
            print("[WARN] site.min.js: VALID_PIN still present — may need manual check")
        if 'AIza' in site_min:
            print("[WARN] site.min.js: AIza key still present")

# ── 3. Update middleware.js — add HTTP Basic Auth for /blog-admin ─────────────
middleware_path = REPO / 'middleware.js'
new_middleware = '''/**
 * Vercel Edge Middleware — fires before static files are served.
 *
 * Route rules:
 *  1. /blog-admin and /blog-admin.html: enforce HTTP Basic Auth.
 *     Credentials are read from BLOG_ADMIN_USER and BLOG_ADMIN_PASS env vars.
 *     If either is unset, return 403. Never put credentials in code.
 *  2. /: return HTTP 410 Gone only when the wc-ajax query parameter is present.
 *  3. All other requests: pass through untouched.
 */
export const config = {
  matcher: ['/', '/blog-admin', '/blog-admin.html'],
};

export default function middleware(request) {
  const url = new URL(request.url);
  const { pathname } = url;

  // ── Rule 1: HTTP Basic Auth for Blog Admin routes ──────────────────────────
  if (pathname === '/blog-admin' || pathname === '/blog-admin.html') {
    const adminUser = process.env.BLOG_ADMIN_USER;
    const adminPass = process.env.BLOG_ADMIN_PASS;

    if (!adminUser || !adminPass) {
      return new Response('Forbidden — admin credentials not configured', {
        status: 403,
        headers: { 'Content-Type': 'text/plain', 'Cache-Control': 'no-store' },
      });
    }

    const authHeader = request.headers.get('Authorization') || '';
    const expected = 'Basic ' + btoa(`${adminUser}:${adminPass}`);

    if (authHeader !== expected) {
      return new Response('Authentication required', {
        status: 401,
        headers: {
          'WWW-Authenticate': 'Basic realm="Blog Admin", charset="UTF-8"',
          'Content-Type': 'text/plain',
          'Cache-Control': 'no-store',
        },
      });
    }

    // Credentials verified — pass through
    return undefined;
  }

  // ── Rule 2: 410 Gone for WordPress legacy wc-ajax on homepage ─────────────
  if (pathname === '/' && url.searchParams.has('wc-ajax')) {
    return new Response('Gone', {
      status: 410,
      headers: {
        'Content-Type': 'text/plain',
        'Cache-Control': 'no-store',
      },
    });
  }

  // ── Rule 3: All other requests pass through ────────────────────────────────
  return undefined;
}
'''
middleware_path.write_text(new_middleware, encoding='utf-8', newline='\r\n')
print("[OK] middleware.js: added HTTP Basic Auth for /blog-admin")

print("\nTask C complete.")
