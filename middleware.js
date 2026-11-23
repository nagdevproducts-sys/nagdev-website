/**
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
