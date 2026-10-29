import json
import re
from pathlib import Path
import pytest
from bs4 import BeautifulSoup
import pymupdf as fitz

REPO_ROOT = Path(__file__).resolve().parent.parent
MASTER_PATH = REPO_ROOT / "seo" / "product-master.json"
CATALOG_PATH = REPO_ROOT / "downloads" / "catalog.pdf"
TDS_DIR = REPO_ROOT / "downloads" / "tds"
PRODUCTS_DIR = REPO_ROOT / "products"

EXPECTED_CANONICAL_HS = {
    # 15 Active Products (7 regular_supply + 8 on_enquiry)
    'commercial-castor-oil': '1515.30',
    'first-special-grade-castor-oil': '1515.30',
    'fpd-castor-oil': '1515.30',
    'castor-cake': '2306.90',
    'hydrogenated-castor-oil': '1516.20',
    'dehydrated-castor-oil': '1518.00',
    'dco-fatty-acid': '3823.19',
    'ppg-castor-oil': '1515.30',
    'cold-pressed-castor-oil': '1515.30',
    'castor-oil-bp93': '1515.30',
    'castor-oil-usp-nf': '1515.30',
    'castor-oil-ph-eur': '1515.30',
    'castor-oil-ip': '1515.30',
    'castor-oil-jp': '1515.30',
    'cosmetic-grade-castor-oil': '1515.30',

    # 17 Planned / Under Development Products
    'ricinoleic-acid': '2918.19',
    '12-hydroxystearic-acid': '2918.19',
    'sebacic-acid': '2917.13',
    'high-protein-castor-meal': '2306.90',
    'crude-glycerin': '1520.00',
    'refined-glycerin': '2905.45',
    'bio-polyurethane-polyols': '3907.29',
    'sodium-sulphate-anhydrous': '2833.11',
    'dioctyl-sebacate': '2917.13',
    'dibutyl-sebacate': '2917.13',
    'methyl-12-hydroxystearate': '2918.19',
    'methyl-ricinoleate': '2918.19',
    'lithium-12-hydroxystearate': '2918.19',
    'calcium-12-hydroxystearate': '2918.19',
    'zinc-undecylenate': '2918.19',
    'zinc-ricinoleate': '2918.19',
    'blown-oxidized-castor-oil': '1518.00',
}

@pytest.fixture(scope="module")
def master_data():
    with open(MASTER_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

@pytest.fixture(scope="module")
def catalog_text():
    assert CATALOG_PATH.exists(), f"Catalog PDF missing at {CATALOG_PATH}"
    doc = fitz.open(CATALOG_PATH)
    return "\n".join([page.get_text() for page in doc])

def test_product_master_has_all_32_canonical_hs_codes(master_data):
    """Verify all 32 products in product-master.json have the exact canonical HS code."""
    assert len(master_data) == 32
    for p in master_data:
        slug = p["slug"]
        expected_hs = EXPECTED_CANONICAL_HS.get(slug)
        assert expected_hs is not None, f"Unknown slug {slug} in master"
        assert p.get("hs_code") == expected_hs, f"Master HS mismatch for {slug}: expected {expected_hs}, got {p.get('hs_code')}"

def test_active_15_products_hs_code_consistency(master_data, catalog_text):
    """Verify that all 15 active products match across Master, Page Chip, JSON-LD, TDS, and Catalog."""
    active_products = [p for p in master_data if p.get("status") != "under_development"]
    assert len(active_products) == 15

    for p in active_products:
        slug = p["slug"]
        expected_hs = EXPECTED_CANONICAL_HS[slug]
        
        # 1. Page Chip & JSON-LD
        html_path = PRODUCTS_DIR / f"{slug}.html"
        assert html_path.exists(), f"Missing HTML page for {slug}"
        html_text = html_path.read_text(encoding="utf-8")

        m_chip = re.search(r'HS\s*(?:Code|Tariff)?\s*[:\-]?\s*([0-9]{4}\.[0-9]{2})', html_text, re.IGNORECASE)
        assert m_chip is not None, f"Missing HS chip in {slug}.html"
        assert m_chip.group(1) == expected_hs, f"HS chip mismatch in {slug}.html: {m_chip.group(1)} != {expected_hs}"

        m_mpn = re.search(r'"mpn"\s*:\s*"([^"]+)"', html_text)
        assert m_mpn is not None, f"Missing JSON-LD mpn in {slug}.html"
        assert m_mpn.group(1) == expected_hs, f"JSON-LD mpn mismatch in {slug}.html: {m_mpn.group(1)} != {expected_hs}"

        m_ident = re.search(r'"propertyID"\s*:\s*"HS Code"\s*,\s*"value"\s*:\s*"([^"]+)"', html_text)
        assert m_ident is not None, f"Missing JSON-LD HS Code identifier in {slug}.html"
        assert m_ident.group(1) == expected_hs, f"JSON-LD HS Code identifier mismatch in {slug}.html: {m_ident.group(1)} != {expected_hs}"

        # 2. TDS PDF
        tds_path = TDS_DIR / f"{slug}.pdf"
        assert tds_path.exists(), f"Missing TDS PDF for {slug}"
        tds_doc = fitz.open(tds_path)
        tds_text = "\n".join([page.get_text() for page in tds_doc])
        m_tds = re.search(r'HS\s*(?:Tariff\s*Code|Code)?\s*[:\-]?\s*([0-9]{4}\.[0-9]{2})', tds_text, re.IGNORECASE)
        assert m_tds is not None, f"Missing HS code in TDS PDF for {slug}"
        assert m_tds.group(1) == expected_hs, f"TDS HS mismatch in {slug}.pdf: {m_tds.group(1)} != {expected_hs}"

        # 3. Catalog PDF
        assert p["display_name"] in catalog_text or p.get("brand_code", "").replace("™", "").strip() in catalog_text
        assert expected_hs in catalog_text

def test_planned_17_products_hs_code_consistency(master_data, catalog_text):
    """Verify that all 17 planned / under-development products have consistent HS codes."""
    planned_products = [p for p in master_data if p.get("status") == "under_development"]
    assert len(planned_products) == 17

    for p in planned_products:
        slug = p["slug"]
        expected_hs = EXPECTED_CANONICAL_HS[slug]

        html_path = PRODUCTS_DIR / f"{slug}.html"
        assert html_path.exists(), f"Missing HTML page for {slug}"
        html_text = html_path.read_text(encoding="utf-8")

        m_chip = re.search(r'HS\s*(?:Code|Tariff)?\s*[:\-]?\s*([0-9]{4}\.[0-9]{2})', html_text, re.IGNORECASE)
        assert m_chip is not None and m_chip.group(1) == expected_hs

        m_mpn = re.search(r'"mpn"\s*:\s*"([^"]+)"', html_text)
        assert m_mpn is not None and m_mpn.group(1) == expected_hs

        tds_path = TDS_DIR / f"{slug}.pdf"
        assert tds_path.exists(), f"Missing TDS PDF for {slug}"
        tds_doc = fitz.open(tds_path)
        tds_text = "\n".join([page.get_text() for page in tds_doc])
        m_tds = re.search(r'HS\s*(?:Tariff\s*Code|Code)?\s*[:\-]?\s*([0-9]{4}\.[0-9]{2})', tds_text, re.IGNORECASE)
        assert m_tds is not None and m_tds.group(1) == expected_hs

def test_rule_r22_lovibond_gardner_consistency(master_data):
    """Rule R22: Ensure no page whose spec table uses Lovibond mentions Gardner in FAQs/text, and vice versa."""
    for p in master_data:
        slug = p["slug"]
        html_path = PRODUCTS_DIR / f"{slug}.html"
        content = html_path.read_text(encoding="utf-8", errors="ignore")
        soup = BeautifulSoup(content, "html.parser")

        table = soup.find("table")
        table_colour_spec = ""
        if table:
            for row in table.find_all("tr"):
                row_str = row.get_text()
                if any(k in row_str.lower() for k in ["colour", "color", "lovibond", "gardner", "tintometer"]):
                    table_colour_spec += row_str.strip() + " | "

        table_has_lovibond = bool(re.search(r'lovibond', table_colour_spec, re.IGNORECASE))
        table_has_gardner = bool(re.search(r'gardner', table_colour_spec, re.IGNORECASE))

        for tag in soup.find_all(["table", "script", "style"]):
            tag.decompose()
        body_text = soup.get_text()

        body_has_lovibond = bool(re.search(r'\blovibond\b', body_text, re.IGNORECASE))
        body_has_gardner = bool(re.search(r'\bgardner\b', body_text, re.IGNORECASE))

        if table_has_lovibond:
            assert not body_has_gardner, f"Rule R22 violation in {slug}: Spec table uses Lovibond, but body/FAQs mention Gardner"
        if table_has_gardner:
            assert not body_has_lovibond, f"Rule R22 violation in {slug}: Spec table uses Gardner, but body/FAQs mention Lovibond"
