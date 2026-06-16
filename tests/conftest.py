from __future__ import annotations

import io
import os
from decimal import Decimal

os.environ["APP_ENV"] = "test"  # отключает прогрев пайплайна в lifespan

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from src.api.dependencies import get_pipeline
from src.api.main import app
from src.db import models
from src.db.base import Base, get_db


class FakePipeline:
    result = {
        "merchant": "Пятёрочка",
        "date": "2026-06-01",
        "total": Decimal("123.45"),
        "language": "ru",
        "receipt_type": "Продукты",
        "items": [
            {"name": "Молоко 3.2%", "good": "молоко", "brand": "Простоквашино"},
        ],
        "status": "ok",
    }

    def process(self, image):
        return dict(self.result)


@pytest.fixture
def db_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session_factory(db_engine):
    return sessionmaker(bind=db_engine, autoflush=False, autocommit=False)


@pytest.fixture
def db_session(session_factory):
    db = session_factory()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def _reset_rate_limit():
    from src.utils.ratelimit import login_limiter
    login_limiter._hits.clear()
    yield
    login_limiter._hits.clear()


@pytest.fixture
def client(session_factory):
    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_pipeline] = lambda: FakePipeline()
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def make_user(client, db_session):

    def _make(email="user@test.com", password="secret123", admin=False):
        client.post("/auth/register", json={"email": email, "password": password})
        if admin:
            user = db_session.query(models.User).filter_by(email=email).one()
            user.is_admin = True
            db_session.commit()
        resp = client.post(
            "/auth/login", data={"username": email, "password": password}
        )
        token = resp.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return _make


@pytest.fixture
def auth_headers(make_user):
    return make_user()


@pytest.fixture
def image_upload():

    def _make(name="receipt.jpg"):
        buf = io.BytesIO()
        Image.new("RGB", (40, 60), "white").save(buf, format="JPEG")
        buf.seek(0)
        return {"file": (name, buf, "image/jpeg")}

    return _make
