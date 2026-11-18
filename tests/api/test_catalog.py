import pytest

from api.models import Category, ErrorResponse, Product


@pytest.mark.api
def test_categories_returns_seeded_catalog(anon):
    response = anon.categories()

    assert response.status_code == 200, response.text
    categories = [
        Category.model_validate(item) for item in response.json()["categories"]
    ]
    assert categories
    assert all(category.slug for category in categories)


@pytest.mark.api
def test_products_returns_paginated_list(anon):
    response = anon.products(limit=5, offset=0)

    assert response.status_code == 200, response.text
    body = response.json()
    products = [Product.model_validate(item) for item in body["products"]]
    assert body["limit"] == 5
    assert body["offset"] == 0
    assert len(products) <= 5
    assert products


@pytest.mark.api
def test_product_detail(anon):
    listing = anon.products(limit=1, offset=0)
    assert listing.status_code == 200, listing.text
    product_id = listing.json()["products"][0]["id"]

    response = anon.product(product_id)

    assert response.status_code == 200, response.text
    product = Product.model_validate(response.json())
    assert product.id == product_id
    assert product.status == "active"


@pytest.mark.api
def test_product_detail_not_found(anon):
    response = anon.product(99999999)

    assert response.status_code == 404
    error = ErrorResponse.model_validate(response.json())
    assert error.error.code == "not_found"


@pytest.mark.api
def test_product_search(anon):
    response = anon.products(q="耳机", limit=10)

    assert response.status_code == 200, response.text
    assert response.json()["limit"] == 10


@pytest.mark.api
@pytest.mark.parametrize(
    "params",
    [
        {"limit": "abc"},
        {"offset": "abc"},
        {"category_id": "abc"},
    ],
)
def test_products_rejects_invalid_query_params(anon, params):
    response = anon.products(**params)

    assert response.status_code == 400, response.text
    error = ErrorResponse.model_validate(response.json())
    assert error.error.code == "invalid_argument"
