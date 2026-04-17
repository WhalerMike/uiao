from __future__ import annotations

from typing import Dict, List, Tuple

import yaml

from uiao.impl.ir.models.core import (
    Control,
    Policy,
    ProvenanceRecord,
)


def load_ksi_library() -> Dict[str, dict]:
    """Load all KSI files from the 7 category subdirectories.

    Resolves the rules directory via :class:`uiao.impl.config.Settings`
    so the sibling ``uiao-core/rules`` checkout is found post four-repo
    split.
    """
    from uiao.impl.config import Settings

    ksi_root = Settings().rules_dir / "ksi"
    ksi_dict = {}
    for ksi_file in ksi_root.rglob("ksi-*.yaml"):
        with open(ksi_file, encoding="utf-8") as f:
            ksi_data = yaml.safe_load(f)
            ksi_dict[ksi_data["ksi_id"]] = ksi_data
    return ksi_dict


def ksi_to_ir_control(ksi: dict, provenance: ProvenanceRecord) -> Control:
    """Convert a single KSI to IR Control object."""
    return Control(
        id=ksi["ksi_id"],
        source="ksi",
        description=ksi.get("description") or ksi.get("title"),
        parameters=ksi.get("parameters") or {},
        mappings={
            "nist80053": ksi.get("related_controls", []),
            "fedramp": ksi.get("related_controls", []),
            "ztmm": ksi.get("tags", []),
        },
        provenance=provenance,
    )


def ksi_to_ir_policy(ksi: dict, control: Control, tenant_boundary_id: str) -> Policy:
    """Convert a KSI to IR Policy object."""
    return Policy(
        id=f"policy:ksi:{ksi['ksi_id']}:default",
        control_ref=control.id,
        description=ksi.get("title"),
        scope={
            "identities": ["selector:role:all"],
            "resources": ["selector:service:all"],
            "boundaries": [tenant_boundary_id],
        },
        conditions={},
        expected_state={
            "pass_criteria": ksi.get("pass_criteria"),
            "uiao_extensions": ksi.get("uiao_extensions", {}),
        },
        provenance=control.provenance,
    )


def build_ksi_ir_mapping(
    tenant_boundary_id: str = "boundary:tenant:m365:contoso",
) -> Tuple[List[Control], List[Policy]]:
    """Full deterministic mapping: All 163 KSIs -> IR Controls + Policies."""
    ksi_library = load_ksi_library()
    controls: List[Control] = []
    policies: List[Policy] = []
    provenance = ProvenanceRecord(
        source="ksi-to-ir-mapping",
        timestamp="1970-01-01T00:00:00Z",
        version="1.2",
        hash=None,
    )
    for _ksi_id, ksi in sorted(ksi_library.items()):
        control = ksi_to_ir_control(ksi, provenance)
        policy = ksi_to_ir_policy(ksi, control, tenant_boundary_id)
        controls.append(control)
        policies.append(policy)
    print(f"Mapped {len(controls)} KSIs to IR Controls + Policies")
    return controls, policies


if __name__ == "__main__":
    controls, policies = build_ksi_ir_mapping()
    print(f"Generated {len(controls)} Controls and {len(policies)} Policies")

