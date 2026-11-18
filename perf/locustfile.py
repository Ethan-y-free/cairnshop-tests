from __future__ import annotations

import os
import uuid

import requests
from locust import HttpUser, between, events, task

BASE_URL = os.getenv("CAIRNSHOP_TEST_BASE_URL", "http://127.0.0.1:8080")
ADMIN_EMAIL = os.getenv("CAIRNSHOP_TEST_ADMIN_EMAIL", "admin@cairnshop.local")
ADMIN_PASSWORD = os.getenv("CAIRNSHOP_TEST_ADMIN_PASSWORD", "admin123456")

PERF_PRODUCT_ID: int | None = None


def _random_ip() -> str:
    value = uuid.uuid4().int
    return f"198.18.{value % 256}.{(value >> 8) % 254 + 1}"


@events.test_start.add_listener
def create_perf_product(environment, **kwargs) -> None:
    """压测开始前用管理员账号创建一个高库存商品。"""
    global PERF_PRODUCT_ID

    session = requests.Session()
    session.headers["X-Forwarded-For"] = _random_ip()

    login = session.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"identifier": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=5,
    )
    login.raise_for_status()

    categories = session.get(
        f"{BASE_URL}/api/v1/catalog/categories", timeout=5
    ).json()["categories"]
    if not categories:
        raise RuntimeError("catalog is empty; run `cairnshop-backend seed` first")

    suffix = uuid.uuid4().hex[:8]
    payload = {
        "sku": f"PERF-{suffix}",
        "name": f"Perf 商品 {suffix}",
        "description": "Locust 压测专用商品",
        "detail": "由 perf/locustfile.py 创建",
        "image_url": "",
        "status": "active",
        "category_id": categories[0]["id"],
        "price_cents": 999,
        "original_price_cents": 0,
        "stock": 100000,
    }
    created = session.post(
        f"{BASE_URL}/api/v1/ops/catalog/products",
        json=payload,
        timeout=5,
    )
    created.raise_for_status()
    PERF_PRODUCT_ID = created.json()["id"]


class BrowseUser(HttpUser):
    """只读流量：分类、列表、详情。"""

    host = BASE_URL
    weight = 3
    wait_time = between(1, 3)

    def on_start(self) -> None:
        self.client.headers["X-Forwarded-For"] = _random_ip()
        self.product_id: int | None = None
        response = self.client.get("/api/v1/catalog/products?limit=1")
        if response.status_code == 200:
            products = response.json().get("products", [])
            if products:
                self.product_id = products[0]["id"]

    @task(5)
    def list_products(self) -> None:
        self.client.get("/api/v1/catalog/products?limit=20")

    @task(3)
    def list_categories(self) -> None:
        self.client.get("/api/v1/catalog/categories")

    @task(2)
    def product_detail(self) -> None:
        if self.product_id is not None:
            self.client.get(f"/api/v1/catalog/products/{self.product_id}")


class ShopperUser(HttpUser):
    """登录、加购、查看购物车、低频下单。"""

    host = BASE_URL
    weight = 1
    wait_time = between(2, 5)

    def on_start(self) -> None:
        self.client.headers["X-Forwarded-For"] = _random_ip()
        self.product_id = PERF_PRODUCT_ID
        if self.product_id is None:
            products = self.client.get("/api/v1/catalog/products?limit=1").json()[
                "products"
            ]
            self.product_id = products[0]["id"]

        email = f"perf-{uuid.uuid4().hex[:12]}@example.com"
        registered = self.client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "phone": "",
                "password": "secret123",
                "display_name": f"Perf {uuid.uuid4().hex[:6]}",
            },
        )
        registered.raise_for_status()
        self._add_item()

    def _add_item(self) -> None:
        self.client.post(
            "/api/v1/cart/items",
            json={"product_id": self.product_id, "quantity": 1},
        )

    @task(4)
    def view_cart(self) -> None:
        self.client.get("/api/v1/cart")

    @task(2)
    def add_item(self) -> None:
        self._add_item()

    @task(1)
    def checkout(self) -> None:
        with self.client.post(
            "/api/v1/orders",
            headers={"Idempotency-Key": f"perf-{uuid.uuid4().hex}"},
            catch_response=True,
        ) as response:
            if response.status_code == 201:
                response.success()
            else:
                response.failure(f"checkout status={response.status_code}")
        self._add_item()
