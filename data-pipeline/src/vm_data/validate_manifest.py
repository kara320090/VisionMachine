"""Metadata and split-leakage validator; does not inspect photos or verify licenses."""
import argparse, csv, json, re
from pathlib import Path, PurePosixPath
from uuid import UUID
from vm_contracts.models import CROP_CODES

COLUMNS = ["sample_id", "inspection_id", "subject_id", "parent_plant_id", "batch_id",
           "duplicate_group_id", "crop_code", "image_relpath", "image_sha256", "split",
           "source_kind", "label", "label_basis", "license_status"]

def validate_rows(rows, *, allow_synthetic=False, final=False):
    errors = []
    if not rows:
        return ["EMPTY_MANIFEST"]
    parent = list(range(len(rows)))
    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    def union(i,j):
        parent[root(i)] = root(j)
    seen_ids = {"sample_id": set(), "inspection_id": set()}
    groups = {}
    checked_rows = []
    for i,row in enumerate(rows):
        tag = f"row {i+2}"
        missing = set(COLUMNS)-set(row)
        if missing:
            errors.append(f"{tag}: MISSING_COLUMNS {','.join(sorted(missing))}")
            continue
        if set(row)-set(COLUMNS):
            errors.append(f"{tag}: UNEXPECTED_COLUMNS")
        if any(not isinstance(v,str) for v in row.values()):
            errors.append(f"{tag}: INVALID_CSV_ROW")
            continue
        checked_rows.append(i)
        for field in ["sample_id","inspection_id","subject_id","batch_id","crop_code","image_relpath","image_sha256","split","source_kind","label","license_status"]:
            if not row[field].strip():
                errors.append(f"{tag}: EMPTY_{field}")
        for field in seen_ids:
            value = row[field]
            if field == "inspection_id":
                try:
                    value = str(UUID(value))
                except ValueError:
                    pass
            if value in seen_ids[field]:
                errors.append(f"{tag}: DUPLICATE_{field}")
            seen_ids[field].add(value)
        for field in ["sample_id","subject_id","parent_plant_id","batch_id","duplicate_group_id"]:
            if row[field] and not re.fullmatch(r"[A-Za-z0-9_-]{1,80}",row[field]):
                errors.append(f"{tag}: INVALID_{field}")
        try:
            UUID(row["inspection_id"])
        except ValueError:
            errors.append(f"{tag}: INVALID_inspection_id")
        if row["crop_code"] not in CROP_CODES:
            errors.append(f"{tag}: UNKNOWN_CROP")
        path = row["image_relpath"]
        if not PurePosixPath(path).name or PurePosixPath(path).is_absolute() or '..' in PurePosixPath(path).parts or '\\' in path or ':' in path:
            errors.append(f"{tag}: UNSAFE_IMAGE_PATH")
        if not re.fullmatch(r"[0-9a-f]{64}",row["image_sha256"]):
            errors.append(f"{tag}: INVALID_IMAGE_HASH")
        if row["split"] not in {"train","val","test","unassigned"}:
            errors.append(f"{tag}: INVALID_SPLIT")
        if row["source_kind"] not in {"self_collected","public","synthetic"}:
            errors.append(f"{tag}: INVALID_SOURCE_KIND")
        if row["source_kind"] == "synthetic" and (not allow_synthetic or final):
            errors.append(f"{tag}: SYNTHETIC_FORBIDDEN")
        if row["label"] not in {"no_visible_abnormality","suspected_abnormality","uncertain","unlabeled"}:
            errors.append(f"{tag}: INVALID_LABEL")
        if row["license_status"] not in {"pending","approved","restricted"}:
            errors.append(f"{tag}: INVALID_LICENSE_STATUS")
        if final:
            if row["split"] == "unassigned": errors.append(f"{tag}: UNASSIGNED_SPLIT")
            if row["license_status"] != "approved": errors.append(f"{tag}: LICENSE_NOT_APPROVED")
            if row["label"] == "unlabeled" or not row["label_basis"].strip(): errors.append(f"{tag}: LABEL_NOT_READY")
        # Subject and parent share a namespace so fruit->plant links are transitive.
        tokens = [("entity",row["subject_id"]),("entity",row["parent_plant_id"]),
                  ("batch",row["batch_id"]),("duplicate",row["duplicate_group_id"]),
                  ("hash",row["image_sha256"])]
        for kind,value in tokens:
            if not value:
                continue
            key = (kind,value)
            if key in groups: union(i,groups[key])
            else: groups[key]=i
    split_groups = {}
    for i in checked_rows:
        row = rows[i]
        if row.get("split") in {"train","val","test"}:
            split_groups.setdefault(root(i),set()).add(row["split"])
    for splits in split_groups.values():
        if len(splits)>1:
            errors.append("SPLIT_LEAKAGE: linked subjects/batches/duplicates span " + ','.join(sorted(splits)))
    return errors

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--allow-synthetic", action="store_true", help="Fixtures only; cannot override --final")
    parser.add_argument("--final", action="store_true", help="Reject unassigned/unlabeled/unapproved/synthetic rows")
    args=parser.parse_args()
    try:
        with args.manifest.open(encoding="utf-8-sig", newline="") as f:
            rows=list(csv.DictReader(f))
        errors=validate_rows(rows,allow_synthetic=args.allow_synthetic,final=args.final)
    except (OSError, UnicodeError, csv.Error) as exc:
        parser.exit(2, f"Cannot read manifest: {exc}\n")
    print(json.dumps({"rows":len(rows),"valid":not errors,"errors":errors},ensure_ascii=False,indent=2))
    raise SystemExit(1 if errors else 0)

if __name__=="__main__": main()
