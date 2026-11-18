import sys
from pathlib import Path

# Permite importar módulos del agente (config, src) desde tests/
AGENT_ROOT = Path(__file__).resolve().parent.parent
if str(AGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(AGENT_ROOT))

import pytest


@pytest.fixture(autouse=True)
def _no_real_llm(monkeypatch):
    """Ningún test debe llamar a un LLM real; los que lo necesitan lo simulan."""
    from config import config

    def _unavailable():
        raise RuntimeError("LLM real deshabilitado en tests")

    monkeypatch.setattr(config, "get_llm", _unavailable)


@pytest.fixture(autouse=True)
def _no_real_canvas(monkeypatch):
    """Ningún test debe llamar a la API real de Canvas; los que la usan la simulan."""
    from src.tools import canvas_api

    def _blocked(method, endpoint, *args, **kwargs):
        raise RuntimeError(f"Llamada real a Canvas bloqueada en tests: {method} {endpoint}")

    monkeypatch.setattr(canvas_api, "_canvas_request", _blocked)
