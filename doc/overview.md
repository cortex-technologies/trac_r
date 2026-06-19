# Architecture Overview

## What trac_r does

trac_r is a zero-config ML experiment tracker. A training script creates an `ExperimentTracker`, calls `log()` each step, and the tracker writes CSV files + a `meta.json` into a local `tracker/` directory. A built-in HTTP dashboard reads those files and renders interactive Chart.js charts. Optionally, runs can be uploaded to a Hugging Face Dataset repo and the dashboard can stream them back.

## Project Layout

```
pyproject.toml               # Package config, CLI entry point
src/trac_r/
├── __init__.py              # Re-exports ExperimentTracker
├── tracker.py               # Core tracking logic (write-side)
├── dashboard.py             # HTTP server + CLI (read-side)
└── static/
    └── index.html           # Single-file SPA (HTML + CSS + JS)
```

## Data Flow

```
Training Script
    │
    ▼
ExperimentTracker            ──► tracker/<run_dir>/meta.json
  .log()                     ──► tracker/<run_dir>/metrics.csv
  .save_trajectory()         ──► tracker/<run_dir>/trajectory.csv
  .save_confusion_matrix()   ──► tracker/<run_dir>/confusion.csv
  .sync_to_hf()              ──► Hugging Face Dataset repo
    │
    ▼
DashboardHandler (HTTP)
  GET /api/runs              ──► lists runs (local dirs or HF repo)
  GET /api/status            ──► returns mode (local / cloud)
  GET /<run_dir>/<file>      ──► serves CSV/JSON (local fs or hf_hub_download)
  GET /                      ──► serves index.html
    │
    ▼
index.html (browser)
  fetchRuns()                ──► sidebar with checkboxes
  loadMultipleRunsData()     ──► fetches CSVs, builds Chart.js datasets
  updateChart()              ──► renders line / scatter / heatmap charts
```

## Dependencies

| Package | Purpose |
|---|---|
| `huggingface_hub` | Upload runs (`HfApi.upload_folder`) and lazy-download in cloud mode (`hf_hub_download`) |
| `chart.js` (CDN) | Line, scatter rendering in the dashboard |
| `chartjs-chart-matrix` (CDN) | Heatmap / confusion matrix rendering |

No other runtime dependencies. Python ≥ 3.12.

## Entry Point

`pyproject.toml` defines the CLI script:

```toml
[project.scripts]
trac-r = "trac_r.dashboard:main"
```

Running `trac-r` launches the HTTP dashboard on port 8000.
