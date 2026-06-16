from __future__ import annotations

import io
import threading
from contextlib import redirect_stdout

from flask import Flask, jsonify, request

try:
    from .agent_runner import run_agent
    from .configuration import parse_config, validate_config
    from .flow import FLOW_STEPS
    from .summary import summarize_state
except ImportError:
    from agent_runner import run_agent
    from configuration import parse_config, validate_config
    from flow import FLOW_STEPS
    from summary import summarize_state


app = Flask(__name__)
_run_lock = threading.Lock()


def _cors_response(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
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

    if _run_lock.locked():
        return jsonify({"ok": False, "error": "Ya hay una ejecucion en curso."}), 409

    overrides = _request_overrides()
    validation_error = validate_config(overrides)
    if validation_error:
        return jsonify({"ok": False, "error": validation_error}), 400

    logs = io.StringIO()
    with _run_lock:
        try:
            with redirect_stdout(logs):
                final_state, exit_code = run_agent(overrides)
        except Exception as exc:
            return _agent_error_response(exc, logs)

    return _agent_success_response(final_state, exit_code, logs)


def _request_overrides() -> dict:
    payload = request.get_json(silent=True) or {}
    return parse_config(payload.get("config", payload))


def _agent_error_response(exc: Exception, logs: io.StringIO):
    return jsonify(
        {
            "ok": False,
            "error": str(exc),
            "logs": logs.getvalue(),
            "summary": None,
        }
    ), 500


def _agent_success_response(final_state: dict, exit_code: int, logs: io.StringIO):
    return jsonify(
        {
            "ok": exit_code == 0,
            "exitCode": exit_code,
            "logs": logs.getvalue(),
            "summary": summarize_state(final_state),
        }
    ), 200 if exit_code == 0 else 422


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
