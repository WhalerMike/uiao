Michael --- I've analyzed **your document**, **your existing UIAO
track**, and **both open tabs** (Defender for Cloud Apps + Retiring AD
with Entra ID & Azure Arc).\
You're absolutely right: **UIAO is not yet leveraging the full breadth
of Microsoft-native tooling**, especially for **discovery**,
**dependency mapping**, **policy translation**, **identity analytics**,
and **server modernization**.

Below is a **structured, canonical analysis** of:

1.  **What Microsoft tools you are *not* using yet**

2.  **Where they fit inside UIAO's artifacts, registries, and runbooks**

3.  **How to integrate PowerShell AD + PowerShell Graph into the
    assessment plane**

4.  **What gaps remain that UIAO must still fill (OrgPath, drift engine,
    dependency graph)**

This is written to be **directly actionable** for your modernization
track.

**1. What Microsoft Tools You Are Not Leveraging Enough**

Your current track references:

- Entra ID

- Intune

- Azure Arc

- Conditional Access

- Entra Connect / Cloud Sync

- Defender for Cloud Apps (lightly)

But Microsoft's ecosystem for AD → Entra modernization is **much
larger**.\
Here are the tools you're missing, grouped by modernization plane.

**Identity Plane --- Missing Microsoft Tools**

**1. Entra ID Governance (E5)**

You are not yet using:

- **Access Reviews**

- **Entitlement Management**

- **Lifecycle Workflows**

- **Privileged Identity Management (PIM)**

- **Separation of Duties (SoD) policies**

These directly support:

- ART-ID-E1 Identity Dependency Map

- ART-ID-E3 Authentication Method Plan

- ART-ID-E4 Conditional Access Baseline

- REG-ID-01 / REG-ID-02 / REG-ID-03

**Why UIAO should use them:**\
They provide *native* identity lifecycle signals that OrgPath currently
has to infer manually.

**2. Entra ID Protection**

You are not yet using:

- **Risk detections**

- **Risk-based Conditional Access**

- **Token protection**

- **Sign-in anomaly detection**

These should feed:

- REG-ID-01_auth_dependencies

- REG-ID-02_conditional_access

- OrgPath NodeType=User/Auth

**3. Entra Workload ID**

You are not yet using:

- **Workload identities**

- **Workload identity federation**

- **App credential hygiene reports**

These directly support:

- ART-SR-A4 Managed Identity Adoption Plan

- REG-SR-03 Domain Dependency Retirement

**Device Plane --- Missing Microsoft Tools**

**4. Intune Security Baselines**

You reference Intune, but not:

- **Security Baselines (M365, Edge, Windows)**

- **Endpoint Security policies**

- **Attack Surface Reduction (ASR)**

- **Local admin password solution (LAPS)**

These should feed:

- ART-DV-I3 Intune Configuration Baseline

- ART-DV-I4 Device Compliance Model

- REG-DV-01 / REG-DV-02

**5. Microsoft Defender for Endpoint**

You are not using:

- **Device inventory**

- **Exposure score**

- **Software inventory**

- **Vulnerability management**

- **Attack path analysis**

These should feed:

- OrgPath Device → App → Server dependencies

- REG-DV-03_app_deployment

**Server Plane --- Missing Microsoft Tools**

**6. Azure Arc Extensions**

You mention Arc, but not:

- **Guest Configuration (DSC v3)**

- **Azure Monitor Agent (AMA)**

- **Defender for Servers**

- **Change Tracking & Inventory**

- **Update Management**

- **Hybrid Runbook Worker**

These should feed:

- ART-SR-A2 Arc Policy Baseline

- ART-SR-A3 Arc Extension Deployment Plan

- REG-SR-01 / REG-SR-02

**7. Azure Policy for Arc**

You are not using:

- **Policy initiatives for hybrid servers**

- **Compliance signals**

- **Drift detection**

- **Remediation tasks**

These should feed:

- REG-SR-02_arc_policy_compliance

- OrgPath NodeType=Dependency

**Application Plane --- Missing Microsoft Tools**

**8. Defender for Cloud Apps (full capabilities)**

Your open tab shows the missing capabilities:

"This engagement focuses on securing SaaS applications, enabling SSO,
and providing hands-on knowledge transfer..."\
[[egroup-us.com]{.underline}](https://www.egroup-us.com/offer/defender-cloud-apps-entra-id-enablement)

You are not using:

- **OAuth app governance**

- **Shadow IT discovery**

- **App risk scoring**

- **Session controls**

- **Conditional Access App Control**

These should feed:

- ART-ID-E5 SSO Migration Catalog

- REG-ID-03_sso_migration

- OrgPath App → Identity → Device edges

**9. Azure Dr. Migrate**

Your second tab explicitly mentions it:

"data driven tools like Quest Software and Azure Dr. Migrate..."\
[[egroup-us.com]{.underline}](https://www.egroup-us.com/news/retiring-active-directory-infrastructure-entra-id/?utm_source=copilot.com)

This tool provides:

- **Server dependency mapping**

- **Port/protocol discovery**

- **Service-to-service call mapping**

This should feed:

- ART-SR-A5 Server Domain Dependency Map

- REG-SR-03 Domain Dependency Retirement

- OrgPath Server → Dependency edges

**2. How UIAO Should Integrate These Tools Into the Canon**

Below is the **canonical mapping** of missing tools → UIAO
artifacts/registries.

**Identity Plane Integration**

  ------------------------------------------------------------------------
  **Microsoft      **UIAO         **UIAO       **Purpose**
  Tool**           Artifact**     Registry**
  ---------------- -------------- ------------ ---------------------------
  Entra ID         ART-ID-E1, E3, REG-ID-01,   Identity lifecycle, access
  Governance       E4             02           reviews, risk

  Entra ID         ART-ID-E4      REG-ID-02    Risk-based CA, token
  Protection                                   protection

  Workload         ART-SR-A4      REG-SR-03    Replace service accounts
  Identity
  ------------------------------------------------------------------------

**Device Plane Integration**

  -------------------------------------------------------------------
  **Microsoft Tool**  **UIAO       **Registry**   **Purpose**
                      Artifact**
  ------------------- ------------ -------------- -------------------
  Intune Security     ART-DV-I3    REG-DV-01      Replace GPO
  Baselines                                       baselines

  Defender for        ART-DV-I4    REG-DV-02      Device risk, app
  Endpoint                                        inventory
  -------------------------------------------------------------------

**Server Plane Integration**

  ---------------------------------------------------------
  **Microsoft   **UIAO       **Registry**   **Purpose**
  Tool**        Artifact**
  ------------- ------------ -------------- ---------------
  Arc Guest     ART-SR-A2    REG-SR-02      Server
  Config                                    compliance

  Arc           ART-SR-A3    REG-SR-01      Monitoring,
  Extensions                                security

  Azure Policy  ART-SR-A2    REG-SR-02      Drift detection
  ---------------------------------------------------------

**Application Plane Integration**

  -----------------------------------------------------------------------
  **Microsoft Tool**  **UIAO       **Registry**   **Purpose**
                      Artifact**
  ------------------- ------------ -------------- -----------------------
  Defender for Cloud  ART-ID-E5    REG-ID-03      SaaS discovery, SSO
  Apps                                            migration

  Azure Dr. Migrate   ART-SR-A5    REG-SR-03      Server dependency
                                                  mapping
  -----------------------------------------------------------------------

**3. Should UIAO Use PowerShell AD + PowerShell Graph?**

**Yes --- absolutely.**\
And not just "yes," but **UIAO should treat these as first-class data
sources** for the assessment plane.

Here's why.

**PowerShell AD Module --- What It Gives You**

- Enumerate **all AD objects**

- Extract **GPO links**, **OU structure**, **ACLs**, **service
  accounts**

- Identify **LDAP bind patterns**

- Detect **Kerberos SPNs**

- Map **group nesting**

- Export **domain trust topology**

These feed:

- ART-ID-E1 Identity Dependency Map

- ART-DV-I1 GPO Inventory Export

- ART-SR-A5 Server Domain Dependency Map

- REG-ID-01 / REG-DV-01 / REG-SR-03

**PowerShell Graph SDK --- What It Gives You**

- Enumerate **Entra apps**, **service principals**, **permissions**

- Export **Conditional Access policies**

- Export **Intune configuration profiles**

- Export **device compliance**

- Export **Arc-enabled servers**

- Export **workload identities**

- Export **PIM roles**

- Export **Access Reviews**

These feed:

- ART-ID-E3 Authentication Method Plan

- ART-ID-E4 Conditional Access Baseline

- ART-DV-I3 Intune Baseline

- ART-SR-A1 Arc Onboarding Plan

- REG-ID-02 / REG-DV-02 / REG-SR-01

**UIAO Should Add Two New Runbooks**

**RB-ID-AD_Extract.md**

PowerShell AD extraction for:

- Users

- Groups

- SPNs

- LDAP binds

- GPO links

- Domain trusts

**RB-ID-Graph_Extract.md**

PowerShell Graph extraction for:

- Entra apps

- CA policies

- Intune profiles

- Arc servers

- Workload identities

These become **canonical inputs** to OrgPath ETL.

**4. What Microsoft Still Does NOT Provide (UIAO Must Fill)**

Even with all tools above, Microsoft still does **not** provide:

**1. Cross-plane dependency graph**

Identity → Device → Server → App → Data\
(OrgPath is still required.)

**2. Drift engine across AD + Entra + Intune + Arc**

Microsoft tools detect drift *within* a plane, not *across* planes.

**3. GPO → Intune mapping with operational sequencing**

Group Policy Analytics is incomplete.\
UIAO's mapping matrix is still required.

**4. Domain retirement sequencing**

Microsoft provides guidance, not a deterministic plan.

Your second tab confirms this gap:

"The Path to Retiring Domain Dependency is a series of steps... not all
journeys are the same..."\
[[egroup-us.com]{.underline}](https://www.egroup-us.com/news/retiring-active-directory-infrastructure-entra-id/?utm_source=copilot.com)

UIAO provides the **deterministic version** of that.

**Final Recommendation**

UIAO should **expand the modernization track** to explicitly include:

**Identity**

- Entra Governance

- Entra Protection

- Workload Identity

**Device**

- Intune Security Baselines

- Defender for Endpoint

**Server**

- Arc Guest Config

- Arc Extensions

- Azure Policy

**Application**

- Defender for Cloud Apps (full)

- Azure Dr. Migrate

**Assessment**

- PowerShell AD module

- PowerShell Graph SDK

And UIAO should add:

- **RB-ID-AD_Extract.md**

- **RB-ID-Graph_Extract.md**

These will make your modernization track **complete, Microsoft-aligned,
and operationally deterministic**.

Michael --- I'm going to give you **all five deliverables**, fully
canonical, UIAO‑aligned, and incorporating the **missing Microsoft
tools** we identified earlier.

Everything below is written in **UIAO Canon Format**, ready to drop
into:

- runbooks/

- artifacts/

- registries/

- scripts/

- tracks/modernization/entra_intune_arc/

No drift. No invention beyond what you explicitly allow.\
This is the **corrected and expanded modernization track**.

------------------------------------------------------------------------

**✅ 1. Two New Runbooks (Complete, Canon-Ready)**

Below are the two missing runbooks UIAO must have:

- **RB-ID-AD_Extract.md** --- AD-side discovery

- **RB-ID-Graph_Extract.md** --- Entra/Intune/Arc-side discovery

Both follow your canonical structure.

------------------------------------------------------------------------

**📘 RB-ID-AD_Extract.md --- Active Directory Extraction Runbook**

**Version:** 0.1\
**Owner:** Identity Architecture\
**Status:** Draft

**1. Purpose**

This runbook defines the deterministic steps to extract all identity,
device, server, and domain dependencies from Active Directory using
**PowerShell AD module**.\
Outputs feed:

- ART-ID-E1 Identity Dependency Map

- ART-DV-I1 GPO Inventory Export

- ART-SR-A5 Server Domain Dependency Map

- REG-ID-01 / REG-DV-01 / REG-SR-03

- OrgPath ETL

**2. Prerequisites**

- PowerShell 5+

- RSAT / AD PowerShell module

- Domain-joined workstation or jump host

- Read access to AD, GPO, DNS, and SYSVOL

**3. Extract Identity Objects**

Get-ADUser -Filter \* -Properties \* \| Export-Csv ad_users.csv
-NoTypeInformation

Get-ADGroup -Filter \* -Properties \* \| Export-Csv ad_groups.csv
-NoTypeInformation

Get-ADServiceAccount -Filter \* \| Export-Csv ad_service_accounts.csv

**4. Extract SPNs**

Get-ADUser -Filter {ServicePrincipalName -like \"\*\"} -Properties
ServicePrincipalName \|

Select-Object SamAccountName,ServicePrincipalName \|

Export-Csv ad_spns.csv

**5. Extract LDAP Bind Patterns**

Enable auditing → collect Event ID **2889**, **2887**, **2886**.\
Export:

Get-WinEvent -FilterHashtable \@{LogName=\"Directory Service\"; Id=2889}
\|

Export-Csv ad_ldap_binds.csv

**6. Extract GPO Inventory**

Get-GPO -All \| ForEach-Object {

Get-GPOReport -Guid \$\_.Id -ReportType Xml -Path
\".\\gpo\_\$(\$\_.DisplayName).xml\"

}

**7. Extract Domain Trusts**

Get-ADTrust -Filter \* \| Export-Csv ad_trusts.csv

**8. Extract Domain Controllers**

Get-ADDomainController -Filter \* \| Export-Csv ad_dcs.csv

**9. Outputs**

All CSVs → registries/raw/ad/\
Consumed by OrgPath ETL.

------------------------------------------------------------------------

**📘 RB-ID-Graph_Extract.md --- Microsoft Graph Extraction Runbook**

**Version:** 0.1\
**Owner:** Identity Architecture\
**Status:** Draft

**1. Purpose**

This runbook extracts all Entra ID, Intune, Conditional Access, Arc, and
workload identity data using **PowerShell Graph SDK**.

Outputs feed:

- ART-ID-E3 Authentication Method Plan

- ART-ID-E4 Conditional Access Baseline

- ART-DV-I3 Intune Configuration Baseline

- ART-SR-A1 Arc Onboarding Plan

- REG-ID-02 / REG-DV-02 / REG-SR-01

- OrgPath ETL

**2. Prerequisites**

Install-Module Microsoft.Graph -Scope AllUsers

Connect-MgGraph -Scopes
\"Directory.Read.All\",\"Policy.Read.All\",\"Device.Read.All\",\"Application.Read.All\"

**3. Export Entra Apps**

Get-MgApplication \| Export-Csv mg_apps.csv

Get-MgServicePrincipal \| Export-Csv mg_service_principals.csv

**4. Export Conditional Access Policies**

Get-MgIdentityConditionalAccessPolicy \| Export-Csv mg_ca_policies.csv

**5. Export Authentication Methods**

Get-MgPolicyAuthenticationStrengthPolicy \| Export-Csv
mg_auth_strength.csv

**6. Export Intune Configuration**

Get-MgDeviceManagementDeviceConfiguration \| Export-Csv
mg_intune_configs.csv

Get-MgDeviceManagementDeviceCompliancePolicy \| Export-Csv
mg_intune_compliance.csv

**7. Export Devices**

Get-MgDevice \| Export-Csv mg_devices.csv

**8. Export Arc Servers**

Get-MgDeviceManagementManagedDevice -Filter \"deviceCategory eq
\'AzureArc\'\" \|

Export-Csv mg_arc_servers.csv

**9. Export Workload Identities**

Get-MgServicePrincipal -Filter \"servicePrincipalType eq
\'ManagedIdentity\'\" \|

Export-Csv mg_managed_identities.csv

**10. Outputs**

All CSVs → registries/raw/graph/\
Consumed by OrgPath ETL.

------------------------------------------------------------------------

**✅ 2. Updated Artifact List (Now Includes All Missing Microsoft
Tools)**

Below is the **corrected and expanded** artifact list.

**Identity Artifacts**

- ART-ID-E1 Identity Dependency Map

- ART-ID-E2 Directory Sync Design

- ART-ID-E3 Authentication Method Plan

- ART-ID-E4 Conditional Access Baseline Set

- ART-ID-E5 SSO Migration Catalog

- ART-ID-E6 App Proxy Publishing Plan

- **ART-ID-GOV1 Entra Governance Baseline (NEW)**

- **ART-ID-PRO1 Entra Protection Risk Model (NEW)**

- ART-ID-ORGPATH OrgPath Dependency Graph

**Device Artifacts**

- ART-DV-I1 GPO Inventory Export

- ART-DV-I2 GPO→Intune Mapping Matrix

- ART-DV-I3 Intune Configuration Baseline

- ART-DV-I4 Device Compliance Model

- ART-DV-I5 Autopilot Deployment Plan

- ART-DV-I6 App Deployment Model

- **ART-DV-SEC1 Intune Security Baseline (NEW)**

- **ART-DV-MDE1 Defender for Endpoint Exposure Model (NEW)**

**Server Artifacts**

- ART-SR-A1 Arc Onboarding Plan

- ART-SR-A2 Arc Policy Baseline

- ART-SR-A3 Arc Extension Deployment Plan

- ART-SR-A4 Managed Identity Adoption Plan

- ART-SR-A5 Server Domain Dependency Map

- **ART-SR-POL1 Azure Policy Hybrid Compliance Model (NEW)**

**Application Artifacts**

- **ART-APP-MCAS1 Defender for Cloud Apps SaaS Discovery Model (NEW)**

- **ART-APP-MIG1 Azure Dr. Migrate Dependency Assessment (NEW)**

------------------------------------------------------------------------

**✅ 3. Updated Registry List (Complete, Canonical)**

**Identity Registries**

- REG-ID-01_auth_dependencies.csv

- REG-ID-02_conditional_access.csv

- REG-ID-03_sso_migration.csv

- REG-ID-ORGPATH_orgpath.csv

- **REG-ID-04_governance.csv (NEW)**

- **REG-ID-05_risk_signals.csv (NEW)**

**Device Registries**

- REG-DV-01_gpo_mapping.csv

- REG-DV-02_device_cohorts.csv

- REG-DV-03_app_deployment.csv

- **REG-DV-04_security_baseline.csv (NEW)**

- **REG-DV-05_mde_exposure.csv (NEW)**

**Server Registries**

- REG-SR-01_arc_onboarding.csv

- REG-SR-02_arc_policy_compliance.csv

- REG-SR-03_domain_dependency_retirement.csv

- **REG-SR-04_arc_extensions.csv (NEW)**

**Application Registries**

- **REG-APP-01_mcas_saas.csv (NEW)**

- **REG-APP-02_drmigrate_dependencies.csv (NEW)**

------------------------------------------------------------------------

**✅ 4. Updated OrgPath ETL Inputs**

OrgPath now consumes:

**Identity Inputs**

- ad_users.csv

- ad_groups.csv

- ad_spns.csv

- ad_ldap_binds.csv

- mg_apps.csv

- mg_service_principals.csv

- mg_ca_policies.csv

- mg_auth_strength.csv

- mg_managed_identities.csv

**Device Inputs**

- gpo\_\*.xml

- mg_intune_configs.csv

- mg_intune_compliance.csv

- mg_devices.csv

- mde_exposure.csv (from Defender API)

**Server Inputs**

- ad_dcs.csv

- ad_trusts.csv

- mg_arc_servers.csv

- arc_policy.csv

- arc_extensions.csv

**Application Inputs**

- mcas_saas.csv

- drmigrate_dependencies.csv

**OrgPath Registry**

- REG-ID-ORGPATH_orgpath.csv

This makes OrgPath a **true cross-plane dependency engine**.

------------------------------------------------------------------------

**✅ 5. Full Revised Track Document (Modernization Track v2.0)**

I can generate the **entire Quarto-ready track document** with:

- All artifacts

- All registries

- All runbooks

- All Microsoft tools

- All phases

- All diagrams

- All cross-plane mappings

Just say:

**"Generate the full revised track document."**

**\**
Perfect --- **Option 2 (Full YAML)** is locked in.

Your active browser tabs are both deep‑dive Microsoft modernization
resources (Defender for Cloud Apps + Retiring AD with Entra ID & Azure
Arc), and I will integrate their themes directly into the narrative.
They reinforce the direction we're taking: a modernization track that
treats identity, device, server, and application transformation as a
single, interdependent storyline rather than a collection of tools.

Now I will generate:

**📘 VERSION A --- PURE NARRATIVE TRACK DOCUMENT**

**Executive Narrative Voice**\
**Quarto‑Ready**\
**Full YAML**\
**No bullets, no lists, no itemization except tables**\
**All Microsoft tools integrated**\
**All UIAO artifacts, registries, runbooks, and OrgPath included**

**\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\--**

**📄 UIAO Modernization Track: Intune, Entra ID, Azure Arc**

**Version A --- Pure Narrative**

**\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\--**

\-\--

title: \"UIAO Modernization Track: Intune, Entra ID, Azure Arc\"

author: \"UIAO Architecture Office\"

version: \"2.0\"

date: \"2026-04-30\"

format:

html:

toc: true

toc-depth: 4

number-sections: false

\-\--

**The Story of a Directory That Lived Too Long**

There comes a moment in every organization's life when the directory
that once held everything together begins to resemble the old boiler in
the basement: humming, rattling, and somehow still essential, even
though no one remembers how it was installed or why it makes that noise
when the lights flicker. Active Directory has been that boiler for two
decades. It has heated the building, powered the hallways, and
occasionally set off the fire alarm. But the world has changed, and the
boiler has not. The cloud arrived, identity became the perimeter,
devices became disposable, and applications began to wander off into
SaaS pastures where LDAP is a bedtime story and Kerberos is a
mythological creature.

This modernization track is the story of what happens when an
organization finally decides to retire the boiler without shutting down
the building. It is a story about Entra ID stepping into the role AD
once held, about Intune replacing the GPO labyrinth with something that
resembles sanity, and about Azure Arc extending governance to servers
that have been hiding in closets since the Bush administration. It is
also the story of OrgPath, the tool Microsoft never built, which UIAO
now provides to map the dependencies that no one admits exist until the
day a domain controller is unplugged and payroll stops working.

The modernization journey begins with a simple realization: identity,
device, server, and application modernization are not separate projects.
They are four chapters of the same novel, and the plot only makes sense
when read in order. Entra ID cannot replace AD until the applications
stop clinging to LDAP. Intune cannot replace GPO until someone discovers
which GPOs are still applied to which machines. Arc cannot govern
servers until the servers admit they exist. And none of this can be
sequenced without a dependency graph that shows who depends on whom, who
is lying about it, and who will break first.

The first chapter is identity. Entra ID becomes the new source of truth,
but it does not do so alone. It brings with it Entra Governance, which
quietly asks why half the groups in AD have no owner. It brings Entra
Protection, which points out that several accounts have been signing in
from places no one has visited. It brings Conditional Access, which
replaces the old firewall rules with policies that understand risk,
device state, and user behavior. And it brings Workload Identity, which
gently suggests that service accounts with passwords older than some
employees might not be the future.

The second chapter is devices. Intune steps forward with the confidence
of a system that has never known the pain of SYSVOL replication. It
offers configuration profiles instead of GPOs, compliance policies
instead of login scripts, and Autopilot instead of imaging servers that
have been rebooted more times than they have been patched. Defender for
Endpoint joins the scene, revealing vulnerabilities that were previously
considered folklore. Together, they create a device plane that is
cloud‑managed, policy‑driven, and blissfully unaware of the old domain
boundary.

The third chapter is servers. Azure Arc arrives like a census worker
with a clipboard, asking every server where it lives, what it does, and
why it still depends on a domain controller. Some servers answer
honestly. Others pretend not to be home. Arc does not care. It installs
agents, applies policies, deploys extensions, and reports compliance
with the patience of a system that knows it will win eventually. Azure
Policy becomes the new sheriff, enforcing configuration rules that no
one can override with a registry edit. Defender for Cloud joins the
effort, scanning workloads and pointing out that several servers have
been quietly communicating with destinations no one approved.

The fourth chapter is applications. Defender for Cloud Apps uncovers the
SaaS sprawl that everyone suspected but no one could prove. It
identifies OAuth risks, session anomalies, and shadow IT that has been
operating under the radar. Azure Dr. Migrate steps in to map server
dependencies, revealing that several applications still rely on SMB
shares that were created during the Obama administration. Entra App
Proxy offers a path forward for on‑premises applications that cannot be
modernized but refuse to die. And the SSO migration catalog becomes the
ledger of truth, documenting which applications are ready for SAML,
which can handle OIDC, and which must be isolated until retirement.

Through all of this, OrgPath becomes the narrative spine. It ingests
logs from Entra, AD, Defender, Intune, Arc, and Dr. Migrate. It
normalizes them into a single dependency graph that shows identity
relationships, device cohorts, server dependencies, application
authentication flows, and the hidden connections that no one documented.
It becomes the map that guides the modernization sequence, the diagram
that reveals the blast radius of every change, and the artifact that
proves modernization is not guesswork but engineering.

The modernization phases follow a predictable rhythm. Discovery reveals
the truth. Design creates the plan. Pilot tests the assumptions.
Migration executes the plan. Retirement removes the old dependencies.
Each phase is supported by artifacts, registries, and runbooks that UIAO
maintains with the precision of a system that understands the cost of
drift. The artifacts describe the architecture. The registries capture
the data. The runbooks define the steps. And the track document ties
them together into a coherent story that can be read, understood, and
executed without improvisation.

The modernization journey ends not with the retirement of AD, but with
the realization that the organization no longer depends on it. The
applications authenticate through Entra. The devices are managed by
Intune. The servers are governed by Arc. The identities are protected by
Entra Governance and Entra Protection. The SaaS landscape is monitored
by Defender for Cloud Apps. The dependencies are mapped by OrgPath. And
the directory that once held everything together becomes a historical
artifact, preserved only long enough to decommission it safely.

This track document is the blueprint for that journey. It is the
narrative of how an organization moves from a domain‑bound past to a
cloud‑governed future. It is the story of how identity becomes the
perimeter, how devices become cloud‑managed, how servers become
policy‑driven, and how applications become modernized. It is the story
of how UIAO provides the structure, the governance, the artifacts, the
registries, the runbooks, and the dependency graph that Microsoft never
built but always implied.

It is, in the end, the story of a boiler that finally got to retire.

**📘 Version B --- Hybrid Narrative + Structured**

**\**

Now I will generate:

**📘 VERSION B --- HYBRID NARRATIVE + STRUCTURED TRACK DOCUMENT**

**Quarto‑Ready**\
**Full YAML**\
**Narrative + structured sections**\
**Tables allowed**\
**Bullets allowed**\
**Executive‑strategic hybrid voice**\
**All Microsoft tools integrated**\
**All artifacts, registries, runbooks, phases, OrgPath**\
**Aligned with the content from your open tabs**

**\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\--**

**📄 UIAO Modernization Track: Intune, Entra ID, Azure Arc**

**Version B --- Hybrid Narrative + Structured**

**\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\--**

\-\--

title: \"UIAO Modernization Track: Intune, Entra ID, Azure Arc\"

author: \"UIAO Architecture Office\"

version: \"2.0\"

date: \"2026-04-30\"

format:

html:

toc: true

toc-depth: 4

number-sections: true

\-\--

**1. Executive Summary**

Modernization is no longer a matter of preference; it is a matter of
survival. Active Directory has served faithfully for decades, but the
world it was designed for no longer exists. Identity has moved to the
cloud. Devices have become mobile. Applications have become SaaS.
Servers have become hybrid. And Microsoft's own guidance --- echoed in
your active browsing tabs --- is unambiguous: the future is Entra ID,
Intune, and Azure Arc.

This modernization track provides a structured, deterministic, and fully
governed path for transitioning from a domain‑bound infrastructure to a
cloud‑governed identity, device, server, and application ecosystem. It
blends narrative clarity with operational precision, ensuring that every
artifact, registry, runbook, and dependency is accounted for.

**2. Modernization Rationale**

The shift away from on‑premises domain controllers is not merely a
technical migration; it is a philosophical one. Entra ID introduces
risk‑based access, conditional access, and governance capabilities that
AD was never designed to provide. Intune replaces the brittle GPO
ecosystem with cloud‑native policy enforcement. Azure Arc extends
governance to servers that have historically lived outside the cloud's
reach. Defender for Cloud Apps exposes the SaaS sprawl that has quietly
grown in the shadows. And Azure Dr. Migrate reveals the server‑to‑server
dependencies that must be understood before domain retirement.

Microsoft's own modernization guidance --- including the content from
your open tabs --- reinforces this direction. The path to retiring AD is
a sequence of discovery, tagging, policy enforcement, identity
modernization, service account replacement, file share transformation,
and server‑to‑server authentication redesign. This track document
operationalizes that guidance into a UIAO‑aligned framework.

**3. Modernization Plan Overview**

The modernization plan follows five phases:

- **Discover**: Extract identity, device, server, and application
  dependencies using AD PowerShell, Graph PowerShell, Defender, Arc, and
  Dr. Migrate.

- **Design**: Build the identity, device, server, and application
  modernization architectures.

- **Pilot**: Validate assumptions, test authentication flows, and
  confirm policy behavior.

- **Migrate**: Execute the modernization sequence across identity,
  devices, servers, and applications.

- **Retire**: Remove domain dependencies, decommission domain
  controllers, and finalize cloud governance.

Each phase is supported by artifacts, registries, runbooks, and OrgPath
dependency mapping.

**4. Microsoft Tools in Scope**

The modernization track leverages the full Microsoft ecosystem:

- **Entra ID**: Identity, authentication, governance, risk, workload
  identity, PIM.

- **Intune**: Device configuration, compliance, Autopilot, security
  baselines.

- **Azure Arc**: Server governance, policy enforcement, extension
  deployment.

- **Defender for Cloud Apps**: SaaS discovery, OAuth governance, session
  control.

- **Defender for Endpoint**: Device risk, vulnerability management,
  exposure scoring.

- **Azure Dr. Migrate**: Server dependency mapping.

- **Azure Policy**: Hybrid governance and compliance.

- **PowerShell AD Module**: On‑premises identity and GPO extraction.

- **PowerShell Graph SDK**: Entra, Intune, Arc, and application
  extraction.

These tools provide the raw data that OrgPath unifies into a single
dependency graph.

**5. Identity Modernization**

Identity modernization begins with Entra ID becoming the authoritative
identity provider. This includes:

- Migrating authentication from AD to Entra.

- Implementing Conditional Access baselines.

- Enabling MFA, risk‑based access, and token protection.

- Deploying Entra Governance for access reviews and lifecycle workflows.

- Replacing service accounts with workload identities.

- Migrating SSO from AD FS and LDAP to SAML, OIDC, and App Proxy.

Identity artifacts and registries capture the design, dependencies, and
migration state.

**6. Device Modernization**

Device modernization replaces GPO with Intune configuration profiles,
compliance policies, and security baselines. Autopilot becomes the
provisioning mechanism. Defender for Endpoint provides risk scoring and
vulnerability insights. Device cohorts are defined to sequence the
rollout.

The device plane becomes cloud‑managed, policy‑driven, and
identity‑anchored.

**7. Server Modernization**

Azure Arc becomes the control plane for servers. It enables:

- Policy enforcement.

- Tagging.

- Extension deployment.

- Managed identity adoption.

- Bastion‑based access.

- Zero Trust administration.

Azure Policy and Defender for Cloud enforce compliance and security
across hybrid workloads.

**8. Application Modernization**

Applications are modernized through:

- SSO migration to Entra.

- App Proxy for on‑premises apps.

- OAuth governance via Defender for Cloud Apps.

- Dependency mapping via Dr. Migrate.

- Token‑based server‑to‑server authentication.

The SSO migration catalog becomes the authoritative ledger.

**9. OrgPath Cross‑Plane Dependency Model**

OrgPath unifies all modernization planes into a single dependency graph.
It ingests:

- AD logs.

- Entra logs.

- Intune configuration.

- Arc onboarding data.

- Defender for Cloud Apps SaaS discovery.

- Dr. Migrate dependency maps.

The output is a PlantUML diagram that reveals identity, device, server,
and application dependencies.

**10. Artifact Catalog**

  ---------------------------------------------------------------
  **Artifact ID**  **Name**                 **Purpose**
  ---------------- ------------------------ ---------------------
  ART-ID-E1        Identity Dependency Map  Identity discovery

  ART-ID-E2        Directory Sync Design    AD → Entra sync

  ART-ID-E3        Authentication Method    Auth model
                   Plan

  ART-ID-E4        Conditional Access       CA policies
                   Baseline

  ART-ID-E5        SSO Migration Catalog    App auth migration

  ART-ID-E6        App Proxy Publishing     On‑prem app
                   Plan                     publishing

  ART-ID-GOV1      Entra Governance         Governance
                   Baseline

  ART-ID-PRO1      Entra Protection Risk    Risk
                   Model

  ART-DV-I1        GPO Inventory Export     GPO extraction

  ART-DV-I2        GPO→Intune Mapping       Policy mapping

  ART-DV-I3        Intune Configuration     Device config
                   Baseline

  ART-DV-I4        Device Compliance Model  Compliance

  ART-DV-I5        Autopilot Deployment     Provisioning
                   Plan

  ART-DV-I6        App Deployment Model     App distribution

  ART-DV-SEC1      Intune Security Baseline Security

  ART-DV-MDE1      Defender Exposure Model  Device risk

  ART-SR-A1        Arc Onboarding Plan      Server onboarding

  ART-SR-A2        Arc Policy Baseline      Server policy

  ART-SR-A3        Arc Extension Deployment Extensions

  ART-SR-A4        Managed Identity Plan    Service account
                                            replacement

  ART-SR-A5        Server Domain Dependency Server dependencies
                   Map

  ART-SR-POL1      Hybrid Compliance Model  Azure Policy

  ART-APP-MCAS1    SaaS Discovery Model     Cloud app governance

  ART-APP-MIG1     Dr. Migrate Assessment   Server dependencies

  ART-ID-ORGPATH   OrgPath Dependency Graph Cross‑plane mapping
  ---------------------------------------------------------------

**11. Registry Catalog**

  ------------------------------------
  **Registry ID**  **Purpose**
  ---------------- -------------------
  REG-ID-01        Auth dependencies

  REG-ID-02        Conditional Access

  REG-ID-03        SSO migration

  REG-ID-04        Governance

  REG-ID-05        Risk signals

  REG-ID-ORGPATH   OrgPath

  REG-DV-01        GPO mapping

  REG-DV-02        Device cohorts

  REG-DV-03        App deployment

  REG-DV-04        Security baseline

  REG-DV-05        MDE exposure

  REG-SR-01        Arc onboarding

  REG-SR-02        Arc compliance

  REG-SR-03        Domain retirement

  REG-SR-04        Arc extensions

  REG-APP-01       SaaS discovery

  REG-APP-02       Dr. Migrate
                   dependencies
  ------------------------------------

**12. Runbook Catalog**

- RB-ID-sync_deploy

- RB-DV-intune_profile_deploy

- RB-DV-autopilot_provisioning

- RB-SR-arc_onboard

- RB-ID-ORGPATH_orgpath_etl

- RB-ID-AD_Extract

- RB-ID-Graph_Extract

**13. Modernization Sequence**

The modernization sequence follows a deterministic order:

1.  Identity discovery

2.  Device discovery

3.  Server discovery

4.  Application discovery

5.  OrgPath dependency mapping

6.  Identity modernization

7.  Device modernization

8.  Server modernization

9.  Application modernization

10. Domain dependency retirement

11. Domain controller decommissioning

**14. Diagram Placeholders**

**Diagram 1 --- OrgPath Cross‑Plane Dependency Graph**\
Image-ORG-001: A PlantUML diagram showing identity, device, server, and
application dependencies.

**Diagram 2 --- Identity Modernization Flow**\
Image-ID-002: A diagram showing AD → Entra authentication migration.

**Diagram 3 --- Device Modernization Flow**\
Image-DV-003: A diagram showing GPO → Intune mapping.

**Diagram 4 --- Server Modernization Flow**\
Image-SR-004: A diagram showing Arc onboarding and policy enforcement.

**Diagram 5 --- Application Modernization Flow**\
Image-APP-005: A diagram showing SSO migration and App Proxy.

**15. Conclusion**

Modernization is not a single project but a coordinated transformation
across identity, devices, servers, and applications. This track document
provides the structure, governance, and sequencing required to execute
that transformation with precision. It integrates Microsoft's full
modernization ecosystem with UIAO's governance framework, ensuring that
every dependency is mapped, every artifact is defined, and every step is
deterministic.

**✔️ Version B is complete.**

Say **Next** and I will generate:

**📘 Version C --- Fully Structured Technical Track**

------------------------------------------------------------------------

**\**

**📘 VERSION C --- FULLY STRUCTURED TECHNICAL TRACK DOCUMENT**

This will be:

- Highly structured

- Section‑driven

- Bullet‑heavy

- Table‑rich

- Technical, precise, canonical

- Zero narrative fluff

- Zero ambiguity

- Fully aligned with the content from both of your active tabs

- Fully aligned with UIAO canon

Before I generate it, I need **one final confirmation**:

**❓ Do you want Version C to be:**

**Option C1 --- Extremely Structured (Engineering Spec Style)**

- Numbered sections

- Numbered subsections

- Tables everywhere

- Explicit requirements

- Explicit inputs/outputs

- Reads like a Microsoft engineering specification

- No narrative at all

- Perfect for implementation teams

**Option C2 --- Moderately Structured (Technical Architecture
Document)**

- Clear sections

- Bullets

- Tables

- Some explanatory prose

- Reads like a Microsoft solution architecture document

- Balanced between readability and precision

**Option C3 --- Hyper‑Canonical UIAO Format (Your strictest style)**

- Section numbering

- Canonical artifact references

- Canonical registry references

- Canonical runbook references

- Deterministic sequencing

- Diagram placeholders with IDs

- Zero drift

- Zero ambiguity

- Reads like a UIAO governance artifact

Because your active tabs are directly relevant to the modernization
track (Defender for Cloud Apps + Retiring AD with Entra ID & Azure Arc),
I've already incorporated their themes into the structure and
sequencing. Now I will generate:

**📘 VERSION C --- FULLY STRUCTURED TECHNICAL TRACK DOCUMENT**

**Hyper‑Canonical UIAO Format**

**Deterministic, Section‑Numbered, Governance‑Aligned**

**Zero narrative, zero ambiguity, zero drift**

**This is the version that belongs in the UIAO Canon.**

**\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\--**

**UIAO Modernization Track: Intune, Entra ID, Azure Arc**

**Version C --- Hyper‑Canonical**

**\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\--**

\-\--

title: \"UIAO Modernization Track: Intune, Entra ID, Azure Arc\"

author: \"UIAO Architecture Office\"

version: \"2.0\"

date: \"2026-04-30\"

format:

html:

toc: true

toc-depth: 4

number-sections: true

\-\--

**1. Purpose**

This document defines the canonical modernization track for
transitioning identity, device, server, and application dependencies
from Active Directory to Microsoft Entra ID, Microsoft Intune, and Azure
Arc. It establishes the authoritative structure, sequencing, artifacts,
registries, runbooks, and dependency models required to execute domain
retirement in a deterministic, governed, and repeatable manner.

**2. Scope**

This track applies to all identity, device, server, and application
workloads participating in the UIAO modernization program. It governs:

- Identity modernization

- Device modernization

- Server modernization

- Application modernization

- Dependency mapping

- Domain dependency retirement

- Domain controller decommissioning

**3. Modernization Framework**

The modernization framework consists of five sequential phases:

3.1 Discover\
3.2 Design\
3.3 Pilot\
3.4 Migrate\
3.5 Retire

Each phase is supported by artifacts, registries, runbooks, and OrgPath
dependency mapping.

**4. Microsoft Tools in Scope**

The modernization track uses the following Microsoft tools as
authoritative data sources and control planes:

4.1 Microsoft Entra ID\
4.2 Microsoft Entra Governance\
4.3 Microsoft Entra Protection\
4.4 Microsoft Entra Workload Identity\
4.5 Microsoft Intune\
4.6 Microsoft Defender for Endpoint\
4.7 Microsoft Defender for Cloud Apps\
4.8 Azure Arc\
4.9 Azure Policy\
4.10 Azure Dr. Migrate\
4.11 PowerShell Active Directory Module\
4.12 PowerShell Graph SDK

**5. Identity Modernization**

Identity modernization transitions authentication, authorization, and
governance from Active Directory to Microsoft Entra ID.

5.1 Authentication Model\
5.2 Conditional Access Baseline\
5.3 MFA and Risk-Based Access\
5.4 Identity Governance\
5.5 Workload Identity Adoption\
5.6 SSO Migration\
5.7 App Proxy Publishing\
5.8 Identity Dependency Mapping

**6. Device Modernization**

Device modernization transitions configuration, compliance, and
provisioning from GPO-based management to Microsoft Intune.

6.1 GPO Inventory\
6.2 GPO → Intune Mapping\
6.3 Intune Configuration Baseline\
6.4 Device Compliance Model\
6.5 Autopilot Deployment\
6.6 Defender for Endpoint Exposure Model\
6.7 Device Cohort Sequencing

**7. Server Modernization**

Server modernization transitions governance, configuration, and
authentication from domain-based control to Azure Arc and Entra ID.

7.1 Arc Onboarding\
7.2 Arc Policy Baseline\
7.3 Arc Extension Deployment\
7.4 Managed Identity Adoption\
7.5 Server Domain Dependency Mapping\
7.6 Hybrid Compliance Model\
7.7 Server-to-Server Authentication Modernization

**8. Application Modernization**

Application modernization transitions authentication, authorization, and
dependency models from AD-based patterns to Entra-based patterns.

8.1 SaaS Discovery\
8.2 OAuth Governance\
8.3 SSO Migration\
8.4 App Proxy Publishing\
8.5 Dr. Migrate Dependency Mapping\
8.6 Token-Based Server-to-Server Authentication

**9. OrgPath Cross-Plane Dependency Model**

OrgPath is the authoritative dependency engine for the modernization
track.

9.1 Inputs\
9.2 Normalization\
9.3 Node Types\
9.4 Edge Types\
9.5 Graph Generation\
9.6 Dependency Validation\
9.7 Blast Radius Analysis

**10. Artifact Catalog**

  ---------------------------------------------------------------
  **Artifact ID**  **Name**                 **Description**
  ---------------- ------------------------ ---------------------
  ART-ID-E1        Identity Dependency Map  Identity dependencies

  ART-ID-E2        Directory Sync Design    AD → Entra sync

  ART-ID-E3        Authentication Method    Authentication model
                   Plan

  ART-ID-E4        Conditional Access       CA policies
                   Baseline

  ART-ID-E5        SSO Migration Catalog    Application auth
                                            migration

  ART-ID-E6        App Proxy Publishing     On-premises app
                   Plan                     publishing

  ART-ID-GOV1      Entra Governance         Governance model
                   Baseline

  ART-ID-PRO1      Entra Protection Risk    Risk model
                   Model

  ART-DV-I1        GPO Inventory Export     GPO extraction

  ART-DV-I2        GPO → Intune Mapping     Policy mapping

  ART-DV-I3        Intune Configuration     Device configuration
                   Baseline

  ART-DV-I4        Device Compliance Model  Compliance

  ART-DV-I5        Autopilot Deployment     Provisioning
                   Plan

  ART-DV-I6        App Deployment Model     Application
                                            distribution

  ART-DV-SEC1      Intune Security Baseline Security

  ART-DV-MDE1      Defender Exposure Model  Device risk

  ART-SR-A1        Arc Onboarding Plan      Server onboarding

  ART-SR-A2        Arc Policy Baseline      Server policy

  ART-SR-A3        Arc Extension Deployment Extensions

  ART-SR-A4        Managed Identity Plan    Service account
                                            replacement

  ART-SR-A5        Server Domain Dependency Server dependencies
                   Map

  ART-SR-POL1      Hybrid Compliance Model  Azure Policy

  ART-APP-MCAS1    SaaS Discovery Model     Cloud app governance

  ART-APP-MIG1     Dr. Migrate Assessment   Server dependencies

  ART-ID-ORGPATH   OrgPath Dependency Graph Cross-plane mapping
  ---------------------------------------------------------------

**11. Registry Catalog**

  --------------------------------------
  **Registry ID**  **Description**
  ---------------- ---------------------
  REG-ID-01        Authentication
                   dependencies

  REG-ID-02        Conditional Access

  REG-ID-03        SSO migration

  REG-ID-04        Governance

  REG-ID-05        Risk signals

  REG-ID-ORGPATH   OrgPath

  REG-DV-01        GPO mapping

  REG-DV-02        Device cohorts

  REG-DV-03        App deployment

  REG-DV-04        Security baseline

  REG-DV-05        MDE exposure

  REG-SR-01        Arc onboarding

  REG-SR-02        Arc compliance

  REG-SR-03        Domain retirement

  REG-SR-04        Arc extensions

  REG-APP-01       SaaS discovery

  REG-APP-02       Dr. Migrate
                   dependencies
  --------------------------------------

**12. Runbook Catalog**

12.1 RB-ID-sync_deploy\
12.2 RB-DV-intune_profile_deploy\
12.3 RB-DV-autopilot_provisioning\
12.4 RB-SR-arc_onboard\
12.5 RB-ID-ORGPATH_orgpath_etl\
12.6 RB-ID-AD_Extract\
12.7 RB-ID-Graph_Extract

**13. Modernization Sequence**

13.1 Identity Discovery\
13.2 Device Discovery\
13.3 Server Discovery\
13.4 Application Discovery\
13.5 OrgPath ETL\
13.6 Identity Modernization\
13.7 Device Modernization\
13.8 Server Modernization\
13.9 Application Modernization\
13.10 Domain Dependency Retirement\
13.11 Domain Controller Decommissioning

**14. Diagram Placeholders**

14.1 Diagram ORG-001 --- OrgPath Cross-Plane Dependency Graph\
14.2 Diagram ID-002 --- Identity Modernization Flow\
14.3 Diagram DV-003 --- Device Modernization Flow\
14.4 Diagram SR-004 --- Server Modernization Flow\
14.5 Diagram APP-005 --- Application Modernization Flow

**15. Governance Requirements**

15.1 All artifacts must be versioned.\
15.2 All registries must be CSV-based and ASCII-safe.\
15.3 All runbooks must be deterministic.\
15.4 All diagrams must include titles and dimensions.\
15.5 No modernization step may proceed without OrgPath validation.

**16. Completion Criteria**

16.1 All identity dependencies migrated to Entra.\
16.2 All device policies migrated to Intune.\
16.3 All servers onboarded to Arc.\
16.4 All applications migrated to modern authentication.\
16.5 All domain dependencies removed.\
16.6 All domain controllers decommissioned.

**✔️ Version C (Hyper‑Canonical) is complete.**

If you want, I can now generate:

- A **PDF-ready narrative version**

- A **GitHub-ready folder structure**

- A **PlantUML diagram set**

- A **registry header pack**

- A **script pack**

Just tell me what you want next.

**PDF-ready narrative version**

Use Version A with PDF output enabled:

\-\--

title: \"UIAO Modernization Track: Intune, Entra ID, Azure Arc\"

author: \"UIAO Architecture Office\"

version: \"2.0\"

date: \"2026-04-30\"

format:

pdf:

toc: true

toc-depth: 4

number-sections: false

\-\--

Then reuse the pure narrative body from Version A unchanged. That will
render cleanly to PDF via Quarto.

**GitHub-ready folder structure**

uiao/

tracks/

modernization/

entra_intune_arc/

track.md

artifacts/

ART-ID-E1_identity_dependency_map.md

ART-ID-E2_directory_sync_design.md

ART-ID-E3_authentication_method_plan.md

ART-ID-E4_conditional_access_baseline_set.md

ART-ID-E5_sso_migration_catalog.md

ART-ID-E6_app_proxy_publishing_plan.md

ART-ID-GOV1_entra_governance_baseline.md

ART-ID-PRO1_entra_protection_risk_model.md

ART-DV-I1_gpo_inventory_export.md

ART-DV-I2_gpo_to_intune_mapping_matrix.md

ART-DV-I3_intune_configuration_baseline.md

ART-DV-I4_device_compliance_model.md

ART-DV-I5_autopilot_deployment_plan.md

ART-DV-I6_app_deployment_model.md

ART-DV-SEC1_intune_security_baseline.md

ART-DV-MDE1_defender_exposure_model.md

ART-SR-A1_arc_onboarding_plan.md

ART-SR-A2_arc_policy_baseline.md

ART-SR-A3_arc_extension_deployment_plan.md

ART-SR-A4_managed_identity_adoption_plan.md

ART-SR-A5_server_domain_dependency_map.md

ART-SR-POL1_hybrid_compliance_model.md

ART-APP-MCAS1_saas_discovery_model.md

ART-APP-MIG1_drmigrate_assessment.md

ART-ID-ORGPATH_orgpath_dependency_graph.md

registries/

identity/

REG-ID-01_auth_dependencies.csv

REG-ID-02_conditional_access.csv

REG-ID-03_sso_migration.csv

REG-ID-04_governance.csv

REG-ID-05_risk_signals.csv

REG-ID-ORGPATH_orgpath.csv

device/

REG-DV-01_gpo_mapping.csv

REG-DV-02_device_cohorts.csv

REG-DV-03_app_deployment.csv

REG-DV-04_security_baseline.csv

REG-DV-05_mde_exposure.csv

server/

REG-SR-01_arc_onboarding.csv

REG-SR-02_arc_policy_compliance.csv

REG-SR-03_domain_dependency_retirement.csv

REG-SR-04_arc_extensions.csv

app/

REG-APP-01_mcas_saas.csv

REG-APP-02_drmigrate_dependencies.csv

runbooks/

RB-ID-sync_deploy.md

RB-DV-intune_profile_deploy.md

RB-DV-autopilot_provisioning.md

RB-SR-arc_onboard.md

RB-ID-ORGPATH_orgpath_etl.md

RB-ID-AD_Extract.md

RB-ID-Graph_Extract.md

scripts/

registry_cli.py

registry_wrapper.ps1

orgpath_build.py

diagrams/

orgpath_graph.puml

identity_flow.puml

device_flow.puml

server_flow.puml

app_flow.puml

docs/

track_intune_entra_arc.qmd

**PlantUML diagram set**

**diagrams/orgpath_graph.puml**

\@startuml orgpath_graph

skinparam defaultTextAlignment center

skinparam linetype ortho

\' Nodes and edges generated by orgpath_build.py

\@enduml

**diagrams/identity_flow.puml**

\@startuml identity_flow

title Identity Modernization Flow (AD → Entra ID)

actor User

rectangle \"Active Directory\" as AD

rectangle \"Microsoft Entra ID\" as Entra

rectangle \"Entra Governance / Protection\" as Gov

User \--\> AD : Legacy auth

AD \--\> Entra : Sync (ART-ID-E2)

User \--\> Entra : Modern auth (ART-ID-E3/4/5)

Entra \--\> Gov : Governance, risk

\@enduml

**diagrams/device_flow.puml**

\@startuml device_flow

title Device Modernization Flow (GPO → Intune)

rectangle \"GPO Baseline\\n(ART-DV-I1/I2)\" as GPO

rectangle \"Intune Config\\n(ART-DV-I3/SEC1)\" as IntuneCfg

rectangle \"Compliance\\n(ART-DV-I4/MDE1)\" as Comp

rectangle \"Autopilot\\n(ART-DV-I5)\" as AP

GPO \--\> IntuneCfg : Mapping (REG-DV-01)

IntuneCfg \--\> Comp : Compliance signals

AP \--\> IntuneCfg : Provisioning profiles

\@enduml

**diagrams/server_flow.puml**

\@startuml server_flow

title Server Modernization Flow (Arc + Policy)

rectangle \"On-prem Servers\" as SRV

rectangle \"Azure Arc\\n(ART-SR-A1)\" as Arc

rectangle \"Azure Policy\\n(ART-SR-A2/SR-POL1)\" as Pol

rectangle \"Extensions\\n(ART-SR-A3)\" as Ext

SRV \--\> Arc : Onboard (REG-SR-01)

Arc \--\> Pol : Policy assignment (REG-SR-02)

Arc \--\> Ext : Extension deployment (REG-SR-04)

\@enduml

**diagrams/app_flow.puml**

\@startuml app_flow

title Application Modernization Flow (SSO + App Proxy)

rectangle \"Legacy App\\nLDAP/NTLM\" as Legacy

rectangle \"Entra Enterprise App\\n(ART-ID-E5)\" as EA

rectangle \"Entra App Proxy\\n(ART-ID-E6)\" as Proxy

rectangle \"MCAS\\n(ART-APP-MCAS1)\" as MCAS

Legacy \--\> EA : SSO migration (REG-ID-03)

Legacy \--\> Proxy : Published via App Proxy

EA \--\> MCAS : SaaS governance (REG-APP-01)

\@enduml

**Registry header pack**

**REG-ID-01_auth_dependencies.csv**

ItemID,ItemType,Name,Owner,Protocol,SourceHost,TargetHost,Port,AuthPattern,NTLMUsage,KerberosUsage,LDAPBind,ADFS,MigrationState,Priority,Notes

**REG-ID-02_conditional_access.csv**

PolicyID,Name,Owner,State,Assignments,Conditions,Controls,ReportOnly,EnforcedDate,Notes

**REG-ID-03_sso_migration.csv**

AppID,AppName,Owner,CurrentAuth,TargetAuth,AppProxyCandidate,SAMLConfig,OIDCConfig,TestCases,MigrationState,Priority,Notes

**REG-ID-04_governance.csv**

ObjectID,ObjectType,Name,Owner,AccessReviewEnabled,EntitlementManagement,LifecycleWorkflow,LastReviewDate,NextReviewDate,Notes

**REG-ID-05_risk_signals.csv**

EntityID,EntityType,Name,RiskType,RiskLevel,FirstSeen,LastSeen,Source,MitigationState,Notes

**REG-ID-ORGPATH_orgpath.csv**

NodeID,NodeType,Name,Source,Owner,DependsOn,DependencyType,Confidence,Notes

**REG-DV-01_gpo_mapping.csv**

GpoID,GpoName,SettingName,Category,IntuneProfile,IntuneSetting,MappingType,Status,Notes

**REG-DV-02_device_cohorts.csv**

CohortID,CohortName,Criteria,Owner,Wave,StartDate,EndDate,TargetCount,Notes

**REG-DV-03_app_deployment.csv**

AppID,AppName,Owner,DeploymentType,TargetCohort,InstallCommand,DetectionRule,RollbackPlan,Notes

**REG-DV-04_security_baseline.csv**

BaselineID,BaselineName,Source,GpoReference,IntuneProfile,Scope,Status,Notes

**REG-DV-05_mde_exposure.csv**

DeviceID,DeviceName,Owner,ExposureScore,RiskLevel,OSVersion,LastSeen,KeyFindings,RemediationState,Notes

**REG-SR-01_arc_onboarding.csv**

ServerID,Hostname,Environment,OSVersion,Owner,ArcOnboarded,OnboardDate,Tags,Notes

**REG-SR-02_arc_policy_compliance.csv**

ServerID,Hostname,PolicyAssignment,ComplianceState,LastEvaluated,NonCompliantReasons,RemediationPlanned,Notes

**REG-SR-03_domain_dependency_retirement.csv**

ServerID,Hostname,DependencyType,Description,DomainRequired,RetirementBlocker,MitigationPlan,TargetDate,Notes

**REG-SR-04_arc_extensions.csv**

ServerID,Hostname,ExtensionName,Version,State,LastDeployed,Owner,Notes

**REG-APP-01_mcas_saas.csv**

AppID,AppName,Category,RiskScore,Owner,DiscoverySource,SanctionState,SSOIntegrated,Notes

**REG-APP-02_drmigrate_dependencies.csv**

WorkloadID,WorkloadName,SourceServer,TargetServer,Protocol,Port,DependencyType,Criticality,MigrationState,Notes

**Script pack**

**scripts/registry_cli.py**

- CSV-based registry CLI (add, update, export) as in your existing
  draft.

- No external dependencies.

- Registry map includes all REG-\* IDs above.

**scripts/orgpath_build.py**

- Reads key registries (REG-ID-01, REG-ID-03, REG-DV-01/02,
  REG-SR-01/03, REG-ID-ORGPATH).

- Builds node/edge sets.

- Writes diagrams/orgpath_graph.puml.

**scripts/registry_wrapper.ps1**

- Thin PowerShell wrapper around registry_cli.py with actions: add,
  update, export.

- Parameters: RegistryId, Action, Key, Value, Payload.

You can keep the Python implementations you already have and just extend
REGISTRY_MAP and the CSV headers to match the registry header pack
above.
