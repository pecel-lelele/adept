from __future__ import annotations

import pytest

from app.core import refdata


def test_rows_rejects_unlisted_reference_table(monkeypatch: pytest.MonkeyPatch) -> None:
    def unexpected_connection() -> None:
        pytest.fail("unsupported tables must be rejected before opening a database connection")

    monkeypatch.setattr(refdata, "use_postgres", lambda: True)
    monkeypatch.setattr(refdata, "connection", unexpected_connection)

    with pytest.raises(ValueError, match="Unsupported reference-data table"):
        refdata.rows("taxonomy", "skills; DROP TABLE skills")
