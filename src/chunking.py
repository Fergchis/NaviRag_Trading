"""Simple and traceable text chunking for NaviRag Trading."""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from src.config import DATA_PROCESSED_DIR

DOCUMENTS_FILE = DATA_PROCESSED_DIR / "documents.json"
CHUNKS_OUTPUT_FILE = DATA_PROCESSED_DIR / "chunks.json"
MAX_CHUNK_CHARACTERS = 1200


def load_processed_documents(input_file: Path = DOCUMENTS_FILE) -> list[dict]:
    """Load pages extracted by the ingestion step."""
    if not input_file.exists():
        raise FileNotFoundError(
            f"No existe {input_file}. Ejecuta primero: python -m src.ingest"
        )

    payload = json.loads(input_file.read_text(encoding="utf-8"))
    return payload.get("documents", [])


def split_text_blocks(text: str) -> list[str]:
    """Split page text into readable blocks."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return []

    blocks = re.split(r"\n\s*\n+", normalized)
    return [block.strip() for block in blocks if block.strip()]


def split_long_block(block: str, max_characters: int = MAX_CHUNK_CHARACTERS) -> list[str]:
    """Split a long block by words without exceeding the target size too much."""
    if len(block) <= max_characters:
        return [block]

    chunks = []
    current_words = []
    current_length = 0

    for word in block.split():
        extra_length = len(word) + (1 if current_words else 0)
        if current_words and current_length + extra_length > max_characters:
            chunks.append(" ".join(current_words))
            current_words = [word]
            current_length = len(word)
        else:
            current_words.append(word)
            current_length += extra_length

    if current_words:
        chunks.append(" ".join(current_words))

    return chunks


def chunk_documents(documents: list[dict]) -> list[dict]:
    """Create traceable chunks from page-level documents."""
    chunks = []
    global_chunk_index = 1

    for page in documents:
        text = page.get("text", "")
        page_blocks = split_text_blocks(text)
        page_chunk_index = 1

        for block in page_blocks:
            for chunk_text in split_long_block(block):
                clean_text = chunk_text.strip()
                if not clean_text:
                    continue

                chunks.append(
                    {
                        "chunk_id": f"chunk_{global_chunk_index:06d}",
                        "file": page.get("file"),
                        "page": page.get("page"),
                        "page_chunk_index": page_chunk_index,
                        "text": clean_text,
                        "character_count": len(clean_text),
                    }
                )
                global_chunk_index += 1
                page_chunk_index += 1

    return chunks


def save_chunks(chunks: list[dict], output_file: Path = CHUNKS_OUTPUT_FILE) -> None:
    """Save chunks to a processed JSON file."""
    output_file.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "system": "NaviRag Trading",
        "description": "Chunks trazables generados desde paginas extraidas.",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_file": str(DOCUMENTS_FILE),
        "total_chunks": len(chunks),
        "chunks": chunks,
    }
    output_file.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    """Run chunking from the command line."""
    documents = load_processed_documents()
    chunks = chunk_documents(documents)
    save_chunks(chunks)
    print(f"Chunking completado. Chunks generados: {len(chunks)}")
    print(f"Salida: {CHUNKS_OUTPUT_FILE}")


if __name__ == "__main__":
    main()
