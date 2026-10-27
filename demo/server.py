"""Lightweight HTTP server to serve local demo web forms."""
from __future__ import annotations

import functools
import http.server
import socketserver
import threading
from pathlib import Path
from typing import Optional


class DemoServer:
    """Threaded local HTTP server for the demo web form application."""

    def __init__(self, port: int = 8080, directory: Optional[str | Path] = None):
        self.port = port
        self.directory = Path(directory) if directory else Path(__file__).parent.resolve()
        self.httpd: Optional[socketserver.TCPServer] = None
        self.thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Starts the HTTP server on a daemon background thread."""
        handler_class = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(self.directory))
        
        # Allow immediate socket reuse
        socketserver.TCPServer.allow_reuse_address = True
        self.httpd = socketserver.TCPServer(("127.0.0.1", self.port), handler_class)

        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        print(f"Demo server started at http://127.0.0.1:{self.port} serving '{self.directory}'")

    def stop(self) -> None:
        """Shuts down the HTTP server."""
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()
            self.httpd = None
            print("Demo server stopped.")


if __name__ == "__main__":
    import time
    server = DemoServer(8080)
    server.start()
    print("Serving demo application. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.stop()
