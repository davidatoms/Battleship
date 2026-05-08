import os
import random
import sys

# Add the project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from strategies.rl import RLAgent
from src.board import Board
from src.game.engine import Engine
from battleship_cli import ai_placement

def train(episodes=1000):
    agent = RLAgent(epsilon=0.2) # Higher epsilon during training
    
    print(f"Starting training for {episodes} episodes...")
    
    for i in range(episodes):
        # Set up a new game
        board_agent = ai_placement(player=0, player_name="Agent")
        board_opponent = ai_placement(player=1, player_name="Opponent")
        
        engine = Engine(boards=[board_agent, board_opponent])
        agent.tried_cells = set()
        agent.last_hit_pos = None
        
        turns = 0
        while not engine.is_over():
            if engine.current == 0:
                agent.take_turn(engine)
            else:
                # Random opponent
                target_board = engine.boards[0]
                choices = [(r, c) for r in range(10) for c in range(10) 
                           if target_board.cell(r, c) not in ("X", "o")]
                r, c = random.choice(choices)
                engine.take_turn(r, c)
            turns += 1
        
        if (i + 1) % 100 == 0:
            print(f"Episode {i+1}/{episodes} completed.")

    agent.save_q_table("ml/q_table.npy")
    print("Training complete. Q-table saved to ml/q_table.npy")

if __name__ == "__main__":
    train(2000)
