"""Self-test for how a folder's settings and an account's settings combine."""
import pytest

pytestmark = pytest.mark.selftest


def test_account_value_replaces_folder_value(settings):
    """The fake account uses high ports, so a service on a laptop can not fail the test."""
    assert settings["closed_ports"] == [59998, 59999]
