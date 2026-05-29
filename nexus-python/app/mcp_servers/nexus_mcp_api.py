import json
from typing import Any, Literal
import httpx
from mcp.server.fastmcp import FastMCP

server = FastMCP("api")


@server.tool(
    "call_api",
    description="通用 REST API 调用，返回 JSON。支持 GET/POST/PUT/DELETE。"
)
async def call_api(
        endpoint: str,
        method: Literal["GET", "POST", "PUT", "DELETE", "PATCH"] = "GET",
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        json_body: dict[str, Any] | None = None,
        timeout: float = 30.0,
) -> dict[str, Any]:
    """
    异步发起 HTTP 请求，返回解析后的 JSON。

    如果响应状态码 >= 400，或返回非 JSON，会抛出 RuntimeError。
    """
    # 默认补充 Accept 头，避免某些 API 返回 XML
    request_headers = {"Accept": "application/json"}
    if headers:
        request_headers.update(headers)

    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.request(
                method=method.upper(),
                url=endpoint,
                params=params,
                headers=request_headers,
                json=json_body,
            )
    except httpx.TimeoutException as e:
        raise RuntimeError(f"API 请求超时: {method} {endpoint} (>{timeout}s)") from e
    except httpx.RequestError as e:
        raise RuntimeError(f"API 请求失败: {method} {endpoint}, 原因: {e}") from e

    # 显式检查 HTTP 状态码，4xx/5xx 提前暴露
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        # 尝试提取错误响应体，方便上层定位
        error_text = response.text[:500]
        raise RuntimeError(
            f"API 返回错误状态码: {response.status_code}, "
            f"URL: {endpoint}, 响应: {error_text}"
        ) from e

    # 安全解析 JSON
    content_type = response.headers.get("content-type", "")
    if "application/json" not in content_type:
        # 有些 API 虽然返回 200，但内容是 HTML/纯文本
        raise RuntimeError(
            f"API 返回非 JSON 内容: {content_type}, "
            f"URL: {endpoint}, 响应: {response.text[:200]}"
        )

    try:
        return response.json()
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"API 响应 JSON 解析失败: {endpoint}, 原始响应: {response.text[:200]}"
        ) from e