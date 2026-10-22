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
# A figure with its unit: "RM 450", "72%", "6" (a price, a share or a plain count).
_FIGURE = re.compile(r"(RM\s?)?(\d+(?:[.,]\d+)*)(\s?%)?", re.IGNORECASE)
# A plain number used as a list or step marker, not a claim: "1.", "2)", "step 3", "week 4".
_MARKER = re.compile(
    r"(?:^|\n)\s*\d{1,2}[.)]\s"
    r"|\b(?:step|langkah|week|weeks|minggu|module|modul|level|tahap)\s+\d{1,2}\b",
    re.IGNORECASE,
)
# Names a model might invent outside tags: a quoted title, or Title Case words next to a word
# for a course, programme, role or certificate ("the Galactic Leadership course").
_KIND_WORDS = (
    r"course|courses|programme|program|programmes|training|certificate|certification|"
    r"bootcamp|degree|diploma|role|roles|position|job|kursus|latihan|peranan|jawatan|sijil"
)
_TITLE = r"(?:[A-Z][\w&'+-]*\s+){1,6}[A-Z][\w&'+-]*"
_INVENTED = re.compile(
    '["\u201c]([^"\u201d\n]{3,80})["\u201d]'
    + rf"|\b({_TITLE})\s+(?:{_KIND_WORDS})\b"
    + rf"|\b(?:{_KIND_WORDS})\s+(?:called|named|titled|bernama)\s+({_TITLE})"
)
# Names Adi may write freely: the product, the scheme and common provider names.
_ALLOWED_NAMES = {
    "adept",
    "adi",
    "hrd corp",
    "un",
    "sdg",
    "future skills radar",
    "ai",
    "coursera",
    "microsoft learn",
    "google",
    "ibm",
    "malaysia",
    "malaysian",
    "bahasa melayu",
}
_PAGE_PATH = re.compile(r"/[A-Za-z0-9/_-]{0,100}")
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


def _safe_page(page: str) -> str:
    """Only a plain route path reaches the prompt (never free text from the caller)."""
    return page if _PAGE_PATH.fullmatch(page) else "/"


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
    """The official label of a catalogue entry, or None when the ID does not exist."""
    if kind == "course":
        found = ctx.refs.courses.get(ref_id)
        return found[0] if found else None
    table: dict[str, str] = {
        "role": ctx.refs.roles,
        "skill": ctx.refs.skills,
        "sdg": ctx.refs.sdg,
        "page": ctx.refs.pages,
    }.get(kind, {})  # type: ignore[assignment]
    return table.get(ref_id)


def invented_names(text: str, ctx: ctx_mod.Context) -> list[str]:
    """Course-, role- or programme-like names written outside tags that are not in the catalogue.

    The model must tag every catalogue item; anything that looks like a title but is untagged
    and unknown is treated as invented, and the whole answer is replaced by the guide.
    """
    known = {
        label.lower()
        for table in (ctx.refs.roles, ctx.refs.skills, ctx.refs.pages, ctx.refs.sdg)
        for label in table.values()
    }
    known |= {title.lower() for title, _ in ctx.refs.courses.values()}
    known |= _ALLOWED_NAMES
    found: list[str] = []
    for m in _INVENTED.finditer(_TAG.sub(" ", text)):
        name = next(g for g in m.groups() if g).strip()
        lowered = name.lower()
        if lowered in known or any(lowered in k for k in known):
            continue
        found.append(name)
    return found[:5]


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


def _figure_key(m: re.Match[str]) -> str:
    number = m.group(2).replace(",", "")
    if m.group(1):
        return f"rm{number}"
    if m.group(3):
        return f"{number}%"
    return number


def unchecked_figures(text: str, ctx: ctx_mod.Context) -> list[str]:
    """Figures in the answer that the context does not contain, compared with their units.

    "26%" needs a "26%" in the data (the year 2026 does not count), "RM 10" needs "RM 10".
    Only list and step markers ("2.", "step 3") are skipped.
    """
    context = ctx.text()
    known = {_figure_key(m) for m in _FIGURE.finditer(context)}
    known_bare = {m.group(2).replace(",", "") for m in _FIGURE.finditer(context)}
    body = _TAG.sub(" ", text)
    markers = [(m.start(), m.end()) for m in _MARKER.finditer(body)]
    out: list[str] = []
    for m in _FIGURE.finditer(body):
        if any(start <= m.start() < end for start, end in markers):
            continue
        key = _figure_key(m)
        plain = not (m.group(1) or m.group(3))
        if key in known or (plain and key in known_bare):
            continue
        out.append(m.group(0).strip())
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
    # Every caller-supplied turn is untrusted (the client sends the assistant turns back too).
    history = [
        {"role": m.role, "content": _clean_question(m.content)[:1200]} for m in body.messages[-8:]
    ]
    prompt = _system_prompt(ctx, body.locale, _safe_page(body.page))
    system = redact_text(clean_extracted_text(prompt))
    messages = [{"role": "system", "content": system}, *history]
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
        invented = invented_names(text, ctx)
        outcome = "rejected_unknown_ids" if rejected or invented else "ok"
        _record(provider, outcome, rejected + invented)
        figures = unchecked_figures(text, ctx)
        if invented or not any(p.text.strip() for p in parts):
            # A name outside the catalogue is never shown: the guide answers instead.
            log.warning("assistant answer named items outside the catalogue: %s", invented)
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
