# Python 3 server example
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

_DEFAULT_HOSTNAME = "localhost"
_DEFAULT_PORT = 8080


class MyServer(BaseHTTPRequestHandler):
    def do_GET(self):
        headers = str(self.headers).strip('\r\n')
        print(
            f"\n\n#####\n# POST request\n# Path: {self.path}\n# Headers:\n{headers} ")
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(bytes("123321", "utf-8"))

    def do_POST(self):
        if self.headers['Content-type'] == 'application/json':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
        else:
            post_data = None

        headers = str(self.headers).strip('\r\n')
        print(f"\n\n#####\n# POST request\n# Path: {self.path}\n# Params:\n{post_data}\n# Headers:\n{headers} ")
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(bytes("111111", "utf-8"))


if __name__ == "__main__":
    if len(sys.argv) > 1:
        server_port = int(sys.argv[1])
    else:
        server_port = _DEFAULT_PORT
    webServer = HTTPServer((_DEFAULT_HOSTNAME, server_port), MyServer)
    print("Server started http://%s:%s" % (_DEFAULT_HOSTNAME, server_port))

    try:
        webServer.serve_forever()
    except KeyboardInterrupt:
        pass

    webServer.server_close()
    print("Server stopped.")
