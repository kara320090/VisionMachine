"""Fixtures are fabricated metadata, never evidence of measured performance."""
import csv
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def inspection():
    return json.loads((ROOT / "contracts/examples/inspection.synthetic.json").read_text(encoding="utf-8"))


@pytest.fixture
def manifest_rows():
    with (ROOT / "data/examples/manifest.synthetic.csv").open(encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))
