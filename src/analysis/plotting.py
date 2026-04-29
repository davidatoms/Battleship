"""Matplotlib helpers for visualising Battleship probability fields.

These helpers are kept separate from the math so the math is testable
without a matplotlib dependency.  Importing this module requires
matplotlib.
"""

from __future__ import annotations

from typing import Iterable, Optional, Sequence, Tuple

import numpy as np

from .energy_field import normalize, probability_to_energy_field
from .probability import MISS, OPEN_HIT, SUNK, UNKNOWN


_MARKER_FACECOLOR = {
    UNKNOWN: "#0f172a",
    MISS: "#cbd5e1",
    OPEN_HIT: "#ef4444",
    SUNK: "#7f1d1d",
}
_MARKER_TEXT = {
    UNKNOWN: "",
    MISS: "o",
    OPEN_HIT: "X",
    SUNK: "#",
}


def plot_view(ax, view: np.ndarray, *, title: str = "Shooter's view") -> None:
    """Draw the shooter's discrete view as a colored grid."""
    import matplotlib.patches as patches

    size = view.shape[0]
    ax.set_xlim(-0.5, size - 0.5)
    ax.set_ylim(size - 0.5, -0.5)
    ax.set_aspect("equal")
    ax.set_title(title)
    for r in range(size):
        for c in range(size):
            ch = str(view[r, c])
            face = _MARKER_FACECOLOR.get(ch, "#1e293b")
            ax.add_patch(
                patches.Rectangle(
                    (c - 0.5, r - 0.5), 1, 1,
                    facecolor=face, edgecolor="#334155", linewidth=0.5,
                )
            )
            text = _MARKER_TEXT.get(ch, "")
            if text:
                ax.text(c, r, text, ha="center", va="center",
                        color="#0f172a" if ch == MISS else "white",
                        fontsize=10, fontweight="bold")
    ax.set_xticks(range(size))
    ax.set_xticklabels([chr(ord("A") + i) for i in range(size)], fontsize=8)
    ax.set_yticks(range(size))
    ax.set_yticklabels([str(i + 1) for i in range(size)], fontsize=8)
    for spine in ax.spines.values():
        spine.set_visible(False)


def plot_probability_field(
    ax,
    prob_map: np.ndarray,
    *,
    title: str = "Posterior",
    resolution: int = 240,
    cmap: str = "viridis",
    overlay_target: Optional[Tuple[int, int]] = None,
    annotate_max: bool = True,
) -> None:
    """Render a Gaussian energy field for ``prob_map`` on ``ax``."""
    h, w = prob_map.shape
    Z = probability_to_energy_field(prob_map, resolution=resolution)
    Z = normalize(Z)
    ax.imshow(
        Z,
        origin="lower",
        extent=[-0.5, w - 0.5, h - 0.5, -0.5],
        cmap=cmap,
        interpolation="bilinear",
        vmin=0.0,
        vmax=1.0,
    )
    ax.set_aspect("equal")
    ax.set_title(title)
    ax.set_xticks(range(w))
    ax.set_xticklabels([chr(ord("A") + i) for i in range(w)], fontsize=8)
    ax.set_yticks(range(h))
    ax.set_yticklabels([str(i + 1) for i in range(h)], fontsize=8)
    for spine in ax.spines.values():
        spine.set_visible(False)

    if overlay_target is not None:
        r, c = overlay_target
        ax.scatter([c], [r], s=140, marker="x", color="#fde047", linewidths=2)

    if annotate_max and prob_map.size:
        flat_idx = int(np.argmax(prob_map))
        if prob_map.flat[flat_idx] > 0:
            r, c = divmod(flat_idx, w)
            ax.scatter([c], [r], s=80, facecolor="none",
                       edgecolor="#fde047", linewidths=2)


def plot_turn_summary(
    view: np.ndarray,
    prior: np.ndarray,
    posterior_hit: np.ndarray,
    posterior_miss: np.ndarray,
    *,
    target: Tuple[int, int],
    actual_outcome: Optional[str] = None,
    shooter_name: str = "Shooter",
    turn_index: Optional[int] = None,
    resolution: int = 240,
):
    """Build a 1x4 figure: discrete view + prior + counterfactual hit/miss.

    Returns the matplotlib Figure.
    """
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 4, figsize=(20, 5))
    suptitle = f"{shooter_name}"
    if turn_index is not None:
        suptitle += f" -- turn {turn_index}"
    if actual_outcome:
        suptitle += f" -- shot at {target} ({actual_outcome})"
    fig.suptitle(suptitle, fontsize=14)

    plot_view(axes[0], view, title="Shooter's view")
    plot_probability_field(
        axes[1], prior, title="Prior posterior",
        resolution=resolution, overlay_target=target,
    )
    plot_probability_field(
        axes[2], posterior_hit, title="If shot was a HIT",
        resolution=resolution, overlay_target=target, cmap="magma",
    )
    plot_probability_field(
        axes[3], posterior_miss, title="If shot was a MISS",
        resolution=resolution, overlay_target=target, cmap="cividis",
    )

    fig.tight_layout(rect=(0, 0, 1, 0.95))
    return fig


def plot_aggregate_hit_vs_miss(
    mean_post_hit: np.ndarray,
    mean_post_miss: np.ndarray,
    *,
    resolution: int = 320,
    title: str = "Mean posterior right after a hit vs after a miss",
):
    """Side-by-side aggregate hit/miss heatmaps over an entire game."""
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(12, 6))
    fig.suptitle(title, fontsize=14)
    plot_probability_field(
        axes[0], mean_post_hit,
        title="After hits (avg)", resolution=resolution, cmap="magma",
        annotate_max=False,
    )
    plot_probability_field(
        axes[1], mean_post_miss,
        title="After misses (avg)", resolution=resolution, cmap="cividis",
        annotate_max=False,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    return fig
