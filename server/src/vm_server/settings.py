"""Local storage settings; importing this module never creates files."""
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    storage_dir: Path

    @classmethod
    def from_environment(cls) -> "Settings":
        value = os.environ.get("VM_STORAGE_DIR", "./storage").strip()
        if not value:
            raise ValueError("VM_STORAGE_DIR must not be empty")
        return cls(storage_dir=Path(value).expanduser().resolve())

    @property
    def database_path(self) -> Path:
        return self.storage_dir / "visionmachine.db"

    @property
    def uploads_dir(self) -> Path:
        return self.storage_dir / "uploads"
