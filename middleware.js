/**
 * Vercel Edge Middleware — fires before static files are served.
 * Returns HTTP 410 Gone ONLY for requests to "/" with a wc-ajax query parameter.
 * All other requests pass through untouched.
 */
export const config = {
  matcher: ['/'],
};

export default function middleware(request) {
  const url = new URL(request.url);

  // Return 410 Gone only when wc-ajax query key is present (WordPress legacy AJAX)
  if (url.pathname === '/' && url.searchParams.has('wc-ajax')) {
    return new Response('Gone', {
      status: 410,
      headers: {
        'Content-Type': 'text/plain',
        'Cache-Control': 'no-store',
      },
    });
  }

  // All other requests: pass through (return undefined = no-op)
  return undefined;
}
