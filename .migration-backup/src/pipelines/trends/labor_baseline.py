"""src/pipelines/trends/labor_baseline.py

PART 3 – Labor-decay baseline (Source B: BLS 2023-2033 projections).

Reads:
  src/data/seed/canonical_skills.csv
  src/data/seed/bls_projections_2023_2033.csv

Writes:
  src/data/seed/labor_decay.csv   (columns: skill_id, labor_decay, labor_decay_source_note)

Run:
  PYTHONPATH=src/api:src uv run --no-project python src/pipelines/trends/labor_baseline.py

Design notes:
  * The mapping from skill → SOC is an editorial decision documented inline per
    skill_id.  It picks the SOC code whose occupation most directly depends on
    the skill as its *primary* task.
  * annualized_rate in BLS is already percent/yr.  We convert to a fraction:
    labor_decay = annualized_rate / 100.
  * Skills for which NO suitable SOC proxy exists receive 0.0 and a note
    explaining the gap; the composite scorer treats 0.0 as "no labor signal"
    and relies entirely on the research-velocity component.
  * This script is idempotent: running it twice produces the same output.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[3]
SEED_DIR = REPO_ROOT / "src" / "data" / "seed"
CANONICAL = SEED_DIR / "canonical_skills.csv"
BLS_CSV = SEED_DIR / "bls_projections_2023_2033.csv"
OUT_CSV = SEED_DIR / "labor_decay.csv"


# ---------------------------------------------------------------------------
# Editorial mapping: skill_id → (SOC code, occupation title, annualized_rate)
# Documented inline for full traceability.
# ---------------------------------------------------------------------------

# fmt: off
SKILL_SOC_MAP: dict[str, tuple[str, str]] = {
    # ── emerging_ai_native ──────────────────────────────────────────────────
    # Most emerging-AI skills map to 15-1299 (Computer occupations NEC) or
    # 15-1252 (Software developers) as the closest available SOC proxy.
    # Where no good proxy exists the skill gets 0.0 with a note.
    "prompt-engineering":        ("15-1299", "Computer occupations, all other"),
    "llm-fine-tuning":           ("15-1252", "Software developers"),
    "rag-systems":               ("15-1252", "Software developers"),
    "ai-literacy":               ("25-1011", "Business teachers, postsecondary"),
    "mlops":                     ("15-1252", "Software developers"),
    "vector-databases":          ("15-1243", "Database architects"),
    "ai-agents":                 ("15-1252", "Software developers"),
    "multimodal-ai":             ("15-1252", "Software developers"),
    "ai-safety":                 ("15-1299", "Computer occupations, all other"),
    "explainable-ai":            ("15-1299", "Computer occupations, all other"),
    "ai-ethics":                 ("15-1299", "Computer occupations, all other"),
    "llm-evaluation":            ("15-1253", "Software quality assurance analysts"),
    "data-pipelines":            ("15-1242", "Database administrators"),
    "synthetic-data-gen":        ("15-1299", "Computer occupations, all other"),
    "feature-engineering":       ("15-1299", "Computer occupations, all other"),
    "model-monitoring":          ("15-1253", "Software quality assurance analysts"),
    "federated-learning":        ("15-1299", "Computer occupations, all other"),
    "ai-product-management":     ("11-3031", "Financial managers"),  # closest mgmt proxy
    "cloud-ai-services":         ("15-1244", "Network and computer systems administrators"),
    "low-code-ai":               ("15-1254", "Web developers"),
    "nlp-engineering":           ("15-1252", "Software developers"),
    "computer-vision":           ("15-1252", "Software developers"),
    "time-series-forecasting":   ("13-2051", "Financial and investment analysts"),
    "causal-inference":          ("19-3011", "Economists"),
    "graph-ml":                  ("15-1252", "Software developers"),
    "recommendation-systems":    ("15-1252", "Software developers"),
    "robotic-process-automation": ("15-1299", "Computer occupations, all other"),
    "ai-assisted-coding":        ("15-1252", "Software developers"),
    "generative-design":         ("27-1011", "Art directors"),
    "security-ai":               ("15-1212", "Information security analysts"),
    "climate-ai":                ("19-2041", "Environmental scientists and specialists"),
    "healthcare-ai":             ("29-2010", "Clinical laboratory technologists"),
    "fintech-ai":                ("13-2051", "Financial and investment analysts"),
    "digital-twin":              ("15-1252", "Software developers"),
    "edge-ai":                   ("15-1252", "Software developers"),
    "quantum-ml":                ("15-1221", "Computer and information research scientists"),
    "data-governance-ai":        ("15-1242", "Database administrators"),
    "bias-auditing":             ("15-1253", "Software quality assurance analysts"),
    "human-ai-collaboration":    ("15-1299", "Computer occupations, all other"),
    "conversational-ai":         ("15-1252", "Software developers"),
    # ── at_risk_routine ────────────────────────────────────────────────────
    "manual-data-entry":         ("43-9021", "Data entry keyers"),
    "bookkeeping":               ("43-3031", "Bookkeeping, accounting, and auditing clerks"),
    "payroll-processing":        ("43-3051", "Payroll and timekeeping clerks"),
    "document-filing":           ("43-4071", "File clerks"),
    "invoice-processing":        ("43-3011", "Bill and account collectors"),
    "report-generation":         ("43-9061", "Office clerks, general"),
    "scheduling-admin":          ("43-6014", "Secretaries and admin assistants (other)"),
    "data-entry-forms":          ("43-9021", "Data entry keyers"),
    "bank-reconciliation":       ("43-3031", "Bookkeeping, accounting, and auditing clerks"),
    "excel-basic":               ("43-9061", "Office clerks, general"),
    "copy-editing-routine":      ("27-3041", "Editors"),
    "claims-processing":         ("43-9041", "Insurance claims and policy processing clerks"),
    "ticket-routing":            ("43-9061", "Office clerks, general"),
    "order-entry":               ("43-4151", "Order clerks"),
    "inventory-counting":        ("43-5071", "Shipping, receiving, and inventory clerks"),
    "loan-application-processing": ("43-3061", "Procurement clerks"),
    "hr-admin-routine":          ("43-4161", "Human resources assistants"),
    "customer-id-verification":  ("43-4051", "Customer service representatives"),
    "tax-form-filing":           ("13-2082", "Tax preparers"),
    "contract-template-drafting": ("23-1012", "Judicial law clerks"),
    "supply-chain-tracking":     ("43-5011", "Cargo and freight agents"),
    "call-centre-scripted":      ("43-4051", "Customer service representatives"),
    "email-triage":              ("43-9061", "Office clerks, general"),
    "expense-reporting":         ("43-3031", "Bookkeeping, accounting, and auditing clerks"),
    "procurement-admin":         ("43-3061", "Procurement clerks"),
    "data-cleaning-manual":      ("43-9021", "Data entry keyers"),
    "translation-routine":       ("27-3041", "Editors"),
    "report-distribution":       ("43-9061", "Office clerks, general"),
    "basic-sql-queries":         ("15-1242", "Database administrators"),
    "spreadsheet-macros":        ("43-9061", "Office clerks, general"),
    "logistics-dispatch":        ("43-5061", "Production, planning, and expediting clerks"),
    "sla-monitoring":            ("15-1299", "Computer occupations, all other"),
    "label-annotation":          ("43-9021", "Data entry keyers"),
    "churn-flag-alerts":         ("15-1299", "Computer occupations, all other"),
    "vendor-master-data":        ("43-3061", "Procurement clerks"),
    "technical-writing-routine": ("27-3041", "Editors"),
    "asset-tracking":            ("43-5071", "Shipping, receiving, and inventory clerks"),
    "meeting-minutes":           ("43-6014", "Secretaries and admin assistants (other)"),
    "trade-confirmation":        ("43-3031", "Bookkeeping, accounting, and auditing clerks"),
    # ── stable_oversight ───────────────────────────────────────────────────
    "risk-compliance":           ("13-2061", "Financial examiners"),
    "audit-internal":            ("13-2011", "Accountants and auditors"),
    "python":                    ("15-1252", "Software developers"),
    "data-visualisation":        ("15-1252", "Software developers"),
    "sql-advanced":              ("15-1242", "Database administrators"),
    "process-mapping":           ("13-1161", "Market research analysts"),
    "customer-service":          ("43-4051", "Customer service representatives"),
    "logistics-planning":        ("43-5061", "Production, planning, and expediting clerks"),
    "stakeholder-management":    ("11-3031", "Financial managers"),
    "project-management":        ("13-1071", "Human resources specialists"),
    "change-management":         ("13-1071", "Human resources specialists"),
    "critical-thinking":         ("19-3011", "Economists"),
    "negotiation":               ("23-1011", "Lawyers"),
    "coaching-mentoring":        ("21-1012", "Educational, guidance, and career counselors"),
    "regulatory-affairs":        ("13-2061", "Financial examiners"),
    "cybersecurity-governance":  ("15-1212", "Information security analysts"),
    "data-privacy":              ("15-1212", "Information security analysts"),
    "financial-analysis":        ("13-2051", "Financial and investment analysts"),
    "ux-research":               ("15-1255", "Web and digital interface designers"),
    "supply-chain-strategy":     ("43-5061", "Production, planning, and expediting clerks"),
    "enterprise-architecture":   ("15-1241", "Computer network architects"),
    "learning-development":      ("21-1012", "Educational, guidance, and career counselors"),
    "workforce-planning":        ("13-1071", "Human resources specialists"),
    "esg-reporting":             ("19-2041", "Environmental scientists and specialists"),
    "cross-cultural-communication": ("27-3043", "Writers and authors"),
    "public-speaking":           ("27-3011", "Broadcast announcers and radio disc jockeys"),
    "strategic-planning":        ("11-1011", "Chief executives"),
    "knowledge-management":      ("13-1071", "Human resources specialists"),
    "vendor-management":         ("13-1071", "Human resources specialists"),
    "clinical-judgement":        ("29-1141", "Registered nurses"),
    "legal-research":            ("23-1012", "Judicial law clerks"),
}
# fmt: on


def load_bls() -> dict[str, tuple[float, str]]:
    """Return {soc_code: (annualized_rate_fraction, occupation_title)}."""
    result: dict[str, tuple[float, str]] = {}
    with BLS_CSV.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            soc = row["soc_code"].strip()
            rate = float(row["annualized_rate"]) / 100.0  # percent → fraction
            title = row["occupation_title"].strip()
            result[soc] = (rate, title)
    return result


def load_skills() -> list[str]:
    with CANONICAL.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        return [row["skill_id"] for row in reader]


def build_labor_decay() -> list[dict[str, str]]:
    bls = load_bls()
    skills = load_skills()
    rows: list[dict[str, str]] = []

    for skill_id in skills:
        entry = SKILL_SOC_MAP.get(skill_id)
        if entry is None:
            # No editorial mapping provided for this skill.
            labor_decay = 0.0
            note = (
                f"BLS 2023-2033: no SOC proxy mapped for '{skill_id}'; "
                "labor_decay set to 0.0 (velocity component only)"
            )
        else:
            soc, occupation_label_editorial = entry
            if soc in bls:
                rate, bls_title = bls[soc]
                labor_decay = rate
                note = (
                    f"BLS 2023-2033 projection for SOC {soc} ({bls_title}), {rate * 100:+.1f}%/yr"
                )
            else:
                # SOC listed in map but not in the snapshot CSV (edge case).
                labor_decay = 0.0
                note = (
                    f"BLS 2023-2033: SOC {soc} ({occupation_label_editorial}) "
                    "not found in snapshot; labor_decay set to 0.0"
                )

        rows.append(
            {
                "skill_id": skill_id,
                "labor_decay": str(round(labor_decay, 6)),
                "labor_decay_source_note": note,
            }
        )
    return rows


def write_output(rows: list[dict[str, str]]) -> None:
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh, fieldnames=["skill_id", "labor_decay", "labor_decay_source_note"]
        )
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows -> {OUT_CSV}")


def main() -> None:
    if not CANONICAL.exists():
        print(f"ERROR: {CANONICAL} not found", file=sys.stderr)
        sys.exit(1)
    if not BLS_CSV.exists():
        print(f"ERROR: {BLS_CSV} not found", file=sys.stderr)
        sys.exit(1)

    rows = build_labor_decay()
    write_output(rows)


if __name__ == "__main__":
    main()
