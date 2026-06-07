# agent-control-plane

A small, cooperative **multi-LLM orchestrator** — a salvaged, rebuilt
distillation of the shared "Michael Control Plane" Copilot code.

> **Scope note.** This is *not* part of the `uiao` governance product. It is a
> separate experiment that happens to live in this repo under `experiments/`.
> It has its own package (`agent_control_plane`) outside `src/`, so it is not
> installed with `uiao` and is not covered by the `uiao` CI gates. Run its
> tests explicitly (see below).

## Why it exists

The original Copilot project had a sound **idea** and a thin **implementation**:
~16 orchestrator files, most of them 1 KB stubs; a `copilot_client.py` that was
actually an Azure OpenAI wrapper (synchronous `requests`); module-level config
globals; and no tests. This rebuild keeps the parts worth keeping and discards
the rest.

### Kept

* **A vendor-neutral client contract** (`LLMClient`: `ask` / `summarize` /
  `critique` / `embed` / `describe`). Orchestration never depends on a vendor.
* **A layered architecture** — clients (substrate) → orchestrator (logic) →
  human checkpoint (arbiter).
* **The charter** — ego-free cooperation, capability-not-authority, and the
  human as final arbiter (see below).

### Discarded / rebuilt

| Original | This version |
|---|---|
| Synchronous `requests` | `async` + `httpx` (lazy-imported) |
| Module-level `SETTINGS` global, hard imports | dependency injection everywhere |
| `raise_for_status()` leaking transport errors | typed `LLMError` → graceful degradation |
| `copilot_client.py` (mislabeled; never touched Copilot) | honest `AzureOpenAIClient` |
| String `if`-ladder routing | capability map (`Router`) |
| ~16 one-KB stubs (`consensus`, `divergence`, …) | a small core that actually runs |
| No tests; needs live keys to run | `ScriptedClient` + an offline test suite |
| `Exports_From_Copilot.txt` (chat links) | dropped — not code |

## The charter (salvaged doctrine)

* **No AI is "the" control plane**; none is "in charge." The system is
  capability-based, not authority-based.
* **The human is the final arbiter** of direction and acceptance — encoded as
  the injected `Checkpoint` boundary, not as prose.
* **Operate at systems altitude**; surface conflicts instead of smoothing them.
* **Traceability is structural** — every step emits an `Event`.

## Run the offline demo

```bash
cd experiments/agent-control-plane
python -m agent_control_plane.demo
```

## Run the tests

```bash
cd experiments/agent-control-plane
python -m pytest -q
```

The suite is fully offline (no API keys, no network) thanks to
`ScriptedClient`. Async code is driven via `asyncio.run(...)` so no
`pytest-asyncio` plugin is required.

## Shape

```
agent_control_plane/
  clients/
    base.py          # LLMClient contract + typed errors + metadata
    azure_openai.py  # async Azure OpenAI chat-completions client
    perplexity.py    # async Perplexity client
    scripted.py      # deterministic in-memory client (tests/demo)
  routing.py         # Capability enum + Router
  events.py          # Event + EventSink (in-memory / JSONL)
  checkpoint.py      # Decision + Checkpoint (auto-approve / callback)
  orchestrator.py    # reason → checkpoint → execute → synthesize
  demo.py            # runnable offline example
tests/               # offline pytest suite
```

## Wiring real agents

```python
from agent_control_plane import (
    AzureOpenAIClient, PerplexityClient, Orchestrator, Router, Capability,
)

clients = {
    "azure-openai": AzureOpenAIClient(
        api_key=..., endpoint=..., deployment_id=..., api_version="2024-02-01",
    ),
    "perplexity": PerplexityClient(api_key=..., model="sonar"),
}
router = Router({
    Capability.REASON: "azure-openai",
    Capability.EXECUTE: "perplexity",
    Capability.SYNTHESIZE: "azure-openai",
})
orchestrator = Orchestrator(clients=clients, router=router)
result = await orchestrator.run_cycle("…your task…")
```
