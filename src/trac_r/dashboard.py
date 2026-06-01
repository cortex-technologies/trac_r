import http.server
import socketserver
import json
import os
import urllib.parse
import argparse

try:
    from huggingface_hub import HfApi, hf_hub_download
except ImportError:
    HfApi: type["HfApi"] | None = None

PORT = 8000
TRACKER_DIR = "tracker"
REPO_ID: str | None = None


class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)

        # API Endpoint to get all runs
        if parsed_path.path == "/api/runs":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            # Add CORS headers just in case
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            runs = []
            if REPO_ID and HfApi:
                # Cloud Mode
                api = HfApi()
                try:
                    # Get top level directories which are runs
                    repo_files = api.list_repo_files(
                        repo_id=REPO_ID, repo_type="dataset"
                    )

                    # Find all unique run folders
                    run_folders = set()
                    for f in repo_files:
                        if "/" in f and f.startswith("run"):
                            run_folders.add(f.split("/")[0])

                    for run_name in sorted(run_folders, reverse=True):
                        meta = {"run_name": run_name, "timestamp": "Unknown"}
                        # Try to get meta.json
                        if f"{run_name}/meta.json" in repo_files:
                            try:
                                local_meta_path = hf_hub_download(
                                    repo_id=REPO_ID,
                                    repo_type="dataset",
                                    filename=f"{run_name}/meta.json",
                                )
                                with open(local_meta_path, "r") as f:
                                    meta = json.load(f)
                            except Exception:
                                pass
                        meta["folder"] = run_name
                        runs.append(meta)
                except Exception as e:
                    print(f"Error fetching runs from HF: {e}")
            else:
                # Local Mode
                if os.path.exists(TRACKER_DIR):
                    for run_name in sorted(os.listdir(TRACKER_DIR), reverse=True):
                        run_path = os.path.join(TRACKER_DIR, run_name)
                        if os.path.isdir(run_path):
                            meta_path = os.path.join(run_path, "meta.json")
                            meta = {}
                            if os.path.exists(meta_path):
                                with open(meta_path, "r") as f:
                                    meta = json.load(f)
                            else:
                                meta = {"run_name": run_name, "timestamp": "Unknown"}
                            meta["folder"] = run_path
                            runs.append(meta)

            self.wfile.write(json.dumps(runs).encode("utf-8"))
            return

        # API Endpoint to get status
        elif parsed_path.path == "/api/status":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            status = {"mode": "cloud" if REPO_ID else "local", "repo": REPO_ID}
            self.wfile.write(json.dumps(status).encode("utf-8"))
            return

        # Serve the dashboard index for root path
        elif parsed_path.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()

            static_dir = os.path.join(os.path.dirname(__file__), "static")
            index_path = os.path.join(static_dir, "index.html")

            with open(index_path, "rb") as f:
                self.wfile.write(f.read())
            return

        # Fallback to standard static file serving (allows the UI to fetch metrics.csv)
        else:
            # If in cloud mode and requesting a file inside a run folder
            if REPO_ID and HfApi and parsed_path.path.startswith("/run"):
                filename = parsed_path.path.lstrip("/")
                try:
                    local_path = hf_hub_download(
                        repo_id=REPO_ID, repo_type="dataset", filename=filename
                    )
                    with open(local_path, "rb") as f:
                        content = f.read()
                    self.send_response(200)
                    self.send_header(
                        "Content-type",
                        "text/csv" if filename.endswith(".csv") else "application/json",
                    )
                    self.end_headers()
                    self.wfile.write(content)
                    return
                except Exception as e:
                    self.send_error(404, f"File not found on HF Hub: {e}")
                    return

            # Local fallback
            return super().do_GET()


def main():
    global REPO_ID, PORT
    parser = argparse.ArgumentParser(description="Tracker Dashboard")
    parser.add_argument(
        "--repo-id",
        type=str,
        default=os.environ.get("HF_REPO_ID"),
        help="Hugging Face Dataset Repo ID (e.g. username/dataset)",
    )
    parser.add_argument("--port", type=int, default=PORT, help="Port to run on")
    args = parser.parse_args()

    REPO_ID = args.repo_id
    PORT = args.port

    if REPO_ID:
        if not HfApi:
            print("❌ huggingface_hub is not installed! Run `uv add huggingface_hub`")
            exit(1)
        print(f"☁️ Running in CLOUD MODE against Hugging Face Repo: {REPO_ID}")
    else:
        print(f"🏠 Running in LOCAL MODE reading from ./{TRACKER_DIR}")

    # Ensure address can be reused
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), DashboardHandler) as httpd:
        print(f"🚀 Dashboard is live! Open http://localhost:{PORT} in your browser.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down dashboard...")


if __name__ == "__main__":
    main()
