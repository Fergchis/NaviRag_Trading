"""PDF ingestion placeholders.

Real PDF extraction will be implemented in a later stage.
"""

from pathlib import Path


def list_pdf_files(raw_dir: Path) -> list[Path]:
    """Return PDF files available for future ingestion."""
    return sorted(raw_dir.glob("*.pdf"))


def ingest_documents() -> list[dict]:
    """Placeholder for PDF text extraction with metadata."""
    return []
