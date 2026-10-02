"""
net.py – Shared HTTP helpers.
"""

from collections.abc import Mapping
from typing import Any

import requests

from . import config
from .errors import NetworkError


def fetch_json(
    url: str,
    headers: Mapping[str, str] | None = None,
    params: Mapping[str, str] | None = None,
    timeout: int | None = None,
) -> Any:
    """GET *url* and return parsed JSON. Raises NetworkError on failure."""
    try:
        resp = requests.get(
            url,
            headers=dict(headers or {}),
            params=dict(params or {}),
            timeout=timeout or config.REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        raise NetworkError(f"Request to {url} failed: {exc}") from exc
