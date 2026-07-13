"""Configuration defaults for the support trend detection demo."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_PATH = ROOT / "data" / "sample_tickets.csv"
DEFAULT_CURRENT_DAYS = 14
DEFAULT_PREVIOUS_DAYS = 14
DEFAULT_MAX_TRENDS = 8
RANDOM_STATE = 42
