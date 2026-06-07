"""Async Azure OpenAI Chat Completions client.

Salvaged and corrected from the original ``copilot_client.py``. That file was
**mislabeled**: despite the name it never spoke to Microsoft Copilot — it
POSTed to the Azure OpenAI Chat Completions API. This version keeps the useful
part (the request shape) and fixes the rest:

* ``async`` via ``httpx.AsyncClient`` instead of blocking ``requests``;
* ``httpx`` is lazy-imported inside :meth:`ask`, so importing this module (and
  the whole package) needs only the standard library;
* transport / response-shape failures raise :class:`LLMTransportError`.
"""

from __future__ import annotations

from typing import Any

from .base import LLMClient, LLMMetadata, LLMTransportError


class AzureOpenAIClient(LLMClient):
    """Chat-completions client for an Azure OpenAI deployment."""

    def __init__(
        self,
        *,
        api_key: str,
        endpoint: str,
        deployment_id: str,
        api_version: str,
        model: str = "",
        system_message: str = "",
        timeout: float = 60.0,
        name: str = "azure-openai",
    ) -> None:
        self.name = name
        self._api_key = api_key
        self._endpoint = endpoint.rstrip("/")
        self._deployment_id = deployment_id
        self._api_version = api_version
        self._model = model
        self._system_message = system_message
        self._timeout = timeout

    async def ask(self, prompt: str, *, system: str | None = None, **kwargs: Any) -> str:
        import httpx  # lazy: keep package import stdlib-only

        url = (
            f"{self._endpoint}/openai/deployments/{self._deployment_id}"
            f"/chat/completions?api-version={self._api_version}"
        )
        system_content = system if system is not None else self._system_message
        messages: list[dict[str, str]] = []
        if system_content:
            messages.append({"role": "system", "content": system_content})
        messages.append({"role": "user", "content": prompt})

        payload: dict[str, Any] = {"messages": messages, **kwargs}
        if self._model:
            payload["model"] = self._model

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    url,
                    headers={"api-key": self._api_key, "Content-Type": "application/json"},
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
            provider="AzureOpenAI",
            model=self._model,
            supports_embeddings=False,
            extra={
                "endpoint": self._endpoint,
                "deployment_id": self._deployment_id,
                "api_version": self._api_version,
            },
        )


__all__ = ["AzureOpenAIClient"]
