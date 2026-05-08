import json
import os
import time
import argparse
from pathlib import Path
from typing import List, Dict
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

class SpatialIntelligenceDashboard:
    """
    Analyzes multiple event types per cell (Hits, Misses, Sinks)
    and provides a multi-panel dashboard.
    """
    def __init__(self, log_dir: str = "game_logs"):
        self.log_dir = Path(log_dir)
        self.size = 10
        self.reset_data()

    def reset_data(self):
        self.hits = np.zeros((self.size, self.size))
        self.misses = np.zeros((self.size, self.size))
        self.sinks = np.zeros((self.size, self.size))
        self.game_count = 0

    def process_logs(self):
        self.reset_data()
        logs = list(self.log_dir.glob("*.json"))
        self.game_count = len(logs)
        
        for log_file in logs:
            try:
                with open(log_file, "r") as f:
                    log_data = json.load(f)
                    events = log_data.get("events", [])
                    for e in events:
                        if e["type"] == "turn":
                            r, c = e["target"]
                            outcome = e.get("outcome")
                            if outcome == "hit":
                                self.hits[r, c] += 1
                            elif outcome == "miss":
                                self.misses[r, c] += 1
                            elif outcome == "sunk":
                                self.hits[r, c] += 1 # A sink is also a hit
                                self.sinks[r, c] += 1
            except Exception as e:
                pass # Silent skip for malformed/locked logs

    def render(self, output_path: str = "stats_viz/spatial_intelligence.png"):
        fig, axes = plt.subplots(1, 3, figsize=(22, 6))
        
        labels = [chr(ord('A')+i) for i in range(self.size)]
        ticks = range(1, self.size + 1)

        # Panel 1: Hits
        sns.heatmap(self.hits, annot=True, fmt=".0f", cmap="YlOrRd", ax=axes[0],
                    xticklabels=labels, yticklabels=ticks)
        axes[0].set_title(f"Hit Density (Total Games: {self.game_count})")

        # Panel 2: Misses
        sns.heatmap(self.misses, annot=True, fmt=".0f", cmap="Blues", ax=axes[1],
                    xticklabels=labels, yticklabels=ticks)
        axes[1].set_title("Miss Density (Where AI guesses wrong)")

        # Panel 3: Sinks
        sns.heatmap(self.sinks, annot=True, fmt=".0f", cmap="Purples", ax=axes[2],
                    xticklabels=labels, yticklabels=ticks)
        axes[2].set_title("Sink Locations (Final Blows)")

        plt.tight_layout()
        plt.savefig(output_path)
        plt.close()
        return output_path

def live_monitor(refresh_sec: int = 5):
    dashboard = SpatialIntelligenceDashboard()
    print(f"Starting Live Spatial Intelligence Monitor (refreshing every {refresh_sec}s)...")
    print("Dashboard will be saved to stats_viz/spatial_intelligence.png")
    
    try:
        while True:
            dashboard.process_logs()
            path = dashboard.render()
            # print(f"[{time.strftime('%H:%M:%S')}] Dashboard updated.")
            time.sleep(refresh_sec)
    except KeyboardInterrupt:
        print("\nMonitor stopped.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="Run in live monitor mode")
    parser.add_argument("--refresh", type=int, default=5, help="Refresh interval in seconds")
    args = parser.parse_args()

    if args.live:
        live_monitor(args.refresh)
    else:
        db = SpatialIntelligenceDashboard()
        db.process_logs()
        db.render()
        print("Dashboard generated: stats_viz/spatial_intelligence.png")
