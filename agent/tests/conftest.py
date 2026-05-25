import sys
from pathlib import Path

# Permite importar módulos del agente (config, src) desde tests/
AGENT_ROOT = Path(__file__).resolve().parent.parent
if str(AGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(AGENT_ROOT))
