"""Posterior probability density for an opponent's Battleship grid.

The model is the classical "count consistent placements" estimator.
Given the shooter's view of the opponent board (some cells are known
misses, some are open hits, some are cells of fully-sunken ships, the
rest are unknown), and given the lengths of the opponent's ships that
are still afloat, we enumerate every legal placement (cardinal
orientations only) of every alive ship and tally how many of them put
a cell on each unknown square.

Two regimes:

* "hunt mode" -- no open hits in the view.  Every consistent placement
  contributes equally; the resulting heatmap is the classic
  centre-heavy, edge-light Battleship density.
* "target mode" -- at least one open hit.  Only placements that cover
  at least one open hit are counted, which concentrates probability
  around the known hit(s) -- the same intuition that makes Battleship
  AIs switch from hunting to targeting after a hit.
"""

from __future__ import annotations

from typing import Iterable, List, Sequence, Tuple

import numpy as np


UNKNOWN = "?"
MISS = "M"
OPEN_HIT = "H"
SUNK = "S"

VALID_MARKERS = {UNKNOWN, MISS, OPEN_HIT, SUNK}

# Two cardinals are enough -- (0, -1) and (-1, 0) generate the same
# placements as (0, 1) and (1, 0), just with the anchor at the other
# end of the ship.
_DELTAS = ((0, 1), (1, 0))


def _enumerate_placements(
    size: int, length: int
) -> Iterable[List[Tuple[int, int]]]:
    if length <= 0 or length > size:
        return
    for dr, dc in _DELTAS:
        if dr == 0:
            row_range = range(size)
            col_range = range(size - length + 1)
        else:
            row_range = range(size - length + 1)
            col_range = range(size)
        for r in row_range:
            for c in col_range:
                yield [(r + i * dr, c + i * dc) for i in range(length)]


def compute_probability_map(
    view: np.ndarray,
    alive_ship_lengths: Sequence[int],
) -> np.ndarray:
    """Return a probability density over unknown cells.

    Parameters
    ----------
    view :
        ``(size, size)`` array of single characters in
        :data:`VALID_MARKERS`.
    alive_ship_lengths :
        Lengths of opponent ships that are still afloat (i.e. excluding
        any ship the shooter has fully sunk).

    Returns
    -------
    ndarray of shape ``view.shape``, non-negative, summing to ``1`` over
    all unknown cells (or all zero if no consistent placement exists).
    """
    if view.ndim != 2 or view.shape[0] != view.shape[1]:
        raise ValueError("view must be a square 2D array")
    size = view.shape[0]
    counts = np.zeros((size, size), dtype=np.float64)

    has_open_hits = bool(np.any(view == OPEN_HIT))

    for length in alive_ship_lengths:
        for cells in _enumerate_placements(size, length):
            consistent = True
            covers_open_hit = False
            for r, c in cells:
                marker = view[r, c]
                if marker == MISS or marker == SUNK:
                    consistent = False
                    break
                if marker == OPEN_HIT:
                    covers_open_hit = True
            if not consistent:
                continue
            if has_open_hits and not covers_open_hit:
                continue
            for r, c in cells:
                if view[r, c] == UNKNOWN:
                    counts[r, c] += 1.0

    total = counts.sum()
    if total > 0:
        counts /= total
    return counts


def counterfactual_outcomes(
    view: np.ndarray,
    alive_ship_lengths: Sequence[int],
    target: Tuple[int, int],
) -> Tuple[np.ndarray, np.ndarray]:
    """Posterior probability maps for the *next* shot, conditioned on
    the just-fired shot at ``target`` being a hit vs a miss.

    Notes
    -----
    The "if hit" branch treats the cell as an open hit even if it
    would in fact sink a ship, because the shooter cannot tell which
    ship would be sunk before firing.  This keeps the visualisation
    a pure function of the observable board state.
    """
    r, c = target
    if view[r, c] != UNKNOWN:
        raise ValueError("target cell is not unknown")
    view_hit = view.copy()
    view_hit[r, c] = OPEN_HIT
    view_miss = view.copy()
    view_miss[r, c] = MISS
    p_hit = compute_probability_map(view_hit, alive_ship_lengths)
    p_miss = compute_probability_map(view_miss, alive_ship_lengths)
    return p_hit, p_miss
