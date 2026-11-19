/**
 * Vercel Edge Middleware — fires before static files are served.
 * Returns HTTP 410 Gone for any request with a wc-ajax query parameter.
 * 
 * This handles legacy WordPress AJAX URLs: /?wc-ajax=get_refreshed_fragments etc.
 */
export const config = {
  matcher: ['/'],
};

export default function middleware(request) {
  const url = new URL(request.url);
  
  // Return 410 Gone for any /?wc-ajax=... request
  if (url.searchParams.has('wc-ajax')) {
    return new Response('Gone', {
      status: 410,
      headers: {
        'Content-Type': 'text/plain',
        'Cache-Control': 'no-store',
      },
    });
  }
  
  // All other requests pass through
  return undefined;
}
