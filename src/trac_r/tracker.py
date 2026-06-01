import os
import csv
import json
import subprocess
import sys
import shutil
import getpass
from datetime import datetime
from typing import TypedDict, NotRequired
from huggingface_hub import HfApi


class ChartConfig(TypedDict):
    title: str
    filename: str
    type: str
    options: dict[str, object]


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

        # Count existing runs to determine run number
        os.makedirs(self.root_dir, exist_ok=True)
        existing_runs = [
            d
            for d in os.listdir(self.root_dir)
            if os.path.isdir(os.path.join(self.root_dir, d))
        ]
        self.run_number = len(existing_runs) + 1

        # Create specific run directory
        dir_name = f"run{self.run_number:03d}_{self.run_name}_{self.timestamp}_{self.git_commit}"
        self.run_dir = os.path.join(self.root_dir, dir_name)
        os.makedirs(self.run_dir, exist_ok=True)

        # Setup CSV log headers tracking
        self.metrics_headers = {}  # Map from filename to list of headers

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
        with open(os.path.join(self.run_dir, "meta.json"), "w") as f:
            json.dump(self.meta, f, indent=4)

    def register_chart(
        self,
        title: str,
        filename: str,
        chart_type: str,
        options: dict[str, object] | None = None,
    ):
        """Registers a custom chart so the UI engine automatically renders it."""
        chart_config: ChartConfig = {
            "title": title,
            "filename": filename,
            "type": chart_type,
            "options": options or {},
        }
        # Avoid duplicating entries
        for existing in self.meta["charts"]:
            if existing["title"] == title:
                existing.update(chart_config)
                self._save_meta()
                return

        self.meta["charts"].append(chart_config)
        self._save_meta()

    def log_metrics(self, filename: str = "metrics.csv", **kwargs):
        """Logs metrics to a CSV file. Dynamically handles headers."""
        data = {}
        data.update(kwargs)

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

        # Handle dynamic new keys gracefully
        for k in data.keys():
            if k not in self.metrics_headers[filename]:
                self.metrics_headers[filename].append(k)

        with open(metrics_file, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.metrics_headers[filename])
            if f.tell() == 0:
                writer.writeheader()
            writer.writerow(data)

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
            print(f"🧹 Cleaning up local folder: {self.run_dir}")
            shutil.rmtree(self.run_dir)

    def save_trajectory(self, true_data, pred_data, filename="trajectory.csv"):
        """
        Saves a 2D trajectory of ground truth vs predicted data to a CSV.
        true_data: numpy array of shape (seq_len, 2+)
        pred_data: numpy array of shape (seq_len, 2+)
        """
        csv_path = os.path.join(self.run_dir, filename)

        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                ["step", "true_dim0", "true_dim1", "pred_dim0", "pred_dim1"]
            )

            max_len = max(len(true_data), len(pred_data))
            for i in range(max_len):
                t0 = true_data[i, 0] if i < len(true_data) else ""
                t1 = true_data[i, 1] if i < len(true_data) else ""
                p0 = pred_data[i, 0] if i < len(pred_data) else ""
                p1 = pred_data[i, 1] if i < len(pred_data) else ""

                writer.writerow([i, t0, t1, p0, p1])

        self.register_chart(
            title="2D Trajectory",
            filename=filename,
            chart_type="scatter",
            options={"equal_aspect": True, "show_lines": True},
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
                    writer.writerow([i, j, matrix_data[i][j], classes[i], classes[j]])

        self.register_chart(
            title=title,
            filename=filename,
            chart_type="heatmap",
            options={"classes": classes},
        )
        print(f"Saved confusion matrix: {csv_path}")
