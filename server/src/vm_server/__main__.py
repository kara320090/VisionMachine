"""python -m vm_server init-db (explicit local setup, not a deployment)."""
import argparse
import json
import sqlite3

from vm_server.database import SchemaError, initialize_database
from vm_server.settings import Settings


def main() -> None:
    parser = argparse.ArgumentParser(description="VisionMachine local development tools")
    parser.add_argument("command", choices=["init-db"])
    args = parser.parse_args()
    try:
        settings = Settings.from_environment()
        version = initialize_database(settings.database_path)
        settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    except (ValueError, OSError, sqlite3.Error, SchemaError) as exc:
        parser.exit(1, f"Local setup failed: {exc}\n")
    print(json.dumps({
        "command": args.command,
        "schema_version": version,
        "database": str(settings.database_path),
        "uploads": str(settings.uploads_dir),
        "http_storage_implemented": False,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
