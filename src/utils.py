"""Shared utility placeholders."""


def format_source_label(source: dict) -> str:
    """Format a future source label with document and page metadata."""
    document = source.get("document", "documento desconocido")
    page = source.get("page")
    if page is None:
        return document
    return f"{document}, página {page}"
