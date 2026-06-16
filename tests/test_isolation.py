"""Тесты изоляции данных по user_id"""
from __future__ import annotations


def _upload(client, headers, image_upload):
    return client.post("/receipts", headers=headers, files=image_upload())


def test_user_cannot_see_others_receipt(client, make_user, image_upload):
    alice = make_user("alice@test.com")
    bob = make_user("bob@test.com")
    rid = _upload(client, alice, image_upload).json()["id"]
    assert client.get("/receipts", headers=bob).json() == []
    assert client.get(f"/receipts/{rid}", headers=bob).status_code == 404


def test_user_cannot_modify_others_receipt(client, make_user, image_upload):
    alice = make_user("alice@test.com")
    bob = make_user("bob@test.com")
    rid = _upload(client, alice, image_upload).json()["id"]
    assert client.put(f"/receipts/{rid}", headers=bob, json={"merchant": "X"}).status_code == 404
    assert client.put(
        f"/receipts/{rid}/review", headers=bob, json={"items": []}
    ).status_code == 404
    assert client.delete(f"/receipts/{rid}", headers=bob).status_code == 404
    assert client.get(f"/receipts/{rid}", headers=alice).json()["merchant"] == "Пятёрочка"


def test_analytics_isolated(client, make_user, image_upload):
    alice = make_user("alice@test.com")
    bob = make_user("bob@test.com")
    _upload(client, alice, image_upload)
    assert client.get("/analytics/summary", headers=alice).json()["total"] == 123.45
    assert client.get("/analytics/summary", headers=bob).json()["total"] == 0.0


def test_budgets_and_goals_isolated(client, make_user):
    alice = make_user("alice@test.com")
    bob = make_user("bob@test.com")
    bid = client.post("/analytics/budgets", headers=alice, json={"limit_amount": "5000"}).json()["id"]
    gid = client.post(
        "/analytics/goals", headers=alice, json={"title": "Отпуск", "target_amount": "100000"}
    ).json()["id"]
    assert client.get("/analytics/budgets", headers=bob).json() == []
    assert client.get("/analytics/goals", headers=bob).json() == []
    assert client.delete(f"/analytics/budgets/{bid}", headers=bob).status_code == 404
    assert client.put(
        f"/analytics/goals/{gid}", headers=bob, json={"current_amount": "1"}
    ).status_code == 404
