import numpy as np
import pytest

from src.analysis.probability import (
    MISS,
    OPEN_HIT,
    SUNK,
    UNKNOWN,
    compute_probability_map,
    counterfactual_outcomes,
)
from src.analysis.replay import build_view_from_board
from src.board import Board
from src.ship import Carrier, Destroyer, EAST, SOUTH


def _empty_view(size: int = 10) -> np.ndarray:
    return np.full((size, size), UNKNOWN, dtype="<U1")


def test_empty_board_density_sums_to_one():
    view = _empty_view()
    pmap = compute_probability_map(view, [5, 4, 3, 3, 2])
    assert pmap.shape == (10, 10)
    assert pmap.min() >= 0
    np.testing.assert_allclose(pmap.sum(), 1.0)


def test_centre_is_higher_than_corner_in_hunt_mode():
    view = _empty_view()
    pmap = compute_probability_map(view, [5, 4, 3, 3, 2])
    assert pmap[4, 4] > pmap[0, 0]
    assert pmap[5, 5] > pmap[9, 9]


def test_miss_cell_has_zero_probability():
    view = _empty_view()
    view[4, 4] = MISS
    pmap = compute_probability_map(view, [5, 4, 3, 3, 2])
    assert pmap[4, 4] == 0


def test_open_hit_concentrates_probability_around_hit():
    view = _empty_view()
    view[4, 4] = OPEN_HIT
    pmap = compute_probability_map(view, [5, 4, 3, 3, 2])
    neighbours = [(3, 4), (5, 4), (4, 3), (4, 5)]
    far = (0, 0)
    for n in neighbours:
        assert pmap[n] > pmap[far]
    diagonal = (3, 3)
    assert pmap[max(neighbours, key=lambda n: pmap[n])] > pmap[diagonal]


def test_open_hit_known_cells_are_zero():
    view = _empty_view()
    view[4, 4] = OPEN_HIT
    pmap = compute_probability_map(view, [5, 4, 3, 3, 2])
    assert pmap[4, 4] == 0


def test_sunk_cells_have_zero_probability():
    view = _empty_view()
    view[0, 0] = SUNK
    view[0, 1] = SUNK
    pmap = compute_probability_map(view, [5, 4, 3, 3])
    assert pmap[0, 0] == 0
    assert pmap[0, 1] == 0


def test_counterfactual_outcomes_diverge():
    view = _empty_view()
    view[4, 4] = OPEN_HIT
    p_hit, p_miss = counterfactual_outcomes(view, [5, 4, 3, 3, 2], target=(4, 5))
    assert p_hit[4, 6] > p_miss[4, 6]
    assert p_miss[4, 5] == 0
    assert p_hit[4, 5] == 0


def test_counterfactual_rejects_known_target():
    view = _empty_view()
    view[2, 2] = MISS
    with pytest.raises(ValueError):
        counterfactual_outcomes(view, [5, 4, 3, 3, 2], target=(2, 2))


def test_build_view_from_live_boards_has_open_hit_after_partial_strike():
    own = Board()
    opp = Board()
    opp.place_ship(Carrier(orientation=EAST, anchor=(0, 0)))
    opp.place_ship(Destroyer(orientation=SOUTH, anchor=(5, 5)))
    opp.receive_shot(0, 0)
    opp.receive_shot(9, 9)
    view, alive, sunk = build_view_from_board(own, opp)
    assert view[0, 0] == OPEN_HIT
    assert view[9, 9] == MISS
    assert alive == [5, 2]
    assert sunk == []


def test_build_view_after_sinking_marks_full_ship_as_sunk():
    own = Board()
    opp = Board()
    opp.place_ship(Destroyer(orientation=EAST, anchor=(0, 0)))
    opp.receive_shot(0, 0)
    opp.receive_shot(0, 1)
    view, alive, sunk = build_view_from_board(own, opp)
    assert view[0, 0] == SUNK
    assert view[0, 1] == SUNK
    assert alive == []
    assert sunk == [2]
