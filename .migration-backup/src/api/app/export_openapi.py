"""Write the OpenAPI schema to a file: python -m app.export_openapi <path>."""

import json
import sys
from pathlib import Path

from app.main import app


def main(out: Path) -> None:
    schema = app.openapi()
    text = json.dumps(schema, indent=2, ensure_ascii=False) + "\n"
    out.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {out}")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("openapi.json"))
