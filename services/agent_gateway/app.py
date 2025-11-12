import os
import asyncio
from typing import List, Literal, TypedDict

import httpx
from fastapi import FastAPI
from pydantic import BaseModel

from langchain_openai import ChatOpenAI
from langchain.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import START, END, StateGraph
from langgraph.checkpoint.memory import MemorySaver

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
MCP_BRIDGE_URL = os.getenv("MCP_BRIDGE_URL", "http://localhost:8765")

# ------------------------- Tools -------------------------

@tool("list_files", return_direct=False)
def list_files() -> str:
    """List available files from the MCP filesystem (mounted under /data)."""
    url = f"{MCP_BRIDGE_URL}/list"
    with httpx.Client(timeout=10) as client:
        r = client.get(url)
        r.raise_for_status()
        files = r.json().get("files", [])
    if not files:
        return "No files found."
    return "\n".join(files)

@tool("read_file", return_direct=False)
def read_file(path: str) -> str:
    """Read a file's content from the MCP filesystem by relative path (e.g. sample.txt)."""
    url = f"{MCP_BRIDGE_URL}/read"
    with httpx.Client(timeout=20) as client:
        r = client.post(url, json={"path": path})
        if r.status_code != 200:
            return f"Error reading {path}: {r.text}"
        content = r.json().get("content", "")
    return content[:8000]  # cap content for context size

TOOLS = [list_files, read_file]

# ------------------------- Agent Node -------------------------

class AgentState(TypedDict):
    messages: List

llm = ChatOpenAI(model=OPENAI_MODEL, temperature=0.2)
llm_with_tools = llm.bind_tools(TOOLS)

SYSTEM = SystemMessage(
    content=(
        "You are an agentic assistant. When asked about files, use tools list_files/read_file. "
        "Always cite which tool you used in the answer. Be concise."
    )
)

async def agent_node(state: AgentState):
    msgs = [SYSTEM] + state["messages"]
    resp = await llm_with_tools.ainvoke(msgs)
    return {"messages": state["messages"] + [resp]}

# Router: if tool call requested, execute tools then call model again
async def router(state: AgentState):
    last = state["messages"][-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tools"
    return END

async def tools_node(state: AgentState):
    last = state["messages"][-1]
    results = []
    for call in last.tool_calls:
        name = call["name"]
        args = call.get("args", {})
        for t in TOOLS:
            if t.name == name:
                try:
                    res = t.run(**args)
                except Exception as e:
                    res = f"Tool {name} error: {e}"
                results.append({"tool": name, "output": res})
                break
    tool_msgs = []
    for r in results:
        tool_msgs.append(AIMessage(content=f"Tool {r['tool']} output:\n{r['output']}"))
    return {"messages": state["messages"] + tool_msgs}

# Build graph
builder = StateGraph(AgentState)

builder.add_node("agent", agent_node)
builder.add_node("tools", tools_node)

builder.add_edge(START, "agent")

builder.add_conditional_edges("agent", router, {"tools": "tools", END: END})
# After tools, go back to agent for final answer
builder.add_edge("tools", "agent")

memory = MemorySaver()
app_graph = builder.compile(checkpointer=memory)

# ------------------------- FastAPI -------------------------

app = FastAPI(title="Agent Gateway", version="0.1")

class ChatRequest(BaseModel):
    conversation_id: str
    message: str

@app.get("/health")
async def health():
    return {"status": "ok", "model": OPENAI_MODEL}

@app.post("/chat")
async def chat(req: ChatRequest):
    thread_id = req.conversation_id
    events = app_graph.stream({"messages": [HumanMessage(content=req.message)]}, config={"configurable": {"thread_id": thread_id}})
    final = None
    for ev in events:
        final = ev
    # final state contains messages; pick the last assistant message
    msgs = final["messages"]
    last = None
    for m in reversed(msgs):
        if isinstance(m, AIMessage):
            last = m
            break
    return {
        "reply": (last.content if last else "(no reply)"),
        "turn_messages": [str(type(m)) for m in msgs]
    }