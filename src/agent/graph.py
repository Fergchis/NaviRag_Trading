from typing import TypedDict

from src.agent.memory import AgentMemory
from src.agent.tools import AgentTools


BLOCKED_ANSWER = (
    "No puedo entregar recomendaciones financieras, senales de compra o venta "
    "ni instrucciones de inversion. Puedo explicar conceptos de trading con "
    "fines educativos."
)

INSUFFICIENT_CONTEXT_ANSWER = (
    "No encontre contexto suficiente en los documentos cargados para responder "
    "esta pregunta de forma confiable."
)

RETRIEVAL_ERROR_ANSWER = (
    "Error de recuperacion de contexto. Intenta nuevamente mas tarde o revisa "
    "la conexion con la base de documentos."
)

GENERATION_ERROR_ANSWER = (
    "Error en la generacion de respuesta del LLM. El servicio de lenguaje no "
    "esta disponible o alcanzo su limite temporal. Intenta nuevamente mas tarde."
)


class TradingAgentState(TypedDict, total=False):
    query: str
    session_id: str
    top_k: int
    history: list[dict]
    short_term: list[dict]
    long_term: dict
    safety: dict
    search_query: str
    chunks: list[dict]
    answer: str
    sources: list[dict]
    route: str
    decision_reason: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    error: str
    plan: list[dict]
    saved_memory: dict


class TradingAgentGraph:
    def __init__(
        self,
        tools: AgentTools | None = None,
        memory: AgentMemory | None = None,
    ):
        self.memory = memory or AgentMemory()
        self.tools = tools or AgentTools(memory=self.memory)
        self.app = None

    def run(self, query: str, history: list, session_id: str, top_k: int = 5) -> dict:
        initial_state: TradingAgentState = {
            "query": query,
            "session_id": session_id,
            "history": history,
            "top_k": top_k,
            "sources": [],
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "plan": [],
        }
        final_state = self._get_app().invoke(
            initial_state,
            config={"configurable": {"thread_id": session_id}},
        )
        return self._format_result(final_state)

    def _build_graph(self):
        StateGraph, END, MemorySaver = self._get_langgraph_classes()
        graph = StateGraph(TradingAgentState)

        graph.add_node("load_memory", self.load_memory_node)
        graph.add_node("check_financial_safety", self.check_financial_safety_node)
        graph.add_node("blocked_response", self.blocked_response_node)
        graph.add_node("agent", self.agent_node)
        graph.add_node("generate_query", self.generate_query_node)
        graph.add_node("retrieve_context", self.retrieve_context_node)
        graph.add_node("generate_answer", self.generate_answer_node)
        graph.add_node("save_memory", self.save_memory_node)

        graph.set_entry_point("load_memory")
        graph.add_edge("load_memory", "check_financial_safety")
        graph.add_conditional_edges(
            "check_financial_safety",
            self.route_after_safety,
            {
                "blocked": "blocked_response",
                "agent": "agent",
            },
        )
        graph.add_edge("blocked_response", "save_memory")
        graph.add_conditional_edges(
            "agent",
            self.route_after_agent,
            {
                "generate_query": "generate_query",
            },
        )
        graph.add_edge("generate_query", "retrieve_context")
        graph.add_conditional_edges(
            "retrieve_context",
            self.route_after_retrieval,
            {
                "generate_answer": "generate_answer",
                "save_memory": "save_memory",
            },
        )
        graph.add_edge("generate_answer", "save_memory")
        graph.add_edge("save_memory", END)

        return graph.compile(checkpointer=MemorySaver())

    def _get_app(self):
        if self.app is None:
            self.app = self._build_graph()
        return self.app

    def _get_langgraph_classes(self):
        try:
            from langgraph.checkpoint.memory import MemorySaver
            from langgraph.graph import END, StateGraph
        except ImportError as exc:
            raise RuntimeError(
                "La dependencia 'langgraph' debe instalarse desde requirements.txt "
                "para ejecutar el grafo del agente Ev2."
            ) from exc

        return StateGraph, END, MemorySaver

    def load_memory_node(self, state: TradingAgentState) -> TradingAgentState:
        session_id = state["session_id"]
        short_term = self.memory.get_short_term(state.get("history", []))
        long_term = self.tools.get("load_memory_tool").func({"session_id": session_id})
        return {
            "short_term": short_term,
            "long_term": long_term,
            "plan": self._append_plan(
                state,
                "load_memory",
                "load_memory_tool",
                "completed",
                "Memoria cargada para la sesion.",
            ),
        }

    def check_financial_safety_node(self, state: TradingAgentState) -> TradingAgentState:
        safety = self.tools.get("safety_check_tool").func({"query": state["query"]})
        return {
            "safety": safety,
            "plan": self._append_plan(
                state,
                "check_financial_safety",
                "safety_check_tool",
                "completed",
                safety["reason"],
            ),
        }

    def blocked_response_node(self, state: TradingAgentState) -> TradingAgentState:
        return {
            "answer": BLOCKED_ANSWER,
            "route": "blocked",
            "decision_reason": state.get("safety", {}).get(
                "reason",
                "La consulta fue bloqueada por seguridad financiera.",
            ),
            "plan": self._append_plan(
                state,
                "blocked_response",
                "safety_check_tool",
                "completed",
                "Respuesta segura generada sin consultar el RAG.",
            ),
        }

    def agent_node(self, state: TradingAgentState) -> TradingAgentState:
        reason = (
            "Consulta permitida: el agente prepara una busqueda semantica "
            "antes de responder."
        )
        return {
            "decision_reason": reason,
            "plan": self._append_plan(
                state,
                "agent",
                "planner",
                "completed",
                reason,
            ),
        }

    def generate_query_node(self, state: TradingAgentState) -> TradingAgentState:
        search_query = state["query"].strip()
        return {
            "search_query": search_query,
            "plan": self._append_plan(
                state,
                "generate_query",
                "planner",
                "completed",
                "Query preparada para recuperacion semantica.",
            ),
        }

    def retrieve_context_node(self, state: TradingAgentState) -> TradingAgentState:
        try:
            chunks = self.tools.get("retrieve_context_tool").func({
                "query": state.get("search_query") or state["query"],
                "top_k": state.get("top_k", 5),
            })
        except Exception:
            return {
                "answer": RETRIEVAL_ERROR_ANSWER,
                "route": "retrieval_error",
                "decision_reason": "Fallo la recuperacion de contexto desde un servicio externo.",
                "error": "Error de recuperacion de contexto.",
                "plan": self._append_plan(
                    state,
                    "retrieve_context",
                    "retrieve_context_tool",
                    "failed",
                    "Error de recuperacion de contexto.",
                ),
            }

        return {
            "chunks": chunks,
            "plan": self._append_plan(
                state,
                "retrieve_context",
                "retrieve_context_tool",
                "completed",
                f"Chunks recuperados: {len(chunks)}.",
            ),
        }

    def generate_answer_node(self, state: TradingAgentState) -> TradingAgentState:
        chunks = state.get("chunks", [])
        if not self._has_useful_context(chunks):
            return {
                "answer": INSUFFICIENT_CONTEXT_ANSWER,
                "sources": [],
                "route": "insufficient_context",
                "decision_reason": "No se recuperaron chunks con texto util.",
                "plan": self._append_plan(
                    state,
                    "generate_answer",
                    "write_answer_tool",
                    "skipped",
                    "No hay contexto util para generar respuesta.",
                ),
            }

        try:
            response = self.tools.get("write_answer_tool").func({
                "query": state["query"],
                "history": state.get("short_term", []),
                "chunks": chunks,
            })
        except Exception:
            return {
                "answer": GENERATION_ERROR_ANSWER,
                "sources": [],
                "route": "generation_error",
                "decision_reason": "Fallo la generacion de respuesta desde un servicio externo.",
                "error": "Error en la generacion de respuesta del LLM.",
                "plan": self._append_plan(
                    state,
                    "generate_answer",
                    "write_answer_tool",
                    "failed",
                    "Error en la generacion de respuesta del LLM.",
                ),
            }

        return {
            "answer": response["answer"],
            "sources": response.get("sources", []),
            "route": "rag_answer",
            "decision_reason": "La consulta paso seguridad y tenia contexto recuperado.",
            "prompt_tokens": response.get("prompt_tokens", 0),
            "completion_tokens": response.get("completion_tokens", 0),
            "total_tokens": response.get("total_tokens", 0),
            "plan": self._append_plan(
                state,
                "generate_answer",
                "write_answer_tool",
                "completed",
                "Respuesta generada desde contexto recuperado.",
            ),
        }

    def save_memory_node(self, state: TradingAgentState) -> TradingAgentState:
        route = state.get("route", "unknown")
        saved = self.tools.get("save_memory_tool").func({
            "session_id": state["session_id"],
            "query": state["query"],
            "route": route,
        })
        return {
            "saved_memory": saved,
            "plan": self._append_plan(
                state,
                "save_memory",
                "save_memory_tool",
                "completed",
                "Memoria de sesion actualizada.",
            ),
        }

    def route_after_safety(self, state: TradingAgentState) -> str:
        if state.get("safety", {}).get("blocked"):
            return "blocked"
        return "agent"

    def route_after_agent(self, state: TradingAgentState) -> str:
        return "generate_query"

    def route_after_retrieval(self, state: TradingAgentState) -> str:
        if state.get("route") == "retrieval_error":
            return "save_memory"
        return "generate_answer"

    def _format_result(self, state: TradingAgentState) -> dict:
        long_term = state.get("long_term", {})
        saved = state.get("saved_memory", {})
        short_term = state.get("short_term", [])
        return {
            "answer": state.get("answer", ""),
            "sources": state.get("sources", []),
            "plan": state.get("plan", []),
            "decision": {
                "route": state.get("route", "unknown"),
                "reason": state.get("decision_reason", ""),
            },
            "memory": {
                "session_id": state.get("session_id", ""),
                "short_term_messages": len(short_term),
                "long_term_loaded": int(long_term.get("interaction_count", 0)) > 0,
                "long_term_saved": bool(saved),
            },
            "prompt_tokens": state.get("prompt_tokens", 0),
            "completion_tokens": state.get("completion_tokens", 0),
            "total_tokens": state.get("total_tokens", 0),
        }

    def _append_plan(
        self,
        state: TradingAgentState,
        step: str,
        tool: str,
        status: str,
        reason: str,
    ) -> list[dict]:
        return state.get("plan", []) + [{
            "step": step,
            "tool": tool,
            "status": status,
            "reason": reason,
        }]

    def _has_useful_context(self, chunks: list[dict]) -> bool:
        return any(chunk.get("text", "").strip() for chunk in chunks)
