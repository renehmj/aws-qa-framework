"""Setup for this project: which server to test from outside."""
import os
from urllib.parse import urlparse

import pytest


@pytest.fixture
def server_host(live):
    """Live: the test server. Mock: this machine."""
    return urlparse(os.environ["QA_API_URL"]).hostname if live else "127.0.0.1"
