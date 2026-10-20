from pipelines.guardrails import check_links


def test_collects_course_and_evidence_urls() -> None:
    urls = check_links.collect_urls()
    assert any("learn.microsoft.com" in u for u in urls)
    assert any("unstats.un.org/sdgs/metadata" in u for u in urls)
    assert all(u.startswith("https://") for u in urls)


def test_broken_flags_errors_and_unreachable_but_not_bot_walls() -> None:
    codes = {"ok": 200, "gone": 404, "wall": 403, "down": None}
    result = check_links.broken(codes, check=lambda u: codes[u])
    assert result == [("gone", 404), ("down", None)]
