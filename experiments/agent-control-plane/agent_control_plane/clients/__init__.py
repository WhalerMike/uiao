"""Cognitive-engine clients: the vendor-neutral seam."""

from __future__ import annotations

from .azure_openai import AzureOpenAIClient
from .base import (
    LLMClient,
    LLMError,
    LLMMetadata,
    LLMNotSupported,
    LLMTransportError,
)
from .perplexity import PerplexityClient
from .scripted import ScriptedClient

__all__ = [
    "LLMClient",
    "LLMMetadata",
    "LLMError",
    "LLMTransportError",
    "LLMNotSupported",
    "AzureOpenAIClient",
    "PerplexityClient",
    "ScriptedClient",
]
