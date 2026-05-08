"""Per-step heatmap export with a CSV manifest.

For every turn in a game log this module renders three single-panel
probability heatmaps -- the prior posterior, the counterfactual
"if HIT" posterior, and the counterfactual "if MISS" posterior --
and writes a ``steps.csv`` index file whose rows pair each turn's
metadata with the on-disk paths of its images.

Also writes ``steps_manifest.json`` next to the CSV so programmatic
consumers get typed rows and export metadata without parsing CSV.

The intended layout for one game is therefore::

    <output_dir>/
        battleship-log.json   # written by the caller
        steps.csv             # one row per turn
        steps_manifest.json   # same rows + export options + truncation flag
        step_001_prior.png
        step_001_hit.png
        step_001_miss.png
        ...

The CSV is portable: every path column stores just the file name
(relative to ``steps.csv``) so the directory can be moved or zipped
without breaking links.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

from ..board import Board
from ..game.log import GameLog
from .probability import (
    UNKNOWN,
    compute_probability_map,
    counterfactual_outcomes,
)
from .replay import replay_state


CSV_COLUMNS = (
    "turn",
    "event_index",
    "shooter",
    "shooter_name",
    "target_row",
    "target_col",
    "target_label",
    "outcome",
    "sunk_ship",
    "prior_path",
    "hit_path",
    "miss_path",
    "actual_path",
)

DEFAULT_MANIFEST_NAME = "steps_manifest.json"


def _label(target: Tuple[int, int]) -> str:
    r, c = target
    return f"{Board._column_label(c)}{r + 1}"


def _render_field(
    prob_map: np.ndarray,
    output_path: Path,
    *,
    title: str,
    cmap: str,
    target: Optional[Tuple[int, int]] = None,
    resolution: int = 240,
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from .plotting import plot_probability_field

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(5, 5))
    plot_probability_field(
        ax,
        prob_map,
        title=title,
        resolution=resolution,
        cmap=cmap,
        overlay_target=target,
    )
    fig.tight_layout()
    fig.savefig(output_path, dpi=140, bbox_inches="tight")
    plt.close(fig)


def _coerce_log(log: Union[GameLog, str, Path]) -> GameLog:
    if isinstance(log, GameLog):
        return log
    return GameLog.load(Path(log))


def _more_eligible_turns_remain(
    events: List[Dict[str, Any]],
    last_ev_idx: int,
    shooter: Optional[int],
) -> bool:
    """True iff another turn after ``last_ev_idx`` would export a row."""
    for ev_idx in range(last_ev_idx + 1, len(events)):
        ev = events[ev_idx]
        if ev.get("type") != "turn":
            continue
        if shooter is not None and ev.get("shooter") != shooter:
            continue
        if ev.get("outcome") in ("invalid", "already"):
            continue
        ev_shooter = int(ev.get("shooter", 0))
        target_raw = ev.get("target") or [0, 0]
        target = (int(target_raw[0]), int(target_raw[1]))
        view, alive_lengths, _ = replay_state(
            events, up_to_index=ev_idx, shooter=ev_shooter
        )
        if view[target[0], target[1]] != UNKNOWN:
            continue
        try:
            counterfactual_outcomes(view, alive_lengths, target)
        except ValueError:
            continue
        return True
    return False


def _write_manifest(
    path: Path,
    *,
    csv_name: str,
    rows: List[Dict[str, Any]],
    shooter: Optional[int],
    resolution: int,
    include_prior: bool,
    max_steps: Optional[int],
    truncated: bool,
) -> None:
    payload = {
        "version": 1,
        "kind": "step_heatmaps",
        "csv": csv_name,
        "truncated": truncated,
        "exported_rows": len(rows),
        "options": {
            "shooter": shooter,
            "resolution": resolution,
            "include_prior": include_prior,
            "max_steps": max_steps,
        },
        "columns": list(CSV_COLUMNS),
        "rows": rows,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def export_step_index(
    log: Union[GameLog, str, Path],
    output_dir: Union[str, Path],
    *,
    shooter: Optional[int] = None,
    resolution: int = 240,
    include_prior: bool = True,
    csv_name: str = "steps.csv",
    manifest_name: str = DEFAULT_MANIFEST_NAME,
    max_steps: Optional[int] = None,
) -> Tuple[Path, Path]:
    """Render per-step heatmaps and write the CSV + JSON manifests.

    ``max_steps``, when set, caps how many turns are exported (PNG + CSV
    rows).  Must be positive when provided.  The aggregate figures
    elsewhere are unaffected.

    Returns ``(csv_path, manifest_path)``.  An empty CSV (header only)
    and an empty ``rows`` array in the manifest are written if the log
    has no resolvable turns.
    """
    log_obj = _coerce_log(log)
    events = list(log_obj.events)

    if max_steps is not None and max_steps <= 0:
        raise ValueError("max_steps must be positive when set")

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    rows: List[Dict[str, Any]] = []
    turn_counter = 0
    truncated = False
    break_ev_idx: Optional[int] = None

    for ev_idx, ev in enumerate(events):
        if ev.get("type") != "turn":
            continue
        if shooter is not None and ev.get("shooter") != shooter:
            continue
        outcome = str(ev.get("outcome", ""))
        if outcome in ("invalid", "already"):
            continue

        ev_shooter = int(ev.get("shooter", 0))
        target_raw = ev.get("target") or [0, 0]
        target = (int(target_raw[0]), int(target_raw[1]))

        view, alive_lengths, _ = replay_state(
            events, up_to_index=ev_idx, shooter=ev_shooter
        )
        if view[target[0], target[1]] != UNKNOWN:
            continue

        prior = compute_probability_map(view, alive_lengths)
        try:
            p_hit, p_miss = counterfactual_outcomes(view, alive_lengths, target)
        except ValueError:
            continue

        turn_counter += 1
        prefix = f"step_{turn_counter:03d}"
        prior_path = out_dir / f"{prefix}_prior.png"
        hit_path = out_dir / f"{prefix}_hit.png"
        miss_path = out_dir / f"{prefix}_miss.png"

        if include_prior:
            _render_field(
                prior,
                prior_path,
                title=f"Step {turn_counter} -- prior",
                cmap="viridis",
                target=target,
                resolution=resolution,
            )
        _render_field(
            p_hit,
            hit_path,
            title=f"Step {turn_counter} -- if HIT",
            cmap="magma",
            target=target,
            resolution=resolution,
        )
        _render_field(
            p_miss,
            miss_path,
            title=f"Step {turn_counter} -- if MISS",
            cmap="cividis",
            target=target,
            resolution=resolution,
        )

        actual_path = hit_path if outcome in ("hit", "sunk") else miss_path

        row_dict: Dict[str, Any] = {
            "turn": turn_counter,
            "event_index": ev_idx,
            "shooter": ev_shooter,
            "shooter_name": ev.get("shooter_name", ""),
            "target_row": target[0],
            "target_col": target[1],
            "target_label": ev.get("target_label") or _label(target),
            "outcome": outcome,
            "sunk_ship": ev.get("sunk_ship") or "",
            "prior_path": prior_path.name if include_prior else "",
            "hit_path": hit_path.name,
            "miss_path": miss_path.name,
            "actual_path": actual_path.name,
        }
        rows.append(row_dict)

        if max_steps is not None and len(rows) >= max_steps:
            break_ev_idx = ev_idx
            break

    if max_steps is not None and break_ev_idx is not None:
        truncated = _more_eligible_turns_remain(events, break_ev_idx, shooter)

    csv_path = out_dir / csv_name
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(CSV_COLUMNS))
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    manifest_path = out_dir / manifest_name
    _write_manifest(
        manifest_path,
        csv_name=csv_name,
        rows=rows,
        shooter=shooter,
        resolution=resolution,
        include_prior=include_prior,
        max_steps=max_steps,
        truncated=truncated,
    )
    return csv_path, manifest_path
