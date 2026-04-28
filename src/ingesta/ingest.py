import json
from pathlib import Path

from markitdown import MarkItDown

from src.config import DATA_PROCESSED_DIR, DATA_RAW_DIR

DOCUMENTS_FILE = DATA_PROCESSED_DIR / "documents.json"


class PDFIngester:
    def __init__(self):
        self.converter = MarkItDown()

    def scan_pdfs(self, directory: str) -> list[Path]:
        return sorted(Path(directory).glob("*.pdf"))

    def _convert_to_text(self, file_path: Path) -> str:
        result = self.converter.convert(str(file_path))
        return result.text_content

    def ingest_directory(self, directory: str = str(DATA_RAW_DIR)) -> list[dict]:
        pdf_files = self.scan_pdfs(directory)
        print(f"Found {len(pdf_files)} PDF(s) in '{directory}'")

        documents = []
        for file_path in pdf_files:
            print(f"Processing: {file_path.name}")
            text = self._convert_to_text(file_path)
            documents.append({
                "file": file_path.name,
                "path": str(file_path),
                "page": None,
                "section": "document",
                "text": text,
            })

        return documents


def save_documents(documents: list[dict]):
    DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "documents": documents,
        "total_documents": len(documents),
    }
    DOCUMENTS_FILE.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main():
    ingester = PDFIngester()
    documents = ingester.ingest_directory()
    save_documents(documents)
    print(f"Ingestion complete. Documents: {len(documents)}")
    print(f"Output: {DOCUMENTS_FILE}")


if __name__ == "__main__":
    main()
