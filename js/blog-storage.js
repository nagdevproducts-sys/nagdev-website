/**
 * NAGDEV PRODUCTS — BLOG STORAGE & SYNC ENGINE
 * Unified data access for built-in articles + custom authored posts.
 * Uses IndexedDB for high-capacity local storage (unlimited content & photos)
 * with transparent fallback to localStorage.
 */

(function () {
  'use strict';

  const DB_NAME = 'nagdev_blog_db';
  const DB_VERSION = 1;
  const STORE_NAME = 'posts';
  const LS_KEY = 'nagdev_custom_blog_posts';

  // Open IndexedDB
  function openDB() {
    return new Promise((resolve, reject) => {
      if (!window.indexedDB) {
        resolve(null);
        return;
      }
      const req = indexedDB.open(DB_NAME, DB_VERSION);
      req.onupgradeneeded = (e) => {
        const db = e.target.result;
        if (!db.objectStoreNames.contains(STORE_NAME)) {
          db.createObjectStore(STORE_NAME, { keyPath: 'id' });
        }
      };
      req.onsuccess = (e) => resolve(e.target.result);
      req.onerror = () => resolve(null); // fallback
    });
  }

  // Get custom posts from IndexedDB / localStorage
  async function getCustomPosts() {
    try {
      const db = await openDB();
      if (db) {
        return new Promise((resolve) => {
          const tx = db.transaction(STORE_NAME, 'readonly');
          const store = tx.objectStore(STORE_NAME);
          const req = store.getAll();
          req.onsuccess = () => resolve(req.result || []);
          req.onerror = () => resolve(getFromLS());
        });
      }
    } catch (e) {
      console.warn('IndexedDB read error, using localStorage fallback', e);
    }
    return getFromLS();
  }

  function getFromLS() {
    try {
      const data = localStorage.getItem(LS_KEY);
      return data ? JSON.parse(data) : [];
    } catch (e) {
      return [];
    }
  }

  function saveToLS(posts) {
    try {
      localStorage.setItem(LS_KEY, JSON.stringify(posts));
    } catch (e) {
      console.warn('localStorage save failed (quota exceeded)', e);
    }
  }

  // BlogStorage API
  const BlogStorage = {
    // Get all posts (built-in seed + custom authored)
    async getAllPosts() {
      const builtIn = window.NAGDEV_BLOG_POSTS || [];
      const custom = await getCustomPosts();

      // Merge: custom posts take precedence if same id
      const customMap = new Map();
      custom.forEach(p => customMap.set(p.id, p));

      const merged = [];
      // Add custom posts
      custom.forEach(p => merged.push(p));

      // Add built-in posts that haven't been edited/overridden
      builtIn.forEach(p => {
        if (!customMap.has(p.id)) {
          merged.push(p);
        }
      });

      // Sort by date descending
      merged.sort((a, b) => new Date(b.date || 0) - new Date(a.date || 0));
      return merged;
    },

    // Get single post by slug or id
    async getPostBySlug(slug) {
      const all = await this.getAllPosts();
      return all.find(p => p.slug === slug || p.id === slug) || null;
    },

    // Save a post (create or update)
    async savePost(post) {
      if (!post.id) {
        post.id = 'post-' + Date.now();
      }
      if (!post.slug) {
        post.slug = post.title
          .toLowerCase()
          .replace(/[^a-z0-9]+/g, '-')
          .replace(/(^-|-$)+/g, '');
      }
      if (!post.date) {
        post.date = new Date().toISOString().split('T')[0];
      }
      if (!post.author) {
        post.author = 'Nagdev Technical Editorial Team';
      }
      if (!post.readTime) {
        // Calculate read time roughly 200 words/min
        const text = (post.content || '').replace(/<[^>]*>/g, ' ');
        const words = text.trim().split(/\s+/).length;
        const mins = Math.max(1, Math.round(words / 200));
        post.readTime = mins + ' min read';
      }

      // Save to IndexedDB
      try {
        const db = await openDB();
        if (db) {
          await new Promise((resolve, reject) => {
            const tx = db.transaction(STORE_NAME, 'readwrite');
            const store = tx.objectStore(STORE_NAME);
            store.put(post);
            tx.oncomplete = () => resolve();
            tx.onerror = () => reject(tx.error);
          });
        }
      } catch (e) {
        console.warn('IndexedDB save error, persisting to LS', e);
      }

      // Also update localStorage mirror
      const custom = getFromLS();
      const idx = custom.findIndex(p => p.id === post.id);
      if (idx >= 0) {
        custom[idx] = post;
      } else {
        custom.push(post);
      }
      saveToLS(custom);

      return post;
    },

    // Delete a post by id
    async deletePost(id) {
      try {
        const db = await openDB();
        if (db) {
          const tx = db.transaction(STORE_NAME, 'readwrite');
          tx.objectStore(STORE_NAME).delete(id);
        }
      } catch (e) {}

      const custom = getFromLS().filter(p => p.id !== id);
      saveToLS(custom);
      return true;
    },

    // Generate static HTML for permanent git export
    generateStaticHtml(post) {
      const canonicalUrl = `https://www.nagdevproducts.com/blog/${post.slug}.html`;
      const fullTitle = `${post.title} | Nagdev Products`;
      const coverUrl = post.coverImage.startsWith('data:') 
        ? post.coverImage 
        : (post.coverImage.startsWith('http') ? post.coverImage : `https://www.nagdevproducts.com/${post.coverImage}`);

      return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${escapeHtml(fullTitle)}</title>
  <meta name="description" content="${escapeHtml(post.seoDescription || '')}">
  <meta name="keywords" content="${escapeHtml((post.tags || []).join(', '))}">
  <link rel="canonical" href="${canonicalUrl}">

  <!-- Open Graph / Social Sharing -->
  <meta property="og:type" content="article">
  <meta property="og:url" content="${canonicalUrl}">
  <meta property="og:title" content="${escapeHtml(post.title)}">
  <meta property="og:description" content="${escapeHtml(post.seoDescription || '')}">
  <meta property="og:image" content="${coverUrl}">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">

  <!-- Twitter Card -->
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="${escapeHtml(post.title)}">
  <meta name="twitter:description" content="${escapeHtml(post.seoDescription || '')}">
  <meta name="twitter:image" content="${coverUrl}">

  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;0,700;1,400;1,600&family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="../css/main.css">
  <link rel="stylesheet" href="../css/blog.css">

  <!-- Structured Data: BlogPosting -->
  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@type": "BlogPosting",
    "headline": ${JSON.stringify(post.title)},
    "description": ${JSON.stringify(post.seoDescription || '')},
    "image": [${JSON.stringify(coverUrl)}],
    "datePublished": ${JSON.stringify(post.date)},
    "dateModified": ${JSON.stringify(post.date)},
    "author": {
      "@type": "Organization",
      "name": ${JSON.stringify(post.author || 'Nagdev Products Private Limited')},
      "url": "https://www.nagdevproducts.com/"
    },
    "publisher": {
      "@type": "Organization",
      "name": "Nagdev Products Private Limited",
      "logo": {
        "@type": "ImageObject",
        "url": "https://www.nagdevproducts.com/images/logo.png"
      }
    },
    "mainEntityOfPage": {
      "@type": "WebPage",
      "@id": ${JSON.stringify(canonicalUrl)}
    }
  }
  </script>

  <!-- Structured Data: BreadcrumbList -->
  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    "itemListElement": [
      {"@type": "ListItem", "position": 1, "name": "Home", "item": "https://www.nagdevproducts.com/"},
      {"@type": "ListItem", "position": 2, "name": "Blog", "item": "https://www.nagdevproducts.com/blog.html"},
      {"@type": "ListItem", "position": 3, "name": ${JSON.stringify(post.title)}, "item": ${JSON.stringify(canonicalUrl)}}
    ]
  }
  </script>
</head>
<body>
<a href="#main-content" class="skip-to-content">Skip to main content</a>

<!-- HEADER -->
<header class="site-header" id="site-header">
  <div class="container-wide">
    <div class="header-inner">
      <a href="../index.html" class="header-logo" aria-label="Nagdev Products Home">
        <img src="../images/logo.png" alt="Nagdev Products Private Limited" width="180" height="53">
      </a>
      <nav class="header-nav" aria-label="Main navigation">
        <ul class="nav-list" role="list">
          <li><a href="../index.html" class="nav-link">Home</a></li>
          <li><a href="../products.html" class="nav-link">Products</a></li>
          <li><a href="../chemistry-tree.html" class="nav-link">Chemistry Tree</a></li>
          <li><a href="../about.html" class="nav-link">About</a></li>
          <li><a href="../plant.html" class="nav-link">Our Plant</a></li>
          <li><a href="../quality.html" class="nav-link">Quality</a></li>
          <li><a href="../markets.html" class="nav-link">Markets</a></li>
          <li><a href="../blog.html" class="nav-link active">Blog</a></li>
          <li><a href="../contact.html" class="nav-link">Contact</a></li>
        </ul>
      </nav>
      <div class="header-cta">
        <a href="../contact.html" class="btn btn-primary btn-sm">Request a Quote →</a>
      </div>
      <button class="mobile-toggle" id="mobile-toggle" aria-label="Open navigation" aria-expanded="false">
        <span></span><span></span><span></span>
      </button>
    </div>
  </div>
</header>

<!-- Mobile Drawer -->
<div class="mobile-backdrop" id="mobile-backdrop" aria-hidden="true"></div>
<div class="mobile-drawer" id="mobile-drawer" role="dialog" aria-label="Navigation menu">
  <div class="mobile-drawer-header">
    <img src="../images/logo.png" alt="Nagdev Products" height="36" style="width:auto;">
    <button class="mobile-drawer-close" id="mobile-drawer-close" aria-label="Close menu">✕</button>
  </div>
  <ul class="mobile-nav-list" role="list">
    <li><a href="../index.html" class="mobile-nav-link">Home</a></li>
    <li><a href="../products.html" class="mobile-nav-link">Products</a></li>
    <li><a href="../chemistry-tree.html" class="mobile-nav-link">🌿 Chemistry Tree</a></li>
    <li><a href="../about.html" class="mobile-nav-link">About</a></li>
    <li><a href="../plant.html" class="mobile-nav-link">Our Plant</a></li>
    <li><a href="../quality.html" class="mobile-nav-link">Quality</a></li>
    <li><a href="../markets.html" class="mobile-nav-link">Markets</a></li>
    <li><a href="../blog.html" class="mobile-nav-link active">Blog &amp; Insights</a></li>
    <li><a href="../contact.html" class="mobile-nav-link">Contact</a></li>
  </ul>
  <a href="../contact.html" class="btn btn-primary" style="width:100%;justify-content:center;">Request a Quote →</a>
</div>

<!-- MAIN CONTENT -->
<main id="main-content">
  <!-- Article Hero Header -->
  <article class="blog-article">
    <header class="blog-article-header">
      <div class="container-narrow">
        <nav class="breadcrumb-nav" aria-label="Breadcrumb">
          <a href="../index.html">Home</a> &gt; 
          <a href="../blog.html">Blog</a> &gt; 
          <span aria-current="page">${escapeHtml(post.category || 'Article')}</span>
        </nav>

        <span class="blog-category-badge">${escapeHtml(post.category || 'Technical Article')}</span>
        <h1 class="blog-article-title">${escapeHtml(post.title)}</h1>

        <div class="blog-meta-bar">
          <div class="meta-item">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
            <span>${escapeHtml(post.author || 'Nagdev Products')}</span>
          </div>
          <div class="meta-item">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
            <time datetime="${post.date}">${formatDate(post.date)}</time>
          </div>
          <div class="meta-item">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
            <span>${escapeHtml(post.readTime || '5 min read')}</span>
          </div>
        </div>
      </div>
    </header>

    <!-- Cover Image (Fixed 1200x630) -->
    <div class="container-mid">
      <figure class="blog-hero-figure">
        <img src="${post.coverImage.startsWith('http') || post.coverImage.startsWith('data:') ? post.coverImage : '../' + post.coverImage}" alt="${escapeHtml(post.title)}" width="1200" height="630" class="blog-hero-img">
      </figure>
    </div>

    <!-- Article Content -->
    <div class="container-narrow">
      <div class="blog-content-body typography">
        ${post.content || ''}
      </div>

      <!-- Tag list -->
      ${post.tags && post.tags.length ? `
      <div class="blog-tags-wrapper">
        <span class="tags-label">Keywords:</span>
        ${post.tags.map(t => `<span class="blog-tag-pill">${escapeHtml(t)}</span>`).join('')}
      </div>` : ''}

      ${post.relatedLink && post.relatedLink.url ? `
      <!-- Related Website / Product Link Card (Selected by Admin) -->
      <div class="blog-related-link-card">
        <div class="related-link-content">
          <span class="related-link-eyebrow">Explore Related Solution</span>
          <h4 class="related-link-title">${escapeHtml(post.relatedLink.title || 'Related Page')}</h4>
          <p class="related-link-text">Access detailed technical datasheets (TDS), specifications, bulk packaging, and formulation guidance.</p>
        </div>
        <a href="${post.relatedLink.url.startsWith('http') ? post.relatedLink.url : '../' + post.relatedLink.url.replace(/^(\.\.\/)+/, '')}" class="btn btn-primary btn-sm related-link-btn">
          Explore ${escapeHtml(post.relatedLink.title || 'Page')} →
        </a>
      </div>` : ''}

      <!-- Formulator CTA Box -->
      <div class="blog-cta-box">
        <h3>Formulating with Castor Derivatives?</h3>
        <p>Our technical team in Banaskantha, Gujarat provides batch samples, certificates of analysis (CoA), and custom specifications for global formulators.</p>
        <div class="blog-cta-actions">
          <a href="../contact.html" class="btn btn-primary">Request Commercial Quote →</a>
          <a href="../products.html" class="btn btn-secondary">Explore 20-Product Catalog</a>
        </div>
      </div>
    </div>
  </article>
</main>

<!-- FOOTER -->
<footer class="site-footer" role="contentinfo">
  <div class="container-wide">
    <div class="footer-top">
      <div class="footer-brand">
        <a href="../index.html" class="footer-logo" aria-label="Nagdev Products Home">
          <img src="../images/logo-dark.png" alt="Nagdev Products Private Limited" height="42" style="width:auto;">
        </a>
        <p class="footer-tagline">
          Manufacturer and exporter of Castor Oil and Castor Oil derivatives.<br>
          Based in Banaskantha, Gujarat, India.
        </p>
      </div>
      <div>
        <div class="footer-col-title">Navigation</div>
        <ul class="footer-links">
          <li><a href="../index.html" class="footer-link">Home</a></li>
          <li><a href="../products.html" class="footer-link">Products</a></li>
          <li><a href="../chemistry-tree.html" class="footer-link">Chemistry Tree</a></li>
          <li><a href="../about.html" class="footer-link">About</a></li>
          <li><a href="../plant.html" class="footer-link">Our Plant</a></li>
          <li><a href="../quality.html" class="footer-link">Quality</a></li>
          <li><a href="../markets.html" class="footer-link">Markets</a></li>
          <li><a href="../blog.html" class="footer-link">Blog</a></li>
          <li><a href="../contact.html" class="footer-link">Contact</a></li>
        </ul>
      </div>
      <div>
        <div class="footer-col-title">Products</div>
        <ul class="footer-links">
          <li><a href="../castor-oils.html" class="footer-link">Castor Oils</a></li>
          <li><a href="../castor-oil-derivatives.html" class="footer-link">Castor Derivatives</a></li>
          <li><a href="../products.html" class="footer-link">All 20 Products →</a></li>
        </ul>
      </div>
      <div>
        <div class="footer-col-title">Contact</div>
        <address style="font-style:normal;">
          <div class="footer-contact">
            <div class="footer-contact-item">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 0116 0z"/><circle cx="12" cy="10" r="3"/></svg>
              <span>Survey No. 301 P-2, Jada-Kotarwada Rd, Sardarpura, Banaskantha, Gujarat – 385330</span>
            </div>
            <div class="footer-contact-item">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07A19.5 19.5 0 013.07 9.81 19.79 19.79 0 01.1 1.18 2 2 0 012.08 0h3a2 2 0 012 1.72 12.84 12.84 0 00.7 2.81 2 2 0 01-.45 2.11L6.21 7.91a16 16 0 006 6l1.27-1.27a2 2 0 012.11-.45 12.84 12.84 0 002.81.7A2 2 0 0122 14.92v2z"/></svg>
              <a href="tel:+916352098306">+91 63520 98306</a>
            </div>
            <div class="footer-contact-item">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>
              <a href="mailto:info@nagdevproducts.com">info@nagdevproducts.com</a>
            </div>
          </div>
        </address>
      </div>
    </div>
    <div class="footer-bottom">
      <p class="footer-copyright">&copy; 2026 Nagdev Products Private Limited. All rights reserved.</p>
    </div>
  </div>
</footer>

<script src="../js/site.js"></script>
</body>
</html>`;
    }
  };

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function formatDate(isoStr) {
    if (!isoStr) return '';
    try {
      const d = new Date(isoStr);
      return d.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
    } catch (e) {
      return isoStr;
    }
  }

  window.BlogStorage = BlogStorage;
})();
