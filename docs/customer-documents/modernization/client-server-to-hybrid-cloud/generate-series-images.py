#!/usr/bin/env python3
"""One-shot image generator for the Client-Server to Hybrid-Cloud series.

Generates the 11 figure images referenced in chapters 00..10 via Google's
Gemini API (Nano Banana image model). Saves PNGs to ./images/ with slugs
that match each chapter's markdown reference exactly.

Usage:
    # Windows PowerShell:
    $env:GEMINI_API_KEY = "<your-key>"
    cd docs\\customer-documents\\modernization\\client-server-to-hybrid-cloud
    python generate-series-images.py

    # macOS / Linux / bash:
    export GEMINI_API_KEY="<your-key>"
    cd docs/customer-documents/modernization/client-server-to-hybrid-cloud
    python generate-series-images.py

Options:
    --dry-run     Report what would be generated; no API calls.
    --force       Regenerate even if the PNG already exists.
    --only SLUG   Generate only the single image matching SLUG
                  (e.g. --only 04-orgpath-fanout).

Dependencies:
    pip install google-genai

Idempotent: an existing PNG is skipped unless --force is passed.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# ── configuration ────────────────────────────────────────────────────────

MODEL = "gemini-2.5-flash-image"

# Shared style header prepended to every prompt so the series has one
# consistent aesthetic. Matches the UIAO visual-language rules recorded
# in IMAGE-PROMPTS.md.
STYLE_HEADER = (
    "Style: clean, federal, McKinsey-grade editorial infographic. "
    "Flat vector with subtle depth; neutral slate + federal navy "
    "(#1F3A5F) accents; soft teal highlights; white background; no "
    "gradients. No people. No Microsoft or vendor logos. Widescreen "
    "16:9 aspect ratio. Small readable sans-serif text labels on "
    "elements; monospace for canon identifiers (MOD_A..Z, DM_010..090, "
    "OrgPath values like ORG-FIN-AP). Government-appropriate; no "
    "marketing gloss. Scene: "
)

# Per-image prompts. slug is the filename stem; prompt is appended after
# STYLE_HEADER. Order matches chapter order 00..10.
IMAGES: list[tuple[str, str]] = [
    (
        "00-ad-hidden-governance-surface",
        "Active Directory at the center of an enterprise governance "
        "surface. A single solid navy rounded rectangle labeled "
        "'Active Directory Domain Services' in the middle. Eleven thin "
        "curved lines radiate outward to eleven labeled leaves arranged "
        "evenly in a circle around it. Each leaf is a small rounded "
        "rectangle containing a category name and a one-line descriptor. "
        "The eleven categories clockwise from top: Users (identity "
        "lifecycle); Computers (domain join, GPO targeting); Service "
        "Accounts (SPNs, Kerberos delegation); Security Groups (access "
        "control, policy scoping); Group Policy Objects (device "
        "configuration); DNS / DHCP (name resolution, IP allocation); "
        "PKI / Certificate Services (certificate issuance); RADIUS / NPS "
        "(802.1X, VPN authentication); LDAP (application authentication); "
        "SPNs / App Registrations (Kerberos service identity); Trust "
        "Relationships (cross-domain authentication).",
    ),
    (
        "01-platform-server-five-roles",
        "A single large rounded-rectangle host labeled 'UIAO-GIT01 · "
        "Windows Server 2025 · Tier-0'. Inside the host, five "
        "horizontally arranged panels, each a distinct role: (1) "
        "'Canonical Source of Truth' with a Gitea mark and a small Git "
        "commit-graph icon; (2) 'HTTPS Reverse Proxy + Client-Cert "
        "Terminator' with an IIS label and a lock-with-certificate icon; "
        "(3) 'Legacy-to-Modern Auth Bridge' with two adjacent badges — "
        "'AD Kerberos (read-only)' and 'Entra OIDC (read-write)'; (4) "
        "'Transformation Engine Host' showing three stacked pills — "
        "PowerShell, Python, API Integrators; (5) 'Adapter Dispatcher' "
        "showing labels 'DM_010..080' and 'MOD_I'. External connectors "
        "extend to small outline boxes around the perimeter labeled "
        "AD Forest, Entra ID, Intune, Azure Arc, Infoblox.",
    ),
    (
        "02-assessment-ingestion-pipeline",
        "A left-to-right pipeline diagram. Left: a labeled cylinder "
        "'Client / Server AD Forest' with a small 'Tier B access' badge. "
        "Middle: eleven parallel horizontal lanes, each a rounded "
        "rectangle stream labeled top to bottom: Forest + Domain "
        "topology, OU hierarchy, Users, Computers, Service Accounts + "
        "SPNs, Groups, GPOs, DNS Zones, DHCP Scopes, ADCS / PKI, LDAP "
        "Bindings + Kerberos SPN Map. Each lane passes through two "
        "small process boxes — 'PowerShell (UIAOADAssessment)' then "
        "'Python (uiao.assess.graph)'. Right: a labeled folder-tree "
        "rendering of 'assessments/<run-id>/' with 'provenance.yaml' at "
        "the top, and a small lock icon labeled 'signed' over the folder.",
    ),
    (
        "03-analyze-plan-deliver",
        "A three-stage horizontal pipeline. Stage 1 'Analyze' (labeled "
        "brain: 'Copilot · governance') shows four sub-outputs: "
        "current-state graph, target-state graph, diff, risk score. "
        "Stage 2 'Plan' (same brain) shows a small YAML action-list "
        "preview with 3-4 sample actions (type: create-administrative"
        "-unit, type: assign-role-scoped) and a 'MOD_J validated' stamp. "
        "Stage 3 'Deliver' (labeled brain: 'Execution Substrate · "
        "execution') shows vendor-API call icons (Graph, ARM, Infoblox "
        "WAPI) and an evidence packet on the far right. A bold vertical "
        "dashed line between Stage 2 and Stage 3 labeled 'Two-Brain "
        "handoff · authorized plan only'. Federal navy for the "
        "governance brain; soft teal for the execution brain.",
    ),
    (
        "04-orgpath-fanout",
        "A user object in the center (simple abstract head-and-shoulders "
        "outline), captioned with a monospace tag 'extensionAttribute1 "
        "= ORG-FIN-AP-EAST'. Five labeled arrows radiate outward to "
        "five downstream effects: (1) Dynamic Group Membership → "
        "'OrgTree-FIN-AP-Users' with a group icon; (2) Administrative "
        "Unit Scope → 'AU-ORG-FIN-AP' with a scope icon; (3) "
        "Conditional Access Targeting → a CA policy badge; (4) "
        "Group-Based License Assignment → a license SKU badge; (5) "
        "Drift Detection (MOD_M) → a comparator icon. Below the figure, "
        "a single-line footer: 'One attribute. Five governance outcomes. "
        "Zero admin-portal clicks.'",
    ),
    (
        "05-gpo-retirement-map",
        "A two-column mapping diagram. Left column: six stacked legacy "
        "GPO category boxes in pale slate — Device Configuration, "
        "Security Baselines, Software Deployment, Access Control, "
        "Server Configuration, Browser / Mailbox Config. Right column: "
        "six corresponding modern target boxes — Intune Configuration "
        "Profiles; Intune Security Baselines + Entra Auth Methods; "
        "Intune Win32 Apps + Autopilot; Conditional Access + Entra "
        "Session Controls; Azure Arc Guest Configuration + Azure "
        "Policy; Intune Settings Catalog + Office 365 Policies. One "
        "horizontal arrow per row labeled 'regenerate, not copy'. A "
        "dashed border around the right column labeled 'OrgPath-scoped "
        "targeting — every profile targets OrgTree dynamic groups'.",
    ),
    (
        "06-hybrid-dns-topology",
        "A three-column topology diagram. Left column 'On-prem "
        "namespace': three sample records — UIAO-GIT01.corp, "
        "fileserver.corp, printer.corp — each a small host icon. Middle "
        "column 'Hybrid path': a large rounded rectangle labeled 'Azure "
        "DNS Private Resolver' with two labeled endpoints — 'inbound "
        "endpoint' (arrow from left) and 'outbound endpoint' (arrow "
        "from right). Below it, a Private DNS Zone box 'uiao.internal "
        "(authoritative)'. Right column 'Cloud namespace': a record "
        "'privatelink.blob.core.windows.net' with a generic cloud-"
        "storage icon. Below the figure, a single horizontal band "
        "labeled 'IPAM (DM_010) · single source of truth' with arrows "
        "up into both Private DNS Zone and DHCP-scope records.",
    ),
    (
        "07-device-state-transitions",
        "A state-transition diagram with five labeled states as rounded "
        "rectangles: 'Domain-Joined (legacy)' far left; 'Azure AD "
        "Registered' at top; 'Entra Hybrid Joined (transition, not "
        "destination)' rendered with a dashed border and a small "
        "warning glyph; 'Entra Joined (target for user PCs)' far right "
        "with a solid checkmark; 'Arc-connected server (target for "
        "servers)' below, offset. Labeled directed arrows between "
        "states show three migration patterns: 'greenfield via "
        "Autopilot' (direct to Entra Joined); 'reset-and-re-enroll' "
        "(Domain-Joined to Entra Joined); 'hybrid-then-cloud' "
        "(Domain-Joined to Hybrid to Entra Joined). A dotted branch "
        "from any state to 'Arc-connected server' shows the server path.",
    ),
    (
        "08-morning-login-flow",
        "A vertical sequence diagram with seven numbered rounded-"
        "rectangle step panels, each with a short title: (1) Device "
        "boot — Intune compliance check, BitLocker unlock; (2) Sign-in "
        "— CAC + PIN, Entra CBA validates certificate chain, CAE-aware "
        "token issued; (3) Conditional Access evaluation — CA-100 "
        "baseline, four signals ticked (compliant device, CBA MFA, "
        "location, risk); (4) Application access — M365 apps, Platform "
        "SSO satisfies subsequent auths; (5) VPN-replacement — SASE "
        "ZTNA reverse-proxy to on-prem app; (6) Privileged elevation "
        "— PIM request, FIDO2 re-challenge, CyberArk session recording, "
        "MOD_X telemetry; (7) End of day — token expires, CAE revokes. "
        "On the right side, a narrow vertical rail labeled 'OrgPath-"
        "scoped · provenance-bound · drift-monitored' running full height.",
    ),
    (
        "09-program-gantt",
        "A Gantt-style program timeline spanning 52 weeks on the "
        "horizontal axis. Along the top, seven labeled phase bands "
        "spanning the weeks: Phase 0 Pre-flight (wk 1-4), Phase 1 "
        "Foundation (5-8), Phase 2 Pilot Division (9-16), Phase 3 "
        "General Rollout (17-36), Phase 4 Legacy Retirement (37-44), "
        "Phase 5 AD DS Retirement (45-48), Phase 6 Steady State (49+). "
        "Below, five horizontal workstream lanes stacked vertically: "
        "Identity, Policy, Services, Compute, Access. Each lane has "
        "pale bars showing activity intensity per phase. Six vertical "
        "gate markers with thick lines labeled G0 through G5 at weeks "
        "4, 8, 16, 36, 44, 48.",
    ),
    (
        "10-instruments-vs-orchestra",
        "A stylized orchestra-stage illustration (diagrammatic, not "
        "photographic). Eight instruments arranged in classical "
        "orchestra seating, each labeled with a Microsoft-native tool: "
        "Entra ID (first violin), Intune (second violin), Azure Arc "
        "(cello), Conditional Access (viola), Azure PIM (double bass), "
        "ScubaGear (oboe), Azure Private Resolver (clarinet), Entra CBA "
        "(French horn). At the front center, a conductor's podium with "
        "an open score; the conductor rendered as the UIAO platform "
        "server icon (a rounded-rectangle WS2025 host) with a baton. "
        "The score is labeled with canon artifacts visible on its "
        "pages: MOD_A, MOD_B, MOD_D, MOD_M, DM_010, DM_020. Faint "
        "sheet-music staves flow from the score to each instrument, "
        "representing governed plans and evidence. Warm paper-tone "
        "palette on the stage floor; federal navy on the conductor.",
    ),
]


# ── runtime ──────────────────────────────────────────────────────────────


def build_client(api_key: str):
    """Import google-genai lazily so --dry-run works without the dep."""
    try:
        from google import genai  # type: ignore
    except ImportError:
        print(
            "ERROR: package 'google-genai' is not installed.\n"
            "  Run:  pip install google-genai",
            file=sys.stderr,
        )
        sys.exit(2)
    return genai.Client(api_key=api_key)


def generate_one(client, slug: str, prompt_body: str, out_path: Path) -> bool:
    """Generate a single image. Returns True on success, False otherwise."""
    full_prompt = STYLE_HEADER + prompt_body
    try:
        resp = client.models.generate_content(
            model=MODEL,
            contents=full_prompt,
        )
    except Exception as exc:  # noqa: BLE001 — surface any API error
        print(f"  [error] {slug}: {exc}", file=sys.stderr)
        return False

    # Nano Banana returns image bytes in inline_data parts.
    for cand in resp.candidates or []:
        for part in cand.content.parts:
            data = getattr(part, "inline_data", None)
            if data is not None and getattr(data, "data", None):
                out_path.write_bytes(data.data)
                print(f"  [ok]    {slug} → {out_path.name} ({len(data.data):,} bytes)")
                return True

    print(f"  [warn]  {slug}: no image part in response", file=sys.stderr)
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="report what would be generated; no API calls")
    ap.add_argument("--force", action="store_true", help="regenerate even if output exists")
    ap.add_argument("--only", metavar="SLUG", help="generate only the single image matching SLUG")
    args = ap.parse_args()

    here = Path(__file__).parent.resolve()
    out_dir = here / "images"
    out_dir.mkdir(exist_ok=True)

    targets = IMAGES
    if args.only:
        targets = [t for t in IMAGES if t[0] == args.only]
        if not targets:
            print(f"ERROR: --only slug '{args.only}' not in the image set.", file=sys.stderr)
            print("Known slugs:", file=sys.stderr)
            for slug, _ in IMAGES:
                print(f"  {slug}", file=sys.stderr)
            return 2

    print(f"Target images: {len(targets)}")
    print(f"Output folder: {out_dir}")
    print(f"Model:         {MODEL}")
    print()

    if args.dry_run:
        for slug, _ in targets:
            status = "exists" if (out_dir / f"{slug}.png").exists() else "would-generate"
            print(f"  [{status}] {slug}.png")
        return 0

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY environment variable is not set.", file=sys.stderr)
        return 2

    client = build_client(api_key)

    generated = 0
    skipped = 0
    failed = 0

    for slug, prompt_body in targets:
        out_path = out_dir / f"{slug}.png"
        if out_path.exists() and not args.force:
            print(f"  [skip]  {slug}: already exists (use --force to regenerate)")
            skipped += 1
            continue
        ok = generate_one(client, slug, prompt_body, out_path)
        if ok:
            generated += 1
        else:
            failed += 1

    print()
    print(f"Summary: generated={generated}  skipped={skipped}  failed={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
