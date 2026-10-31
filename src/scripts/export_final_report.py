"""Export the public, unsigned Phase 2 report from its tracked Markdown source.

Run from the repository root. No network, database, model or office automation.
The private organiser submission still needs leader contact, attestations and signature.
"""

from pathlib import Path

from export_technical_declaration import render_pdf

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "docs/submission/submission-proposal.md"
OUTPUT = ROOT / "submission/SDC2026_Pecel-Lele_Final.pdf"


if __name__ == "__main__":
    render_pdf(SOURCE, OUTPUT, "Adept Final Project Report")
