#!/usr/bin/env bash
set -euo pipefail
umask 077
cd "$(dirname "$0")/.."
gpu_status="$(nvidia-smi)"
printf '%s\n' "$gpu_status"
driver_cuda="$(printf '%s\n' "$gpu_status" | sed -n 's/.*CUDA Version: *\([0-9][0-9.]*\).*/\1/p' | head -n 1)"
if [ -z "$driver_cuda" ] || [ "$(printf '%s\n' 12.9 "$driver_cuda" | sort -V | head -n 1)" != 12.9 ]; then
  echo 'This locked CUDA 12.9 runtime needs a supporting NVIDIA driver. Check the ORT compatibility table.' >&2
  exit 1
fi
if [ ! -x .venv/bin/python ]; then
  "${VM_PYTHON:-python3.12}" -m venv .venv
fi
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -c server/gpu-requirements.lock.txt -r requirements.lock.txt -e '.[dev,gpu]'
if [ ! -f .env ]; then
  .venv/bin/python - <<'PY'
from pathlib import Path
import secrets
p=Path('.env')
p.write_text('VM_STORAGE_DIR=./storage\nVM_HOST=127.0.0.1\nVM_PORT=8000\nVM_API_KEY='+secrets.token_urlsafe(32)+'\n')
p.chmod(0o600)
PY
fi
.venv/bin/python -m pip check
.venv/bin/python scripts/check_gpu_runtime.py
echo "Set VM_HOST to the Tailscale address in .env, prepare the verified ONNX, then run: .venv/bin/python scripts/run_gpu_server.py"
