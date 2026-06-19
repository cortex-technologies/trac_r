import math
import random
import time
import os
import sys

# Add the parent directory to sys.path so we can import trac_r if running from src/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.trac_r import ExperimentTracker

def main():
    # Initialize the tracker
    tracker = ExperimentTracker(run_name="dummy_training_test")
    
    print(f"Tracking experiment at: {tracker.run_dir}")
    
    # 1. Log scalar metrics over time
    print("Logging scalar metrics...")
    
    # Manually register a combined chart for train and val loss on the same graph
    tracker.register_chart(
        title="Train vs Val Loss",
        filename="metrics.csv",
        chart_type="line",
        series=[
            {"name": "Train Loss", "x": "epoch", "y": "train_loss"},
            {"name": "Val Loss", "x": "epoch", "y": "val_loss"}
        ]
    )
    
    epochs = 20
    for epoch in range(epochs):
        # Dummy metrics
        train_loss = math.exp(-0.2 * epoch) + random.gauss(0, 0.05)
        val_loss = math.exp(-0.18 * epoch) + random.gauss(0, 0.08) + 0.1 # Slightly higher and noisier
        accuracy = 1.0 - math.exp(-0.2 * epoch) + random.gauss(0, 0.02)
        learning_rate = 0.01 * (0.9 ** epoch)
        
        tracker.log(
            metrics={
                "train_loss": train_loss,
                "val_loss": val_loss,
                "val_accuracy": accuracy,
                "learning_rate": learning_rate,
            },
            step=epoch,
            step_label="epoch"
        )
        time.sleep(0.05) # Simulate training time
        
    # 2. Save a trajectory (e.g., ground truth vs predicted positions)
    print("Logging trajectory data...")
    seq_len = 100
    true_data = []
    pred_data = []
    
    for i in range(seq_len):
        t = i * (4 * math.pi / seq_len)
        
        # True trajectory (spiral)
        true_x = t * math.cos(t)
        true_y = t * math.sin(t)
        true_data.append([true_x, true_y])
        
        # Predicted trajectory (noisy spiral)
        pred_x = true_x + random.gauss(0, 1.0)
        pred_y = true_y + random.gauss(0, 1.0)
        pred_data.append([pred_x, pred_y])
        
    tracker.save_trajectory(true_data, pred_data)
    
    # 3. Save a confusion matrix
    print("Logging confusion matrix...")
    classes = ["Cat", "Dog", "Bird", "Fish", "Reptile"]
    num_classes = len(classes)
    
    # Create a dummy confusion matrix (diagonal heavy)
    matrix_data = []
    for i in range(num_classes):
        row = []
        for j in range(num_classes):
            if i == j:
                row.append(random.randint(50, 100))
            else:
                row.append(random.randint(0, 15))
        matrix_data.append(row)
    
    tracker.save_confusion_matrix(matrix_data, classes=classes)

    # 4. Custom Scatter Plot
    print("Logging custom scatter plot...")
    # Register the chart manually
    tracker.register_chart(
        title="Clustering Scatter",
        filename="clusters.csv",
        chart_type="scatter",
        series=[
            {"name": "Cluster A", "x": "A_x", "y": "A_y"},
            {"name": "Cluster B", "x": "B_x", "y": "B_y"}
        ]
    )
    
    # Generate some random clustered data
    for _ in range(50):
        # Cluster A is centered at (2, 2)
        # Cluster B is centered at (-2, -2)
        tracker.log_metrics(
            filename="clusters.csv",
            A_x=random.gauss(2, 0.5),
            A_y=random.gauss(2, 0.5),
            B_x=random.gauss(-2, 0.8),
            B_y=random.gauss(-2, 0.8)
        )
    
    print(f"Dummy training finished. Data saved to: {tracker.run_dir}")

if __name__ == "__main__":
    main()
