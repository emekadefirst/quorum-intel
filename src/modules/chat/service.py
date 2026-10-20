"""Chat service: thin wrapper around the trading_agent.

Stateless: the client sends the full conversation history each turn, we hand
it to the agent, and return the final assistant message. Agent-called tool
results are not surfaced to the client (the final message already synthesizes
them). Later: stream intermediate steps, persist history, etc.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

from src.intelligence.agents import trading_agent

Role = Literal["user", "assistant", "system"]


class ChatMessage(BaseModel):
    role: Role
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]


class ChatResponse(BaseModel):
    message: ChatMessage


def _to_lc(messages: list[ChatMessage]) -> list[tuple[str, str]]:
    """LangChain accepts (role, content) tuples for human/ai/system."""
    role_map = {"user": "human", "assistant": "ai", "system": "system"}
    return [(role_map[m.role], m.content) for m in messages]


def _extract_text(obj: Any) -> str:
    """LangChain messages may carry string content or a list of content blocks."""
    content = getattr(obj, "content", obj)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text" and "text" in block:
                    parts.append(str(block["text"]))
            elif isinstance(block, str):
                parts.append(block)
        return "".join(parts)
    return str(content)


class ChatService:
    @classmethod
    async def send(cls, req: ChatRequest) -> ChatResponse:
        if not req.messages or req.messages[-1].role != "user":
            raise ValueError("Last message must be from the user.")

        result = await trading_agent.ainvoke(
            {"messages": _to_lc(req.messages)}  # type: ignore[arg-type]
        )
        out_messages = result.get("messages", []) if isinstance(result, dict) else []
        if not out_messages:
            raise RuntimeError("Agent returned no messages.")

        final = out_messages[-1]
        text = _extract_text(final).strip() or "(empty response)"
        return ChatResponse(message=ChatMessage(role="assistant", content=text))
