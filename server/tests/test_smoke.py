"""Smoke test: app boots, healthz responds."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_root(client: TestClient):
    r = client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert "name" in body and "docs" in body


def test_healthz(client: TestClient):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_openapi(client: TestClient):
    r = client.get("/openapi.json")
    assert r.status_code == 200
    spec = r.json()
    # 验证关键路由已注册
    paths = spec["paths"]
    assert "/api/v1/dashboard/global-kpi" in paths
    assert "/api/v1/dashboard/heatmap" in paths
    assert "/api/v1/spots" in paths
    assert "/api/v1/comments" in paths
    assert "/api/v1/search/spots" in paths
    assert "/api/v1/geocode" in paths
