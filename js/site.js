/* ==========================================================================
   NAGDEV PRODUCTS — SHARED SITE JAVASCRIPT
   Handles: Header scroll, mobile drawer, fade-up animations, toast
   ========================================================================== */

(function () {
  'use strict';

  // ── Header scroll behaviour ──────────────────────────────────────────────
  const header = document.getElementById('site-header');
  if (header) {
    const onScroll = () => {
      header.classList.toggle('scrolled', window.scrollY > 40);
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }

  // ── Mobile drawer ────────────────────────────────────────────────────────
  const mobileToggle   = document.getElementById('mobile-toggle');
  const mobileDrawer   = document.getElementById('mobile-drawer');
  const mobileBackdrop = document.getElementById('mobile-backdrop');
  const mobileClose    = document.getElementById('mobile-drawer-close');

  function openDrawer() {
    if (!mobileDrawer) return;
    mobileDrawer.classList.add('open');
    mobileBackdrop.classList.add('open');
    document.body.classList.add('drawer-open');
    document.body.style.overflow = 'hidden';
    if (mobileToggle) mobileToggle.setAttribute('aria-expanded', 'true');
  }
  function closeDrawer() {
    if (!mobileDrawer) return;
    mobileDrawer.classList.remove('open');
    mobileBackdrop.classList.remove('open');
    document.body.classList.remove('drawer-open');
    document.body.style.overflow = '';
    if (mobileToggle) mobileToggle.setAttribute('aria-expanded', 'false');
  }

  if (mobileToggle)   mobileToggle.addEventListener('click', openDrawer);
  if (mobileClose)    mobileClose.addEventListener('click', closeDrawer);
  if (mobileBackdrop) mobileBackdrop.addEventListener('click', closeDrawer);

  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') closeDrawer();
  });

  // ── Active nav link ──────────────────────────────────────────────────────
  const currentPath = window.location.pathname.split('/').pop() || 'index.html';
  const currentHash = window.location.hash;
  document.querySelectorAll('.nav-link, .mobile-nav-link').forEach(link => {
    const rawHref = link.getAttribute('href') || '';
    const hrefPath = rawHref.split('#')[0].split('/').pop();
    const hrefHash = rawHref.includes('#') ? '#' + rawHref.split('#')[1] : '';

    if (hrefHash) {
      if (currentHash && hrefHash === currentHash) {
        link.classList.add('active');
      }
    } else if (hrefPath === currentPath || (currentPath === '' && hrefPath === 'index.html')) {
      link.classList.add('active');
    }
  });

  // ── Dropdown support for touch/click ─────────────────────────────────────
  const dropdownItem = document.querySelector('.nav-item-has-dropdown');
  if (dropdownItem) {
    const dropdownToggle = dropdownItem.querySelector('.nav-link-dropdown');
    if (dropdownToggle) {
      dropdownToggle.addEventListener('click', function (e) {
        if ('ontouchstart' in window || navigator.maxTouchPoints > 0) {
          if (!dropdownItem.classList.contains('touch-open')) {
            e.preventDefault();
            dropdownItem.classList.add('touch-open');
          }
        }
      });
      document.addEventListener('click', function (e) {
        if (!dropdownItem.contains(e.target)) {
          dropdownItem.classList.remove('touch-open');
        }
      });
    }
  }

  // ── Scroll fade-up animations ────────────────────────────────────────────
  const fadeEls = document.querySelectorAll('.fade-up');
  if (fadeEls.length && 'IntersectionObserver' in window) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });
    fadeEls.forEach(el => observer.observe(el));
  } else {
    fadeEls.forEach(el => el.classList.add('visible'));
  }

  // ── Toast system ─────────────────────────────────────────────────────────
  window.showToast = function (msg, type) {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = msg;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 3200);
  };

  // ── Enquiry form (contact page) ──────────────────────────────────────────
  const enquiryForm = document.getElementById('enquiry-form');
  if (enquiryForm) {
    enquiryForm.addEventListener('submit', function (e) {
      e.preventDefault();
      // Basic validation
      const requiredFields = this.querySelectorAll('[required]');
      let valid = true;
      requiredFields.forEach(field => {
        field.style.borderColor = '';
        if (!field.value.trim()) {
          field.style.borderColor = '#c0392b';
          valid = false;
        }
      });
      if (!valid) {
        window.showToast('Please fill in all required fields.');
        return;
      }
      const btn = this.querySelector('[type="submit"]');
      btn.textContent = 'Submitting…';
      btn.disabled = true;
      // Note: This form requires a backend or email service to deliver enquiries.
      // Currently recording the submission locally. Connect to Formspree / EmailJS / backend to activate.
      setTimeout(() => {
      // Generate enquiry reference: NP-YYYYMMDD-XXXX
      const now = new Date();
      const dateStr = now.getFullYear().toString() +
        String(now.getMonth()+1).padStart(2,'0') +
        String(now.getDate()).padStart(2,'0');
      const refNum = 'NP-' + dateStr + '-' + String(Math.floor(1000 + Math.random() * 9000));
      window.showToast(`Thank you — your enquiry has been received. Reference: ${refNum}. Our team will contact you by email or phone within 1 business day.`);
      enquiryForm.reset();
      btn.textContent = 'Send Enquiry →';
      btn.disabled = false;
    }, 900);
  });
}

// ── WhatsApp Floating Button ─────────────────────────────────────────────────
(function () {
  const waPhone = '916352098306'; // +91 63520 98306
  const waMsg = encodeURIComponent('Hello Nagdev Products, I am interested in your castor oil / derivatives. Please share product specifications, MOQ and pricing.');
  const waUrl = `https://wa.me/${waPhone}?text=${waMsg}`;

  const btn = document.createElement('a');
  btn.href = waUrl;
  btn.target = '_blank';
  btn.rel = 'noopener noreferrer';
  btn.setAttribute('aria-label', 'Chat on WhatsApp');
  btn.setAttribute('title', 'WhatsApp Commercial Enquiry');
  btn.id = 'whatsapp-fab';
  btn.innerHTML = `<svg viewBox="0 0 24 24" fill="currentColor" width="26" height="26" aria-hidden="true">
    <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z"/>
    <path d="M12 0C5.373 0 0 5.373 0 12c0 2.123.554 4.116 1.527 5.845L0 24l6.335-1.502A11.94 11.94 0 0012 24c6.627 0 12-5.373 12-12S18.627 0 12 0zm0 21.818a9.794 9.794 0 01-5.003-1.373l-.36-.214-3.724.883.936-3.617-.235-.373A9.79 9.79 0 012.182 12C2.182 6.575 6.575 2.182 12 2.182S21.818 6.575 21.818 12 17.425 21.818 12 21.818z"/>
  </svg>`;

  const style = document.createElement('style');
  style.textContent = `
    #whatsapp-fab {
      position: fixed;
      bottom: 1.5rem;
      right: 1.5rem;
      z-index: 1500;
      width: 52px;
      height: 52px;
      background: #25D366;
      color: #fff;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 4px 16px rgba(37,211,102,0.45);
      transition: transform 0.2s, box-shadow 0.2s, opacity 0.25s ease, visibility 0.25s ease;
      text-decoration: none;
    }
    #whatsapp-fab:hover {
      transform: scale(1.1);
      box-shadow: 0 6px 22px rgba(37,211,102,0.55);
    }
    body.drawer-open #whatsapp-fab {
      opacity: 0 !important;
      visibility: hidden !important;
      pointer-events: none !important;
    }
    @media (max-width: 768px) {
      #whatsapp-fab { bottom: 1.25rem; right: 1.25rem; width: 48px; height: 48px; }
    }
  `;

  document.head.appendChild(style);
  document.addEventListener('DOMContentLoaded', function () {
    document.body.appendChild(btn);
  });
  if (document.readyState !== 'loading') {
    document.body.appendChild(btn);
  }
})();

// ── Secret 5-Click Logo Admin Panel Trigger ─────────────────────────────────
(function () {
  let logoClickCount = 0;
  let lastClickTime = 0;
  const CLICK_WINDOW_MS = 2500;
  const REQUIRED_CLICKS = 5;
  const AUTH_KEY = 'nagdev_admin_auth';
  const VALID_ID = 'admin';
  const VALID_PIN = '230893';

  function getAdminUrl() {
    const isSubdir = window.location.pathname.includes('/products/') || window.location.pathname.includes('/blog/');
    return isSubdir ? '../blog-admin.html' : 'blog-admin.html';
  }

  function showAdminModal() {
    let modal = document.getElementById('nagdev-admin-trigger-modal');
    if (!modal) {
      modal = document.createElement('div');
      modal.id = 'nagdev-admin-trigger-modal';
      modal.innerHTML = `
        <div style="position:fixed;inset:0;background:rgba(7,40,20,0.85);backdrop-filter:blur(6px);display:flex;align-items:center;justify-content:center;z-index:99999;padding:1rem;">
          <div style="background:#ffffff;border-radius:14px;max-width:400px;width:100%;padding:2rem;box-shadow:0 25px 50px rgba(0,0,0,0.4);border:2px solid #B8841A;text-align:center;position:relative;font-family:'Inter',-apple-system,sans-serif;">
            <button id="admin-trigger-close" style="position:absolute;top:14px;right:16px;background:none;border:none;font-size:1.4rem;color:#888;cursor:pointer;line-height:1;" aria-label="Close">✕</button>
            <div style="font-family:'Cormorant Garamond',Georgia,serif;font-size:1.75rem;font-weight:600;color:#0B3D1E;margin-bottom:0.25rem;">Admin Studio</div>
            <p style="font-size:0.85rem;color:#666;margin-bottom:1.5rem;">Enter administrative credentials to open Editorial Studio</p>
            <form id="admin-trigger-form" autocomplete="off" style="text-align:left;">
              <div style="margin-bottom:1rem;">
                <label style="display:block;font-size:0.8rem;font-weight:600;color:#222;margin-bottom:0.3rem;">Login ID</label>
                <input type="text" id="trigger-login-id" style="width:100%;padding:0.7rem 0.85rem;border-radius:6px;border:1px solid #ddd;font-size:0.95rem;box-sizing:border-box;outline:none;" placeholder="Enter ID (Admin)" required autocomplete="username">
              </div>
              <div style="margin-bottom:1.25rem;">
                <label style="display:block;font-size:0.8rem;font-weight:600;color:#222;margin-bottom:0.3rem;">PIN Code</label>
                <input type="password" id="trigger-login-pin" maxlength="10" style="width:100%;padding:0.7rem 0.85rem;border-radius:6px;border:1px solid #ddd;font-size:0.95rem;box-sizing:border-box;outline:none;" placeholder="Enter 6-digit PIN" required autocomplete="current-password">
              </div>
              <div id="trigger-error" style="display:none;color:#c0392b;font-size:0.825rem;font-weight:600;margin-bottom:1rem;padding:0.4rem 0.6rem;background:#fee;border-radius:4px;border:1px solid #fcc;">
                Invalid Login ID or PIN.
              </div>
              <button type="submit" style="width:100%;padding:0.75rem;border-radius:6px;background:#0B3D1E;color:#fff;border:none;font-weight:600;font-size:0.95rem;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:0.5rem;">
                Unlock Studio →
              </button>
            </form>
          </div>
        </div>
      `;
      document.body.appendChild(modal);

      const closeBtn = modal.querySelector('#admin-trigger-close');
      closeBtn.addEventListener('click', () => { modal.style.display = 'none'; });

      const form = modal.querySelector('#admin-trigger-form');
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
      });
    }

    modal.style.display = 'block';
    const idInput = modal.querySelector('#trigger-login-id');
    const pinInput = modal.querySelector('#trigger-login-pin');
    const errEl = modal.querySelector('#trigger-error');
    if (errEl) errEl.style.display = 'none';
    if (idInput) { idInput.value = ''; idInput.focus(); }
    if (pinInput) pinInput.value = '';
  }

  function handleLogoClick(e) {
    const now = Date.now();
    if (now - lastClickTime > CLICK_WINDOW_MS) {
      logoClickCount = 1;
    } else {
      logoClickCount++;
    }
    lastClickTime = now;

    if (logoClickCount === REQUIRED_CLICKS) {
      e.preventDefault();
      e.stopPropagation();
      logoClickCount = 0;

      // Check if already authenticated
      if (sessionStorage.getItem(AUTH_KEY) === 'true') {
        if (window.showToast) window.showToast('Opening Admin Studio…');
        setTimeout(() => {
          window.location.href = getAdminUrl();
        }, 200);
      } else {
        showAdminModal();
      }
    }
  }

  function attachListeners() {
    const logos = document.querySelectorAll('.header-logo, .mobile-drawer-header img, [data-admin-trigger]');
    logos.forEach(logo => {
      logo.removeEventListener('click', handleLogoClick);
      logo.addEventListener('click', handleLogoClick);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', attachListeners);
  } else {
    attachListeners();
  }
})();

})();
