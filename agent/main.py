import sys
from typing import Any

from src.pipeline import run_agent as _run_agent


def run_agent(overrides: dict[str, Any] | None = None) -> tuple[dict, int]:
    return _run_agent(overrides)


def main() -> None:
    _, exit_code = run_agent()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
