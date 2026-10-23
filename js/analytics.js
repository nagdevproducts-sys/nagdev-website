/**
 * Nagdev Products Private Limited — Analytics & Consent Mode v2
 * Measurement ID: G-HL3JQ3ZQKF
 * Privacy-safe implementation:
 * - Data sent only on www.nagdevproducts.com (or on preview/localhost with ?ga_debug=1)
 * - Consent Mode v2: ad storage/personalization permanently denied; analytics granted outside EEA/UK/CH
 * - Conversion event delegation without PII
 */
(function () {
  'use strict';

  const GA_MEASUREMENT_ID = 'G-HL3JQ3ZQKF';
  const STORAGE_KEY = 'nagdev_consent';
  const EXPIRY_DAYS = 365;
  const FIRED_STORAGE_KEY = 'nagdev_leads_fired';
  const MAX_FIRED_REFS = 50;

  // Lead Reference De-duplication Helpers
  function getFiredRefs() {
    const refs = [];
    try {
      const s = sessionStorage.getItem(FIRED_STORAGE_KEY);
      if (s) {
        const parsed = JSON.parse(s);
        if (Array.isArray(parsed)) {
          for (let i = 0; i < parsed.length; i++) {
            if (refs.indexOf(parsed[i]) === -1) refs.push(parsed[i]);
          }
        }
      }
    } catch (e) {}
    try {
      const l = localStorage.getItem(FIRED_STORAGE_KEY);
      if (l) {
        const parsed = JSON.parse(l);
        if (Array.isArray(parsed)) {
          for (let i = 0; i < parsed.length; i++) {
            if (refs.indexOf(parsed[i]) === -1) refs.push(parsed[i]);
          }
        }
      }
    } catch (e) {}
    return refs;
  }

  function markRefFired(ref) {
    if (!ref) return;
    try {
      let sRefs = [];
      try {
        const raw = sessionStorage.getItem(FIRED_STORAGE_KEY);
        if (raw) sRefs = JSON.parse(raw) || [];
      } catch (e) {}
      if (!Array.isArray(sRefs)) sRefs = [];
      if (sRefs.indexOf(ref) === -1) {
        sRefs.push(ref);
        if (sRefs.length > MAX_FIRED_REFS) sRefs = sRefs.slice(-MAX_FIRED_REFS);
        sessionStorage.setItem(FIRED_STORAGE_KEY, JSON.stringify(sRefs));
      }
    } catch (e) {}

    try {
      let lRefs = [];
      try {
        const raw = localStorage.getItem(FIRED_STORAGE_KEY);
        if (raw) lRefs = JSON.parse(raw) || [];
      } catch (e) {}
      if (!Array.isArray(lRefs)) lRefs = [];
      if (lRefs.indexOf(ref) === -1) {
        lRefs.push(ref);
        if (lRefs.length > MAX_FIRED_REFS) lRefs = lRefs.slice(-MAX_FIRED_REFS);
        localStorage.setItem(FIRED_STORAGE_KEY, JSON.stringify(lRefs));
      }
    } catch (e) {}
  }

  function isRefFired(ref) {
    if (!ref) return false;
    const fired = getFiredRefs();
    return fired.indexOf(ref) !== -1;
  }

  function isValidRef(ref) {
    return typeof ref === 'string' && /^NP-\d{8}-[A-Za-z0-9]+$/i.test(ref.trim());
  }

  // 1. Host & Debug Verification
  function isProduction() {
    return window.location.hostname === 'www.nagdevproducts.com';
  }

  function isDebug() {
    try {
      const params = new URLSearchParams(window.location.search);
      return params.get('ga_debug') === '1';
    } catch (e) {
      return false;
    }
  }

  function shouldTrack() {
    return isProduction() || isDebug();
  }

  // Helper for gtag calls
  function gtagCall() {
    if (typeof window.gtag === 'function') {
      window.gtag.apply(null, arguments);
    } else {
      window.dataLayer = window.dataLayer || [];
      window.dataLayer.push(arguments);
    }
  }

  // 2. Stored Consent Management
  function getStoredConsent() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return null;
      const data = JSON.parse(raw);
      if (data && data.timestamp && (Date.now() - data.timestamp < EXPIRY_DAYS * 86400000)) {
        return data.choice; // 'granted' | 'denied'
      }
      localStorage.removeItem(STORAGE_KEY);
    } catch (e) {}
    return null;
  }

  function saveStoredConsent(choice) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({
        choice: choice,
        timestamp: Date.now()
      }));
    } catch (e) {}
  }

  function isEEATimezone() {
    try {
      const tz = Intl.DateTimeFormat().resolvedOptions().timeZone || '';
      return tz.startsWith('Europe/') || tz === 'Atlantic/Reykjavik';
    } catch (e) {
      return false;
    }
  }

  // 3. Consent Banner Creation & Control
  function createBannerStyles() {
    if (document.getElementById('nagdev-consent-styles')) return;
    const style = document.createElement('style');
    style.id = 'nagdev-consent-styles';
    style.textContent = `
      .nagdev-consent-banner {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        z-index: 99999;
        background: #0B3D1E;
        color: #FFFFFF;
        border-top: 1.5px solid #C5A059;
        padding: 1rem 1.5rem;
        box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.25);
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        font-size: 0.875rem;
        line-height: 1.5;
        animation: slideUpConsent 0.3s ease-out;
      }
      @keyframes slideUpConsent {
        from { transform: translateY(100%); }
        to { transform: translateY(0); }
      }
      .nagdev-consent-inner {
        max-width: 1200px;
        margin: 0 auto;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1.5rem;
        flex-wrap: wrap;
      }
      .nagdev-consent-text {
        flex: 1 1 500px;
        margin: 0;
        color: #F1F5F9;
      }
      .nagdev-consent-link {
        color: #E2B96E;
        text-decoration: underline;
        font-weight: 600;
        margin-left: 0.35rem;
      }
      .nagdev-consent-link:hover {
        color: #FFFFFF;
      }
      .nagdev-consent-actions {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        flex-shrink: 0;
      }
      .nagdev-consent-btn {
        padding: 0.55rem 1.25rem;
        font-size: 0.84rem;
        font-weight: 700;
        border-radius: 6px;
        cursor: pointer;
        border: none;
        transition: all 0.2s ease;
      }
      .nagdev-consent-btn-accept {
        background: #C5A059;
        color: #0B3D1E;
      }
      .nagdev-consent-btn-accept:hover, .nagdev-consent-btn-accept:focus {
        background: #D4AF37;
        outline: 2px solid #FFFFFF;
      }
      .nagdev-consent-btn-reject {
        background: #FFFFFF;
        color: #0B3D1E;
      }
      .nagdev-consent-btn-reject:hover, .nagdev-consent-btn-reject:focus {
        background: #F1F5F9;
        outline: 2px solid #C5A059;
      }
      @media (max-width: 768px) {
        .nagdev-consent-banner { padding: 0.85rem 1rem; }
        .nagdev-consent-inner { gap: 0.75rem; }
        .nagdev-consent-actions { width: 100%; justify-content: flex-end; }
      }
    `;
    document.head.appendChild(style);
  }

  function showConsentBanner() {
    createBannerStyles();
    let banner = document.getElementById('nagdev-consent-banner');
    if (!banner) {
      banner = document.createElement('div');
      banner.id = 'nagdev-consent-banner';
      banner.className = 'nagdev-consent-banner';
      banner.setAttribute('role', 'region');
      banner.setAttribute('aria-label', 'Cookie consent banner');
      banner.innerHTML = `
        <div class="nagdev-consent-inner">
          <p class="nagdev-consent-text">
            We use analytics cookies to understand how buyers use this site. No advertising cookies.
            <a href="/privacy" class="nagdev-consent-link">Privacy policy</a>
          </p>
          <div class="nagdev-consent-actions">
            <button type="button" id="nagdev-consent-reject" class="nagdev-consent-btn nagdev-consent-btn-reject">Reject</button>
            <button type="button" id="nagdev-consent-accept" class="nagdev-consent-btn nagdev-consent-btn-accept">Accept analytics</button>
          </div>
        </div>
      `;
      document.body.appendChild(banner);

      document.getElementById('nagdev-consent-accept').addEventListener('click', function () {
        saveStoredConsent('granted');
        gtagCall('consent', 'update', { analytics_storage: 'granted' });
        banner.style.display = 'none';
      });

      document.getElementById('nagdev-consent-reject').addEventListener('click', function () {
        saveStoredConsent('denied');
        gtagCall('consent', 'update', { analytics_storage: 'denied' });
        banner.style.display = 'none';
      });
    } else {
      banner.style.display = 'block';
    }

    const acceptBtn = document.getElementById('nagdev-consent-accept');
    if (acceptBtn) acceptBtn.focus();
  }

  function initConsent() {
    const stored = getStoredConsent();
    if (stored) {
      gtagCall('consent', 'update', { analytics_storage: stored });
      return;
    }
    // Show banner and default to denied if visitor is in EEA/UK/CH timezone
    if (isEEATimezone()) {
      gtagCall('consent', 'update', { analytics_storage: 'denied' });
      if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', showConsentBanner);
      } else {
        showConsentBanner();
      }
    }
  }

  // 4. Initialize Consent & GA4 Config
  initConsent();

  if (shouldTrack()) {
    gtagCall('js', new Date());
    const configOptions = {
      send_page_view: true,
      allow_google_signals: false,
      allow_ad_personalization_signals: false
    };

    // CRITICAL REQUIREMENT: Production must never send debug_mode.
    // Make sure debug_mode is set ONLY on non-production hosts with ?ga_debug=1.
    if (!isProduction() && isDebug()) {
      configOptions.debug_mode = true;
    } else {
      delete configOptions.debug_mode;
    }

    gtagCall('config', GA_MEASUREMENT_ID, configOptions);
  }

  // 5. Product Slug Normalization Map
  const PRODUCT_SLUG_MAP = {
    '12-hydroxystearic-acid': '12-hydroxystearic-acid',
    'bio-polyurethane-polyols': 'bio-polyurethane-polyols',
    'blown-oxidized-castor-oil': 'blown-oxidized-castor-oil',
    'calcium-12-hydroxystearate': 'calcium-12-hydroxystearate',
    'castor-cake': 'castor-cake',
    'castor-cake-fertilizer': 'castor-cake',
    'castor-oil-bp93': 'castor-oil-bp93',
    'cold-pressed-castor-oil': 'cold-pressed-castor-oil',
    'commercial-castor-oil': 'commercial-castor-oil',
    'crude-glycerin': 'crude-glycerin',
    'dco-fatty-acid': 'dco-fatty-acid',
    'de-oiled-cake-castor-meal': 'castor-cake',
    'dehydrated-castor-oil': 'dehydrated-castor-oil',
    'dibutyl-sebacate': 'dibutyl-sebacate',
    'dioctyl-sebacate': 'dioctyl-sebacate',
    'first-special-grade-castor-oil': 'first-special-grade-castor-oil',
    'first-special-grade-fsg-castor-oil': 'first-special-grade-castor-oil',
    'fpd-castor-oil': 'fpd-castor-oil',
    'high-protein-castor-meal': 'high-protein-castor-meal',
    'hydrogenated-castor-oil': 'hydrogenated-castor-oil',
    'lithium-12-hydroxystearate': 'lithium-12-hydroxystearate',
    'methyl-12-hydroxystearate': 'methyl-12-hydroxystearate',
    'methyl-ricinoleate': 'methyl-ricinoleate',
    'ppg-castor-oil': 'ppg-castor-oil',
    'refined-glycerin': 'refined-glycerin',
    'ricinoleic-acid': 'ricinoleic-acid',
    'sebacic-acid': 'sebacic-acid',
    'sodium-sulphate-anhydrous': 'sodium-sulphate-anhydrous',
    'zinc-ricinoleate': 'zinc-ricinoleate',
    'zinc-undecylenate': 'zinc-undecylenate',
    'ndevoleo comm — commercial castor oil': 'commercial-castor-oil',
    'ndevoleo comm - commercial castor oil': 'commercial-castor-oil',
    'commercial castor oil': 'commercial-castor-oil',
    'ndevoleo fsg — first special grade (fsg) castor oil': 'first-special-grade-castor-oil',
    'ndevoleo fsg - first special grade (fsg) castor oil': 'first-special-grade-castor-oil',
    'first special grade (fsg) castor oil': 'first-special-grade-castor-oil',
    'first special grade castor oil': 'first-special-grade-castor-oil',
    'fsg castor oil': 'first-special-grade-castor-oil',
    'ndevwax hco — hydrogenated castor oil (castor wax)': 'hydrogenated-castor-oil',
    'ndevwax hco - hydrogenated castor oil (castor wax)': 'hydrogenated-castor-oil',
    'hydrogenated castor oil (castor wax)': 'hydrogenated-castor-oil',
    'hydrogenated castor oil': 'hydrogenated-castor-oil',
    'castor wax': 'hydrogenated-castor-oil',
    'ndevacid 12-hsa — 12-hydroxystearic acid': '12-hydroxystearic-acid',
    'ndevacid 12-hsa - 12-hydroxystearic acid': '12-hydroxystearic-acid',
    '12-hydroxystearic acid': '12-hydroxystearic-acid',
    'ndevacid ric — ricinoleic acid': 'ricinoleic-acid',
    'ndevacid ric - ricinoleic acid': 'ricinoleic-acid',
    'ricinoleic acid': 'ricinoleic-acid',
    'ndevgly 995 — refined glycerin (99.5%)': 'refined-glycerin',
    'ndevgly 995 - refined glycerin (99.5%)': 'refined-glycerin',
    'refined glycerin (99.5%)': 'refined-glycerin',
    'refined glycerin': 'refined-glycerin',
    'ndevest mr — methyl ricinoleate': 'methyl-ricinoleate',
    'ndevest mr - methyl ricinoleate': 'methyl-ricinoleate',
    'methyl ricinoleate': 'methyl-ricinoleate',
    'ndevest m12h — methyl 12-hydroxystearate': 'methyl-12-hydroxystearate',
    'ndevest m12h - methyl 12-hydroxystearate': 'methyl-12-hydroxystearate',
    'methyl 12-hydroxystearate': 'methyl-12-hydroxystearate',
    'ndevacid seb — sebacic acid': 'sebacic-acid',
    'ndevacid seb - sebacic acid': 'sebacic-acid',
    'sebacic acid': 'sebacic-acid',
    'ndevest dos — dioctyl sebacate': 'dioctyl-sebacate',
    'ndevest dos - dioctyl sebacate': 'dioctyl-sebacate',
    'dioctyl sebacate': 'dioctyl-sebacate',
    'ndevest dbs — dibutyl sebacate': 'dibutyl-sebacate',
    'ndevest dbs - dibutyl sebacate': 'dibutyl-sebacate',
    'dibutyl sebacate': 'dibutyl-sebacate',
    'ndevpol bio — bio-polyurethane polyols': 'bio-polyurethane-polyols',
    'ndevpol bio - bio-polyurethane polyols': 'bio-polyurethane-polyols',
    'bio-polyurethane polyols': 'bio-polyurethane-polyols',
    'ndevpol dco — dehydrated castor oil': 'dehydrated-castor-oil',
    'ndevpol dco - dehydrated castor oil': 'dehydrated-castor-oil',
    'dehydrated castor oil': 'dehydrated-castor-oil',
    'ndevox blo — blown / oxidized castor oil': 'blown-oxidized-castor-oil',
    'ndevox blo - blown / oxidized castor oil': 'blown-oxidized-castor-oil',
    'blown / oxidized castor oil': 'blown-oxidized-castor-oil',
    'blown oxidized castor oil': 'blown-oxidized-castor-oil',
    'ndevacid dco — dco fatty acid': 'dco-fatty-acid',
    'ndevacid dco - dco fatty acid': 'dco-fatty-acid',
    'dco fatty acid': 'dco-fatty-acid',
    'ndevsoap li12 — lithium 12-hydroxystearate': 'lithium-12-hydroxystearate',
    'ndevsoap li12 - lithium 12-hydroxystearate': 'lithium-12-hydroxystearate',
    'lithium 12-hydroxystearate': 'lithium-12-hydroxystearate',
    'ndevsoap ca12 — calcium 12-hydroxystearate': 'calcium-12-hydroxystearate',
    'ndevsoap ca12 - calcium 12-hydroxystearate': 'calcium-12-hydroxystearate',
    'calcium 12-hydroxystearate': 'calcium-12-hydroxystearate',
    'ndevsoap znr — zinc ricinoleate': 'zinc-ricinoleate',
    'ndevsoap znr - zinc ricinoleate': 'zinc-ricinoleate',
    'zinc ricinoleate': 'zinc-ricinoleate',
    'ndevsoap znu — zinc undecylenate': 'zinc-undecylenate',
    'ndevsoap znu - zinc undecylenate': 'zinc-undecylenate',
    'zinc undecylenate': 'zinc-undecylenate',
    'ndevagro cake — castor cake organic fertilizer': 'castor-cake',
    'ndevagro cake - castor cake organic fertilizer': 'castor-cake',
    'castor cake organic fertilizer': 'castor-cake',
    'castor cake': 'castor-cake',
    'ndevoleo cp — cold pressed castor oil': 'cold-pressed-castor-oil',
    'cold pressed castor oil': 'cold-pressed-castor-oil',
    'ndevoleo bp93 — castor oil bp 93 / pharma': 'castor-oil-bp93',
    'castor oil bp 93 / pharma': 'castor-oil-bp93',
    'ndevoleo ppg — pale pressed grade (ppg)': 'ppg-castor-oil',
    'pale pressed grade (ppg)': 'ppg-castor-oil',
    'ndevoleo fpd — fpd castor oil': 'fpd-castor-oil',
    'fpd castor oil': 'fpd-castor-oil',
    'ndevagro hpro — high protein castor meal': 'high-protein-castor-meal',
    'high protein castor meal': 'high-protein-castor-meal',
    'ndevgly crude — crude glycerin (80% min)': 'crude-glycerin',
    'crude glycerin (80% min)': 'crude-glycerin',
    'crude glycerin': 'crude-glycerin',
    'ndevchem na2so4 — sodium sulphate anhydrous': 'sodium-sulphate-anhydrous',
    'sodium sulphate anhydrous': 'sodium-sulphate-anhydrous'
  };

  function normalizeProductSlug(raw) {
    if (!raw || typeof raw !== 'string') return 'other';
    const cleaned = raw.toLowerCase().trim().replace(/[™®]/g, '');
    if (Object.prototype.hasOwnProperty.call(PRODUCT_SLUG_MAP, cleaned)) {
      return PRODUCT_SLUG_MAP[cleaned];
    }
    const slugStyle = cleaned.replace(/[—/()%,]/g, '-').replace(/\s+/g, '-').replace(/-+/g, '-').replace(/^-|-$/g, '');
    if (Object.prototype.hasOwnProperty.call(PRODUCT_SLUG_MAP, slugStyle)) {
      return PRODUCT_SLUG_MAP[slugStyle];
    }
    for (const key in PRODUCT_SLUG_MAP) {
      if (Object.prototype.hasOwnProperty.call(PRODUCT_SLUG_MAP, key)) {
        if (key.length > 5 && (cleaned.indexOf(key) !== -1 || key.indexOf(cleaned) !== -1)) {
          return PRODUCT_SLUG_MAP[key];
        }
      }
    }
    return 'other';
  }

  // 6. Conversion Tracking Helpers
  function getLinkLocation(element) {
    if (!element) return 'body';
    if (element.closest('#whatsapp-fab') || element.closest('.fab') || element.closest('.floating')) return 'floating';
    if (element.closest('header') || element.closest('.site-header') || element.closest('.top-bar')) return 'header';
    if (element.closest('footer') || element.closest('.site-footer')) return 'footer';
    return 'body';
  }

  function getProductSlug() {
    const path = window.location.pathname;
    const match = path.match(/\/products\/([a-z0-9-]+)/i);
    if (match && match[1]) {
      return normalizeProductSlug(match[1]);
    }

    try {
      const params = new URLSearchParams(window.location.search);
      const prod = params.get('product');
      if (prod) {
        return normalizeProductSlug(prod);
      }
    } catch (e) {}
    return 'other';
  }

  function trackEvent(eventName, params) {
    if (!shouldTrack()) return;
    const defaultParams = {
      page_path: window.location.pathname,
      product_slug: getProductSlug()
    };
    const finalParams = Object.assign(defaultParams, params);
    if (finalParams.product_slug) {
      finalParams.product_slug = normalizeProductSlug(finalParams.product_slug);
    } else {
      finalParams.product_slug = 'other';
    }
    gtagCall('event', eventName, finalParams);
  }

  // 6. Delegated Event Listeners
  document.addEventListener('click', function (e) {
    const anchor = e.target.closest('a');
    const button = e.target.closest('button');

    // Cookie Settings trigger
    if (button && (button.id === 'cookie-settings-btn' || button.classList.contains('cookie-settings-trigger'))) {
      e.preventDefault();
      showConsentBanner();
      return;
    }
    if (anchor && (anchor.id === 'cookie-settings-link' || anchor.classList.contains('cookie-settings-trigger') || (anchor.getAttribute('href') === '#cookie-settings'))) {
      e.preventDefault();
      showConsentBanner();
      return;
    }

    if (!anchor) return;
    const href = (anchor.getAttribute('href') || '').trim();
    if (!href) return;

    // WhatsApp Click
    if (href.includes('wa.me') || href.includes('api.whatsapp.com')) {
      trackEvent('whatsapp_click', {
        link_location: getLinkLocation(anchor)
      });
      return;
    }

    // Phone Click
    if (href.startsWith('tel:')) {
      trackEvent('phone_click', {
        link_location: getLinkLocation(anchor)
      });
      return;
    }

    // Email Click
    if (href.startsWith('mailto:')) {
      trackEvent('email_click', {
        link_location: getLinkLocation(anchor)
      });
      return;
    }

    // TDS Download (links to /downloads/tds/*.pdf or ending in .pdf with tds)
    if (href.includes('/downloads/tds/') && href.toLowerCase().endsWith('.pdf')) {
      const fileName = href.split('/').pop().split('?')[0];
      let prodSlug = getProductSlug();
      if (!prodSlug || prodSlug === 'other') {
        const rawPdfSlug = fileName.replace(/\.pdf$/i, '').replace(/^tds[-_]/i, '');
        prodSlug = normalizeProductSlug(rawPdfSlug);
      }
      trackEvent('tds_download', {
        file_name: fileName,
        product_slug: prodSlug,
        link_location: getLinkLocation(anchor)
      });
      return;
    }

    // Quote / Inquire CTA Click (links to /contact)
    const cleanHref = href.split('?')[0].split('#')[0];
    if (cleanHref === '/contact' || cleanHref === 'contact.html' || cleanHref.endsWith('/contact.html')) {
      const ctaText = (anchor.textContent || '').trim().replace(/\s+/g, ' ');
      trackEvent('quote_cta_click', {
        cta_text: ctaText,
        link_location: getLinkLocation(anchor)
      });
      return;
    }
  });

  // 7. Confirmed Lead & Sample Request Tracking
  let ajaxLeadFired = false;

  // Listen for the custom nagdev_lead_success event dispatched by site.js on verified AJAX submission
  window.addEventListener('nagdev_lead_success', function (e) {
    const detail = e.detail || {};
    const ref = detail.ref;
    if (ref) {
      if (!isValidRef(ref) || isRefFired(ref)) {
        return;
      }
      markRefFired(ref);
    } else {
      if (ajaxLeadFired) return;
      ajaxLeadFired = true;
    }

    const formType = detail.form_type || 'quote';
    const prodSlug = detail.product_slug ? normalizeProductSlug(detail.product_slug) : getProductSlug();
    const params = {
      form_type: formType,
      product_slug: prodSlug,
      link_location: 'body'
    };
    if (detail.country) {
      params.country = detail.country;
    }

    trackEvent('generate_lead', params);

    if (formType === 'sample') {
      trackEvent('sample_request', params);
    }
  });

  // Handle ?submitted=success on /contact with de-duplication and address bar cleanup
  function handleSubmittedSuccess() {
    if (!window.location.pathname.includes('/contact')) return;
    try {
      const url = new URL(window.location.href);
      const params = url.searchParams;
      if (params.get('submitted') === 'success') {
        const ref = (params.get('ref') || '').trim();
        const formType = (params.get('type') || 'quote').toLowerCase();
        const prodParam = params.get('product') || '';

        // Clean address bar: remove submitted and ref, keeping any other parameters
        params.delete('submitted');
        params.delete('ref');
        const newSearch = params.toString();
        const newUrl = url.pathname + (newSearch ? '?' + newSearch : '') + url.hash;
        window.history.replaceState(null, '', newUrl);

        // Require valid ref format NP-YYYYMMDD-XXXX
        if (isValidRef(ref)) {
          if (!isRefFired(ref)) {
            markRefFired(ref);
            const leadParams = {
              form_type: formType.includes('sample') ? 'sample' : (formType.includes('sds') ? 'sds' : 'quote'),
              product_slug: prodParam ? normalizeProductSlug(prodParam) : getProductSlug(),
              link_location: 'body'
            };
            trackEvent('generate_lead', leadParams);
            if (leadParams.form_type === 'sample') {
              trackEvent('sample_request', leadParams);
            }
          }
        }
      }
    } catch (e) {}
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', handleSubmittedSuccess);
  } else {
    handleSubmittedSuccess();
  }

  window.nagdevShowConsent = showConsentBanner;
})();
