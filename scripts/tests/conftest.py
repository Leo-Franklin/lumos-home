import sys
from pathlib import Path

# Make scripts/ importable so tests can `import check_api_contract`
SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))
