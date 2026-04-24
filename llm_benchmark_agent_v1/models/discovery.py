"""Discover available models from a LiteLLM proxy."""

from __future__ import annotations

import aiohttp
from dataclasses import dataclass, field
from config import settings


@dataclass
class ModelInfo:
    id: str
    owned_by: str = ""
    max_tokens: int | None = None
    input_cost_per_token: float | None = None
    output_cost_per_token: float | None = None
    supports_function_calling: bool = False
    supports_vision: bool = False
    metadata: dict = field(default_factory=dict)


async def _get(session: aiohttp.ClientSession, url: str) -> dict | list:
    headers = {}
    if settings.LITELLM_API_KEY:
        headers["Authorization"] = f"Bearer {settings.LITELLM_API_KEY}"
    async with session.get(url, headers=headers) as resp:
        resp.raise_for_status()
        return await resp.json()


def _is_embedding_model(model_id: str, model_info: dict) -> bool:
    """Return True if the model looks like an embedding model."""
    mid = model_id.lower()
    for kw in settings.EMBEDDING_FILTER_KEYWORDS:
        if kw in mid:
            return True
    mode = model_info.get("model_info", {}).get("mode", "")
    if mode and "embedding" in mode.lower():
        return True
    return False


async def list_models() -> list[ModelInfo]:
    """Fetch model list from /v1/models and enrich with /model/info metadata.

    Embedding models are automatically excluded.
    """
    base = settings.LITELLM_PROXY_URL.rstrip("/")
    async with aiohttp.ClientSession() as session:
        models_resp = await _get(session, f"{base}/v1/models")
        raw_models: list[dict] = models_resp.get("data", [])

        info_map: dict[str, dict] = {}
        try:
            info_resp = await _get(session, f"{base}/model/info")
            for entry in info_resp.get("data", []):
                model_name = entry.get("model_name", "")
                if model_name:
                    info_map[model_name] = entry
        except Exception:
            pass  # /model/info may not be available on all deployments

    results: list[ModelInfo] = []
    for m in raw_models:
        model_id = m.get("id", "")
        if not model_id:
            continue
        info = info_map.get(model_id, {})
        if _is_embedding_model(model_id, info):
            continue
        model_info_block = info.get("model_info", {})
        results.append(
            ModelInfo(
                id=model_id,
                owned_by=m.get("owned_by", ""),
                max_tokens=model_info_block.get("max_tokens"),
                input_cost_per_token=model_info_block.get("input_cost_per_token"),
                output_cost_per_token=model_info_block.get("output_cost_per_token"),
                supports_function_calling=model_info_block.get(
                    "supports_function_calling", False
                ),
                supports_vision=model_info_block.get("supports_vision", False),
                metadata=info,
            )
        )
    return results


async def list_model_ids() -> list[str]:
    """Return just the model id strings."""
    models = await list_models()
    return [m.id for m in models]
