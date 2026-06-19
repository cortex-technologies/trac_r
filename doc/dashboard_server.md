# Dashboard Server

**File:** `src/trac_r/dashboard.py`

---


## Class: `DashboardHandler`

Extends `http.server.SimpleHTTPRequestHandler`. Overrides `do_GET` to handle custom routes.

### Routes

| Path | Response | Description |
|---|---|---|
| `/` | `text/html` | Serves `static/index.html` with `no-cache` headers |
| `/api/runs` | `application/json` | Returns a JSON array of run metadata objects |
| `/api/status` | `application/json` | Returns `{"mode": "local"|"cloud", "repo": ...}` |
| `/<run_dir>/<file>` | `text/csv` / `application/json` | In cloud mode: lazy-downloads from HF. In local mode: falls through to `SimpleHTTPRequestHandler` |

### `/api/runs` — Detail

**Local mode:** Scans `TRACKER_DIR` for subdirectories. For each, reads `meta.json` if present. Adds `folder` (relative path) and `files` (directory listing) to each entry. Returns sorted newest-first.

**Cloud mode:** Calls `HfApi().list_repo_files()`. Groups files by top-level `run*` folder. Downloads `meta.json` via `hf_hub_download` for each run. Returns sorted newest-first.

---

## Function: `main()`

CLI entry point registered as `trac-r` in `pyproject.toml`.

### Arguments

| Flag | Type | Default | Description |
|---|---|---|---|
| `--repo-id` | `str` | `$HF_REPO_ID` env var | HF dataset repo; enables cloud mode |
| `--port` | `int` | `8000` | Server port |
| `--tracker-dir`| `str` | `"tracker"` | Local directory to scan for runs |

### Behaviour

1. Parses args.
2. Injects `repo_id` and `tracker_dir` into the request handler using `functools.partial`.
3. Prints mode banner (local or cloud).
4. Starts `socketserver.TCPServer` with `allow_reuse_address = True`.
5. Serves until `KeyboardInterrupt`.
