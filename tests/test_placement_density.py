"""Tests for conditional fleet placement occupancy counts."""

import numpy as np

from src.analysis.placement_density import (
    approximate_placement_density_given_first_ship,
    cardinal_segment_masks,
    placement_density_given_first_ship,
)
from src.rules import FleetShipSpec, HouseRules


def test_two_destroyers_on_2x2_one_fixed():
    rules = HouseRules(
        board_size=2,
        fleet=(
            FleetShipSpec("D1", 1),
            FleetShipSpec("D2", 1),
        ),
    )
    masks = cardinal_segment_masks(2, 1)
    assert len(masks) == 4
    corner = masks[0]
    d, total = placement_density_given_first_ship(rules, 0, corner)
    assert total == 3
    assert d.sum() == 6
    assert int(d.max()) == 3


def test_density_matches_total_on_fixed_cells():
    rules = HouseRules(
        board_size=3,
        fleet=(FleetShipSpec("S", 2),),
    )
    m = cardinal_segment_masks(3, 2)[0]
    d, total = placement_density_given_first_ship(rules, 0, m)
    assert total == 1
    assert d.sum() == 2


def test_invalid_mask_raises():
    rules = HouseRules(board_size=3, fleet=(FleetShipSpec("S", 2),))
    bad = 0b101  # two bits not adjacent horizontally/vertically on row
    try:
        placement_density_given_first_ship(rules, 0, bad)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")


def test_conditional_smoke_small_fleet():
    """Faster than full 10x10 classic fleet; still exercises multi-ship recursion."""
    rules = HouseRules(
        board_size=5,
        fleet=(
            FleetShipSpec("Cruiser", 3),
            FleetShipSpec("Destroyer", 2),
        ),
    )
    n = rules.board_size
    # Horizontal cruiser along top row.
    m = sum(1 << (0 * n + j) for j in range(3))
    density, total = placement_density_given_first_ship(rules, 0, m)
    assert total > 0
    assert density[0, 0] == density[0, 2] == total
    assert np.all(density >= 0)


def test_approximate_nonzero_with_seed():
    rules = HouseRules(
        board_size=5,
        fleet=(
            FleetShipSpec("Cruiser", 3),
            FleetShipSpec("Destroyer", 2),
        ),
    )
    n = rules.board_size
    m = sum(1 << (0 * n + j) for j in range(3))
    rng = np.random.default_rng(42)
    d = approximate_placement_density_given_first_ship(
        rules, 0, m, n_samples=500, rng=rng
    )
    assert d.sum() > 100
