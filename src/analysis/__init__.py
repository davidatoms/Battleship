"""Analytical tools for Battleship games.

This subpackage contains framework-agnostic helpers for reasoning about
partially-observed Battleship states:

* :mod:`src.analysis.probability` -- posterior probability density that
  each unshot cell hides a ship, given the shots seen so far.
* :mod:`src.analysis.replay` -- walk a JSON game log and reconstruct
  what each player knows about the opponent's board at any point.
* :mod:`src.analysis.energy_field` -- render a probability grid as a
  continuous Gaussian "energy field" (Phi-fractal style).
* :mod:`src.analysis.plotting` -- matplotlib helpers for the side-by-side
  prior / hit / miss visualisations.
"""

from .probability import (
    UNKNOWN,
    MISS,
    OPEN_HIT,
    SUNK,
    compute_probability_map,
    counterfactual_outcomes,
)
from .replay import replay_state, build_view_from_board

__all__ = [
    "UNKNOWN",
    "MISS",
    "OPEN_HIT",
    "SUNK",
    "compute_probability_map",
    "counterfactual_outcomes",
    "replay_state",
    "build_view_from_board",
    "visualise_log",
]


def __getattr__(name):  # noqa: D401 -- module-level lazy import
    if name == "visualise_log":
        from .visualize import visualise_log
        return visualise_log
    raise AttributeError(name)
