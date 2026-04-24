"""LangGraph-compatible LLM factory using ChatLiteLLM."""

from __future__ import annotations

from langchain_community.chat_models.litellm import ChatLiteLLM
from langchain_core.language_models.chat_models import BaseChatModel

from autodoc.cli.config import AutoDocConfig


def create_chat_model(config: AutoDocConfig, temperature: float = 0.2) -> BaseChatModel:
    """
    Build a ChatLiteLLM instance configured for the user's LLM provider.

    Supports LiteLLM Proxy, Ollama, vLLM, OpenAI, and Azure via the
    provider-aware model string from AutoDocConfig.get_litellm_model().
    """
    model_name = config.get_litellm_model()

    kwargs: dict = {
        "model": model_name,
        "temperature": temperature,
        "max_retries": config.max_retries,
    }

    if config.llm_provider == "litellm_proxy":
        kwargs["api_base"] = config.llm_base_url
        kwargs["api_key"] = config.llm_api_key
    elif config.llm_provider == "ollama":
        kwargs["api_base"] = config.llm_base_url
        kwargs["api_key"] = config.llm_api_key or "dummy"
        kwargs["custom_llm_provider"] = "ollama"
    elif config.llm_provider == "vllm":
        kwargs["api_base"] = config.llm_base_url
        kwargs["api_key"] = config.llm_api_key or "dummy"
    elif config.llm_provider == "azure":
        kwargs["api_base"] = config.llm_base_url
        kwargs["api_key"] = config.llm_api_key
    else:
        kwargs["api_key"] = config.llm_api_key

    return ChatLiteLLM(**kwargs)
