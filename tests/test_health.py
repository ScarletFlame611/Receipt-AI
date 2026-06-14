"""Тесты health-check: честно отражает готовность ML-пайплайна."""
from __future__ import annotations

import pytest

import src.api.dependencies as deps


class _StubPipeline:
    def process(self, image):
        return {}


@pytest.fixture
def reset_pipeline():
    """Гарантирует чистое состояние синглинга пайплайна вокруг теста."""
    saved = deps._pipeline
    deps._pipeline = None
    yield
    deps._pipeline = saved


def test_health_reports_loading_when_pipeline_absent(client, reset_pipeline):
    deps._pipeline = None
    r = client.get("/api/health")
    assert r.status_code == 503
    body = r.json()
    assert body["status"] == "loading"
    assert body["pipeline_loaded"] is False
    assert body["components"] == {}


def test_health_ok_when_pipeline_loaded(client, reset_pipeline):
    deps._pipeline = _StubPipeline()
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["pipeline_loaded"] is True
    assert "version" in body
