import pytest

from scripts.demo import require_local_development


@pytest.mark.parametrize(
    "target,environment",
    [
        ("https://adept-my.replit.app", "production"),
        ("http://localhost.attacker.test", "development"),
        ("http://127.0.0.1:8000", "production"),
    ],
)
def test_demo_mutations_refuse_production_or_external_targets(
    target: str, environment: str
) -> None:
    with pytest.raises(ValueError):
        require_local_development(target, environment)


def test_local_development_demo_target_is_explicit() -> None:
    require_local_development("http://127.0.0.1:18091", "development")
