"""Regression test for the network: what must stay closed."""
import pytest

from checks.shared.ports import port_is_open

pytestmark = pytest.mark.regression


def test_tc21_admin_ports_are_closed(server_host, settings):
    """TC-21 (negative): SSH, RDP, and database ports can not be reached from outside."""
    open_ports = [port for port in settings["closed_ports"] if port_is_open(server_host, port)]
    assert not open_ports, f"{server_host} has open ports: {open_ports}"
