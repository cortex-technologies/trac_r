# Data Formats

All data lives under `<root_dir>/<run_dir>/`. Default `root_dir` is `tracker`.

---

## Run Directory Naming

```
run<NNN>_<run_name>_<YYYYMMDD_HHMMSS>_<git_commit>/
```

Example: `run003_baseline_20250615_143022_a1b2c3d/`

---

## `meta.json`

Written on tracker init; updated whenever `register_chart` is called.

```json
{
    "run_name": "baseline",
    "run_number": 3,
    "timestamp": "20250615_143022",
    "git_commit": "a1b2c3d",
    "source_script": "train.py",
    "charts": [
        {
            "title": "loss",
            "filename": "metrics.csv",
            "type": "line",
            "series": [{"name": "loss", "x": "step", "y": "loss"}]
        },
        {
            "title": "Confusion Matrix",
            "filename": "confusion.csv",
            "type": "heatmap",
            "series": [{"x": "pred_class", "y": "true_class", "value": "count"}],
            "layout": {"classes": ["cat", "dog", "bird"]}
        }
    ]
}
```

---

## CSV Files

### `metrics.csv` (default)

Written by `log()` / `log_metrics()`. Headers are dynamic — new columns are appended as they appear.

```csv
step,loss,accuracy
1,2.31,0.10
2,2.15,0.15
```

### `trajectory.csv`

Written by `save_trajectory()`. Fixed columns:

```csv
step,true_dim0,true_dim1,pred_dim0,pred_dim1
0,1.0,2.0,1.1,2.2
```

### `confusion.csv`

Written by `save_confusion_matrix()`. Fixed columns:

```csv
true_class,pred_class,count,true_label,pred_label
0,0,50,cat,cat
0,1,5,cat,dog
```

---

## Chart Config Spec

### `type` values

| Value | Rendered as | Chart.js type |
|---|---|---|
| `"line"` | Single-series line | `scatter` + `showLine` |
| `"line_multi"` | Multi-series line | `scatter` + `showLine` |
| `"scatter"` | XY scatter | `scatter` |
| `"heatmap"` | Color matrix | `matrix` (plugin) |

`"line"` and `"line_multi"` are functionally identical at the config level. The frontend treats a chart with one series as `line` and multiple as `line_multi` based on the `series` array length. Both are auto-registered by `log()`.

### Series Objects

Each entry in the `series` array maps CSV columns to chart axes:

```json
{"name": "loss", "x": "step", "y": "loss"}
```

For heatmaps, a `value` key is also used:

```json
{"x": "pred_class", "y": "true_class", "value": "count"}
```

### Layout Object

| Key | Type | Used by | Effect |
|---|---|---|---|
| `equal_aspect` | `bool` | scatter | Forces square canvas, matched X/Y ranges |
| `show_lines` | `bool` | scatter | Connects points with lines |
| `classes` | `list[str]` | heatmap | Axis tick labels |
