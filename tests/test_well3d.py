import numpy as np
import pytest


def test_render_well_animation_writes_a_gif(tmp_path):
    pytest.importorskip("matplotlib")
    pytest.importorskip("PIL")

    from src.analysis.well3d import find_pivot, render_well_animation

    rng = np.random.default_rng(0)
    pmap = rng.random((10, 10))
    pmap[4, 4] = pmap.max() + 0.5

    pivot = find_pivot(pmap, mode="max_prob")
    assert pivot == (4, 4)

    out = tmp_path / "well.gif"
    render_well_animation(
        pmap,
        out,
        resolution=40,
        n_frames=4,
        fps=8,
        title="Test well",
    )
    assert out.exists()
    assert out.stat().st_size > 1000
    assert out.read_bytes()[:6] in (b"GIF87a", b"GIF89a")


def test_pivot_modes_work():
    from src.analysis.well3d import find_pivot

    pmap = np.zeros((5, 5))
    pmap[2, 3] = 1.0

    assert find_pivot(pmap, mode="max_prob") == (2, 3)
    assert find_pivot(pmap, mode="shot_cell", shot_cell=(0, 0)) == (0, 0)
    assert find_pivot(pmap, mode="explicit", explicit=(4, 4)) == (4, 4)


def test_pivot_mode_validation():
    from src.analysis.well3d import find_pivot

    pmap = np.zeros((5, 5))
    with pytest.raises(ValueError):
        find_pivot(pmap, mode="explicit")
    with pytest.raises(ValueError):
        find_pivot(pmap, mode="shot_cell")
