#!/usr/bin/env python3
import http.server
import json
import os
import sys

PORT = int(os.environ.get("PORT", 8080))
REPO_DIR = os.path.dirname(os.path.abspath(__file__))
FAVORITES_FILE = os.path.join(REPO_DIR, "data", "favorites.json")

class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=REPO_DIR, **kwargs)

    def do_GET(self):
        if self.path == "/api/favorites":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.end_headers()
            
            data = {"favorites": []}
            if os.path.exists(FAVORITES_FILE):
                try:
                    with open(FAVORITES_FILE, "r") as f:
                        data = json.load(f)
                except Exception as e:
                    print(f"Error reading favorites file: {e}")
            self.wfile.write(json.dumps(data).encode("utf-8"))
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == "/api/favorites":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)
            
            try:
                payload = json.loads(post_data.decode("utf-8"))
                
                # Ensure data directory exists
                os.makedirs(os.path.dirname(FAVORITES_FILE), exist_ok=True)
                
                # Write to favorites.json
                with open(FAVORITES_FILE, "w") as f:
                    json.dump(payload, f, indent=2)
                
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success"}).encode("utf-8"))
                print("Successfully saved favorites.json")
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
                print(f"Error handling POST /api/favorites: {e}")
        else:
            self.send_response(404)
            self.end_headers()

if __name__ == "__main__":
    # Change working dir to repo root so relative paths work
    os.chdir(REPO_DIR)
    
    server_address = ("", PORT)
    httpd = http.server.HTTPServer(server_address, CustomHandler)
    print(f"Serving progression dashboard locally on http://localhost:{PORT}")
    print(f"Favorites file will be written to: {FAVORITES_FILE}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.")
        sys.exit(0)
