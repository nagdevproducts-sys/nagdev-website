/* ==========================================================================
   NAGDEV PRODUCTS — SHARED SITE JAVASCRIPT
   Handles: Header scroll, mobile drawer, fade-up animations, toast
   ========================================================================== */

(function () {
  'use strict';

  // ── Header scroll behaviour ──────────────────────────────────────────────
  const header = document.getElementById('site-header');
  if (header) {
    const topBar = document.querySelector('.top-bar');
    let ticking = false;
    const onScroll = () => {
      if (!ticking) {
        window.requestAnimationFrame(() => {
          const topBarH = (topBar && topBar.offsetHeight) ? topBar.offsetHeight : 35;
          header.classList.toggle('scrolled', window.scrollY > topBarH);
          ticking = false;
        });
        ticking = true;
      }
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    if (window.scrollY > 0) {
      onScroll();
    } else {
      header.classList.remove('scrolled');
    }
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
  const rawPath = window.location.pathname.replace(/\/$/, '').split('/').pop() || '';
  const currentPath = (rawPath === '' || rawPath === 'index.html') ? '' : rawPath.replace(/\.html$/, '');
  const currentHash = window.location.hash;
  document.querySelectorAll('.nav-link, .mobile-nav-link').forEach(link => {
    const rawHref = link.getAttribute('href') || '';
    const hrefClean = (rawHref.split('#')[0].replace(/\/$/, '').split('/').pop() || '').replace(/\.html$/, '');
    const hrefHash = rawHref.includes('#') ? '#' + rawHref.split('#')[1] : '';

    if (hrefHash) {
      if (currentHash && hrefHash === currentHash) {
        link.classList.add('active');
      }
    } else if (hrefClean === currentPath || (currentPath === '' && (rawHref === '/' || hrefClean === ''))) {
      link.classList.add('active');
    }
  });

  // ── Mega-Menu: Navigation, Hover, Keyboard & Touch Support (Phase 11) ────
  const dropdownItem = document.querySelector('.nav-item-has-dropdown');
  if (dropdownItem) {
    const dropdownToggle = dropdownItem.querySelector('.nav-link-dropdown');
    const megaMenu = dropdownItem.querySelector('.mega-menu');
    let closeTimer = null;

    function openMenu() {
      if (closeTimer) {
        clearTimeout(closeTimer);
        closeTimer = null;
      }
      dropdownItem.classList.add('is-open');
      dropdownItem.classList.add('touch-open');
      if (dropdownToggle) dropdownToggle.setAttribute('aria-expanded', 'true');
    }

    function closeMenu(immediate = false) {
      if (immediate) {
        if (closeTimer) {
          clearTimeout(closeTimer);
          closeTimer = null;
        }
        dropdownItem.classList.remove('is-open');
        dropdownItem.classList.remove('touch-open');
        if (dropdownToggle) dropdownToggle.setAttribute('aria-expanded', 'false');
      } else {
        if (closeTimer) clearTimeout(closeTimer);
        closeTimer = setTimeout(() => {
          dropdownItem.classList.remove('is-open');
          dropdownItem.classList.remove('touch-open');
          if (dropdownToggle) dropdownToggle.setAttribute('aria-expanded', 'false');
          closeTimer = null;
        }, 300);
      }
    }

    // HOVER (fine pointer): opens the mega-menu; stays open while pointer is on trigger or panel, closes 300ms after leaving
    dropdownItem.addEventListener('mouseenter', () => {
      if (window.matchMedia('(pointer: fine)').matches) {
        openMenu();
      }
    });

    dropdownItem.addEventListener('mouseleave', () => {
      if (window.matchMedia('(pointer: fine)').matches) {
        closeMenu(false); // 300ms delay
      }
    });

    if (dropdownToggle) {
      // CLICK on "Products":
      // Fine pointer (mouse) -> navigates to /products directly (default anchor navigation)
      // Touch (coarse pointer): the FIRST tap opens the menu; a tap outside closes it.
      dropdownToggle.addEventListener('click', (e) => {
        const isCoarse = window.matchMedia('(pointer: coarse)').matches;
        const isOpen = dropdownItem.classList.contains('is-open');
        if (isCoarse) {
          if (!isOpen) {
            e.preventDefault();
            openMenu();
          }
          // If already open on touch, clicking again navigates to /products
        }
        // Fine pointer: default action (navigates to /products) proceeds!
      });

      // KEYBOARD:
      // Enter on "Products" navigates to /products (default anchor navigation)
      // ArrowDown / Space opens the menu and focuses the first link; Esc closes it
      dropdownToggle.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          // Navigates to /products (default action)
        } else if (e.key === 'ArrowDown' || e.key === ' ') {
          e.preventDefault();
          openMenu();
          const firstLink = megaMenu ? megaMenu.querySelector('a') : null;
          if (firstLink) firstLink.focus();
        } else if (e.key === 'Escape') {
          e.preventDefault();
          closeMenu(true);
        }
      });
    }

    // Touch / click outside closes menu
    document.addEventListener('click', (e) => {
      if (!dropdownItem.contains(e.target)) {
        closeMenu(true);
      }
    });
    document.addEventListener('touchstart', (e) => {
      if (!dropdownItem.contains(e.target)) {
        closeMenu(true);
      }
    }, { passive: true });

    // Escape closes menu anywhere
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && dropdownItem.classList.contains('is-open')) {
        closeMenu(true);
        if (dropdownToggle) dropdownToggle.focus();
      }
    });

    // Clicking any link inside mega menu closes immediately
    if (megaMenu) {
      megaMenu.querySelectorAll('a').forEach(link => {
        link.addEventListener('click', () => {
          closeMenu(true);
        });
      });
    }

    // Column arrow-key navigation inside megaMenu
    dropdownItem.addEventListener('keydown', (e) => {
      if (megaMenu && (e.key === 'ArrowLeft' || e.key === 'ArrowRight' || e.key === 'ArrowUp' || e.key === 'ArrowDown')) {
        const target = e.target;
        if (target && target.tagName === 'A' && megaMenu.contains(target)) {
          const cols = Array.from(megaMenu.querySelectorAll('.mega-col'));
          const currentCol = target.closest('.mega-col');
          if (currentCol) {
            const colIndex = cols.indexOf(currentCol);
            const colLinks = Array.from(currentCol.querySelectorAll('a'));
            const linkIndex = colLinks.indexOf(target);

            if (e.key === 'ArrowDown') {
              if (linkIndex >= 0 && linkIndex < colLinks.length - 1) {
                e.preventDefault();
                colLinks[linkIndex + 1].focus();
              } else if (linkIndex === colLinks.length - 1) {
                const footerFirst = megaMenu.querySelector('.mega-menu-bottom a');
                if (footerFirst) {
                  e.preventDefault();
                  footerFirst.focus();
                }
              }
            } else if (e.key === 'ArrowUp') {
              if (linkIndex > 0) {
                e.preventDefault();
                colLinks[linkIndex - 1].focus();
              } else if (linkIndex === 0) {
                e.preventDefault();
                const topLink = megaMenu.querySelector('.mega-top-link');
                if (topLink && target !== topLink) {
                  topLink.focus();
                } else if (dropdownToggle) {
                  dropdownToggle.focus();
                }
              }
            } else if (e.key === 'ArrowRight' && colIndex < cols.length - 1) {
              e.preventDefault();
              const nextColLinks = Array.from(cols[colIndex + 1].querySelectorAll('a'));
              const targetIdx = Math.min(linkIndex, nextColLinks.length - 1);
              if (targetIdx >= 0 && nextColLinks[targetIdx]) {
                nextColLinks[targetIdx].focus();
              }
            } else if (e.key === 'ArrowLeft' && colIndex > 0) {
              e.preventDefault();
              const prevColLinks = Array.from(cols[colIndex - 1].querySelectorAll('a'));
              const targetIdx = Math.min(linkIndex, prevColLinks.length - 1);
              if (targetIdx >= 0 && prevColLinks[targetIdx]) {
                prevColLinks[targetIdx].focus();
              }
            }
          } else if (target.closest('.mega-menu-bottom')) {
            const footerLinks = Array.from(megaMenu.querySelectorAll('.mega-menu-bottom a'));
            const fIndex = footerLinks.indexOf(target);
            if (e.key === 'ArrowRight' && fIndex < footerLinks.length - 1) {
              e.preventDefault();
              footerLinks[fIndex + 1].focus();
            } else if (e.key === 'ArrowLeft' && fIndex > 0) {
              e.preventDefault();
              footerLinks[fIndex - 1].focus();
            } else if (e.key === 'ArrowUp') {
              e.preventDefault();
              const lastColLinks = Array.from(cols[0].querySelectorAll('a'));
              if (lastColLinks.length) lastColLinks[lastColLinks.length - 1].focus();
            }
          } else if (target.classList.contains('mega-top-link')) {
            if (e.key === 'ArrowDown') {
              e.preventDefault();
              const firstColLink = megaMenu.querySelector('.mega-col a');
              if (firstColLink) firstColLink.focus();
            } else if (e.key === 'ArrowUp') {
              e.preventDefault();
              if (dropdownToggle) dropdownToggle.focus();
            }
          }
        }
      }
    });
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
  const alertContainer = document.getElementById('enquiry-alert-container');

  // Set initial form timestamp for spam protection
  const formTsInput = document.getElementById('form-timestamp');
  if (formTsInput) formTsInput.value = Date.now().toString();

  function escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/[&<>"']/g, function (m) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m];
    });
  }

  function renderEnquirySuccess(refNum, product, company, name, email) {
    if (!alertContainer) return;
    const safeRef = escapeHtml(refNum);
    const safeProd = escapeHtml(product || 'General Commercial Product');
    const safeCo = escapeHtml(company || '');
    const safeName = escapeHtml(name || '');
    const safeEmail = escapeHtml(email || 'your email');

    const waText = encodeURIComponent(
      `Hello Nagdev Products Sales Desk, I have submitted an official enquiry (Ref: ${refNum}) for ${product}${company ? ' on behalf of ' + company : ''}. Please confirm receipt and share quotation.`
    );
    const waUrl = `https://wa.me/916352098306?text=${waText}`;

    alertContainer.style.display = 'block';
    alertContainer.innerHTML = `
      <div style="background:#f4f6f2;border:2px solid var(--forest);border-radius:10px;padding:2rem;margin-bottom:2rem;box-shadow:0 4px 16px rgba(11,61,30,0.08);">
        <div style="display:flex;align-items:flex-start;gap:1rem;margin-bottom:1.5rem;">
          <div style="width:48px;height:48px;border-radius:50%;background:var(--forest);color:#fff;display:flex;align-items:center;justify-content:center;flex-shrink:0;">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="24" height="24" aria-hidden="true"><polyline points="20 6 9 17 4 12"/></svg>
          </div>
          <div>
            <div style="font-size:0.75rem;font-weight:700;color:var(--gold-text, #6B5628);text-transform:uppercase;letter-spacing:0.08em;margin-bottom:0.25rem;">Enquiry Successfully Received</div>
            <h3 style="font-family:var(--font-display);font-size:1.6rem;color:var(--forest);margin:0 0 0.25rem 0;">Thank You, ${safeName || 'Valued Buyer'}</h3>
            <p style="margin:0;color:var(--text-muted);font-size:0.9rem;">Your commercial inquiry has been logged in our enterprise dispatch system.</p>
          </div>
        </div>

        <div style="background:#fff;border:1px solid var(--border-light);border-radius:8px;padding:1.25rem;margin-bottom:1.5rem;">
          <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(200px, 1fr));gap:1rem;font-size:0.875rem;">
            <div>
              <span style="color:var(--text-muted);display:block;font-size:0.75rem;text-transform:uppercase;letter-spacing:0.05em;">Reference Number</span>
              <strong style="color:var(--forest);font-family:monospace;font-size:1.05rem;">${safeRef}</strong>
            </div>
            <div>
              <span style="color:var(--text-muted);display:block;font-size:0.75rem;text-transform:uppercase;letter-spacing:0.05em;">Product Required</span>
              <strong>${safeProd}</strong>
            </div>
            <div>
              <span style="color:var(--text-muted);display:block;font-size:0.75rem;text-transform:uppercase;letter-spacing:0.05em;">Registered Email</span>
              <span>${safeEmail}</span>
            </div>
            <div>
              <span style="color:var(--text-muted);display:block;font-size:0.75rem;text-transform:uppercase;letter-spacing:0.05em;">Commercial Desk SLA</span>
              <strong style="color:#27ae60;">Response within 24 business hours</strong>
            </div>
          </div>
        </div>

        <div style="display:flex;gap:0.75rem;flex-wrap:wrap;align-items:center;">
          <a href="${waUrl}" target="_blank" rel="noopener noreferrer" class="btn btn-primary btn-sm" style="background:#25D366;border-color:#25D366;color:#fff;">
            Confirm on WhatsApp &rarr;
          </a>
          <button type="button" id="btn-reset-enquiry" class="btn btn-outline btn-sm" style="color:var(--forest);">
            Submit Another Inquiry
          </button>
        </div>
      </div>
    `;

    document.getElementById('btn-reset-enquiry')?.addEventListener('click', function () {
      alertContainer.style.display = 'none';
      if (enquiryForm) {
        enquiryForm.style.display = 'block';
        enquiryForm.reset();
        const tsInput = document.getElementById('form-timestamp');
        if (tsInput) tsInput.value = Date.now().toString();
      }
    });

    alertContainer.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

  function showEnquiryError(name, company, product, message) {
    const errContainer = document.getElementById('enquiry-error-container');
    if (errContainer) {
      const summary = `Hello Nagdev Products Sales Desk, my website enquiry could not be sent online. Here are my details:\nName: ${name || ''}\nCompany: ${company || ''}\nProduct: ${product || ''}\nMessage: ${message || 'Quotation request'}`;
      const waBtn = errContainer.querySelector('#error-whatsapp-btn');
      if (waBtn) {
        waBtn.href = `https://wa.me/916352098306?text=${encodeURIComponent(summary)}`;
      }
      errContainer.style.display = 'block';
      errContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
    window.showToast('Sorry, your enquiry could not be sent. Please WhatsApp us at +91 63520 98306 or email nagdevproducts@gmail.com.');
  }

  if (enquiryForm) {
    enquiryForm.addEventListener('submit', async function (e) {
      e.preventDefault();

      const errContainer = document.getElementById('enquiry-error-container');
      if (errContainer) errContainer.style.display = 'none';

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

      const emailInput = this.querySelector('input[name="email"]');
      if (emailInput && emailInput.value.trim()) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(emailInput.value.trim())) {
          emailInput.style.borderColor = '#c0392b';
          valid = false;
          window.showToast('Please provide a valid email address.');
          return;
        }
      }

      if (!valid) {
        window.showToast('Please fill in all required fields marked with *');
        return;
      }

      const btn = this.querySelector('[type="submit"]');
      const originalBtnText = btn.innerHTML;
      btn.innerHTML = `<span style="display:inline-block;width:14px;height:14px;border:2px solid #fff;border-top-color:transparent;border-radius:50%;animation:spin 0.6s linear infinite;margin-right:6px;vertical-align:middle;"></span> Sending enquiry…`;
      btn.disabled = true;

      const nameVal = (this.querySelector('input[name="name"]')?.value || '').trim();
      const companyVal = (this.querySelector('input[name="company"]')?.value || '').trim();
      const emailVal = (this.querySelector('input[name="email"]')?.value || '').trim();
      const phoneVal = (this.querySelector('input[name="phone"]')?.value || '').trim();
      const countryVal = (this.querySelector('input[name="country"]')?.value || '').trim();
      const enquiryTypeVal = (this.querySelector('select[name="enquiry_type"]')?.value || '').trim();
      const productVal = (this.querySelector('select[name="product"]')?.value || '').trim();
      const quantityVal = (this.querySelector('input[name="quantity"]')?.value || '').trim();
      const packingVal = (this.querySelector('select[name="packing"]')?.value || '').trim();
      const messageVal = (this.querySelector('textarea[name="message"]')?.value || '').trim();

      const sampleHidden = document.getElementById('sample-products-hidden');
      const sampleSlugsVal = (sampleHidden ? sampleHidden.value : '') || '';

      const payload = {
        name: nameVal,
        company: companyVal,
        email: emailVal,
        phone: phoneVal,
        country: countryVal,
        enquiry_type: enquiryTypeVal,
        product: productVal,
        quantity: quantityVal,
        packing: packingVal,
        message: messageVal,
        sample_products: sampleSlugsVal,
        _honey: (this.querySelector('input[name="_honey"]')?.value || '').trim(),
        _timestamp: (document.getElementById('form-timestamp')?.value || Date.now().toString()).trim(),
        page_url: window.location.href,
        utm_source: new URLSearchParams(window.location.search).get('utm_source') || ''
      };

      try {
        const response = await fetch('/api/enquiry', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          },
          body: JSON.stringify(payload)
        });

        const resData = await response.json().catch(() => ({}));

        if (response.ok && resData.ok === true) {
          const serverRef = resData.ref;
          window.showToast(`Enquiry ${serverRef} received!`);
          enquiryForm.style.display = 'none';
          renderEnquirySuccess(serverRef, productVal, companyVal, nameVal, emailVal);

          let formType = 'quote';
          if (enquiryTypeVal.includes('Sample') || sampleSlugsVal) formType = 'sample';
          else if (enquiryTypeVal.includes('TDS') || enquiryTypeVal.includes('Specification')) formType = 'sds';
          else if (enquiryTypeVal.includes('Quote') || enquiryTypeVal.includes('Bulk')) formType = 'quote';
          else formType = 'general';

          window.dispatchEvent(new CustomEvent('nagdev_lead_success', {
            detail: {
              ref: serverRef,
              form_type: formType,
              product_slug: sampleSlugsVal || productVal,
              product_slugs: sampleSlugsVal || productVal,
              country: countryVal
            }
          }));

          if (typeof window.clearSampleCart === 'function') {
            window.clearSampleCart();
          }
        } else {
          showEnquiryError(nameVal, companyVal, productVal, messageVal);
        }
      } catch (err) {
        console.error('Enquiry dispatch error:', err);
        showEnquiryError(nameVal, companyVal, productVal, messageVal);
      } finally {
        btn.innerHTML = originalBtnText;
        btn.disabled = false;
      }
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

  // WhatsApp FAB styling moved to css/main.css
  function appendFab() {
    if (!document.getElementById('whatsapp-fab') && document.body) {
      document.body.appendChild(btn);
    }
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', appendFab);
  } else {
    appendFab();
  }
})();


  // ── Dynamic TDS Generator Loader (P0-4) ──────────────────────────────────
  window.downloadProductTDS = function (productId, targetBtn) {
    if (window._realDownloadProductTDS) {
      return window._realDownloadProductTDS(productId);
    }

    const btn = targetBtn || (window.event && window.event.currentTarget) || document.getElementById('print-tds-btn');
    let origHtml = '';
    if (btn) {
      origHtml = btn.innerHTML;
      btn.disabled = true;
      btn.style.pointerEvents = 'none';
      btn.innerHTML = '<span style="display:inline-block;width:13px;height:13px;border:2px solid currentColor;border-top-color:transparent;border-radius:50%;animation:spin 0.6s linear infinite;margin-right:6px;vertical-align:middle;"></span> Generating TDS...';
    }

    const script = document.createElement('script');
    script.src = '/js/tds-generator.js';
    script.async = true;
    script.onload = function () {
      if (btn) {
        btn.innerHTML = origHtml;
        btn.disabled = false;
        btn.style.pointerEvents = '';
      }
      if (typeof window.downloadProductTDS === 'function' && window.downloadProductTDS !== window._stubDownloadProductTDS) {
        window.downloadProductTDS(productId);
      }
    };
    script.onerror = function () {
      if (btn) {
        btn.innerHTML = origHtml;
        btn.disabled = false;
        btn.style.pointerEvents = '';
      }
      if (typeof window.showToast === 'function') {
        window.showToast('Could not load TDS generator. Please try again.');
      }
    };
    document.head.appendChild(script);
  };
  window._stubDownloadProductTDS = window.downloadProductTDS;


  // ── Multi-Sample Request Flow (Phase 13 Feature B2) ──────────────────────────
  const SAMPLE_STORAGE_KEY = 'nagdev_sample_cart';

  function getSampleCart() {
    try {
      const data = localStorage.getItem(SAMPLE_STORAGE_KEY);
      return data ? JSON.parse(data) : [];
    } catch (e) {
      return [];
    }
  }

  function saveSampleCart(items) {
    try {
      localStorage.setItem(SAMPLE_STORAGE_KEY, JSON.stringify(items));
    } catch (e) {}
  }

  function addSampleItem(slug, name) {
    const cart = getSampleCart();
    if (cart.some(item => item.slug === slug)) {
      return { success: true, count: cart.length };
    }
    if (cart.length >= 5) {
      if (typeof window.showToast === 'function') {
        window.showToast('Maximum 5 sample grades per request. Remove a grade to add another.');
      } else {
        alert('Maximum 5 sample grades per request. Remove a grade to add another.');
      }
      return { success: false, count: cart.length, limitReached: true };
    }
    cart.push({ slug: slug, name: name || slug });
    saveSampleCart(cart);
    updateSampleUI();
    if (typeof window.showToast === 'function') {
      window.showToast(`Added ${name} to sample request (${cart.length}/5)`);
    }
    return { success: true, count: cart.length };
  }

  function removeSampleItem(slug) {
    let cart = getSampleCart();
    const removedItem = cart.find(item => item.slug === slug);
    cart = cart.filter(item => item.slug !== slug);
    saveSampleCart(cart);
    updateSampleUI();
    if (removedItem && typeof window.showToast === 'function') {
      window.showToast(`Removed ${removedItem.name} from sample request`);
    }
    return cart.length;
  }

  function clearSampleCart() {
    try {
      localStorage.removeItem(SAMPLE_STORAGE_KEY);
    } catch (e) {}
    updateSampleUI();
  }

  window.clearSampleCart = clearSampleCart;
  window.getSampleCart = getSampleCart;
  window.addSampleItem = addSampleItem;
  window.removeSampleItem = removeSampleItem;

  function updateSampleUI() {
    const cart = getSampleCart();
    const count = cart.length;
    const inCartSlugs = new Set(cart.map(i => i.slug));

    // 1. Update toggle buttons sitewide
    document.querySelectorAll('.btn-sample-toggle').forEach(btn => {
      const slug = btn.getAttribute('data-slug');
      if (!slug) return;
      const isSelected = inCartSlugs.has(slug);
      btn.setAttribute('aria-pressed', isSelected ? 'true' : 'false');
      if (isSelected) {
        btn.classList.add('in-cart');
        if (btn.classList.contains('btn-sample-toggle-sm')) {
          btn.innerHTML = '✓ Added';
        } else {
          btn.innerHTML = '✓ Added to request (Remove)';
        }
      } else {
        btn.classList.remove('in-cart');
        if (btn.classList.contains('btn-sample-toggle-sm')) {
          btn.innerHTML = '+ Sample';
        } else {
          btn.innerHTML = '+ Add to sample request';
        }
      }
    });

    // 2. Update or create floating sticky drawer
    let drawer = document.getElementById('sample-request-drawer');
    if (count > 0) {
      if (!drawer) {
        drawer = document.createElement('aside');
        drawer.id = 'sample-request-drawer';
        drawer.className = 'sample-request-drawer';
        drawer.setAttribute('aria-label', 'Sample request summary');
        document.body.appendChild(drawer);
      }
      const slugList = cart.map(i => encodeURIComponent(i.slug)).join(',');
      const contactUrl = `/contact?type=sample&products=${slugList}`;
      drawer.style.display = 'flex';
      drawer.innerHTML = `
        <div class="sample-drawer-body">
          <span class="sample-drawer-icon" aria-hidden="true">🧪</span>
          <span class="sample-drawer-label">Sample request (<strong>${count}</strong>/5)</span>
          <a href="${contactUrl}" class="sample-drawer-action" aria-label="Review and submit sample request for ${count} products">Request &rarr;</a>
          <button type="button" class="sample-drawer-close" aria-label="Clear all samples from request" title="Clear sample request">&times;</button>
        </div>
      `;
      const closeBtn = drawer.querySelector('.sample-drawer-close');
      if (closeBtn) {
        closeBtn.addEventListener('click', function(e) {
          e.preventDefault();
          e.stopPropagation();
          clearSampleCart();
        });
      }
    } else if (drawer) {
      drawer.style.display = 'none';
    }

    // 3. Update chips on /contact if present
    renderContactChips();
  }

  function renderContactChips() {
    const wrap = document.getElementById('sample-chips-wrap');
    if (!wrap) return;
    const list = document.getElementById('sample-chips-list');
    const hidden = document.getElementById('sample-products-hidden');
    const select = document.getElementById('contact-product');
    const enquiryTypeSelect = document.getElementById('contact-enquiry-type');

    const cart = getSampleCart();
    if (cart.length === 0) {
      wrap.style.display = 'none';
      if (hidden) hidden.value = '';
      if (select) {
        const customOpt = select.querySelector('option[data-multi-sample="true"]');
        if (customOpt) customOpt.remove();
      }
      return;
    }

    wrap.style.display = 'block';

    // Auto-select Sample Request option in enquiry type
    if (enquiryTypeSelect && !enquiryTypeSelect.value.includes('Sample')) {
      for (let i = 0; i < enquiryTypeSelect.options.length; i++) {
        if (enquiryTypeSelect.options[i].value.includes('Sample')) {
          enquiryTypeSelect.selectedIndex = i;
          break;
        }
      }
    }

    const slugStr = cart.map(i => i.slug).join(',');
    const nameStr = cart.map(i => i.name).join(', ');
    if (hidden) hidden.value = slugStr;

    // Update select element with multi-sample option
    if (select) {
      let customOpt = select.querySelector('option[data-multi-sample="true"]');
      if (!customOpt) {
        customOpt = document.createElement('option');
        customOpt.setAttribute('data-multi-sample', 'true');
        select.prepend(customOpt);
      }
      customOpt.value = `Multi-Sample (${cart.length} grades): ${slugStr}`;
      customOpt.textContent = `🧪 Multi-Sample (${cart.length} grades): ${nameStr}`;
      select.value = customOpt.value;
    }

    if (list) {
      list.innerHTML = cart.map(item => `
        <div class="sample-chip" role="listitem" data-slug="${escapeHtml(item.slug)}">
          <span>${escapeHtml(item.name)}</span>
          <button type="button" class="btn-remove-chip" aria-label="Remove ${escapeHtml(item.name)} from sample request" data-slug="${escapeHtml(item.slug)}">&times;</button>
        </div>
      `).join('');

      list.querySelectorAll('.btn-remove-chip').forEach(btn => {
        btn.addEventListener('click', function(e) {
          e.preventDefault();
          e.stopPropagation();
          const slug = this.getAttribute('data-slug');
          removeSampleItem(slug);
        });
      });
    }
  }

  // Handle URL parameters on /contact (e.g. ?type=sample&products=fsg,commercial)
  function initContactUrlParams() {
    if (!window.location.pathname.includes('/contact')) return;
    try {
      const url = new URL(window.location.href);
      const params = url.searchParams;
      const typeParam = params.get('type') || params.get('inquiry') || '';
      const prodParam = params.get('products') || params.get('product') || '';

      if (prodParam && (typeParam === 'sample' || params.get('type') === 'sample')) {
        const slugs = prodParam.split(',').map(s => s.trim()).filter(Boolean);
        slugs.forEach(slug => {
          const formattedName = slug.split('-').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
          addSampleItem(slug, formattedName);
        });
      }
    } catch (e) {}
  }

  // Delegate click event for sample toggle buttons
  document.addEventListener('click', function(e) {
    const btn = e.target.closest('.btn-sample-toggle');
    if (!btn) return;
    e.preventDefault();
    e.stopPropagation();
    const slug = btn.getAttribute('data-slug');
    const name = btn.getAttribute('data-name') || slug;
    const cart = getSampleCart();
    if (cart.some(item => item.slug === slug)) {
      removeSampleItem(slug);
    } else {
      addSampleItem(slug, name);
    }
  });

  // Initialize sample UI on page load
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
      initContactUrlParams();
      updateSampleUI();
    });
  } else {
    initContactUrlParams();
    updateSampleUI();
  }

})();
