from __future__ import annotations

import json
import time

CHECKOUT_FLAG = "cairnshop/flags/checkout_enabled"


def wait_for_checkout_flag(
    admin_client,
    enabled: bool,
    timeout: float = 5.0,
) -> dict:
    """等待配置缓存刷新到指定状态。

    checkout 读的是 ConfigService 的内存快照（默认 500ms 刷新一次），
    运营接口写的是 CairnKV 原始值；写完必须等快照追上再断言。
    """
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        response = admin_client.ops_config_get()
        if response.status_code == 200:
            raw = response.json().get("keys", {}).get(CHECKOUT_FLAG)
            if raw:
                try:
                    last = json.loads(raw)
                    if bool(last.get("enabled")) is enabled:
                        return last
                except json.JSONDecodeError:
                    pass
        time.sleep(0.1)
    raise AssertionError(
        f"checkout flag did not become enabled={enabled} within {timeout}s; "
        f"last={last}"
    )


def wait_for_snapshot_key(admin_client, key: str, timeout: float = 5.0) -> dict:
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        response = admin_client.ops_config_get()
        if response.status_code == 200:
            raw = response.json().get("keys", {}).get(key)
            if raw:
                try:
                    last = json.loads(raw)
                    return last
                except json.JSONDecodeError:
                    pass
        time.sleep(0.1)
    raise AssertionError(
        f"config key {key} did not appear in snapshot within {timeout}s; "
        f"last={last}"
    )
