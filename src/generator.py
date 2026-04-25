"""Answer generation placeholders."""


def generate_placeholder_answer(question: str, context: list[dict]) -> str:
    """Return a safe placeholder answer until real RAG generation exists."""
    _ = question
    if not context:
        return (
            "No hay información suficiente en los documentos cargados para "
            "responder con seguridad. Esta versión inicial aún no procesa PDFs "
            "ni recupera fragmentos reales."
        )
    return "Respuesta educativa pendiente de implementación."
