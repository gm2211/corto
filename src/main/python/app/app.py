"""Flask web application for controlling and monitoring the Corto boat simulator."""

import argparse

import ultraimport
from flask import Flask, render_template, jsonify, request

# Using ultraimport for importing modules relative to this file's location
(
    initialize_simulator,
    get_boat_state,
    apply_control_request,
    set_course,
    clear_course,
    set_demo_course,
    reset_simulation,
) = ultraimport("__dir__/../simulator/simulator_integration.py", [
    "initialize_simulator",
    "get_boat_state",
    "apply_control_request",
    "set_course",
    "clear_course",
    "set_demo_course",
    "reset_simulation",
])

app = Flask(__name__)
# The UI is plain static files that change while developing: do not let the browser cache them.
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
app.config["TEMPLATES_AUTO_RELOAD"] = True

simulator = initialize_simulator()


def _json_body():
    """The request's JSON object, or an empty dict. Raises ValueError if the body is not an object."""
    data = request.get_json(silent=True)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError("expected a JSON object")
    return data


def _ok(**extra):
    return jsonify({"status": "success", **extra, "state": get_boat_state(simulator)})


@app.errorhandler(ValueError)
def _bad_request(error):
    """Invalid input from the network is a 400, never a 500."""
    return jsonify({"status": "error", "message": str(error)}), 400


@app.route('/')
def index():
    """Serve the main application page."""
    return render_template('index.html')


@app.route('/api/state')
@app.route('/api/boat-location')  # kept as an alias for the old name
def state():
    """Boat telemetry, mode and course. Polled by the UI at 10 Hz."""
    return jsonify(get_boat_state(simulator))


@app.route('/api/control', methods=['POST'])
def control():
    """Boat controls. Body: {command, value} (rudder -100..100, sails 0..100, throttle 0..100,
    emergency_stop, set_environment) and/or {mode: manual|auto, running, auto_trim, time_scale}."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not data:
        return jsonify({"status": "error", "message": "No JSON data provided"}), 400
    apply_control_request(simulator, data)
    return _ok()


@app.route('/api/course', methods=['POST'])
def course_set():
    """Replace the course. Body: {marks: [{lat, lng}, ...], loop?, active?}."""
    data = _json_body()
    if 'marks' not in data:
        raise ValueError("marks is required")
    set_course(simulator, data['marks'], data.get('loop'), data.get('active', 0))
    return _ok()


@app.route('/api/course', methods=['DELETE'])
def course_clear():
    """Remove every mark (and stop the autopilot)."""
    clear_course(simulator)
    return _ok()


@app.route('/api/course/demo', methods=['POST'])
def course_demo():
    """Replace the course with the demo triangle, laid out from the boat and rotated to the wind."""
    data = _json_body()
    set_demo_course(simulator, data.get('scale'))
    return _ok()


@app.route('/api/reset', methods=['POST'])
def reset():
    """Put the boat back at the start (or {lat, lng, heading?}) at rest, with neutral controls."""
    data = _json_body()
    reset_simulation(simulator, data.get('lat'), data.get('lng'), data.get('heading'))
    return _ok()


def main(argv=None):
    """Run the simulator UI: `python src/main/python/app/app.py --port 5000`."""
    parser = argparse.ArgumentParser(description='Run the Corto boat simulator app')
    parser.add_argument('--host', default='127.0.0.1', help='Interface to bind (default: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=5000, help='Port to run the app on (default: 5000)')
    args = parser.parse_args(argv)

    # use_reloader=False: the reloader would start a second process (and a second simulator thread)
    app.run(host=args.host, port=args.port, debug=False, use_reloader=False, threaded=True)


if __name__ == '__main__':
    main()
