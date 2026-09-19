-- Local schema draft; not connected to the starter HTTP app yet.
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS inspections (
    inspection_id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    subject_type TEXT NOT NULL CHECK(subject_type IN ('plant','fruit')),
    parent_plant_id TEXT,
    batch_id TEXT NOT NULL,
    crop_code TEXT NOT NULL,
    captured_at_utc TEXT NOT NULL,
    received_at_utc TEXT NOT NULL,
    image_storage_key TEXT NOT NULL UNIQUE,
    image_sha256 TEXT NOT NULL CHECK(length(image_sha256)=64),
    request_sha256 TEXT NOT NULL CHECK(length(request_sha256)=64),
    metadata_json TEXT NOT NULL CHECK(json_valid(metadata_json)),
    is_mock INTEGER NOT NULL CHECK(is_mock IN (0,1)),
    deleted_at_utc TEXT
);
CREATE INDEX IF NOT EXISTS idx_inspections_owner_time ON inspections(owner_id, received_at_utc);
CREATE TABLE IF NOT EXISTS analyses (
    analysis_id TEXT PRIMARY KEY,
    inspection_id TEXT NOT NULL REFERENCES inspections(inspection_id) ON DELETE CASCADE,
    status TEXT NOT NULL CHECK(status IN ('pending_model','queued','processing','completed','failed')),
    model_version TEXT,
    model_mode TEXT CHECK(model_mode IN ('rgb','sensor','fusion')),
    result_json TEXT CHECK(result_json IS NULL OR json_valid(result_json)),
    created_at_utc TEXT NOT NULL,
    completed_at_utc TEXT
);
CREATE INDEX IF NOT EXISTS idx_analyses_inspection ON analyses(inspection_id);
