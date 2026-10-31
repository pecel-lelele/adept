"""Container entry points: serve the API (default) or, explicitly, migrate and seed.

    python src/docker/boot.py            # API only; never touches the schema or seed data
    python src/docker/boot.py migrate    # apply migrations, then load seeds (one-off service)

Starting the API must not migrate or seed: a restart would otherwise rewrite a database
nobody chose to change. Compose runs the one-off step as the `migrate` service under the
`setup` profile.
"""

from __future__ import annotations

import os
import subprocess
import sys


def migrate() -> None:
    subprocess.run([sys.executable, "src/db/migrate.py", "up"], check=True)
    subprocess.run([sys.executable, "src/db/seed.py"], check=True)


def serve() -> None:
    os.execvp(
        sys.executable,
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
    )


def main(argv: list[str]) -> int:
    if argv == ["migrate"]:
        migrate()
        return 0
    if argv:
        print("usage: boot.py [migrate]", file=sys.stderr)
        return 2
    serve()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
