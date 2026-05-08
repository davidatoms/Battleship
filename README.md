# Battleship (Python)

A modular, extensible implementation of the classic *Battleship* board-game written in Python.

---

## Features so far

* 10 × 10 board with pretty printing (row/column headers).
* `Ship` dataclass supplies standard fleet (Carrier, Battleship, Cruiser, Submarine, Destroyer).
* `Setup` helper for interactive or automatic fleet placement.
* **Advanced AI Opponents**:
  * **Random AI**: Shoots randomly at unknown cells.
  * **Heuristic AI**: Implements a "Hunt, Target, and Destroy" strategy, locking onto ships and following their orientation once found.
  * **RL Model**: A Reinforcement Learning (Q-learning) agent that has learned the optimal targeting strategy through thousands of self-play games.
* `GameLog`: Automatically records every placement and shot to a JSON file for replay or analysis.
* `Probability Map`: Statistical analysis of likely ship locations based on the current board state.

## Quick start

```bash
python battleship_cli.py
```
Follow the prompts to choose your game mode (Hot-seat or vs. AI).

## Repository structure

```
Battleship/
├── ml/
│   ├── heuristic_ai.py   # State-machine AI
│   ├── rl_ai.py          # Q-learning agent
│   ├── train.py          # Training loop for RL agent
│   └── q_table.npy       # Pre-trained RL weights
├── src/
│   ├── board.py          # Board model & rendering helpers
│   ├── setup.py          # Interactive fleet-placement helper
│   ├── game/
│   │   ├── engine.py     # Turn logic & hit/miss handling
│   │   └── log.py        # Game event logging
│   └── analysis/
│       └── probability.py # Heatmap generation
├── battleship_cli.py     # Command-line front-end
└── tests/                # Unit tests
```

## Roadmap

1. Add a curses-based TUI for full interactive play.
2. Network play via sockets or WebSocket for online multiplayer.
3. Deep Reinforcement Learning (DQN) implementation.

---

Contributions welcome! Feel free to open issues or submit pull requests.
