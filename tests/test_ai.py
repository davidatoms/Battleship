import pytest
import random
from strategies import HeuristicAI, RLAgent
from src.game.engine import Engine
from battleship_cli import ai_placement

def test_heuristic_ai_completion():
    """Verify that the Heuristic AI can complete a game against a random opponent."""
    ai = HeuristicAI(seed=42)
    board1 = ai_placement(player=0, player_name="Random")
    board2 = ai_placement(player=1, player_name="Heuristic")
    
    engine = Engine(boards=[board1, board2])
    
    turns = 0
    while not engine.is_over() and turns < 200:
        if engine.current == 0:
            # Simple random opponent
            target_board = engine.boards[1]
            choices = [(r, c) for r in range(10) for c in range(10) 
                       if target_board.cell(r, c) not in ("X", "o")]
            r, c = random.choice(choices)
            engine.take_turn(r, c)
        else:
            ai.take_turn(engine)
        turns += 1
    
    assert engine.is_over()
    assert engine.winner() is not None

def test_rl_ai_completion():
    """Verify that the RL AI can complete a game (even with a blank Q-table)."""
    ai = RLAgent(epsilon=0)
    board1 = ai_placement(player=0, player_name="Random")
    board2 = ai_placement(player=1, player_name="RL")
    
    engine = Engine(boards=[board1, board2])
    
    turns = 0
    while not engine.is_over() and turns < 200:
        if engine.current == 0:
            target_board = engine.boards[1]
            choices = [(r, c) for r in range(10) for c in range(10) 
                       if target_board.cell(r, c) not in ("X", "o")]
            r, c = random.choice(choices)
            engine.take_turn(r, c)
        else:
            ai.take_turn(engine)
        turns += 1
    
    assert engine.is_over()
