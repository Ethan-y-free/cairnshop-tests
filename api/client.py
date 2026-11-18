from __future__ import annotations

import json
import time
from typing import Any

import allure
import requests


class ApiClient:
    """薄封装 requests.Session。

    职责：
    - 统一 base_url / timeout / JSON 头；
    - 每次请求自动写 Allure 附件，失败时能看到原始请求和响应；
    - 可选 X-Forwarded-For：测试里用它隔离限流（后端按该头识别客户端 IP）。
    """

    def __init__(
        self,
        base_url: str,
        timeout: float = 5.0,
        xff: str | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})
        if xff:
            self.session.headers["X-Forwarded-For"] = xff

    def request(
        self,
        method: str,
        path: str,
        *,
        expected: int | None = None,
        **kwargs: Any,
    ) -> requests.Response:
        url = f"{self.base_url}{path}"
        started = time.perf_counter()
        response = self.session.request(method, url, timeout=self.timeout, **kwargs)
        elapsed_ms = (time.perf_counter() - started) * 1000

        self._attach(method, path, kwargs, response, elapsed_ms)

        if expected is not None and response.status_code != expected:
            raise AssertionError(
                f"{method} {path}: expected {expected}, "
                f"got {response.status_code}: {response.text[:800]}"
            )
        return response

    def get(self, path: str, **kwargs: Any) -> requests.Response:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> requests.Response:
        return self.request("POST", path, **kwargs)

    def put(self, path: str, **kwargs: Any) -> requests.Response:
        return self.request("PUT", path, **kwargs)

    def patch(self, path: str, **kwargs: Any) -> requests.Response:
        return self.request("PATCH", path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> requests.Response:
        return self.request("DELETE", path, **kwargs)

    def close(self) -> None:
        self.session.close()

    @staticmethod
    def _attach(
        method: str,
        path: str,
        kwargs: dict[str, Any],
        response: requests.Response,
        elapsed_ms: float,
    ) -> None:
        with allure.step(
            f"{method} {path} -> {response.status_code} ({elapsed_ms:.1f} ms)"
        ):
            title = f"{method} {path}\nstatus={response.status_code}\n"
            if "params" in kwargs:
                title += f"params={kwargs['params']}\n"
            if "headers" in kwargs:
                title += f"headers={kwargs['headers']}\n"
            allure.attach(
                title,
                name="request",
                attachment_type=allure.attachment_type.TEXT,
            )
            if "json" in kwargs:
                allure.attach(
                    json.dumps(kwargs["json"], ensure_ascii=False, indent=2),
                    name="request body",
                    attachment_type=allure.attachment_type.JSON,
                )
            allure.attach(
                response.text[:8000] or "<empty>",
                name="response body",
                attachment_type=allure.attachment_type.TEXT,
            )
