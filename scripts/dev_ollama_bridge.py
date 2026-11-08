"""Local Docker Desktop bridge for WSL development; never part of the deployed stack.

Run in a container published only to localhost:11435. Cluster pods reach Ollama
directly; this bridge is for WSL commands when Windows firewall blocks the WSL gateway.
"""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen


class Bridge(BaseHTTPRequestHandler):
    def forward(self):
        if not self.path.startswith("/api/"):
            self.send_error(404)
            return
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        req = Request(
            "http://host.docker.internal:11434" + self.path,
            data=body if self.command == "POST" else None,
            headers={"Content-Type": "application/json"},
            method=self.command,
        )
        try:
            result = urlopen(req, timeout=300)
        except HTTPError as exc:
            result = exc
        data = result.read()
        self.send_response(result.status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    do_GET = forward
    do_POST = forward


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 11435), Bridge).serve_forever()
