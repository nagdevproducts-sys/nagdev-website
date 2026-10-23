/**
 * Nagdev Products Private Limited — Analytics & Consent Mode v2
 * Measurement ID: G-HL3JQ3ZQKF
 * Performance-safe GA4 installation with host verification
 */
(function () {
  'use strict';

  const GA_MEASUREMENT_ID = 'G-HL3JQ3ZQKF';

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

  function gtagCall() {
    if (typeof window.gtag === 'function') {
      window.gtag.apply(null, arguments);
    } else {
      window.dataLayer = window.dataLayer || [];
      window.dataLayer.push(arguments);
    }
  }

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
})();
