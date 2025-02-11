import http.server
import os
import socketserver
from urllib.parse import urlparse, parse_qs

from .template_processors import SearchTemplate


class Home(http.server.CGIHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        # Set the static files directory
        self.static_dir = os.path.join(os.path.dirname(__file__), "static")
        super().__init__(*args, directory=self.static_dir, **kwargs)

    def process_post(self):
        content_length = int(self.headers["Content-Length"])
        raw_post_data = self.rfile.read(content_length).decode("utf-8")
        post_data = dict(
            data.split("=") for data in raw_post_data.split("&") if "token" not in data
        )
        return post_data

    def do_GET(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        if path.startswith("/static/"):
            # Adjust the path to serve from the static directory
            self.path = path[7:]  # Remove "/static/" prefix
            super().do_GET()

        # Get params
        query_params = parse_qs(parsed_url.query)
        search = query_params.get("search", None) or query_params.get("s", None)
        force_cache = query_params.get("force_cache", None)
        if search:
            search = search[0]
        if force_cache:
            force_cache = True if force_cache[0] == "on" else False
        # Template
        template = SearchTemplate(search, force_cache)
        render = template.render()

        # Render Response
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(render.encode())


class Server:
    PORT = 1234

    def __init__(self):
        socketserver.TCPServer.allow_reuse_address = True

    def run(self):
        with socketserver.TCPServer(("", self.PORT), Home) as httpd:  # type: ignore
            print(f"Serving at http://localhost:{self.PORT}")
            print("Press CTRL-D to finish the proccesses.")
            httpd.serve_forever()
