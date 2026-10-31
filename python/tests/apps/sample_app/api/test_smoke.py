"""Smoke test: is the API alive?"""
from urllib.parse import urlparse

import pytest
import requests

from checks.shared.ports import port_is_open

pytestmark = pytest.mark.smoke


def test_tc12_api_is_healthy(api):
    """TC-12: The API port is open and /health says ok."""
    url = urlparse(api["url"])
    assert port_is_open(url.hostname, url.port), f"cannot reach {api['url']}"
    assert requests.get(f"{api['url']}/health", timeout=5).json()["status"] == "ok"
