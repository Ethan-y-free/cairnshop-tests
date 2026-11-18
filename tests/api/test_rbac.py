import pytest

from api.models import ErrorResponse


@pytest.mark.api
def test_anonymous_cannot_access_ops(anon):
    response = anon.ops_status()

    assert response.status_code == 401
    error = ErrorResponse.model_validate(response.json())
    assert error.error.code == "unauthorized"


@pytest.mark.api
def test_customer_cannot_access_ops(customer_client):
    response = customer_client.ops_status()

    assert response.status_code == 403
    error = ErrorResponse.model_validate(response.json())
    assert error.error.code == "forbidden"


@pytest.mark.api
def test_admin_can_access_ops_status(admin_client):
    response = admin_client.ops_status()

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["mysql_ok"] is True
    assert "config" in body
    assert "cairnkv" in body
