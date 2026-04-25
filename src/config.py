"""Application configuration constants."""

from pathlib import Path

APP_NAME = "NaviRag Trading"
ORGANIZATION = "Iwakura Trading Academy"

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_RAW_DIR = BASE_DIR / "data" / "raw"
DATA_PROCESSED_DIR = BASE_DIR / "data" / "processed"
VECTORSTORE_DIR = BASE_DIR / "data" / "vectorstore"
