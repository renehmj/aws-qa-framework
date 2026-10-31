import socket


def port_is_open(host, port, timeout=3):
    """True if a network connection to host:port works."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False
