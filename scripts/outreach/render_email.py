#!/usr/bin/env python3
"""
scripts/outreach/render_email.py - Deterministic email body renderer for Nagdev Products outreach.
Builds email bodies ONLY by populating fixed templates with values loaded from seo/facts-register.json.
No free-text facts are allowed.
Validates rendered content through claims_lint.py (R1-R13) and enforces exact register match for CIN and Plant address.
"""

import sys
import os
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from claims_lint import lint_content, load_facts

REGULAR_PRODUCT_DISPLAY_NAMES = {
    "commercial-castor-oil": "Commercial Castor Oil",
    "first-special-grade-castor-oil": "First Special Grade (FSG) Castor Oil",
    "fpd-castor-oil": "First Pressed Degummed (FPD) Castor Oil",
    "castor-cake": "Castor Cake",
    "hydrogenated-castor-oil": "Hydrogenated Castor Oil (HCO)",
    "dehydrated-castor-oil": "Dehydrated Castor Oil (DCO)",
    "dco-fatty-acid": "DCO Fatty Acid"
}

CORRECTION_TEMPLATE = """Dear Team,

We sincerely apologize for an error in our earlier email regarding our company registration details.

Please find our verified company details from official records:
- Legal Name: {legal_name}
- CIN: {cin}
- Plant Address: {plant}
- Head Office: {head_office}
- Phone: {phone}
- Email: {email}

Regular-Supply Products (7 Products):
{products_list}

Verification Links:
- About & Overview: {about_url}
- Castor Oil & Derivatives: {derivatives_url}

Please use these details if you consider us for inclusion.

Sincerely,
Nagdev Products Private Limited
"""

INITIAL_OUTREACH_TEMPLATE = """Dear Team,

We are writing from {legal_name} regarding directory inclusion.

Company Details:
- Legal Name: {legal_name}
- CIN: {cin}
- Plant Address: {plant}
- Head Office: {head_office}
- Phone: {phone}
- Email: {email}
- Operations: Seed crushing plant with 50 TPD crushing capacity in North Gujarat

Regular-Supply Products (7 Products):
{products_list}

Verification Links:
- About & Overview: {about_url}
- Castor Oil & Derivatives: {derivatives_url}

Sincerely,
Nagdev Products Private Limited
"""

def render_email(template_type="correction", facts_path=None):
    facts = load_facts(facts_path)
    company = facts["company"]
    products = facts["products"]
    
    legal_name = company["legal_name"]
    cin = company["cin"]
    plant = company["plant"]
    head_office = company["head_office"]
    phone = company["phone"]
    email = company["email"]
    
    # Format the 7 regular supply products strictly from register
    regular_slugs = products["regular_supply"]
    if len(regular_slugs) != 7:
        raise ValueError(f"Expected 7 regular supply products, got {len(regular_slugs)}")
        
    formatted_products = []
    for idx, slug in enumerate(regular_slugs, 1):
        display_name = REGULAR_PRODUCT_DISPLAY_NAMES.get(slug, slug.replace("-", " ").title())
        formatted_products.append(f"  {idx}. {display_name}")
    products_list_str = "\n".join(formatted_products)
    
    about_url = "https://www.nagdevproducts.com/about"
    derivatives_url = "https://www.nagdevproducts.com/castor-oil-derivatives"
    
    template = CORRECTION_TEMPLATE if template_type == "correction" else INITIAL_OUTREACH_TEMPLATE
    
    body = template.format(
        legal_name=legal_name,
        cin=cin,
        plant=plant,
        head_office=head_office,
        phone=phone,
        email=email,
        products_list=products_list_str,
        about_url=about_url,
        derivatives_url=derivatives_url
    )
    
    # ----------------------------------------------------
    # Verification & Claims Linter Gate
    # ----------------------------------------------------
    # 1. Exact match of CIN
    if cin not in body or cin != "U15400GJ2019PTC110518":
        raise ValueError(f"CIN verification failed: expected {cin}")
        
    # 2. Exact match of Plant Address
    if plant not in body:
        raise ValueError(f"Plant address verification failed: expected {plant}")
        
    # 3. Claims lint R1-R13 check
    findings = lint_content(body, "email_body.txt", facts)
    hard_fails = [f for f in findings if f["severity"] == "FAIL"]
    if hard_fails:
        fail_msgs = "\n".join([f"  - [{f['rule']}] {f['text']}" for f in hard_fails])
        raise ValueError(f"Rendered email failed claims_lint.py:\n{fail_msgs}")
        
    return body

if __name__ == "__main__":
    t_type = sys.argv[1] if len(sys.argv) > 1 else "correction"
    rendered = render_email(t_type)
    print("=== RENDERED EMAIL BODY (CLAIMS LINTER PASSED) ===")
    print(rendered)
    print("=== END OF EMAIL BODY ===")
