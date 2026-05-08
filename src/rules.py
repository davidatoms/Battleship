"""House rules and fleet specification for Battleship.

Use :class:`HouseRules` to configure board size, which ships (names and
lengths) each player fields, and optional gameplay flags.  The classic
Hasbro-style fleet is the default.

Fleet inference
---------------

Once you know the agreed ruleset and which opponent ships you have
already sunk (names come from turn events in the log), you can compute
exactly how many ships remain and of what lengths via
:func:`remaining_specs_after_sinks` and :func:`remaining_lengths_after_sinks`.
That matches what a human deduces after sinking the Carrier they know
the opponent started with one fewer capital ship, etc.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from collections import Counter

from .ship import Ship

# ---------------------------------------------------------------------------
# Fleet specs (immutable tuples so defaults stay hashable / frozen-rules safe)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FleetShipSpec:
    """One ship type in the fleet (name + segment length)."""

    name: str
    length: int


# Classic 1990s Hasbro-style fleet: 5 ships, 17 occupied cells total.
CLASSIC_FLEET: Tuple[FleetShipSpec, ...] = (
    FleetShipSpec("Carrier", 5),
    FleetShipSpec("Battleship", 4),
    FleetShipSpec("Cruiser", 3),
    FleetShipSpec("Submarine", 3),
    FleetShipSpec("Destroyer", 2),
)


@dataclass(frozen=True)
class HouseRules:
    """Configurable rules for a Battleship session.

    Attributes
    ----------
    board_size :
        Square grid side length (classic is 10).
    fleet :
        Ordered list of ships each player places. Duplicates are allowed
        (e.g. two Destroyers) if your house allows it.
    cardinal_placement_only :
        If True, only N/E/S/W orientations are intended for placement UIs
        (the engine still supports diagonals in the model unless you block them).
    salvo_shots_per_turn :
        Placeholder for salvo variants (shots per turn); not enforced by
        :class:`~src.game.engine.Engine` yet.
    reveal_ship_class_on_sink :
        If True, logs include ``sunk_ship`` names (current behaviour). Some
        house rules hide class until game end — then inference uses lengths only.
    """

    board_size: int = 10
    fleet: Tuple[FleetShipSpec, ...] = CLASSIC_FLEET
    cardinal_placement_only: bool = False
    salvo_shots_per_turn: int = 1
    reveal_ship_class_on_sink: bool = True


def default_rules() -> HouseRules:
    """Classic 10x10 board with the standard five-ship fleet."""
    return HouseRules()


def fleet_lengths(rules: HouseRules) -> List[int]:
    """Lengths of all ships in fleet order."""
    return [s.length for s in rules.fleet]


def fleet_total_cells(rules: HouseRules) -> int:
    """Total ship segments on the board for one player."""
    return sum(s.length for s in rules.fleet)


def fleet_ship_count(rules: HouseRules) -> int:
    return len(rules.fleet)


def starting_name_counts(rules: HouseRules) -> Counter:
    """Multiset of ship names at game start."""
    return Counter(spec.name for spec in rules.fleet)


def build_fleet_from_rules(rules: HouseRules) -> List[Ship]:
    """Instantiate :class:`~src.ship.Ship` instances from ``rules.fleet``."""
    return [Ship(name=spec.name, length=spec.length) for spec in rules.fleet]


def fleet_specs_as_json(rules: HouseRules) -> List[Dict[str, Union[str, int]]]:
    """Serializable fleet description for ``game_start`` log events."""
    return [{"name": s.name, "length": s.length} for s in rules.fleet]


def house_rules_from_events(events: Sequence[Dict[str, Any]]) -> HouseRules:
    """Recover :class:`HouseRules` from the first ``game_start`` event, if any."""
    for ev in events:
        if ev.get("type") != "game_start":
            continue
        size = int(ev.get("size", 10))
        raw = ev.get("fleet")
        if isinstance(raw, list) and raw:
            specs: List[FleetShipSpec] = []
            for item in raw:
                if isinstance(item, dict) and "name" in item and "length" in item:
                    specs.append(
                        FleetShipSpec(str(item["name"]), int(item["length"]))
                    )
            if specs:
                return HouseRules(board_size=size, fleet=tuple(specs))
        return HouseRules(board_size=size)
    return default_rules()


def partition_fleet_after_sinks(
    rules: HouseRules,
    sunk_ship_names: Sequence[str],
) -> Tuple[List[FleetShipSpec], List[FleetShipSpec]]:
    """Split the starting fleet into ships accounted for by sinks vs still alive.

    Returns ``(sunk_specs_in_event_order, alive_specs)``. Unrecognized names in
    ``sunk_ship_names`` are skipped without consuming a spec.
    """
    pool = list(rules.fleet)
    sunk_ordered: List[FleetShipSpec] = []
    for want in sunk_ship_names:
        idx = None
        for i, spec in enumerate(pool):
            if spec.name == want:
                idx = i
                break
        if idx is None:
            continue
        sunk_ordered.append(pool.pop(idx))
    return sunk_ordered, pool


def remaining_specs_after_sinks(
    rules: HouseRules,
    sunk_ship_names: Sequence[str],
) -> List[FleetShipSpec]:
    """Ship specs still afloat given sinking events."""
    _, alive = partition_fleet_after_sinks(rules, sunk_ship_names)
    return alive


def remaining_lengths_after_sinks(
    rules: HouseRules,
    sunk_ship_names: Sequence[str],
) -> List[int]:
    """Sorted lengths of ships still alive (longest first), for hunt/target logic."""
    specs = remaining_specs_after_sinks(rules, sunk_ship_names)
    return sorted((s.length for s in specs), reverse=True)


def infer_opponent_alive_lengths_from_log(
    rules: HouseRules,
    events: Sequence[dict],
    *,
    shooter: int,
    up_to_index: Optional[int] = None,
) -> List[int]:
    """Collect sunk opponent ship names from turn events and return alive lengths.

    Use when you do not have opponent placement data but do have a ruleset and
    a log that records ``sunk_ship`` on sinking shots.
    """
    if up_to_index is None:
        up_to_index = len(events)
    sunk_names: List[str] = []
    for ev in events[:max(0, up_to_index)]:
        if ev.get("type") != "turn":
            continue
        if ev.get("shooter") != shooter:
            continue
        if ev.get("outcome") != "sunk":
            continue
        name = ev.get("sunk_ship")
        if name:
            sunk_names.append(str(name))
    return remaining_lengths_after_sinks(rules, sunk_names)
