"""Initialize the local demo database, then replace this process with the API."""

from __future__ import annotations

import os
import subprocess
import sys


def main() -> None:
    for script in ("src/db/migrate.py", "src/db/seed.py"):
        subprocess.run([sys.executable, script], check=True)
    os.execvp(
        sys.executable,
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
    )


if __name__ == "__main__":
    main()
