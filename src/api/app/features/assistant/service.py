"""Adi's answers: a language model grounded in the person's Adept data, checked before showing.

Defences, in order:
1. The question is injection-filtered and PII-redacted before it reaches the model.
2. The model sees only a CONTEXT block built from Adept's own data (see `context.py`).
3. Roles, skills, courses, SDG targets and pages may only appear as [[kind:id]] tags; each tag is
   resolved against the catalogue and rendered with its official label. Unknown IDs are dropped
   and logged (they count as rejected IDs on /about).
4. Figures in the answer that do not appear in the context are reported as unchecked.
5. No model, an open circuit breaker, a timeout or a bad answer: the deterministic guide answers
   from the same context, so Adi always works.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime

from app.contracts.assistant import AnswerPart, AssistantIn, AssistantReply, Locale
from app.core.auth import CurrentUser
from app.core.llm.gateway import BREAKER, CALL_LOG, LlmCallRecord
from app.core.llm.provider import LLMProvider, LLMUnavailableError, get_provider
from app.core.logging import get_logger
from app.core.security.pii import redact_text
from app.core.security.sanitize import clean_extracted_text
from app.features.assistant import context as ctx_mod
from app.features.assistant import guide

log = get_logger("app.assistant")

_TAG = re.compile(r"\[\[(role|skill|course|sdg|page):([^\]\s]{1,100})\]\]")
_FIGURE = re.compile(r"(?:RM\s?)?\d+(?:[.,]\d+)?\s?%?")
_LANG = {"en": "English", "ms": "Bahasa Melayu", "zh": "Simplified Chinese"}
MAX_REPLY_TOKENS = 700


def _system_prompt(ctx: ctx_mod.Context, locale: Locale, page: str) -> str:
    who = {
        "visitor": "a visitor who has not signed up yet",
        "learner": "a signed-in learner",
        "manager": "a signed-in HR / L&D manager or career-centre advisor",
    }[ctx.audience]
    return (
        "You are Adi, the friendly guide inside Adept, a Malaysian career and reskilling app. "
        f"You are talking to {who}, currently on the page {page}.\n"
        "Rules you must follow:\n"
        "- Answer ONLY from the CONTEXT below. If the answer is not there, say so briefly and "
        "point to the page that would help. Never invent jobs, courses, skills, SDG targets, "
        "statistics, salaries or dates.\n"
        "- Whenever you mention a role, skill, course, SDG target or app page, write it ONLY as a "
        "tag copied from CONTEXT or from the page list: [[role:id]], [[skill:id]], "
        "[[course:id]], [[sdg:4.4]], [[page:/app/pathway]]. Do not write their names yourself.\n"
        "- Only use numbers that appear in CONTEXT. Fit scores, trends and outlooks are "
        "estimates: say so when you use them.\n"
        "- You support decisions; the person decides. Never make or suggest hiring decisions, "
        "and never judge people by age, gender, ethnicity, religion or background.\n"
        f"- Reply in {_LANG[locale]}, warm and plain, at most 120 words. Use short paragraphs "
        "or '- ' bullet lines. End with one concrete next step.\n\n"
        "Pages you may link: "
        + ", ".join(f"[[page:{p}]] ({label})" for p, label in ctx_mod.PAGES.items())
        + "\n\nCONTEXT:\n"
        + ctx.text()
    )


def _clean_question(text: str) -> str:
    return redact_text(clean_extracted_text(text))[:2000]


def _href(kind: str, ref_id: str, ctx: ctx_mod.Context) -> str | None:
    if kind == "role":
        return f"/app/matches/{ref_id}" if ctx.audience == "learner" else None
    if kind == "skill":
        return "/app/radar" if ctx.audience == "learner" else None
    if kind == "course":
        return ctx.refs.courses[ref_id][1]
    if kind == "page":
        return ref_id
    if kind == "sdg":
        return "/app/sdg" if ctx.audience == "learner" else None
    return None


def _label(kind: str, ref_id: str, ctx: ctx_mod.Context) -> str | None:
    table: dict[str, str] = {
        "role": ctx.refs.roles,
        "skill": ctx.refs.skills,
        "sdg": ctx.refs.sdg,
        "page": ctx.refs.pages,
    }.get(kind, {})  # type: ignore[assignment]
    if kind == "course":
        found = ctx.refs.courses.get(ref_id)
        return found[0] if found else None
    if kind == "sdg" and ref_id not in table:
        return f"SDG {ref_id}" if re.fullmatch(r"\d{1,2}\.[0-9a-c]{1,2}", ref_id) else None
    return table.get(ref_id)


def to_parts(text: str, ctx: ctx_mod.Context) -> tuple[list[AnswerPart], list[str]]:
    """Split an answer into text and checked references; return (parts, rejected ids)."""
    parts: list[AnswerPart] = []
    rejected: list[str] = []
    pos = 0
    for m in _TAG.finditer(text):
        if m.start() > pos:
            parts.append(AnswerPart(kind="text", text=text[pos : m.start()]))
        kind, ref_id = m.group(1), m.group(2)
        label = _label(kind, ref_id, ctx)
        if label is None:
            rejected.append(f"{kind}:{ref_id}")
        else:
            parts.append(
                AnswerPart(
                    kind=kind,  # type: ignore[arg-type]
                    text=label,
                    ref_id=ref_id,
                    href=_href(kind, ref_id, ctx),
                )
            )
        pos = m.end()
    if pos < len(text):
        parts.append(AnswerPart(kind="text", text=text[pos:]))
    # Drop stray brackets the model might leave and collapse empty pieces.
    cleaned = [
        p.model_copy(update={"text": re.sub(r"\[\[[^\]]*\]\]", "", p.text)})
        if p.kind == "text"
        else p
        for p in parts
    ]
    return [p for p in cleaned if p.text.strip() or p.kind != "text"], rejected


def unchecked_figures(text: str, ctx: ctx_mod.Context) -> list[str]:
    """Numbers in the answer that the context does not contain (step numbers excluded)."""
    known = ctx.text().replace(",", "")
    out: list[str] = []
    for m in _FIGURE.finditer(_TAG.sub(" ", text)):
        figure = m.group(0).strip()
        bare = figure.replace("RM", "").replace(" ", "").replace(",", "")
        if not bare or (bare.isdigit() and int(bare) <= 12 and "%" not in figure):
            continue  # small counts and step numbers ("3 steps", "step 2")
        if bare.rstrip("%") not in known:
            out.append(figure)
    return sorted(set(out))[:5]


def _record(provider: LLMProvider, outcome: str, rejected: list[str]) -> None:
    CALL_LOG.append(
        LlmCallRecord(
            at=datetime.now(UTC),
            provider=provider.name,
            model=provider.model,
            task="assistant.chat",
            n_candidates=0,
            selected=(),
            rejected=tuple(rejected),
            outcome=outcome,  # type: ignore[arg-type]
        )
    )


def _ask_model(body: AssistantIn, ctx: ctx_mod.Context, provider: LLMProvider) -> str:
    BREAKER.check()
    history = [
        {
            "role": m.role,
            "content": _clean_question(m.content) if m.role == "user" else m.content[:1200],
        }
        for m in body.messages[-8:]
    ]
    messages = [
        {"role": "system", "content": _system_prompt(ctx, body.locale, body.page)},
        *history,
    ]
    try:
        text = provider.chat(messages, max_tokens=MAX_REPLY_TOKENS)
    except LLMUnavailableError:
        BREAKER.failure()
        raise
    BREAKER.success()
    return text


def answer(user: CurrentUser | None, body: AssistantIn) -> AssistantReply:
    ctx = ctx_mod.build(user, body.scenario)
    question = _clean_question(body.messages[-1].content)
    provider = _provider()
    used_llm = False
    text = ""
    rejected: list[str] = []
    if provider.name != "none":
        try:
            text = _ask_model(body, ctx, provider)
            used_llm = True
        except LLMUnavailableError as exc:
            log.warning("assistant model unavailable, using the guide: %s", exc)
            _record(provider, "unavailable", [])
    if used_llm:
        parts, rejected = to_parts(text, ctx)
        _record(provider, "rejected_unknown_ids" if rejected else "ok", rejected)
        figures = unchecked_figures(text, ctx)
        if not any(p.text.strip() for p in parts):
            used_llm, figures = False, []
    if not used_llm:
        parts, _ = to_parts(guide.reply(question, ctx, body.locale), ctx)
        figures = []
    return AssistantReply(
        parts=parts,
        suggestions=guide.suggestions(ctx, body.page, body.locale),
        used_llm=used_llm,
        provider=provider.name if used_llm else "none",
        model=getattr(provider, "last_model", provider.model) if used_llm else "",
        grounded_on=ctx.grounded_on,
        unchecked_figures=figures,
        meta=ctx.meta,
    )


def _provider() -> LLMProvider:
    try:
        return get_provider()
    except LLMUnavailableError as exc:
        log.warning("LLM provider misconfigured, Adi uses its guide: %s", exc)
        from app.core.llm.provider import NullProvider

        return NullProvider()
