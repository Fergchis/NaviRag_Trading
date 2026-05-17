from src.agent.memory import AgentMemory
from src.agent.planner import AgentPlanner, PlanStep, serialize_plan
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


class TradingAgent:
    def __init__(
        self,
        planner: AgentPlanner | None = None,
        memory: AgentMemory | None = None,
        tools: AgentTools | None = None,
    ):
        self.planner = planner or AgentPlanner()
        self.memory = memory or AgentMemory()
        self.tools = tools or AgentTools(memory=self.memory)

    def run(self, query: str, history: list, session_id: str, top_k: int = 5) -> dict:
        plan = self.planner.create_plan(query)
        short_term = self.memory.get_short_term(history)

        long_term = self._execute_load_memory(plan, session_id)
        safety = self._execute_safety(plan, query)
        if safety["blocked"]:
            self._skip_after(plan, "safety_check", "La consulta fue bloqueada por seguridad.")
            saved = self._execute_save_memory(plan, session_id, query, "blocked")
            return self._build_response(
                answer=BLOCKED_ANSWER,
                route="blocked",
                decision_reason=safety["reason"],
                plan=plan,
                session_id=session_id,
                short_term=short_term,
                long_term=long_term,
                saved=saved,
            )

        try:
            chunks = self._execute_retrieve_context(plan, query, top_k)
        except Exception:
            self._mark_step(plan, "retrieve_context", "failed", "Error de recuperacion de contexto.")
            self._mark_step(plan, "write_answer", "skipped", "No se genera respuesta sin contexto recuperado.")
            saved = self._execute_save_memory(plan, session_id, query, "retrieval_error")
            return self._build_response(
                answer=RETRIEVAL_ERROR_ANSWER,
                route="retrieval_error",
                decision_reason="Fallo la recuperacion de contexto desde un servicio externo.",
                plan=plan,
                session_id=session_id,
                short_term=short_term,
                long_term=long_term,
                saved=saved,
            )

        if not self._has_useful_context(chunks):
            self._mark_step(plan, "write_answer", "skipped", "No hay contexto util para generar respuesta.")
            saved = self._execute_save_memory(plan, session_id, query, "insufficient_context")
            return self._build_response(
                answer=INSUFFICIENT_CONTEXT_ANSWER,
                route="insufficient_context",
                decision_reason="No se recuperaron chunks con texto util.",
                plan=plan,
                session_id=session_id,
                short_term=short_term,
                long_term=long_term,
                saved=saved,
            )

        try:
            response = self._execute_write_answer(plan, query, short_term, chunks)
        except Exception:
            self._mark_step(plan, "write_answer", "failed", "Error en la generacion de respuesta del LLM.")
            saved = self._execute_save_memory(plan, session_id, query, "generation_error")
            return self._build_response(
                answer=GENERATION_ERROR_ANSWER,
                route="generation_error",
                decision_reason="Fallo la generacion de respuesta desde un servicio externo.",
                plan=plan,
                session_id=session_id,
                short_term=short_term,
                long_term=long_term,
                saved=saved,
            )

        saved = self._execute_save_memory(plan, session_id, query, "rag_answer")
        return self._build_response(
            answer=response["answer"],
            route="rag_answer",
            decision_reason="La consulta paso seguridad y tenia contexto recuperado.",
            plan=plan,
            session_id=session_id,
            short_term=short_term,
            long_term=long_term,
            saved=saved,
            sources=response.get("sources", []),
            prompt_tokens=response.get("prompt_tokens", 0),
            completion_tokens=response.get("completion_tokens", 0),
            total_tokens=response.get("total_tokens", 0),
        )

    def _execute_load_memory(self, plan: list[PlanStep], session_id: str) -> dict:
        memory = self.tools.get("load_memory_tool").func({"session_id": session_id})
        self._mark_step(plan, "load_memory", "completed", "Memoria cargada.")
        return memory

    def _execute_safety(self, plan: list[PlanStep], query: str) -> dict:
        safety = self.tools.get("safety_check_tool").func({"query": query})
        self._mark_step(plan, "safety_check", "completed", safety["reason"])
        return safety

    def _execute_retrieve_context(self, plan: list[PlanStep], query: str, top_k: int) -> list[dict]:
        chunks = self.tools.get("retrieve_context_tool").func({"query": query, "top_k": top_k})
        self._mark_step(plan, "retrieve_context", "completed", f"Chunks recuperados: {len(chunks)}.")
        return chunks

    def _execute_write_answer(
        self,
        plan: list[PlanStep],
        query: str,
        history: list[dict],
        chunks: list[dict],
    ) -> dict:
        response = self.tools.get("write_answer_tool").func({
            "query": query,
            "history": history,
            "chunks": chunks,
        })
        self._mark_step(plan, "write_answer", "completed", "Respuesta generada desde contexto recuperado.")
        return response

    def _execute_save_memory(self, plan: list[PlanStep], session_id: str, query: str, route: str) -> dict:
        saved = self.tools.get("save_memory_tool").func({
            "session_id": session_id,
            "query": query,
            "route": route,
        })
        self._mark_step(plan, "save_memory", "completed", "Memoria de sesion actualizada.")
        return saved

    def _build_response(
        self,
        answer: str,
        route: str,
        decision_reason: str,
        plan: list[PlanStep],
        session_id: str,
        short_term: list[dict],
        long_term: dict,
        saved: dict,
        sources: list[dict] | None = None,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        total_tokens: int = 0,
    ) -> dict:
        return {
            "answer": answer,
            "sources": sources or [],
            "plan": serialize_plan(plan),
            "decision": {
                "route": route,
                "reason": decision_reason,
            },
            "memory": {
                "session_id": session_id,
                "short_term_messages": len(short_term),
                "long_term_loaded": int(long_term.get("interaction_count", 0)) > 0,
                "long_term_saved": bool(saved),
            },
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
        }

    def _has_useful_context(self, chunks: list[dict]) -> bool:
        return any(chunk.get("text", "").strip() for chunk in chunks)

    def _mark_step(self, plan: list[PlanStep], name: str, status: str, reason: str) -> None:
        for step in plan:
            if step.name == name:
                step.status = status
                step.reason = reason
                return

    def _skip_after(self, plan: list[PlanStep], name: str, reason: str) -> None:
        skip = False
        for step in plan:
            if step.name == name:
                skip = True
                continue
            if skip:
                step.status = "skipped"
                step.reason = reason
