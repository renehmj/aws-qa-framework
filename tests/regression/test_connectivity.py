"""Regression tests for the network: what must work, and what must stay closed."""
from urllib.parse import urlparse

import pytest

from checks.connectivity import port_is_open

pytestmark = [pytest.mark.regression, pytest.mark.connectivity]


def test_tc21_admin_ports_are_closed(api, config):
    """TC-21 (negative): SSH, RDP, and database ports can not be reached from outside."""
    host = urlparse(api["url"]).hostname
    open_ports = [port for port in config["closed_ports"] if port_is_open(host, port)]
    assert not open_ports, f"{host} has open ports: {open_ports}"


def test_tc35_required_connections_work(config):
    """TC-35 (positive): Hybrid paths, such as cloud to on-prem, are reachable."""
    if not config["required_connections"]:
        pytest.skip("no required connections are listed for this environment")
    broken = [link["name"] for link in config["required_connections"] if not port_is_open(link["host"], link["port"])]
    assert not broken, f"cannot reach: {broken}"
