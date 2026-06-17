from __future__ import annotations

import io
import json
import threading
import uuid
from contextlib import redirect_stdout
from dataclasses import dataclass, field
from typing import Any

try:
    from .agent_runner import run_agent
    from .summary import summarize_state
except ImportError:
    from agent_runner import run_agent
    from summary import summarize_state


@dataclass
class AgentRun:
    id: str
    events: list[dict[str, Any]] = field(default_factory=list)
    condition: threading.Condition = field(default_factory=threading.Condition)
    completed: bool = False

    def emit(self, event_type: str, data: dict[str, Any]) -> None:
        event = {"type": event_type, **data}
        with self.condition:
            self.events.append(event)
            self.condition.notify_all()


class StreamingStdout(io.TextIOBase):
    def __init__(self, run: AgentRun):
        self.run = run
        self.logs: list[str] = []

    def writable(self) -> bool:
        return True

    def write(self, value: str) -> int:
        if value:
            self.logs.append(value)
            self.run.emit("log", {"message": value})
        return len(value)

    def flush(self) -> None:
        return None


_runs: dict[str, AgentRun] = {}
_run_lock = threading.Lock()


def start_run(overrides: dict[str, Any]) -> AgentRun | None:
    if _run_lock.locked():
        return None

    run = AgentRun(id=uuid.uuid4().hex)
    _runs[run.id] = run

    thread = threading.Thread(target=_execute_run, args=(run, overrides), daemon=True)
    thread.start()
    return run


def get_run(run_id: str) -> AgentRun | None:
    return _runs.get(run_id)


def run_blocking(overrides: dict[str, Any]) -> tuple[dict[str, Any], int] | None:
    if _run_lock.locked():
        return None

    logs = io.StringIO()
    with _run_lock:
        try:
            with redirect_stdout(logs):
                final_state, exit_code = run_agent(overrides)
        except Exception as exc:
            return {
                "ok": False,
                "error": str(exc),
                "logs": logs.getvalue(),
                "summary": None,
            }, 500

    return {
        "ok": exit_code == 0,
        "exitCode": exit_code,
        "logs": logs.getvalue(),
        "summary": summarize_state(final_state),
    }, 200 if exit_code == 0 else 422


def event_stream(run: AgentRun):
    cursor = 0
    while True:
        heartbeat = False
        with run.condition:
            while cursor >= len(run.events) and not run.completed:
                run.condition.wait(timeout=15)
                if cursor >= len(run.events) and not run.completed:
                    heartbeat = True
                    break

            if heartbeat:
                event = None
            elif cursor < len(run.events):
                event = run.events[cursor]
                cursor += 1
            elif run.completed:
                break
            else:
                continue

        if heartbeat:
            yield _sse("heartbeat", {"ok": True})
            continue

        yield _sse(event["type"], event)
        if event["type"] in {"done", "error"}:
            break


def _execute_run(run: AgentRun, overrides: dict[str, Any]) -> None:
    stdout = StreamingStdout(run)
    with _run_lock:
        try:
            run.emit("started", {"message": "Ejecucion iniciada."})
            with redirect_stdout(stdout):
                final_state, exit_code = run_agent(overrides)
            run.emit(
                "done",
                {
                    "ok": exit_code == 0,
                    "exitCode": exit_code,
                    "logs": "".join(stdout.logs),
                    "summary": summarize_state(final_state),
                },
            )
        except Exception as exc:
            run.emit(
                "error",
                {
                    "ok": False,
                    "error": str(exc),
                    "logs": "".join(stdout.logs),
                    "summary": None,
                },
            )
        finally:
            with run.condition:
                run.completed = True
                run.condition.notify_all()


def _sse(event_type: str, data: dict[str, Any]) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event_type}\ndata: {payload}\n\n"
