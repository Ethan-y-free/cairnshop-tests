import json
import uuid

import pytest

from api.models import ErrorResponse
from tests.api.helpers import wait_for_snapshot_key


def _key() -> str:
    return f"cairnshop/promos/qa-{uuid.uuid4().hex[:8]}"


def _value(percent: int = 5) -> dict:
    return {
        "id": "qa-promo",
        "name": "QA Promo",
        "type": "percent",
        "percent": percent,
        "threshold_cents": 0,
        "enabled": False,
        "priority": 1,
    }


@pytest.mark.api
@pytest.mark.requires_cairnkv
def test_config_update_and_read(admin_client):
    key = _key()

    response = admin_client.ops_config_put(key, _value())

    assert response.status_code == 200, response.text
    document = response.json()
    assert document["version"] == 1
    assert document["updated_by"]
    assert document["percent"] == 5

    latest = admin_client.ops_config_get(key)
    assert latest.status_code == 200, latest.text
    body = latest.json()
    assert body["key"] == key
    # /ops/config?key= 返回的是 CairnKV 中存储的原始 JSON 字符串。
    assert json.loads(body["value"])["percent"] == 5


@pytest.mark.api
@pytest.mark.requires_cairnkv
def test_config_history_and_rollback(admin_client):
    key = _key()
    assert admin_client.ops_config_put(key, _value(5)).status_code == 200
    assert admin_client.ops_config_put(key, _value(6)).status_code == 200

    history = admin_client.ops_config_history(key)

    assert history.status_code == 200, history.text
    body = history.json()
    assert body["key"] == key
    assert body["current"]["version"] == 2
    assert any(entry["version"] == 1 for entry in body["history"])

    rollback = admin_client.ops_config_rollback(key, 1)

    assert rollback.status_code == 200, rollback.text
    document = rollback.json()
    assert document["version"] == 3
    assert document["percent"] == 5

    latest = admin_client.ops_config_get(key)
    assert latest.status_code == 200
    assert json.loads(latest.json()["value"])["percent"] == 5


@pytest.mark.api
@pytest.mark.requires_cairnkv
def test_config_snapshot_refreshes_with_new_key(admin_client):
    key = _key()
    assert admin_client.ops_config_put(key, _value(7)).status_code == 200

    snapshot = wait_for_snapshot_key(admin_client, key)

    assert snapshot["percent"] == 7
    assert snapshot["version"] == 1


@pytest.mark.api
@pytest.mark.requires_cairnkv
def test_audit_contains_config_update(admin_client):
    key = _key()
    assert admin_client.ops_config_put(key, _value()).status_code == 200

    response = admin_client.ops_audit(limit=100)

    assert response.status_code == 200, response.text
    entries = response.json()["entries"]
    assert any(
        entry["action"] == "config.update" and entry["target_id"] == key
        for entry in entries
    )


@pytest.mark.api
@pytest.mark.requires_cairnkv
def test_config_rejects_invalid_key(admin_client):
    response = admin_client.ops_config_put("not-a-config-key", {"enabled": True})

    assert response.status_code == 400, response.text
    error = ErrorResponse.model_validate(response.json())
    assert error.error.code == "config_write_failed"


@pytest.mark.api
@pytest.mark.requires_cairnkv
def test_config_rejects_non_object_value(admin_client):
    response = admin_client.client.put(
        "/api/v1/ops/config",
        json={"key": _key(), "value": "not-an-object"},
    )

    assert response.status_code == 400, response.text
    error = ErrorResponse.model_validate(response.json())
    assert error.error.code == "invalid_argument"


@pytest.mark.api
@pytest.mark.requires_cairnkv
def test_history_requires_key(admin_client):
    response = admin_client.client.get("/api/v1/ops/config/history")

    assert response.status_code == 400, response.text
    error = ErrorResponse.model_validate(response.json())
    assert error.error.code == "invalid_argument"


@pytest.mark.api
@pytest.mark.requires_cairnkv
def test_rollback_unknown_version(admin_client):
    key = _key()
    assert admin_client.ops_config_put(key, _value()).status_code == 200

    response = admin_client.ops_config_rollback(key, 99)

    assert response.status_code == 404, response.text
    error = ErrorResponse.model_validate(response.json())
    assert error.error.code == "config_rollback_failed"


@pytest.mark.api
def test_config_write_requires_ops(customer_client):
    response = customer_client.ops_config_put(_key(), _value())

    assert response.status_code == 403
    error = ErrorResponse.model_validate(response.json())
    assert error.error.code == "forbidden"


@pytest.mark.api
def test_config_write_requires_auth(anon):
    response = anon.ops_config_put(_key(), _value())

    assert response.status_code == 401
    error = ErrorResponse.model_validate(response.json())
    assert error.error.code == "unauthorized"
