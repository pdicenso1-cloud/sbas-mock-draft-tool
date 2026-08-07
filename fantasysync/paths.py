"""Project paths shared across FantasySync modules."""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
STATE_FILE = DATA_DIR / "saved_state.json"
