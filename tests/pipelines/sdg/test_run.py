from pytest import CaptureFixture

from pipelines.sdg import run


def test_placeholder_runs(capsys: CaptureFixture[str]) -> None:
    run.main()
    assert "pipelines.sdg" in capsys.readouterr().out
