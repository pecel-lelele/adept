from pytest import CaptureFixture

from pipelines.trends import run


def test_placeholder_runs(capsys: CaptureFixture[str]) -> None:
    run.main()
    assert "pipelines.trends" in capsys.readouterr().out
