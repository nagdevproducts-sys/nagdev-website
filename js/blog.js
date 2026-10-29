/**
 * NAGDEV PRODUCTS — BLOG DIRECTORY CONTROLLER
 * Progressive Enhancement: operates strictly on server-rendered cards.
 * No data array re-rendering, no IndexedDB / localStorage.
 */

(function () {
  'use strict';

  const POSTS_PER_PAGE = 12;

  let currentFilter = 'all';
  let searchQuery = '';
  let currentPage = 1;

  const featuredSection = document.getElementById('featured-section');
  const postsGrid = document.getElementById('blog-posts-grid');
  const searchInput = document.getElementById('blog-search-input');
  const filterContainer = document.getElementById('category-filters');
  const noResultsBox = document.getElementById('blog-no-results');
  const resetBtn = document.getElementById('reset-filters-btn');
  let paginationContainer = document.getElementById('blog-pagination');

  if (!postsGrid) return;

  const cards = Array.from(postsGrid.querySelectorAll('.blog-card'));

  // Ensure pagination container exists in DOM if not present
  if (!paginationContainer) {
    paginationContainer = document.createElement('nav');
    paginationContainer.id = 'blog-pagination';
    paginationContainer.className = 'blog-pagination';
    paginationContainer.setAttribute('aria-label', 'Blog pagination');
    postsGrid.parentNode.insertBefore(paginationContainer, postsGrid.nextSibling);
  }

  function matchesFilter(card, filter) {
    if (filter === 'all') return true;
    const type = (card.getAttribute('data-type') || '').trim();
    const cat = (card.getAttribute('data-category') || '').trim().toLowerCase();
    const lang = (card.getAttribute('data-lang') || '').trim().toLowerCase();
    const f = filter.toLowerCase().trim();

    if (f === 'guide' || f === 't1') {
      return type === 'T1' || cat.includes('guide');
    }
    if (f === 'application' || f === 't2') {
      return type === 'T2' || cat.includes('application');
    }
    if (f === 'buyer' || f === 't3') {
      return type === 'T3' || cat.includes('buyer') || cat.includes('procurement');
    }
    if (f === 'regional' || f === 't4') {
      return type === 'T4' || cat.includes('regional');
    }
    if (f === 'gu' || f === 't5') {
      return type === 'T5' || lang === 'gu';
    }
    return type.toLowerCase() === f || cat === f;
  }

  function matchesSearch(card, query) {
    if (!query) return true;
    const q = query.toLowerCase().trim();
    const title = (card.querySelector('.blog-card-title')?.textContent || '').toLowerCase();
    const excerpt = (card.querySelector('.blog-card-excerpt')?.textContent || '').toLowerCase();
    const category = (card.querySelector('.blog-card-category')?.textContent || '').toLowerCase();
    return title.includes(q) || excerpt.includes(q) || category.includes(q);
  }

  function renderPagination(totalPages, activePage) {
    if (!paginationContainer) return;
    if (totalPages <= 1) {
      paginationContainer.style.display = 'none';
      paginationContainer.innerHTML = '';
      return;
    }

    paginationContainer.style.display = 'flex';
    let html = '';

    // Prev Button
    html += `<button class="blog-pagination-btn prev-btn" ${activePage === 1 ? 'disabled' : ''} data-page="${activePage - 1}" aria-label="Previous page">&larr; Prev</button>`;

    // Page numbers
    for (let p = 1; p <= totalPages; p++) {
      html += `<button class="blog-pagination-btn page-num ${p === activePage ? 'active' : ''}" data-page="${p}" aria-label="Page ${p}" ${p === activePage ? 'aria-current="page"' : ''}>${p}</button>`;
    }

    // Next Button
    html += `<button class="blog-pagination-btn next-btn" ${activePage === totalPages ? 'disabled' : ''} data-page="${activePage + 1}" aria-label="Next page">Next &rarr;</button>`;

    paginationContainer.innerHTML = html;
  }

  function updateView() {
    const matchingCards = [];

    cards.forEach(card => {
      if (matchesFilter(card, currentFilter) && matchesSearch(card, searchQuery)) {
        matchingCards.push(card);
      } else {
        card.style.display = 'none';
      }
    });

    const totalMatching = matchingCards.length;

    if (totalMatching === 0) {
      if (noResultsBox) noResultsBox.style.display = 'block';
      if (paginationContainer) paginationContainer.style.display = 'none';
      if (featuredSection) featuredSection.style.display = 'none';
      return;
    }

    if (noResultsBox) noResultsBox.style.display = 'none';

    // Show featured only on page 1 of 'all' without search
    if (featuredSection) {
      if (currentFilter === 'all' && !searchQuery.trim() && currentPage === 1) {
        featuredSection.style.display = '';
      } else {
        featuredSection.style.display = 'none';
      }
    }

    const totalPages = Math.ceil(totalMatching / POSTS_PER_PAGE);
    if (currentPage > totalPages) currentPage = totalPages;
    if (currentPage < 1) currentPage = 1;

    const startIndex = (currentPage - 1) * POSTS_PER_PAGE;
    const endIndex = startIndex + POSTS_PER_PAGE;

    matchingCards.forEach((card, idx) => {
      if (idx >= startIndex && idx < endIndex) {
        card.style.display = '';
      } else {
        card.style.display = 'none';
      }
    });

    renderPagination(totalPages, currentPage);
  }

  // Filter click handler
  if (filterContainer) {
    filterContainer.addEventListener('click', (e) => {
      const btn = e.target.closest('.blog-filter-btn');
      if (!btn) return;
      filterContainer.querySelectorAll('.blog-filter-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentFilter = btn.getAttribute('data-filter') || btn.getAttribute('data-category') || 'all';
      currentPage = 1;
      updateView();
    });
  }

  // Search input handler
  if (searchInput) {
    let debounceTimer;
    searchInput.addEventListener('input', (e) => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        searchQuery = e.target.value;
        currentPage = 1;
        updateView();
      }, 150);
    });
  }

  // Reset button handler
  if (resetBtn) {
    resetBtn.addEventListener('click', () => {
      if (searchInput) searchInput.value = '';
      searchQuery = '';
      currentFilter = 'all';
      currentPage = 1;
      if (filterContainer) {
        filterContainer.querySelectorAll('.blog-filter-btn').forEach((b, idx) => {
          b.classList.toggle('active', idx === 0);
        });
      }
      updateView();
    });
  }

  // Pagination click handler
  if (paginationContainer) {
    paginationContainer.addEventListener('click', (e) => {
      const btn = e.target.closest('.blog-pagination-btn');
      if (!btn || btn.disabled) return;
      const targetPage = parseInt(btn.getAttribute('data-page'), 10);
      if (!isNaN(targetPage) && targetPage !== currentPage) {
        currentPage = targetPage;
        updateView();
        const header = document.querySelector('.section-header') || postsGrid;
        if (header) {
          header.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      }
    });
  }

  // Initial execution to setup page 1
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', updateView);
  } else {
    updateView();
  }
})();
