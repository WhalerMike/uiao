"""Runnable, offline demonstration of a cooperative cycle.

    python -m agent_control_plane.demo

Wires two :class:`ScriptedClient` agents (so it needs no API keys or network)
and runs one reason -> checkpoint -> execute -> synthesize cycle, printing the
synthesis and the recorded event trail.
"""

from __future__ import annotations

import asyncio

from .clients import ScriptedClient
from .events import InMemoryEventSink
from .orchestrator import Orchestrator
from .routing import Capability, Router


async def _main() -> None:
    reasoner = ScriptedClient(
        "azure-openai",
        replies={
            "Analyze": "Plan: 1) define the substrate, 2) wire two agents, 3) add a checkpoint.",
            "executive-ready": "Summary: a minimal two-agent substrate is ready; next, add tests.",
        },
    )
    executor = ScriptedClient(
        "perplexity",
        replies={"Execute": "Executed: scaffolded clients, router, and orchestrator; all green."},
    )

    router = Router(
        {
            Capability.REASON: "azure-openai",
            Capability.EXECUTE: "perplexity",
            Capability.SYNTHESIZE: "azure-openai",
        }
    )
    events = InMemoryEventSink()
    orchestrator = Orchestrator(
        clients={"azure-openai": reasoner, "perplexity": executor},
        router=router,
        events=events,
    )

    result = await orchestrator.run_cycle("Stand up a minimal two-agent substrate.")

    print("=== synthesis ===")
    print(result.synthesis)
    print("\n=== event trail ===")
    for event in events.events:
        print(f"  [{event.agent:>12}] {event.action:<10} {event.status}")


if __name__ == "__main__":
    asyncio.run(_main())
