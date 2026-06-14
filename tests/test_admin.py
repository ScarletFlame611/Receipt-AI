"""Тесты админских роутов: доступ, список, блокировка, метрики."""
from __future__ import annotations

from src.db import models


def test_admin_routes_forbidden_for_regular_user(client, auth_headers):
    assert client.get("/admin/users", headers=auth_headers).status_code == 403
    assert client.get("/admin/metrics", headers=auth_headers).status_code == 403


def test_admin_routes_require_auth(client):
    assert client.get("/admin/users").status_code == 401


def test_admin_lists_users(client, make_user):
    admin = make_user("admin@test.com", admin=True)
    make_user("u1@test.com")
    users = client.get("/admin/users", headers=admin).json()
    emails = {u["email"] for u in users}
    assert {"admin@test.com", "u1@test.com"} <= emails


def test_admin_block_and_unblock(client, make_user, db_session):
    admin = make_user("admin@test.com", admin=True)
    target = make_user("victim@test.com")
    uid = db_session.query(models.User).filter_by(email="victim@test.com").one().id

    # блокировка -> пользователь теряет доступ
    assert client.post(f"/admin/users/{uid}/block", headers=admin).status_code == 200
    assert client.get("/auth/me", headers=target).status_code == 403

    # разблокировка -> доступ восстановлен (новый токен после реактивации)
    assert client.post(f"/admin/users/{uid}/unblock", headers=admin).status_code == 200
    restored = make_user("victim@test.com")  # повторный логин
    assert client.get("/auth/me", headers=restored).status_code == 200


def test_admin_cannot_block_self(client, make_user, db_session):
    admin = make_user("admin@test.com", admin=True)
    uid = db_session.query(models.User).filter_by(email="admin@test.com").one().id
    assert client.post(f"/admin/users/{uid}/block", headers=admin).status_code == 400


def test_admin_block_missing_user_404(client, make_user):
    admin = make_user("admin@test.com", admin=True)
    assert client.post("/admin/users/9999/block", headers=admin).status_code == 404


def test_admin_metrics(client, make_user, auth_headers, image_upload):
    # обычный пользователь + один чек
    client.post("/receipts", headers=auth_headers, files=image_upload())
    admin = make_user("admin@test.com", admin=True)
    m = client.get("/admin/metrics", headers=admin).json()
    assert m["users_total"] == 2
    assert m["receipts_total"] == 1
    assert m["items_total"] == 1
