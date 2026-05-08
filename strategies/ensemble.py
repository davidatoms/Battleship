from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

import numpy as np

from src.analysis.probability import UNKNOWN, OPEN_HIT, MISS, compute_probability_map
from src.game.engine import Engine, TurnResult

from .heuristic import HeuristicAI
from .rl import RLAgent

_REPO_ROOT = Path(__file__).resolve().parents[1]


class EnsembleAI:
    """
    Ensemble AI combining probability, RL, and heuristic experts with weighted voting.
    """

    def __init__(self, size: int = 10, seed: Optional[int] = None):
        self.size = size
        self.heuristic_expert = HeuristicAI(size=size, seed=seed)
        self.rl_expert = RLAgent(size=size, epsilon=0)
        self.tried_cells: set[Tuple[int, int]] = set()

        q_table_path = _REPO_ROOT / "ml" / "q_table.npy"
        if q_table_path.exists():
            self.rl_expert.load_q_table(str(q_table_path))

    def take_turn(self, engine: Engine) -> TurnResult:
        r, c = self._choose_move(engine)
        result = engine.take_turn(r, c)
        self.tried_cells.add((r, c))

        self.heuristic_expert.tried_cells.add((r, c))
        self.heuristic_expert._update_state(result)

        self.rl_expert.tried_cells.add((r, c))
        self.rl_expert._update_internal(result)

        return result

    def _choose_move(self, engine: Engine) -> Tuple[int, int]:
        target_board = engine.boards[1 - engine.current]

        view = np.full((self.size, self.size), UNKNOWN, dtype=object)
        for r in range(self.size):
            for c in range(self.size):
                cell = target_board.cell(r, c)
                if cell == "o":
                    view[r, c] = MISS
                elif cell == "X":
                    view[r, c] = OPEN_HIT

        alive_lengths = [s.length for s in target_board.ships if not s.is_sunk()]
        prob_scores = compute_probability_map(view, alive_lengths)
        if prob_scores.max() > 0:
            prob_scores /= prob_scores.max()

        rl_scores = np.zeros((self.size, self.size))
        rl_state = self.rl_expert._get_state(engine)
        q_values = self.rl_expert._get_q_values(rl_state)

        best_rl_action = np.argmax(q_values)
        rl_r, rl_c = self.rl_expert._action_to_coord(int(best_rl_action), engine)
        if 0 <= rl_r < self.size and 0 <= rl_c < self.size:
            rl_scores[rl_r, rl_c] = 1.0

        heuristic_scores = np.zeros((self.size, self.size))
        h_r, h_c = self.heuristic_expert._choose_move(engine)
        heuristic_scores[h_r, h_c] = 1.0

        if self.heuristic_expert.state == "hunt":
            w_prob, w_rl, w_heur = 0.7, 0.2, 0.1
        else:
            w_prob, w_rl, w_heur = 0.2, 0.3, 0.5

        combined_scores = (w_prob * prob_scores) + (w_rl * rl_scores) + (w_heur * heuristic_scores)

        for r, c in self.tried_cells:
            combined_scores[r, c] = -1.0

        max_idx = np.argmax(combined_scores)
        r, c = divmod(max_idx, self.size)

        return (int(r), int(c))
