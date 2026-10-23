from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

from app.features.pathway import verification


def test_certificate_probe_does_not_follow_redirects_to_another_resource():
    visited: list[str] = []

    class Redirect(BaseHTTPRequestHandler):
        def do_HEAD(self):  # noqa: N802
            visited.append(self.path)
            self.send_response(302)
            self.send_header("Location", "/private-resource")
            self.end_headers()

        def log_message(self, *_args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Redirect)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        assert verification.probe(f"http://127.0.0.1:{server.server_port}/certificate") == 302
        assert visited == ["/certificate"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
