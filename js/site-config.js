/**
 * Nagdev Products Private Limited — Single Source of Truth Configuration (NAP & Company Facts)
 * Used across header top bar, footer, contact page, schemas, and dynamic components.
 */

const SITE_CONFIG = {
  company: {
    legalName: "Nagdev Products Private Limited",
    brandName: "Nagdev Products",
    website: "https://www.nagdevproducts.com",
    tagline: "Integrated castor oil and derivatives manufacturer from Gujarat's castor belt.",
    positioning: "Integrated Castor Oil & Derivatives Plant · North Gujarat",
    heroBadge: "Manufacturer & Exporter · Commissioning 2027 · Now Booking Supply Contracts",
    qualityStatement: "Quality systems aligned to ISO 9001 · REACH-ready export documentation",
    inspectionPolicy: "Every consignment ships with a Certificate of Analysis; third-party inspection (SGS / Bureau Veritas) on request.",
    laboratory: "our in-house QC laboratory",
    ctaPrimary: "Book 2027 supply contracts — request samples & pricing",
    crushingCapacity: "50 MT/day",
    commissioningYear: "2027",
    status: "Commissioning 2027 · Now Booking Supply Contracts"
  },
  contact: {
    phone: "+91 63520 98306",
    phoneTel: "+916352098306",
    whatsapp: "+91 63520 98306",
    whatsappLink: "https://wa.me/916352098306?text=Hello%20Nagdev%20Products%2C%20I%20would%20like%20to%20enquire%20about%202027%20supply%20contracts%20and%20product%20specifications.",
    email: "nagdevproducts@gmail.com",
    address: {
      street: "Survey No. 301 P-2, Jada-Kotarwada Road, Village – Sardarpura, Post – Ravel",
      taluka: "Taluka – Deodar",
      district: "District – Vav-Tharad",
      state: "Gujarat",
      postalCode: "385330",
      country: "India",
      countryCode: "IN",
      fullText: "Survey No. 301 P-2, Jada-Kotarwada Road, Village – Sardarpura, Post – Ravel, Taluka – Deodar, District – Vav-Tharad, Gujarat – 385330, India",
      marketingRegion: "Banaskantha–Vav-Tharad castor belt, North Gujarat"
    },
    googleMapsUrl: "https://maps.app.goo.gl/4eETjMFpRmRxWcf6A",
    coordinates: {
      latitude: "24.183805",
      longitude: "71.736510"
    }
  },
  catalog: {
    totalProducts: 27,
    coreCount: 14,
    specialtyCount: 13,
    coreLabel: "Core Products",
    specialtyLabel: "Specialty Range — Available on Enquiry"
  }
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = SITE_CONFIG;
}
if (typeof window !== 'undefined') {
  window.SITE_CONFIG = SITE_CONFIG;
}
