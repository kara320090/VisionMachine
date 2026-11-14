"""Enable only this VisionMachine clone's bounded installation enrollment."""
import argparse
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--enable", action="store_true", required=True)
    args = parser.parse_args()
    from dotenv import dotenv_values
    config = ROOT / ".env"
    if not (ROOT / "server/src/vm_server/devices.py").is_file() or not config.is_file():
        raise SystemExit("Run from the VisionMachine clone that already has its GPU .env configured.")
    if not dotenv_values(config).get("VM_API_KEY"):
        raise SystemExit("Existing VisionMachine server authentication must be configured first.")
    original = config.read_text(encoding="utf-8")
    backup_folder = ROOT / "storage/deployment-backups"
    backup_folder.mkdir(parents=True, exist_ok=True)
    backup = backup_folder / ("auto-connection-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".env")
    with backup.open("x", encoding="utf-8") as stream:
        os.chmod(backup, 0o600)
        stream.write(original)
    lines = [line for line in original.splitlines() if not line.startswith(("VM_DEVICE_ENROLLMENT_ENABLED=", "VM_DEVICE_LIMIT="))]
    lines += ["VM_DEVICE_ENROLLMENT_ENABLED=1", "VM_DEVICE_LIMIT=100"]
    temporary = config.with_suffix(".env.auto-connect-tmp")
    with temporary.open("x", encoding="utf-8") as stream:
        os.chmod(temporary, 0o600)
        stream.write("\n".join(lines) + "\n")
    temporary.replace(config)
    print("VisionMachine enrollment enabled (100 installations). Existing key and other services were preserved.")


if __name__ == "__main__":
    main()
