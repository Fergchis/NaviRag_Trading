from src.agent.memory import AgentMemory
from src.generate.generate import RAGGenerator
from src.retrieval.retrieval import Retriever
from src.utils.safety import is_forbidden_question


class AgentTools:
    def __init__(
        self,
        memory: AgentMemory | None = None,
        retriever: Retriever | None = None,
        generator: RAGGenerator | None = None,
    ):
        self.memory = memory or AgentMemory()
        self.retriever = retriever
        self.generator = generator
        self.tools = self._build_tools()

    def get(self, name: str):
        return self.tools[name]

    def _build_tools(self) -> dict:
        Tool = self._get_langchain_tool_class()
        return {
            "load_memory_tool": Tool(
                name="load_memory_tool",
                func=self.load_memory,
                description=(
                    "Carga memoria de largo plazo para una sesion. "
                    "Argumentos: {'session_id': str}."
                ),
            ),
            "safety_check_tool": Tool(
                name="safety_check_tool",
                func=self.safety_check,
                description=(
                    "Detecta preguntas de recomendacion financiera o senales de trading. "
                    "Argumentos: {'query': str}."
                ),
            ),
            "retrieve_context_tool": Tool(
                name="retrieve_context_tool",
                func=self.retrieve_context,
                description=(
                    "Recupera chunks semanticos desde MongoDB Vector Search. "
                    "Argumentos: {'query': str, 'top_k': int}."
                ),
            ),
            "write_answer_tool": Tool(
                name="write_answer_tool",
                func=self.write_answer,
                description=(
                    "Genera una respuesta educativa usando chunks ya recuperados. "
                    "Argumentos: {'query': str, 'history': list, 'chunks': list}."
                ),
            ),
            "save_memory_tool": Tool(
                name="save_memory_tool",
                func=self.save_memory,
                description=(
                    "Guarda datos minimos de continuidad de la sesion. "
                    "Argumentos: {'session_id': str, 'query': str, 'route': str}."
                ),
            ),
        }

    def _get_langchain_tool_class(self):
        try:
            from langchain_core.tools import Tool
        except ImportError as exc:
            raise RuntimeError(
                "La dependencia 'langchain' debe instalarse desde requirements.txt "
                "para construir las tools del agente."
            ) from exc

        return Tool

    def load_memory(self, payload: dict) -> dict:
        session_id = payload["session_id"]
        return self.memory.load_long_term(session_id)

    def safety_check(self, payload: dict) -> dict:
        blocked = is_forbidden_question(payload["query"])
        return {
            "blocked": blocked,
            "reason": (
                "La pregunta solicita recomendacion financiera o senal de trading."
                if blocked
                else "La pregunta puede responderse con enfoque educativo."
            ),
        }

    def retrieve_context(self, payload: dict) -> list[dict]:
        return self._get_retriever().retrieve(
            query=payload["query"],
            top_k=payload.get("top_k", 5),
        )

    def write_answer(self, payload: dict) -> dict:
        return self._get_generator().generate_from_context(
            query=payload["query"],
            history=payload.get("history", []),
            chunks=payload.get("chunks", []),
        )

    def save_memory(self, payload: dict) -> dict:
        return self.memory.save_interaction(
            session_id=payload["session_id"],
            query=payload["query"],
            route=payload["route"],
        )

    def _get_retriever(self) -> Retriever:
        if self.retriever is None:
            self.retriever = Retriever()
        return self.retriever

    def _get_generator(self) -> RAGGenerator:
        if self.generator is None:
            self.generator = RAGGenerator()
        return self.generator
