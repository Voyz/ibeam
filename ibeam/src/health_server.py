import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
import logging

_LOGGER = logging.getLogger('ibeam.' + Path(__file__).stem)


def new_health_server(port: int, check_status, get_shutdown_status):
    class HealthzHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/livez":
                return self._live()
            elif self.path == "/readyz":
                return self._ready()
            self.send_error(404, "Not Found")

        def _live(self):
            if get_shutdown_status():
                self._send_500()
            else:
                self._send_ok()

        def _ready(self):
            status = check_status()
            if not status.authenticated:
                return self._not_ready()
            self._send_ok()

        def _send_ok(self):
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write("OK".encode())

        def _send_500(self):
            self.send_response(500)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write("Internal Error".encode())

        def _not_ready(self):
            self.send_response(503)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write("Not Ready".encode())

    server = HTTPServer(('', port), HealthzHandler)
    threading.Thread(target=server.serve_forever).start()
    _LOGGER.info(f'Health server started at port={port}')
    return server
