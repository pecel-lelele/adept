"""count_mentions sends every sentence in one encode call (one remote job series)."""

from __future__ import annotations

from collections.abc import Sequence

from pipelines.trends.arxiv_ingest import count_mentions

SKILL_A = [1.0, 0.0]
SKILL_B = [0.0, 1.0]


class FakeEncoder:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def encode(
        self, texts: Sequence[str], *, batch_size: int = 32, show_progress_bar: bool = False
    ) -> list[list[float]]:
        self.calls.append(list(texts))
        return [SKILL_A if "alpha" in t else SKILL_B for t in texts]


def test_one_encode_call_and_per_paper_counts() -> None:
    papers = [
        {"title": "Synthetic alpha paper", "abstract": "An alpha sentence here. Another one."},
        {"title": "Synthetic beta paper", "abstract": "Only beta content inside."},
        {"title": "", "abstract": ""},
    ]
    model = FakeEncoder()
    counts = count_mentions(papers, ["a", "b"], {"a": SKILL_A, "b": SKILL_B}, model)
    assert len(model.calls) == 1
    assert counts == {"a": 1, "b": 2}


def test_no_model_counts_nothing() -> None:
    papers = [{"title": "Synthetic alpha paper", "abstract": "An alpha sentence here."}]
    assert count_mentions(papers, ["a"], {"a": SKILL_A}, None) == {"a": 0}
