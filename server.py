#!/usr/bin/env python3
import http.server
import json
import os
import sys

PORT = int(os.environ.get("PORT", 8080))
REPO_DIR = os.path.dirname(os.path.abspath(__file__))
FAVORITES_FILE = os.path.join(REPO_DIR, "data", "favorites.json")

# GCS Persistence Configuration
BUCKET_NAME = os.environ.get("GCS_BUCKET_NAME")
use_gcs = False

if BUCKET_NAME:
    try:
        from google.cloud import storage
        use_gcs = True
        print(f"Using GCS bucket '{BUCKET_NAME}' for favorites persistence.")
    except ImportError:
        print("google-cloud-storage package not found. Falling back to local file persistence.")

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
            if use_gcs:
                try:
                    from google.cloud import storage
                    client = storage.Client()
                    bucket = client.bucket(BUCKET_NAME)
                    blob = bucket.blob("favorites.json")
                    if blob.exists():
                        content = blob.download_as_text()
                        data = json.loads(content)
                except Exception as e:
                    print(f"Error reading favorites from GCS: {e}")
            else:
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
                
                if use_gcs:
                    try:
                        from google.cloud import storage
                        client = storage.Client()
                        bucket = client.bucket(BUCKET_NAME)
                        blob = bucket.blob("favorites.json")
                        blob.upload_from_string(json.dumps(payload, indent=2), content_type="application/json")
                        print(f"Successfully saved favorites to GCS bucket '{BUCKET_NAME}'")
                    except Exception as e:
                        print(f"Error writing favorites to GCS: {e}")
                        # Fallback locally if GCS write fails
                        os.makedirs(os.path.dirname(FAVORITES_FILE), exist_ok=True)
                        with open(FAVORITES_FILE, "w") as f:
                            json.dump(payload, f, indent=2)
                else:
                    # Ensure data directory exists
                    os.makedirs(os.path.dirname(FAVORITES_FILE), exist_ok=True)
                    # Write to favorites.json
                    with open(FAVORITES_FILE, "w") as f:
                        json.dump(payload, f, indent=2)
                    print("Successfully saved favorites.json locally")
                
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success"}).encode("utf-8"))
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
    if use_gcs:
        print(f"GCS Persistence active with bucket: {BUCKET_NAME}")
    else:
        print(f"Local file persistence active at: {FAVORITES_FILE}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.")
        sys.exit(0)
