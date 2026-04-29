"""Render a discrete probability grid as a continuous Gaussian energy
field, using the technique introduced in the ``phi-based-fractals``
project (``src/arc_energy_field.py``).

Each non-zero cell of the grid contributes a Gaussian "knot" centered
at the cell's continuous coordinates; the bandwidth ``beta`` is tied
to the inverse grid resolution so that the visual structure is
preserved across different board sizes.
"""

from __future__ import annotations

import math
from typing import Optional

import numpy as np


PHI = 1.618033988749895
INV_PHI = 1.0 / PHI


def probability_to_energy_field(
    prob_map: np.ndarray,
    *,
    resolution: int = 240,
    beta_factor: float = INV_PHI,
    weight_power: float = 1.0,
) -> np.ndarray:
    """Convert a discrete ``(H, W)`` probability grid into a continuous
    ``(resolution, resolution)`` energy field.

    Parameters
    ----------
    prob_map :
        2-D non-negative array of probabilities (or any density).
    resolution :
        Side length of the output continuous grid.
    beta_factor :
        Multiplier on the natural bandwidth ``1 / max(H, W)``.  The
        default ``1/Phi`` gives the same harmonic decay used by the
        phi-based-fractals ARC fields.
    weight_power :
        Optional non-linear shaping of the input probabilities (use
        ``0.5`` for a square-root softening, ``2.0`` for sharpening).

    Returns
    -------
    ndarray of shape ``(resolution, resolution)``.  Pixel ``[0, 0]`` is
    the bottom-left corner so it can be passed to
    ``ax.imshow(..., origin="lower")``.
    """
    if prob_map.ndim != 2:
        raise ValueError("prob_map must be 2-dimensional")
    h, w = prob_map.shape
    bandwidth = beta_factor / max(h, w)
    x = np.linspace(0, 1, resolution)
    y = np.linspace(0, 1, resolution)
    X, Y = np.meshgrid(x, y)
    Z = np.zeros_like(X)
    two_beta_sq = 2.0 * bandwidth * bandwidth
    for r in range(h):
        for c in range(w):
            p = float(prob_map[r, c])
            if p <= 0:
                continue
            cy = 1.0 - (r + 0.5) / h
            cx = (c + 0.5) / w
            dist_sq = (X - cx) ** 2 + (Y - cy) ** 2
            Z += (p ** weight_power) * np.exp(-dist_sq / two_beta_sq)
    return Z


def normalize(Z: np.ndarray) -> np.ndarray:
    """Linearly rescale ``Z`` to ``[0, 1]`` for plotting."""
    lo, hi = float(Z.min()), float(Z.max())
    if math.isclose(lo, hi):
        return np.zeros_like(Z)
    return (Z - lo) / (hi - lo)
