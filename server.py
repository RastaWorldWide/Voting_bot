import http.server
import socketserver
from urllib.parse import unquote

class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        if self.path.endswith(".html"):
            self.send_header('Content-Type', 'text/html; charset=utf-8')
        super().end_headers()

PORT = 8080
with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"Serving at http://localhost:{PORT}")
    httpd.serve_forever()