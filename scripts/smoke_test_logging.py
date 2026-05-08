import os
import sys
import unittest
from unittest.mock import patch
from pathlib import Path
import glob

# Add project root
sys.path.insert(0, os.getcwd())

import battleship_cli

def smoke_test():
    print("Running logging smoke test...")
    
    # Mock inputs: 
    # 1. Choose mode '2' (Random AI)
    # 2. Type 'auto' for human placement
    # 3. provide coordinates until game ends (we'll just mock a lot of coordinates)
    
    # Create a generator for inputs to simulate a full game
    def input_generator():
        yield "2"      # Choose Random AI
        yield "auto"   # Auto-place
        yield ""       # Press Enter to start
        
        # Fire at every cell sequentially to ensure the game ends
        for r in range(10):
            for c in range(10):
                yield f"{chr(ord('A')+c)}{r+1}"

    gen = input_generator()
    
    def mocked_input(prompt_text=""):
        try:
            val = next(gen)
            # print(f"Mocked input: {val}")
            return val
        except StopIteration:
            return "quit"

    # Clear game_logs before test to be sure
    log_dir = Path("game_logs")
    old_logs = set(log_dir.glob("*.json"))

    with patch('builtins.input', side_effect=mocked_input), \
         patch('battleship_cli.clear_screen'): # Keep output clean
        try:
            battleship_cli.main([])
        except SystemExit:
            pass

    new_logs = set(log_dir.glob("*.json")) - old_logs
    
    if new_logs:
        print(f"SUCCESS: Generated {len(new_logs)} new log(s):")
        for log in new_logs:
            print(f"  - {log}")
    else:
        print("FAILURE: No new logs found in game_logs/")
        sys.exit(1)

if __name__ == "__main__":
    smoke_test()
