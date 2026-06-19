# Tracker Module

**File:** `src/trac_r/tracker.py`  
**Public export:** `from trac_r import ExperimentTracker`

---

## Types

### `ChartConfig` (TypedDict)

Stored inside `meta.json` to tell the dashboard how to render a chart.

| Field | Type | Required | Description |
|---|---|---|---|
| `title` | `str` | yes | Chart title shown in the UI |
| `filename` | `str` | yes | CSV file the chart reads from |
| `type` | `str` | yes | `"line"`, `"scatter"`, or `"heatmap"` |
| `series` | `list[dict]` | no | Column mappings (see [data_formats.md](data_formats.md#series-objects)) |
| `layout` | `dict` | no | Rendering hints (`equal_aspect`, `show_lines`, `classes`) |

### `ExperimentMeta` (TypedDict)

The shape of `meta.json` written per run.

| Field | Type | Required | Description |
|---|---|---|---|
| `run_name` | `str` | yes | User-supplied name |
| `run_number` | `int` | yes | Auto-incremented |
| `timestamp` | `str` | yes | `YYYYMMDD_HHMMSS` |
| `git_commit` | `str` | yes | Short hash, may have `-dirty` suffix |
| `charts` | `list[ChartConfig]` | yes | Registered chart configurations |
| `source_script` | `str` | no | Basename of the calling script |

---

## Free Function

### `get_git_commit() → str`

Returns the current short git hash. Appends `-dirty` if `git status --porcelain` is non-empty. Returns `"unknown"` on any error.

---

## Class: `ExperimentTracker`

### Constructor

```python
ExperimentTracker(
    run_name: str,
    root_dir: str = "tracker",
    hf_token: str | None = None,
)
```

1. Records timestamp and git commit.
2. Counts existing subdirectories in `root_dir` to derive `run_number`.
3. Creates the run directory: `<root_dir>/run<NNN>_<name>_<timestamp>_<commit>/`.
4. Writes initial `meta.json`.

### Instance Attributes

| Attribute | Type | Description |
|---|---|---|
| `run_name` | `str` | Name of this run |
| `root_dir` | `str` | Parent tracker directory |
| `hf_token` | `str \| None` | HF token (can be set later via `sync_to_hf`) |
| `run_number` | `int` | Sequential run number |
| `run_dir` | `str` | Full path to this run's directory |
| `timestamp` | `str` | `YYYYMMDD_HHMMSS` |
| `git_commit` | `str` | Short hash |
| `meta` | `ExperimentMeta` | In-memory metadata dict |
| `metrics_headers` | `dict[str, list[str]]` | Tracks CSV column order per file |

### Methods

#### `log(metrics, step=None, step_label="step", filename="metrics.csv")`

High-level logging API. Delegates to `log_metrics` and auto-registers a line chart for each new metric key.

| Param | Type | Default | Description |
|---|---|---|---|
| `metrics` | `dict[str, object]` | — | Key-value pairs to log |
| `step` | `int \| float \| None` | `None` | X-axis value; omitted if `None` |
| `step_label` | `str` | `"step"` | Column name for the step value |
| `filename` | `str` | `"metrics.csv"` | Target CSV file |

#### `log_metrics(filename="metrics.csv", **kwargs)`

Low-level CSV writer. Appends one row. Dynamically expands headers if new keys appear.

#### `register_chart(title, filename, chart_type, series=None, layout=None)`

Adds or updates a `ChartConfig` entry in `meta.json`. De-duplicates by `title`.

#### `save_trajectory(true_data, pred_data, filename="trajectory.csv")`

Writes a 2D trajectory CSV with columns `step, true_dim0, true_dim1, pred_dim0, pred_dim1`. Registers a scatter chart with `equal_aspect` and `show_lines`.

**Inputs:** numpy arrays of shape `(seq_len, 2+)`.

#### `save_confusion_matrix(matrix_data, classes=None, title="Confusion Matrix", filename="confusion.csv")`

Writes a confusion matrix CSV with columns `true_class, pred_class, count, true_label, pred_label`. Registers a heatmap chart.

**Inputs:** 2D numpy array or nested list `[true][pred]`. `classes` is an optional list of string labels.

#### `sync_to_hf(repo_id, cleanup=False)`

Uploads the run directory to a Hugging Face Dataset repo. See [cloud_sync.md](cloud_sync.md).

#### `_save_meta()`

Internal. Writes `self.meta` to `<run_dir>/meta.json`.
