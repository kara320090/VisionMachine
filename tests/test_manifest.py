import pytest

from vm_data.validate_manifest import validate_rows


def test_synthetic_data_requires_explicit_permission(manifest_rows):
    assert validate_rows(manifest_rows, allow_synthetic=True) == []
    assert any("SYNTHETIC_FORBIDDEN" in error for error in validate_rows(manifest_rows))
    assert any("SYNTHETIC_FORBIDDEN" in error for error in validate_rows(manifest_rows, allow_synthetic=True, final=True))


@pytest.mark.parametrize("field", ["subject_id", "batch_id", "duplicate_group_id", "image_sha256"])
def test_related_data_cannot_cross_splits(manifest_rows, field):
    value = manifest_rows[0][field] or "fixture-duplicate-group"
    manifest_rows[0][field] = manifest_rows[1][field] = value
    errors = validate_rows(manifest_rows, allow_synthetic=True)
    assert any("SPLIT_LEAKAGE" in error for error in errors)


def test_fruits_linked_to_parent_plant_cannot_cross_splits(manifest_rows):
    manifest_rows[1]["parent_plant_id"] = manifest_rows[0]["subject_id"]
    assert any("SPLIT_LEAKAGE" in error for error in validate_rows(manifest_rows, allow_synthetic=True))


def test_transitive_relationship_through_unassigned_sample(manifest_rows):
    manifest_rows[1]["split"] = "unassigned"
    manifest_rows[1]["parent_plant_id"] = manifest_rows[0]["subject_id"]
    manifest_rows[1]["batch_id"] = manifest_rows[2]["batch_id"]
    assert any("SPLIT_LEAKAGE" in error for error in validate_rows(manifest_rows, allow_synthetic=True))


@pytest.mark.parametrize("path", ["../private/x.jpg", "/x.jpg", "C:/x.jpg", "raw\\x.jpg", "."])
def test_unsafe_paths_rejected(manifest_rows, path):
    manifest_rows[0]["image_relpath"] = path
    assert any("UNSAFE_IMAGE_PATH" in error for error in validate_rows(manifest_rows, allow_synthetic=True))


@pytest.mark.parametrize("field", ["sample_id", "inspection_id"])
def test_duplicate_ids_rejected(manifest_rows, field):
    manifest_rows[1][field] = manifest_rows[0][field]
    assert any(f"DUPLICATE_{field}" in error for error in validate_rows(manifest_rows, allow_synthetic=True))


def test_uuid_case_does_not_hide_duplicate(manifest_rows):
    manifest_rows[0]["inspection_id"] = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    manifest_rows[1]["inspection_id"] = manifest_rows[0]["inspection_id"].upper()
    assert any("DUPLICATE_inspection_id" in error for error in validate_rows(manifest_rows, allow_synthetic=True))


def test_missing_column_is_rejected(manifest_rows):
    del manifest_rows[0]["subject_id"]
    assert any("MISSING_COLUMNS" in error for error in validate_rows(manifest_rows, allow_synthetic=True))


def test_malformed_csv_row_reports_errors_without_crashing(manifest_rows):
    manifest_rows[0]["split"] = ["train", "test"]
    manifest_rows[1][None] = ["unexpected", "values"]
    errors = validate_rows(manifest_rows, allow_synthetic=True)
    assert any("INVALID_CSV_ROW" in error for error in errors)
    assert any("UNEXPECTED_COLUMNS" in error for error in errors)


def test_final_rejects_incomplete_annotations(manifest_rows):
    manifest_rows[0].update(split="unassigned", label="unlabeled", label_basis="", license_status="pending")
    errors = validate_rows(manifest_rows, final=True)
    assert any("UNASSIGNED_SPLIT" in error for error in errors)
    assert any("LABEL_NOT_READY" in error for error in errors)
    assert any("LICENSE_NOT_APPROVED" in error for error in errors)


def test_complete_real_format_passes_structure_check_only(manifest_rows):
    # Still fabricated unit-test rows. Approval/real are fields, not verified facts.
    for row in manifest_rows:
        row.update(source_kind="self_collected", license_status="approved")
    assert validate_rows(manifest_rows, final=True) == []


def test_empty_manifest_rejected():
    assert validate_rows([]) == ["EMPTY_MANIFEST"]
