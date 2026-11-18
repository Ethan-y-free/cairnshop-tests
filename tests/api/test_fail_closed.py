import pytest

from api.models import ErrorResponse
from data.factories import idempotency_key
from tests.api.helpers import CHECKOUT_FLAG, wait_for_checkout_flag


@pytest.mark.api
@pytest.mark.requires_cairnkv
@pytest.mark.slow
def test_checkout_fails_closed_then_recovers(admin_client, new_customer, order_product):
    assert new_customer.add_to_cart(order_product.id, 1).status_code == 200

    try:
        disabled = admin_client.ops_config_put(CHECKOUT_FLAG, {"enabled": False})
        assert disabled.status_code == 200, disabled.text
        wait_for_checkout_flag(admin_client, False)

        response = new_customer.checkout(idempotency_key())

        assert response.status_code == 503, response.text
        error = ErrorResponse.model_validate(response.json())
        assert error.error.code == "checkout_disabled"
    finally:
        restored = admin_client.ops_config_put(CHECKOUT_FLAG, {"enabled": True})
        assert restored.status_code == 200, restored.text
        wait_for_checkout_flag(admin_client, True)

    # 购物车在 503 时没有被清空，恢复配置后可以正常下单。
    recovered = new_customer.checkout(idempotency_key())

    assert recovered.status_code == 201, recovered.text
