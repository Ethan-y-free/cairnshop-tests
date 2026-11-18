from __future__ import annotations

from collections.abc import Callable, Iterator

import pytest

from api.client import ApiClient
from api.endpoints import CairnShopApi
from api.models import Category, Product
from config.settings import Settings
from data.factories import (
    product_payload,
    random_ip,
    unique_display_name,
    unique_email,
)


@pytest.fixture(scope="session")
def settings() -> Settings:
    return Settings()


@pytest.fixture
def api_factory(settings: Settings) -> Iterator[Callable[..., CairnShopApi]]:
    """创建带独立 X-Forwarded-For 的匿名客户端，避免限流互相影响。"""
    clients: list[ApiClient] = []

    def make(
        xff: str | None = None,
        timeout: float | None = None,
    ) -> CairnShopApi:
        client = ApiClient(
            settings.base_url,
            timeout=timeout or settings.timeout,
            xff=xff or random_ip(),
        )
        clients.append(client)
        return CairnShopApi(client)

    yield make
    for client in clients:
        client.close()


@pytest.fixture
def anon(api_factory: Callable[..., CairnShopApi]) -> CairnShopApi:
    return api_factory()


@pytest.fixture(scope="session")
def admin_client(settings: Settings) -> Iterator[CairnShopApi]:
    client = ApiClient(
        settings.base_url,
        timeout=settings.timeout,
        xff=random_ip(),
    )
    api = CairnShopApi(client)
    response = api.login(settings.admin_email, settings.admin_password)
    if response.status_code != 200:
        client.close()
        pytest.fail(
            "admin login failed; check CAIRNSHOP_TEST_ADMIN_EMAIL/PASSWORD "
            f"and run `cairnshop-backend seed` first: {response.status_code} "
            f"{response.text[:300]}"
        )
    yield api
    try:
        api.logout()
    finally:
        client.close()


@pytest.fixture(scope="session")
def customer_client(settings: Settings) -> Iterator[CairnShopApi]:
    client = ApiClient(
        settings.base_url,
        timeout=settings.timeout,
        xff=random_ip(),
    )
    api = CairnShopApi(client)
    response = api.register(
        email=unique_email("customer"),
        password="secret123",
        display_name=unique_display_name(),
    )
    if response.status_code != 201:
        client.close()
        pytest.fail(
            f"customer registration failed: {response.status_code} "
            f"{response.text[:300]}"
        )
    yield api
    client.close()


@pytest.fixture(scope="session")
def category_id(admin_client: CairnShopApi) -> int:
    response = admin_client.categories()
    assert response.status_code == 200, response.text
    categories = [
        Category.model_validate(item) for item in response.json()["categories"]
    ]
    assert categories, "catalog is empty; run `cairnshop-backend seed` first"
    return categories[0].id


@pytest.fixture(scope="session")
def test_product(admin_client: CairnShopApi, category_id: int) -> Product:
    """每个测试会话创建一个专用商品，避免依赖 seed 商品的库存。"""
    response = admin_client.ops_create_product(product_payload(category_id))
    assert response.status_code == 201, response.text
    return Product.model_validate(response.json())


@pytest.fixture
def new_customer(api_factory: Callable[..., CairnShopApi]) -> CairnShopApi:
    """每个订单用例一个全新用户，避免 checkout 10 次/分钟的用户级限流。"""
    api = api_factory()
    response = api.register(
        email=unique_email("order"),
        password="secret123",
        display_name=unique_display_name(),
    )
    assert response.status_code == 201, response.text
    return api


@pytest.fixture(scope="session")
def order_product(admin_client: CairnShopApi, category_id: int) -> Product:
    """订单/库存用例专用商品，库存 1000，避免被前面的用例扣光。"""
    response = admin_client.ops_create_product(
        product_payload(category_id, stock=1000, price_cents=2599)
    )
    assert response.status_code == 201, response.text
    return Product.model_validate(response.json())


@pytest.fixture
def empty_cart(customer_client: CairnShopApi) -> CairnShopApi:
    response = customer_client.cart()
    assert response.status_code == 200, response.text
    for item in response.json()["items"]:
        customer_client.remove_cart_item(item["product_id"])
    return customer_client


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if Settings().require_cairnkv:
        return
    skip = pytest.mark.skip(
        reason="requires CairnKV; set CAIRNSHOP_TEST_REQUIRE_CAIRNKV=1 to run"
    )
    for item in items:
        if "requires_cairnkv" in item.keywords:
            item.add_marker(skip)
