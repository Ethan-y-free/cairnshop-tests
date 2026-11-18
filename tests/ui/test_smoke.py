import re

import pytest

playwright_sync = pytest.importorskip("playwright.sync_api")
expect = playwright_sync.expect

from data.factories import (  # noqa: E402
    product_payload,
    random_ip,
    unique_display_name,
    unique_email,
)


@pytest.mark.ui
@pytest.mark.requires_cairnkv
def test_login_add_to_cart_checkout_and_pay(
    page,
    settings,
    admin_client,
    category_id,
    api_factory,
):
    # 给这个浏览器会话一个独立 IP，避免和接口用例共用登录限流窗口。
    page.set_extra_http_headers({"X-Forwarded-For": random_ip()})

    created = admin_client.ops_create_product(
        product_payload(category_id, stock=50, price_cents=1999)
    )
    assert created.status_code == 201, created.text
    product = created.json()

    api = api_factory()
    email = unique_email("ui")
    display_name = unique_display_name()
    registered = api.register(
        email=email,
        password="secret123",
        display_name=display_name,
    )
    assert registered.status_code == 201, registered.text

    page.goto(f"{settings.ui_url}/login")
    page.get_by_placeholder("you@example.com").fill(email)
    page.locator('input[type="password"]').fill("secret123")
    page.get_by_role("button", name="登录", exact=True).click()

    expect(page).to_have_url(re.compile(r"/$"))
    expect(page.locator(".who")).to_have_text(display_name)
    expect(page.get_by_text("双十一提前购")).to_be_visible()

    page.goto(f"{settings.ui_url}/product/{product['id']}")
    expect(page.get_by_role("heading", name=product["name"])).to_be_visible()
    page.get_by_role("button", name="加入购物车").click()
    expect(page.get_by_text("已加入购物车")).to_be_visible()

    page.goto(f"{settings.ui_url}/cart")
    expect(page.get_by_role("heading", name="购物车")).to_be_visible()
    page.get_by_role("button", name="去结算").click()

    expect(page).to_have_url(re.compile(r"/orders$"))
    expect(page.get_by_text("下单成功", exact=False)).to_be_visible()
    expect(page.get_by_role("heading", name="我的订单")).to_be_visible()

    pay = page.get_by_role("button", name="支付").first
    expect(pay).to_be_visible()
    pay.click()

    expect(page.get_by_text("支付成功")).to_be_visible()
    expect(page.locator("article.order .el-tag").first).to_have_text("paid")
