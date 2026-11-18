import pytest

from api.models import ErrorResponse, Order
from data.factories import idempotency_key, product_payload


def _checkout_with_item(api, product, quantity: int = 1, key: str | None = None):
    add = api.add_to_cart(product.id, quantity)
    assert add.status_code == 200, add.text
    return api.checkout(key or idempotency_key())


@pytest.mark.api
def test_checkout_creates_pending_order(new_customer, order_product):
    response = _checkout_with_item(new_customer, order_product, quantity=2)

    assert response.status_code == 201, response.text
    order = Order.model_validate(response.json())
    assert order.status == "pending"
    assert order.order_no.startswith("CS")
    assert order.subtotal_cents == order_product.price_cents * 2
    assert order.total_cents <= order.subtotal_cents
    assert len(order.items) == 1
    assert order.items[0].product_id == order_product.id
    assert order.items[0].quantity == 2


@pytest.mark.api
def test_checkout_is_idempotent(new_customer, order_product):
    key = idempotency_key()
    first = _checkout_with_item(new_customer, order_product, 1, key)
    assert first.status_code == 201, first.text
    first_order = Order.model_validate(first.json())

    # 同一个 Idempotency-Key 重放：不重复扣库存，返回第一次的订单。
    second = new_customer.checkout(key)

    assert second.status_code == 201, second.text
    assert Order.model_validate(second.json()).order_no == first_order.order_no


@pytest.mark.api
def test_checkout_requires_idempotency_key(new_customer, order_product):
    assert new_customer.add_to_cart(order_product.id, 1).status_code == 200

    response = new_customer.client.post("/api/v1/orders")

    assert response.status_code == 400, response.text
    error = ErrorResponse.model_validate(response.json())
    assert error.error.code == "invalid_argument"


@pytest.mark.api
def test_checkout_empty_cart_returns_409(new_customer):
    response = new_customer.checkout(idempotency_key())

    assert response.status_code == 409, response.text
    error = ErrorResponse.model_validate(response.json())
    assert error.error.code == "cart_empty"


@pytest.mark.api
def test_checkout_requires_auth(anon):
    response = anon.checkout(idempotency_key())

    assert response.status_code == 401
    error = ErrorResponse.model_validate(response.json())
    assert error.error.code == "unauthorized"


@pytest.mark.api
def test_pay_order(new_customer, order_product):
    checkout = _checkout_with_item(new_customer, order_product)
    assert checkout.status_code == 201, checkout.text
    order_no = checkout.json()["order_no"]

    pay = new_customer.pay(order_no)

    assert pay.status_code == 200, pay.text
    assert pay.json()["status"] == "paid"
    detail = new_customer.order(order_no)
    assert detail.status_code == 200
    assert Order.model_validate(detail.json()).status == "paid"


@pytest.mark.api
def test_cancel_order_restores_stock(new_customer, order_product):
    before = new_customer.product(order_product.id)
    assert before.status_code == 200
    before_stock = before.json()["stock"]

    checkout = _checkout_with_item(new_customer, order_product, quantity=2)
    assert checkout.status_code == 201, checkout.text
    order_no = checkout.json()["order_no"]

    after_checkout = new_customer.product(order_product.id)
    assert after_checkout.status_code == 200
    assert after_checkout.json()["stock"] == before_stock - 2

    cancel = new_customer.cancel(order_no)
    assert cancel.status_code == 200, cancel.text
    assert cancel.json()["status"] == "cancelled"

    after_cancel = new_customer.product(order_product.id)
    assert after_cancel.status_code == 200
    assert after_cancel.json()["stock"] == before_stock


@pytest.mark.api
def test_cannot_pay_cancelled_order(new_customer, order_product):
    checkout = _checkout_with_item(new_customer, order_product)
    assert checkout.status_code == 201
    order_no = checkout.json()["order_no"]
    assert new_customer.cancel(order_no).status_code == 200

    pay = new_customer.pay(order_no)

    assert pay.status_code == 409, pay.text
    error = ErrorResponse.model_validate(pay.json())
    assert error.error.code == "order_error"


@pytest.mark.api
def test_cannot_cancel_paid_order(new_customer, order_product):
    checkout = _checkout_with_item(new_customer, order_product)
    assert checkout.status_code == 201
    order_no = checkout.json()["order_no"]
    assert new_customer.pay(order_no).status_code == 200

    cancel = new_customer.cancel(order_no)

    assert cancel.status_code == 409, cancel.text
    error = ErrorResponse.model_validate(cancel.json())
    assert error.error.code == "order_error"


@pytest.mark.api
def test_different_idempotency_keys_create_distinct_orders(new_customer, order_product):
    first = _checkout_with_item(new_customer, order_product)
    second = _checkout_with_item(new_customer, order_product)

    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    assert first.json()["order_no"] != second.json()["order_no"]


@pytest.mark.api
def test_order_list_contains_created_order(new_customer, order_product):
    checkout = _checkout_with_item(new_customer, order_product)
    assert checkout.status_code == 201
    order_no = checkout.json()["order_no"]

    listing = new_customer.orders()

    assert listing.status_code == 200, listing.text
    orders = [Order.model_validate(item) for item in listing.json()["orders"]]
    assert any(order.order_no == order_no for order in orders)


@pytest.mark.api
def test_order_detail_not_found(new_customer):
    response = new_customer.order("CSNOTFOUND")

    assert response.status_code == 404
    error = ErrorResponse.model_validate(response.json())
    assert error.error.code == "not_found"


@pytest.mark.api
def test_orders_require_auth(anon):
    response = anon.orders()

    assert response.status_code == 401


@pytest.mark.api
def test_checkout_out_of_stock(admin_client, category_id, new_customer):
    created = admin_client.ops_create_product(
        product_payload(category_id, stock=1, price_cents=999)
    )
    assert created.status_code == 201, created.text
    product = created.json()

    # 先加购（此时库存 1），再把库存改成 0，结算应返回 out_of_stock。
    assert new_customer.add_to_cart(product["id"], 1).status_code == 200
    updated = admin_client.ops_update_product(product["id"], {"stock": 0})
    assert updated.status_code == 200, updated.text

    response = new_customer.checkout(idempotency_key())

    assert response.status_code == 409, response.text
    error = ErrorResponse.model_validate(response.json())
    assert error.error.code == "out_of_stock"
