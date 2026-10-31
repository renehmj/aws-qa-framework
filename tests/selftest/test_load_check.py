"""Self-tests for the load test: a slow or broken API must fail it."""
import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import pytest

from checks.load import k6_problems

pytestmark = pytest.mark.selftest

SCRIPT = Path(__file__).parents[1] / "load" / "api_load.js"


def _serve(status, delay):
    class BadHandler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def _answer(self):
            self.rfile.read(int(self.headers.get("Content-Length", 0)))
            time.sleep(delay)
            body = json.dumps({"status": "ok"}).encode()
            self.send_response(200 if self.path == "/health" else status)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        do_GET = do_POST = _answer

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), BadHandler)
    Thread(target=server.serve_forever, daemon=True).start()
    return server


@pytest.mark.parametrize("status, delay, expected", [
    (500, 0, "http_req_failed"),      # the API returns errors
    (201, 0.7, "http_req_duration"),  # the API is too slow
], ids=["errors", "too-slow"])
def test_bad_api_fails_the_load_test(k6, status, delay, expected, tmp_path):
    server = _serve(status, delay)
    url = f"http://127.0.0.1:{server.server_port}"
    problems = k6_problems(SCRIPT, url, "token", 2, "3s", tmp_path / "summary.json")
    server.shutdown()
    assert any(expected in problem for problem in problems)
