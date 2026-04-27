"""Migration sandbox (UIAO_119 v2, §4.4 action 119.3 c).

The migration sandbox lets an operator preview the effect of a tenant
or environment change *before* promoting it. Concretely:

- The operator has a "before" :class:`TenantContext` (the current
  state — say `acme` in `dev`) and an "after" context (`acme` in
  `stage`).
- They have a runner — typically an enforcement-runtime dispatch, an
  archive manager replay, or any callable shaped
  ``(ctx) -> Iterable[Any]`` that produces deterministic outputs.
- :class:`MigrationSandbox` invokes the runner under each context,
  serializes the outputs through the supplied ``serialize`` callable
  (default: :func:`repr`), and emits a :class:`SandboxDiff` showing
  what's added, removed, and unchanged between the two runs.

The diff is structural — adds and removes are computed by set
difference on the serialized strings, not on object identity. Any
hashable, deterministically-serializable output works.

Why a separate module: keeps the sandbox primitive testable and
reusable. The first natural consumers (in tests) are the
:class:`EnforcementRuntime` and :class:`ArchiveManager`, but the
shape is generic so future consumers (orchestrator dispatch, CQL
queries) plug in without rework.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

from uiao.governance.tenancy import TenantContext


@dataclass(frozen=True)
class SandboxRun:
    """One execution of the runner under one :class:`TenantContext`."""

    label: str
    """Free-form label, e.g. ``"before"`` / ``"after"`` / ``"dev-to-stage"``."""
    context: TenantContext
    outputs: tuple[str, ...]
    """Serialized outputs in deterministic order. The order is the
    runner's natural iteration order — the diff treats outputs as a
    set so order does not affect added / removed."""

    def as_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "tenant_id": self.context.tenant_id,
            "actor": self.context.actor,
            "environment": self.context.environment.value,
            "outputs": list(self.outputs),
        }


@dataclass(frozen=True)
class SandboxDiff:
    """Structural diff between two :class:`SandboxRun` outputs.

    ``added`` is "in after but not before"; ``removed`` is "in before
    but not after"; ``unchanged`` is the intersection. All three are
    sorted lexicographically so the result is deterministic.
    """

    before: SandboxRun
    after: SandboxRun
    added: tuple[str, ...] = field(default_factory=tuple)
    removed: tuple[str, ...] = field(default_factory=tuple)
    unchanged: tuple[str, ...] = field(default_factory=tuple)

    @property
    def is_clean(self) -> bool:
        """True when the after run produces exactly the before set."""
        return not self.added and not self.removed

    def as_dict(self) -> dict[str, Any]:
        return {
            "before": self.before.as_dict(),
            "after": self.after.as_dict(),
            "added": list(self.added),
            "removed": list(self.removed),
            "unchanged": list(self.unchanged),
            "is_clean": self.is_clean,
        }


def _default_serialize(value: Any) -> str:
    return repr(value)


@dataclass
class MigrationSandbox:
    """Runs a callable under two :class:`TenantContext` instances and
    diffs the results.

    Typical use:

        sandbox = MigrationSandbox(runner=lambda ctx: dispatch(ctx))
        diff = sandbox.run(before=current_ctx, after=proposed_ctx)
        if diff.is_clean:
            promote(proposed_ctx)
        else:
            print(diff.as_dict())
    """

    runner: Callable[[TenantContext], Iterable[Any]]
    serialize: Callable[[Any], str] = _default_serialize

    def _run_one(self, ctx: TenantContext, label: str) -> SandboxRun:
        raw_outputs = list(self.runner(ctx))
        serialized = tuple(self.serialize(o) for o in raw_outputs)
        return SandboxRun(label=label, context=ctx, outputs=serialized)

    def run(
        self,
        *,
        before: TenantContext,
        after: TenantContext,
        before_label: str = "before",
        after_label: str = "after",
    ) -> SandboxDiff:
        before_run = self._run_one(before, before_label)
        after_run = self._run_one(after, after_label)
        before_set = set(before_run.outputs)
        after_set = set(after_run.outputs)
        added = tuple(sorted(after_set - before_set))
        removed = tuple(sorted(before_set - after_set))
        unchanged = tuple(sorted(before_set & after_set))
        return SandboxDiff(
            before=before_run,
            after=after_run,
            added=added,
            removed=removed,
            unchanged=unchanged,
        )

    def explain(self, diff: SandboxDiff) -> str:
        """One-line human-readable summary used by CLI / report
        consumers. Empty when the diff is clean."""
        if diff.is_clean:
            return ""
        parts: list[str] = []
        if diff.added:
            parts.append(f"+{len(diff.added)} added")
        if diff.removed:
            parts.append(f"-{len(diff.removed)} removed")
        return f"{diff.before.label} → {diff.after.label}: " + ", ".join(parts)


__all__ = [
    "MigrationSandbox",
    "SandboxDiff",
    "SandboxRun",
]
