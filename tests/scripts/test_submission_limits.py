"""The filled finalist templates stay within the organisers' word limits."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "scripts"))

from fill_submission_docx import word_count, word_limits  # noqa: E402

EXPECTED = {
    "docs/submission/submission-final-report.md": {
        "final-description": 250,
        "final-implementation": 300,
        "final-market": 250,
    },
    "docs/submission/submission-technical-declaration.md": {
        "technical-2.1": 200,
        "technical-4.3": 100,
        "technical-5": 100,
        "technical-6.1": 150,
        "technical-6.2": 150,
    },
}


class SubmissionLimitsTest(unittest.TestCase):
    def test_word_count_ignores_markdown_markers(self) -> None:
        self.assertEqual(word_count("> **Two** [words](https://example.com)\n> • more"), 3)

    def test_every_template_limit_is_marked_and_respected(self) -> None:
        for path, limits in EXPECTED.items():
            found = word_limits((ROOT / path).read_text("utf-8"))
            self.assertEqual({name: limit for name, _, limit in found}, limits, path)
            for name, words, limit in found:
                self.assertLessEqual(words, limit, f"{path}: {name}")


if __name__ == "__main__":
    unittest.main()
