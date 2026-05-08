from src.rules import (
    CLASSIC_FLEET,
    FleetShipSpec,
    HouseRules,
    default_rules,
    fleet_specs_as_json,
    house_rules_from_events,
    partition_fleet_after_sinks,
    remaining_lengths_after_sinks,
)


def test_default_rules_classic_fleet():
    r = default_rules()
    assert r.board_size == 10
    assert len(r.fleet) == 5


def test_fleet_specs_as_json_roundtrip():
    r = default_rules()
    ev = {"type": "game_start", "size": 10, "fleet": fleet_specs_as_json(r)}
    recovered = house_rules_from_events([ev])
    assert recovered.fleet == CLASSIC_FLEET


def test_partition_after_sink_removes_spec():
    r = default_rules()
    sunk, alive = partition_fleet_after_sinks(r, ["Carrier"])
    assert [s.length for s in sunk] == [5]
    assert [s.name for s in alive] == [
        "Battleship",
        "Cruiser",
        "Submarine",
        "Destroyer",
    ]


def test_remaining_lengths_sorted():
    r = default_rules()
    lengths = remaining_lengths_after_sinks(r, ["Destroyer", "Submarine"])
    assert lengths == [5, 4, 3]


def test_custom_fleet_in_game_start():
    custom = HouseRules(
        board_size=8,
        fleet=(
            FleetShipSpec("Dinghy", 2),
            FleetShipSpec("Dinghy", 2),
        ),
    )
    ev = {"type": "game_start", "size": 8, "fleet": fleet_specs_as_json(custom)}
    got = house_rules_from_events([ev])
    assert got.board_size == 8
    assert len(got.fleet) == 2
