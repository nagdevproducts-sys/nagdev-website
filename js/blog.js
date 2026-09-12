/**
 * NAGDEV PRODUCTS — BLOG DIRECTORY CONTROLLER
 * Handles client-side rendering, instant search, and category filtering.
 */

(function () {
  'use strict';

  let allPosts = [];
  let currentCategory = 'all';
  let searchQuery = '';

  const featuredContainer = document.getElementById('featured-post-container');
  const featuredSection = document.getElementById('featured-section');
  const postsGrid = document.getElementById('blog-posts-grid');
  const searchInput = document.getElementById('blog-search-input');
  const categoryFilters = document.getElementById('category-filters');
  const noResultsBox = document.getElementById('blog-no-results');
  const resetBtn = document.getElementById('reset-filters-btn');

  // Format date helper
  function formatDate(isoStr) {
    if (!isoStr) return '';
    try {
      const d = new Date(isoStr);
      return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
    } catch (e) {
      return isoStr;
    }
  }

  // Escape HTML
  function esc(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  // Known pre-rendered static HTML files in /blog/
  const PRE_RENDERED_SLUGS = [
    'sustainable-castor-oil-derivatives-green-chemistry',
    'hydrogenated-castor-oil-12-hsa-lithium-greases',
    'dehydrated-castor-oil-alkyd-resins-coatings',
    'bio-based-polyurethane-polyols-castor-oil'
  ];

  // Get article link (pre-rendered static file if exists, or fallback to blog-post.html)
  function getPostLink(post) {
    if (!post) return 'blog.html';
    if (post.slug && PRE_RENDERED_SLUGS.includes(post.slug)) {
      return `blog/${post.slug}.html`;
    }
    // Dynamic or browser-authored post:
    return `blog-post.html?slug=${encodeURIComponent(post.slug)}`;
  }

  // Render featured post
  function renderFeatured(post) {
    if (!featuredContainer || !post) {
      if (featuredSection) featuredSection.style.display = 'none';
      return;
    }

    if (featuredSection) featuredSection.style.display = '';
    const link = getPostLink(post);
    featuredContainer.innerHTML = `
      <div class="featured-card">
        <a href="${link}" class="featured-media" aria-label="${esc(post.title)}">
          <img src="${post.coverImage}" alt="${esc(post.title)}" width="1200" height="630" loading="eager">
        </a>
        <div class="featured-content">
          <span class="featured-badge">✦ Featured Insight · ${esc(post.category)}</span>
          <h2 class="featured-title">
            <a href="${link}">${esc(post.title)}</a>
          </h2>
          <p class="featured-excerpt">${esc(post.seoDescription || '')}</p>
          <div class="featured-meta">
            <span>By ${esc(post.author || 'Nagdev Products')}</span>
            <span>•</span>
            <time datetime="${post.date}">${formatDate(post.date)}</time>
            <span>•</span>
            <span>${esc(post.readTime || '5 min read')}</span>
          </div>
          <div>
            <a href="${link}" class="btn btn-primary btn-sm">Read Full Paper →</a>
          </div>
        </div>
      </div>
    `;
  }

  // Render grid cards
  function renderGrid(posts) {
    if (!postsGrid) return;
    if (!posts.length) {
      postsGrid.innerHTML = '';
      if (noResultsBox) noResultsBox.style.display = 'block';
      return;
    }

    if (noResultsBox) noResultsBox.style.display = 'none';

    postsGrid.innerHTML = posts.map(post => {
      const link = getPostLink(post);
      return `
        <article class="blog-card">
          <a href="${link}" class="blog-card-media" aria-label="${esc(post.title)}">
            <img src="${post.coverImage}" alt="${esc(post.title)}" width="600" height="315" loading="lazy">
          </a>
          <div class="blog-card-body">
            <div class="blog-card-category">${esc(post.category)}</div>
            <h3 class="blog-card-title">
              <a href="${link}">${esc(post.title)}</a>
            </h3>
            <p class="blog-card-excerpt">${esc(post.seoDescription || '')}</p>
            <div class="blog-card-footer">
              <time datetime="${post.date}">${formatDate(post.date)} · ${esc(post.readTime || '5 min')}</time>
              <a href="${link}" class="blog-read-link">Read →</a>
            </div>
          </div>
        </article>
      `;
    }).join('');
  }

  // Filter posts based on search and category
  function applyFilters() {
    let filtered = allPosts.slice();

    // Category filter
    if (currentCategory !== 'all') {
      filtered = filtered.filter(p => p.category === currentCategory);
    }

    // Search query filter
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      filtered = filtered.filter(p => {
        const titleMatch = (p.title || '').toLowerCase().includes(q);
        const descMatch = (p.seoDescription || '').toLowerCase().includes(q);
        const tagsMatch = (p.tags || []).some(t => t.toLowerCase().includes(q));
        const authorMatch = (p.author || '').toLowerCase().includes(q);
        return titleMatch || descMatch || tagsMatch || authorMatch;
      });
    }

    // If searching or filtering by category, hide separate featured banner and show all filtered in grid
    if (currentCategory !== 'all' || searchQuery.trim()) {
      if (featuredSection) featuredSection.style.display = 'none';
      renderGrid(filtered);
    } else {
      // Normal state: pick featured post and render all publications in grid (newest first)
      const featured = filtered.find(p => p.featured) || filtered[0];
      renderFeatured(featured);
      renderGrid(filtered);
    }
  }

  // Initialize
  async function init() {
    if (window.BlogStorage) {
      allPosts = await window.BlogStorage.getAllPosts();
    } else {
      allPosts = window.NAGDEV_BLOG_POSTS || [];
    }

    applyFilters();

    // Category click handler
    if (categoryFilters) {
      categoryFilters.addEventListener('click', (e) => {
        const btn = e.target.closest('.blog-filter-btn');
        if (!btn) return;
        categoryFilters.querySelectorAll('.blog-filter-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentCategory = btn.getAttribute('data-category') || 'all';
        applyFilters();
      });
    }

    // Search input handler
    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        searchQuery = e.target.value;
        applyFilters();
      });
    }

    // Reset button
    if (resetBtn) {
      resetBtn.addEventListener('click', () => {
        if (searchInput) searchInput.value = '';
        searchQuery = '';
        currentCategory = 'all';
        if (categoryFilters) {
          categoryFilters.querySelectorAll('.blog-filter-btn').forEach((b, idx) => {
            b.classList.toggle('active', idx === 0);
          });
        }
        applyFilters();
      });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
