import os
import random
import sys
import time
from typing import List, Type

# Add the project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.game.engine import Engine
from battleship_cli import ai_placement
from strategies import EnsembleAI, HeuristicAI, HybridAI, RLAgent, RandomShooting

def run_benchmark(ai_class: Type, name: str, episodes=50):
    print(f"Benchmarking {name}...")
    total_turns = 0
    wins = 0
    start_time = time.time()

    for _ in range(episodes):
        ai = ai_class()
        board_ai = ai_placement(player=0, player_name=name)
        board_opp = ai_placement(player=1, player_name="Random")
        
        engine = Engine(boards=[board_ai, board_opp])
        
        turns = 0
        while not engine.is_over() and turns < 200:
            if engine.current == 0:
                ai.take_turn(engine)
            else:
                # Random opponent
                choices = [(r, c) for r in range(10) for c in range(10) 
                           if engine.boards[0].cell(r, c) not in ("X", "o")]
                r, c = random.choice(choices)
                engine.take_turn(r, c)
            turns += 1
        
        if engine.winner() == 0:
            wins += 1
        total_turns += turns

    avg_turns = total_turns / episodes
    win_rate = (wins / episodes) * 100
    duration = time.time() - start_time
    print(f"  Win Rate: {win_rate}% | Avg Turns: {avg_turns:.2f} | Time: {duration:.2f}s")

if __name__ == "__main__":
    agents = [
        (RandomShooting, "Random AI"),
        (HeuristicAI, "Heuristic AI"),
        (RLAgent, "RL AI"),
        (HybridAI, "Hybrid AI"),
        (EnsembleAI, "Ensemble AI"),
    ]
    
    for ai_class, name in agents:
        run_benchmark(ai_class, name, episodes=100)
