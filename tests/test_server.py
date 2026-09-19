from fastapi.testclient import TestClient

from vm_server.main import app

client = TestClient(app)


def test_health_and_capabilities_do_not_claim_a_trained_model():
    health = client.get("/healthz")
    assert health.status_code == 200
    assert health.json()["model_available"] is False
    capabilities = client.get("/v1/capabilities").json()
    assert capabilities["validated_diagnostic_crops"] == []
    assert len(capabilities["crop_catalog"]) == 8
    assert "image_upload" in capabilities["pending"]
    assert "metadata_validation" in capabilities["implemented"]


def test_validation_is_pending_not_a_fake_diagnosis(inspection):
    response = client.post("/v1/dev/validate-inspection", json=inspection)
    assert response.status_code == 200
    result = response.json()
    assert result["inspection_id"] == inspection["inspection_id"]
    assert result["status"] == "pending_model"
    assert result["outcome"] is None
    assert result["confidence"] is None
    assert result["origin"] == "none"
    assert result["is_mock_input"] is True
    assert set(result["warnings"]) == {"MODEL_NOT_AVAILABLE", "MOCK_DATA"}


def test_mismatched_measurement_returns_validation_error(inspection):
    inspection["sensor_packet"]["request_id"] = "22222222-2222-4222-8222-222222222222"
    response = client.post("/v1/dev/validate-inspection", json=inspection)
    assert response.status_code == 422


def test_upload_not_implemented_is_not_reported_as_success(inspection):
    assert client.post("/v1/inspections", json=inspection).status_code == 404
