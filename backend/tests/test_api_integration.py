import json
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import init_db

init_db()
client = TestClient(app)

def test_api_health_endpoint():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["project"] == "data-quality-auditor-alan-vo"

def test_api_unauthenticated_request_rejected():
    resp = client.get("/api/datasets")
    assert resp.status_code == 401
    assert "Authorization" in resp.json().get("detail", "") or resp.status_code == 401

def test_api_demo_token_and_me():
    # 1. Obtain demo analyst token
    resp = client.post("/api/auth/demo-token?role=analyst")
    assert resp.status_code == 200
    token_data = resp.json()
    token = token_data["access_token"]
    assert token

    # 2. Check /api/auth/me with Bearer token
    headers = {"Authorization": f"Bearer {token}"}
    me_resp = client.get("/api/auth/me", headers=headers)
    assert me_resp.status_code == 200
    user_info = me_resp.json()
    assert user_info["username"] == "demo-analyst"
    assert "analyst" in user_info["roles"]

def test_api_dataset_lifecycle_and_audit_workflow():
    # Obtain analyst token
    t_resp = client.post("/api/auth/demo-token?role=analyst")
    token = t_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Ingest CSV dataset
    csv_payload = {
        "name": "Production Metrics",
        "file_type": "csv",
        "content": "service_id,latency_ms,error_rate,owner_email\nsrv-1,45.2,0.01,ops1@company.com\nsrv-2,50.1,,ops2@company.com\nsrv-3,950.0,0.05,ops3@company.com\nsrv-1,45.2,0.01,ops1@company.com\n",
    }
    create_resp = client.post("/api/datasets", json=csv_payload, headers=headers)
    assert create_resp.status_code == 201
    dataset = create_resp.json()
    dataset_id = dataset["id"]
    assert dataset["record_count"] == 4
    assert dataset["column_count"] == 4

    # 2. Ingest Baseline dataset for drift
    base_payload = {
        "name": "Baseline Metrics",
        "file_type": "csv",
        "content": "service_id,latency_ms,error_rate\nsrv-1,42.0,0.01\nsrv-2,44.0,0.01\nsrv-3,46.0,0.02\n",
    }
    base_resp = client.post("/api/datasets", json=base_payload, headers=headers)
    assert base_resp.status_code == 201
    baseline_id = base_resp.json()["id"]

    # 3. Run Quality Audit
    audit_req = {"dataset_id": dataset_id, "include_llm_advisory": False}
    audit_resp = client.post("/api/audits", json=audit_req, headers=headers)
    assert audit_resp.status_code == 201
    audit_run = audit_resp.json()
    audit_id = audit_run["id"]
    assert audit_run["overall_score"] > 0
    assert audit_run["scorecard"]["record_count"] == 4
    assert audit_run["scorecard"]["duplicates_count"] == 1

    # 4. Read Audit Details
    get_audit = client.get(f"/api/audits/{audit_id}", headers=headers)
    assert get_audit.status_code == 200
    assert get_audit.json()["id"] == audit_id

    # 5. Export Markdown Report
    export_resp = client.get(f"/api/audits/{audit_id}/export?format=markdown", headers=headers)
    assert export_resp.status_code == 200
    assert "Data Quality Audit Report" in export_resp.text

    # 6. Run Drift Analysis
    drift_req = {"dataset_id": dataset_id, "baseline_id": baseline_id, "include_llm_advisory": False}
    drift_resp = client.post("/api/drift", json=drift_req, headers=headers)
    assert drift_resp.status_code == 201
    drift_res = drift_resp.json()
    assert "owner_email" in drift_res["added_columns"]
    assert drift_res["drift_score"] > 0

    # 7. Generate Remediation Playbook
    playbook_resp = client.get(f"/api/remediation/playbook/{audit_id}", headers=headers)
    assert playbook_resp.status_code == 200
    playbook = playbook_resp.json()
    assert len(playbook["rules"]) > 0
    assert "clean_dataset" in playbook["full_script"]

    # 8. Test Role Denial on Delete: viewer/analyst cannot delete dataset
    del_resp = client.delete(f"/api/datasets/{dataset_id}", headers=headers)
    assert del_resp.status_code == 403

    # 9. Admin can delete dataset
    admin_token = client.post("/api/auth/demo-token?role=admin").json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    del_admin_resp = client.delete(f"/api/datasets/{dataset_id}", headers=admin_headers)
    assert del_admin_resp.status_code == 204

def test_api_audit_logs_list_and_get():
    """Test GET /api/audit-logs returns paginated audit log items with action, resource_type, user, and details."""
    # Obtain analyst token
    t_resp = client.post("/api/auth/demo-token?role=analyst")
    token = t_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create some audit log entries via the API (ingest dataset creates audit logs)
    csv_payload = {
        "name": "Test Audit Logs",
        "file_type": "csv",
        "content": "id,value\n1,100\n2,200\n",
    }
    create_resp = client.post("/api/datasets", json=csv_payload, headers=headers)
    assert create_resp.status_code == 201
    dataset_id = create_resp.json()["id"]

    # Run audit to create more audit logs
    audit_req = {"dataset_id": dataset_id, "include_llm_advisory": False}
    audit_resp = client.post("/api/audits", json=audit_req, headers=headers)
    assert audit_resp.status_code == 201

    # 1. List audit logs (default pagination)
    list_resp = client.get("/api/audit-logs", headers=headers)
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert "items" in list_data
    assert "total" in list_data
    assert "page" in list_data
    assert "page_size" in list_data
    assert list_data["page"] == 1
    assert list_data["page_size"] == 20
    assert list_data["total"] >= 2  # at least dataset create + audit run
    assert len(list_data["items"]) >= 2

    # Verify each item has required fields
    for item in list_data["items"]:
        assert "id" in item
        assert "action" in item
        assert "resource_type" in item
        assert "resource_id" in item
        assert "user_id" in item
        assert "user_role" in item
        assert "details" in item
        assert isinstance(item["details"], dict)
        assert "created_at" in item

    # 2. Test filtering by action
    filter_resp = client.get("/api/audit-logs?action=create", headers=headers)
    assert filter_resp.status_code == 200
    filter_data = filter_resp.json()
    for item in filter_data["items"]:
        assert item["action"] == "create"

    # 3. Test filtering by resource_type
    filter_resp2 = client.get("/api/audit-logs?resource_type=dataset", headers=headers)
    assert filter_resp2.status_code == 200
    filter_data2 = filter_resp2.json()
    for item in filter_data2["items"]:
        assert item["resource_type"] == "dataset"

    # 4. Test filtering by user_id
    filter_resp3 = client.get("/api/audit-logs?user_id=demo-analyst", headers=headers)
    assert filter_resp3.status_code == 200
    filter_data3 = filter_resp3.json()
    for item in filter_data3["items"]:
        assert item["user_id"] == "demo-analyst"

    # 5. Test pagination
    page2_resp = client.get("/api/audit-logs?page=2&page_size=1", headers=headers)
    assert page2_resp.status_code == 200
    page2_data = page2_resp.json()
    assert page2_data["page"] == 2
    assert page2_data["page_size"] == 1
    assert len(page2_data["items"]) <= 1

    # 6. Test GET single audit log
    first_log_id = list_data["items"][0]["id"]
    get_resp = client.get(f"/api/audit-logs/{first_log_id}", headers=headers)
    assert get_resp.status_code == 200
    log_item = get_resp.json()
    assert log_item["id"] == first_log_id
    assert "action" in log_item
    assert "resource_type" in log_item
    assert "resource_id" in log_item
    assert "user_id" in log_item
    assert "user_role" in log_item
    assert isinstance(log_item["details"], dict)
    assert "created_at" in log_item

    # 7. Test GET non-existent audit log returns 404
    fake_id = "00000000-0000-0000-0000-000000000000"
    not_found_resp = client.get(f"/api/audit-logs/{fake_id}", headers=headers)
    assert not_found_resp.status_code == 404

    # 8. Test unauthenticated access rejected
    unauth_resp = client.get("/api/audit-logs")
    assert unauth_resp.status_code == 401

def test_api_audit_logs_viewer_access():
    """Authenticated users with viewer role can list audit log entries."""
    t_resp = client.post("/api/auth/demo-token?role=viewer")
    token = t_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    list_resp = client.get("/api/audit-logs", headers=headers)
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert "items" in list_data
    assert "total" in list_data
