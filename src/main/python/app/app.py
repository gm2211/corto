"""Corto web app: shows the boat live over LoRa, or the simulator (test bench), chosen at startup."""

import argparse

import ultraimport
from flask import Flask, render_template, jsonify, request

# Using ultraimport for importing modules relative to this file's location
(
    NotAvailable,
    SimSource,
    SourceUnavailable,
    build_source,
    lora_radio_available,
) = ultraimport("__dir__/sources.py", [
    "NotAvailable",
    "SimSource",
    "SourceUnavailable",
    "build_source",
    "lora_radio_available",
])
(
    BoatSource,
    LoopbackRadio,
    SilentRadio,
) = ultraimport("__dir__/boat_link.py", ["BoatSource", "LoopbackRadio", "SilentRadio"])

# What the tests (and other scripts) take from this module
__all__ = ["NotAvailable", "SimSource", "BoatSource", "LoopbackRadio", "SilentRadio", "SourceUnavailable",
           "build_source", "lora_radio_available", "create_app", "main"]

# Interfaces that are not loopback: serving the boat there lets anyone on that network drive it (no auth)
LOCAL_HOSTS = ("127.0.0.1", "localhost", "::1")


def create_app(source):
    """The Flask app for one source (SimSource or BoatSource); routes close over it."""
    app = Flask(__name__)
    # The UI is plain static files that change while developing: do not let the browser cache them.
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    app.source = source

    def json_body():
        """The request's JSON object, or an empty dict. Raises ValueError if the body is not an object."""
        data = request.get_json(silent=True)
        if data is None:
            return {}
        if not isinstance(data, dict):
            raise ValueError("expected a JSON object")
        return data

    def ok(**extra):
        return jsonify({"status": "success", **extra, "state": source.state()})

    @app.errorhandler(ValueError)
    def bad_request(error):
        """Invalid input from the network is a 400, never a 500. NotAvailable (the boat cannot do that) is a 409."""
        return jsonify({"status": "error", "message": str(error)}), getattr(error, "http_status", 400)

    @app.route('/')
    def index():
        """Serve the main application page."""
        return render_template('index.html', source=source.kind, source_label=source.label)

    @app.route('/api/state')
    @app.route('/api/boat-location')  # kept as an alias for the old name
    def state():
        """The boat's telemetry, link health, mode and course. Polled by the UI at 10 Hz."""
        return jsonify(source.state())

    @app.route('/api/control', methods=['POST'])
    def control():
        """Boat controls. Body: {command, value} (rudder -100..100, sails 0..100, throttle 0..100,
        emergency_stop, set_environment) and/or {mode: manual|auto, running, auto_trim, time_scale}.
        With the real boat only rudder, sails, throttle, emergency_stop and running exist; the rest is a 409."""
        data = request.get_json(silent=True)
        if not isinstance(data, dict) or not data:
            return jsonify({"status": "error", "message": "No JSON data provided"}), 400
        source.control(data)
        return ok()

    @app.route('/api/course', methods=['POST'])
    def course_set():
        """Replace the course. Body: {marks: [{lat, lng}, ...], loop?, active?}."""
        data = json_body()
        if 'marks' not in data:
            raise ValueError("marks is required")
        source.set_course(data['marks'], data.get('loop'), data.get('active', 0))
        return ok()

    @app.route('/api/course', methods=['DELETE'])
    def course_clear():
        """Remove every mark (and stop the autopilot, or stop sending the course to the boat)."""
        source.clear_course()
        return ok()

    @app.route('/api/course/demo', methods=['POST'])
    def course_demo():
        """Simulator only. Replace the course with the demo triangle, laid out from the boat and rotated to the wind."""
        data = json_body()
        source.demo_course(data.get('scale'))
        return ok()

    @app.route('/api/reset', methods=['POST'])
    def reset():
        """Simulator only. Put the boat back at the start (or {lat, lng, heading?}) at rest, with neutral controls."""
        data = json_body()
        source.reset(data.get('lat'), data.get('lng'), data.get('heading'))
        return ok()

    return app


def main(argv=None):
    """Run the app: `python src/main/python/app/app.py --port 5000`."""
    parser = argparse.ArgumentParser(description='Run the Corto web app: the boat over LoRa, or the simulator')
    parser.add_argument('--source', choices=('auto', 'boat', 'sim'), default='auto',
                        help='boat: the real boat over the LoRa radio; sim: the simulator, a test bench; '
                             'auto: the boat if this machine has the radio libraries and the radio opens, '
                             'else the simulator (default: auto)')
    parser.add_argument('--radio', choices=('lora', 'loopback', 'silent'), default=None,
                        help='boat source only. lora: the real radio; loopback: a simulated boat behind a fake '
                             'radio, for development; silent: never answers, to see the no-link states '
                             '(default: lora)')
    parser.add_argument('--poll-interval', type=float, default=2.0, metavar='SECONDS',
                        help='how often the boat is asked for telemetry (default: 2.0, minimum 1.0)')
    parser.add_argument('--host', default='127.0.0.1', help='Interface to bind (default: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=5000, help='Port to run the app on (default: 5000)')
    args = parser.parse_args(argv)
    if args.poll_interval < 1.0:
        parser.error('--poll-interval must be at least 1.0 seconds')

    try:
        source = build_source(args.source, args.radio, args.poll_interval)
    except SourceUnavailable as error:
        parser.error(str(error))

    if source.note:
        print(source.note)
    print(f"Serving {source.label} on http://{args.host}:{args.port}")
    if source.kind == 'boat' and args.host not in LOCAL_HOSTS:
        print("Warning: the app has no login. Anyone who can reach this address can drive the boat; "
              "only bind it to a network you trust.")

    # use_reloader=False: the reloader would start a second process (and a second simulator or radio link)
    try:
        create_app(source).run(host=args.host, port=args.port, debug=False, use_reloader=False, threaded=True)
    finally:
        source.close()


if __name__ == '__main__':
    main()
