from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from prompts.prompt import AGENT_SYSTEM_PROMPT, QUERY_REFORMULATION_PROMPT
from src.agent.memory import AgentMemory
from src.agent.tools import tools
from src.utils.llm import get_chat_model
from src.utils.safety import is_forbidden_question


BLOCKED_ANSWER = (
    "No puedo entregar recomendaciones financieras, senales de compra o venta "
    "ni instrucciones de inversion. Puedo explicar conceptos de trading con "
    "fines educativos."
)

INSUFFICIENT_CONTEXT_ANSWER = (
    "No encontre contexto suficiente en los documentos cargados para responder "
    "esta pregunta de forma confiable."
)


class TradingAgentState(TypedDict, total=False):
    messages: Annotated[list, add_messages]
    query: str
    session_id: str
    top_k: int
    history: list[dict]
    short_term: list[dict]
    long_term: dict
    safety: dict
    search_query: str
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
    def __init__(self, memory: AgentMemory | None = None):
        self.memory = memory or AgentMemory()
        self.llm = get_chat_model()
        self.agent_llm = self.llm.bind_tools(tools)
        self.query_llm = get_chat_model()
        self.tools_node = ToolNode(tools)
        self.app = self._build_graph()

    def run(self, query: str, history: list, session_id: str, top_k: int = 5) -> dict:
        initial_state: TradingAgentState = {
            "messages": [HumanMessage(content=query)],
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
        final_state = self.app.invoke(
            initial_state,
            config={"configurable": {"thread_id": session_id}},
        )
        return self._format_result(final_state)

    def _build_graph(self):
        graph = StateGraph(TradingAgentState)

        graph.add_node("load_memory", self.load_memory_node)
        graph.add_node("check_financial_safety", self.check_financial_safety_node)
        graph.add_node("blocked_response", self.blocked_response_node)
        graph.add_node("agent", self.agent_node)
        graph.add_node("generate_query", self.generate_query_node)
        graph.add_node("tools", self.tools_node)
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
            self.route_tools,
            {
                "generate_query": "generate_query",
                "save_memory": "save_memory",
            },
        )
        graph.add_edge("generate_query", "tools")
        graph.add_edge("tools", "agent")
        graph.add_edge("save_memory", END)

        return graph.compile(checkpointer=MemorySaver())

    def load_memory_node(self, state: TradingAgentState) -> TradingAgentState:
        short_term = self.memory.get_short_term(state.get("history", []))
        long_term = self.memory.load_long_term(state["session_id"])
        return {
            "short_term": short_term,
            "long_term": long_term,
            "plan": self._append_plan(
                state,
                "load_memory",
                "memory",
                "completed",
                "Memoria cargada para la sesion.",
            ),
        }

    def check_financial_safety_node(self, state: TradingAgentState) -> TradingAgentState:
        blocked = is_forbidden_question(state["query"])
        reason = (
            "La pregunta solicita recomendacion financiera o senal de trading."
            if blocked
            else "La pregunta puede responderse con enfoque educativo."
        )
        return {
            "safety": {"blocked": blocked, "reason": reason},
            "plan": self._append_plan(
                state,
                "check_financial_safety",
                "safety",
                "completed",
                reason,
            ),
        }

    def blocked_response_node(self, state: TradingAgentState) -> TradingAgentState:
        return {
            "messages": [AIMessage(content=BLOCKED_ANSWER)],
            "answer": BLOCKED_ANSWER,
            "route": "blocked",
            "decision_reason": state.get("safety", {}).get(
                "reason",
                "La consulta fue bloqueada por seguridad financiera.",
            ),
            "plan": self._append_plan(
                state,
                "blocked_response",
                "safety",
                "completed",
                "Respuesta segura generada sin consultar el RAG.",
            ),
        }

    def agent_node(self, state: TradingAgentState) -> TradingAgentState:
        system_prompt = AGENT_SYSTEM_PROMPT
        recent_questions = state.get("long_term", {}).get("recent_questions", [])
        if recent_questions:
            system_prompt += "\n\nPreguntas recientes de esta sesion:\n- " + "\n- ".join(
                recent_questions
            )

        response = self.agent_llm.invoke(
            [SystemMessage(content=system_prompt)] + state["messages"]
        )
        usage = self._usage(response)

        if response.tool_calls:
            tool_names = ", ".join(call["name"] for call in response.tool_calls)
            return {
                "messages": [response],
                **self._add_usage(state, usage),
                "decision_reason": f"El agente selecciono las tools: {tool_names}.",
                "plan": self._append_plan(
                    state,
                    "agent",
                    tool_names,
                    "completed",
                    "El LLM decidio usar tools antes de responder.",
                ),
            }

        sources, had_tool_result = self._tool_result(state)
        route = "rag_answer" if sources else "insufficient_context"
        answer = response.content or INSUFFICIENT_CONTEXT_ANSWER
        if not sources and had_tool_result:
            answer = response.content or INSUFFICIENT_CONTEXT_ANSWER

        return {
            "messages": [response],
            "answer": answer,
            "sources": sources,
            "route": route,
            "decision_reason": (
                "El agente respondio usando el contexto recuperado por rag_search."
                if sources
                else "rag_search no entrego contexto suficiente."
            ),
            **self._add_usage(state, usage),
            "plan": self._append_plan(
                state,
                "agent",
                "rag_search" if had_tool_result else "llm",
                "completed",
                "El LLM genero la respuesta final.",
            ),
        }

    def generate_query_node(self, state: TradingAgentState) -> TradingAgentState:
        last_message = state["messages"][-1]
        original_query = state["query"]
        search_query = original_query
        status = "completed"
        reason = "Query reformulada por el LLM."
        usage = {"prompt": 0, "completion": 0, "total": 0}

        try:
            conversation = "\n".join(
                f"{message.type}: {message.content}"
                for message in state["messages"]
                if getattr(message, "content", None)
            )
            result = self.query_llm.invoke([
                SystemMessage(content=QUERY_REFORMULATION_PROMPT),
                HumanMessage(content=conversation),
            ])
            search_query = result.content.strip() or original_query
            usage = self._usage(result)
        except Exception as exc:
            status = "fallback"
            reason = "Fallo la reformulacion; se uso la consulta original."

        updated_tool_calls = []
        for tool_call in last_message.tool_calls:
            updated = dict(tool_call)
            if updated["name"] == "rag_search":
                updated["args"] = {
                    "query": search_query,
                    "top_k": state.get("top_k", 5),
                }
            updated_tool_calls.append(updated)

        updated_message = AIMessage(
            id=last_message.id,
            content=last_message.content,
            tool_calls=updated_tool_calls,
        )
        return {
            "messages": [updated_message],
            "search_query": search_query,
            **self._add_usage(state, usage),
            "plan": self._append_plan(
                state,
                "generate_query",
                "query_llm",
                status,
                reason,
            ),
        }

    def save_memory_node(self, state: TradingAgentState) -> TradingAgentState:
        route = state.get("route", "unknown")
        saved = self.memory.save_interaction(
            session_id=state["session_id"],
            query=state["query"],
            route=route,
        )
        return {
            "saved_memory": saved,
            "plan": self._append_plan(
                state,
                "save_memory",
                "memory",
                "completed",
                "Memoria de sesion actualizada.",
            ),
        }

    def route_after_safety(self, state: TradingAgentState) -> str:
        if state.get("safety", {}).get("blocked"):
            return "blocked"
        return "agent"

    def route_tools(self, state: TradingAgentState) -> str:
        last_message = state["messages"][-1]
        if isinstance(last_message, AIMessage) and last_message.tool_calls:
            return "generate_query"
        return "save_memory"

    def _tool_result(self, state: TradingAgentState) -> tuple[list[dict], bool]:
        for message in reversed(state["messages"]):
            if isinstance(message, ToolMessage):
                artifact = message.artifact or {}
                return artifact.get("sources", []), True
        return [], False

    def _usage(self, message: AIMessage) -> dict:
        usage = message.usage_metadata or {}
        prompt = int(usage.get("input_tokens", 0))
        completion = int(usage.get("output_tokens", 0))
        total = int(usage.get("total_tokens", prompt + completion))
        return {"prompt": prompt, "completion": completion, "total": total}

    def _add_usage(self, state: TradingAgentState, usage: dict) -> dict:
        return {
            "prompt_tokens": state.get("prompt_tokens", 0) + usage["prompt"],
            "completion_tokens": state.get("completion_tokens", 0) + usage["completion"],
            "total_tokens": state.get("total_tokens", 0) + usage["total"],
        }

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
            "error": state.get("error"),
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
