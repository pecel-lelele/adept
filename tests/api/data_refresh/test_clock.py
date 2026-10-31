"""A scheduled trigger cannot report still-due failed work as a successful no-op."""

import pytest

from scripts import call_data_refresh


def test_cooldown_is_an_unfinished_refresh(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(call_data_refresh, "request", lambda *a, **k: {"status": "cooldown"})
    assert call_data_refresh.main() == 1


def test_only_current_data_is_a_successful_noop(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(call_data_refresh, "request", lambda *a, **k: {"status": "up_to_date"})
    assert call_data_refresh.main() == 0
