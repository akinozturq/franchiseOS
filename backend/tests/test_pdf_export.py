import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

from backend.app.core.security import create_access_token

client = TestClient(app)

def get_auth_token(username: str = "admin") -> str:
    return create_access_token({"sub": username})

def test_reconciliation_pdf_export():
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}", "X-Branch-Id": "1"}

    res = client.get("/api/v1/reconciliation/export-pdf?year=2026&month=1", headers=headers)
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert "attachment; filename=" in res.headers["content-disposition"]
    # PDF files start with binary marker '%PDF'
    assert res.content.startswith(b"%PDF")
    assert len(res.content) > 1000  # valid PDF with layout, tables, fonts

def test_bonus_pdf_export():
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}", "X-Branch-Id": "1"}

    res = client.get("/api/v1/bonus/export-pdf?year=2026&month=1", headers=headers)
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert "attachment; filename=" in res.headers["content-disposition"]
    assert res.content.startswith(b"%PDF")
    assert len(res.content) > 1000

def test_pdf_export_when_period_closed():
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}", "X-Branch-Id": "1"}

    # Close period 2026-02 if not closed
    client.post("/api/v1/period-closures", json={"year": 2026, "month": 2}, headers=headers)

    # Export PDF from closed period
    rec_res = client.get("/api/v1/reconciliation/export-pdf?year=2026&month=2", headers=headers)
    assert rec_res.status_code == 200
    assert rec_res.content.startswith(b"%PDF")

    bonus_res = client.get("/api/v1/bonus/export-pdf?year=2026&month=2", headers=headers)
    assert bonus_res.status_code == 200
    assert bonus_res.content.startswith(b"%PDF")
