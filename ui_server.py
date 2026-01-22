import sys
import subprocess
from http.server import SimpleHTTPRequestHandler, HTTPServer
from pathlib import Path

PORT = 8000
traitement_en_cours = False

BASE_DIR = Path(__file__).resolve().parent


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)

    def do_GET(self):
        if self.path == "/api/dashboard":
            self.send_response(200)
            self.send_header("Content-type", "application/json; charset=utf-8")
            self.end_headers()

            result = subprocess.run(
                [sys.executable, str(BASE_DIR / "dashboard.py")],
                capture_output=True,
                text=True,
                cwd=str(BASE_DIR)   # 🔥 LIGNE CRITIQUE
            )

            self.wfile.write(result.stdout.encode("utf-8"))
            return

        super().do_GET()

    def do_POST(self):
        global traitement_en_cours

        if self.path == "/traiter":
            if traitement_en_cours:
                self.send_response(429)
                self.end_headers()
                return

            traitement_en_cours = True

            subprocess.run(
                [sys.executable, str(BASE_DIR / "core" / "traiter_dossier.py")],
                check=False,
                cwd=str(BASE_DIR)   # 🔥 LIGNE CRITIQUE
            )

            traitement_en_cours = False

            self.send_response(302)
            self.send_header("Location", "/dashboard.html")
            self.end_headers()
            return

        self.send_error(404)


if __name__ == "__main__":
    print(f"Interface disponible sur http://localhost:{PORT}")
    HTTPServer(("", PORT), Handler).serve_forever()
