"""Async Perplexity client (OpenAI-compatible chat completions).

Salvaged from the original ``perplexity_client.py`` and modernized the same
way as :mod:`.azure_openai`: async, lazy ``httpx`` import, typed errors.
"""

from __future__ import annotations

from typing import Any

from .base import LLMClient, LLMMetadata, LLMTransportError


class PerplexityClient(LLMClient):
    """Chat-completions client for the Perplexity API."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str = "https://api.perplexity.ai",
        timeout: float = 60.0,
        name: str = "perplexity",
    ) -> None:
        self.name = name
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    async def ask(self, prompt: str, *, system: str | None = None, **kwargs: Any) -> str:
        import httpx  # lazy: keep package import stdlib-only

        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload: dict[str, Any] = {"model": self._model, "messages": messages, **kwargs}
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{self._base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:
            raise LLMTransportError(f"{self.name}: request failed: {exc}") from exc

        try:
            return str(data["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMTransportError(f"{self.name}: unexpected response shape") from exc

    def describe(self) -> LLMMetadata:
        return LLMMetadata(
            provider="Perplexity",
            model=self._model,
            supports_embeddings=False,
            extra={"base_url": self._base_url},
        )


__all__ = ["PerplexityClient"]
