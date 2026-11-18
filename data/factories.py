from __future__ import annotations

import random
import socket
import string
import uuid


def unique_email(prefix: str = "qa") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}@example.com"


def unique_phone() -> str:
    return "139" + "".join(random.choices(string.digits, k=8))


def unique_display_name() -> str:
    return f"QA-{uuid.uuid4().hex[:6]}"


def idempotency_key(prefix: str = "it") -> str:
    return f"{prefix}-{uuid.uuid4().hex}"


def random_ip() -> str:
    """给测试客户端分配独立的 X-Forwarded-For，隔离限流窗口。"""
    # 198.18.0.0/15 是 benchmark 保留网段，不会和真实环境冲突。
    return (
        f"198.18.{random.randint(0, 255)}.{random.randint(1, 254)}"
        if random.random() < 0.5
        else f"198.19.{random.randint(0, 255)}.{random.randint(1, 254)}"
    )


def local_ip() -> str:
    """当前机器出口 IP，仅用于日志/报告，不参与断言。"""
    try:
        return socket.gethostbyname(socket.gethostname())
    except OSError:
        return "127.0.0.1"


def product_payload(
    category_id: int,
    *,
    stock: int = 100,
    price_cents: int = 1999,
) -> dict:
    suffix = uuid.uuid4().hex[:8]
    return {
        "sku": f"QA-{suffix}",
        "name": f"QA 测试商品 {suffix}",
        "description": "自动化测试专用商品",
        "detail": "由 cairnshop-tests 创建，供接口/性能测试使用",
        "image_url": "",
        "status": "active",
        "category_id": category_id,
        "price_cents": price_cents,
        "original_price_cents": price_cents * 2,
        "stock": stock,
    }
