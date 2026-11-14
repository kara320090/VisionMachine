"""Bounded anonymous installation enrollment; never ship the server key in an APK."""
import base64
import hashlib
import hmac
import os
import secrets
import sqlite3
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Response
from vm_contracts.models import DeviceRegistrationRequest, DeviceRegistrationResult
from vm_server.settings import Settings

router = APIRouter()
_lock = threading.Lock()


@dataclass(frozen=True)
class Principal:
    # None is the pre-existing server administrator key, not an anonymous user.
    device_id: str | None


def failure(status, code, retry_after=None):
    return HTTPException(status_code=status, detail={"code": code},
        headers={"Retry-After": str(retry_after)} if retry_after else None)


def connect():
    folder = Settings.from_environment().storage_dir
    folder.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(folder / "rgb_devices.sqlite3", timeout=30)
    db.row_factory = sqlite3.Row
    db.execute("""CREATE TABLE IF NOT EXISTS devices (
        id TEXT PRIMARY KEY, proof_sha TEXT NOT NULL, nonce TEXT NOT NULL,
        token_sha TEXT UNIQUE NOT NULL, expires_at INTEGER NOT NULL,
        revoked INTEGER NOT NULL DEFAULT 0, created_at INTEGER NOT NULL)""")
    db.execute("""CREATE TABLE IF NOT EXISTS usage (
        identity TEXT NOT NULL, bucket INTEGER NOT NULL, count INTEGER NOT NULL,
        PRIMARY KEY(identity, bucket))""")
    return db


def _consume(db, identity, bucket, maximum, retry_after):
    row = db.execute("SELECT count FROM usage WHERE identity=? AND bucket=?", (identity, bucket)).fetchone()
    if row and row[0] >= maximum:
        raise failure(429, "RATE_LIMITED", retry_after)
    db.execute("INSERT INTO usage VALUES (?,?,1) ON CONFLICT(identity,bucket) DO UPDATE SET count=count+1",
               (identity, bucket))


def register_installation(payload):
    if os.environ.get("VM_DEVICE_ENROLLMENT_ENABLED") != "1":
        raise failure(404, "ENROLLMENT_DISABLED")
    seed = os.environ.get("VM_API_KEY", "")
    if not seed:
        raise failure(503, "SERVER_AUTH_NOT_CONFIGURED")
    now = int(time.time())
    identity = str(payload.installation_id)
    proof_sha = hashlib.sha256(payload.registration_secret.encode()).hexdigest()
    with _lock, connect() as db:
        db.execute("BEGIN IMMEDIATE")
        _consume(db, "enrollment", now // 60, 30, 60)
        db.execute("DELETE FROM usage WHERE identity='enrollment' AND bucket<?", (now // 60 - 5,))
        # Failed enrollment proofs also consume the public endpoint's limit.
        db.commit()
        db.execute("BEGIN IMMEDIATE")
        prior = db.execute("SELECT * FROM devices WHERE id=?", (identity,)).fetchone()
        if prior:
            if not hmac.compare_digest(prior["proof_sha"], proof_sha):
                raise failure(409, "DEVICE_ID_CONFLICT")
            if prior["revoked"]:
                raise failure(403, "DEVICE_REVOKED")
        elif db.execute("SELECT count(*) FROM devices").fetchone()[0] >= int(os.environ.get("VM_DEVICE_LIMIT", "100")):
            raise failure(503, "DEVICE_LIMIT_REACHED")
        fresh = prior is None or prior["expires_at"] <= now + 60
        nonce = secrets.token_hex(16) if fresh else prior["nonce"]
        expires = now + 30 * 24 * 3600 if fresh else prior["expires_at"]
        message = f"visionmachine-device-v1:{identity}:{payload.registration_secret}:{nonce}".encode()
        token = "vm_device_" + base64.urlsafe_b64encode(hmac.new(seed.encode(), message, hashlib.sha256).digest()).decode().rstrip("=")
        token_sha = hashlib.sha256(token.encode()).hexdigest()
        db.execute("""INSERT INTO devices(id,proof_sha,nonce,token_sha,expires_at,created_at) VALUES (?,?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET nonce=excluded.nonce, token_sha=excluded.token_sha, expires_at=excluded.expires_at""",
            (identity, proof_sha, nonce, token_sha, expires, now))
        db.commit()
    return {"schema_version": "0.1.0", "server_id": "visionmachine-4090", "installation_id": identity,
            "api_key": token, "expires_at": datetime.fromtimestamp(expires, timezone.utc).isoformat()}


def authenticate(value):
    seed = os.environ.get("VM_API_KEY", "")
    if seed and value and hmac.compare_digest(seed.encode(), value.encode()):
        return Principal(None)
    if not value or not value.startswith("vm_device_") or len(value) > 128:
        return None
    with connect() as db:
        row = db.execute("SELECT id, expires_at, revoked FROM devices WHERE token_sha=?",
                         (hashlib.sha256(value.encode()).hexdigest(),)).fetchone()
    if row and not row["revoked"] and row["expires_at"] > time.time():
        return Principal(row["id"])
    return None


def consume_request(principal):
    if principal.device_id is None:
        return
    now = int(time.time())
    with _lock, connect() as db:
        db.execute("BEGIN IMMEDIATE")
        _consume(db, principal.device_id, now // 3600, 120, 3600 - now % 3600)
        db.execute("DELETE FROM usage WHERE identity=? AND bucket<?", (principal.device_id, now // 3600 - 48))
        db.commit()


@router.post("/api/v1/devices/register", response_model=DeviceRegistrationResult)
def register(payload: DeviceRegistrationRequest, response: Response):
    response.headers["Cache-Control"] = "no-store"
    return register_installation(payload)
