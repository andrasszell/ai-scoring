from __future__ import annotations

import time
from typing import Any

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import settings

_last_sec_request = 0.0


def _headers(extra: dict[str, str] | None = None) -> dict[str, str]:
    headers = {
        "User-Agent": settings.sec_user_agent,
        "Accept-Encoding": "gzip, deflate",
        "Accept": "application/json,text/html,text/plain,*/*",
    }
    if extra:
        headers.update(extra)
    return headers


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
def get(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    sec: bool = False,
) -> requests.Response:
    """HTTP GET with retries, a descriptive User-Agent, and SEC rate limiting."""
    global _last_sec_request
    if sec:
        elapsed = time.time() - _last_sec_request
        if elapsed < 0.25:
            time.sleep(0.25 - elapsed)
        _last_sec_request = time.time()
    response = requests.get(url, params=params, headers=_headers(headers), timeout=settings.request_timeout)
    response.raise_for_status()
    return response
