from __future__ import annotations

from flask import Flask, Response, jsonify, request

try:
    from .configuration import parse_config, validate_config
    from .flow import FLOW_STEPS
    from .run_manager import event_stream, get_run, run_blocking, start_run
except ImportError:
    from configuration import parse_config, validate_config
    from flow import FLOW_STEPS
    from run_manager import event_stream, get_run, run_blocking, start_run


app = Flask(__name__)


def _cors_response(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    response.headers["Cache-Control"] = "no-cache"
    return response


app.after_request(_cors_response)


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"ok": True, "service": "canvas-lms-agent-api"})


@app.route("/api/flow", methods=["GET"])
def flow():
    return jsonify({"steps": FLOW_STEPS})


@app.route("/api/run-agent", methods=["POST", "OPTIONS"])
def run_agent_endpoint():
    if request.method == "OPTIONS":
        return ("", 204)

    overrides = _request_overrides()
    validation_error = validate_config(overrides)
    if validation_error:
        return jsonify({"ok": False, "error": validation_error}), 400

    result = run_blocking(overrides)
    if result is None:
        return jsonify({"ok": False, "error": "Ya hay una ejecucion en curso."}), 409

    payload, status_code = result
    return jsonify(payload), status_code


@app.route("/api/runs", methods=["POST", "OPTIONS"])
def create_run_endpoint():
    if request.method == "OPTIONS":
        return ("", 204)

    overrides = _request_overrides()
    validation_error = validate_config(overrides)
    if validation_error:
        return jsonify({"ok": False, "error": validation_error}), 400

    run = start_run(overrides)
    if run is None:
        return jsonify({"ok": False, "error": "Ya hay una ejecucion en curso."}), 409

    return jsonify({"ok": True, "runId": run.id}), 202


@app.route("/api/runs/<run_id>/events", methods=["GET"])
def run_events_endpoint(run_id: str):
    run = get_run(run_id)
    if run is None:
        return jsonify({"ok": False, "error": "Ejecucion no encontrada."}), 404

    return Response(event_stream(run), mimetype="text/event-stream")


def _request_overrides() -> dict:
    payload = request.get_json(silent=True) or {}
    return parse_config(payload.get("config", payload))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
