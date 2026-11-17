#!/usr/bin/env python3
"""Loopback-only search UI and Google autocomplete proxy. No query logging."""
import argparse
import json
import threading
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CACHE = {}
LOCK = threading.Lock()
FILES = {"/spotlight-ai": ("index.html", "text/html; charset=utf-8"),
         "/app.js": ("app.js", "text/javascript; charset=utf-8")}


def suggestions(query):
    key = query.casefold()
    with LOCK:
        cached = CACHE.get(key)
    if cached and time.monotonic() - cached[0] < 300:
        return cached[1]
    url = "https://suggestqueries.google.com/complete/search?" + urllib.parse.urlencode(
        {"client": "firefox", "q": query, "hl": "en"})
    request = urllib.request.Request(url, headers={"User-Agent": "SpotlightAISearch/1.0"})
    with urllib.request.urlopen(request, timeout=4) as response:
        data = json.load(response)
    result = [item for item in data[1] if isinstance(item, str)][:5]
    with LOCK:
        if len(CACHE) >= 256:
            CACHE.clear()
        CACHE[key] = (time.monotonic(), result)
    return result


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_GET(self):
        host = self.headers.get("Host", "").split(":")[0]
        if host not in ("127.0.0.1", "localhost"):
            self.send_error(403)
            return
        url = urllib.parse.urlsplit(self.path)
        if url.path == "/api/suggest":
            query = urllib.parse.parse_qs(url.query).get("q", [""])[0].strip()[:200]
            try:
                data = suggestions(query) if query else []
            except (OSError, ValueError, IndexError, TypeError, KeyError):
                data = []
            content, mime = json.dumps(data).encode(), "application/json"
        elif url.path in FILES:
            filename, mime = FILES[url.path]
            content = (ROOT / filename).read_bytes()
        else:
            self.send_error(404)
            return
        try:
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline'; form-action https://www.google.com; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(content)
        except (BrokenPipeError, ConnectionResetError):
            pass


def create_server(port=18476):
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    return server


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=18476)
    args = parser.parse_args()
    with create_server(args.port) as server:
        server.serve_forever()
