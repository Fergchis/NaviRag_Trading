import json
from datetime import UTC, datetime
from pathlib import Path

from src.config import BASE_DIR


DEFAULT_MEMORY_PATH = BASE_DIR / "data" / "memory" / "session_memory.json"


class AgentMemory:
    def __init__(self, memory_path: Path = DEFAULT_MEMORY_PATH, short_term_limit: int = 6):
        self.memory_path = memory_path
        self.short_term_limit = short_term_limit

    def get_short_term(self, history: list[dict]) -> list[dict]:
        return history[-self.short_term_limit :]

    def load_long_term(self, session_id: str) -> dict:
        data = self._read_all()
        return data.get(session_id, self._empty_session(session_id))

    def save_interaction(self, session_id: str, query: str, route: str) -> dict:
        data = self._read_all()
        session = data.get(session_id, self._empty_session(session_id))
        questions = session.get("recent_questions", [])
        if route != "blocked":
            questions.append(query)

        session.update({
            "session_id": session_id,
            "recent_questions": questions[-5:],
            "last_route": route,
            "updated_at": self._now(),
            "interaction_count": int(session.get("interaction_count", 0)) + 1,
        })
        data[session_id] = session
        self._write_all(data)
        return session

    def _read_all(self) -> dict:
        if not self.memory_path.exists():
            return {}

        with self.memory_path.open("r", encoding="utf-8") as file:
            try:
                return json.load(file)
            except json.JSONDecodeError:
                return {}

    def _write_all(self, data: dict) -> None:
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        with self.memory_path.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=True, indent=2)

    def _empty_session(self, session_id: str) -> dict:
        return {
            "session_id": session_id,
            "recent_questions": [],
            "updated_at": None,
            "interaction_count": 0,
        }

    def _now(self) -> str:
        return datetime.now(UTC).isoformat()
