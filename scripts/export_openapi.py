"""Generate the implemented HTTP contract only; planned routes stay in docs."""
import argparse
import json
from pathlib import Path

from vm_server.main import app


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    target = Path(__file__).resolve().parents[1] / "contracts" / "openapi.json"
    content = json.dumps(app.openapi(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.check:
        if not target.exists() or target.read_text(encoding="utf-8") != content:
            parser.exit(1, "Outdated OpenAPI: run python scripts/export_openapi.py\n")
        print("OpenAPI verified")
    else:
        target.write_text(content, encoding="utf-8")
        print("OpenAPI exported")


if __name__ == "__main__":
    main()
