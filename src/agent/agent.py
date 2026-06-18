from src.agent.graph import TradingAgentGraph
from src.agent.memory import AgentMemory


class TradingAgent:
    def __init__(
        self,
        memory: AgentMemory | None = None,
        graph: TradingAgentGraph | None = None,
    ):
        self.memory = memory or AgentMemory()
        self.graph = graph or TradingAgentGraph(memory=self.memory)

    def run(self, query: str, history: list, session_id: str, top_k: int = 5) -> dict:
        return self.graph.run(
            query=query,
            history=history,
            session_id=session_id,
            top_k=top_k,
        )
