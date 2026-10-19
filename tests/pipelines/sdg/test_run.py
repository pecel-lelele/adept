import csv
import json
from datetime import date
from pathlib import Path

import pytest

from pipelines.sdg import run

FIXTURE = Path(__file__).parent / "fixtures" / "goal_list_sample.json"
SEED = Path(__file__).resolve().parents[3] / "src" / "data" / "seed" / "sdg"


def _payload() -> list[dict[str, object]]:
    data: list[dict[str, object]] = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return data


def test_parse_keeps_all_17_goals_with_short_titles() -> None:
    goals, targets = run.parse(_payload())
    assert [g.id for g in goals] == list(range(1, 18))
    assert goals[3].short_title == "Quality Education"
    assert all(t.id.startswith(f"{t.goal}.") for t in targets)


def test_parse_rejects_incomplete_payload() -> None:
    with pytest.raises(ValueError, match="1..17"):
        run.parse(_payload()[:16])


def test_targets_sort_numerically_then_lettered() -> None:
    payload = [{"code": "1", "title": "g", "targets": [{"code": c, "title": "t"}
               for c in ("1.b", "1.10", "1.2", "1.a")]}]  # fmt: skip
    payload += [{"code": str(n), "title": "g", "targets": [{"code": f"{n}.1", "title": "t"}]}
                for n in range(2, 18)]  # fmt: skip
    _, targets = run.parse(payload)
    assert [t.id for t in targets if t.goal == 1] == ["1.2", "1.10", "1.a", "1.b"]


def test_main_writes_seed_csvs(tmp_path: Path) -> None:
    run.main(["--from-file", str(FIXTURE), "--out", str(tmp_path), "--retrieved", "2026-10-20"])
    with (tmp_path / "sdg_goals.csv").open(encoding="utf-8") as fh:
        goals = list(csv.DictReader(fh))
    assert len(goals) == 17 and goals[0]["retrieved_at"] == str(date(2026, 10, 20))


def test_committed_seed_has_the_full_official_list() -> None:
    with (SEED / "sdg_targets.csv").open(encoding="utf-8") as fh:
        targets = list(csv.DictReader(fh))
    assert len(targets) == 169
    assert {int(t["goal"]) for t in targets} == set(range(1, 18))


def test_light_endpoints_combine_into_the_parsed_shape() -> None:
    from app.features.sdg.sources import combine

    goals = [{"code": str(n), "title": f"Goal {n}"} for n in range(1, 18)]
    targets = [{"goal": str(n), "code": f"{n}.1", "title": f"Target {n}.1"} for n in range(1, 18)]
    parsed_goals, parsed_targets = run.parse(combine(goals, targets))
    assert len(parsed_goals) == 17 and [t.id for t in parsed_targets][:2] == ["1.1", "2.1"]
