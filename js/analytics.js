/**
 * Nagdev Products Private Limited — Analytics & Consent Mode v2
 * Measurement ID: G-HL3JQ3ZQKF
 * Privacy-safe implementation:
 * - Data sent only on www.nagdevproducts.com (or on preview/localhost with ?ga_debug=1)
 * - Consent Mode v2: ad storage/personalization permanently denied; analytics granted outside EEA/UK/CH
 */
(function () {
  'use strict';

  const GA_MEASUREMENT_ID = 'G-HL3JQ3ZQKF';
  const STORAGE_KEY = 'nagdev_consent';
  const EXPIRY_DAYS = 365;

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

    if (!isProduction() && isDebug()) {
      configOptions.debug_mode = true;
    }

    gtagCall('config', GA_MEASUREMENT_ID, configOptions);
  }

  document.addEventListener('click', function (e) {
    const button = e.target.closest('button');
    const anchor = e.target.closest('a');
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
  });

  window.nagdevShowConsent = showConsentBanner;
})();
