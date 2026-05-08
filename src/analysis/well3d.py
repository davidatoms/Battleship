"""3D rotating "energy well" animations for probability fields.

Each Battleship probability density is converted to a continuous
Gaussian field (the same machinery as :mod:`src.analysis.energy_field`)
and then rendered as a 3-D surface where the surface height is the
*negative* of the field, so peaks of probability become wells.

The camera orbits a chosen pivot cell -- by default the deepest point
of the surface, which is the discrete cell with the highest posterior
probability of hiding a ship.  That pivot is the "specific point in
time" the user can interrogate: the rotating surface visualises every
other hidden cell's relative posterior energy with respect to it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple, Union

import numpy as np

from .energy_field import probability_to_energy_field


PivotMode = str  # "max_prob" | "shot_cell" | "explicit"


def find_pivot(
    prob_map: np.ndarray,
    *,
    mode: PivotMode = "max_prob",
    explicit: Optional[Tuple[int, int]] = None,
    shot_cell: Optional[Tuple[int, int]] = None,
) -> Tuple[int, int]:
    """Pick the (row, col) cell to orbit the camera around.

    ``mode`` is one of:

    * ``"max_prob"`` -- the cell with the highest probability (= the
      deepest well in the inverted surface).
    * ``"shot_cell"`` -- the cell the player fired at (must be passed
      via ``shot_cell``).  This makes the rotation literally spin
      around the move that turn was about.
    * ``"explicit"`` -- the cell passed via ``explicit``.
    """
    if mode == "explicit":
        if explicit is None:
            raise ValueError("explicit pivot mode requires `explicit=(r, c)`")
        return (int(explicit[0]), int(explicit[1]))
    if mode == "shot_cell":
        if shot_cell is None:
            raise ValueError("shot_cell pivot mode requires `shot_cell=(r, c)`")
        return (int(shot_cell[0]), int(shot_cell[1]))
    flat = int(np.argmax(prob_map))
    h, w = prob_map.shape
    return (flat // w, flat % w)


def render_well_animation(
    prob_map: np.ndarray,
    output_path: Union[str, Path],
    *,
    resolution: int = 100,
    n_frames: int = 24,
    elevation_deg: float = 32.0,
    fps: int = 12,
    title: str = "",
    pivot_mode: PivotMode = "max_prob",
    explicit_pivot: Optional[Tuple[int, int]] = None,
    shot_cell: Optional[Tuple[int, int]] = None,
    cmap: str = "magma",
) -> Path:
    """Render a 360-degree orbital GIF around the deepest well.

    The continuous Gaussian field is plotted as ``-value`` so peaks of
    probability become wells; the camera azimuth sweeps from 0 to 360
    degrees while the elevation is held fixed.

    Returns the path the animation was written to.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.animation import FuncAnimation, PillowWriter
    from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

    if prob_map.ndim != 2:
        raise ValueError("prob_map must be 2D")
    h, w = prob_map.shape
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    Z = probability_to_energy_field(prob_map, resolution=resolution)
    z_max = float(Z.max())
    if z_max <= 0:
        # No information: write a flat plane so the file is still produced.
        Z_norm = np.zeros_like(Z)
    else:
        Z_norm = Z / z_max
    surface = -Z_norm

    xs = np.linspace(0, w - 1, resolution)
    ys = np.linspace(0, h - 1, resolution)
    X, Y = np.meshgrid(xs, ys)

    pivot = find_pivot(
        prob_map,
        mode=pivot_mode,
        explicit=explicit_pivot,
        shot_cell=shot_cell,
    )
    pivot_r, pivot_c = pivot
    pivot_x, pivot_y = float(pivot_c), float(pivot_r)

    fig = plt.figure(figsize=(7, 6))
    ax = fig.add_subplot(111, projection="3d")

    ax.plot_surface(
        X,
        Y,
        surface,
        cmap=cmap,
        linewidth=0,
        antialiased=True,
        alpha=0.95,
        rcount=resolution,
        ccount=resolution,
    )

    ax.set_xlim(0, w - 1)
    ax.set_ylim(h - 1, 0)
    ax.set_zlim(-1.08, 0.08)
    ax.set_xticks(range(w))
    ax.set_xticklabels([chr(ord("A") + i) for i in range(w)], fontsize=7)
    ax.set_yticks(range(h))
    ax.set_yticklabels([str(i + 1) for i in range(h)], fontsize=7)
    ax.set_zlabel("-P(ship)", fontsize=8)
    full_title = title or "Probability well"
    pivot_label = f"{chr(ord('A') + pivot_c)}{pivot_r + 1}"
    ax.set_title(f"{full_title}\npivot = {pivot_label} ({pivot_mode})", fontsize=11)

    # Vertical "well-axis" marker so the pivot is visible at every camera angle.
    ax.plot(
        [pivot_x, pivot_x],
        [pivot_y, pivot_y],
        [-1.05, 0.05],
        color="#fde047",
        linewidth=1.8,
    )
    ax.scatter(
        [pivot_x], [pivot_y], [-1.0],
        color="#fde047",
        s=80,
        edgecolor="#1f2937",
    )

    def update(frame: int):
        azim = (frame / n_frames) * 360.0
        ax.view_init(elev=elevation_deg, azim=azim)
        return ()

    anim = FuncAnimation(fig, update, frames=n_frames, blit=False)
    writer = PillowWriter(fps=fps)
    anim.save(str(out), writer=writer)
    plt.close(fig)
    return out
