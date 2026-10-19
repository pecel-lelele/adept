"""Security-relevant configuration that is easy to regress (review finding P1)."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_postgres_port_is_bound_to_localhost_by_default() -> None:
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    ports = re.findall(r'-\s*"([^"]+):5432"', compose)
    assert ports, "db service must publish 5432"
    for mapping in ports:
        assert mapping.startswith("${POSTGRES_BIND:-127.0.0.1}:"), mapping


def test_env_example_documents_bind_address() -> None:
    env = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "POSTGRES_BIND=127.0.0.1" in env
