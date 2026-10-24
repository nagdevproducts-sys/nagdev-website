# Nagdev Technical SEO & Verification Architecture

## 1. Single Source of Truth: Facts Register
All factual claims, product classifications, production metrics, facility addresses, and commercial boundaries are codified in:
`seo/facts-register.json`

### Core Product Classifications:
1. **Regular Supply (7 Grades):**
   - Commercial Castor Oil (`commercial-castor-oil`)
   - First Special Grade Castor Oil (`first-special-grade-castor-oil`)
   - Castor Cake (Organic Manure) (`castor-cake`)
   - Hydrogenated Castor Oil / Castor Wax (`hydrogenated-castor-oil`)
   - Ricinoleic Acid (`ricinoleic-acid`)
   - 12-Hydroxystearic Acid (`12-hydroxystearic-acid`)
   - Refined Glycerin 99.5% (`refined-glycerin`)
2. **On Enquiry (7 Grades):**
   - Cold Pressed Castor Oil (`cold-pressed-castor-oil`)
   - Castor Oil BP 93 / Pharma (`castor-oil-bp93`)
   - Pale Pressed Grade Castor Oil (`ppg-castor-oil`)
   - First Pressed Degummed Castor Oil (`fpd-castor-oil`)
   - High Protein Castor Meal (`high-protein-castor-meal`)
   - Crude Glycerin 80% (`crude-glycerin`)
   - Sodium Sulphate Anhydrous (`sodium-sulphate-anhydrous`)
3. **Under Development / R&D (13 Grades):**
   - Sebacic Acid, Dehydrated Castor Oil (DCO), DCO Fatty Acid, Bio-PU Polyols, Dioctyl Sebacate (DOS), Dibutyl Sebacate (DBS), Methyl 12-Hydroxystearate, Methyl Ricinoleate, Lithium 12-Hydroxystearate, Calcium 12-Hydroxystearate, Zinc Undecylenate, Zinc Ricinoleate, Blown Oxidized Castor Oil.

### Operational Boundaries:
- **Crushing Capacity:** 50 TPD mechanical expeller crushing. Any annual capacity claim (e.g. 15,000 TPA or 30,000 TPA) is prohibited unless ratified in `facts-register.json`.
- **Plant Location:** Survey No. 301 P-2, Jada-Kotarwada Road, Village Sardarpura, Taluka Deodar, District Vav-Tharad, Gujarat 385330.
- **Banned Claims:** Premier/leading/largest manufacturer, worldwide/global supplier, ISO 9001/14001, REACH registered, Halal, Kosher, FSSAI, Fumigation Certificate, contract/toll manufacturing.

---

## 2. Permanent Claims Linter (`scripts/claims_lint.py`)
`scripts/claims_lint.py` scans all deployable HTML, txt, and xml assets against rules (a)-(e):
- **Rule (a) Banned phrases:** Scans all text, attributes, and JSON-LD for banned claims.
- **Rule (b) Unqualified under-development claims:** Scans sentences containing under-development product names and commercial trigger words (`supply`, `produce`, `manufacture`, `available`), enforcing that `under development`, `R&D`, or `developmental` qualifications are explicitly attached.
- **Rule (c) Product count accuracy:** Prohibits grouping products as a generic "20 Specialty Range"; enforces exact counts (7 on enquiry, 13 under development).
- **Rule (d) Plant District:** Enforces updated district name `District Vav-Tharad` and flags outdated references.
- **Rule (e) Unapproved Annual Capacity:** Flags unratified annual capacity claims.

### Running the Linter:
```bash
python scripts/claims_lint.py
```
Exit code `0` indicates 0 failures. Any failure exits `1` and blocks CI/CD and deployment.

Reports generated:
- `seo/claims-lint-report.md`
- `seo/claims-lint-report.csv`

---

## 3. Mandatory Pre-Merge Gate
Before merging any feature branch into `main`, the claims linter must pass with **0 failures**:
```bash
python scripts/claims_lint.py
```
No pull request or merge commit may proceed if the linter exits with a non-zero code.
