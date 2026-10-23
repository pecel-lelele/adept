"""F8 check (owner M3): every course URL and SDG evidence URL still resolves.

Run weekly by .github/workflows/data-sources.yml. Prints each broken link and exits 1 if any
is broken, so a dead course page or moved UN metadata file is noticed within a week.

    PYTHONPATH=src/api:src .venv/bin/python -m pipelines.guardrails.check_links
"""

from __future__ import annotations

import ssl
import sys
import urllib.error
import urllib.request
from collections.abc import Callable, Iterable

from app.core import seed

Probe = Callable[[str], int | None]


def collect_urls() -> list[str]:
    urls: set[str] = set()
    for row in seed.rows("courses", "courses"):
        urls.update(u for u in (row["url"], row.get("source_url", "")) if u.startswith("https://"))
    for table in ("role_sdg_map", "skill_sdg_map"):
        urls.update(r["evidence_url"] for r in seed.rows("sdg", table) if r.get("evidence_url"))
    return sorted(urls)


def probe(url: str) -> int | None:
    """HTTP status (HEAD, then GET if HEAD is refused), or None if unreachable."""
    ctx = ssl.create_default_context()
    for method in ("HEAD", "GET"):
        req = urllib.request.Request(url, method=method, headers={"User-Agent": "adept-links/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=30, context=ctx) as r:
                return int(r.status)
        except urllib.error.HTTPError as exc:
            if method == "HEAD" and exc.code in (403, 405):
                continue
            return int(exc.code)
        except (urllib.error.URLError, TimeoutError):
            return None
    return None


def broken(urls: Iterable[str], check: Probe = probe) -> list[tuple[str, int | None]]:
    # 403 usually means bot protection on a live page, not a dead link.
    return [(u, code) for u in urls if (code := check(u)) is None or code >= 400 and code != 403]


def main() -> int:
    urls = collect_urls()
    bad = broken(urls)
    for url, code in bad:
        print(f"BROKEN {code or 'unreachable'} {url}")
    print(f"checked {len(urls)} links, {len(bad)} broken")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
