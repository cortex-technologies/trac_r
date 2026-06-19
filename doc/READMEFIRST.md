# trac_r — Documentation Index

A local-first, cloud-native, lazy-loading ML experiment tracker.

## Architecture

| Document | Covers |
|---|---|
| [overview.md](overview.md) | High-level architecture, data flow, project layout |
| [tracker.md](tracker.md) | `ExperimentTracker` class — all methods, types, storage format |
| [dashboard_server.md](dashboard_server.md) | `DashboardHandler`, REST API endpoints, CLI entry point |
| [dashboard_frontend.md](dashboard_frontend.md) | Single-page HTML/JS UI, Chart.js rendering, multi-run comparison |
| [cloud_sync.md](cloud_sync.md) | Hugging Face Hub integration (upload + lazy download) |
| [data_formats.md](data_formats.md) | `meta.json` schema, CSV conventions, chart config spec |
