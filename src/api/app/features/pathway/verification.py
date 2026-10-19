"""Verifying course completions (F5), pure functions.

A learner's tick is self-reported. Two ways to strengthen it:

1. **Certificate link, checked automatically.** The learner pastes the provider's own
   verification link. We accept it as `provider_verified` only if it is on that provider's
   official verification pages and resolves. We never read the page content: it carries the
   learner's name, which the reviewer checks by opening it.
2. **Confirmation by the organisation.** HR (company) or a career advisor (institution)
   confirms or rejects. For HRD Corp-claimable courses this is the natural route: the
   employer's claim already requires the provider's attendance record.

Badges show the weakest evidence behind them, so a badge is never stronger than its proof.
"""

from __future__ import annotations

import ssl
import urllib.error
import urllib.request
from collections.abc import Callable, Iterable, Mapping
from urllib.parse import urlsplit

from app.contracts.pathway import CompletionEvidence, Course, CourseStatus, LinkStatus

# Official credential / certificate verification pages, by provider.
VERIFY_PAGES: dict[str, tuple[str, ...]] = {
    "coursera": (
        "https://www.coursera.org/account/accomplishments/",
        "https://coursera.org/account/accomplishments/",
        "https://www.coursera.org/verify/",
        "https://coursera.org/verify/",
        "https://coursera.org/share/",
    ),
    "microsoft learn": ("https://learn.microsoft.com/",),
    # Credly hosts digital badges for many providers (IBM, Microsoft, universities).
    "credly": ("https://www.credly.com/badges/", "https://www.credly.com/go/"),
}

RANK: dict[str, int] = {"self_reported": 0, "certificate_link": 1, "org_confirmed": 2}

Probe = Callable[[str], int | None]


def provider_key(course: Course) -> str | None:
    name = course.provider.lower()
    for key in ("coursera", "microsoft learn"):
        if key in name:
            return key
    return None


def is_provider_page(url: str, course: Course) -> bool:
    """True if `url` is on the course provider's (or Credly's) verification pages."""
    allowed = list(VERIFY_PAGES["credly"])
    key = provider_key(course)
    if key:
        allowed += VERIFY_PAGES[key]
    if not url.startswith(tuple(allowed)):
        return False
    if key == "microsoft learn" and url.startswith("https://learn.microsoft.com/"):
        # Shared achievements and transcripts live under /users/.
        return "/users/" in urlsplit(url).path
    return True


def probe(url: str) -> int | None:
    """HTTP status of `url` (HEAD, then GET if HEAD is refused), None if unreachable."""
    ctx = ssl.create_default_context()
    for method in ("HEAD", "GET"):
        req = urllib.request.Request(url, method=method, headers={"User-Agent": "adept/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=5, context=ctx) as r:
                return int(r.status)
        except urllib.error.HTTPError as exc:
            if method == "HEAD" and exc.code in (403, 405):
                continue
            return int(exc.code)
        except (urllib.error.URLError, TimeoutError, ValueError):
            return None
    return None


def check_link(url: str, course: Course, check: Probe = probe) -> LinkStatus:
    if not is_provider_page(url, course):
        return "not_provider_page"
    code = check(url)
    return "provider_verified" if code is not None and code < 400 else "unreachable"


def effective_statuses(
    statuses: Mapping[str, CourseStatus], evidence: Mapping[str, CompletionEvidence]
) -> dict[str, CourseStatus]:
    """A completion a reviewer rejected no longer counts."""
    return {
        cid: status
        for cid, status in statuses.items()
        if not (status == "completed" and cid in evidence and evidence[cid].kind == "org_rejected")
    }


def evidence_strength(ev: CompletionEvidence | None) -> str:
    if ev is None:
        return "self_reported"
    if ev.kind == "certificate_link" and ev.link_status != "provider_verified":
        return "self_reported"  # a link we could not check proves nothing yet
    return ev.kind if ev.kind in RANK else "self_reported"


def weakest(course_ids: Iterable[str], evidence: Mapping[str, CompletionEvidence]) -> str:
    kinds = [evidence_strength(evidence.get(cid)) for cid in course_ids]
    return min(kinds, key=RANK.__getitem__) if kinds else "self_reported"
