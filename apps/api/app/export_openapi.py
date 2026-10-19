"""Write the OpenAPI schema to a file: python -m app.export_openapi <path>."""

import json
import sys
from pathlib import Path

from app.main import app


def main(out: Path) -> None:
    schema = app.openapi()
    out.write_text(json.dumps(schema, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("openapi.json"))
