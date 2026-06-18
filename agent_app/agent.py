import os
from typing import Annotated, Literal, Optional, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, create_react_agent
from langgraph.store.memory import InMemoryStore
from pydantic import BaseModel

from agent_app.prompts import (
    ANSWER_AGENT_SYSTEM_PROMPT,
    MEMORY_AGENT_SYSTEM_PROMPT,
    QUERY_REFORMULATION_PROMPT,
    RAG_AGENT_SYSTEM_PROMPT,
    SUPERVISOR_SYSTEM_PROMPT,
)
from agent_app.tools import MEMORY_NAMESPACE, memory_tools, rag_tools
from agent_app.utils.embeddings import GitHubModelsEmbeddings

load_dotenv()


def get_chat_model() -> ChatOpenAI:
    endpoint = os.getenv(
        "GITHUB_MODELS_CHAT_ENDPOINT",
        "https://models.github.ai/inference/chat/completions",
    )
    base_url = endpoint.removesuffix("/chat/completions").rstrip("/")
    return ChatOpenAI(
        api_key=os.getenv("GITHUB_TOKEN"),
        base_url=base_url,
        model=os.getenv("GITHUB_CHAT_MODEL", "openai/gpt-4o-mini"),
        temperature=0,
    )


class AgentState(TypedDict, total=False):
    messages: Annotated[list, add_messages]
    user_query: str
    next: str
    executed_agents: list[str]
    final_agent: str
    retrieval_used: bool
    memory_used: bool
    financial_rejection: bool
    retrieved_context: str


class Route(BaseModel):
    next: Literal[
        "rag_agent",
        "memory_agent",
        "answer_agent",
        "rag_then_answer",
        "memory_then_answer",
        "memory_then_rag_then_answer",
        "FINISH",
    ]
    response: Optional[str] = None
    financial_rejection: bool = False


class RagState(TypedDict):
    messages: Annotated[list, add_messages]


llm = get_chat_model()
query_llm = get_chat_model()

github_embeddings = GitHubModelsEmbeddings()
store = InMemoryStore(index={"dims": 1536, "embed": github_embeddings})

memory_agent = create_react_agent(
    llm,
    memory_tools,
    prompt=MEMORY_AGENT_SYSTEM_PROMPT,
    store=store,
)
answer_agent = create_react_agent(
    llm,
    tools=[],
    prompt=ANSWER_AGENT_SYSTEM_PROMPT,
)


rag_llm = llm.bind_tools(rag_tools)


def call_rag_model(state: RagState) -> RagState:
    response = rag_llm.invoke([
        SystemMessage(content=RAG_AGENT_SYSTEM_PROMPT),
        *state["messages"],
    ])
    return {"messages": [response]}


def generate_query(state: RagState) -> RagState:
    conversation = "\n".join(
        f"{message.type}: {message.content}"
        for message in state["messages"]
        if getattr(message, "content", None)
    )
    result = query_llm.invoke([
        SystemMessage(content=QUERY_REFORMULATION_PROMPT),
        SystemMessage(content=f"Conversación:\n{conversation}"),
    ])
    search_query = result.content.strip()

    last_message = state["messages"][-1]
    updated_tool_calls = []
    for tool_call in last_message.tool_calls:
        updated = dict(tool_call)
        if updated["name"] == "rag_search":
            updated["args"] = {"query": search_query}
        updated_tool_calls.append(updated)

    updated_message = AIMessage(
        id=last_message.id,
        content=last_message.content,
        tool_calls=updated_tool_calls,
    )
    return {"messages": [updated_message]}


def should_continue_rag(state: RagState) -> str:
    last_message = state["messages"][-1]
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        if any(call["name"] == "rag_search" for call in last_message.tool_calls):
            return "generate_query"
    return END


rag_builder = StateGraph(RagState)
rag_builder.add_node("rag_model", call_rag_model)
rag_builder.add_node("generate_query", generate_query)
rag_builder.add_node("tools", ToolNode(rag_tools))
rag_builder.set_entry_point("rag_model")
rag_builder.add_conditional_edges(
    "rag_model",
    should_continue_rag,
    {"generate_query": "generate_query", END: END},
)
rag_builder.add_edge("generate_query", "tools")
rag_builder.add_edge("tools", "rag_model")
rag_agent = rag_builder.compile()


def summarize_for(messages: list, role: str, user_query: str) -> HumanMessage:
    role_instruction = {
        "rag": (
            "Resume qué información documental debe recuperarse para contestar la consulta "
            "original. Ignora como tema de búsqueda las instrucciones operativas y los "
            "mensajes internos de memoria. Solo describe la tarea de recuperación."
        ),
        "memory_save": (
            "Resume qué información útil y estable del usuario debe guardarse. La tarea "
            "delegada debe exigir llamar exactamente una vez a save_memory. No agregues "
            "información que el usuario no haya comunicado."
        ),
        "answer": (
            "Prepara la tarea de respuesta a la consulta original. Incluye únicamente los "
            "recuerdos recuperados y los fragmentos documentales relevantes. Conserva "
            "literalmente las etiquetas [FUENTE N] y sus metadatos. No cambies el tema."
        ),
        "safe_answer": (
            "La consulta pide una recomendación financiera, señal o instrucción accionable. "
            "Solicita un rechazo educativo seguro y conserva el tema para ofrecer una "
            "explicación conceptual no accionable."
        ),
    }
    response = llm.invoke([
        SystemMessage(content=(
            "Eres un asistente que resume conversaciones para delegarlas a un agente "
            f"especializado. Consulta original: {user_query}\n"
            f"Instrucción: {role_instruction[role]}"
        )),
        *messages,
    ])
    return HumanMessage(content=(
        f"Consulta original: {user_query}\n"
        f"Tarea delegada: {response.content}"
    ))


def supervisor_node(state: AgentState) -> dict:
    supervisor_llm = llm.with_structured_output(Route)
    result = supervisor_llm.invoke([
        {"role": "system", "content": SUPERVISOR_SYSTEM_PROMPT},
        *state["messages"],
    ])
    updates: dict = {
        "next": result.next,
        "executed_agents": [],
        "final_agent": "supervisor",
        "retrieval_used": False,
        "memory_used": False,
        "retrieved_context": "",
        "financial_rejection": result.financial_rejection,
    }
    last_human = next(
        (
            message
            for message in reversed(state["messages"])
            if isinstance(message, HumanMessage)
        ),
        None,
    )
    if last_human is not None:
        updates["user_query"] = str(last_human.content)
    if result.response:
        updates["messages"] = [AIMessage(content=result.response)]
    return updates


def _append_agent(state: AgentState, agent_name: str) -> list[str]:
    return [*state.get("executed_agents", []), agent_name]


def rag_node(state: AgentState, config: RunnableConfig) -> dict:
    summary = summarize_for(state["messages"], "rag", state["user_query"])
    result = rag_agent.invoke({"messages": [summary]}, config)
    messages = result["messages"]
    contexts = [
        str(message.content)
        for message in messages
        if isinstance(message, ToolMessage) and message.content
    ]
    return {
        "messages": messages,
        "executed_agents": _append_agent(state, "rag_agent"),
        "final_agent": "rag_agent",
        "retrieval_used": bool(contexts),
        "retrieved_context": "\n\n".join(contexts),
    }


def search_long_term_memory(query: str, config: RunnableConfig) -> list[str]:
    user_id = config.get("configurable", {}).get("user_id")
    if not user_id:
        return []

    results = store.search(
        (MEMORY_NAMESPACE, str(user_id)),
        query=query,
        limit=5,
    )
    memories = []
    for item in results:
        value = item.value
        if isinstance(value, dict):
            memory = value.get("memory")
        else:
            memory = value
        if memory:
            memories.append(str(memory))
    return memories


def memory_node(state: AgentState, config: RunnableConfig) -> dict:
    if state["next"] == "memory_agent":
        summary = summarize_for(state["messages"], "memory_save", state["user_query"])
        result = memory_agent.invoke({"messages": [summary]}, config)
        messages = result["messages"]
        memory_used = any(
            call["name"] == "save_memory"
            for message in messages
            if isinstance(message, AIMessage)
            for call in message.tool_calls
        )
    else:
        memories = search_long_term_memory(state["user_query"], config)
        content = (
            "Memorias long-term recuperadas:\n- " + "\n- ".join(memories)
            if memories
            else "No se encontraron memorias long-term relevantes para esta consulta."
        )
        messages = [AIMessage(content=content)]
        memory_used = True

    return {
        "messages": messages,
        "executed_agents": _append_agent(state, "memory_agent"),
        "final_agent": "memory_agent",
        "memory_used": memory_used,
    }


def answer_node(state: AgentState, config: RunnableConfig) -> dict:
    role = "safe_answer" if state.get("financial_rejection") else "answer"
    summary = summarize_for(state["messages"], role, state["user_query"])
    result = answer_agent.invoke({"messages": [summary]}, config)
    return {
        "messages": result["messages"],
        "executed_agents": _append_agent(state, "answer_agent"),
        "final_agent": "answer_agent",
    }


def supervisor_route(state: AgentState) -> str:
    route = state["next"]
    if route == "FINISH":
        return END
    if route in {"rag_then_answer"}:
        return "rag_agent"
    if route in {"memory_then_answer", "memory_then_rag_then_answer"}:
        return "memory_agent"
    return route


def after_memory_route(state: AgentState) -> str:
    if state["next"] == "memory_then_answer":
        return "answer_agent"
    if state["next"] == "memory_then_rag_then_answer":
        return "rag_agent"
    return END


def after_rag_route(state: AgentState) -> str:
    if state["next"] in {"rag_then_answer", "memory_then_rag_then_answer"}:
        return "answer_agent"
    return END


builder = StateGraph(AgentState)
builder.add_node("supervisor", supervisor_node)
builder.add_node("rag_agent", rag_node)
builder.add_node("memory_agent", memory_node)
builder.add_node("answer_agent", answer_node)

builder.add_edge(START, "supervisor")
builder.add_conditional_edges("supervisor", supervisor_route)
builder.add_conditional_edges("memory_agent", after_memory_route)
builder.add_conditional_edges("rag_agent", after_rag_route)
builder.add_edge("answer_agent", END)

checkpointer = MemorySaver()
graph = builder.compile(checkpointer=checkpointer, store=store)
