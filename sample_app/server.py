"""A tiny telemetry API. It uses only Python's standard library."""
import hmac
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from sample_app.telemetry import battery_status, power_kw, reading_errors

VERSION = "1.0.0"


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    token = ""
    latest = {}

    def do_GET(self):
        if self.path == "/health":
            self._send(200, {"status": "ok", "version": VERSION})
        elif not self._logged_in():
            self._send(401, {"error": "login required"})
        elif self.path.startswith("/units/"):
            unit = self.latest.get(self.path.removeprefix("/units/"))
            self._send(200, unit) if unit else self._send(404, {"error": "unknown unit"})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        reading = self._read_json()
        if not self._logged_in():
            self._send(401, {"error": "login required"})
        elif self.path != "/readings":
            self._send(404, {"error": "not found"})
        elif reading is None:
            self._send(400, {"errors": ["body must be a JSON object"]})
        elif reading_errors(reading):
            self._send(400, {"errors": reading_errors(reading)})
        else:
            unit = {
                "unit_id": reading["unit_id"],
                "status": battery_status(reading["state_of_charge"]),
                "power_kw": power_kw(reading["voltage_v"], reading["current_a"]),
            }
            self.latest[reading["unit_id"]] = unit
            self._send(201, unit)

    def _logged_in(self):
        sent = self.headers.get("Authorization", "")
        return hmac.compare_digest(sent, f"Bearer {self.token}")

    def _read_json(self):
        length = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(length))
        except ValueError:
            return None
        return body if isinstance(body, dict) else None

    def _send(self, status, body):
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass  # keep the output clean during load tests


def make_server(port, token, host="127.0.0.1"):
    handler = type("AppHandler", (Handler,), {"token": token, "latest": {}})
    return ThreadingHTTPServer((host, port), handler)


if __name__ == "__main__":
    make_server(int(os.environ.get("PORT", 8080)), os.environ["API_TOKEN"], host="0.0.0.0").serve_forever()
