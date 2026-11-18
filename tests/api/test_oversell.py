from concurrent.futures import ThreadPoolExecutor

import pytest

from data.factories import (
    idempotency_key,
    product_payload,
    unique_display_name,
    unique_email,
)


@pytest.mark.api
@pytest.mark.requires_cairnkv
@pytest.mark.slow
def test_oversell_only_stock_winners_succeed(admin_client, api_factory, category_id):
    created = admin_client.ops_create_product(
        product_payload(category_id, stock=10, price_cents=999)
    )
    assert created.status_code == 201, created.text
    product = created.json()

    buyers = []
    for _ in range(15):
        # 2 vCPU VM + MySQL 连接池 4 下，15 路并发结算会排队，
        # 默认 5s 容易误判超时；这里给压测场景放宽到 30s。
        buyer = api_factory(timeout=30)
        registered = buyer.register(
            email=unique_email("buyer"),
            password="secret123",
            display_name=unique_display_name(),
        )
        assert registered.status_code == 201, registered.text
        added = buyer.add_to_cart(product["id"], 1)
        assert added.status_code == 200, added.text
        buyers.append(buyer)

    def checkout(buyer) -> int:
        return buyer.checkout(idempotency_key()).status_code

    with ThreadPoolExecutor(max_workers=15) as pool:
        statuses = list(pool.map(checkout, buyers))

    assert statuses.count(201) == 10, statuses
    assert statuses.count(409) == 5, statuses
    assert all(status in (201, 409) for status in statuses), statuses

    detail = admin_client.product(product["id"])
    assert detail.status_code == 200, detail.text
    assert detail.json()["stock"] == 0
