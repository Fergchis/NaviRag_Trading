"""Simple PDF ingestion for NaviRag Trading.

This module only extracts text and basic metadata from PDFs placed in
``data/raw``. It does not create embeddings, vector stores, retrieval results
or LLM answers.
"""

import json
import argparse
from datetime import datetime, timezone
from importlib.util import find_spec
from pathlib import Path

from src.config import DATA_PROCESSED_DIR, DATA_RAW_DIR

PROCESSED_OUTPUT_FILE = DATA_PROCESSED_DIR / "documents.json"


def list_pdf_files(raw_dir: Path) -> list[Path]:
    """Return PDF files available for ingestion."""
    return sorted(raw_dir.glob("*.pdf"))


def _require_markitdown():
    """Import MarkItDown only when ingestion is executed."""
    if find_spec("markitdown") is None:
        raise RuntimeError(
            "Falta la dependencia 'markitdown[pdf]'. Instala dependencias con "
            "'pip install -r requirements.txt'."
        )

    from markitdown import MarkItDown

    return MarkItDown


def extract_pdf_pages(pdf_path: Path) -> list[dict]:
    """Extract document text and metadata from one PDF file."""
    MarkItDown = _require_markitdown()
    result = MarkItDown().convert(str(pdf_path))
    clean_text = (result.text_content or "").strip()

    return [
        {
            "file": pdf_path.name,
            "path": str(pdf_path),
            "page": None,
            "section": "document",
            "text": clean_text,
            "character_count": len(clean_text),
        }
    ]


def ingest_documents(
    raw_dir: Path = DATA_RAW_DIR,
    output_file: Path = PROCESSED_OUTPUT_FILE,
) -> list[dict]:
    """Extract text from all PDFs and save a processed JSON file."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    pdf_files = list_pdf_files(raw_dir)
    documents = []

    for pdf_file in pdf_files:
        documents.extend(extract_pdf_pages(pdf_file))

    payload = {
        "system": "NaviRag Trading",
        "description": "Texto extraido desde PDFs locales para uso educativo.",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_dir": str(raw_dir),
        "total_pdf_files": len(pdf_files),
        "total_documents": len(documents),
        "documents": documents,
    }

    output_file.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return documents


def main() -> None:
    """Run ingestion from the command line."""
    parser = argparse.ArgumentParser(description="Ingesta PDFs locales.")
    parser.parse_args()

    documents = ingest_documents()
    print(f"Ingesta completada. Documentos procesados: {len(documents)}")
    print(f"Salida: {PROCESSED_OUTPUT_FILE}")


if __name__ == "__main__":
    main()
