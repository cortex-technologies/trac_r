# Dashboard Frontend

**File:** `src/trac_r/static/index.html`  
Single-file SPA — all HTML, CSS, and JS inlined.

---

## External Dependencies (CDN)

| Library | Version | Purpose |
|---|---|---|
| `chart.js` | latest | Line and scatter charts |
| `chartjs-chart-matrix` | 2.0.1 | Heatmap / confusion matrix chart type |

---

## Layout

```
┌──────────────┬──────────────────────────────┐
│   Sidebar    │        Main Content          │
│              │                              │
│ Status badge │  Header row:                 │
│ "Clear All"  │    Run title + layout ctrl   │
│              │                              │
│ Run list     │  Warnings container          │
│  (checkboxes)│                              │
│              │  Charts grid                 │
│              │   (auto-fit, configurable)   │
└──────────────┴──────────────────────────────┘
```

- **Sidebar** (300px): Lists all runs as checkboxes. Multiple runs can be selected for overlay comparison.
- **Main content**: Responsive CSS grid of chart boxes.

---

## Global State

| Variable | Type | Purpose |
|---|---|---|
| `allRuns` | `Array` | Full run list from `/api/runs` |
| `selectedRuns` | `Array` | Currently checked runs |
| `chartInstances` | `Object` | Map of chart ID → Chart.js instance (for cleanup) |
| `chartConfigs` | `Object` | Map of chart ID → aggregated config + data from all selected runs |
| `currentLoadId` | `int` | Debounce counter; stale fetches are discarded |

---

## Key Functions

### `fetchRuns()`

Calls `GET /api/runs`. Populates sidebar. Auto-selects the first run.

### `fetchStatus()`

Calls `GET /api/status`. Sets the sidebar badge to "☁️ Cloud" or "🏠 Local".

### `loadMultipleRunsData()`

Core data-loading function. For each selected run:

1. Collects CSV filenames to fetch from the run's `charts` array.
2. Fetches each CSV, parses headers and rows.
3. Builds `chartConfigs` entries keyed by a sanitized chart ID.
4. Handles line/scatter charts (overlaid across runs) and non-line charts (heatmaps — controlled by the "Non-Line Charts" dropdown: latest only / all / none).
5. Calls `createChartDOM()` to inject the HTML, then `updateChart()` for each.

### `createChartDOM(id, title, type, layout)`

Returns an HTML string for a chart box containing:
- Controls bar: Log Y toggle, smoothing slider, equal-aspect toggle (conditional).
- Canvas element inside a sized container.

### `updateChart(id)`

Reads the current control state (log scale, smoothing weight, equal aspect) and the aggregated `chartConfigs[id]`, then builds and instantiates a Chart.js chart.

| Chart type | Chart.js type | Notes |
|---|---|---|
| `line` | `scatter` (with `showLine: true`) | Raw + smoothed traces when smoothing > 0 |
| `line_multi` | `scatter` | Multiple series; dashed lines for series index > 0 |
| `scatter` | `scatter` | Supports `show_lines` and `equal_aspect` layout |
| `heatmap` | `matrix` | Uses `chartjs-chart-matrix`; color intensity = count/max |

### `calculateEMA(data, weight)`

Exponential moving average. `weight = 0` returns raw data. Used for the smoothing slider.

---

## Multi-Run Comparison

When multiple runs are selected:
- Line/scatter charts overlay datasets using per-run colors from `RUN_COLORS`.
- Labels include the run name for disambiguation.
- Non-line charts (heatmaps) are controlled by the dropdown: show only latest, show all, or hide.

---

## Layout Control

The "Layout" dropdown sets `grid-template-columns` on the charts container:
- **Auto**: `repeat(auto-fit, minmax(450px, 1fr))`
- **1 / 2 / 3**: Fixed column count.

After changing, all chart instances are resized via `chart.resize()`.
