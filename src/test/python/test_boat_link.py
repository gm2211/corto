"""The app's link to the real boat: the wire format, polling, link states, commands, and the sim-only 409s.

No hardware: a ScriptedRadio records what is sent and delivers the packets a test wants, and a fake clock
makes the timing exact. app.app is imported inside fixtures only: it loads simulator/simulator.py with ultraimport,
which registers it as sys.modules["simulator"] and would shadow the simulator package for the tests collected after.
"""
import importlib
import importlib.util
import math
import os
import sys
from unittest.mock import MagicMock

import pytest

from api.objects.commands.set_destination import SetDestination
from api.objects.nav_params.nav_params import NavParams
from api.objects.units.angle import Angle
from api.objects.units.gps_coord import GPSCoord
from api.objects.units.percent import Percent
from api.objects.units.speed import Speed
from telemetry.nav_params_recorder import NavParamsRecorder

# heading 315, rudder 75% (= +50 signed), at sea off Casco Bay, motor 20%, 3.5 kn, wind from 225, sheet 60%
GOOD = "315.0|75|43.6545,-70.223|20|3.5|225.0|60"
PLACEHOLDER = "0|0|0,0|0|0|0|0"  # what the boat answers today: no GPS, no wind vane
START = (43.6545, -70.223)
NULL_IN_BOAT_MODE = ("cog", "sog", "tws", "aws", "awa", "heel", "drift", "current_speed", "current_direction",
                     "time_scale", "sim_time", "mode", "auto_trim")
LORA_RADIO_PY = os.path.join(os.path.dirname(__file__), "..", "..", "main", "python", "lora", "radio.py")


# --- wire format ------------------------------------------------------------------------------------------

def test_nav_params_round_trip_with_float_rudder_and_negative_longitude():
    params = NavParams(
        heading=Angle(315.5), rudder_position=Percent(62.5), position=GPSCoord(43.6545, -70.223),
        motor_throttle=Percent(20), speed_over_water=Speed(3.5), true_wind_angle=Angle(225.0), sail_trim=Percent(60))
    assert NavParams.can_parse_lora_data(params.serialize_for_lora()) is True
    assert NavParams.deserialize_from_lora(params.serialize_for_lora()) == params


def test_the_boats_placeholder_telemetry_parses():
    params = NavParams.deserialize_from_lora(PLACEHOLDER)
    assert params.position == GPSCoord(0, 0) and params.rudder_position == Percent(0) and params.heading == Angle(0)


@pytest.mark.parametrize("text", [
    "", "setup", "R50", "T", "1|2|3", "1|2|3|4|5|6|7|8",
    "nan|50|1,1|0|0|0|0", "0|50|1,1|0|inf|0|0", "0|abc|1,1|0|0|0|0",
    "0|150|1,1|0|0|0|0", "0|-1|1,1|0|0|0|0", "0|50|1,1|101|0|0|0", "0|50|1,1|0|0|0|100.5",
    "0|50|91,0|0|0|0|0", "0|50|0,181|0|0|0|0", "0|50|1,2,3|0|0|0|0", "0|50|1|0|0|0|0",
])
def test_garbage_is_not_telemetry(text):
    assert NavParams.can_parse_lora_data(text) is False
    with pytest.raises(ValueError):
        NavParams.deserialize_from_lora(text)


def test_gps_coord_parses_and_validates():
    # Regression: this used to test `lat in range(-90, 91)` on a string, so nothing ever parsed, and
    # can_parse_lora_data returned None for good data
    assert GPSCoord.can_parse_lora_data("43.6545,-70.223") is True
    assert GPSCoord.deserialize_from_lora("43.6545,-70.223") == GPSCoord(43.6545, -70.223)
    assert GPSCoord.deserialize_from_lora("-90,180") == GPSCoord(-90, 180)
    for bad in ("91,0", "0,181", "-90.5,0", "abc,1", "1", "1,2,3", "nan,0", "0,inf", ""):
        assert GPSCoord.can_parse_lora_data(bad) is False
        with pytest.raises(ValueError):
            GPSCoord.deserialize_from_lora(bad)


def test_set_destination_round_trips():
    command = SetDestination(GPSCoord(43.6561, -70.2251))
    assert command.serialize_for_lora() == "D43.6561,-70.2251"
    assert SetDestination.can_parse_lora_data("D43.6561,-70.2251") is True
    assert SetDestination.deserialize_from_lora(command.serialize_for_lora()) == command
    for bad in ("D", "D91,0", "D1", "43.6,-70.2", "Dnan,0"):
        assert SetDestination.can_parse_lora_data(bad) is False


def test_the_boats_recorder_remembers_what_it_is_told():
    recorder = NavParamsRecorder()
    assert recorder.get_cur_nav_params().rudder_position == Percent(50)  # centred, not full port
    recorder.record_rudder_position(Percent(20))
    recorder.record_sail_trim(Percent(80))
    recorder.record_motor_throttle(Percent(30))
    recorder.record_speed_over_water(Speed(2.5))
    params = recorder.get_cur_nav_params()
    assert (params.rudder_position, params.sail_trim, params.motor_throttle) == (Percent(20), Percent(80), Percent(30))
    assert params.speed_over_water == Speed(2.5)
    assert NavParams.deserialize_from_lora(params.serialize_for_lora()) == params


# --- test doubles -----------------------------------------------------------------------------------------

class ScriptedRadio:
    """Records what is sent. Each 'T' is answered with the next queued reply; deliver() hears anything else."""
    last_rssi = -71.0

    def __init__(self):
        self.sent = []
        self.replies = []
        self.callback = None

    def register_callback(self, callback):
        self.callback = callback

    def send(self, message):
        self.sent.append(message)
        if message == "T" and self.replies:
            self.deliver(self.replies.pop(0))

    def deliver(self, text):
        self.callback(text)

    @property
    def commands(self):
        return [m for m in self.sent if m != "T"]


class Clock:
    """Time in whole milliseconds, so that steps of 50 ms land exactly on 2 s, 5 s, ..."""

    def __init__(self):
        self.ms = 1_000_000

    def __call__(self):
        return self.ms / 1000.0


class Link:
    """A BoatSource on a ScriptedRadio and a fake clock, plus a test client for its app."""

    def __init__(self, module, radio=None, **source_kwargs):
        self.module = module
        self.radio = radio or ScriptedRadio()
        self.clock = Clock()
        self.source = module.BoatSource(self.radio, clock=self.clock, autostart=False, **source_kwargs)
        self.client = module.create_app(self.source).test_client()

    def run(self, seconds, step_ms=50):
        """Let the link thread tick every 50 ms for `seconds`, as it does for real."""
        for _ in range(round(seconds * 1000 / step_ms)):
            self.source.tick()
            self.clock.ms += step_ms

    def post(self, path, body):
        return self.client.post(path, json=body)

    def control(self, body):
        return self.client.post("/api/control", json=body)

    def state(self):
        return self.client.get("/api/state").get_json()


@pytest.fixture()
def app_module():
    return importlib.import_module("app.app")


@pytest.fixture()
def link(app_module):
    link = Link(app_module)
    yield link
    link.source.close()


def mark(north_m, east_m):
    """A mark this many metres north and east of START."""
    lat = START[0] + north_m / 111320.0
    return {"lat": lat, "lng": START[1] + east_m / (111320.0 * math.cos(math.radians(lat)))}


def telemetry_at(lat, lng):
    return f"315.0|50|{lat},{lng}|0|3.0|225.0|50"


# --- polling ----------------------------------------------------------------------------------------------

def test_telemetry_is_polled_every_two_seconds_and_not_more_often(link):
    link.run(0.05)
    assert link.radio.sent == ["T"]
    link.run(1.9)
    assert link.radio.sent == ["T"]
    link.run(0.1)
    assert link.radio.sent == ["T", "T"]
    link.run(4.0)
    assert link.radio.sent.count("T") == 4


def test_a_poll_interval_below_the_reply_window_is_raised_to_it(app_module):
    link = Link(app_module, poll_interval_s=0.1)
    link.run(2.0)
    assert link.radio.sent.count("T") == 3  # at 0, 0.8 and 1.6 s: never inside the previous reply window


def test_telemetry_becomes_state(link):
    link.radio.replies.append(GOOD)
    link.run(0.05)
    state = link.state()
    assert state["source"] == "boat"
    assert (state["lat"], state["lng"], state["heading"]) == (43.6545, -70.223, 315.0)
    assert state["rudder"] == 50 and state["rudder_deg"] == pytest.approx(22.5)  # servo 75% = +50 signed = 22.5 deg
    assert state["twd"] == 225.0 and state["twa"] == pytest.approx(-90) and state["opt_trim"] == pytest.approx(50)
    assert (state["trim"], state["throttle"], state["stw"]) == (60, 20, 3.5)
    for key in NULL_IN_BOAT_MODE:
        assert state[key] is None, key
    assert state["link"].pop("age_s") == pytest.approx(0, abs=0.11)
    assert state["link"] == {"kind": "boat", "state": "ok", "fix": True, "rssi": -71.0, "polls": 1, "replies": 1}
    assert state["capabilities"]["manual"] and state["capabilities"]["run_course"]
    assert not any(state["capabilities"][k] for k in ("mode", "auto_trim", "demo", "environment", "time_scale", "reset"))


def test_boat_and_simulator_serve_the_same_keys(link, app_module):
    sim = app_module.create_app(app_module.SimSource(autostart=False)).test_client().get("/api/state").get_json()
    assert set(link.state()) == set(sim)  # before the first report
    link.radio.replies.append(GOOD)
    link.run(0.05)
    assert set(link.state()) == set(sim)
    assert {"source", "link", "capabilities", "commanded"} <= set(sim)


def test_nothing_known_before_the_first_report(link):
    state = link.state()
    assert state["link"]["state"] == "connecting" and state["link"]["fix"] is False and state["link"]["age_s"] is None
    assert state["lat"] is None and state["heading"] is None and state["rudder"] is None and state["twd"] is None
    # With the wind unknown nothing can be flagged upwind
    marks = [mark(0, 0), mark(0, 100)]
    state = link.post("/api/course", {"marks": marks}).get_json()["state"]
    assert state["warnings"] == [] and not any(leg["upwind"] for leg in state["course"]["legs"])


# --- link states ------------------------------------------------------------------------------------------

def test_connecting_becomes_lost_when_nothing_ever_arrives(link):
    link.run(19.0)
    assert link.state()["link"]["state"] == "connecting"
    link.run(2.0)
    state = link.state()
    assert state["link"]["state"] == "lost" and state["link"]["replies"] == 0 and state["link"]["polls"] >= 10


def test_ok_then_stale_then_lost_with_the_last_values_kept(link):
    link.radio.replies.append(GOOD)
    link.run(0.05)
    link.run(3.0)
    assert link.state()["link"]["state"] == "ok"
    link.run(3.0)  # ~6 s since the report
    state = link.state()
    assert state["link"]["state"] == "stale" and state["link"]["age_s"] == pytest.approx(6, abs=0.2)
    link.run(19.0)  # ~25 s
    state = link.state()
    assert state["link"]["state"] == "lost" and state["link"]["age_s"] == pytest.approx(25, abs=0.2)
    assert state["lat"] == 43.6545 and state["heading"] == 315.0  # the last report is still shown
    link.radio.deliver(GOOD)
    assert link.state()["link"]["state"] == "ok"


def test_the_boats_placeholder_position_means_no_fix(link):
    link.radio.replies.append(PLACEHOLDER)
    link.run(0.05)
    link.post("/api/course", {"marks": [mark(0, 50)]})
    state = link.state()
    assert state["link"]["state"] == "ok" and state["link"]["fix"] is False
    assert state["lat"] is None and state["lng"] is None and state["to_mark"] is None
    assert state["heading"] == 0 and state["rudder"] == -100  # the rest of the report is still shown


def test_packets_that_are_not_telemetry_are_ignored(link):
    for noise in ("setup", "R50", "TR20", "D43.6,-70.2", "garbage", ""):
        link.radio.deliver(noise)
    state = link.state()
    assert state["link"]["replies"] == 0 and state["link"]["state"] == "connecting" and state["heading"] is None
    link.radio.deliver(GOOD)
    link.radio.deliver("setup")
    state = link.state()
    assert state["link"]["replies"] == 1 and state["heading"] == 315.0


# --- commands ---------------------------------------------------------------------------------------------

@pytest.mark.parametrize("command,value,sent", [
    ("rudder", -60, "R20"), ("rudder", 60, "R80"), ("rudder", 0, "R50"), ("rudder", 5000, "R100"),
    ("rudder", -5000, "R0"), ("rudder", 33.4, "R67"), ("sails", 250, "S100"), ("sails", -4, "S0"),
    ("sails", 33.4, "S33"), ("throttle", 40, "TR40"), ("throttle", -5, "TR0"), ("throttle", 100.0, "TR100"),
])
def test_manual_commands_go_out_as_clamped_integers(link, command, value, sent):
    link.run(1.0)  # the first poll and its reply window are over
    state = link.control({"command": command, "value": value}).get_json()["state"]
    link.run(0.5)
    assert link.radio.commands == [sent]
    expected = {"rudder": "rudder", "sails": "trim", "throttle": "throttle"}[command]
    assert state["commanded"][expected] is not None


def test_commands_are_coalesced_and_rate_limited(link):
    link.run(1.0)
    for value in (10, 20, 30):  # three slider events before the link thread gets to run
        link.control({"command": "rudder", "value": value})
    link.run(0.05)
    assert link.radio.commands == ["R65"]  # only the latest went out
    link.control({"command": "rudder", "value": 40})
    link.run(0.2)
    assert link.radio.commands == ["R65"]  # under 0.25 s since the last rudder packet: held back
    link.run(0.1)
    assert link.radio.commands == ["R65", "R70"]
    # Other channels are not held up by the rudder's gap
    link.control({"command": "rudder", "value": 50})
    link.control({"command": "sails", "value": 70})
    link.run(0.05)
    assert "S70" in link.radio.commands


def test_the_link_stays_quiet_while_a_reply_may_be_coming(link):
    link.run(0.05)  # T goes out
    link.control({"command": "rudder", "value": 20})
    link.run(0.6)
    assert link.radio.commands == []  # still inside the reply window
    link.run(0.3)
    assert link.radio.commands == ["R60"]


def test_a_reply_ends_the_quiet_window_early(link):
    link.radio.replies.append(GOOD)
    link.run(0.05)  # T goes out and is answered at once
    link.control({"command": "rudder", "value": 20})
    link.run(0.1)
    assert link.radio.commands == ["R60"]


def test_emergency_stop_centres_everything_and_stops_sending_the_course(link):
    link.post("/api/course", {"marks": [mark(0, 100)]})
    link.radio.replies.append(telemetry_at(*START))
    link.control({"running": True})
    link.run(1.0)
    assert any(m.startswith("D") for m in link.radio.commands)
    link.control({"command": "rudder", "value": 80})
    link.run(0.5)
    link.radio.sent.clear()
    state = link.control({"command": "emergency_stop"}).get_json()["state"]
    assert state["running"] is False
    link.run(12.0)
    assert [m for m in link.radio.commands if m in ("R50", "S0", "TR0")] == ["R50", "S0", "TR0"]
    assert not any(m.startswith("D") for m in link.radio.commands)  # the course is no longer being sent
    assert (state["commanded"]["rudder"], state["commanded"]["trim"], state["commanded"]["throttle"]) == (0, 0, 0)


# --- sending a course -------------------------------------------------------------------------------------

def test_a_course_is_sent_mark_by_mark(link):
    marks = [mark(0, 100), mark(100, 100)]
    state = link.post("/api/course", {"marks": marks, "loop": False}).get_json()["state"]
    assert state["running"] is False
    link.radio.replies.append(telemetry_at(*START))
    link.run(0.05)
    assert link.radio.commands == []  # nothing is sent until "Send to boat"

    state = link.control({"running": True}).get_json()["state"]
    assert state["running"] is True
    link.run(1.0)
    first = SetDestination(GPSCoord(marks[0]["lat"], marks[0]["lng"])).serialize_for_lora()
    assert link.radio.commands == [first]
    state = link.state()
    assert state["to_mark"]["index"] == 0
    assert state["commanded"]["destination"]["index"] == 0 and state["commanded"]["destination"]["age_s"] is not None

    # The boat reports being at mark 1: mark 2 goes out
    link.radio.deliver(telemetry_at(marks[0]["lat"], marks[0]["lng"]))
    link.run(1.0)
    second = SetDestination(GPSCoord(marks[1]["lat"], marks[1]["lng"])).serialize_for_lora()
    assert link.radio.commands == [first, second]
    assert link.state()["to_mark"]["index"] == 1

    # ...and at mark 2: the course is finished and nothing more is sent
    link.radio.deliver(telemetry_at(marks[1]["lat"], marks[1]["lng"]))
    link.radio.sent.clear()
    link.run(12.0)
    state = link.state()
    assert state["running"] is False and state["course"]["finished"] is True
    assert not any(m.startswith("D") for m in link.radio.commands)


def test_the_active_mark_is_repeated_while_the_course_is_sent(link):
    link.post("/api/course", {"marks": [mark(0, 500)]})
    link.radio.replies.append(telemetry_at(*START))
    link.control({"running": True})
    link.run(9.0)
    assert len([m for m in link.radio.commands if m.startswith("D")]) == 1
    link.run(2.0)
    assert len([m for m in link.radio.commands if m.startswith("D")]) == 2
    link.control({"running": False})
    link.run(25.0)
    assert len([m for m in link.radio.commands if m.startswith("D")]) == 2


def test_editing_the_course_while_sending_resends_the_active_mark(link):
    link.post("/api/course", {"marks": [mark(0, 500)]})
    link.control({"running": True})
    link.run(1.0)
    link.post("/api/course", {"marks": [mark(0, 300)]})
    link.run(1.0)
    destinations = [m for m in link.radio.commands if m.startswith("D")]
    assert len(destinations) == 2 and destinations[0] != destinations[1]


def test_sending_needs_a_mark(link):
    assert link.control({"running": True}).status_code == 400
    assert link.state()["running"] is False


def test_clearing_the_course_stops_sending_it(link):
    link.post("/api/course", {"marks": [mark(0, 500)]})
    link.control({"running": True})
    link.run(1.0)
    state = link.client.delete("/api/course").get_json()["state"]
    assert state["running"] is False and state["course"]["marks"] == []
    link.radio.sent.clear()
    link.run(15.0)
    assert not any(m.startswith("D") for m in link.radio.commands)


# --- what the boat cannot do ------------------------------------------------------------------------------

@pytest.mark.parametrize("path,body", [
    ("/api/reset", {}),
    ("/api/reset", {"lat": 43.7, "lng": -70.1}),
    ("/api/course/demo", {}),
    ("/api/control", {"time_scale": 5}),
    ("/api/control", {"command": "set_environment", "value": {"wind_speed": 5}}),
    ("/api/control", {"mode": "auto"}),
    ("/api/control", {"mode": "manual"}),
    ("/api/control", {"auto_trim": True}),
    ("/api/control", {"mode": "auto", "running": True}),
])
def test_simulator_only_actions_are_a_409_with_the_boat(link, path, body):
    response = link.post(path, body)
    assert response.status_code == 409
    assert response.get_json()["status"] == "error" and response.get_json()["message"]
    assert link.radio.commands == []


@pytest.mark.parametrize("path,body", [
    ("/api/control", {"command": "rudder", "value": "left"}),
    ("/api/control", {"command": "rudder", "value": None}),
    ("/api/control", {"command": "rudder", "value": float("nan")}),
    ("/api/control", {"command": "sails", "value": True}),
    ("/api/control", {"command": "fly"}),
    ("/api/control", {}),
    ("/api/course", {"marks": "nope"}),
    ("/api/course", {"marks": [{"lat": 123, "lng": 0}]}),
    ("/api/course", {}),
])
def test_bad_input_is_still_a_400_with_the_boat(link, path, body):
    assert link.post(path, body).status_code == 400
    assert link.radio.commands == []


def test_bad_input_changes_nothing(link):
    link.run(1.0)
    # The command is bad, so the (valid) running flag in the same body must not be applied either
    link.post("/api/course", {"marks": [mark(0, 500)]})
    assert link.control({"running": True, "command": "fly"}).status_code == 400
    assert link.state()["running"] is False


# --- pages ------------------------------------------------------------------------------------------------

def test_the_page_names_its_source(link, app_module):
    boat = link.client.get("/").get_data(as_text=True)
    assert 'data-source="boat"' in boat and "Boat · LoRa" in boat and "<title>Corto</title>" in boat
    sim = app_module.create_app(app_module.SimSource(autostart=False)).test_client().get("/").get_data(as_text=True)
    assert 'data-source="sim"' in sim and ">Simulator<" in sim and "<title>Corto · Simulator</title>" in sim
    old_header = "boat " + "simulator"  # what the page used to call itself (split so that grepping the repo for it finds nothing)
    for page in (boat, sim):
        assert old_header not in page.lower()


# --- the loopback boat ------------------------------------------------------------------------------------

def test_loopback_end_to_end(app_module):
    simulator = app_module.SimSource(autostart=False).simulator
    link = Link(app_module, radio=app_module.LoopbackRadio(simulator))
    simulator.set_environmental_factors(12.0, 225.0, 0.0, 90.0)

    link.run(0.1)
    sim_state = simulator.get_telemetry()
    state = link.state()
    assert state["link"]["state"] == "ok" and state["link"]["fix"] is True
    assert (state["lat"], state["lng"]) == (sim_state["lat"], sim_state["lng"])
    assert state["heading"] == pytest.approx(sim_state["heading"]) and state["twd"] == pytest.approx(225.0)

    link.control({"command": "rudder", "value": 60})
    link.control({"command": "sails", "value": 70})
    link.control({"command": "throttle", "value": 30})
    link.run(1.0)
    servos = simulator.servos_controller
    assert (servos.servo_2_position.value, servos.servo_1_position.value, servos.motor_throttle.value) == (80, 70, 30)

    simulator.advance(20.0)
    link.run(2.1)  # the next poll
    state = link.state()
    sim_state = simulator.get_telemetry()
    assert state["rudder"] == pytest.approx(60) and state["trim"] == 70 and state["throttle"] == 30
    assert state["lat"] == pytest.approx(sim_state["lat"]) and state["heading"] == pytest.approx(sim_state["heading"])
    assert state["stw"] > 0

    # A destination makes the simulated boat steer to it, like the real boat does
    target = mark(100, 100)
    link.post("/api/course", {"marks": [target]})
    link.control({"running": True})
    link.run(1.0)
    assert simulator.autopilot.running and simulator.autopilot.course.target().lat == pytest.approx(target["lat"])


def test_loopback_ignores_commands_it_cannot_parse(app_module):
    simulator = app_module.SimSource(autostart=False).simulator
    radio = app_module.LoopbackRadio(simulator)
    radio.register_callback(lambda text: None)
    for message in ("", "R", "R150", "Rx", "S-3", "TR101", "D91,0", "setup", "Q"):
        radio.send(message)
    assert simulator.servos_controller.servo_2_position.value == 50


def test_a_silent_radio_never_answers(app_module):
    link = Link(app_module, radio=app_module.SilentRadio())
    link.run(21.0)
    assert link.state()["link"]["state"] == "lost" and link.state()["link"]["replies"] == 0


# --- choosing the source ----------------------------------------------------------------------------------

@pytest.fixture()
def no_physics_thread(app_module, monkeypatch):
    """build_source("auto") may return a SimSource: do not start the process-wide simulator's thread for it."""
    real = app_module.build_source.__globals__["initialize_simulator"]
    monkeypatch.setitem(app_module.build_source.__globals__, "initialize_simulator",
                        lambda autostart=True: real(autostart=False))


def test_auto_falls_back_to_the_simulator_without_the_radio_libraries(app_module, monkeypatch, no_physics_thread):
    monkeypatch.setitem(app_module.build_source.__globals__, "lora_radio_available", lambda: False)
    source = app_module.build_source("auto")
    assert source.kind == "sim" and "no LoRa radio libraries" in source.note
    source.close()


def test_auto_falls_back_when_the_radio_will_not_open(app_module, monkeypatch, no_physics_thread):
    monkeypatch.setitem(app_module.build_source.__globals__, "lora_radio_available", lambda: True)
    monkeypatch.setitem(app_module.build_source.__globals__, "_build_boat", failing_boat)
    source = app_module.build_source("auto")
    assert source.kind == "sim" and "Could not open the LoRa radio" in source.note
    source.close()


def test_an_explicit_boat_whose_radio_will_not_open_is_an_error(app_module, monkeypatch):
    # A None entry in sys.modules makes `import board` fail, as it does off the Pi; this never reaches real hardware
    monkeypatch.setitem(sys.modules, "board", None)
    monkeypatch.delitem(sys.modules, "radio", raising=False)
    with pytest.raises(app_module.SourceUnavailable) as error:
        app_module.build_source("boat")
    assert "--source sim" in str(error.value) and "--radio loopback" in str(error.value)


def failing_boat(radio, poll_interval_s):
    raise importlib.import_module("app.app").SourceUnavailable("Could not open the LoRa radio (test)")


def test_a_fake_radio_needs_the_boat_source(app_module):
    source = app_module.build_source("boat", "silent")
    assert source.kind == "boat" and source.label == "Boat · Silent"
    source.close()
    with pytest.raises(app_module.SourceUnavailable):
        app_module.build_source("sim", "loopback")
    with pytest.raises(ValueError):
        app_module.build_source("moon")


@pytest.mark.parametrize("argv", [["--source", "sim", "--radio", "silent"], ["--poll-interval", "0.2"]])
def test_bad_command_lines_exit_before_serving(app_module, argv):
    with pytest.raises(SystemExit) as exit_info:
        app_module.main(argv)
    assert exit_info.value.code == 2


# --- the radio driver (stubbed: the real one touches the GPIO when imported) -------------------------------

def test_the_radio_keeps_listening_after_it_sends(monkeypatch):
    modules = {name: MagicMock(name=name) for name in
               ("board", "busio", "digitalio", "adafruit_rfm9x", "adafruit_ssd1306", "RPi", "RPi.GPIO")}
    modules["RPi"].GPIO = modules["RPi.GPIO"]
    for name, module in modules.items():
        monkeypatch.setitem(sys.modules, name, module)
    spec = importlib.util.spec_from_file_location("radio_under_test", LORA_RADIO_PY)
    radio_module = importlib.util.module_from_spec(spec)  # not put in sys.modules: it is bound to the stubs
    spec.loader.exec_module(radio_module)

    radio = radio_module.Radio()
    heard = []
    radio.send("T")
    radio.radio.send.assert_called_with(b"T", keep_listening=False)  # nothing is listening for a callback yet

    radio.register_callback(heard.append)
    assert radio.interrupt_initialized is True
    radio.radio.send.assert_called_with(b"setup", keep_listening=True)
    radio.send("T")
    radio.radio.send.assert_called_with(b"T", keep_listening=True)

    radio.radio.last_rssi = -80
    assert radio.last_rssi == -80

    on_packet = modules["RPi.GPIO"].add_event_callback.call_args[0][1]
    radio.radio.rx_done = True
    radio.radio.receive.return_value = b"hello"
    on_packet(22)
    radio.radio.receive.return_value = b"\xff\xfe"  # noise is not always UTF-8
    on_packet(22)
    assert heard[0] == "hello" and len(heard) == 2
