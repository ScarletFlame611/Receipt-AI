"""Тесты основных роутов: загрузка/CRUD чеков и аналитика."""
from __future__ import annotations


def _upload(client, headers, image_upload):
    return client.post("/receipts", headers=headers, files=image_upload())


# --------------------------------------------------------------------------
# Чеки
# --------------------------------------------------------------------------
def test_upload_receipt_runs_pipeline(client, auth_headers, image_upload):
    r = _upload(client, auth_headers, image_upload)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["merchant"] == "Пятёрочка"
    assert body["status"] == "ok"
    assert body["purchase_date"] == "2026-06-01"  # ISO-строка из пайплайна -> date
    assert len(body["items"]) == 1
    assert body["items"][0]["good"] == "молоко"


def test_upload_rejects_unauthenticated(client, image_upload):
    assert client.post("/receipts", files=image_upload()).status_code == 401


def test_upload_rejects_bad_extension(client, auth_headers):
    files = {"file": ("note.txt", b"not an image", "text/plain")}
    assert client.post("/receipts", headers=auth_headers, files=files).status_code == 415


def test_upload_rejects_empty_file(client, auth_headers):
    files = {"file": ("receipt.jpg", b"", "image/jpeg")}
    assert client.post("/receipts", headers=auth_headers, files=files).status_code == 400


def test_list_and_get_receipt(client, auth_headers, image_upload):
    rid = _upload(client, auth_headers, image_upload).json()["id"]
    listing = client.get("/receipts", headers=auth_headers).json()
    assert len(listing) == 1
    got = client.get(f"/receipts/{rid}", headers=auth_headers)
    assert got.status_code == 200
    assert got.json()["id"] == rid


def test_get_missing_receipt_404(client, auth_headers):
    assert client.get("/receipts/999", headers=auth_headers).status_code == 404


def test_update_receipt_fields(client, auth_headers, image_upload):
    rid = _upload(client, auth_headers, image_upload).json()["id"]
    r = client.put(f"/receipts/{rid}", headers=auth_headers, json={"merchant": "Магнит"})
    assert r.status_code == 200
    assert r.json()["merchant"] == "Магнит"


def test_review_replaces_items(client, auth_headers, image_upload):
    rid = _upload(client, auth_headers, image_upload).json()["id"]
    r = client.put(
        f"/receipts/{rid}/review",
        headers=auth_headers,
        json={
            "merchant": "Лента",
            "total": "99.00",
            "items": [
                {"name": "Хлеб", "price": "30.00"},
                {"name": "Сыр", "price": "69.00"},
            ],
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["merchant"] == "Лента"
    assert len(body["items"]) == 2  # старая позиция заменена двумя новыми
    names = {it["name"] for it in body["items"]}
    assert names == {"Хлеб", "Сыр"}


def test_delete_receipt(client, auth_headers, image_upload):
    rid = _upload(client, auth_headers, image_upload).json()["id"]
    assert client.delete(f"/receipts/{rid}", headers=auth_headers).status_code == 204
    assert client.get(f"/receipts/{rid}", headers=auth_headers).status_code == 404


# --------------------------------------------------------------------------
# Аналитика
# --------------------------------------------------------------------------
def test_summary_after_upload(client, auth_headers, image_upload):
    _upload(client, auth_headers, image_upload)
    body = client.get("/analytics/summary", headers=auth_headers).json()
    assert body["total"] == 123.45
    assert isinstance(body["by_category"], list)


def test_timeline_groups_by_month(client, auth_headers, image_upload):
    _upload(client, auth_headers, image_upload)
    timeline = client.get("/analytics/timeline", headers=auth_headers).json()
    assert {"period": "2026-06", "total": 123.45} in timeline


def test_top_merchants(client, auth_headers, image_upload):
    _upload(client, auth_headers, image_upload)
    top = client.get("/analytics/top-merchants", headers=auth_headers).json()
    assert top[0]["merchant"] == "Пятёрочка"
    assert top[0]["count"] == 1


def test_budgets_crud(client, auth_headers):
    created = client.post("/analytics/budgets", headers=auth_headers, json={"limit_amount": "5000"})
    assert created.status_code == 201
    bid = created.json()["id"]
    assert len(client.get("/analytics/budgets", headers=auth_headers).json()) == 1
    assert client.delete(f"/analytics/budgets/{bid}", headers=auth_headers).status_code == 204
    assert len(client.get("/analytics/budgets", headers=auth_headers).json()) == 0


def test_goals_crud(client, auth_headers):
    created = client.post(
        "/analytics/goals", headers=auth_headers,
        json={"title": "Отпуск", "target_amount": "100000"},
    )
    assert created.status_code == 201
    gid = created.json()["id"]
    updated = client.put(
        f"/analytics/goals/{gid}", headers=auth_headers, json={"current_amount": "5000"}
    )
    assert updated.status_code == 200
    assert float(updated.json()["current_amount"]) == 5000.0
    assert client.delete(f"/analytics/goals/{gid}", headers=auth_headers).status_code == 204


def test_analytics_requires_auth(client):
    assert client.get("/analytics/summary").status_code == 401


def test_categories_endpoint(client, auth_headers):
    r = client.get("/categories", headers=auth_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_categories_requires_auth(client):
    assert client.get("/categories").status_code == 401
