You're asking for the whole thing wired, not hand‑wavy theory---so let's
treat this like a real feature track being added to an existing product.

I'll assume a "typical" UIAO layout (root uiao/ with tracks/,
artifacts/, registries/, runbooks/, docs/, scripts/). Where something
doesn't exist, I'll extend the closest existing structure rather than
invent a parallel one.

**1. Development Tree and integration strategy**

**Goal:** Add an *Intune / Entra ID / Azure Arc Modernization Track*
**inside** the existing UIAO tree, reusing global artifacts/,
registries/, runbooks/, docs/, and scripts/ rather than duplicating
them.

**Integration pattern:**

- **Tracks:**

  - If you already have tracks/modernization/ or similar, add:

    - tracks/modernization/entra_intune_arc/track.md (index)

  - If not, add under tracks/ only (no new top‑level root).

- **Artifacts:**

  - New artifacts go into the **existing global artifacts/ folder**,
    using your canonical IDs.

  - No new artifacts/entra_intune_arc/ subtree---just more artifacts
    with consistent IDs.

- **Registries:**

  - Reuse global registries/identity/, registries/device/,
    registries/server/.

  - Add new CSVs only where there is no existing registry with the same
    purpose.

- **Runbooks / docs / scripts:**

  - Reuse runbooks/, docs/, scripts/ at root; add new files with clear
    names, not new parallel trees.

**2. Concrete Development Tree (what we're adding)**

Assuming repo root is uiao/:

uiao/

├── tracks/

│ └── modernization/

│ └── entra_intune_arc/

│ └── track.md

├── artifacts/

│ ├── ART-ID-E1_identity_dependency_map.md

│ ├── ART-ID-E2_directory_sync_design.md

│ ├── ART-ID-E3_authentication_method_plan.md

│ ├── ART-ID-E4_conditional_access_baseline_set.md

│ ├── ART-ID-E5_sso_migration_catalog.md

│ ├── ART-ID-E6_app_proxy_publishing_plan.md

│ ├── ART-DV-I1_gpo_inventory_export.md

│ ├── ART-DV-I2_gpo_to_intune_mapping_matrix.md

│ ├── ART-DV-I3_intune_configuration_baseline.md

│ ├── ART-DV-I4_device_compliance_model.md

│ ├── ART-DV-I5_autopilot_deployment_plan.md

│ ├── ART-DV-I6_app_deployment_model.md

│ ├── ART-SR-A1_arc_onboarding_plan.md

│ ├── ART-SR-A2_arc_policy_baseline.md

│ ├── ART-SR-A3_arc_extension_deployment_plan.md

│ ├── ART-SR-A4_managed_identity_adoption_plan.md

│ ├── ART-SR-A5_server_domain_dependency_map.md

│ └── ART-ID-ORGPATH_orgpath_dependency_graph.md

├── registries/

│ ├── identity/

│ │ ├── REG-ID-01_auth_dependencies.csv

│ │ ├── REG-ID-02_conditional_access.csv

│ │ ├── REG-ID-03_sso_migration.csv

│ │ └── REG-ID-ORGPATH_orgpath.csv

│ ├── device/

│ │ ├── REG-DV-01_gpo_mapping.csv

│ │ ├── REG-DV-02_device_cohorts.csv

│ │ └── REG-DV-03_app_deployment.csv

│ └── server/

│ ├── REG-SR-01_arc_onboarding.csv

│ ├── REG-SR-02_arc_policy_compliance.csv

│ └── REG-SR-03_domain_dependency_retirement.csv

├── runbooks/

│ ├── RB-ID-sync_deploy.md

│ ├── RB-DV-intune_profile_deploy.md

│ ├── RB-DV-autopilot_provisioning.md

│ ├── RB-SR-arc_onboard.md

│ └── RB-ID-ORGPATH_orgpath_etl.md

├── docs/

│ └── track_intune_entra_arc.qmd

└── scripts/

├── registry_cli.py

└── registry_wrapper.ps1

If any of those files already exist with the same purpose, we **extend**
them instead of adding new ones.

**3. Map every UIAO artifact to Microsoft tools**

Here's the mapping you asked for---UIAO artifact → Microsoft tool(s) →
how it's used in the AD→Entra/Intune/Arc transformation.

  --------------------------------------------------------------------------------------------------
  **Artifact ID**      **Artifact       **Microsoft tool(s)**   **How it's used in the plan**
                       name**
  -------------------- ---------------- ----------------------- ------------------------------------
  **ART‑ID‑E1**        Identity         Entra ID sign‑in logs,  Discover apps/services using
                       Dependency Map   AD DS logs, Defender    AD/LDAP/NTLM/Kerberos; feed
                                        for Cloud Apps          REG‑ID‑01 and OrgPath.

  **ART‑ID‑E2**        Directory Sync   Microsoft Entra Connect Define sync topology, attribute
                       Design           / Entra Cloud Sync      flows, writeback, HA; governs
                                                                AD→Entra identity.

  **ART‑ID‑E3**        Authentication   Entra ID                Choose auth model, MFA, risk
                       Method Plan      (PHS/PTA/Federation),   policies, password reset; sequence
                                        Entra ID Protection,    cutover.
                                        SSPR

  **ART‑ID‑E4**        Conditional      Entra Conditional       Define baseline CA policies,
                       Access Baseline  Access, Intune          report‑only → enforce waves.
                       Set              compliance signals

  **ART‑ID‑E5**        SSO Migration    Entra Enterprise Apps,  Migrate apps from LDAP/AD FS/basic
                       Catalog          Entra App Proxy, AD FS  auth to SAML/OIDC/App Proxy.
                                        (source)

  **ART‑ID‑E6**        App Proxy        Entra Application Proxy Publish on‑prem apps securely
                       Publishing Plan                          without VPN; integrate with CA.

  **ART‑DV‑I1**        GPO Inventory    Group Policy Management Export GPOs, feed mapping to Intune.
                       Export           Console, Group Policy
                                        Analytics

  **ART‑DV‑I2**        GPO→Intune       Group Policy Analytics, Classify each GPO setting as
                       Mapping Matrix   Intune configuration    Direct/Partial/Unsupported/Retire.
                                        profiles

  **ART‑DV‑I3**        Intune           Microsoft Intune        Implement mapped policies as config
                       Configuration                            profiles and baselines.
                       Baseline

  **ART‑DV‑I4**        Device           Intune compliance       Define compliance rules and CA
                       Compliance Model policies, Entra         integration.
                                        Conditional Access

  **ART‑DV‑I5**        Autopilot        Windows Autopilot,      Plan cohorts, profiles, and rollout
                       Deployment Plan  Intune enrollment       waves for Entra‑joined devices.

  **ART‑DV‑I6**        App Deployment   Intune app deployment   Package and deploy apps to devices;
                       Model            (Win32/MSIX/Store),     replace legacy software
                                        Company Portal          distribution.

  **ART‑SR‑A1**        Arc Onboarding   Azure Arc agent, Azure  Onboard servers to Arc; define
                       Plan             portal                  cohorts and tagging.

  **ART‑SR‑A2**        Arc Policy       Azure Policy, Defender  Apply policy initiatives to Arc
                       Baseline         for Cloud               servers; enforce
                                                                configuration/security.

  **ART‑SR‑A3**        Arc Extension    Azure Arc extensions    Deploy monitoring/security agents to
                       Deployment Plan  (Log Analytics,         Arc servers.
                                        Defender, etc.)

  **ART‑SR‑A4**        Managed Identity Managed Identities, Key Replace service accounts/secrets
                       Adoption Plan    Vault, Entra service    with MI.
                                        principals

  **ART‑SR‑A5**        Server Domain    Azure Arc, AD DS, GPO,  Map server dependencies on AD; plan
                       Dependency Map   file services           domain retirement.

  **ART‑ID‑ORGPATH**   OrgPath          Custom ETL + Entra/AD   Build the "missing" cross‑system
                       Dependency Graph logs + Defender for     dependency graph Microsoft doesn't
                                        Cloud Apps              give you.
  --------------------------------------------------------------------------------------------------

**4. OrgPath as the missing Microsoft capability**

**Purpose:** OrgPath fills the gap between Microsoft's point tools by
building a **cross‑plane dependency graph**: identity → device → server
→ app → data.

- **Artifact:** ART-ID-ORGPATH_orgpath_dependency_graph.md

- **Registry:** REG-ID-ORGPATH_orgpath.csv

**How it works (method):**

1.  **Ingest sources:**

    - Entra sign‑in logs (who accessed what, from where).

    - AD DS security logs (LDAP binds, Kerberos tickets).

    - Defender for Cloud Apps (cloud app usage, Shadow IT).

    - Arc/Intune inventories (which devices/servers are managed).

2.  **Normalize into REG‑ID‑ORGPATH:**

> CSV header:
>
> NodeID,NodeType,Name,Source,Owner,DependsOn,DependencyType,Confidence,Notes

- NodeType: User, App, Server, Device, Group, Policy, Share, DB.

- DependsOn: comma‑separated NodeIDs.

3.  **Generate graph:**

    - Python script in scripts/orgpath_build.py reads all registries and
      emits orgpath.graphml or orgpath.puml.

    - Diagrams go into diagrams/orgpath\_\*.puml.

4.  **Use in planning:**

    - Identify "blast radius" of retiring AD DS or a specific GPO.

    - Prioritize which apps/servers must be migrated before domain
      controllers can be decommissioned.

**5. Mapping LDAP‑dependent apps to Entra‑based replacements**

**Goal:** For each app that currently uses LDAP/NTLM/Kerberos against
AD, define its Entra‑based future state.

**Method (stepwise):**

1.  **Discover LDAP usage:**

    - Use DC logs (LDAP bind events), network captures, and app configs
      to populate REG-ID-01_auth_dependencies.csv with:

      - ItemType=App, Protocol=LDAP, AuthPattern=SimpleBind or SASL,
        SourceHost, TargetHost, Port.

2.  **Classify each app:**

    - **Category A:** Web app that can support SAML/OIDC → target Entra
      Enterprise App.

    - **Category B:** On‑prem web app without modern auth → target Entra
      App Proxy + header‑based auth or custom adapter.

    - **Category C:** Legacy thick client using LDAP directly → target:

      - Replace with modern app, or

      - Isolate behind secure LDAP gateway, or

      - Keep AD DS in a reduced, isolated footprint.

3.  **Record migration plan in REG-ID-03_sso_migration.csv:**

4.  AppID,AppName,Owner,CurrentAuth,TargetAuth,AppProxyCandidate,SAMLConfig,OIDCConfig,TestCases,MigrationState,Priority,Notes

    - CurrentAuth: LDAP, NTLM, Kerberos, Basic, AD FS.

    - TargetAuth: SAML, OIDC, AppProxy, "RemainOnAD" (only if absolutely
      necessary).

5.  **Update OrgPath:**

    - For each app, add NodeType=App and DependsOn entries pointing to
      AD DS, GPOs, servers, and users.

    - As you migrate, update DependsOn to Entra/Intune/Arc nodes instead
      of AD DS.

**6. GitHub build plan in exact order**

This is the sequence I'd follow to build this into your existing repo.

**Step 1 --- Create feature branch**

git checkout -b feature/track_intune_entra_arc

**Step 2 --- Add track index**

Create tracks/modernization/entra_intune_arc/track.md with:

- Purpose, scope, phases (Discover → Design → Pilot → Migrate → Retire).

- Links to artifacts, registries, runbooks, docs.

**Step 3 --- Add artifacts (empty templates)**

For each artifact ID above, create a file in artifacts/ with:

Artifact ID: ART-ID-E2

Name: Directory Sync Design

Version: 0.1

Owner: MISSING

Status: DRAFT

Purpose

\...

Scope

\...

Microsoft Tools

\- Microsoft Entra Connect

\- Entra Cloud Sync

Inputs

\...

Outputs

\...

Structure

1\. \...

(You already have most of these templates; this step is just adding them
to the repo in the right place.)

**Step 4 --- Add registries (CSV headers only)**

Create or extend:

- registries/identity/REG-ID-01_auth_dependencies.csv

- registries/identity/REG-ID-02_conditional_access.csv

- registries/identity/REG-ID-03_sso_migration.csv

- registries/identity/REG-ID-ORGPATH_orgpath.csv

- registries/device/REG-DV-01_gpo_mapping.csv

- registries/device/REG-DV-02_device_cohorts.csv

- registries/device/REG-DV-03_app_deployment.csv

- registries/server/REG-SR-01_arc_onboarding.csv

- registries/server/REG-SR-02_arc_policy_compliance.csv

- registries/server/REG-SR-03_domain_dependency_retirement.csv

Each with the headers we defined earlier.

**Step 5 --- Add OrgPath ETL script and runbook**

- scripts/orgpath_build.py --- reads all registries, writes
  orgpath.graphml.

- runbooks/RB-ID-ORGPATH_orgpath_etl.md --- step‑by‑step instructions to
  run ETL and interpret results.

**Step 6 --- Add registry CLI and PowerShell wrapper**

- scripts/registry_cli.py --- simple Python CLI to add/update/export
  registry rows.

- scripts/registry_wrapper.ps1 --- PowerShell wrapper that calls
  registry_cli.py with add, update, export.

**Step 7 --- Add Quarto track doc**

- docs/track_intune_entra_arc.qmd --- track overview, phases,
  artifact/registry list, and integration points.

**Step 8 --- Commit and push**

git add tracks/modernization/entra_intune_arc \\

artifacts \\

registries \\

runbooks \\

docs/track_intune_entra_arc.qmd \\

scripts/registry_cli.py \\

scripts/registry_wrapper.ps1

git commit -m \"Add Intune/Entra/Arc modernization track (artifacts,
registries, OrgPath, CLI)\"

git push -u origin feature/track_intune_entra_arc

**7. Commit‑ready file skeletons (no greenfield duplication)**

Here are minimal, safe skeletons you can drop in **as‑is** and then fill
out.

**Example artifact skeleton (ART‑ID‑E2)**

Artifact ID: ART-ID-E2

Name: Directory Sync Design

Version: 0.1

Owner: MISSING

Status: DRAFT

Purpose

Describe the Microsoft Entra Connect / Entra Cloud Sync design for
synchronizing on-premises AD identities to Entra ID.

Scope

All AD forests and domains in scope for Entra ID synchronization.

Microsoft Tools

\- Microsoft Entra Connect

\- Microsoft Entra Cloud Sync

Inputs

\- ART-ID-E1 Identity Dependency Map

\- AD forest topology

\- Compliance requirements

Outputs

\- Runbook: RB-ID-sync_deploy.md

\- Config: sync_config.json

\- Diagram: sync_topology.puml

Structure

1\. Executive summary

2\. Tool selection (Connect vs Cloud Sync)

3\. Topology and HA

4\. Attribute flows and scoping

5\. Security and monitoring

6\. Cutover and rollback

Change log

\- v0.1 created by MISSING

**Example registry header (REG‑ID‑01)**

ItemID,ItemType,Name,Owner,Protocol,SourceHost,TargetHost,Port,AuthPattern,NTLMUsage,KerberosUsage,LDAPBind,ADFS,MigrationState,Priority,Notes

**Example OrgPath registry header (REG‑ID‑ORGPATH)**

NodeID,NodeType,Name,Source,Owner,DependsOn,DependencyType,Confidence,Notes

**Example PowerShell wrapper skeleton (registry_wrapper.ps1)**

param(

\[Parameter(Mandatory=\$true)\]\[string\]\$RegistryId,

\[Parameter(Mandatory=\$true)\]\[ValidateSet(\"add\",\"update\",\"export\")\]\[string\]\$Action,

\[string\]\$Key,

\[string\]\$Value,

\[string\]\$Payload

)

\$scriptDir = Split-Path -Parent \$MyInvocation.MyCommand.Definition

\$pythonCli = Join-Path \$scriptDir \"registry_cli.py\"

\$pythonCli = (Resolve-Path \$pythonCli).Path

function Run-Python {

param(\$args)

\$proc = Start-Process -FilePath python -ArgumentList \$args
-NoNewWindow -Wait -PassThru

if (\$proc.ExitCode -ne 0) {

throw \"Python CLI failed with exit code \$(\$proc.ExitCode)\"

}

}

switch (\$Action) {

\"add\" {

if (-not \$Payload) { throw \"Payload is required for add action\" }

\$args = \"\`\"\$pythonCli\`\" add \--registry \`\"\$RegistryId\`\"
\--entry \`\"\$Payload\`\"\"

Run-Python \$args

}

\"update\" {

if (-not (\$Key -and \$Value -and \$Payload)) { throw \"Key, Value, and
Payload are required for update action\" }

\$args = \"\`\"\$pythonCli\`\" update \--registry \`\"\$RegistryId\`\"
\--key \`\"\$Key\`\" \--value \`\"\$Value\`\" \--updates
\`\"\$Payload\`\"\"

Run-Python \$args

}

\"export\" {

\$args = \"\`\"\$pythonCli\`\" export \--registry \`\"\$RegistryId\`\"\"

Run-Python \$args

}

}

two minimal, drop‑in Python scripts.

**1. scripts/registry_cli.py**

**Minimal, CSV‑based, no external deps**

#!/usr/bin/env python3

import argparse

import csv

import json

import os

import sys

from typing import Dict, List

\# Map RegistryId -\> relative CSV path

REGISTRY_MAP: Dict\[str, str\] = {

\"REG-ID-01\": os.path.join(\"registries\", \"identity\",
\"REG-ID-01_auth_dependencies.csv\"),

\"REG-ID-02\": os.path.join(\"registries\", \"identity\",
\"REG-ID-02_conditional_access.csv\"),

\"REG-ID-03\": os.path.join(\"registries\", \"identity\",
\"REG-ID-03_sso_migration.csv\"),

\"REG-ID-ORGPATH\": os.path.join(\"registries\", \"identity\",
\"REG-ID-ORGPATH_orgpath.csv\"),

\"REG-DV-01\": os.path.join(\"registries\", \"device\",
\"REG-DV-01_gpo_mapping.csv\"),

\"REG-DV-02\": os.path.join(\"registries\", \"device\",
\"REG-DV-02_device_cohorts.csv\"),

\"REG-DV-03\": os.path.join(\"registries\", \"device\",
\"REG-DV-03_app_deployment.csv\"),

\"REG-SR-01\": os.path.join(\"registries\", \"server\",
\"REG-SR-01_arc_onboarding.csv\"),

\"REG-SR-02\": os.path.join(\"registries\", \"server\",
\"REG-SR-02_arc_policy_compliance.csv\"),

\"REG-SR-03\": os.path.join(\"registries\", \"server\",
\"REG-SR-03_domain_dependency_retirement.csv\"),

}

def load_rows(path: str) -\> List\[Dict\[str, str\]\]:

if not os.path.exists(path):

return \[\]

with open(path, newline=\"\", encoding=\"utf-8\") as f:

reader = csv.DictReader(f)

return list(reader)

def save_rows(path: str, rows: List\[Dict\[str, str\]\], fieldnames:
List\[str\]) -\> None:

os.makedirs(os.path.dirname(path), exist_ok=True)

with open(path, \"w\", newline=\"\", encoding=\"utf-8\") as f:

writer = csv.DictWriter(f, fieldnames=fieldnames)

writer.writeheader()

for r in rows:

writer.writerow(r)

def get_fieldnames(path: str, rows: List\[Dict\[str, str\]\]) -\>
List\[str\]:

if rows:

return list(rows\[0\].keys())

if os.path.exists(path):

with open(path, newline=\"\", encoding=\"utf-8\") as f:

reader = csv.reader(f)

header = next(reader, None)

if header:

return header

raise SystemExit(f\"Cannot determine fieldnames for {path}; ensure
header exists or add first row with all fields.\")

def cmd_export(args: argparse.Namespace) -\> None:

path = REGISTRY_MAP.get(args.registry)

if not path:

raise SystemExit(f\"Unknown registry id: {args.registry}\")

rows = load_rows(path)

writer = csv.DictWriter(sys.stdout, fieldnames=get_fieldnames(path,
rows) if rows else \[\])

if rows:

writer.writeheader()

for r in rows:

writer.writerow(r)

def cmd_add(args: argparse.Namespace) -\> None:

path = REGISTRY_MAP.get(args.registry)

if not path:

raise SystemExit(f\"Unknown registry id: {args.registry}\")

try:

entry = json.loads(args.entry)

except json.JSONDecodeError as e:

raise SystemExit(f\"Invalid JSON for entry: {e}\")

rows = load_rows(path)

if rows:

fieldnames = list(rows\[0\].keys())

else:

fieldnames = list(entry.keys())

\# ensure all fields present

for k in entry.keys():

if k not in fieldnames:

fieldnames.append(k)

rows.append({k: str(entry.get(k, \"\")) for k in fieldnames})

save_rows(path, rows, fieldnames)

def cmd_update(args: argparse.Namespace) -\> None:

path = REGISTRY_MAP.get(args.registry)

if not path:

raise SystemExit(f\"Unknown registry id: {args.registry}\")

try:

updates = json.loads(args.updates)

except json.JSONDecodeError as e:

raise SystemExit(f\"Invalid JSON for updates: {e}\")

rows = load_rows(path)

if not rows:

raise SystemExit(f\"No rows found in {path}\")

fieldnames = list(rows\[0\].keys())

if args.key not in fieldnames:

raise SystemExit(f\"Key \'{args.key}\' not in registry header:
{fieldnames}\")

for r in rows:

if r.get(args.key) == args.value:

for k, v in updates.items():

if k not in fieldnames:

fieldnames.append(k)

r\[k\] = str(v)

save_rows(path, rows, fieldnames)

def main() -\> None:

parser = argparse.ArgumentParser(description=\"UIAO registry CLI
(CSV-based, no external deps)\")

sub = parser.add_subparsers(dest=\"command\", required=True)

p_export = sub.add_parser(\"export\", help=\"Export a registry to stdout
(CSV)\")

p_export.add_argument(\"\--registry\", required=True, help=\"Registry ID
(e.g., REG-ID-01)\")

p_export.set_defaults(func=cmd_export)

p_add = sub.add_parser(\"add\", help=\"Add an entry to a registry\")

p_add.add_argument(\"\--registry\", required=True, help=\"Registry ID
(e.g., REG-ID-01)\")

p_add.add_argument(\"\--entry\", required=True, help=\"JSON object
representing the row to add\")

p_add.set_defaults(func=cmd_add)

p_update = sub.add_parser(\"update\", help=\"Update entries in a
registry\")

p_update.add_argument(\"\--registry\", required=True, help=\"Registry ID
(e.g., REG-ID-01)\")

p_update.add_argument(\"\--key\", required=True, help=\"Column name used
as key\")

p_update.add_argument(\"\--value\", required=True, help=\"Key value to
match\")

p_update.add_argument(\"\--updates\", required=True, help=\"JSON object
with fields to update\")

p_update.set_defaults(func=cmd_update)

args = parser.parse_args()

args.func(args)

if \_\_name\_\_ == \"\_\_main\_\_\":

main()

**2. scripts/orgpath_build.py**

**Reads registries, emits PlantUML graph**

This script:

- Reads the key registries (identity, device, server, OrgPath).

- Builds a simple node/edge model.

- Writes diagrams/orgpath_graph.puml as a PlantUML diagram.

#!/usr/bin/env python3

import csv

import os

from typing import Dict, List, Set, Tuple

BASE_DIR =
os.path.dirname(os.path.dirname(os.path.abspath(\_\_file\_\_)))

REGISTRY_FILES = {

\"REG-ID-01\": os.path.join(BASE_DIR, \"registries\", \"identity\",
\"REG-ID-01_auth_dependencies.csv\"),

\"REG-ID-03\": os.path.join(BASE_DIR, \"registries\", \"identity\",
\"REG-ID-03_sso_migration.csv\"),

\"REG-DV-01\": os.path.join(BASE_DIR, \"registries\", \"device\",
\"REG-DV-01_gpo_mapping.csv\"),

\"REG-DV-02\": os.path.join(BASE_DIR, \"registries\", \"device\",
\"REG-DV-02_device_cohorts.csv\"),

\"REG-SR-01\": os.path.join(BASE_DIR, \"registries\", \"server\",
\"REG-SR-01_arc_onboarding.csv\"),

\"REG-SR-03\": os.path.join(BASE_DIR, \"registries\", \"server\",
\"REG-SR-03_domain_dependency_retirement.csv\"),

\"REG-ID-ORGPATH\": os.path.join(BASE_DIR, \"registries\", \"identity\",
\"REG-ID-ORGPATH_orgpath.csv\"),

}

def read_csv(path: str) -\> List\[Dict\[str, str\]\]:

if not os.path.exists(path):

return \[\]

with open(path, newline=\"\", encoding=\"utf-8\") as f:

reader = csv.DictReader(f)

return list(reader)

def build_nodes_and_edges() -\> Tuple\[Dict\[str, Dict\[str, str\]\],
Set\[Tuple\[str, str\]\]\]:

nodes: Dict\[str, Dict\[str, str\]\] = {}

edges: Set\[Tuple\[str, str\]\] = set()

\# 1) OrgPath registry is the canonical graph source

orgpath_rows = read_csv(REGISTRY_FILES\[\"REG-ID-ORGPATH\"\])

for r in orgpath_rows:

node_id = r.get(\"NodeID\")

if not node_id:

continue

nodes\[node_id\] = {

\"NodeType\": r.get(\"NodeType\", \"Unknown\"),

\"Name\": r.get(\"Name\", node_id),

}

depends_on = r.get(\"DependsOn\", \"\")

if depends_on:

for dep in depends_on.split(\",\"):

dep = dep.strip()

if dep:

edges.add((node_id, dep))

\# 2) Identity auth dependencies (REG-ID-01)

for r in read_csv(REGISTRY_FILES\[\"REG-ID-01\"\]):

item_id = r.get(\"ItemID\")

name = r.get(\"Name\", item_id)

if not item_id:

continue

nodes.setdefault(item_id, {\"NodeType\": r.get(\"ItemType\",
\"IdentityItem\"), \"Name\": name})

target = r.get(\"TargetHost\")

if target:

target_id = f\"SRV:{target}\"

nodes.setdefault(target_id, {\"NodeType\": \"Server\", \"Name\":
target})

edges.add((item_id, target_id))

\# 3) SSO migration (REG-ID-03)

for r in read_csv(REGISTRY_FILES\[\"REG-ID-03\"\]):

app_id = r.get(\"AppID\")

app_name = r.get(\"AppName\", app_id)

if not app_id:

continue

nodes.setdefault(app_id, {\"NodeType\": \"App\", \"Name\": app_name})

current_auth = r.get(\"CurrentAuth\", \"\")

target_auth = r.get(\"TargetAuth\", \"\")

if current_auth:

auth_node = f\"AUTH:{current_auth}\"

nodes.setdefault(auth_node, {\"NodeType\": \"Auth\", \"Name\":
current_auth})

edges.add((app_id, auth_node))

if target_auth:

target_node = f\"AUTH:{target_auth}\"

nodes.setdefault(target_node, {\"NodeType\": \"Auth\", \"Name\":
target_auth})

edges.add((app_id, target_node))

\# 4) Device cohorts (REG-DV-02)

for r in read_csv(REGISTRY_FILES\[\"REG-DV-02\"\]):

cohort_id = r.get(\"CohortID\")

cohort_name = r.get(\"CohortName\", cohort_id)

if not cohort_id:

continue

nodes.setdefault(cohort_id, {\"NodeType\": \"DeviceCohort\", \"Name\":
cohort_name})

\# 5) Arc onboarding (REG-SR-01)

for r in read_csv(REGISTRY_FILES\[\"REG-SR-01\"\]):

server_id = r.get(\"ServerID\")

hostname = r.get(\"Hostname\", server_id)

if not server_id:

continue

nodes.setdefault(server_id, {\"NodeType\": \"Server\", \"Name\":
hostname})

env = r.get(\"Environment\", \"\")

if env:

env_node = f\"ENV:{env}\"

nodes.setdefault(env_node, {\"NodeType\": \"Environment\", \"Name\":
env})

edges.add((server_id, env_node))

\# 6) Domain dependency retirement (REG-SR-03)

for r in read_csv(REGISTRY_FILES\[\"REG-SR-03\"\]):

server_id = r.get(\"ServerID\")

dep_type = r.get(\"DependencyType\", \"\")

if not server_id or not dep_type:

continue

dep_node = f\"DEP:{dep_type}\"

nodes.setdefault(dep_node, {\"NodeType\": \"Dependency\", \"Name\":
dep_type})

edges.add((server_id, dep_node))

return nodes, edges

def write_plantuml(nodes: Dict\[str, Dict\[str, str\]\], edges:
Set\[Tuple\[str, str\]\]) -\> None:

diagrams_dir = os.path.join(BASE_DIR, \"diagrams\")

os.makedirs(diagrams_dir, exist_ok=True)

out_path = os.path.join(diagrams_dir, \"orgpath_graph.puml\")

with open(out_path, \"w\", encoding=\"utf-8\") as f:

f.write(\"@startuml orgpath_graph\\n\")

f.write(\"skinparam defaultTextAlignment center\\n\")

f.write(\"skinparam linetype ortho\\n\\n\")

\# Nodes

for node_id, meta in nodes.items():

label = meta.get(\"Name\", node_id).replace(\'\"\', \"\'\")

ntype = meta.get(\"NodeType\", \"Node\")

f.write(f\'class \"{label}\\\\n({ntype})\" as \"{node_id}\"\\n\')

f.write(\"\\n\")

\# Edges

for src, dst in edges:

if src in nodes and dst in nodes:

f.write(f\'\"{src}\" \--\> \"{dst}\"\\n\')

f.write(\"\\n@enduml\\n\")

def main() -\> None:

nodes, edges = build_nodes_and_edges()

write_plantuml(nodes, edges)

if \_\_name\_\_ == \"\_\_main\_\_\":

main()

Here is the **exact, minimal, canonical UIAO runbook** you asked for ---
**RB-ID-ORGPATH_orgpath_etl.md** --- written in the same style as the
rest of your modernization track artifacts.\
It is **ready to drop directly into**:

runbooks/RB-ID-ORGPATH_orgpath_etl.md

No greenfield assumptions. No duplication. No drift.\
It references only the registries and scripts you already have.

**RB-ID-ORGPATH_orgpath_etl.md**

***OrgPath ETL & Graph Generation Runbook***

**Version:** 0.1\
**Owner:** Identity Architecture\
**Status:** Draft

**1. Purpose**

This runbook defines the **exact operational steps** to:

1.  Execute the **OrgPath ETL** pipeline

2.  Read all UIAO registries (identity, device, server, OrgPath)

3.  Generate the **OrgPath dependency graph**

4.  Produce a **PlantUML diagram** (orgpath_graph.puml)

5.  Validate the output and interpret the resulting dependency map

OrgPath is the **cross‑plane dependency model** that Microsoft tooling
does not provide.\
It unifies:

- Entra ID sign‑in dependencies

- LDAP/NTLM/Kerberos dependencies

- GPO → Intune dependencies

- Device → server → app dependencies

- Arc onboarding and domain retirement dependencies

This runbook ensures the OrgPath graph is **deterministic, reproducible,
and aligned with UIAO governance**.

**2. Prerequisites**

**2.1 Required files**

These must already exist in the repo:

scripts/orgpath_build.py

registries/identity/REG-ID-ORGPATH_orgpath.csv

registries/identity/REG-ID-01_auth_dependencies.csv

registries/identity/REG-ID-03_sso_migration.csv

registries/device/REG-DV-01_gpo_mapping.csv

registries/device/REG-DV-02_device_cohorts.csv

registries/server/REG-SR-01_arc_onboarding.csv

registries/server/REG-SR-03_domain_dependency_retirement.csv

**2.2 Required environment**

- Python 3.x installed

- Repo cloned locally

- No external Python dependencies required

**2.3 Required data population**

Before running ETL, ensure:

- Identity dependencies are populated

- SSO migration catalog has at least initial rows

- Device cohorts exist

- Arc onboarding registry has server rows

- Domain dependency retirement registry has at least one dependency row

- OrgPath registry has at least one node

**3. Execution Steps**

**Step 1 --- Navigate to repo root**

Set-Location \<path-to-your-repo\>

**Step 2 --- Run the OrgPath ETL script**

python .\\scripts\\orgpath_build.py

**Step 3 --- Confirm output file creation**

The script generates:

diagrams/orgpath_graph.puml

Validate:

Test-Path .\\diagrams\\orgpath_graph.puml

Expected output:

True

**Step 4 --- Render the PlantUML diagram (optional)**

If you have PlantUML locally:

java -jar plantuml.jar .\\diagrams\\orgpath_graph.puml

This produces:

diagrams/orgpath_graph.png

If you use VS Code PlantUML extension, simply open the .puml file.

**4. Understanding the Output**

**4.1 Node Types**

OrgPath generates nodes from registries:

  --------------------------------------------------------------------
  **NodeType**       **Source Registry** **Meaning**
  ------------------ ------------------- -----------------------------
  **User**           REG-ID-ORGPATH      Identity principal

  **App**            REG-ID-03           Application requiring auth

  **Server**         REG-SR-01 /         Arc server or LDAP target
                     REG-ID-01

  **DeviceCohort**   REG-DV-02           Autopilot/Intune cohort

  **Dependency**     REG-SR-03           AD/GPO/NTLM/Kerberos
                                         dependency

  **Auth**           REG-ID-03           Current/target auth model

  **Environment**    REG-SR-01           Prod/Dev/Test/DMZ
  --------------------------------------------------------------------

**4.2 Edge Types**

Edges represent dependencies:

- **App → AUTH:** current or target authentication

- **App → Server:** LDAP/NTLM/Kerberos dependency

- **Server → Dependency:** GPO, logon script, service account, file
  share

- **Server → Environment:** Arc environment classification

- **Node → Node:** any OrgPath-defined dependency

**4.3 How to read the graph**

**Example patterns**

**Pattern A --- LDAP-bound app**

APP:FinancePortal \--\> SRV:DC01

SRV:DC01 \--\> DEP:LDAP

**Pattern B --- App moving from AD FS to Entra**

APP:HRPortal \--\> AUTH:ADFS

APP:HRPortal \--\> AUTH:OIDC

**Pattern C --- Server with domain retirement blockers**

SRV:APP01 \--\> DEP:Kerberos

SRV:APP01 \--\> DEP:GPO

**Pattern D --- Device cohort dependencies**

COHORT:Wave1 \--\> APP:Teams

COHORT:Wave1 \--\> APP:FinancePortal

**5. Validation Steps**

**5.1 Validate registry completeness**

Get-Content registries\\identity\\REG-ID-ORGPATH_orgpath.csv \|
Select-Object -First 5

Ensure:

- NodeID is unique

- DependsOn references valid NodeIDs

**5.2 Validate graph structure**

Open orgpath_graph.puml and confirm:

- No orphan nodes unless expected

- No circular dependencies unless intentional

- All major systems appear (identity, device, server, app)

**5.3 Validate cross-plane coverage**

Ensure the graph includes:

- Identity → App

- App → Server

- Server → Dependency

- Device → Cohort

- Cohort → App

- Server → Environment

**6. Troubleshooting**

**6.1 Missing nodes**

If a node appears without edges:

- Check DependsOn column in OrgPath registry

- Check registry headers for typos

- Ensure CSVs have no BOM or hidden characters

**6.2 Missing edges**

If dependencies don't appear:

- Confirm comma-separated values in DependsOn

- Ensure no trailing spaces

- Ensure NodeIDs match exactly (case-sensitive)

**6.3 Script errors**

Common causes:

- CSV header mismatch

- Missing registry file

- JSON-like values in CSV fields

Fix by validating headers against UIAO canonical templates.

**7. Maintenance**

**7.1 When to re-run ETL**

- After any registry update

- After adding new apps, servers, or dependencies

- Before each modernization wave

- Before AD DS retirement checkpoints

**7.2 Versioning**

Commit the generated .puml file with message:

Update OrgPath graph after registry changes

**8. Outputs**

After running this runbook, you will have:

diagrams/orgpath_graph.puml

This file represents the **single source of truth** for:

- Identity dependencies

- Device dependencies

- Server dependencies

- Authentication flows

- Domain retirement blockers

- Migration sequencing

It is the **governance backbone** for the Intune/Entra/Arc modernization
track.

**9. End of Runbook**

Here's everything, clean and drop‑in.

**1. PlantUML theme for UIAO**

**File:** diagrams/uiao_theme.puml

\' UIAO PlantUML Theme

\' File: diagrams/uiao_theme.puml

skinparam defaultFontName \"Segoe UI\"

skinparam defaultFontSize 12

skinparam shadowing false

skinparam roundcorner 8

skinparam linetype ortho

skinparam class {

BackgroundColor #F5F7FA

BorderColor #2B4C7E

ArrowColor #2B4C7E

}

skinparam package {

BackgroundColor #E8EEF7

BorderColor #2B4C7E

}

skinparam note {

BackgroundColor #FFFBEA

BorderColor #C9A227

}

skinparam component {

BackgroundColor #F5F7FA

BorderColor #2B4C7E

}

skinparam rectangle {

BackgroundColor #F5F7FA

BorderColor #2B4C7E

}

skinparam activity {

BackgroundColor #F5F7FA

BorderColor #2B4C7E

}

skinparam sequence {

ArrowColor #2B4C7E

LifeLineBorderColor #2B4C7E

LifeLineBackgroundColor #FFFFFF

}

skinparam legend {

BackgroundColor #FFFFFF

BorderColor #CCCCCC

}

\' Common stereotypes

skinparam class\<\<Identity\>\> {

BackgroundColor #E3F2FD

BorderColor #1565C0

}

skinparam class\<\<Device\>\> {

BackgroundColor #E8F5E9

BorderColor #2E7D32

}

skinparam class\<\<Server\>\> {

BackgroundColor #FFF3E0

BorderColor #EF6C00

}

skinparam class\<\<OrgPath\>\> {

BackgroundColor #F3E5F5

BorderColor #6A1B9A

}

Use in diagrams:

\@startuml some_diagram

!include uiao_theme.puml

\' your diagram here

\@enduml

**2. CI workflow that regenerates OrgPath on every commit**

**File:** .github/workflows/orgpath.yml

name: OrgPath Graph

on:

push:

paths:

\- \"registries/\*\*\"

\- \"scripts/orgpath_build.py\"

\- \"diagrams/uiao_theme.puml\"

\- \".github/workflows/orgpath.yml\"

pull_request:

paths:

\- \"registries/\*\*\"

\- \"scripts/orgpath_build.py\"

\- \"diagrams/uiao_theme.puml\"

\- \".github/workflows/orgpath.yml\"

jobs:

build-orgpath:

runs-on: ubuntu-latest

steps:

\- name: Checkout

uses: actions/checkout@v4

\- name: Set up Python

uses: actions/setup-python@v5

with:

python-version: \"3.x\"

\- name: Run OrgPath ETL

run: \|

python scripts/orgpath_build.py

\- name: Verify OrgPath output exists

run: \|

test -f diagrams/orgpath_graph.puml

\- name: Upload OrgPath diagram artifact

uses: actions/upload-artifact@v4

with:

name: orgpath-diagram

path: diagrams/orgpath_graph.puml

**3. GitHub PR template for modernization changes**

**File:** .github/pull_request_template.md

\# UIAO Modernization Track -- Intune / Entra / Arc

\## 1. Summary

\- \*\*Track area:\*\* (Identity / Device / Server / OrgPath /
Cross-track)

\- \*\*Change type:\*\* (New artifact / Registry update / Runbook /
Script / Diagram)

\- \*\*Short description:\*\*

\## 2. Artifacts and Registries Touched

\- \*\*Artifacts:\*\*

\- \[ \] ART-ID-E1 Identity Dependency Map

\- \[ \] ART-ID-E2 Directory Sync Design

\- \[ \] ART-ID-E3 Authentication Method Plan

\- \[ \] ART-ID-E4 Conditional Access Baseline Set

\- \[ \] ART-ID-E5 SSO Migration Catalog

\- \[ \] ART-ID-E6 App Proxy Publishing Plan

\- \[ \] ART-DV-I1 GPO Inventory Export

\- \[ \] ART-DV-I2 GPO to Intune Mapping Matrix

\- \[ \] ART-DV-I3 Intune Configuration Baseline

\- \[ \] ART-DV-I4 Device Compliance Model

\- \[ \] ART-DV-I5 Autopilot Deployment Plan

\- \[ \] ART-DV-I6 App Deployment Model

\- \[ \] ART-SR-A1 Arc Onboarding Plan

\- \[ \] ART-SR-A2 Arc Policy Baseline

\- \[ \] ART-SR-A3 Arc Extension Deployment Plan

\- \[ \] ART-SR-A4 Managed Identity Adoption Plan

\- \[ \] ART-SR-A5 Server Domain Dependency Map

\- \[ \] ART-ID-ORGPATH OrgPath Dependency Graph

\- \*\*Registries:\*\*

\- \[ \] REG-ID-01 Auth Dependencies

\- \[ \] REG-ID-02 Conditional Access

\- \[ \] REG-ID-03 SSO Migration

\- \[ \] REG-ID-ORGPATH OrgPath

\- \[ \] REG-DV-01 GPO Mapping

\- \[ \] REG-DV-02 Device Cohorts

\- \[ \] REG-DV-03 App Deployment

\- \[ \] REG-SR-01 Arc Onboarding

\- \[ \] REG-SR-02 Arc Policy Compliance

\- \[ \] REG-SR-03 Domain Dependency Retirement

\## 3. Microsoft Tools Involved

List the Microsoft tools and how they are used in this change:

\- Tool:

\- Usage:

\- Impacted plane: (Identity / Device / Server)

\## 4. OrgPath Impact

\- \[ \] \`scripts/orgpath_build.py\` run locally

\- \[ \] \`diagrams/orgpath_graph.puml\` regenerated

\- Describe any notable changes in the OrgPath graph:

\## 5. Validation

\- \[ \] CSV headers validated

\- \[ \] No \`MISSING\` placeholders introduced

\- \[ \] Quarto docs render (if touched)

\- \[ \] PowerShell / Python scripts executed locally (if touched)

\## 6. Risks and Rollback

\- \*\*Risk level:\*\* (Low / Medium / High)

\- \*\*Rollback plan:\*\*

**4. Cross‑track integration diagram (OrgPath → Identity / Device /
Server)**

**File:** diagrams/orgpath_integration.puml

\@startuml orgpath_integration

!include uiao_theme.puml

package \"OrgPath\" {

class \"OrgPath Registry\\n(REG-ID-ORGPATH)\" as ORGPATH \<\<OrgPath\>\>

class \"OrgPath ETL\\n(orgpath_build.py)\" as ORGPATH_ETL
\<\<OrgPath\>\>

class \"OrgPath Graph\\n(orgpath_graph.puml)\" as ORGPATH_GRAPH
\<\<OrgPath\>\>

}

package \"Identity Track\" {

class \"Identity Artifacts\\n(ART-ID-Ex)\" as ID_ART \<\<Identity\>\>

class \"Identity Registries\\n(REG-ID-0x)\" as ID_REG \<\<Identity\>\>

}

package \"Device Track\" {

class \"Device Artifacts\\n(ART-DV-Ix)\" as DV_ART \<\<Device\>\>

class \"Device Registries\\n(REG-DV-0x)\" as DV_REG \<\<Device\>\>

}

package \"Server Track\" {

class \"Server Artifacts\\n(ART-SR-Ax)\" as SR_ART \<\<Server\>\>

class \"Server Registries\\n(REG-SR-0x)\" as SR_REG \<\<Server\>\>

}

ORGPATH_REG = ORGPATH

\' Data flows into OrgPath

ID_REG \--\> ORGPATH : identity\\nsignals

DV_REG \--\> ORGPATH : device\\ncohorts

SR_REG \--\> ORGPATH : server\\nand domain\\ndependencies

\' ETL and graph

ORGPATH \--\> ORGPATH_ETL : read\\nregistries

ORGPATH_ETL \--\> ORGPATH_GRAPH : generate\\nPlantUML graph

\' Graph informs tracks

ORGPATH_GRAPH \--\> ID_ART : prioritize\\nidentity\\nmodernization

ORGPATH_GRAPH \--\> DV_ART : prioritize\\ndevice\\ncohorts

ORGPATH_GRAPH \--\> SR_ART : prioritize\\nserver\\nremediation

legend right

OrgPath unifies:

\- Identity dependencies

\- Device cohorts and policies

\- Server and domain dependencies

and feeds modernization

decisions back into each track.

endlegend

\@enduml

You can now:

- Drop these four files into place.

- Commit on your feature branch.

- Let CI regenerate OrgPath on every change and keep the cross‑track
  story visually coherent.
