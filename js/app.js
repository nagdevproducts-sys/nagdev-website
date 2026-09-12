/**
 * NAGDEV PRODUCTS PRIVATE LIMITED — SHARED APP SCRIPT
 * Handles: sticky header scroll, mobile drawer, smooth scroll, header utilities
 */

(function() {
  'use strict';

  // ── Sticky Header ────────────────────────────────────────────────────────────
  var header = document.getElementById('site-header');
  if (header) {
    window.addEventListener('scroll', function() {
      header.classList.toggle('scrolled', window.scrollY > 30);
    }, { passive: true });
  }

  // ── Mobile Drawer ─────────────────────────────────────────────────────────────
  var toggle   = document.getElementById('mobile-toggle');
  var backdrop = document.getElementById('mobile-drawer-backdrop');
  var drawer   = document.getElementById('mobile-nav-drawer');
  var closeBtn = document.getElementById('mobile-drawer-close');

  function openDrawer() {
    if (!drawer) return;
    drawer.classList.add('active');
    backdrop.classList.add('active');
    document.body.style.overflow = 'hidden';
  }

  function closeDrawer() {
    if (!drawer) return;
    drawer.classList.remove('active');
    backdrop.classList.remove('active');
    document.body.style.overflow = '';
  }

  if (toggle)   toggle.addEventListener('click', openDrawer);
  if (closeBtn) closeBtn.addEventListener('click', closeDrawer);
  if (backdrop) backdrop.addEventListener('click', closeDrawer);

  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') closeDrawer();
  });

  // ── Toast Utility ─────────────────────────────────────────────────────────────
  window.quoteApp = {
    showToast: function(msg) {
      var container = document.getElementById('toast-container');
      if (!container) return;
      var toast = document.createElement('div');
      toast.className = 'toast';
      toast.textContent = msg;
      container.appendChild(toast);
      setTimeout(function() { toast.remove(); }, 3200);
    }
  };

  // ── Smooth scroll for anchor links ───────────────────────────────────────────
  document.querySelectorAll('a[href^="#"]').forEach(function(a) {
    a.addEventListener('click', function(e) {
      var target = document.querySelector(this.getAttribute('href'));
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });

})();
