"""Regression test for on-prem: can the cloud still reach it?"""
import pytest

from checks.shared.ports import port_is_open

pytestmark = pytest.mark.regression


def test_tc35_required_connections_work(config):
    """TC-35 (positive): Hybrid paths, such as cloud to on-prem, are reachable."""
    if not config["required_connections"]:
        pytest.skip("no required connections are listed for this environment")
    broken = [link["name"] for link in config["required_connections"] if not port_is_open(link["host"], link["port"])]
    assert not broken, f"cannot reach: {broken}"
