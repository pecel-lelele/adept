"""Export the Phase 2 report in the organisers' template layout. No network, database or model.

Run from the repository root. Leader contact, attestations and signature are added afterwards.
"""

from pathlib import Path

from template_pdf import render

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "docs/submission/submission-final-report.md"
OUTPUT = ROOT / "submission/SDC2026_Pecel-Lele_Final.pdf"


if __name__ == "__main__":
    render(SOURCE, OUTPUT, "Adept Final Project & Prototype Report")
