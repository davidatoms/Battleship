from __future__ import annotations

import random
from typing import Dict, List, Optional, Tuple

import numpy as np

from src.game.engine import Engine, TurnResult

FIRE_RANDOM = 0
FIRE_UP = 1
FIRE_DOWN = 2
FIRE_LEFT = 3
FIRE_RIGHT = 4


class RLAgent:
    """
    Q-Learning Agent for Battleship.
    Learns to hunt and then target adjacent cells.
    """

    def __init__(self, size: int = 10, epsilon: float = 0.1, alpha: float = 0.5, gamma: float = 0.9):
        self.size = size
        self.epsilon = epsilon
        self.alpha = alpha
        self.gamma = gamma
        self.q_table: Dict[Tuple, np.ndarray] = {}
        self.last_state: Optional[Tuple] = None
        self.last_action: Optional[int] = None
        self.last_hit_pos: Optional[Tuple[int, int]] = None
        self.tried_cells: set[Tuple[int, int]] = set()

    def _get_state(self, engine: Engine) -> Tuple:
        if self.last_hit_pos is None:
            return (False, 0, 0, 0, 0)

        r, c = self.last_hit_pos
        target_board = engine.boards[1 - engine.current]

        def get_status(nr, nc):
            if not (0 <= nr < self.size and 0 <= nc < self.size):
                return 3
            cell = target_board.cell(nr, nc)
            if cell == ".":
                return 0
            if cell == "o":
                return 1
            if cell == "X":
                return 2
            return 0

        up = get_status(r - 1, c)
        down = get_status(r + 1, c)
        left = get_status(r, c - 1)
        right = get_status(r, c + 1)

        return (True, up, down, left, right)

    def _get_q_values(self, state: Tuple) -> np.ndarray:
        if state not in self.q_table:
            self.q_table[state] = np.zeros(5)
        return self.q_table[state]

    def choose_action(self, state: Tuple) -> int:
        if random.random() < self.epsilon:
            return random.randint(0, 4)
        return int(np.argmax(self._get_q_values(state)))

    def take_turn(self, engine: Engine) -> TurnResult:
        state = self._get_state(engine)
        action = self.choose_action(state)

        r, c = self._action_to_coord(action, engine)

        if (r, c) in self.tried_cells or not (0 <= r < self.size and 0 <= c < self.size):
            action = FIRE_RANDOM
            r, c = self._action_to_coord(action, engine)

        result = engine.take_turn(r, c)
        self.tried_cells.add((r, c))

        reward = -1
        if result.outcome == "hit":
            reward = 10
        elif result.outcome == "sunk":
            reward = 50
        elif result.outcome == "miss":
            reward = -2
        elif result.outcome in ("already", "invalid"):
            reward = -10

        next_state = self._get_state(engine)
        self.update_q(state, action, reward, next_state)

        self._update_internal(result)
        return result

    def _action_to_coord(self, action: int, engine: Engine) -> Tuple[int, int]:
        if action == FIRE_RANDOM or self.last_hit_pos is None:
            target_board = engine.boards[1 - engine.current]
            choices = [
                (r, c)
                for r in range(self.size)
                for c in range(self.size)
                if (r, c) not in self.tried_cells and target_board.cell(r, c) not in ("X", "o")
            ]
            if not choices:
                return (0, 0)
            return random.choice(choices)

        r, c = self.last_hit_pos
        if action == FIRE_UP:
            return r - 1, c
        if action == FIRE_DOWN:
            return r + 1, c
        if action == FIRE_LEFT:
            return r, c - 1
        if action == FIRE_RIGHT:
            return r, c + 1
        return r, c

    def update_q(self, state: Tuple, action: int, reward: float, next_state: Tuple):
        old_q = self._get_q_values(state)[action]
        next_max = np.max(self._get_q_values(next_state))
        new_q = old_q + self.alpha * (reward + self.gamma * next_max - old_q)
        self.q_table[state][action] = new_q

    def _update_internal(self, result: TurnResult):
        if result.outcome == "sunk":
            self.last_hit_pos = None
        elif result.outcome == "hit":
            self.last_hit_pos = result.target

    def save_q_table(self, filename: str):
        np.save(filename, self.q_table)

    def load_q_table(self, filename: str):
        self.q_table = np.load(filename, allow_pickle=True).item()
