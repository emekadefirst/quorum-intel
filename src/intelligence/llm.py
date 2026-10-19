"""LLM adapter: LLM_PROVIDER picks which langchain chat model to import.

Supported providers:
    anthropic       -> langchain_anthropic.ChatAnthropic
    google-gemini   -> langchain_google_genai.ChatGoogleGenerativeAI
    openai          -> langchain_openai.ChatOpenAI
    deepseek        -> langchain_openai.ChatOpenAI (OpenAI-compatible endpoint)
    qwen            -> langchain_openai.ChatOpenAI (OpenAI-compatible endpoint)
"""

from __future__ import annotations

from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel

from src.configs.llm import (
    LLM_API_BASE_URL,
    LLM_API_KEY,
    LLM_MAX_TOKENS,
    LLM_MODEL,
    LLM_PROVIDER,
    LLM_TEMPERATURE,
)

# Default model + default OpenAI-compatible base URL per provider
_DEFAULTS: dict[str, tuple[str, str]] = {
    "anthropic": ("claude-sonnet-4-5", ""),
    "google-gemini": ("gemini-2.5-flash", ""),
    "openai": ("gpt-4o-mini", ""),
    "deepseek": ("deepseek-chat", "https://api.deepseek.com/v1"),
    "qwen": ("qwen-plus", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
}


def _build_anthropic(model: str, **kw: Any) -> BaseChatModel:
    from langchain_anthropic import ChatAnthropic

    return ChatAnthropic(model_name=model, api_key=LLM_API_KEY, **kw)


def _build_google_gemini(model: str, **kw: Any) -> BaseChatModel:
    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(model=model, google_api_key=LLM_API_KEY, **kw)


def _build_openai_compatible(model: str, base_url: str, **kw: Any) -> BaseChatModel:
    from langchain_openai import ChatOpenAI

    kwargs: dict[str, Any] = {"model": model, "api_key": LLM_API_KEY, **kw}
    if base_url:
        kwargs["base_url"] = base_url
    return ChatOpenAI(**kwargs)


def get_model(
    provider: str | None = None,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    **kwargs: Any,
) -> BaseChatModel:
    provider = (provider or LLM_PROVIDER).lower()
    if provider not in _DEFAULTS:
        raise ValueError(
            f"Unknown LLM provider {provider!r}; choose from {list(_DEFAULTS)}"
        )
    if not LLM_API_KEY:
        raise RuntimeError("LLM_API_KEY not set")

    default_model, default_base_url = _DEFAULTS[provider]
    chosen_model = model or LLM_MODEL or default_model
    common = {
        "temperature": temperature if temperature is not None else LLM_TEMPERATURE,
        "max_tokens": max_tokens if max_tokens is not None else LLM_MAX_TOKENS,
        **kwargs,
    }

    if provider == "anthropic":
        return _build_anthropic(chosen_model, **common)
    if provider == "google-gemini":
        return _build_google_gemini(chosen_model, **common)
    # openai, deepseek, qwen all share ChatOpenAI
    base_url = LLM_API_BASE_URL or default_base_url
    return _build_openai_compatible(chosen_model, base_url, **common)


model: BaseChatModel = get_model()
