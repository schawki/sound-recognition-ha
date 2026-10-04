import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest


@pytest.fixture(autouse=True)
def _loopback_allowed():
    """The API tests start a local server; pytest-socket (present when the Home Assistant test plugins are) would forbid it."""
    try:
        import pytest_socket
    except ImportError:
        yield
        return
    pytest_socket.enable_socket()
    pytest_socket.socket_allow_hosts(["127.0.0.1"], allow_unix_socket=True)
    yield
    pytest_socket.disable_socket(allow_unix_socket=True)
