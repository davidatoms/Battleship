"""Driver that turns a Battleship game log into PNG visualisations.

This is the function the CLI and the web app both call when the user
asks for a "log + visualisations" bundle.  It is deliberately the only
place that imports matplotlib, so the rest of the engine stays cheap
to import.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

import numpy as np

from ..game.log import GameLog
from .probability import (
    UNKNOWN,
    compute_probability_map,
    counterfactual_outcomes,
)
from .replay import replay_state


LogInput = Union[GameLog, str, Path]


def _safe_filename(stem: str) -> str:
    return "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in stem)


def _walk_turns(events: Sequence[Dict[str, Any]], shooter: Optional[int]):
    for idx, ev in enumerate(events):
        if ev.get("type") != "turn":
            continue
        if shooter is not None and ev.get("shooter") != shooter:
            continue
        if ev.get("outcome") in ("invalid", "already"):
            continue
        yield idx, ev


def _coerce_log(log: LogInput) -> "tuple[GameLog, Optional[Path]]":
    if isinstance(log, GameLog):
        return log, None
    path = Path(log)
    return GameLog.load(path), path


def visualise_log(
    log: LogInput,
    output_dir: Union[str, Path],
    *,
    shooter: Optional[int] = None,
    resolution: int = 240,
    per_turn: bool = False,
    max_turns: Optional[int] = None,
    aggregate: bool = True,
    label: Optional[str] = None,
    well_3d: bool = False,
    well_pivot: str = "max_prob",
    well_resolution: int = 100,
    well_frames: int = 24,
    well_fps: int = 12,
    step_csv: bool = False,
    step_csv_name: str = "steps.csv",
    step_include_prior: bool = True,
    step_max_steps: Optional[int] = None,
) -> List[Path]:
    """Render probability-field visualisations for ``log``.

    Parameters
    ----------
    log :
        Either an in-memory :class:`~src.game.log.GameLog` or a path to
        a saved JSON log file.
    output_dir :
        Directory to write PNGs into.  It is created if needed.
    shooter :
        If given (0 or 1), per-turn figures are restricted to that
        shooter's perspective.
    resolution :
        Pixels per side of the continuous energy fields.
    per_turn :
        Emit a 4-panel figure for each shot (discrete view, prior,
        counterfactual hit, counterfactual miss).
    max_turns :
        Cap on the number of per-turn figures.  ``None`` means no cap.
    aggregate :
        Emit a side-by-side aggregate "after hits vs after misses"
        figure averaged over the whole log.
    label :
        Optional human-readable label baked into the aggregate title.
    well_3d :
        Also emit a 360-degree rotating 3-D "energy well" GIF for each
        per-turn frame, plus an aggregate well GIF over the average
        post-hit posterior.  Slower than the 2-D figures.
    well_pivot :
        Pivot policy for the 3-D animation.  ``"max_prob"`` orbits the
        deepest well (= cell most likely to hide a ship at that turn);
        ``"shot_cell"`` orbits the cell the player actually fired at.
    well_resolution, well_frames, well_fps :
        Tuning knobs for the GIF output.
    step_csv :
        Also emit per-step single-panel heatmaps (prior / if hit / if
        miss) for every turn and a ``steps.csv`` index whose rows pair
        each turn's metadata with on-disk image paths.
    step_csv_name :
        Name of the manifest CSV (default ``steps.csv``).
    step_include_prior :
        Whether to render the prior-posterior PNG for each step (the
        counterfactual hit/miss images are always rendered).
    step_max_steps :
        Cap how many step rows / PNG triplets are emitted.  ``None``
        means export every eligible turn in the log.

    Returns
    -------
    list of :class:`Path` objects -- the PNGs that were written.
    """
    # Lazy-import: matplotlib startup is expensive and we don't want
    # the CLI/web import path to pay for it unless visualisations are
    # actually requested.
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from .plotting import plot_aggregate_hit_vs_miss, plot_turn_summary

    if well_3d:
        from .well3d import render_well_animation

    log_obj, log_path = _coerce_log(log)
    events = list(log_obj.events)

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    generated: List[Path] = []

    if step_csv:
        from .steps import export_step_index

        csv_path, manifest_path = export_step_index(
            log_obj,
            out_dir,
            shooter=shooter,
            resolution=resolution,
            include_prior=step_include_prior,
            csv_name=step_csv_name,
            max_steps=step_max_steps,
        )
        generated.extend([csv_path, manifest_path])
        for asset in sorted(out_dir.iterdir()):
            if asset.is_file() and asset.name.startswith("step_"):
                generated.append(asset)

    players = ["Player 0", "Player 1"]
    for ev in events:
        if ev.get("type") == "game_start" and isinstance(ev.get("players"), list):
            names = ev["players"]
            if len(names) == 2:
                players = [str(n) for n in names]

    by_outcome_hit: List[np.ndarray] = []
    by_outcome_miss: List[np.ndarray] = []

    turn_counter = 0
    for ev_idx, ev in _walk_turns(events, shooter):
        ev_shooter = int(ev["shooter"])
        target = tuple(int(x) for x in ev["target"])
        outcome = ev.get("outcome")

        view, alive_lengths, _ = replay_state(events, up_to_index=ev_idx, shooter=ev_shooter)
        if view[target[0], target[1]] != UNKNOWN:
            continue
        prior = compute_probability_map(view, alive_lengths)
        try:
            p_hit, p_miss = counterfactual_outcomes(view, alive_lengths, target)
        except ValueError:
            continue

        if outcome in ("hit", "sunk"):
            by_outcome_hit.append(p_hit)
        elif outcome == "miss":
            by_outcome_miss.append(p_miss)

        if per_turn and (max_turns is None or turn_counter < max_turns):
            turn_counter += 1
            fig = plot_turn_summary(
                view,
                prior,
                p_hit,
                p_miss,
                target=target,
                actual_outcome=outcome,
                shooter_name=players[ev_shooter],
                turn_index=turn_counter,
                resolution=resolution,
            )
            out = out_dir / f"turn_{turn_counter:03d}_{_safe_filename(str(outcome))}.png"
            fig.savefig(out, dpi=140, bbox_inches="tight")
            plt.close(fig)
            generated.append(out)

            if well_3d:
                gif = out_dir / f"turn_{turn_counter:03d}_well.gif"
                render_well_animation(
                    prior,
                    gif,
                    resolution=well_resolution,
                    n_frames=well_frames,
                    fps=well_fps,
                    title=(
                        f"{players[ev_shooter]} -- turn {turn_counter} "
                        f"-- prior posterior"
                    ),
                    pivot_mode=well_pivot,
                    shot_cell=target,
                )
                generated.append(gif)

    if aggregate and by_outcome_hit and by_outcome_miss:
        mean_hit = np.mean(by_outcome_hit, axis=0)
        mean_miss = np.mean(by_outcome_miss, axis=0)
        title_label = label or (log_path.name if log_path is not None else "game")
        fig = plot_aggregate_hit_vs_miss(
            mean_hit,
            mean_miss,
            resolution=max(resolution, 320),
            title=(
                f"{title_label}: mean posterior right after a hit "
                f"({len(by_outcome_hit)} shots) vs after a miss "
                f"({len(by_outcome_miss)} shots)"
            ),
        )
        out = out_dir / "aggregate_hit_vs_miss.png"
        fig.savefig(out, dpi=160, bbox_inches="tight")
        plt.close(fig)
        generated.append(out)

        if well_3d:
            gif = out_dir / "aggregate_well.gif"
            render_well_animation(
                mean_hit,
                gif,
                resolution=well_resolution,
                n_frames=well_frames,
                fps=well_fps,
                title=f"{title_label}\nmean posterior after hits",
                pivot_mode="max_prob",
            )
            generated.append(gif)

    return generated
