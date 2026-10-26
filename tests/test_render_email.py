#!/usr/bin/env python3
"""
tests/test_render_email.py - Unit tests for scripts/outreach/render_email.py
Verifies that rendered emails strictly use values from seo/facts-register.json
and fails if rendered CIN or plant address deviates from the register.
"""

import unittest
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "outreach"))

from claims_lint import load_facts
from render_email import render_email

class TestRenderEmail(unittest.TestCase):
    def setUp(self):
        self.facts = load_facts()
        self.register_cin = self.facts["company"]["cin"]
        self.register_plant = self.facts["company"]["plant"]

    def test_rendered_cin_matches_register(self):
        for template in ["correction", "initial"]:
            body = render_email(template)
            self.assertIn(self.register_cin, body)
            self.assertEqual(self.register_cin, "U15400GJ2019PTC110518")

    def test_rendered_plant_matches_register(self):
        for template in ["correction", "initial"]:
            body = render_email(template)
            self.assertIn(self.register_plant, body)
            self.assertEqual(
                self.register_plant,
                "Survey No. 301 P-2, Jada-Kotarwada Road, Village Sardarpura, Post Ravel, Taluka Deodar, District Vav-Tharad, Gujarat 385330"
            )

    def test_rendered_body_passes_claims_linter(self):
        for template in ["correction", "initial"]:
            # render_email internally runs lint_content and raises ValueError on any hard failure
            body = render_email(template)
            self.assertIsNotNone(body)

if __name__ == "__main__":
    unittest.main()
