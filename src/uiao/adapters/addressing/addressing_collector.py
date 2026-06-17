"""UIAO addressing-plane drift collector.

File-driven, matching the proven Invoke-GpoAuditPipeline pattern: works from
exported artifacts, not a live infra hook. Inputs:

  intended_bindings.json   the SSOT: governed names → intended target, zones,
                           required critical SRVs, per-name FCrDNS requirement
  observed_zone.json       exported records (Get-DnsServerResourceRecord /
                           Azure DNS export normalised to a flat record list)
  resources.json           set of existing IPs/hosts (for dangling detection)

Classifies the nine satisfiable drift classes defined in UIAO_195. The three
observation-heavy classes (DRIFT-HORIZON, DRIFT-CAA/TLSA, DRIFT-DELEGATION)
are declared as deferred with their required observation — they are not faked.

Canon reference: UIAO_195 §3, ADR-108
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Support both installed-package and direct invocation from repo root.
_repo_root = Path(__file__).resolve().parents[3]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from uiao.governance.drift_core import Finding, Posture, Severity, events_json, gate  # noqa: E402

CRITICAL_SRV = {
    "_kerberos._tcp",
    "_ldap._tcp",
    "_gc._tcp",
    "_kpasswd._tcp",
}

# ---------------------------------------------------------------------------
# Input loading
# ---------------------------------------------------------------------------


def _load_dict(path: str | Path) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected JSON object, got {type(data).__name__}")
    return data


def _load_list(path: str | Path) -> list[dict]:
    data: object = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        records = data.get("records", [])
        if isinstance(records, list):
            return records
    raise ValueError(f"{path}: expected JSON array or object with 'records' key")


def _records_by_name(zone: list[dict]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for r in zone:
        out.setdefault(r["name"], []).append(r)
    return out


# ---------------------------------------------------------------------------
# Satisfiable classifiers
# ---------------------------------------------------------------------------


def _classify_binding(intended: dict, by_name: dict, live: set, ev: str) -> list[Finding]:
    """DRIFT-BINDING — governed name points to wrong or absent target."""
    found = []
    for name, b in intended.get("bindings", {}).items():
        recs = [r for r in by_name.get(name, []) if r["type"] in ("A", "AAAA", "CNAME", "ALIAS")]
        if not recs:
            continue
        targets = {r.get("value") for r in recs}
        if b["target"] not in targets:
            dead = all(t not in live for t in targets)
            found.append(
                Finding(
                    plane="addressing",
                    name=name,
                    drift_class="DRIFT-BINDING",
                    severity=Severity.P1 if dead else Severity.P2,
                    posture=Posture.NEVER_AUTOFIX if dead else Posture.PER_POLICY,
                    intended=f"{b['type']} -> {b['target']}",
                    observed=", ".join(sorted(str(t) for t in targets))
                    + (" (target absent: takeover exposure)" if dead else ""),
                    evidence_ref=ev,
                )
            )
    return found


def _classify_dangling(intended: dict, zone: list, resources: dict, ev: str) -> list[Finding]:
    """DRIFT-DANGLING — ungoverned record pointing at an absent resource."""
    found = []
    live = set(resources.get("ips", [])) | set(resources.get("hosts", []))
    governed = set(intended.get("bindings", {}))
    for r in zone:
        if r["name"] in governed:
            continue  # governed names handled by _classify_binding (no double-count)
        target = r.get("value", "")
        if r["type"] in ("A", "AAAA") and target not in live:
            found.append(_dangling(r, target, ev))
        elif r["type"] in ("CNAME", "ALIAS", "MX") and target and target not in live:
            # MX dangling is a spoofing/takeover vector identical in risk to A.
            found.append(_dangling(r, target, ev))
    return found


def _dangling(r: dict, target: str, ev: str) -> Finding:
    return Finding(
        plane="addressing",
        name=r["name"],
        drift_class="DRIFT-DANGLING",
        severity=Severity.P1,
        posture=Posture.NEVER_AUTOFIX,
        intended="target resolves to an existing governed resource",
        observed=f"{r['type']} -> {target} (resource absent: takeover exposure)",
        evidence_ref=ev,
    )


def _classify_shadow(intended: dict, by_name: dict, ev: str) -> list[Finding]:
    """DRIFT-SHADOW — record present in zone but absent from SSOT registry."""
    found = []
    governed = set(intended.get("bindings", {}))
    covered = governed | set(intended.get("system_names", []))
    for name, recs in by_name.items():
        if name in covered or name.startswith("_") or name.startswith("*."):
            continue
        sev = Severity.P1 if name in governed else Severity.P2
        found.append(
            Finding(
                plane="addressing",
                name=name,
                drift_class="DRIFT-SHADOW",
                severity=sev,
                posture=Posture.NEVER_AUTOFIX,
                intended="name present in SSOT registry",
                observed=f"out-of-band record(s): {sorted({r['type'] for r in recs})}",
                evidence_ref=ev,
            )
        )
    return found


def _classify_srv(intended: dict, by_name: dict, resources: dict, ev: str) -> list[Finding]:
    """DRIFT-SRV — critical Kerberos/LDAP/GC service-locator record missing or dead."""
    found = []
    live = set(resources.get("hosts", []))
    required = set(intended.get("required_srv", [])) | CRITICAL_SRV
    for srv in required:
        hits = [n for n in by_name if n.startswith(srv)]
        if not hits:
            found.append(
                Finding(
                    plane="addressing",
                    name=srv,
                    drift_class="DRIFT-SRV",
                    severity=Severity.P1,
                    posture=Posture.NEVER_AUTOFIX,
                    intended="critical service-locator record present",
                    observed="missing (auth-breaking)",
                    evidence_ref=ev,
                )
            )
            continue
        for n in hits:
            for r in by_name[n]:
                tgt = (r.get("target") or r.get("value") or "").split()[-1]
                if tgt and tgt not in live:
                    found.append(
                        Finding(
                            plane="addressing",
                            name=n,
                            drift_class="DRIFT-SRV",
                            severity=Severity.P1,
                            posture=Posture.NEVER_AUTOFIX,
                            intended="SRV target is a live host",
                            observed=f"-> {tgt} (host absent)",
                            evidence_ref=ev,
                        )
                    )
    return found


def _classify_conflict(by_name: dict, ev: str) -> list[Finding]:
    """DRIFT-CONFLICT — CNAME coexists with other record types (RFC 1034/2181 violation)."""
    found = []
    for name, recs in by_name.items():
        types = {r["type"] for r in recs}
        if "CNAME" in types and types - {"CNAME"}:
            found.append(
                Finding(
                    plane="addressing",
                    name=name,
                    drift_class="DRIFT-CONFLICT",
                    severity=Severity.P1,
                    posture=Posture.NEVER_AUTOFIX,
                    intended="CNAME is the sole record at this name",
                    observed=f"CNAME coexists with {sorted(types - {'CNAME'})} (undefined resolution)",
                    evidence_ref=ev,
                )
            )
    return found


def _classify_wildcard(intended: dict, by_name: dict, ev: str) -> list[Finding]:
    """DRIFT-WILDCARD — a wildcard masks an intended-specific name that is absent."""
    found = []
    wildcards = [n for n in by_name if n.startswith("*.")]
    for w in wildcards:
        suffix = w[1:]  # ".corp.example.gov"
        for name, b in intended.get("bindings", {}).items():
            if name.endswith(suffix) and name not in by_name:
                found.append(
                    Finding(
                        plane="addressing",
                        name=name,
                        drift_class="DRIFT-WILDCARD",
                        severity=Severity.P2,
                        posture=Posture.PER_POLICY,
                        intended=f"explicit record -> {b['target']}",
                        observed=f"absent; masked by wildcard {w}",
                        evidence_ref=ev,
                    )
                )
    return found


def _classify_orphan(intended: dict, ev: str) -> list[Finding]:
    """DRIFT-ORPHAN — zone has zero referencing bindings (retirement candidate)."""
    found = []
    for zone, meta in intended.get("zones", {}).items():
        if meta.get("ref_count", 0) == 0:
            found.append(
                Finding(
                    plane="addressing",
                    name=zone,
                    drift_class="DRIFT-ORPHAN",
                    severity=Severity.P3,
                    posture=Posture.INFORMATIONAL,
                    intended="zone referenced by >=1 binding",
                    observed="zero referencing bindings (retirement candidate)",
                    evidence_ref=ev,
                )
            )
    return found


def _classify_ptr(intended: dict, by_name: dict, ev: str) -> list[Finding]:
    """DRIFT-PTR — name requires FCrDNS but no matching PTR exists."""
    found = []
    ptrs = {r["value"].rstrip(".") for recs in by_name.values() for r in recs if r["type"] == "PTR"}
    for name, b in intended.get("bindings", {}).items():
        if b.get("requires_fcrdns") and name not in ptrs:
            found.append(
                Finding(
                    plane="addressing",
                    name=name,
                    drift_class="DRIFT-PTR",
                    severity=Severity.P2,
                    posture=Posture.PER_POLICY,
                    intended="forward-confirmed reverse (PTR) present",
                    observed="no matching PTR",
                    evidence_ref=ev,
                )
            )
    return found


# ---------------------------------------------------------------------------
# Deferred (observation-heavy) classes — declared, not implemented
# ---------------------------------------------------------------------------

DEFERRED: dict[str, str] = {
    "DRIFT-HORIZON": "multi-vantage resolution probe (internal + external + per-VNet)",
    "DRIFT-CAA/TLSA": "endpoint cert inspection + CAA read against governed CA set",
    "DRIFT-DELEGATION": "parent-NS delegation walk + glue validation",
}


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def run(
    intended_path: str | Path,
    zone_path: str | Path,
    resources_path: str | Path,
) -> tuple[list[Finding], dict]:
    intended = _load_dict(intended_path)
    zone = _load_list(zone_path)
    resources = _load_dict(resources_path)

    by_name = _records_by_name(zone)
    ev = f"file:{Path(zone_path).name}"
    live = set(resources.get("ips", [])) | set(resources.get("hosts", []))

    findings: list[Finding] = []
    findings += _classify_binding(intended, by_name, live, ev)
    findings += _classify_dangling(intended, zone, resources, ev)
    findings += _classify_shadow(intended, by_name, ev)
    findings += _classify_srv(intended, by_name, resources, ev)
    findings += _classify_conflict(by_name, ev)
    findings += _classify_wildcard(intended, by_name, ev)
    findings += _classify_orphan(intended, ev)
    findings += _classify_ptr(intended, by_name, ev)

    return findings, gate(findings)


def report(findings: list[Finding], g: dict) -> None:
    order = {Severity.P1: 0, Severity.P2: 1, Severity.P3: 2}
    print(f"GATE: {g['decision']}   P1={g['counts']['P1']}  P2={g['counts']['P2']}  P3={g['counts']['P3']}")
    print("-" * 78)
    for f in sorted(findings, key=lambda x: order[x.severity]):
        print(f"[{f.severity.value}] {f.drift_class:<18} {f.name}")
        print(f"      intended : {f.intended}")
        print(f"      observed : {f.observed}  ({f.posture.value})")
    print("-" * 78)
    print("DEFERRED (require observation beyond a zone-file read):")
    for cls, need in DEFERRED.items():
        print(f"  {cls:<18} needs: {need}")


if __name__ == "__main__":
    import argparse
    import os

    sample = Path(__file__).resolve().parent / "sample"

    parser = argparse.ArgumentParser(description="UIAO addressing-plane drift collector")
    parser.add_argument("--intended", default=os.environ.get("UIAO_INTENDED", str(sample / "intended_bindings.json")))
    parser.add_argument("--zone", default=os.environ.get("UIAO_ZONE", str(sample / "observed_zone.json")))
    parser.add_argument("--resources", default=os.environ.get("UIAO_RESOURCES", str(sample / "resources.json")))
    parser.add_argument(
        "--output", default=os.environ.get("UIAO_OUTPUT", str(Path(__file__).resolve().parent / "findings.json"))
    )
    args = parser.parse_args()

    findings, g = run(args.intended, args.zone, args.resources)
    report(findings, g)
    out = Path(args.output)
    out.write_text(events_json(findings), encoding="utf-8")
    print(f"\nFindings written to {out}")
    raise SystemExit(1 if g["decision"] == "HALT" else 0)
