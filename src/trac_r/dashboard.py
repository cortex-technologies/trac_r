import http.server
import socketserver
import json
import os
import urllib.parse
import argparse
from typing import Any

try:
    from huggingface_hub import HfApi, hf_hub_download
except ImportError:
    HfApi: type["HfApi"] | None = None

from .utils import local_network_ip


class DashboardServer(socketserver.TCPServer):
    allow_reuse_address = True

    def __init__(
        self, server_address, handler_class, repo_id=None, tracker_dir="tracker"
    ):
        self.repo_id = repo_id
        self.tracker_dir = tracker_dir

        if repo_id and not HfApi:
            raise ModuleNotFoundError(
                "❌ huggingface_hub is not installed! Run `uv add huggingface_hub`"
            )

        if repo_id:
            print(f"☁️ Running in CLOUD MODE against Hugging Face Repo: {repo_id}")
        else:
            print(f"🏠 Running in LOCAL MODE reading from ./{tracker_dir}")

        super().__init__(server_address, handler_class)


class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        assert isinstance(self.server, DashboardServer)
        repo_id = self.server.repo_id
        tracker_dir = self.server.tracker_dir

        # API Endpoint to get all runs
        if parsed_path.path == "/api/runs":
            self.send_response(200)
            self.send_header("Content-type", "application/json; charset=utf-8")
            # Add CORS headers just in case
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            runs = []
            if repo_id and HfApi:
                # Cloud Mode
                api = HfApi()
                try:
                    # Get top level directories which are runs
                    repo_files = api.list_repo_files(
                        repo_id=repo_id, repo_type="dataset"
                    )

                    # Find all unique run folders and their files
                    run_folders = set()
                    run_files = {}
                    for f in repo_files:
                        if "/" in f and f.startswith("run"):
                            folder, filename = f.split("/", 1)
                            run_folders.add(folder)
                            run_files.setdefault(folder, []).append(filename)

                    for run_name in sorted(run_folders, reverse=True):
                        meta = {"run_name": run_name, "timestamp": "Unknown"}
                        # Try to get meta.json
                        if f"{run_name}/meta.json" in repo_files:
                            try:
                                local_meta_path = hf_hub_download(
                                    repo_id=repo_id,
                                    repo_type="dataset",
                                    filename=f"{run_name}/meta.json",
                                )
                                with open(local_meta_path, "r") as f:
                                    meta = json.load(f)
                            except Exception:
                                pass
                        meta["folder"] = run_name
                        meta["files"] = run_files.get(run_name, [])
                        runs.append(meta)
                except Exception as e:
                    print(f"Error fetching runs from HF: {e}")
            else:
                if os.path.exists(tracker_dir):
                    for run_name in sorted(os.listdir(tracker_dir), reverse=True):
                        run_path = os.path.join(tracker_dir, run_name)
                        if os.path.isdir(run_path):
                            meta_path = os.path.join(run_path, "meta.json")
                            meta: dict[str, Any] = {}
                            if os.path.exists(meta_path):
                                with open(meta_path, "r") as f:
                                    meta = json.load(f)
                            else:
                                meta = {"run_name": run_name, "timestamp": "Unknown"}
                            meta["folder"] = run_name
                            try:
                                meta["files"] = os.listdir(run_path)
                            except Exception:
                                meta["files"] = []
                            runs.append(meta)

            # print(runs)
            self.wfile.write(json.dumps(runs).encode("utf-8"))
            return

        # API Endpoint to get status
        elif parsed_path.path == "/api/status":
            self.send_response(200)
            self.send_header("Content-type", "application/json; charset=utf-8")
            self.end_headers()
            status = {
                "mode": "cloud" if repo_id else "local",
                "repo": repo_id,
            }
            self.wfile.write(json.dumps(status).encode("utf-8"))
            return

        # Serve the dashboard index for root path
        elif parsed_path.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
            self.end_headers()

            static_dir = os.path.join(os.path.dirname(__file__), "static")
            index_path = os.path.join(static_dir, "index.html")

            with open(index_path, "rb") as f:
                self.wfile.write(f.read())
            return

        # Serve run data files (CSV / JSON) from tracker directory or HF Hub
        else:
            # Cloud mode: lazy-download from HF Hub
            if repo_id and HfApi and parsed_path.path.startswith("/run"):
                filename = parsed_path.path.lstrip("/")
                try:
                    local_path = hf_hub_download(
                        repo_id=repo_id, repo_type="dataset", filename=filename
                    )
                    with open(local_path, "rb") as f:
                        content = f.read()
                    self.send_response(200)
                    content_type = (
                        "text/csv; charset=utf-8"
                        if filename.endswith(".csv")
                        else "application/json; charset=utf-8"
                    )
                    self.send_header("Content-type", content_type)
                    self.end_headers()
                    self.wfile.write(content)
                    return
                except Exception as e:
                    self.send_error(404, f"File not found on HF Hub: {e}")
                    return

            # Local mode: only serve files that resolve inside TRACKER_DIR
            requested = urllib.parse.unquote(parsed_path.path).lstrip("/")
            tracker_root = os.path.realpath(tracker_dir)
            local_path = os.path.realpath(os.path.join(tracker_dir, requested))
            if not local_path.startswith(tracker_root + os.sep) or not os.path.isfile(
                local_path
            ):
                self.send_error(404, "Not Found")
                return
            self.send_response(200)
            content_type = (
                "text/csv; charset=utf-8"
                if local_path.endswith(".csv")
                else "application/json; charset=utf-8"
            )
            self.send_header("Content-type", content_type)
            self.end_headers()
            with open(local_path, "rb") as f:
                self.wfile.write(f.read())


def main():
    local_network_ip()

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo-id",
        type=str,
        default=os.environ.get("HF_REPO_ID"),
        help="Hugging Face Dataset Repo ID (e.g. username/dataset)",
    )
    parser.add_argument("--port", type=int, default=8000, help="Port to run on")
    parser.add_argument(
        "--tracker-dir",
        type=str,
        default="tracker",
        help="Local directory to scan for runs",
    )
    args = parser.parse_args()

    repo_id = args.repo_id
    port = args.port
    tracker_dir = args.tracker_dir

    with DashboardServer(
        ("", port), DashboardHandler, repo_id=repo_id, tracker_dir=tracker_dir
    ) as httpd:
        print(f"🚀 Dashboard is live! Ctrl / Cmd Click >>> http://localhost:{port} <<<")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down dashboard...")


if __name__ == "__main__":
    main()
