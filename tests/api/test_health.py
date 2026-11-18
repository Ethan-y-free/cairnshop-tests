import pytest


@pytest.mark.api
def test_healthz_returns_ok(anon):
    response = anon.healthz()

    assert response.status_code == 200
    assert response.text.strip() == "ok"


@pytest.mark.api
def test_metrics_exposes_prometheus_counters(anon):
    response = anon.metrics()

    assert response.status_code == 200
    assert "cairnshop_http_requests_total" in response.text
    assert "cairnshop_http_responses_total" in response.text
    assert "cairnshop_checkouts_total" in response.text


@pytest.mark.api
@pytest.mark.requires_cairnkv
def test_readyz_requires_mysql_and_cairnkv(anon):
    response = anon.readyz()

    assert response.status_code == 200
    assert response.text.strip() == "ok"
