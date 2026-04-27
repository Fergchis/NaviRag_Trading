"""Simple and traceable text chunking for NaviRag Trading."""

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from src.config import DATA_PROCESSED_DIR

DOCUMENTS_FILE = DATA_PROCESSED_DIR / "documents.json"
CHUNKS_OUTPUT_FILE = DATA_PROCESSED_DIR / "chunks.json"
MIN_CHUNK_CHARACTERS = 500
TARGET_CHUNK_CHARACTERS = 900
MAX_CHUNK_CHARACTERS = 1200


def load_processed_documents(input_file: Path = DOCUMENTS_FILE) -> list[dict]:
    """Load documents extracted by the ingestion step."""
    if not input_file.exists():
        raise FileNotFoundError(
            f"No existe {input_file}. Ejecuta primero: python -m src.ingesta.ingest"
        )

    payload = json.loads(input_file.read_text(encoding="utf-8"))
    return payload.get("documents", [])


def split_text_blocks(text: str) -> list[str]:
    """Split document text into readable blocks."""
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


def is_markdown_fence_only(text: str) -> bool:
    """Return whether a block only opens or closes a Markdown code fence."""
    clean_text = text.strip().lower()
    return clean_text == "```" or clean_text == "```python"


def merge_text_blocks(
    blocks: list[str],
    min_characters: int = MIN_CHUNK_CHARACTERS,
    target_characters: int = TARGET_CHUNK_CHARACTERS,
    max_characters: int = MAX_CHUNK_CHARACTERS,
) -> list[str]:
    """Merge small MarkItDown blocks into semantically larger chunks."""
    chunks = []
    current_blocks = []
    current_length = 0

    def flush_current() -> None:
        nonlocal current_blocks, current_length
        if not current_blocks:
            return

        chunk_text = "\n\n".join(current_blocks).strip()
        if chunk_text and not is_markdown_fence_only(chunk_text):
            chunks.append(chunk_text)

        current_blocks = []
        current_length = 0

    for block in blocks:
        for piece in split_long_block(block, max_characters=max_characters):
            clean_piece = piece.strip()
            if not clean_piece:
                continue

            if not current_blocks:
                current_blocks = [clean_piece]
                current_length = len(clean_piece)
                continue

            projected_length = current_length + 2 + len(clean_piece)
            should_merge = projected_length <= target_characters or (
                current_length < min_characters and projected_length <= max_characters
            )

            if should_merge:
                current_blocks.append(clean_piece)
                current_length = projected_length
            else:
                flush_current()
                current_blocks = [clean_piece]
                current_length = len(clean_piece)

    flush_current()
    return chunks


def chunk_documents(documents: list[dict]) -> list[dict]:
    """Create traceable chunks from ingested documents."""
    chunks = []
    global_chunk_index = 1

    for page in documents:
        text = page.get("text", "")
        page_blocks = split_text_blocks(text)
        document_chunks = merge_text_blocks(page_blocks)
        page_chunk_index = 1

        for chunk_text in document_chunks:
            clean_text = chunk_text.strip()
            if not clean_text:
                continue

            chunks.append(
                {
                    "chunk_id": f"chunk_{global_chunk_index:06d}",
                    "file": page.get("file"),
                    "path": page.get("path"),
                    "page": page.get("page"),
                    "section": page.get("section"),
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
        "description": "Chunks trazables generados desde documentos extraidos.",
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
    parser = argparse.ArgumentParser(description="Genera chunks desde documentos locales.")
    parser.parse_args()

    documents = load_processed_documents()
    chunks = chunk_documents(documents)
    save_chunks(chunks)
    print(f"Chunking completado. Chunks generados: {len(chunks)}")
    print(f"Salida: {CHUNKS_OUTPUT_FILE}")


if __name__ == "__main__":
    main()
