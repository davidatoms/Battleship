"""Occupancy heatmaps for fleets that extend one fixed ship (cardinal placements).

Use :func:`placement_density_given_first_ship` for **exact** counts (feasible for
small boards / small fleets). For the full classic 10x10 fleet, prefer
:func:`approximate_placement_density_given_first_ship`.
"""

from __future__ import annotations

from typing import Any, List, Tuple

import numpy as np

from ..rules import HouseRules


def _bit_coords(mask: int, n: int) -> List[Tuple[int, int]]:
    out = []
    b = mask
    while b:
        lsb = b & -b
        idx = (lsb.bit_length() - 1)
        r, c = divmod(idx, n)
        out.append((r, c))
        b ^= lsb
    return out


def is_valid_cardinal_segment(mask: int, n: int, length: int) -> bool:
    """Whether ``mask`` is a single contiguous N/E cardinal segment on an n*n grid."""
    if length <= 0 or mask.bit_count() != length:
        return False
    coords = _bit_coords(mask, n)
    if len(coords) != length:
        return False
    rows = {r for r, _ in coords}
    cols = {c for _, c in coords}
    if len(rows) == 1:
        cs = sorted(cols)
        return cs[-1] - cs[0] == length - 1
    if len(cols) == 1:
        rs = sorted(rows)
        return rs[-1] - rs[0] == length - 1
    return False


def cardinal_segment_masks(n: int, length: int) -> Tuple[int, ...]:
    """Distinct placement bitmasks (horizontal and vertical)."""
    seen: set[int] = set()
    for dr, dc in ((0, 1), (1, 0)):
        if dr == 0:
            for r in range(n):
                for c in range(n - length + 1):
                    m = 0
                    for i in range(length):
                        rr, cc = r, c + i
                        m |= 1 << (rr * n + cc)
                    seen.add(m)
        else:
            for r in range(n - length + 1):
                for c in range(n):
                    m = 0
                    for i in range(length):
                        rr, cc = r + i, c
                        m |= 1 << (rr * n + cc)
                    seen.add(m)
    return tuple(sorted(seen))


def segment_masks_for_rules(rules: HouseRules) -> List[Tuple[int, ...]]:
    n = rules.board_size
    return [cardinal_segment_masks(n, spec.length) for spec in rules.fleet]


def placement_density_given_first_ship(
    rules: HouseRules,
    first_fleet_index: int,
    fixed_segment_mask: int,
) -> Tuple[np.ndarray, int]:
    """Counts, over valid full fleets, how often each cell is occupied.

    The first ship (``rules.fleet[first_fleet_index]``) is fixed to
    ``fixed_segment_mask``. All remaining ships are placed in every
    disjoint cardinal way; ships are distinguishable (Cruiser vs Submarine).

    Parameters
    ----------
    rules :
        Board size and fleet (order matches labeled ships).
    first_fleet_index :
        Which fleet slot is already placed (0 .. len(fleet)-1).
    fixed_segment_mask :
        Bitmask of that ship's cells (row-major: bit ``r * n + c``).

    Returns
    -------
    density :
        ``(n, n)`` integer array; ``density[r, c]`` is how many valid
        completions have a ship (including the fixed one) on ``(r, c)``.
    total_completions :
        Number of valid disjoint placements for the rest of the fleet.
    """
    n = rules.board_size
    fleet = rules.fleet
    if not (0 <= first_fleet_index < len(fleet)):
        raise IndexError("first_fleet_index out of range")
    spec = fleet[first_fleet_index]
    if not is_valid_cardinal_segment(fixed_segment_mask, n, spec.length):
        raise ValueError("fixed_segment_mask is not a valid cardinal segment for that ship")

    all_masks = segment_masks_for_rules(rules)
    fixed = fixed_segment_mask

    remaining_idx = [i for i in range(len(fleet)) if i != first_fleet_index]

    def dfs(k: int, occ: int) -> Tuple[int, np.ndarray]:
        if k == len(remaining_idx):
            d = np.zeros((n, n), dtype=np.int64)
            b = occ
            while b:
                lsb = b & -b
                idx = lsb.bit_length() - 1
                r, c = divmod(idx, n)
                d[r, c] = 1
                b ^= lsb
            return 1, d
        total = 0
        dens = np.zeros((n, n), dtype=np.int64)
        si = remaining_idx[k]
        for seg in all_masks[si]:
            if occ & seg:
                continue
            sub, dsub = dfs(k + 1, occ | seg)
            total += sub
            dens += dsub
        return total, dens

    total, density = dfs(0, fixed)
    return density, int(total)


def approximate_placement_density_given_first_ship(
    rules: HouseRules,
    first_fleet_index: int,
    fixed_segment_mask: int,
    *,
    n_samples: int,
    rng: Any,
) -> np.ndarray:
    """Monte Carlo occupancy totals (biased; fast on large fleets).

    Each trial shuffles the remaining ships and, in that order, picks a
    uniformly chosen segment disjoint from ships placed so far. Failed trials
    (no legal segment left) are skipped. The heatmap aggregates successful
    trials only.
    """
    if n_samples <= 0:
        raise ValueError("n_samples must be positive")
    n = rules.board_size
    fleet = rules.fleet
    if not (0 <= first_fleet_index < len(fleet)):
        raise IndexError("first_fleet_index out of range")
    spec = fleet[first_fleet_index]
    if not is_valid_cardinal_segment(fixed_segment_mask, n, spec.length):
        raise ValueError("fixed_segment_mask is not a valid cardinal segment for that ship")

    all_masks = segment_masks_for_rules(rules)
    remaining_idx = [i for i in range(len(fleet)) if i != first_fleet_index]
    density = np.zeros((n, n), dtype=np.int64)

    for _ in range(n_samples):
        occ = int(fixed_segment_mask)
        order = list(remaining_idx)
        rng.shuffle(order)
        ok = True
        for si in order:
            choices = [seg for seg in all_masks[si] if not (occ & seg)]
            if not choices:
                ok = False
                break
            seg = int(rng.choice(choices))
            occ |= seg
        if not ok:
            continue
        b = occ
        while b:
            lsb = b & -b
            idx = lsb.bit_length() - 1
            r, c = divmod(idx, n)
            density[r, c] += 1
            b ^= lsb

    return density
