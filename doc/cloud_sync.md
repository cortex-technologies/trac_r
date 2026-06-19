# Cloud Sync — Hugging Face Integration

trac_r uses Hugging Face Hub for optional cloud storage. No account or config is needed for local-only use.

---

## Upload (Tracker Side)

### `ExperimentTracker.sync_to_hf(repo_id, cleanup=False)`

1. Resolves token: `self.hf_token` → `$HF_TOKEN` env var → interactive `getpass` prompt.
2. Calls `HfApi.upload_folder()`:
   - `folder_path`: the run directory.
   - `repo_id`: e.g. `"username/dataset-name"`.
   - `repo_type`: `"dataset"`.
   - `path_in_repo`: the run folder basename (e.g. `run001_my_run_20250615_...`).
3. If `cleanup=True`, deletes the local run directory after upload.

### Resulting repo structure

```
username/dataset-name/
├── run001_first_20250101_abc1234/
│   ├── meta.json
│   └── metrics.csv
├── run002_second_20250102_def5678/
│   ├── meta.json
│   ├── metrics.csv
│   └── confusion.csv
└── ...
```

---

## Download (Dashboard Side)

When `--repo-id` is passed to `trac-r`:

1. **`/api/runs`** calls `HfApi().list_repo_files()`, groups by `run*/` prefix, and lazy-downloads each `meta.json` via `hf_hub_download` (cached by the HF client).
2. **CSV requests** (`/<run_dir>/<file>`) are intercepted in `DashboardHandler.do_GET`. The file is downloaded via `hf_hub_download` and served.

All downloads go through `huggingface_hub`'s local cache — repeat requests are fast.

---

## Token Resolution Order

1. `hf_token` constructor arg
2. `$HF_TOKEN` environment variable
3. Interactive `getpass` prompt (upload only)
