"""The Flask API: signed rudder end to end, clamping instead of 500s, course and reset endpoints."""
import importlib

import pytest


@pytest.fixture()
def client():
    module = importlib.import_module("app.app")
    simulator = module.simulator
    # Deterministic: park the background physics thread's effect by resetting before and after each test
    module.reset_simulation(simulator)
    simulator.set_environmental_factors(12.0, 225.0, 0.0, 90.0)
    simulator.autopilot.course.clear()
    yield module.app.test_client()
    module.reset_simulation(simulator)
    simulator.autopilot.course.clear()


def post(client, path, body):
    return client.post(path, json=body)


def test_state_endpoint_and_alias_have_the_same_shape(client):
    a, b = client.get("/api/state").get_json(), client.get("/api/boat-location").get_json()
    assert set(a) == set(b)
    for key in ("lat", "lng", "heading", "cog", "sog", "tws", "twd", "rudder", "trim", "mode", "course", "time_scale"):
        assert key in a
    assert a["mode"] == "manual" and a["course"]["marks"] == []


@pytest.mark.parametrize("sent,expected", [(-60, -60), (60, 60), (0, 0), (100, 100), (-100, -100), (5000, 100), (-5000, -100)])
def test_rudder_is_signed_end_to_end_and_clamped(client, sent, expected):
    r = post(client, "/api/control", {"command": "rudder", "value": sent})
    assert r.status_code == 200
    assert r.get_json()["state"]["rudder"] == pytest.approx(expected)


def test_sails_and_throttle_are_clamped_not_abs(client):
    assert post(client, "/api/control", {"command": "sails", "value": -20}).get_json()["state"]["trim"] == 0
    assert post(client, "/api/control", {"command": "sails", "value": 250}).get_json()["state"]["trim"] == 100
    assert post(client, "/api/control", {"command": "throttle", "value": -40}).get_json()["state"]["throttle"] == 0
    assert post(client, "/api/control", {"command": "throttle", "value": 40}).get_json()["state"]["throttle"] == 40


@pytest.mark.parametrize("body", [
    {"command": "rudder", "value": "left"},
    {"command": "rudder", "value": None},
    {"command": "rudder", "value": float("nan")},
    {"command": "rudder", "value": True},
    {"command": "fly"},
    {"mode": "sideways"},
    {"time_scale": "fast"},
    {"command": "set_environment", "value": [1, 2]},
    {},
])
def test_bad_input_is_a_400_not_a_500(client, body):
    assert post(client, "/api/control", body).status_code == 400


def test_garbage_body_is_a_400(client):
    assert client.post("/api/control", data="not json", content_type="application/json").status_code == 400


def test_time_scale_is_clamped(client):
    assert post(client, "/api/control", {"time_scale": 5}).get_json()["state"]["time_scale"] == 5
    assert post(client, "/api/control", {"time_scale": 1e6}).get_json()["state"]["time_scale"] == 30
    assert post(client, "/api/control", {"time_scale": -3}).get_json()["state"]["time_scale"] == 1
    post(client, "/api/control", {"time_scale": 15})


def test_environment_updates_are_partial_and_clamped(client):
    state = post(client, "/api/control", {"command": "set_environment", "value": {"wind_speed": 18, "wind_direction": 400}}).get_json()["state"]
    assert state["tws"] == 18 and state["twd"] == pytest.approx(40)
    assert post(client, "/api/control", {"command": "set_environment", "value": {"wind_speed": 9999}}).get_json()["state"]["tws"] <= 60


def test_course_set_clear_and_demo(client):
    marks = [{"lat": 43.656, "lng": -70.225}, {"lat": 43.657, "lng": -70.224}]
    state = post(client, "/api/course", {"marks": marks, "loop": False}).get_json()["state"]
    assert len(state["course"]["marks"]) == 2 and state["course"]["loop"] is False
    assert state["to_mark"]["index"] == 0
    assert post(client, "/api/course", {"marks": [{"lat": 123, "lng": 0}]}).status_code == 400
    assert post(client, "/api/course", {"marks": "nope"}).status_code == 400
    assert post(client, "/api/course", {}).status_code == 400
    assert client.delete("/api/course").get_json()["state"]["course"]["marks"] == []
    demo = post(client, "/api/course/demo", {}).get_json()["state"]["course"]
    assert len(demo["marks"]) == 3 and demo["loop"] is True and not any(leg["upwind"] for leg in demo["legs"])


def test_upwind_mark_is_flagged_in_the_state(client):
    state = client.get("/api/state").get_json()
    # about 200 m dead upwind (wind from 225) of the boat
    marks = [{"lat": state["lat"] - 0.00127, "lng": state["lng"] - 0.00176}]
    result = post(client, "/api/course", {"marks": marks}).get_json()["state"]
    assert result["to_mark"]["upwind"] is True and result["warnings"]


def test_autopilot_mode_and_start_pause(client):
    post(client, "/api/course/demo", {})
    state = post(client, "/api/control", {"mode": "auto"}).get_json()["state"]
    assert state["mode"] == "auto" and state["running"] is False
    state = post(client, "/api/control", {"running": True}).get_json()["state"]
    assert state["running"] is True
    state = post(client, "/api/control", {"command": "emergency_stop"}).get_json()["state"]
    assert state["mode"] == "manual" and state["running"] is False and state["rudder"] == 0 and state["trim"] == 0


def test_reset_puts_the_boat_back(client):
    state = post(client, "/api/reset", {"lat": 43.7, "lng": -70.1, "heading": 42}).get_json()["state"]
    assert state["lat"] == pytest.approx(43.7, abs=1e-4) and state["lng"] == pytest.approx(-70.1, abs=1e-4)
    assert state["heading"] == pytest.approx(42, abs=0.5) and state["stw"] == pytest.approx(0, abs=0.05)
    assert post(client, "/api/reset", {"lat": 43.7}).status_code == 400
    assert post(client, "/api/reset", {"lat": 999, "lng": 0}).status_code == 400
    state = post(client, "/api/reset", {}).get_json()["state"]
    assert state["lat"] == pytest.approx(43.6545, abs=1e-4) and state["heading"] == pytest.approx(315, abs=0.5)
