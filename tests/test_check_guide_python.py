from pathlib import Path

from scripts.check_guide_python import check_file


def test_check_file_accepts_valid_python_and_ignores_other_languages(tmp_path: Path) -> None:
    guide = tmp_path / "guide.md"
    guide.write_text(
        "```python\nvalue = 1\n```\n"
        "```javascript\nconst value = ;\n```\n"
        "~~~py\nprint(value)\n~~~\n",
        encoding="utf-8",
    )

    assert check_file(guide) == 0


def test_check_file_reports_python_syntax_errors_with_markdown_line(tmp_path: Path, capsys) -> None:
    guide = tmp_path / "guide.md"
    guide.write_text("Intro\n\n```python\nvalue =\n```\n", encoding="utf-8")

    assert check_file(guide) == 1
    assert f"{guide}:4: error:" in capsys.readouterr().err


def test_check_file_reports_unclosed_python_fence(tmp_path: Path, capsys) -> None:
    guide = tmp_path / "guide.md"
    guide.write_text("```python\nvalue = 1\n", encoding="utf-8")

    assert check_file(guide) == 1
    assert f"{guide}:1: error: unclosed Python code fence" in capsys.readouterr().err
