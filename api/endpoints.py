from __future__ import annotations

from typing import Any

import requests

from api.client import ApiClient


class CairnShopApi:
    """按业务域组织的接口方法。

    测试用例只依赖这一层，不直接拼 URL；接口变更时只改这里。
    """

    def __init__(self, client: ApiClient) -> None:
        self.client = client

    # ---- 健康检查 / 指标 ----
    def healthz(self) -> requests.Response:
        return self.client.get("/healthz")

    def readyz(self) -> requests.Response:
        return self.client.get("/readyz")

    def metrics(self) -> requests.Response:
        return self.client.get("/metrics")

    # ---- 认证 ----
    def register(
        self,
        *,
        email: str = "",
        phone: str = "",
        password: str = "secret123",
        display_name: str = "QA User",
    ) -> requests.Response:
        return self.client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "phone": phone,
                "password": password,
                "display_name": display_name,
            },
        )

    def login(self, identifier: str, password: str) -> requests.Response:
        return self.client.post(
            "/api/v1/auth/login",
            json={"identifier": identifier, "password": password},
        )

    def logout(self) -> requests.Response:
        return self.client.post("/api/v1/auth/logout")

    def me(self) -> requests.Response:
        return self.client.get("/api/v1/auth/me")

    # ---- 商品 ----
    def categories(self) -> requests.Response:
        return self.client.get("/api/v1/catalog/categories")

    def products(self, **params: Any) -> requests.Response:
        return self.client.get("/api/v1/catalog/products", params=params)

    def product(self, product_id: int) -> requests.Response:
        return self.client.get(f"/api/v1/catalog/products/{product_id}")

    # ---- 购物车 ----
    def cart(self) -> requests.Response:
        return self.client.get("/api/v1/cart")

    def add_to_cart(self, product_id: int, quantity: int = 1) -> requests.Response:
        return self.client.post(
            "/api/v1/cart/items",
            json={"product_id": product_id, "quantity": quantity},
        )

    def update_cart_item(self, product_id: int, quantity: int) -> requests.Response:
        return self.client.patch(
            f"/api/v1/cart/items/{product_id}",
            json={"quantity": quantity},
        )

    def remove_cart_item(self, product_id: int) -> requests.Response:
        return self.client.delete(f"/api/v1/cart/items/{product_id}")

    # ---- 订单 ----
    def checkout(self, idempotency_key: str) -> requests.Response:
        return self.client.post(
            "/api/v1/orders",
            headers={"Idempotency-Key": idempotency_key},
        )

    def orders(self, limit: int = 20, offset: int = 0) -> requests.Response:
        return self.client.get(
            "/api/v1/orders",
            params={"limit": limit, "offset": offset},
        )

    def order(self, order_no: str) -> requests.Response:
        return self.client.get(f"/api/v1/orders/{order_no}")

    def pay(self, order_no: str) -> requests.Response:
        return self.client.post(f"/api/v1/orders/{order_no}/pay")

    def cancel(self, order_no: str) -> requests.Response:
        return self.client.post(f"/api/v1/orders/{order_no}/cancel")

    # ---- 运营 / 配置 ----
    def ops_status(self) -> requests.Response:
        return self.client.get("/api/v1/ops/status")

    def ops_config_get(self, key: str | None = None) -> requests.Response:
        params = {"key": key} if key else None
        return self.client.get("/api/v1/ops/config", params=params)

    def ops_config_put(self, key: str, value: dict) -> requests.Response:
        return self.client.put(
            "/api/v1/ops/config",
            json={"key": key, "value": value},
        )

    def ops_config_history(self, key: str) -> requests.Response:
        return self.client.get(
            "/api/v1/ops/config/history",
            params={"key": key},
        )

    def ops_config_rollback(self, key: str, version: int) -> requests.Response:
        return self.client.post(
            "/api/v1/ops/config/rollback",
            json={"key": key, "version": version},
        )

    def ops_audit(self, limit: int = 20) -> requests.Response:
        return self.client.get("/api/v1/ops/audit", params={"limit": limit})

    def ops_create_product(self, payload: dict) -> requests.Response:
        return self.client.post("/api/v1/ops/catalog/products", json=payload)

    def ops_update_product(self, product_id: int, payload: dict) -> requests.Response:
        return self.client.patch(
            f"/api/v1/ops/catalog/products/{product_id}",
            json=payload,
        )
