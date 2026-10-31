"""Guardrails & transparency (F8): disclosure, source register, fairness report.

Everything here is computed from the running configuration and data, so the About page cannot
drift from what the system actually does.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from fastapi import FastAPI

from app.contracts.guardrails import (
    CounterfactualResult,
    DataSourceInfo,
    Disclosure,
    FairnessReport,
    RegisterEntry,
    SourcesResponse,
)
from app.core import embeddings, seed
from app.core.fairness import PROTECTED_TERMS, protected_terms_in
from app.core.llm import CALL_LOG, disclosure
from app.features.guardrails import datasync
from app.features.pathway import data as pathway_data
from app.features.pathway import sync as pathway_sync
from app.features.pathway import trend_port
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

# Public reference register only: dates and record counts remain in get_sources().
REGISTRY = tuple(
    RegisterEntry.model_validate(entry)
    for entry in json.loads(Path(__file__).with_name("registry.json").read_text(encoding="utf-8"))
)


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
            "Adi currently answers with a built-in guide. All plans, "
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
    from app.features.data_refresh import trend_store

    if trend_store.series_method() == trend_store.GEMINI_METHOD:
        purpose.append(
            "Google gemini-embedding-001 (384 dimensions) matches public arXiv papers to catalogue "
            "skills for trend signals, in background jobs only, with one stored threshold per "
            "model chosen to match the mentions per paper measured with MiniLM."
        )
    return Disclosure(
        llm_enabled=enabled,
        provider=provider,
        model=model if enabled else "",
        purpose=purpose,
        registry=list(REGISTRY),
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
    from app.features.trends.labour import current

    context = current()
    src = context.meta.sources[0]
    out.append(
        DataSourceInfo(
            name=src.name,
            url=src.url,
            retrieved_at=src.retrieved_at,
            kind="curated" if context.meta.is_fallback else "live_api",
            used_for=(
                f"National survey context for {context.observed_month:%Y-%m}; not a role forecast"
            ),
            records=1,
        )
    )
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


def get_fairness(app: FastAPI, *, rank_evidence: tuple[int, int] | None = None) -> FairnessReport:
    from app.features.impact import service as impact_service
    from app.features.matching.trend_port import fetch_snapshot

    inputs = _api_inputs(app)
    found = protected_terms_in(inputs)
    worst, variants = (
        rank_evidence
        if rank_evidence is not None
        else impact_service.identity_rank_evidence(
            impact_service.load_personas(), fetch_snapshot("moderate")
        )
    )
    checks = [
        CounterfactualResult(
            name="Same skills under swapped synthetic names and career segments",
            passed=variants > 0 and worst == 0,
            detail=f"{variants} identity variants through profile-to-matching and the production "
            f"ranker; largest rank change: {worst}. Limited regression evidence, "
            "not proof of population fairness.",
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
