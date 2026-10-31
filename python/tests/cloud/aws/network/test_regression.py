"""Regression test: admin ports are not open to the internet."""
import pytest

from checks.cloud.aws.network import ports_open_to_world

pytestmark = pytest.mark.regression


@pytest.mark.parametrize("port", [22, 3389], ids=["ssh", "rdp"])
def test_tc04_admin_ports_not_open_to_world(aws, port):
    """TC-04: No security group opens SSH or RDP to the internet."""
    problems = ports_open_to_world(aws, ports=(port,))
    assert not problems, "\n".join(problems)
