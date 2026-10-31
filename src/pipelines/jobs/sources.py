"""Connectors: fetch one board's current openings and return them as `RawPosting`s.

Each connector reads a public API documented (or published for career-site use) by the
platform, identifies itself with a descriptive User-Agent, checks robots.txt, keeps a polite
delay between requests and caps how many postings it reads. Only openings located in Malaysia,
or remote openings that Malaysians can apply for, are kept. Full ad text is used in memory to
find skills and is never stored.
"""

from __future__ import annotations

import html
import json
import os
import re
import time
import urllib.robotparser
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any
from urllib.parse import quote, urlsplit

import httpx

from pipelines.jobs.boards import REMOTE_QUERIES, Board

USER_AGENT = "AdeptJobsBot/1.0 (+https://github.com/pecel-lelele/adept; student hackathon project)"
TIMEOUT_S = 30.0
DELAY_S = 0.4
MAX_PER_BOARD = 300
# One response larger than this is rejected while it streams (memory bound for in-app runs).
MAX_RESPONSE_BYTES = 15_000_000

# Places that mark an on-site opening as Malaysian.
MY_PLACES = (
    "malaysia",
    "kuala lumpur",
    "selangor",
    "petaling jaya",
    "cyberjaya",
    "putrajaya",
    "shah alam",
    "subang",
    "penang",
    "pulau pinang",
    "bayan lepas",
    "batu kawan",
    "johor",
    "iskandar",
    "kedah",
    "kulim",
    "melaka",
    "malacca",
    "ipoh",
    "perak",
    "sarawak",
    "kuching",
    "sabah",
    "kota kinabalu",
    "seremban",
    "negeri sembilan",
    "miri",
)
# Location values that name no place: treated as missing so a later field (offices, country)
# decides. A bare "Remote" primary used to reject a Malaysian office listed second.
PLACEHOLDER_LOCATIONS = frozenset({"remote", "anywhere", "remote anywhere", "anywhere remote"})
# Remote openings open to someone living in Malaysia.
REMOTE_OK = ("malaysia", "worldwide", "anywhere", "global", "asia", "apac", "southeast asia")
# Stored remote scopes where the feed names a region that includes Malaysia.
EXPLICIT_REMOTE_SCOPES = frozenset({"Malaysia", "Southeast Asia", "APAC", "Asia"})


@dataclass
class RawPosting:
    source: str
    board: str
    source_id: str
    employer: str
    title: str
    url: str
    api_url: str
    location: str = ""
    work_mode: str = "onsite"  # onsite | hybrid | remote
    remote_scope: str = ""  # for remote openings: who may apply (e.g. "Malaysia", "APAC")
    employment_type: str = ""
    experience_level: str = ""
    posted_at: date | None = None
    expires_at: date | None = None
    salary_min: float | None = None
    salary_max: float | None = None
    salary_currency: str = ""
    salary_period: str = ""
    text: str = field(default="", repr=False)  # title + ad text, for skill extraction only


class Fetcher:
    """HTTP with robots.txt checks, a fixed delay per host and one shared client."""

    def __init__(
        self,
        client: httpx.Client | None = None,
        delay_s: float = DELAY_S,
        deadline: float | None = None,
    ) -> None:
        self.client = client or httpx.Client(
            timeout=TIMEOUT_S, headers={"User-Agent": USER_AGENT}, follow_redirects=True
        )
        self.delay_s = delay_s
        # time.monotonic() value after which no further request is made (in-app refresh).
        self.deadline = deadline
        self._robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}
        self._last: dict[str, float] = {}

    def _remaining(self) -> float | None:
        if self.deadline is None:
            return None
        left = self.deadline - time.monotonic()
        if left <= 0:
            raise IncompleteRead("time budget reached; previous listings retained")
        return left

    def _rules(self, url: str) -> urllib.robotparser.RobotFileParser | None:
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        if origin not in self._robots:
            rp: urllib.robotparser.RobotFileParser | None = urllib.robotparser.RobotFileParser()
            try:
                body = self._read("GET", f"{origin}/robots.txt")
                if body.lstrip().startswith(b"<"):
                    raise PermissionError("robots check returned an error page")
                rp.parse(body.decode("utf-8", errors="replace").splitlines())
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code not in (404, 410):
                    raise PermissionError("robots check denied or unavailable") from None
                rp = None  # an explicitly absent robots.txt permits the published API
            except httpx.HTTPError as exc:
                raise IncompleteRead("robots check unavailable; board not read") from exc
            self._robots[origin] = rp
        return self._robots[origin]

    def allowed(self, url: str) -> bool:
        rp = self._rules(url)
        return rp is None or rp.can_fetch(USER_AGENT, url)

    def _wait(self, url: str) -> None:
        host = urlsplit(url).netloc
        rp = self._robots.get(f"{urlsplit(url).scheme}://{host}")
        delay = max(self.delay_s, float((rp.crawl_delay(USER_AGENT) if rp else None) or 0))
        gap = time.monotonic() - self._last.get(host, 0.0)
        if gap < delay:
            left = self._remaining()
            if left is not None and delay - gap >= left:
                raise IncompleteRead("crawl delay exceeds remaining time budget")
            time.sleep(delay - gap)
        self._last[host] = time.monotonic()

    def get_json(self, url: str, **kw: Any) -> Any:
        return self._request("GET", url, **kw)

    def post_json(self, url: str, body: Any, **kw: Any) -> Any:
        return self._request("POST", url, json=body, **kw)

    def get_text(self, url: str, **kw: Any) -> str:
        if not self.allowed(url):
            raise PermissionError(f"robots.txt disallows {url}")
        self._wait(url)
        return self._read("GET", url, **kw).decode("utf-8", errors="replace")

    def _request(self, method: str, url: str, **kw: Any) -> Any:
        if not self.allowed(url):
            raise PermissionError(f"robots.txt disallows {url}")
        self._wait(url)
        return json.loads(self._read(method, url, **kw))

    def _read(self, method: str, url: str, **kw: Any) -> bytes:
        """The response body, streamed with a size cap and the run's time budget."""
        left = self._remaining()
        if left is not None:
            kw.setdefault("timeout", min(TIMEOUT_S, left))
        with self.client.stream(method, url, **kw) as r:
            r.raise_for_status()
            body = bytearray()
            for chunk in r.iter_bytes():
                self._remaining()
                body.extend(chunk)
                if len(body) > MAX_RESPONSE_BYTES:
                    raise ValueError("response exceeds the size limit")
        return bytes(body)


# --- cleaning helpers (pure) -----------------------------------------------------------------

_TAG = re.compile(r"<[^>]+>")
_SPACE = re.compile(r"\s+")


def html_to_text(value: str | None) -> str:
    """Ad HTML (possibly entity-escaped twice, as Greenhouse sends it) to plain text."""
    text = html.unescape(html.unescape(value or ""))
    text = re.sub(r"<(br|/p|/li|/h\d|/div)[^>]*>", "\n", text, flags=re.I)
    text = _TAG.sub(" ", text)
    return _SPACE.sub(" ", text).strip()


def _placeholder(place: str) -> bool:
    return " ".join(re.findall(r"[a-z]+", place.lower())) in PLACEHOLDER_LOCATIONS


def in_malaysia(*places: str | None) -> bool:
    """The first supplied location is authoritative; later fields only fill a missing one.

    A bare "Remote" / "Anywhere" names no place, so it counts as missing too.
    """
    primary = next(
        (p.strip().lower() for p in places if p and p.strip() and not _placeholder(p)), ""
    )
    return primary in {"my", "mys"} or any(
        re.search(rf"(?<!\w){re.escape(place)}(?!\w)", primary) for place in MY_PLACES
    )


def remote_scope(*places: str | None) -> str:
    """Who may apply for a remote opening, if a Malaysian can; '' when they cannot."""
    blob = " ".join(p for p in places if p).lower()
    if not blob.strip():
        return "Worldwide"
    for word, label in (
        ("malaysia", "Malaysia"),
        ("southeast asia", "Southeast Asia"),
        ("apac", "APAC"),
        ("asia", "Asia"),
        ("worldwide", "Worldwide"),
        ("anywhere", "Worldwide"),
        ("global", "Worldwide"),
    ):
        if word in blob:
            return label
    return ""


def malaysia_relevance(location: str | None, work_mode: str | None, scope: str | None) -> str:
    """How a stored posting relates to Malaysia: in_malaysia, remote_explicit_my,
    remote_assumed_worldwide or not_malaysia.

    A remote ad naming another place is scoped there, whatever its stored scope says. A stored
    "Worldwide" may mean the feed named no region at all, so it is never a claim about Malaysia.
    """
    if in_malaysia(location):
        return "in_malaysia"
    place = (location or "").strip()
    if work_mode != "remote" or (place and not _placeholder(place)):
        return "not_malaysia"
    if scope in EXPLICIT_REMOTE_SCOPES:
        return "remote_explicit_my"
    return "remote_assumed_worldwide" if scope == "Worldwide" else "not_malaysia"


def iso_day(value: Any) -> date | None:
    """ISO-8601 strings, epoch seconds or epoch milliseconds to a date."""
    if value in (None, ""):
        return None
    try:
        if isinstance(value, (int, float)):
            seconds = value / 1000 if value > 10**11 else value
            return datetime.fromtimestamp(seconds, tz=UTC).date()
        text = str(value).strip()
        if text.isdigit():
            return iso_day(int(text))
        return datetime.fromisoformat(text.replace("Z", "+00:00")[:25]).date()
    except (ValueError, OverflowError, OSError):
        try:
            return datetime.strptime(str(value)[:16], "%a, %d %b %Y").date()
        except ValueError:
            return None


# --- employer applicant-tracking systems -----------------------------------------------------


def greenhouse(f: Fetcher, b: Board) -> Iterator[RawPosting]:
    api = f"https://boards-api.greenhouse.io/v1/boards/{quote(b.board)}/jobs?content=true"
    for j in f.get_json(api).get("jobs", []):
        place = (j.get("location") or {}).get("name", "")
        offices = " ".join(o.get("location") or o.get("name") or "" for o in j.get("offices", []))
        if not in_malaysia(place, offices):
            continue
        remote = "remote" in place.lower()
        yield RawPosting(
            source="greenhouse",
            board=b.board,
            source_id=str(j["id"]),
            employer=b.employer,
            title=j.get("title", "").strip(),
            url=j.get("absolute_url", ""),
            api_url=api,
            location=place,
            work_mode="remote" if remote else "onsite",
            remote_scope="Malaysia" if remote else "",
            posted_at=iso_day(j.get("first_published") or j.get("updated_at")),
            text=f"{j.get('title', '')}\n{html_to_text(j.get('content'))}",
        )


def lever(f: Fetcher, b: Board) -> Iterator[RawPosting]:
    api = f"https://api.lever.co/v0/postings/{quote(b.board)}?mode=json"
    for j in f.get_json(api):
        cats = j.get("categories") or {}
        places = cats.get("location") or ""
        if not in_malaysia(places, j.get("country")):
            continue
        lists = " ".join(
            f"{x.get('text', '')} {html_to_text(x.get('content'))}" for x in j.get("lists") or []
        )
        mode = {"remote": "remote", "hybrid": "hybrid"}.get(j.get("workplaceType", ""), "onsite")
        yield RawPosting(
            source="lever",
            board=b.board,
            source_id=j["id"],
            employer=b.employer,
            title=j.get("text", "").strip(),
            url=j.get("hostedUrl", ""),
            api_url=api,
            location=cats.get("location") or "",
            work_mode=mode,
            remote_scope="Malaysia" if mode == "remote" else "",
            employment_type=cats.get("commitment") or "",
            posted_at=iso_day(j.get("createdAt")),
            text=f"{j.get('text', '')}\n{j.get('descriptionPlain', '')}\n{lists}\n"
            f"{j.get('additionalPlain', '')}",
        )


def ashby(f: Fetcher, b: Board) -> Iterator[RawPosting]:
    api = f"https://api.ashbyhq.com/posting-api/job-board/{quote(b.board)}?includeCompensation=true"
    for j in f.get_json(api).get("jobs", []):
        if not j.get("isListed", True):
            continue
        address = ((j.get("address") or {}).get("postalAddress") or {}).get("addressCountry", "")
        secondary = " ".join((s.get("location") or "") for s in j.get("secondaryLocations") or [])
        if not in_malaysia(j.get("location"), secondary, address):
            continue
        mode = (j.get("workplaceType") or "").lower()
        mode = (
            mode if mode in ("remote", "hybrid") else ("remote" if j.get("isRemote") else "onsite")
        )
        yield RawPosting(
            source="ashby",
            board=b.board,
            source_id=j.get("id") or j.get("jobUrl", ""),
            employer=b.employer,
            title=j.get("title", "").strip(),
            url=j.get("jobUrl") or j.get("applyUrl", ""),
            api_url=api,
            location=j.get("location") or "",
            work_mode=mode,
            remote_scope="Malaysia" if mode == "remote" else "",
            employment_type=j.get("employmentType") or "",
            posted_at=iso_day(j.get("publishedAt")),
            text=j.get("title", "")
            + "\n"
            + (j.get("descriptionPlain") or html_to_text(j.get("descriptionHtml"))),
        )


def smartrecruiters(f: Fetcher, b: Board) -> Iterator[RawPosting]:
    base = f"https://api.smartrecruiters.com/v1/companies/{quote(b.board)}/postings"
    offset = 0
    seen = 0
    while seen < MAX_PER_BOARD:
        page = f.get_json(base, params={"country": "my", "limit": 100, "offset": offset})
        items = page.get("content", [])
        if not items:
            break
        for item in items:
            if seen >= MAX_PER_BOARD:
                break
            seen += 1
            loc = item.get("location") or {}
            detail_url = f"{base}/{item['id']}"
            try:
                d = f.get_json(detail_url)
            except httpx.HTTPError:
                continue
            sections = (d.get("jobAd") or {}).get("sections") or {}
            body = " ".join(html_to_text((sections.get(k) or {}).get("text")) for k in sections)
            mode = "remote" if loc.get("remote") else ("hybrid" if loc.get("hybrid") else "onsite")
            yield RawPosting(
                source="smartrecruiters",
                board=b.board,
                source_id=str(item["id"]),
                employer=b.employer,
                title=item.get("name", "").strip(),
                url=d.get("postingUrl")
                or f"https://jobs.smartrecruiters.com/{b.board}/{item['id']}",
                api_url=base,
                location=loc.get("fullLocation") or loc.get("city") or "Malaysia",
                work_mode=mode,
                remote_scope="Malaysia" if mode == "remote" else "",
                employment_type=(item.get("typeOfEmployment") or {}).get("label", ""),
                experience_level=(item.get("experienceLevel") or {}).get("label", ""),
                posted_at=iso_day(item.get("releasedDate")),
                text=f"{item.get('name', '')}\n{body}",
            )
        offset += len(items)
        if offset >= int(page.get("totalFound") or 0):
            break


def workday(f: Fetcher, b: Board) -> Iterator[RawPosting]:
    """Workday career sites: the JSON search the public careers page itself uses."""
    api = f"https://{b.host}/wday/cxs/{b.board}/{b.site}/jobs"
    offset = 0
    seen = 0
    while seen < MAX_PER_BOARD:
        page = f.post_json(
            api, {"appliedFacets": {}, "limit": 20, "offset": offset, "searchText": "Malaysia"}
        )
        items = page.get("jobPostings", [])
        if not items:
            break
        for item in items:
            if seen >= MAX_PER_BOARD:
                break
            seen += 1
            path = item.get("externalPath", "")
            listed = item.get("locationsText") or ""
            if listed and "location" not in listed.lower() and not in_malaysia(listed, path):
                continue  # clearly elsewhere ("2 Locations" still needs the detail page)
            try:
                info = f.get_json(f"https://{b.host}/wday/cxs/{b.board}/{b.site}{path}")[
                    "jobPostingInfo"
                ]
            except (httpx.HTTPError, KeyError):
                continue
            places = [info.get("location") or "", *(info.get("additionalLocations") or [])]
            country = (info.get("country") or {}).get("descriptor", "")
            if not in_malaysia(country, *places):
                continue
            mode = "remote" if "remote" in " ".join(places).lower() else "onsite"
            yield RawPosting(
                source="workday",
                board=b.board,
                source_id=info.get("jobReqId") or info.get("id") or path,
                employer=b.employer,
                title=info.get("title", "").strip(),
                url=info.get("externalUrl") or f"https://{b.host}/{b.site}{path}",
                api_url=api,
                location=info.get("location") or country,
                work_mode=mode,
                remote_scope="Malaysia" if mode == "remote" else "",
                employment_type=info.get("timeType") or "",
                posted_at=iso_day(info.get("startDate")),
                text=f"{info.get('title', '')}\n{html_to_text(info.get('jobDescription'))}",
            )
        offset += len(items)
        if offset >= int(page.get("total") or 0):
            break


def jibe(f: Fetcher, b: Board) -> Iterator[RawPosting]:
    """Jibe (iCIMS) career sites: the JSON search behind the public careers page."""
    api = f"https://{b.host}/api/jobs"
    page_no = 1
    seen = 0
    while seen < MAX_PER_BOARD:
        page = f.get_json(api, params={"location": "Malaysia", "page": page_no, "limit": 100})
        items = page.get("jobs", [])
        if not items:
            break
        for wrapper in items:
            j = wrapper.get("data") or {}
            seen += 1
            if not in_malaysia(j.get("country"), j.get("city"), j.get("full_location")):
                continue
            slug = j.get("slug") or j.get("req_id")
            yield RawPosting(
                source="jibe",
                board=b.board,
                source_id=str(j.get("req_id") or slug),
                employer=b.employer,
                title=(j.get("title") or "").strip(),
                url=f"https://{b.host}/careers-home/jobs/{slug}",
                api_url=api,
                location=j.get("full_location") or j.get("city") or "Malaysia",
                employment_type=j.get("employment_type") or "",
                posted_at=iso_day(j.get("posted_date") or j.get("create_date")),
                text=f"{j.get('title', '')}\n{html_to_text(j.get('description'))}\n"
                f"{html_to_text(j.get('qualifications'))}\n{html_to_text(j.get('responsibilities'))}",
            )
        if page_no * 100 >= int(page.get("totalCount") or 0):
            break
        page_no += 1


# --- remote-job boards -----------------------------------------------------------------------


class IncompleteRead(RuntimeError):
    """A board yielded some results but could not complete the read."""


def himalayas(f: Fetcher, b: Board) -> Iterator[RawPosting]:
    """Himalayas: remote jobs whose location rules include Malaysia (or no restriction)."""
    api = "https://himalayas.app/jobs/api/search"
    seen: set[str] = set()
    today = date.today()
    for q in REMOTE_QUERIES:
        try:
            page = f.get_json(api, params={"q": q, "country": "Malaysia", "page": 1})
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                raise IncompleteRead("Himalayas rate limit; previous listings retained") from exc
            raise
        for j in page.get("jobs", []):
            guid = j.get("guid") or j.get("applicationLink", "")
            if guid in seen:
                continue
            seen.add(guid)
            countries = j.get("locationRestrictions") or []
            if countries and "Malaysia" not in countries:
                continue
            expires = iso_day(j.get("expiryDate"))
            if expires and expires < today:
                continue
            yield RawPosting(
                source="himalayas",
                board=b.board,
                source_id=guid,
                employer=j.get("companyName", ""),
                title=j.get("title", "").strip(),
                url=j.get("applicationLink", ""),
                api_url=api,
                location="Remote",
                work_mode="remote",
                remote_scope="Malaysia" if countries else "Worldwide",
                employment_type=j.get("employmentType") or "",
                experience_level=" ".join(j.get("seniority") or []),
                posted_at=iso_day(j.get("pubDate")),
                expires_at=expires,
                salary_min=j.get("minSalary"),
                salary_max=j.get("maxSalary"),
                salary_currency=j.get("currency") or "",
                salary_period=j.get("salaryPeriod") or "",
                text=j.get("title", "")
                + "\n"
                + html_to_text(j.get("description") or j.get("excerpt")),
            )


def jobicy(f: Fetcher, b: Board) -> Iterator[RawPosting]:
    api = "https://jobicy.com/api/v2/remote-jobs"
    for j in f.get_json(api, params={"count": 100, "geo": "apac"}).get("jobs", []):
        scope = remote_scope(j.get("jobGeo"))
        if not scope:
            continue
        yield RawPosting(
            source="jobicy",
            board=b.board,
            source_id=str(j.get("id")),
            employer=j.get("companyName", ""),
            title=html.unescape(j.get("jobTitle", "")).strip(),
            url=j.get("url", ""),
            api_url=api,
            location="Remote",
            work_mode="remote",
            remote_scope=scope,
            employment_type=", ".join(j.get("jobType") or []),
            experience_level=j.get("jobLevel") or "",
            posted_at=iso_day(j.get("pubDate")),
            salary_min=j.get("salaryMin") or j.get("annualSalaryMin"),
            salary_max=j.get("salaryMax") or j.get("annualSalaryMax"),
            salary_currency=j.get("salaryCurrency") or "",
            salary_period=j.get("salaryPeriod") or "",
            text=j.get("jobTitle", "")
            + "\n"
            + html_to_text(j.get("jobDescription") or j.get("jobExcerpt")),
        )


def remoteok(f: Fetcher, b: Board) -> Iterator[RawPosting]:
    """Remote OK requires a followed link to its job page and a mention of Remote OK."""
    api = "https://remoteok.com/api"
    for j in f.get_json(api):
        if not isinstance(j, dict) or "id" not in j:
            continue  # the first element is the legal notice
        scope = remote_scope(j.get("location"))
        if not scope:
            continue
        yield RawPosting(
            source="remoteok",
            board=b.board,
            source_id=str(j["id"]),
            employer=j.get("company", ""),
            title=html.unescape(j.get("position", "")).strip(),
            url=j.get("url") or f"https://remoteok.com/remote-jobs/{j['id']}",
            api_url=api,
            location="Remote",
            work_mode="remote",
            remote_scope=scope,
            posted_at=iso_day(j.get("date") or j.get("epoch")),
            salary_min=j.get("salary_min") or None,
            salary_max=j.get("salary_max") or None,
            salary_currency="USD" if j.get("salary_min") else "",
            salary_period="year" if j.get("salary_min") else "",
            text=f"{j.get('position', '')}\n{' '.join(j.get('tags') or [])}\n"
            f"{html_to_text(j.get('description'))}",
        )


def remotive(f: Fetcher, b: Board) -> Iterator[RawPosting]:
    api = "https://remotive.com/api/remote-jobs"
    for j in f.get_json(api).get("jobs", []):
        scope = remote_scope(j.get("candidate_required_location"))
        if not scope:
            continue
        yield RawPosting(
            source="remotive",
            board=b.board,
            source_id=str(j["id"]),
            employer=j.get("company_name", ""),
            title=j.get("title", "").strip(),
            url=j.get("url", ""),
            api_url=api,
            location="Remote",
            work_mode="remote",
            remote_scope=scope,
            employment_type=j.get("job_type") or "",
            posted_at=iso_day(j.get("publication_date")),
            text=f"{j.get('title', '')}\n{' '.join(j.get('tags') or [])}\n"
            f"{html_to_text(j.get('description'))}",
        )


# --- keyed aggregators (run only with a key in the environment) ------------------------------


class MissingKey(RuntimeError):
    """The board needs an API key that is not configured; it is skipped, not failed."""


def careerjet(f: Fetcher, b: Board) -> Iterator[RawPosting]:
    """Careerjet publisher API v4 (Basic auth with the key; en_MY locale)."""
    key = os.environ.get("CAREERJET_API_KEY", "")
    if not key:
        raise MissingKey("CAREERJET_API_KEY")
    api = "https://search.api.careerjet.net/v4/query"
    for q in REMOTE_QUERIES:
        page = f.get_json(
            api,
            auth=(key, ""),
            params={
                "keywords": q,
                "locale_code": os.environ.get("CAREERJET_LOCALE", "en_MY"),
                "page_size": 50,
                "sort": "date",
                "user_ip": "127.0.0.1",
                "user_agent": USER_AGENT,
            },
        )
        for j in page.get("jobs", []):
            yield RawPosting(
                source="careerjet",
                board=b.board,
                source_id=j.get("url", ""),
                employer=j.get("company") or "",
                title=(j.get("title") or "").strip(),
                url=j.get("url", ""),
                api_url=api,
                location=j.get("locations") or "Malaysia",
                posted_at=iso_day(j.get("date")),
                salary_min=j.get("salary_min"),
                salary_max=j.get("salary_max"),
                salary_currency=j.get("salary_currency_code") or "",
                salary_period={"Y": "year", "M": "month", "W": "week", "D": "day", "H": "hour"}.get(
                    j.get("salary_type") or "", ""
                ),
                text=f"{j.get('title', '')}\n{html_to_text(j.get('description'))}",
            )


def jooble(f: Fetcher, b: Board) -> Iterator[RawPosting]:
    key = os.environ.get("JOOBLE_API_KEY", "")
    if not key:
        raise MissingKey("JOOBLE_API_KEY")
    api = f"https://jooble.org/api/{key}"
    for q in REMOTE_QUERIES:
        page = f.post_json(api, {"keywords": q, "location": "Malaysia"})
        for j in page.get("jobs", []):
            if not in_malaysia(j.get("location")):
                continue
            yield RawPosting(
                source="jooble",
                board=b.board,
                source_id=str(j.get("id") or j.get("link")),
                employer=j.get("company") or "",
                title=html_to_text(j.get("title")),
                url=j.get("link", ""),
                api_url="https://jooble.org/api/",  # never store the key
                location=j.get("location") or "Malaysia",
                employment_type=j.get("type") or "",
                posted_at=iso_day(j.get("updated")),
                text=f"{j.get('title', '')}\n{html_to_text(j.get('snippet'))}",
            )


def web3career(f: Fetcher, b: Board) -> Iterator[RawPosting]:
    token = os.environ.get("WEB3_CAREER_TOKEN", "")
    if not token:
        raise MissingKey("WEB3_CAREER_TOKEN")
    api = "https://web3.career/api/v1"
    body = f.get_json(api, params={"token": token, "remote": "true", "limit": 100})
    rows = next((x for x in body if isinstance(x, list)), body) if isinstance(body, list) else []
    for j in rows:
        if not isinstance(j, dict) or not j.get("apply_url"):
            continue
        scope = remote_scope(j.get("location"), j.get("country"))
        if not scope:
            continue
        yield RawPosting(
            source="web3career",
            board=b.board,
            source_id=str(j.get("id") or j["apply_url"]),
            employer=j.get("company") or "",
            title=(j.get("title") or "").strip(),
            url=j["apply_url"],  # unchanged, as web3.career's terms require
            api_url=api,
            location="Remote",
            work_mode="remote",
            remote_scope=scope,
            posted_at=iso_day(j.get("date") or j.get("date_epoch")),
            text=f"{j.get('title', '')}\n{' '.join(j.get('tags') or [])}\n"
            f"{html_to_text(j.get('description'))}",
        )


CONNECTORS: dict[str, Callable[[Fetcher, Board], Iterator[RawPosting]]] = {
    "greenhouse": greenhouse,
    "lever": lever,
    "ashby": ashby,
    "smartrecruiters": smartrecruiters,
    "workday": workday,
    "jibe": jibe,
    "himalayas": himalayas,
    "jobicy": jobicy,
    "remoteok": remoteok,
    "remotive": remotive,
    "careerjet": careerjet,
    "jooble": jooble,
    "web3career": web3career,
}

# How each source is credited next to its openings (several boards require attribution).
SOURCE_NAMES: dict[str, str] = {
    "greenhouse": "Greenhouse job board",
    "lever": "Lever job board",
    "ashby": "Ashby job board",
    "smartrecruiters": "SmartRecruiters job board",
    "workday": "Workday careers site",
    "jibe": "Careers site",
    "himalayas": "Himalayas",
    "jobicy": "Jobicy",
    "remoteok": "Remote OK",
    "remotive": "Remotive",
    "careerjet": "Careerjet",
    "jooble": "Jooble",
    "web3career": "web3.career",
}
