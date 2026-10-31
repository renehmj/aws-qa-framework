"""Smoke tests: is everything alive?

If these fail, there is no point running the regression tests.
"""
from urllib.parse import urlparse

import pytest
import requests

from checks.audit import cloudtrail_problems
from checks.auth import credential_problems
from checks.connectivity import port_is_open

pytestmark = pytest.mark.smoke


@pytest.mark.aws
def test_tc01_credentials_work(aws):
    """TC-01: We can call AWS with the test role."""
    identity = aws.client("sts").get_caller_identity()
    assert identity["Account"], "could not read the account ID"


@pytest.mark.aws
def test_tc02_cloudtrail_is_logging(aws):
    """TC-02: At least one CloudTrail trail exists and is logging."""
    problems = cloudtrail_problems(aws)
    assert not problems, "\n".join(problems)


@pytest.mark.aws
def test_tc11_credentials_are_short_lived(aws):
    """TC-11: We use temporary credentials, and never the root user."""
    problems = credential_problems(aws)
    assert not problems, "\n".join(problems)


@pytest.mark.api
def test_tc12_api_is_healthy(api):
    """TC-12: The API port is open and /health says ok."""
    url = urlparse(api["url"])
    assert port_is_open(url.hostname, url.port), f"cannot reach {api['url']}"
    assert requests.get(f"{api['url']}/health", timeout=5).json()["status"] == "ok"


@pytest.mark.database
def test_tc13_database_login_works(databases, config):
    """TC-13: The QA login works on every database."""
    for db in config["databases"]:
        assert databases[db["name"]].execute("SELECT current_user").fetchone()[0] == db["user"]
