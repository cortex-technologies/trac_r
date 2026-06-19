import os
import re
import csv
import json
import subprocess
import sys

import getpass
from datetime import datetime
from typing import TypedDict, NotRequired
import threading

class ChartConfig(TypedDict):
    title: str
    filename: str
    type: str
    series: NotRequired[list[dict[str, object]]]
    layout: NotRequired[dict[str, object]]


class ExperimentMeta(TypedDict):
    run_name: str
    run_number: int
    timestamp: str
    git_commit: str
    charts: list[ChartConfig]
    source_script: NotRequired[str]


def get_git_commit() -> str:
    """Returns the current short git commit hash, appending '-dirty' if uncommitted changes exist."""
    try:
        commit_hash = (
            subprocess.check_output(["git", "rev-parse", "--short", "HEAD"])
            .decode("ascii")
            .strip()
        )
        status = (
            subprocess.check_output(["git", "status", "--porcelain"])
            .decode("ascii")
            .strip()
        )
        if status:
            return f"{commit_hash}-dirty"
        return commit_hash
    except Exception:
        return "unknown"


class ExperimentTracker:
    def __init__(
        self,
        run_name: str,
        root_dir: str = "tracker",
        hf_token: str | None = None,
    ):
        self.run_name = run_name
        self.root_dir = root_dir
        self.hf_token = hf_token

        # Generate metadata
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.git_commit = get_git_commit()

        # Determine run number from the highest existing run* directory
        os.makedirs(self.root_dir, exist_ok=True)
        max_run = 0
        for d in os.listdir(self.root_dir):
            match = re.match(r"^run(\d+)_", d)
            if match and os.path.isdir(os.path.join(self.root_dir, d)):
                max_run = max(max_run, int(match.group(1)))

        # Create run directory with atomic mkdir to handle parallel launches
        for _ in range(100):
            self.run_number = max_run + 1
            dir_name = f"run{self.run_number:03d}_{self.run_name}_{self.timestamp}_{self.git_commit}"
            self.run_dir = os.path.join(self.root_dir, dir_name)
            try:
                os.mkdir(self.run_dir)
                break
            except FileExistsError:
                max_run = self.run_number
                continue
        else:
            raise RuntimeError(
                f"Failed to create a unique run directory after 100 retries in {self.root_dir}"
            )

        # Setup CSV log headers tracking
        self.metrics_headers = {}  # Map from filename to list of headers
        self._auto_registered_metrics = set()
        self._lock = threading.RLock()

        # Setup metadata dump (useful for loading configs later)
        self.meta: ExperimentMeta = {
            "run_name": self.run_name,
            "run_number": self.run_number,
            "timestamp": self.timestamp,
            "git_commit": self.git_commit,
            "charts": [],  # Dynamic chart registry
        }

        if len(sys.argv) > 0 and os.path.isfile(sys.argv[0]):
            self.meta["source_script"] = os.path.basename(sys.argv[0])

        self._save_meta()

        print(f"Tracking experiment at: {self.run_dir}")

    def _save_meta(self):
        with self._lock:
            with open(os.path.join(self.run_dir, "meta.json"), "w") as f:
                json.dump(self.meta, f, indent=4)

    def register_chart(
        self,
        title: str,
        filename: str,
        chart_type: str,
        series: list[dict[str, object]] | None = None,
        layout: dict[str, object] | None = None,
    ):
        """Registers a custom chart so the UI engine automatically renders it."""
        with self._lock:
            chart_config: ChartConfig = {
                "title": title,
                "filename": filename,
                "type": chart_type,
            }
            if series is not None:
                chart_config["series"] = series
            if layout is not None:
                chart_config["layout"] = layout

            # Avoid duplicating entries
            for existing in self.meta["charts"]:
                if existing["title"] == title:
                    existing.update(chart_config)
                    self._save_meta()
                    return

            self.meta["charts"].append(chart_config)
            self._save_meta()

    def log(
        self,
        metrics: dict[str, object],
        step: int | float | None = None,
        step_label: str = "step",
        filename: str = "metrics.csv",
    ):
        """
        Simplified logging API. Logs metrics and automatically registers line charts
        for any newly seen metric keys.
        """
        data = dict(metrics)
        if step is not None:
            data[step_label] = step

        self.log_metrics(filename, **data)


        for key in metrics.keys():
            if key not in self._auto_registered_metrics and key != step_label:
                self.register_chart(
                    title=f"{key}",
                    filename=filename,
                    chart_type="line",
                    series=[{"name": key, "x": step_label, "y": key}],
                )
                self._auto_registered_metrics.add(key)

    def log_metrics(self, filename: str = "metrics.csv", **kwargs):
        """Logs metrics to a CSV file. Dynamically handles headers."""
        with self._lock:
            data = dict(kwargs)

            metrics_file = os.path.join(self.run_dir, filename)
            file_exists = os.path.isfile(metrics_file)

            if filename not in self.metrics_headers:
                if file_exists:
                    with open(metrics_file, "r") as f:
                        reader = csv.reader(f)
                        try:
                            self.metrics_headers[filename] = next(reader)
                        except StopIteration:
                            self.metrics_headers[filename] = list(data.keys())
                else:
                    self.metrics_headers[filename] = list(data.keys())

            # Check for columns not yet in the header
            new_keys = [
                k for k in data.keys() if k not in self.metrics_headers[filename]
            ]

            if new_keys and file_exists:
                # New columns appeared mid-run — rewrite the file with the expanded header
                self.metrics_headers[filename].extend(new_keys)
                with open(metrics_file, "r", newline="") as f:
                    reader = csv.DictReader(f)
                    existing_rows = list(reader)
                with open(metrics_file, "w", newline="") as f:
                    writer = csv.DictWriter(
                        f, fieldnames=self.metrics_headers[filename]
                    )
                    writer.writeheader()
                    writer.writerows(existing_rows)
                    writer.writerow(data)
            else:
                # No schema change — just append
                self.metrics_headers[filename].extend(new_keys)
                with open(metrics_file, "a", newline="") as f:
                    writer = csv.DictWriter(
                        f, fieldnames=self.metrics_headers[filename]
                    )
                    if f.tell() == 0:
                        writer.writeheader()
                    writer.writerow(data)

    def save_trajectory(self, true_data, pred_data, filename="trajectory.csv"):
        """
        Saves a 2D trajectory of ground truth vs predicted data to a CSV.
        true_data: numpy array of shape (seq_len, 2+)
        pred_data: numpy array of shape (seq_len, 2+)
        """
        with self._lock:
            csv_path = os.path.join(self.run_dir, filename)

            with open(csv_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(
                    ["step", "true_dim0", "true_dim1", "pred_dim0", "pred_dim1"]
                )

                max_len = max(len(true_data), len(pred_data))
                for i in range(max_len):
                    t0 = true_data[i][0] if i < len(true_data) else ""
                    t1 = true_data[i][1] if i < len(true_data) else ""
                    p0 = pred_data[i][0] if i < len(pred_data) else ""
                    p1 = pred_data[i][1] if i < len(pred_data) else ""

                    writer.writerow([i, t0, t1, p0, p1])

            self.register_chart(
                title="2D Trajectory",
                filename=filename,
                chart_type="scatter",
                series=[
                    {"name": "True Path", "x": "true_dim0", "y": "true_dim1"},
                    {"name": "Prediction", "x": "pred_dim0", "y": "pred_dim1"},
                ],
                layout={"equal_aspect": True, "show_lines": True},
            )
            print(f"Saved trajectory data: {csv_path}")

    def save_confusion_matrix(
        self,
        matrix_data,
        classes=None,
        title="Confusion Matrix",
        filename="confusion.csv",
    ):
        """
        Saves a confusion matrix to CSV and registers it for the UI.
        matrix_data: 2D numpy array or nested list [true_class][pred_class]
        classes: List of string labels for the classes.
        """
        with self._lock:
            csv_path = os.path.join(self.run_dir, filename)
            num_classes = len(matrix_data)
            if classes is None:
                classes = [f"Class {i}" for i in range(num_classes)]

            with open(csv_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(
                    ["true_class", "pred_class", "count", "true_label", "pred_label"]
                )

                for i in range(num_classes):
                    for j in range(num_classes):
                        writer.writerow(
                            [i, j, matrix_data[i][j], classes[i], classes[j]]
                        )

            self.register_chart(
                title=title,
                filename=filename,
                chart_type="heatmap",
                series=[{"x": "pred_class", "y": "true_class", "value": "count"}],
                layout={"classes": classes},
            )
            print(f"Saved confusion matrix: {csv_path}")

    def sync_to_hf(self, repo_id: str, cleanup: bool = False):
        """
        Uploads the run directory to Hugging Face and optionally deletes it locally.
        """
        token = self.hf_token or os.environ.get("HF_TOKEN")

        if not token:
            print("⚠️  Hugging Face token missing!")
            print("Get your free token at: https://huggingface.co/settings/tokens")
            token = getpass.getpass(
                "Paste your HF Read/Write Token here (input is hidden): "
            )
            self.hf_token = token  # Save it in memory for subsequent pushes

        from huggingface_hub import HfApi

        api = HfApi(token=token)
        run_folder_name = os.path.basename(self.run_dir)

        print(f"☁️ Uploading run '{run_folder_name}' to Hugging Face Hub ({repo_id})...")
        api.upload_folder(
            folder_path=self.run_dir,
            repo_id=repo_id,
            repo_type="dataset",
            path_in_repo=run_folder_name,
        )
        print("✅ Upload complete!")

        if cleanup:
            import shutil
            print(f"🧹 Cleaning up local folder: {self.run_dir}")
            shutil.rmtree(self.run_dir)