"""Check a real loopback HTTP process; stop only the process started here."""
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, build_opener, ProxyHandler

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    base = f"http://127.0.0.1:{port}"
    opener = build_opener(ProxyHandler({}))
    with tempfile.TemporaryFile() as log:
        process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "vm_server.main:app", "--host", "127.0.0.1", "--port", str(port)],
            cwd=ROOT, stdout=log, stderr=log,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        try:
            deadline = time.monotonic() + 15
            while True:
                if process.poll() is not None:
                    raise RuntimeError("Smoke server exited before startup")
                try:
                    with opener.open(base + "/healthz", timeout=1) as response:
                        health = json.load(response)
                    break
                except (URLError, TimeoutError):
                    if time.monotonic() >= deadline:
                        raise RuntimeError("Smoke server startup timed out")
                    time.sleep(0.1)
            assert health["model_available"] is False
            with opener.open(base + "/v1/capabilities", timeout=3) as response:
                capabilities = json.load(response)
            assert capabilities["validated_diagnostic_crops"] == []
            assert "metadata_validation" in capabilities["implemented"]
            payload = (ROOT / "contracts/examples/inspection.synthetic.json").read_bytes()
            request = Request(base + "/v1/dev/validate-inspection", data=payload,
                              headers={"Content-Type": "application/json"}, method="POST")
            with opener.open(request, timeout=3) as response:
                result = json.load(response)
            assert result["status"] == "pending_model"
            assert result["is_mock_input"] is True
            assert result["outcome"] is None
            print("HTTP smoke passed: health, capabilities, synthetic validation; no model or photo storage")
        except BaseException:
            log.seek(0)
            sys.stderr.write(log.read().decode("utf-8", errors="replace"))
            raise
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)


if __name__ == "__main__":
    main()
