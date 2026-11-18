import pytest

from api.models import ErrorResponse
from data.factories import random_ip


@pytest.mark.api
def test_login_rate_limit_returns_429(api_factory):
    # 固定一个只属于本用例的 IP，前 5 次 401，第 6 次应被限流。
    api = api_factory(xff=random_ip())

    for _ in range(5):
        response = api.login("nobody@example.com", "wrong-password")
        assert response.status_code == 401, response.text

    response = api.login("nobody@example.com", "wrong-password")

    assert response.status_code == 429, response.text
    assert response.headers.get("Retry-After") == "60"
    error = ErrorResponse.model_validate(response.json())
    assert error.error.code == "rate_limited"
