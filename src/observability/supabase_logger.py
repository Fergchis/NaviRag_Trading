import os
from datetime import datetime, timezone
from typing import Any

from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()


class SupabaseLogger:
    def __init__(self):
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")

        self._client: Client = create_client(url, key)

    def create_session(self, thread_id: str, user_id: str) -> str:
        """Creates a new session row. Returns the session UUID."""
        result = self._client.table("sessions").insert({
            "thread_id": thread_id,
            "user_id": user_id,
        }).execute()
        return result.data[0]["id"]

    def log_message(
        self,
        session_id: str,
        role: str,
        content: str,
        blocked: bool = False,
    ) -> str:
        """Logs a user or assistant message. Returns the message UUID."""
        result = self._client.table("messages").insert({
            "session_id": session_id,
            "role": role,
            "content": content,
            "blocked": blocked,
        }).execute()
        return result.data[0]["id"]

    def log_trace(
        self,
        session_id: str,
        message_id: str,
        step_order: int,
        node_name: str,
        started_at: datetime,
        ended_at: datetime,
        input: dict[str, Any] | None = None,
        output: dict[str, Any] | None = None,
        tool_name: str | None = None,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
        company: str | None = None,
        model: str | None = None,
    ) -> str:
        """Logs a single LangGraph node execution with timing and step order. Returns the trace UUID."""
        duration_ms = int((ended_at - started_at).total_seconds() * 1000)
        result = self._client.table("traces").insert({
            "session_id": session_id,
            "message_id": message_id,
            "step_order": step_order,
            "node_name": node_name,
            "tool_name": tool_name,
            "started_at": started_at.isoformat(),
            "ended_at": ended_at.isoformat(),
            "duration_ms": duration_ms,
            "input": input,
            "output": output,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "company": company,
            "model": model,
        }).execute()
        return result.data[0]["id"]

    def log_cost(
        self,
        session_id: str,
        message_id: str,
        trace_id: str,
        company: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> None:
        """Looks up model pricing and logs the cost for a trace."""
        pricing = self._client.table("model_pricing").select(
            "prompt_price_per_1m, completion_price_per_1m"
        ).eq("company", company).eq("model", model).execute()

        if pricing.data:
            prompt_price = float(pricing.data[0]["prompt_price_per_1m"])
            completion_price = float(pricing.data[0]["completion_price_per_1m"])
        else:
            prompt_price, completion_price = 0.0, 0.0

        prompt_cost = (prompt_tokens / 1_000_000) * prompt_price
        completion_cost = (completion_tokens / 1_000_000) * completion_price

        self._client.table("costs").insert({
            "session_id": session_id,
            "message_id": message_id,
            "trace_id": trace_id,
            "company": company,
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "prompt_cost": prompt_cost,
            "completion_cost": completion_cost,
            "total_cost": prompt_cost + completion_cost,
        }).execute()

    @staticmethod
    def now() -> datetime:
        return datetime.now(timezone.utc)
