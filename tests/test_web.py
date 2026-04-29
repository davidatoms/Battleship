import pytest

flask = pytest.importorskip("flask")  # noqa: F401

from web import app as web_app  # noqa: E402


@pytest.fixture
def client():
    web_app._state.reset(["Alice", "Bob"])
    web_app._state.phase = "idle"
    web_app._state.log.events.clear()
    with web_app.app.test_client() as client:
        yield client


def _post(client, path, payload=None):
    return client.post(path, json=payload or {})


def test_new_game_starts_setup(client):
    res = _post(client, "/api/new_game", {"names": ["Alice", "Bob"]})
    assert res.status_code == 200
    data = res.get_json()
    assert data["phase"] == "setup"
    assert data["placing"] == 0
    assert data["player_names"] == ["Alice", "Bob"]


def test_full_game_via_auto_place(client):
    _post(client, "/api/new_game", {"names": ["Alice", "Bob"]})
    res = _post(client, "/api/auto_place")
    assert res.status_code == 200
    assert res.get_json()["setup"]["done"] is True

    res = _post(client, "/api/finish_setup")
    assert res.get_json()["placing"] == 1

    _post(client, "/api/auto_place")
    res = _post(client, "/api/finish_setup")
    assert res.get_json()["phase"] == "battle"

    state = res.get_json()
    size = state["size"]
    safety = 0
    while True:
        safety += 1
        assert safety < 10000, "battle did not end in a reasonable number of shots"
        cur = state.get("phase")
        if cur == "ended":
            break
        shooter = state["current"]
        opp = 1 - shooter
        view = state["opponent_views"][opp]
        target = None
        for r in range(size):
            for c in range(size):
                if view[r][c] not in ("X", "o"):
                    target = (r, c)
                    break
            if target:
                break
        assert target is not None
        r, c = target
        res = _post(client, "/api/shoot", {"row": r, "col": c})
        assert res.status_code == 200
        state = res.get_json()

    assert state["phase"] == "ended"
    assert state["winner"] in (0, 1)


def test_log_download_returns_json(client):
    _post(client, "/api/new_game", {"names": ["Alice", "Bob"]})
    _post(client, "/api/auto_place")
    res = client.get("/api/log/download")
    assert res.status_code == 200
    assert res.mimetype == "application/json"
    body = res.get_data(as_text=True)
    assert '"events"' in body
    assert '"placement"' in body


def test_place_at_rejects_out_of_bounds(client):
    _post(client, "/api/new_game", {"names": ["A", "B"]})
    res = _post(client, "/api/place_at", {"row": 0, "col": 6, "orientation": 90})
    assert res.status_code == 400
    body = res.get_json()
    assert "error" in body
