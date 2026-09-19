"""One cross-platform command for the runnable foundation's checks."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMANDS = [
    ["-m", "pip", "check"],
    ["-m", "pytest", "-q"],
    ["scripts/export_contracts.py", "--check"],
    ["scripts/export_openapi.py", "--check"],
    ["-m", "vm_data.validate_manifest", "data/examples/manifest.synthetic.csv", "--allow-synthetic"],
    ["scripts/smoke_server.py"],
]


def main() -> None:
    for command in COMMANDS:
        print("Running: python " + " ".join(command), flush=True)
        result = subprocess.run([sys.executable, *command], cwd=ROOT)
        if result.returncode:
            raise SystemExit(result.returncode)
    print("Foundation checks passed. Hardware, Android and model evaluation are separate.")


if __name__ == "__main__":
    main()
