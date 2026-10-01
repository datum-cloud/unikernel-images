"""Default entrypoint: a stdlib HTTP server that answers on port 8080.

Replace /src/server.py (or override the command) to run your own application.
"""

import json
import os
import platform
import socket
from http.server import BaseHTTPRequestHandler, HTTPServer


class DualStackServer(HTTPServer):
    """HTTPServer bound to [::] so it accepts IPv6 and IPv4 (mapped) clients.

    Datum compute networks are IPv6-only, so the stock IPv4 bind is unreachable.
    """

    address_family = socket.AF_INET6

    def server_bind(self):
        try:
            self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        except (AttributeError, OSError):
            pass
        super().server_bind()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps({
            "service": "python",
            "message": "Hello from Python on a Datum unikernel",
            "python": platform.python_version(),
            "path": self.path,
        }).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        print(fmt % args, flush=True)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    print(f"listening on :{port}", flush=True)
    try:
        server = DualStackServer(("::", port), Handler)
    except OSError:
        # Runtime without IPv6 sockets: IPv4 is the only option left.
        server = HTTPServer(("0.0.0.0", port), Handler)
    server.serve_forever()
