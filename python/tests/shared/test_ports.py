"""Self-tests for the port check."""
import socket

import pytest

from checks.shared.ports import port_is_open

pytestmark = pytest.mark.selftest


def test_open_and_closed_ports_are_told_apart():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        port = listener.getsockname()[1]
        assert port_is_open("127.0.0.1", port) is True
    assert port_is_open("127.0.0.1", port) is False
