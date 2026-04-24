"""Configuration management using pydantic-settings."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class AutoDocConfig(BaseSettings):
    """AutoDoc Agent configuration — loaded from .env, environment variables, or CLI overrides."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llm_provider: str = "litellm_proxy"  # litellm_proxy, ollama, vllm, openai, azure
    llm_base_url: str = "http://localhost:4000"
    llm_api_key: str = "sk-your-key"
    llm_model: str = "gpt-4o"

    max_tokens_per_module: int = 100_000
    max_tokens_per_leaf: int = 50_000
    max_depth: int = 2

    output_dir: str = "./docs-output"

    # LangGraph agent settings
    max_retries: int = 2
    validation_enabled: bool = True

    def get_litellm_model(self) -> str:
        """
        Return the model string formatted for litellm based on the provider.

        - litellm_proxy: model name as-is (proxy handles routing)
        - ollama: prefixed with "ollama/" for litellm routing
        - vllm: prefixed with "openai/" since vLLM serves OpenAI-compatible API
        - openai: model name as-is
        - azure: prefixed with "azure/" for litellm routing
        """
        model = self.llm_model
        provider = self.llm_provider.lower().strip()

        if provider == "litellm_proxy":
            return model
        elif provider == "ollama":
            return f"ollama/{model}" if not model.startswith("ollama/") else model
        elif provider == "vllm":
            return f"openai/{model}" if not model.startswith("openai/") else model
        elif provider == "azure":
            return f"azure/{model}" if not model.startswith("azure/") else model
        else:
            return model

    def display(self) -> str:
        """Return a formatted display of current config."""
        masked_key = self.llm_api_key[:8] + "..." if len(self.llm_api_key) > 8 else "***"
        return (
            f"  LLM provider:  {self.llm_provider}\n"
            f"  LLM endpoint:  {self.llm_base_url}\n"
            f"  LLM API key:   {masked_key}\n"
            f"  LLM model:     {self.llm_model} (resolved: {self.get_litellm_model()})\n"
            f"  Max tokens/module: {self.max_tokens_per_module}\n"
            f"  Max tokens/leaf:   {self.max_tokens_per_leaf}\n"
            f"  Max depth:     {self.max_depth}\n"
            f"  Output dir:    {self.output_dir}"
        )
