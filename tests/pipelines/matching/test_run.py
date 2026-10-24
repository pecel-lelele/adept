from pytest import CaptureFixture

from pipelines.matching import run


def test_placeholder_runs(capsys: CaptureFixture[str]) -> None:
    run.main()
    assert "pipelines.matching" in capsys.readouterr().out
