"""Setup for this project: where its API is."""
import os
from threading import Thread

import pytest
from sample_app.server import make_server


@pytest.fixture(scope="session")
def api(live):
    """Live: the test server. Mock: the same code, on this machine."""
    if live:
        yield {"url": os.environ["QA_API_URL"], "token": os.environ["QA_API_TOKEN"]}
        return

    server = make_server(port=0, token="local-test-token")
    Thread(target=server.serve_forever, daemon=True).start()
    yield {"url": f"http://127.0.0.1:{server.server_port}", "token": "local-test-token"}
    server.shutdown()
