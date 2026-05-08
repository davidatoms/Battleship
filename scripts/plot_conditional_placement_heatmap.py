"""Draw a heatmap of cell occupancy over all fleets extending one fixed ship.

Example (Carrier horizontal on row 1, columns A–E; fast approximate default)::

    python scripts/plot_conditional_placement_heatmap.py --row 0 --col 0 --horizontal --out carrier_a1e.png

Exact full enumeration (can take a long time on 10x10 classic)::

    python scripts/plot_conditional_placement_heatmap.py --row 0 --col 0 --horizontal --exact --out exact.png
Uses cardinal-only placements (same convention as ``src.analysis.probability``).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running as ``python scripts/...`` from repo root.
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.analysis.placement_density import (
    approximate_placement_density_given_first_ship,
    cardinal_segment_masks,
    placement_density_given_first_ship,
)
from src.analysis.plotting import plot_placement_density_heatmap
from src.rules import HouseRules


def _mask_from_corner(
    n: int,
    *,
    row: int,
    col: int,
    length: int,
    horizontal: bool,
) -> int:
    masks = cardinal_segment_masks(n, length)
    want = set()
    if horizontal:
        for i in range(length):
            want.add((row, col + i))
    else:
        for i in range(length):
            want.add((row + i, col))
    found = []
    for m in masks:
        cells = []
        b = m
        while b:
            lsb = b & -b
            idx = lsb.bit_length() - 1
            cells.append(divmod(idx, n))
            b ^= lsb
        if set(cells) == want:
            found.append(m)
    if len(found) != 1:
        raise SystemExit(f"No unique segment for corner ({row},{col}) len={length} horiz={horizontal}")
    return found[0]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--size", type=int, default=10, help="Board side length")
    parser.add_argument(
        "--ship",
        type=str,
        default="Carrier",
        help="Fleet ship name to fix (must exist in fleet)",
    )
    parser.add_argument("--row", type=int, required=True, help="0-based top row")
    parser.add_argument("--col", type=int, required=True, help="0-based left column")
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--horizontal", action="store_true")
    g.add_argument("--vertical", action="store_true")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("placement_conditional_heatmap.png"),
        help="Output PNG path",
    )
    parser.add_argument(
        "--exact",
        action="store_true",
        help="Enumerate all completions exactly (slow for full classic fleet on 10x10)",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=25_000,
        help="Monte Carlo trials when not using --exact",
    )
    parser.add_argument("--seed", type=int, default=None, help="RNG seed for --samples")
    args = parser.parse_args()

    rules = HouseRules(board_size=args.size)
    names = [s.name for s in rules.fleet]
    if args.ship not in names:
        raise SystemExit(f"Unknown ship {args.ship!r}; fleet has {names}")
    first_idx = names.index(args.ship)
    spec = rules.fleet[first_idx]
    horiz = args.horizontal
    m = _mask_from_corner(
        args.size,
        row=args.row,
        col=args.col,
        length=spec.length,
        horizontal=horiz,
    )

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    rng = np.random.default_rng(args.seed)
    if args.exact:
        density, total = placement_density_given_first_ship(rules, first_idx, m)
        stat = f"{total:,} completions (exact)"
    else:
        density = approximate_placement_density_given_first_ship(
            rules,
            first_idx,
            m,
            n_samples=args.samples,
            rng=rng,
        )
        stat = f"{args.samples:,} Monte Carlo trials (approximate)"

    orient = "horizontal" if horiz else "vertical"
    title = (
        f"{args.ship} fixed {orient} at row {args.row + 1} "
        f"col {chr(ord('A') + args.col)} -- {stat}"
    )
    fig = plot_placement_density_heatmap(density, title=title)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {args.out} ({stat})")


if __name__ == "__main__":
    main()
