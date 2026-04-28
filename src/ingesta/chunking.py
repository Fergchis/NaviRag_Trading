import json

from src.config import DATA_PROCESSED_DIR

DOCUMENTS_FILE = DATA_PROCESSED_DIR / "documents.json"
CHUNKS_FILE = DATA_PROCESSED_DIR / "chunks.json"


def _split_text(text: str, chunk_size: int = 2200, overlap: int = 200) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks


def load_documents() -> list[dict]:
    payload = json.loads(DOCUMENTS_FILE.read_text(encoding="utf-8"))
    return payload.get("documents", [])


def chunk_documents(documents: list[dict]) -> list[dict]:
    chunks = []
    chunk_index = 1

    for document in documents:
        text_chunks = _split_text(document.get("text", ""))
        for page_chunk_index, text in enumerate(text_chunks, start=1):
            chunks.append({
                "chunk_id": f"chunk_{chunk_index:06d}",
                "text": text,
                "file": document.get("file"),
                "path": document.get("path"),
                "page": document.get("page"),
                "section": document.get("section"),
                "page_chunk_index": page_chunk_index,
                "character_count": len(text),
            })
            chunk_index += 1

    return chunks


def save_chunks(chunks: list[dict]):
    DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "chunks": chunks,
        "total_chunks": len(chunks),
    }
    CHUNKS_FILE.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main():
    documents = load_documents()
    chunks = chunk_documents(documents)
    save_chunks(chunks)
    print(f"Chunking complete. Chunks: {len(chunks)}")
    print(f"Output: {CHUNKS_FILE}")


if __name__ == "__main__":
    main()
