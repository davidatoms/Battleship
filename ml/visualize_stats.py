import json
import os
from pathlib import Path
from typing import List, Dict
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

def load_all_logs(log_dir: str = "game_logs") -> List[Dict]:
    logs = []
    path = Path(log_dir)
    for log_file in path.glob("*.json"):
        try:
            with open(log_file, "r") as f:
                logs.append(json.load(f))
        except Exception as e:
            print(f"Skipping {log_file}: {e}")
    return logs

def generate_summary_visuals(logs: List[Dict], output_dir: str = "stats_viz"):
    if not logs:
        print("No logs found to visualize.")
        return

    os.makedirs(output_dir, exist_ok=True)
    
    # Data extraction
    ai_stats = {} # {AI_Name: [turns_to_win, ...]}
    hit_locations = np.zeros((10, 10))
    
    for log in logs:
        # Check if game was won
        events = log.get("events", [])
        game_end = next((e for e in events if e["type"] == "game_end"), None)
        game_start = next((e for e in events if e["type"] == "game_start"), None)
        
        if not game_end or not game_start:
            continue
            
        winner_name = game_end.get("winner_name")
        players = game_start.get("players", [])
        mode = game_start.get("mode", "unknown")
        
        # We assume Player 0 is usually the one we are tracking if in vs-AI
        # Or we track the specific AI names from our new modes
        turns = [e for e in events if e["type"] == "turn"]
        num_turns = len(turns)
        
        # Track winner's efficiency
        if winner_name:
            if winner_name not in ai_stats:
                ai_stats[winner_name] = []
            ai_stats[winner_name].append(num_turns)

        # Track hit density (spatial)
        for turn in turns:
            if turn.get("outcome") in ("hit", "sunk"):
                r, c = turn.get("target")
                hit_locations[r, c] += 1

    # 1. AI Performance Comparison (Win Counts & Avg Turns)
    plt.figure(figsize=(10, 6))
    names = list(ai_stats.keys())
    counts = [len(ai_stats[n]) for n in names]
    
    sns.barplot(x=names, y=counts, palette="viridis")
    plt.title("Total Wins by AI Type")
    plt.ylabel("Number of Wins")
    plt.savefig(os.path.join(output_dir, "wins_comparison.png"))
    plt.close()

    # 2. Turn Distribution (Efficiency)
    plt.figure(figsize=(10, 6))
    for name, turns_list in ai_stats.items():
        if len(turns_list) > 1:
            sns.kdeplot(turns_list, label=name, fill=True)
    plt.title("Efficiency Distribution (Turns to Win)")
    plt.xlabel("Number of Turns")
    plt.legend()
    plt.savefig(os.path.join(output_dir, "efficiency_distribution.png"))
    plt.close()

    # 3. Hit Density Heatmap
    plt.figure(figsize=(8, 7))
    sns.heatmap(hit_locations, annot=True, fmt=".0f", cmap="YlOrRd", 
                xticklabels=[chr(ord('A')+i) for i in range(10)],
                yticklabels=range(1, 11))
    plt.title("Global Hit Density (Where AIs find ships)")
    plt.savefig(os.path.join(output_dir, "hit_density_heatmap.png"))
    plt.close()

    print(f"Visualizations saved to {output_dir}/")

if __name__ == "__main__":
    all_logs = load_all_logs()
    generate_summary_visuals(all_logs)
