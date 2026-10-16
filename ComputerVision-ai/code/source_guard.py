"""Enforce confirmed source corrections independently of proposed labels."""
from pathlib import Path
from common import read_csv, digest


def correction_digest(root):
    path = Path(root) / 'review' / 'confirmed_crop_source_conflicts.csv'
    return digest(path) if path.exists() else None


def validate_source_corrections(root, rows):
    path = Path(root) / 'review' / 'confirmed_crop_source_conflicts.csv'
    if not path.exists():
        return
    corrections = read_csv(path)
    by_id = {r['image_id']: r for r in corrections}
    by_sha = {r['local_sha256']: r for r in corrections}
    for row in rows:
        evidence = by_id.get(row['image_id']) or by_sha.get(row['sha256'])
        if evidence and row['crop'] != evidence['source_crop']:
            raise ValueError('Confirmed source crop conflict: '
                             f"{row['image_id']} is {evidence['source_crop']}, "
                             f"not {row['crop']}. Evidence: {evidence['evidence']}")
