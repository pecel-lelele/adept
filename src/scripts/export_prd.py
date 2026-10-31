"""Export the source-grounded product PRD and pitch brief as a portable PDF.

Uses the repository's installed PyMuPDF dependency, without network or model calls.
"""

from pathlib import Path

from export_technical_declaration import render_pdf

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "docs/submission/final-pitch-prd.md"
OUTPUT = ROOT / "submission/SDC2026_Pecel-Lele_ProductPRD.pdf"


if __name__ == "__main__":
    render_pdf(SOURCE, OUTPUT, "Adept Product and Pitch PRD")
