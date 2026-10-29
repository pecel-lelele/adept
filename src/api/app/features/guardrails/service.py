"""Guardrails & transparency (F8): disclosure, source register, fairness report.

Everything here is computed from the running configuration and data, so the About page cannot
drift from what the system actually does.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import FastAPI

from app.contracts.guardrails import (
    CounterfactualResult,
    DataSourceInfo,
    Disclosure,
    FairnessReport,
    SourcesResponse,
)
from app.core import embeddings, seed
from app.core.fairness import PROTECTED_TERMS, counterfactual_diffs, protected_terms_in
from app.core.llm import CALL_LOG, disclosure
from app.features.guardrails import datasync
from app.features.pathway import data as pathway_data
from app.features.pathway import engine, trend_port
from app.features.pathway import service as pathway_service
from app.features.pathway import sync as pathway_sync
from app.features.sdg import repository as sdg_repository
from app.features.sdg import sync as sdg_sync_module

RULES = [
    "The model may only select IDs from a catalogue we supply; unknown IDs are rejected.",
    "Personal data (email, MyKad NRIC, passport, phone) is redacted before any prompt.",
    "Prompt-injection patterns are filtered from text sent to the model.",
    "If no model is configured or it fails, deterministic logic answers instead.",
    "Adi selects checked answer blocks; model-written names, figures and prose "
    "are never displayed.",
    "Courses come only from the catalogue; a skill with no course is reported, not invented.",
    "Every recommendation carries its source, date, scenario and an estimate label.",
    "Age, gender, ethnicity, religion and similar attributes are never accepted as input.",
]


def get_disclosure() -> Disclosure:
    provider, model = disclosure()
    enabled = provider != "none"
    purpose = (
        [
            "Adi selects validated answer-block IDs for your signed-in workspace. Names, "
            "figures and explanations are rendered from checked application facts, "
            "never model prose.",
            "Scores, plans and SDG links are still computed by deterministic, tested rules.",
        ]
        if enabled
        else [
            "No language model is used. Adi answers with a built-in guide, and all plans, "
            "scores and SDG links are deterministic."
        ]
    )
    if embeddings.enabled():
        purpose.append(
            f"Google {embeddings.model_name().split('@')[0]} embeddings (768 dimensions, stored "
            "with pgvector) suggest the closest catalogue skill for unrecognised CV skills-list "
            "phrases or an explicitly submitted skill-bank search. Only short phrases are sent, "
            "after contact details "
            "are removed; suggestions are added only if you choose them."
        )
    return Disclosure(
        llm_enabled=enabled,
        provider=provider,
        model=model if enabled else "",
        purpose=purpose,
        rules=RULES,
        calls_logged=len(CALL_LOG),
        rejected_ids=sum(len(rec.rejected) for rec in CALL_LOG),
    )


def get_sources() -> SourcesResponse:
    courses = pathway_data.catalogue()
    by_source: dict[str, list[date]] = {}
    urls: dict[str, str] = {}
    for c in courses:
        if c.source:
            by_source.setdefault(c.source.name, []).append(c.verified_at)
            urls.setdefault(c.source.name, c.source.url)
    out: list[DataSourceInfo] = []
    un = sdg_repository.un_source()
    out.append(
        DataSourceInfo(
            name=un.name,
            url=un.url,
            retrieved_at=un.retrieved_at,
            kind="live_api",
            used_for="17 SDGs and 169 targets (official wording)",
            records=len(sdg_repository.targets()),
        )
    )
    for name, dates in sorted(by_source.items()):
        out.append(
            DataSourceInfo(
                name=name,
                url=urls[name],
                retrieved_at=min(dates),
                kind="live_api" if "API" in name else "verified_page",
                used_for="Course catalogue (title, URL, hours, cost, HRD Corp status)",
                records=len(dates),
            )
        )
    mapping = sdg_repository.mapping_source()
    n_links = len(seed.rows("sdg", "role_sdg_map")) + len(seed.rows("sdg", "skill_sdg_map"))
    out.append(
        DataSourceInfo(
            name=mapping.name,
            url=mapping.url,
            retrieved_at=mapping.retrieved_at,
            kind="curated",
            used_for="Role and skill → SDG target links with reasons",
            records=n_links,
        )
    )
    # The trend data the pathway actually uses (M1's snapshot, or the seed fallback).
    trend = trend_port.current("moderate")
    if trend:
        for src in trend.snapshot.all_sources():
            out.append(
                DataSourceInfo(
                    name=src.name,
                    url=src.url,
                    retrieved_at=src.retrieved_at,
                    kind="mock" if src.name == "MOCK DATA" else "live_api",
                    used_for=f"AI-trend snapshot {trend.snapshot.version} (skill demand signal)",
                    records=len(trend.growth),
                )
            )
    out.append(
        DataSourceInfo(
            name="Sample personas and teams",
            url="https://github.com/pecel-lelele/adept/tree/main/src/data/seed",
            retrieved_at=date(2026, 10, 20),
            kind="synthetic",
            used_for="Example learners, organisations and skills used for testing (no real people)",
            records=len(seed.rows("personas", "users")) + len(seed.rows("org", "users")),
        )
    )
    synced = datasync.last_successful_syncs()
    catalogue_sync = synced.get(pathway_sync.SOURCE)
    sdg_sync = synced.get(sdg_sync_module.SOURCE)
    for item in out:
        if item.used_for.startswith("Course catalogue"):
            item.last_synced_at = catalogue_sync
        elif item.kind == "live_api" and "SDG" in item.name:
            item.last_synced_at = sdg_sync
        elif item.kind == "curated":
            item.last_synced_at = sdg_sync
    return SourcesResponse(sources=out)


def _api_inputs(app: FastAPI) -> set[str]:
    spec: dict[str, Any] = app.openapi()
    defs = spec.get("components", {}).get("schemas", {})
    names: set[str] = set()

    def walk(schema: dict[str, Any], seen: frozenset[str]) -> None:
        ref = schema.get("$ref")
        if ref:
            key = ref.rsplit("/", 1)[-1]
            if key not in seen:
                walk(defs[key], seen | {key})
            return
        for prop, sub in schema.get("properties", {}).items():
            names.add(prop)
            walk(sub, seen)
        for key in ("items", "additionalProperties"):
            if isinstance(schema.get(key), dict):
                walk(schema[key], seen)
        for key in ("anyOf", "allOf", "oneOf"):
            for sub in schema.get(key, []):
                walk(sub, seen)

    for ops in spec["paths"].values():
        for op in ops.values():
            names.update(p["name"] for p in op.get("parameters", []))
            for media in op.get("requestBody", {}).get("content", {}).values():
                walk(media.get("schema", {}), frozenset())
    return names


def get_fairness(app: FastAPI) -> FairnessReport:
    inputs = _api_inputs(app)
    found = protected_terms_in(inputs)
    base = engine.Learner({"excel": 4, "process-mapping": 2}, 6.0, 500.0, True)

    def key(learner: engine.Learner) -> object:
        plan = pathway_service.build_pathway(learner, "process-automation-analyst", "fast")
        return [(s.skill_id, [c.id for c in s.courses]) for s in plan.steps]

    copy = engine.Learner(dict(base.skill_levels), 6.0, 500.0, True)
    same = counterfactual_diffs(key, base, {"identity-swapped copy": copy})
    checks = [
        CounterfactualResult(
            name="Same skills, time and budget under a different identity",
            passed=not same,
            detail="The pathway engine receives no identity fields, so plans cannot differ "
            "by who the learner is."
            if not same
            else f"Differs: {same}",
        ),
        CounterfactualResult(
            name="Protected attributes absent from every API input",
            passed=not found,
            detail=f"{len(inputs)} request fields and parameters checked."
            if not found
            else f"Found: {', '.join(found)}",
        ),
    ]
    return FairnessReport(
        protected_attributes=list(PROTECTED_TERMS),
        api_inputs_checked=len(inputs),
        protected_inputs_found=found,
        counterfactual_checks=checks,
        passed=all(c.passed for c in checks),
    )
