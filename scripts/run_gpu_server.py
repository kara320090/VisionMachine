"""Launch one GPU worker on loopback or the encrypted Tailscale interface."""
import ipaddress
import os
from pathlib import Path

from dotenv import load_dotenv
import uvicorn

root = Path(__file__).resolve().parents[1]
load_dotenv(root / ".env")
host = os.environ.get("VM_HOST", "127.0.0.1")
address = ipaddress.ip_address(host)
if not (address.is_loopback or address in ipaddress.ip_network("100.64.0.0/10")):
    raise SystemExit("VM_HOST must be loopback or a Tailscale IPv4 address")
if len(os.environ.get("VM_API_KEY", "")) < 24:
    raise SystemExit("Set a random VM_API_KEY in the private .env first")
os.chdir(root)
os.umask(0o077)
if __name__ == "__main__":
    uvicorn.run("vm_server.main:app", host=host, port=int(os.environ.get("VM_PORT", "8000")),
                workers=1, limit_concurrency=8, proxy_headers=False)
