"""Characterization test: the GPO → OrgPath join is precedence-blind.

This pins the *honest* semantic boundary of the OrgPath migration planner so
no narrative can re-overclaim it.

Background (the claim under test)
---------------------------------
OrgPath has been described as "uniquely composing org hierarchy *with
inheritance*" — i.e. resolving effective policy down a tree the way Active
Directory Group Policy does. AD GPO resolution is **non-monotonic and
order-dependent**: an ancestor link marked *Enforced* (``NoOverride``) punches
through a descendant's *Block Inheritance* and reverses the usual child-wins
precedence. Reproducing that requires an ordered fold over the path with two
control bits per link.

What the code actually does
---------------------------
``gpo_analytics`` faithfully *parses* the per-link ``enforced`` bit (from
``<NoOverride>``) and notes ``Blocked`` elements. But the "differentiated join"
(:func:`build_migration_plan`) consumes only ``link.enabled`` and the SOM path
→ OU intent. The ``enforced`` bit — and Block Inheritance — are **discarded at
the join**: :class:`ScopeTarget`, the join's output type, has no field that can
carry precedence at all.

Consequence: the migration plan cannot represent which setting *wins* at a leaf
when links conflict. That is fine for its stated job (per-GPO Intune migration
planning) but it falsifies any "GPO-class inheritance resolver" moat claim — the
information required to resolve effective policy is structurally absent from the
output.

These tests assert the *current* behavior. If a real precedence resolver is ever
added, they should be updated deliberately (and the moat claim revisited), not
left to rot.
"""

from __future__ import annotations

from uiao.adapters.modernization.active_directory.gpo_analytics import (
    GpoLink,
    GpoReport,
)
from uiao.adapters.modernization.active_directory.gpo_orgpath_plan import (
    build_migration_plan,
)


def _report_with_links(*links: GpoLink) -> GpoReport:
    """A minimal, settings-free GpoReport carrying just the links under test."""
    return GpoReport(
        guid="{ENFORCED-TEST-0000-0000-000000000000}",
        name="Precedence Boundary Fixture",
        computer_enabled=True,
        user_enabled=True,
        created_time="2026-01-01T00:00:00Z",
        modified_time="2026-01-01T00:00:00Z",
        wmi_filter="",
        links=links,
        settings=(),
    )


def test_enforced_bit_is_parsed_into_the_link() -> None:
    """Precondition: the precedence information *exists* before the join."""
    link = GpoLink(
        som_name="Agency",
        som_path="agency.gov/Agency",
        enabled=True,
        enforced=True,
    )
    assert link.enforced is True
    assert "enforced" in link.to_dict()


def test_join_output_cannot_carry_precedence() -> None:
    """The differentiated join drops the enforced bit by construction.

    ``ScopeTarget`` has no precedence field, so two links that differ ONLY in
    their enforced flag produce byte-identical scope targets (modulo the field
    that records it — which does not exist).
    """
    enforced = build_migration_plan(
        _report_with_links(GpoLink(som_name="Finance", som_path="agency.gov/Finance", enabled=True, enforced=True))
    )
    not_enforced = build_migration_plan(
        _report_with_links(GpoLink(som_name="Finance", som_path="agency.gov/Finance", enabled=True, enforced=False))
    )

    [enforced_target] = enforced.scope_targets
    [plain_target] = not_enforced.scope_targets

    # No slot for precedence anywhere in the join's output contract.
    assert "enforced" not in enforced_target.to_dict()
    assert "blocked" not in enforced_target.to_dict()

    # Enforced vs not-enforced are indistinguishable downstream: the plan loses
    # the only information needed to resolve effective policy.
    assert enforced_target.to_dict() == plain_target.to_dict()


def test_conflicting_links_resolve_to_independent_targets_not_an_effective_value() -> None:
    """The Block + Enforced known-answer case the join cannot compute.

    Model the canonical 3-node interaction as two enabled links on one GPO:

        agency.gov/Agency          (Enforced — should punch through below)
        agency.gov/Agency/Finance  (a child OU that, with Block Inheritance,
                                    would otherwise win)

    Correct GPO semantics: the Enforced ancestor wins at the leaf. The planner
    instead emits one scope target *per link*, with no precedence ordering and
    no single resolved effective value — proving it materializes per-link
    recommendations rather than resolving inheritance.
    """
    plan = build_migration_plan(
        _report_with_links(
            GpoLink(som_name="Agency", som_path="agency.gov/Agency", enabled=True, enforced=True),
            GpoLink(
                som_name="Finance",
                som_path="agency.gov/Agency/Finance",
                enabled=True,
                enforced=False,
            ),
        )
    )

    # Both links survive as independent targets — there is no winner.
    assert len(plan.scope_targets) == 2
    # And nothing in any target encodes that the Agency link should win.
    for target in plan.scope_targets:
        assert "enforced" not in target.to_dict()
        assert "precedence" not in target.to_dict()
