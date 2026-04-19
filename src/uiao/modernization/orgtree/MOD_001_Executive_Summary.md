---
document_id: MOD_001
title: "Entra OrgTree Modernization — Executive Summary & Architecture"
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

# Entra OrgTree Modernization Architecture — Governance OS

**Canonical Front Door for Identity Modernization**

April 2026 | Full A–Z Canonical Document Suite

Entra OrgTree Modernization Architecture — Governance OS

Canonical Front Door for Identity Modernization

April 2026  |  Full A–Z Canonical Document Suite

Section 1: Executive Summary

The UIAO Governance Operating System (Governance OS) is a complete, deterministic, drift-resistant operating system for identity modernization using Microsoft Entra ID within the M365 GCC-Moderate boundary. It provides every artifact, schema, decision tree, validation module, and operational runbook required to design, deploy, govern, and sustain a modern identity hierarchy—the OrgTree—without ambiguity, without discretionary interpretation, and without dependency on any single human actor.

The OrgTree is a hierarchical identity structure that replaces legacy Organizational Unit (OU)-based Active Directory models with a portable, attribute-driven hierarchy encoded in Entra ID extension attributes. Each identity object carries an OrgPath—a deterministic, codebook-validated string such as ORG-IT-SEC-SOC—that encodes its exact position in the organizational hierarchy. Dynamic groups, Administrative Units, role-based delegation, Conditional Access policies, and telemetry all derive from this single canonical attribute, eliminating structural duplication and ensuring that every governance decision is traceable to a single source of truth.

This master document, together with Appendices A through Z, constitutes the full canonical corpus. Every appendix is a standalone, internally complete governance artifact. Taken together, the corpus defines: the codebook of valid OrgPaths (Appendix A), the dynamic groups that implement them (Appendix B), the attribute mappings from legacy to modern (Appendix C), the delegation model (Appendix D), every governance workflow (Appendix E), a step-by-step migration runbook (Appendix F), all architectural diagrams in text-rendered form (Appendix G), the JSON schemas (Appendix H), PowerShell validation modules (Appendix I), enforcement test suites (Appendix J), decision trees (Appendix K), SLA models (Appendix L), drift detection engines (Appendix M), the Execution Substrate execution substrate integration (Appendix N), a mock tenant test harness (Appendix O), boundary impact models (Appendix P), escalation playbooks (Appendix Q), the canonical repository structure (Appendix R), the governance state machine (Appendix S), identity risk scoring (Appendix T), multi-cloud boundary rules (Appendix U), contributor workflows (Appendix V), the error taxonomy (Appendix W), telemetry models (Appendix X), identity graph normalization (Appendix Y), and the complete glossary (Appendix Z).

Section 2: Architecture Overview

The OrgTree architecture is a four-layer governance stack. Each layer has a defined responsibility, a set of canonical artifacts, and explicit dependency relationships with adjacent layers. The architecture is fully contained within the M365 GCC-Moderate SaaS boundary.

2.1 Layered Model

Identity Layer contains the raw identity objects: user accounts, group objects, service principals, and their attributes within Entra ID. This is the substrate upon which all structure is built.

Structure Layer encodes the organizational hierarchy using OrgPath extension attributes, dynamic group membership rules, and Administrative Units. It transforms flat identity objects into a navigable, queryable tree.

Policy Layer applies governance controls through Role-Based Access Control (RBAC), Conditional Access policies, lifecycle workflows, and delegation assignments. Every policy artifact references the Structure Layer—never the Identity Layer directly—ensuring that policy follows structure deterministically.

Governance Layer monitors the entire stack through drift detection, enforcement testing, telemetry collection, SLA tracking, and provenance logging. It is the self-correcting feedback loop that keeps all lower layers in canonical compliance.

2.2 Architecture Diagram

+=========================================================================+ |                        GOVERNANCE LAYER                                  | |  Drift Detection | Enforcement Tests | Telemetry | SLA | Provenance    | +=========================================================================+         |                    |                   |              |         v                    v                   v              v +=========================================================================+ |                          POLICY LAYER                                    | |  RBAC Assignments | Conditional Access | Lifecycle Workflows | Delegation| +=========================================================================+         |                    |                   |              |         v                    v                   v              v +=========================================================================+ |                        STRUCTURE LAYER                                   | |  OrgPath Attributes | Dynamic Groups | Administrative Units             | +=========================================================================+         |                    |                   |              |         v                    v                   v              v +=========================================================================+ |                        IDENTITY LAYER                                    | |  User Accounts | Group Objects | Service Principals | Extension Attrs   | +=========================================================================+         |         v +=========================================================================+ |              M365 GCC-MODERATE SaaS BOUNDARY                             | |  Entra ID | Exchange Online | SharePoint | Teams | Power Platform | Graph| +=========================================================================+

2.3 Governance Perimeter

The governance perimeter is defined by the M365 GCC-Moderate SaaS boundary. Every artifact, every automation script, every API call, and every governance decision must operate within this perimeter. Services outside M365 GCC-Moderate are explicitly out of scope and any artifact that references them is non-canonical. The system operates in Commercial Cloud as governed by FedRAMP unless specifically noted.

Section 3: Governance Principles

Seven principles govern every decision, artifact, and action within the Governance OS. These principles are non-negotiable and apply universally across all appendices.

Principle 1: Deterministic State. Every identity object has exactly one canonical state at any point in time. There is no ambiguity about what an object's OrgPath is, which groups it belongs to, which policies apply to it, or who administers it. If two systems disagree about an object's state, the Governance OS canonical state is authoritative.

Principle 2: Schema Fixity. Schema is fixed; values are flexible. The structure of the OrgPath codebook, the shape of JSON schemas, the format of dynamic group rules, and the layout of governance artifacts are immutable once canonized. Only the values within defined enumerations—specific OrgPath codes, specific group names, specific role assignments—may change, and only through governed workflows defined in Appendix E.

Principle 3: Provenance Traceability. Every change to every governance artifact and every identity object is attributable to a source: a human operator identified by role, an automation engine identified by service principal, or the governance engine itself. Unsigned, unattributed changes are drift by definition.

Principle 4: Drift Resistance. The system detects, classifies, and remediates drift automatically. Drift is any deviation between the canonical state defined in the Governance OS and the actual state observed in the tenant. The drift detection engine (Appendix M) runs continuously, classifies drift by category and severity, and triggers remediation workflows (Appendix E) or escalation playbooks (Appendix Q) as appropriate.

Principle 5: Boundary Enforcement. No governance artifact, automation script, API call, or execution path may extend beyond the M365 GCC-Moderate SaaS boundary. Any artifact that references an out-of-scope service is non-canonical and must be rejected at the validation gate (Appendix V).

Principle 6: Two-Brain Execution. Copilot governs: it performs canonical review, policy enforcement, validation, and governance artifact generation. Execution Substrate executes: it runs PowerShell scripts, makes Graph API calls, provisions tenant configurations, and performs automation scripting. Copilot produces deterministic instruction sets; Execution Substrate executes them without interpretation. This separation ensures that governance logic and execution logic never co-mingle.

Principle 7: Tenant Agnosticism. All artifacts are portable across any M365 GCC-Moderate tenant. No artifact contains tenant-specific identifiers, user principal names, tenant GUIDs, or environment-specific configuration values. All tenant-specific values are injected at deployment time through parameterized variables.

Section 4: Document Corpus Map

The following table enumerates all 26 appendices that comprise the full canonical corpus.

Section 5: Governance Lifecycle

Every governance artifact traverses a defined lifecycle from creation to archival. The lifecycle is a directed acyclic state machine with seven primary states and governed transitions. No artifact may skip states, and every transition requires both an authorized actor and a satisfied guard condition.

Author: A governance steward drafts a new artifact or modification, following the contributor workflow (Appendix V) and conforming to canonical schemas (Appendix H).

Validate: The artifact undergoes automated validation against JSON schemas, PowerShell lint rules, boundary compliance checks, and governance enforcement tests (Appendix J). Validation is deterministic: an artifact either passes all gates or is returned to the Author state with specific error codes (Appendix W).

Publish: Upon passing validation and receiving the required approvals, the artifact is merged into the canonical repository (Appendix R) and its status transitions to Canonical.

Monitor: The drift detection engine (Appendix M) continuously monitors the published artifact and the tenant state it governs, comparing snapshots against the canonical baseline.

Detect Drift: When the engine identifies a deviation between canonical and actual state, it classifies the drift (Schema, Value, Hierarchy, Orphan, or Phantom) and generates an alert routed to the appropriate owner.

Remediate: The owner executes the remediation procedure defined for that drift category, using the two-brain model: Copilot determines the remediation instruction set, Execution Substrate executes it.

Re-validate: After remediation, the system re-runs validation to confirm that canonical compliance has been restored. If validation passes, the lifecycle returns to Monitor. If it fails, the artifact re-enters Remediate or escalates per Appendix Q.

5.1 Lifecycle State Diagram

+----------+     submit     +-----------+    pass     +-----------+ |  AUTHOR  |--------------->|  VALIDATE |------------>|  PUBLISH  | +----------+                +-----------+             +-----------+      ^                           |                         |      |                      fail |                         | deploy      |                           v                         v      |                    +------------+            +-----------+      +----return----------|  REJECTED  |            |  MONITOR  |                           +------------+            +-----------+                                                          |                                                     drift detected                                                          v                                                   +--------------+                                                   | DETECT DRIFT |                                                   +--------------+                                                          |                                                     classify + alert                                                          v                                                   +-----------+                                                   | REMEDIATE |                                                   +-----------+                                                          |                                                     fix applied                                                          v                                                   +-------------+                                                   | RE-VALIDATE |                                                   +-------------+                                                      |        |                                                 pass |        | fail                                                      v        v                                                +---------+ +-----------+                                                | MONITOR | | REMEDIATE |                                                +---------+ +-----------+

Section 6: Boundary Model Summary

6.1 M365 GCC-Moderate SaaS Boundary Definition

The Governance OS boundary is the M365 GCC-Moderate SaaS service perimeter. This boundary encompasses all Microsoft 365 cloud services authorized for government community use at the Moderate impact level. The system operates in Commercial Cloud as governed by FedRAMP unless specifically noted.

6.2 In-Scope Services

6.3 Out-of-Scope Services

6.4 Boundary Enforcement Rule

Section 7: Execution Model

7.1 Two-Brain Architecture

The Governance OS employs a two-brain architecture that separates governance reasoning from execution. This separation is fundamental: it ensures that policy interpretation cannot be influenced by execution-time conditions, and that execution cannot deviate from governed instructions.

Copilot (Governance Brain): Responsible for canonical review of all governance artifacts; enforcement of all seven governance principles; validation of schemas, boundary rules, and hierarchical integrity; generation of deterministic instruction sets for execution; provenance recording; and drift classification.

Execution Substrate (Execution Brain): Responsible for executing PowerShell scripts against target tenants; making Microsoft Graph API calls; provisioning tenant configurations (groups, AUs, role assignments); generating validation reports from live tenant data; and returning structured execution results to Copilot for validation.

7.2 Handoff Protocol

Copilot generates a deterministic instruction set conforming to the Instruction Set Schema (Appendix N).

Copilot validates the instruction set against boundary rules before dispatch.

Copilot dispatches the validated instruction set to Execution Substrate.

Execution Substrate executes the instruction set literally, without interpretation or modification.

Execution Substrate returns a structured result conforming to the expected output schema.

Copilot validates the result against expected outcomes and canonical state.

Copilot records full provenance: who requested, what was executed, when, and what changed.
