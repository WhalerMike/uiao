---
document_id: MOD_G
title: "Appendix G — Diagram Pack (Text-Rendered)"
version: "1.0"
status: DRAFT
classification: CANONICAL
owner: Michael Stratton
created_at: 2026-04-18
updated_at: 2026-04-18
boundary: GCC-Moderate
namespace: MOD
parent_canon: UIAO_008
---

# Appendix G — Diagram Pack (Text-Rendered)

Purpose

This appendix provides all architectural, workflow, and structural diagrams for the Governance OS in text-rendered ASCII format. These diagrams are the canonical visual representations; no external diagramming tools or image formats are required.

Scope

Covers eight primary diagrams representing the OrgTree hierarchy, governance layer stack, migration flow, drift detection loop, two-brain execution model, SLA escalation ladder, identity lifecycle, and governance state machine.

Canonical Structure

Each diagram uses ASCII box-drawing characters (+, -, |) and arrow characters (-->, <--) with clear labels. Diagrams are self-contained and require no external rendering.

Technical Scaffolding

Diagram 1: OrgTree Hierarchy

+-------+                               |  ORG  |                               +---+---+             +-----------+---------+---------+-----------+             |           |         |         |           |         +---+---+  +----+--+  +--+---+  +--+---+  +---+---+         |ORG-FIN|  |ORG-HR |  |ORG-IT|  |ORG-OPS|  |ORG-LEG|         +---+---+  +---+---+  +--+---+  +---+---+  +---+---+             |          |         |           |          |      +------+---+   +--+--+   +-+------+  +-+--+   +--+---+      |    |     |   |     |   |   |    |   |    |   |      |    AP    AR   BUD  REC  BEN  SEC INF DEV  LOG  FAC COM   LIT      |                        |   +--+--+               +----+----+   |     |               |         |  EAST  WEST            SOC       IAM                         |                     +---+---+                     |       |                    T1      T2

Diagram 2: Governance Layer Stack

+=======================================================================+ |  GOVERNANCE LAYER                                                      | |  +-------------------+  +------------------+  +-------------------+   | |  | Drift Detection   |  | Enforcement Tests|  | Telemetry + SLA   |   | |  +--------+----------+  +--------+---------+  +--------+----------+   | |           |                      |                      |              | +=======================================================================+             |                      |                      |             v                      v                      v +=======================================================================+ |  POLICY LAYER                                                          | |  +-------------------+  +------------------+  +-------------------+   | |  | RBAC Assignments  |  | Conditional Access|  | Lifecycle Wkflows|   | |  +--------+----------+  +--------+---------+  +--------+----------+   | +=======================================================================+             |                      |                      |             v                      v                      v +=======================================================================+ |  STRUCTURE LAYER                                                       | |  +-------------------+  +------------------+  +-------------------+   | |  | OrgPath Attributes|  | Dynamic Groups   |  | Admin Units       |   | |  +--------+----------+  +--------+---------+  +--------+----------+   | +=======================================================================+             |                      |                      |             v                      v                      v +=======================================================================+ |  IDENTITY LAYER                                                        | |  +-------------------+  +------------------+  +-------------------+   | |  | User Accounts     |  | Group Objects    |  | Service Principals|   | |  +-------------------+  +------------------+  +-------------------+   | +=======================================================================+

Diagram 3: Migration Flow (8 Phases)

[Phase 1]     [Phase 2]       [Phase 3]        [Phase 4] Discovery --> OrgPath     --> Attribute    --> Dynamic Group               Mapping         Provisioning     Deployment                                                     |                                                     v [Phase 8]     [Phase 7]       [Phase 6]        [Phase 5] Decommission <-- Cutover  <-- Validation   <-- AU                                                 Deployment

Diagram 4: Drift Detection Loop

+----------+       +-----------+       +----------+     | SNAPSHOT |------>|  COMPARE  |------>| CLASSIFY |     | (current)|       | (vs base) |       | (category|     +----------+       +-----------+       |+ severity)|          ^                                  +----+-----+          |                                       |          |                                       v     +----------+                           +-----------+     |  VERIFY  |<--------------------------| ALERT +   |     | (re-scan)|                           | ASSIGN    |     +----+-----+                           +-----+-----+          ^                                       |          |                                       v          |                                 +-----------+          +-------------------------------- | REMEDIATE |                                            +-----------+

Diagram 5: Two-Brain Execution Model

+----------------------------------+     +----------------------------------+ |        COPILOT (Govern)          |     |     EXECUTION SUBSTRATE (Execute)      | |                                  |     |                                  | |  +----------------------------+  |     |  +----------------------------+  | |  | Canonical Review           |  |     |  | PowerShell Execution      |  | |  | Policy Enforcement         |  |     |  | Graph API Calls           |  | |  | Validation                 |  |     |  | Tenant Provisioning       |  | |  | Instruction Generation     |  |     |  | Report Generation         |  | |  | Provenance Recording       |  |     |  | Structured Results        |  | |  +----------------------------+  |     |  +----------------------------+  | |                                  |     |                                  | +----------------+-----------------+     +----------------+-----------------+                  |                                        ^                  | Instruction Set (JSON)                  |                  +--------------------------------------> |                                                           |                  <----------------------------------------+                  | Execution Result (JSON)                 |                  |                                        |      +-----------v-----------+                            |      | Validate Result       |                            |      | Record Provenance     |                            |      +-----------------------+                            |

Diagram 6: SLA Escalation Ladder

Time Elapsed        Escalation Level        Action -------------------------------------------------------------- 0%                  [NORMAL]                Owner working      | 75% of SLA         [LEVEL 1: WARNING]      Notify owner      | 100% of SLA        [LEVEL 2: BREACH]       Notify manager      |                                      Escalate ticket 150% of SLA        [LEVEL 3: GOVERNANCE]    Governance Board      |                                      Backup owner 200% of SLA        [LEVEL 4: EMERGENCY]     Executive notify   or CRITICAL                               4-hour mandatory                                             remediation

Diagram 7: Identity Lifecycle

+-----------+    provision    +----------+    activate    +--------+ | PRE-HIRE  |--------------->| ONBOARD  |------------->| ACTIVE | +-----------+                +----------+               +---+----+                                                             |                               +-------------+          transfer                               | TRANSFERRING|<---------+                               +------+------+                                      |                                 re-activate                                      |                                      v                               +--------+     deactivate   +------------+                               | ACTIVE |---------------->| OFFBOARDING|                               +--------+                  +-----+------+                                                                 |                                                            deprovision                                                                 v                                                           +-----------+                                                           | SUSPENDED |                                                           +-----+-----+                                                                 |                                                            after 90 days                                                                 v                                                           +---------+                                                           | DELETED |                                                           +---------+

Diagram 8: Governance State Machine

+-------+  submit   +----------+  validate  +----------+ | DRAFT |---------->| PROPOSED |---------->| UNDER    | +-------+           +----+-----+           | REVIEW   |     ^                    |                  +----+-----+     |                 reject                     |     |                    v                  approve|reject     |              +-----------+                  |    |     +-<return------| REJECTED  |                  |    |                    +-----------+                  v    v                                            +----------+ +-----------+                                            | APPROVED |  | REJECTED |                                            +----+-----+  +-----------+                                                 |                                            canonize                                                 v                                           +-----------+                                           | CANONICAL |                                           +-----+-----+                                                 |                                            deprecate                                                 v                                           +------------+                                           | DEPRECATED |                                           +-----+------+                                                 |                                            after retention                                                 v                                           +----------+                                           | ARCHIVED |                                           +----------+

Boundary Rules

All diagrams represent systems and interactions within the M365 GCC-Moderate boundary unless explicitly labeled as a boundary interface.

No diagram may depict integration with out-of-scope services.

Drift Considerations

Diagrams are governance artifacts; if the architecture they depict changes, the diagrams must be updated through the Governance Artifact Update workflow (Appendix E, Workflow 8).

Governance Alignment

These diagrams implement the Governance OS commitment to transparency and determinism. Every architectural relationship is visible, every state transition is documented, and every boundary is marked.
