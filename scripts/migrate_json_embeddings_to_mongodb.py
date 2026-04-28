"""Migrate local JSON embeddings into MongoDB Atlas."""

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.mongodb import MongoDBClient

DEFAULT_EMBEDDINGS_JSON_FILE = PROJECT_ROOT / "data" / "vectorstore" / "embeddings.json"


def load_json_embedding_records(input_file: Path) -> list[dict]:
    """Load embedding records from the local JSON vectorstore file."""
    if not input_file.exists():
        raise FileNotFoundError(f"No existe {input_file}.")

    payload = json.loads(input_file.read_text(encoding="utf-8"))
    return payload.get("embeddings", [])


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Migra embeddings JSON locales a MongoDB Atlas."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_EMBEDDINGS_JSON_FILE,
        help="Archivo JSON local con embeddings.",
    )
    return parser.parse_args()


def main() -> None:
    """Run the JSON-to-MongoDB migration."""
    args = parse_args()
    try:
        records = load_json_embedding_records(args.input)
        mongo = MongoDBClient()
        written = mongo.upsert_embedding_records(records)
        total = mongo.get_collection().count_documents({})
    except FileNotFoundError as error:
        print(str(error))
    except RuntimeError as error:
        print(str(error))
    except Exception as error:
        print(f"No se pudo migrar embeddings a MongoDB Atlas. Tipo: {type(error).__name__}")
    else:
        print(f"Registros leidos desde JSON: {len(records)}")
        print(f"Registros enviados a MongoDB: {written}")
        print(f"Documentos en MongoDB: {total}")


if __name__ == "__main__":
    main()
