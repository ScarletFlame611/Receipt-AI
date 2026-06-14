"""Тесты аутентификации: регистрация, вход, профиль, сброс пароля, лимит."""
from __future__ import annotations

from src.db import models


def test_register_returns_user(client):
    r = client.post("/auth/register", json={"email": "a@b.com", "password": "secret123"})
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "a@b.com"
    assert body["is_admin"] is False
    assert body["is_active"] is True
    assert "password_hash" not in body  # хеш наружу не утекает


def test_register_duplicate_conflict(client):
    client.post("/auth/register", json={"email": "a@b.com", "password": "secret123"})
    r = client.post("/auth/register", json={"email": "a@b.com", "password": "other123"})
    assert r.status_code == 409


def test_login_success_returns_token(client):
    client.post("/auth/register", json={"email": "a@b.com", "password": "secret123"})
    r = client.post("/auth/login", data={"username": "a@b.com", "password": "secret123"})
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_wrong_password(client):
    client.post("/auth/register", json={"email": "a@b.com", "password": "secret123"})
    r = client.post("/auth/login", data={"username": "a@b.com", "password": "WRONG"})
    assert r.status_code == 401


def test_login_unknown_user(client):
    r = client.post("/auth/login", data={"username": "ghost@b.com", "password": "secret123"})
    assert r.status_code == 401


def test_me_requires_token(client):
    assert client.get("/auth/me").status_code == 401


def test_me_returns_current_user(client, auth_headers):
    r = client.get("/auth/me", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["email"] == "user@test.com"


def test_me_rejects_invalid_token(client):
    r = client.get("/auth/me", headers={"Authorization": "Bearer not.a.jwt"})
    assert r.status_code == 401


def test_logout_ok(client, auth_headers):
    assert client.post("/auth/logout", headers=auth_headers).status_code == 200


def test_inactive_user_blocked(client, make_user, db_session):
    headers = make_user("blockme@test.com")
    user = db_session.query(models.User).filter_by(email="blockme@test.com").one()
    user.is_active = False
    db_session.commit()
    assert client.get("/auth/me", headers=headers).status_code == 403


def test_password_reset_flow(client, db_session):
    client.post("/auth/register", json={"email": "a@b.com", "password": "secret123"})
    # запрос сброса — всегда 200, не раскрывает существование email
    assert client.post("/auth/password-reset/request", json={"email": "a@b.com"}).status_code == 200
    assert client.post("/auth/password-reset/request", json={"email": "ghost@b.com"}).status_code == 200

    token = db_session.query(models.PasswordResetToken).first().token
    r = client.post(
        "/auth/password-reset/confirm",
        json={"token": token, "new_password": "newpass123"},
    )
    assert r.status_code == 200
    # старый пароль больше не работает, новый — работает
    assert client.post("/auth/login", data={"username": "a@b.com", "password": "secret123"}).status_code == 401
    assert client.post("/auth/login", data={"username": "a@b.com", "password": "newpass123"}).status_code == 200


def test_password_reset_token_single_use(client, db_session):
    client.post("/auth/register", json={"email": "a@b.com", "password": "secret123"})
    client.post("/auth/password-reset/request", json={"email": "a@b.com"})
    token = db_session.query(models.PasswordResetToken).first().token
    client.post("/auth/password-reset/confirm", json={"token": token, "new_password": "newpass123"})
    # повторное использование того же токена отклоняется
    r = client.post("/auth/password-reset/confirm", json={"token": token, "new_password": "another123"})
    assert r.status_code == 400


def test_password_reset_invalid_token(client):
    r = client.post("/auth/password-reset/confirm", json={"token": "garbage", "new_password": "x"})
    assert r.status_code == 400


def test_login_rate_limited(client):
    client.post("/auth/register", json={"email": "a@b.com", "password": "secret123"})
    # 5 неудачных попыток исчерпывают лимит, 6-я отбивается 429
    for _ in range(5):
        assert client.post("/auth/login", data={"username": "a@b.com", "password": "WRONG"}).status_code == 401
    assert client.post("/auth/login", data={"username": "a@b.com", "password": "WRONG"}).status_code == 429
