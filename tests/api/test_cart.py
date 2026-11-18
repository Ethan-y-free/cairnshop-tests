import pytest

from api.models import Cart, ErrorResponse


def _items_by_product(cart: Cart, product_id: int):
    return [item for item in cart.items if item.product_id == product_id]


@pytest.mark.api
def test_add_item(empty_cart, test_product):
    response = empty_cart.add_to_cart(test_product.id, quantity=2)

    assert response.status_code == 200, response.text
    cart = Cart.model_validate(response.json())
    items = _items_by_product(cart, test_product.id)
    assert len(items) == 1
    assert items[0].quantity == 2
    assert cart.subtotal_cents == test_product.price_cents * 2


@pytest.mark.api
def test_add_same_item_accumulates(empty_cart, test_product):
    assert empty_cart.add_to_cart(test_product.id, 1).status_code == 200
    response = empty_cart.add_to_cart(test_product.id, 1)

    assert response.status_code == 200, response.text
    cart = Cart.model_validate(response.json())
    assert _items_by_product(cart, test_product.id)[0].quantity == 2


@pytest.mark.api
def test_update_quantity(empty_cart, test_product):
    assert empty_cart.add_to_cart(test_product.id, 1).status_code == 200

    response = empty_cart.update_cart_item(test_product.id, 3)

    assert response.status_code == 200, response.text
    cart = Cart.model_validate(response.json())
    assert _items_by_product(cart, test_product.id)[0].quantity == 3


@pytest.mark.api
def test_update_quantity_to_zero_removes_item(empty_cart, test_product):
    assert empty_cart.add_to_cart(test_product.id, 1).status_code == 200

    response = empty_cart.update_cart_item(test_product.id, 0)

    assert response.status_code == 200, response.text
    cart = Cart.model_validate(response.json())
    assert _items_by_product(cart, test_product.id) == []


@pytest.mark.api
def test_remove_item(empty_cart, test_product):
    assert empty_cart.add_to_cart(test_product.id, 1).status_code == 200

    response = empty_cart.remove_cart_item(test_product.id)

    assert response.status_code == 200, response.text
    cart = Cart.model_validate(response.json())
    assert _items_by_product(cart, test_product.id) == []


@pytest.mark.api
@pytest.mark.parametrize("quantity", [0, -1, 100])
def test_add_item_rejects_invalid_quantity(empty_cart, test_product, quantity):
    response = empty_cart.add_to_cart(test_product.id, quantity)

    assert response.status_code == 400, response.text
    error = ErrorResponse.model_validate(response.json())
    assert error.error.code == "invalid_argument"


@pytest.mark.api
def test_add_nonexistent_product(empty_cart):
    response = empty_cart.add_to_cart(99999999, 1)

    assert response.status_code == 400, response.text
    error = ErrorResponse.model_validate(response.json())
    assert error.error.code == "cart_error"


@pytest.mark.api
def test_cart_requires_auth(anon):
    response = anon.cart()

    assert response.status_code == 401
    error = ErrorResponse.model_validate(response.json())
    assert error.error.code == "unauthorized"


@pytest.mark.api
def test_add_to_cart_requires_auth(anon, test_product):
    response = anon.add_to_cart(test_product.id, 1)

    assert response.status_code == 401
