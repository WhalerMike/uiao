---
document_id: UIAO_005
title: "UIAO-core Value Proposition — Two-Way Governance Architecture for SCuBA and BOD 25-01"
version: "1.0"
status: Current
owner: "Michael Stratton"
author: "Michal Doroszewski"
created_at: "2026-04-18"
updated_at: "2026-06-06"
publish_to_site: true
publication_style: include
published_at: docs/canon/UIAO_005_SCuBA_Value_Proposition_v1.0.html
audience: "CISOs, Federal Modernization Leads, Venture Capital, Analysts, Agency Security Architects"
provenance:
  source: "inbox/UIAO SCuBA Value Proposition - Two-Way Governance Architecture/UIAO SCuBA Value Proposition - Two-Way Governance Architecture.docx"
  version: "1.0"
  derived_at: "2026-04-18"
  derived_by: "Copilot Tasks docx extraction; promoted to canon in ADR-044 shadow-canon cleanup on 2026-04-23"
  images:
    - "image_1a4aa92b.png — SCuBA/ScubaConnect/M365 Relationship Diagram"
    - "image_a611cce0.png — Azure SCuBA Scan JSON Results"
    - "image_b4d3a0b3.png — Execution Models: GitHub-hosted vs Self-hosted Runners"
    - "image_d4d525c0.png — 4-Phase Assessment-Analysis-Update-Reception Workflow"
---
# UIAO-core Value Proposition

## Two-Way Governance Architecture for SCuBA and BOD 25-01

## 1. Executive Summary

Binding Operational Directive 25-01 mandates automated, continuous cloud security assessments across all Federal Civilian Executive Branch agencies. CISA's Secure Cloud Business Applications (SCuBA) program provides the assessment logic through ScubaGear (for Microsoft 365) and ScubaGoggles (for Google Workspace). ScubaConnect automates the execution — replacing interactive, human-dependent runs with non-interactive, certificate-authenticated workflows orchestrated through GitHub Actions. But neither SCuBA nor ScubaConnect provides governance. They produce data, not meaning. They assess posture; they do not govern it.

UIAO-core fills the missing half. It wraps around the entire SCuBA data path as a governance envelope — not inline, but as a two-way prompt-and-conversion mediator. Outbound (Leg 1), UIAO-core captures assessment results in parallel with CISA's official CDM feed, normalizes them into canonical governance artifacts, detects drift against prior baselines, and routes violations to remediation pipelines. Inbound (Leg 2), UIAO-core monitors CISA's upstream policy releases on the cisagov/ScubaGear GitHub repository, detects new baselines and Rego rule changes, generates governance events, and triggers assessment recalibration — closing the loop. No other component in the SCuBA ecosystem watches both directions.

The result is a deterministic governance feedback system that transforms SCuBA from a compliance assessment tool into a continuously governed, audit-ready compliance pipeline. SCuBA assesses. ScubaConnect automates. UIAO governs.

@fig-uiao-005-value-stack frames the three layers that operate over the same SCuBA data path, and what each one adds that the layer beneath it does not provide.

![SCuBA assesses, ScubaConnect automates, and UIAO-core governs — three layers over a single SCuBA data path. SCuBA (ScubaGear / ScubaGoggles) produces assessment data but not meaning; ScubaConnect automates execution but not governance; UIAO-core wraps both as a two-way governance envelope that supplies the missing half through prompt and conversion on two legs.](images/uiao-005-diagram-04-assess-automate-govern.png){#fig-uiao-005-value-stack fig-alt="Three stacked horizontal bands labeled SCuBA (Assesses), ScubaConnect (Automates), and UIAO-core (Governs), each with a short description and a note on what it does not provide, connected top-to-bottom by arrows." width="92%"}

## 2. The Problem: Why SCuBA Alone Cannot Satisfy BOD 25-01

BOD 25-01 imposes two non-negotiable requirements on FCEB agencies. First, agencies must deploy SCuBA automated assessment tools by April 25, 2025. Second, agencies must implement all future updates to mandatory SCuBA policies — a standing obligation that persists indefinitely.

The legacy model for SCuBA compliance is manual, point-in-time, and human-dependent. A system administrator downloads ScubaGear from the cisagov/ScubaGear GitHub repository, opens a PowerShell session, logs in via an interactive browser pop-up (OAuth device-code flow or interactive MFA), runs the assessment script locally on a workstation, generates static HTML/JSON/CSV reports, and manually uploads the results to CISA's CyberScope reporting portal on a quarterly basis. This model is the status quo at most agencies that adopted SCuBA prior to ScubaConnect.

This model has five critical weaknesses that BOD 25-01 explicitly requires agencies to eliminate:

Human-dependent trigger. An administrator must remember to initiate the assessment. There is no automated schedule, no cron, no event-driven trigger. If the administrator is on leave, reassigned, or simply forgets, the assessment does not run.

Interactive authentication. ScubaGear's default authentication model requires a browser pop-up login — an interactive OAuth flow that cannot be automated. This hard-couples the assessment to a human sitting at a keyboard.

Local execution. The script runs on a single workstation, bound to that machine's CPU, RAM, and network connectivity. If the workstation is powered off, reimaged, or disconnected from the network, the assessment fails.

Quarterly frequency. The manual model produces point-in-time snapshots at best quarterly — and often less frequently. Between runs, the agency has zero visibility into configuration drift. BOD 25-01 requires continuous monitoring, not periodic snapshots.

Manual reporting. Results must be manually formatted and uploaded to CyberScope by a human. There is no automated pipeline from assessment output to CISA's CDM Dashboard.

BOD 25-01 explicitly requires eliminating this model. The directive mandates automated, non-interactive, continuously running assessment tools that feed results directly to CISA — without human intermediaries in the data path.

### Table 1: Manual vs. Automated Assessment Models

@tbl-uiao-005-manual-vs-automated contrasts the legacy manual model with the automated model BOD 25-01 requires, across the five weaknesses above.

| Dimension | Legacy manual model | Automated model (ScubaConnect + UIAO-core) |
|---|---|---|
| Trigger | Human-dependent — an administrator must remember to run it; no schedule, cron, or event | Deterministic, time-based GitHub Actions cron; no human initiates the run |
| Authentication | Interactive browser pop-up (OAuth device-code flow or interactive MFA) | Non-interactive Service Principal with certificate-based authentication |
| Execution location | Local, on a single workstation bound to its CPU, RAM, and network | Orchestrated in GitHub Actions; no dependency on any one workstation |
| Frequency | Point-in-time snapshots, at best quarterly — blind to drift between runs | Continuous; daily runs surface configuration drift within twenty-four hours |
| Reporting | Manual formatting and upload to CyberScope by a human | Automated path to CISA's CDM Dashboard, plus governed, versioned artifacts |
| BOD 25-01 alignment | Non-compliant with the directive's intent; exposed to drift between runs | Satisfies the automation mandate and the continuous-monitoring requirement |

: Manual vs. automated assessment models. {#tbl-uiao-005-manual-vs-automated}

## 3. The Solution: UIAO-core as the Governance Envelope

UIAO-core does not sit inline between ScubaConnect and CISA's CDM Dashboard. That data path is sacrosanct. CISA owns it. Agencies cannot inject middleware into it, nor should they. The official assessment results must flow, unaltered and unmediated, from ScubaConnect through the CLAW/TALON integration layer to CISA's CDM Dashboard. Any attempt to intercept, modify, or delay that path would violate the architectural contract that BOD 25-01 establishes.

UIAO-core wraps around the entire SCuBA data path as a governance envelope. It operates on two legs simultaneously, creating a closed-loop feedback system:

Prompt: UIAO detects a change on either end of the data path — new assessment results on the outbound side, new policy baselines on the inbound side — and prompts the appropriate governance response. "Prompt" is used in the control-systems sense: an event-driven trigger that initiates a governed workflow.

Conversion: UIAO converts raw data — JSON assessment results, Rego policy diffs, GitHub release notes — into governance artifacts. These artifacts are versioned, canonical, machine-trackable, and audit-ready. They are the unit of governance that SCuBA alone does not produce.

The combination of prompt and conversion on two legs creates a two-way governance architecture that no other component in the SCuBA ecosystem provides. SCuBA assesses configuration state. ScubaConnect automates that assessment. UIAO-core governs the entire lifecycle — from assessment execution through policy absorption — as a continuous, deterministic feedback loop.

@fig-uiao-005-envelope shows the complete two-way architecture: the three bounded contexts, both legs, and the sacrosanct CDM data path that UIAO-core wraps but never touches.

![The two-way governance architecture. The Agency Cloud Environment (ScubaConnect in a GCC-Moderate boundary) pushes official results along the sacrosanct CDM path to the CISA Domain's CDM Dashboard — UIAO does not touch, intercept, modify, or delay it. In parallel (Leg 1), ScubaConnect feeds a read-only copy to the UIAO Governance Envelope, whose Upstream Policy Watcher, Governance Event Engine, Canonical Artifact Repository, and Drift Detection Engine convert it into governed artifacts. On Leg 2, a new cisagov/ScubaGear release is detected and a recalibration trigger re-runs the assessment, closing the loop.](images/uiao-005-diagram-01-two-way-governance-envelope.png){#fig-uiao-005-envelope fig-alt="A three-column schematic — Agency Cloud Environment on the left, UIAO Governance Envelope in the center, CISA Domain on the right. A red arc across the top carries the sacrosanct CDM path from ScubaConnect to the CDM Dashboard. A dashed teal Leg 1 arrow feeds the envelope in parallel; a navy Leg 2 arrow carries policy releases inbound and a return arrow along the bottom carries the recalibration trigger back to ScubaConnect." width="92%"}

## 4. Leg 1 — Outbound: Assessment to Governance to Reporting

The outbound leg is the path most agencies already understand: assessment results flow from the M365 tenant toward CISA. What agencies typically do not have is a governance layer that intercepts those results — in parallel, never inline — and converts them into governed, versioned, actionable compliance artifacts.

@fig-uiao-005-leg1 traces the outbound leg end to end: the shared assessment execution (Steps 1a–1d), the sacrosanct path to CISA (Step 1e), and the parallel governance pipeline UIAO-core runs on a read-only copy (Steps 1f–1j).

![The Leg 1 outbound pipeline. The top row is the shared assessment execution: Step 1a orchestration (daily cron), Step 1b non-interactive certificate auth, Step 1c configuration pull (Graph, Exchange Online, SharePoint Online), and Step 1d ScubaGear evaluation against Rego baselines. Step 1d branches two ways — Step 1e pushes official results along the sacrosanct path to CISA's CDM Dashboard (untouched by UIAO), while Step 1f sends a parallel, read-only copy into UIAO's governance band: Step 1g event conversion, Step 1h canonical storage, Step 1i drift detection, and Step 1j alerting and remediation.](images/uiao-005-diagram-02-leg1-outbound-pipeline.png){#fig-uiao-005-leg1 fig-alt="A two-row flow diagram. The top row shows four assessment-execution steps left to right; the rightmost step branches up to a red sacrosanct-path box to CISA and down to a teal governance band. The bottom row shows four UIAO governance steps left to right: event conversion, canonical storage, drift detection, and alert/remediate." width="92%"}

### 4.1 Step-by-Step Data Flow

The outbound leg proceeds through the following stages:

**Step 1a — Orchestration Trigger. The GitHub Actions orchestrator fires on a daily cron schedule (e.g., 0 6 * * * UTC). No human initiates the run. The trigger is deterministic and time-based.**

**Step 1b — Non-Interactive Authentication. ScubaConnect authenticates to the M365 tenant via a Service Principal with certificate-based authentication. No browser pop-up. No interactive MFA. No human in the loop. The certificate is stored as a GitHub Actions secret, rotated on a defined cadence.**

**Step 1c — Configuration Pull. ScubaConnect calls M365 APIs — Microsoft Graph, Exchange Online PowerShell, SharePoint Online Management Shell — to pull the current configuration settings for all SCuBA-covered products (Exchange Online, SharePoint Online, Microsoft Teams, OneDrive for Business, Microsoft Defender, Entra ID, Power Platform).**

**Step 1d — Data Return. M365 returns configuration data and audit logs. ScubaGear evaluates these against the current Rego policy baselines and produces assessment results in JSON, CSV, and HTML formats.**

**Step 1e — Sacrosanct Path to CISA. ScubaConnect pushes official results directly to CISA's CDM Dashboard via the CLAW/TALON integration layer. This is the sacrosanct path. UIAO-core does not touch, intercept, modify, or delay this data flow. CISA owns it.**

**Step 1f — Parallel Feed to UIAO. In parallel with Step 1e, ScubaConnect sends the same assessment results to UIAO-core. This is a read-only, non-blocking copy of the data.**

**Step 1g — Governance Event Conversion. UIAO-core's Governance Event Engine receives the raw JSON/CSV output and converts it into a structured governance event — a typed, timestamped, machine-trackable object that captures what was assessed, what passed, what failed, and against which policy baseline version.**

**Step 1h — Canonical Storage. The governance event is stored in the Canonical Artifact Repository as a versioned, immutable artifact. Each run produces exactly one artifact. Artifacts are never overwritten — they accumulate as a complete compliance history.**

**Step 1i — Drift Detection. The Drift Detection Engine compares the current run's results against prior runs. It identifies configuration changes — both improvements (newly compliant settings) and regressions (newly non-compliant settings) — and flags delta items for review.**

**Step 1j — Alerting and Remediation. If a mandatory "Shall" policy violation is detected, an alert is routed to the Agency Dashboard and a remediation ticket is generated in the agency's ticketing system. The ticket includes the specific control, the non-compliant setting, the expected value, and the baseline version that defines the requirement.**

### 4.2 Key Architectural Insight

The defining property of Leg 1 is that governance happens in parallel, never inline. The official results flow to CISA untouched (Step 1e); UIAO-core operates only on a read-only, non-blocking copy (Step 1f). The agency therefore gains a governed, versioned, drift-aware view of its own posture without ever sitting in — or being able to delay — the sacrosanct CDM data path. Conversion is the unit of value: raw JSON and CSV become typed governance events, immutable canonical artifacts, drift deltas, and actionable remediation tickets that SCuBA alone never produces.

### Table 2: Outbound Data Transformation Pipeline

@tbl-uiao-005-outbound walks the outbound transformation stage by stage, from the parallel copy of the raw results to the remediation ticket.

| Stage | Input | UIAO component | Output artifact |
|---|---|---|---|
| Parallel ingest (Step 1f) | Read-only copy of the same results sent to CISA | Parallel feed | Raw assessment payload (JSON / CSV) |
| Event conversion (Step 1g) | Raw JSON / CSV output | Governance Event Engine | Typed, timestamped governance event |
| Canonical storage (Step 1h) | Governance event | Canonical Artifact Repository | Versioned, immutable artifact — one per run |
| Drift detection (Step 1i) | Current artifact vs prior runs | Drift Detection Engine | Delta report (improvements + regressions) |
| Alert + remediation (Step 1j) | Mandatory "Shall" violation | Agency Dashboard + ticketing | Alert + remediation ticket (control, expected value, baseline version) |

: Outbound data transformation pipeline. {#tbl-uiao-005-outbound}

## 5. Leg 2 — Inbound: Policy Updates to Governance to Recalibration

The inbound leg is the leg that does not exist without UIAO-core. It addresses the second, often overlooked requirement of BOD 25-01: agencies "shall implement all future updates to mandatory SCuBA policies." This is not a one-time event. It is a standing obligation that persists for the life of the directive.

@fig-uiao-005-leg2 shows how UIAO-core turns CISA's pull-only policy surfaces into a governed, closed loop — from release detection through recalibration back into Leg 1.

![The Leg 2 inbound recalibration loop. CISA publishes updates through pull-only surfaces (cisagov/ScubaGear releases, the SCuBA Baselines page, BOD 25-01 guidance) with no live push to agencies — so without UIAO-core the inbound signal is invisible and agencies run stale baselines for weeks. With UIAO-core: Step 2a Upstream Policy Watcher detects a release, Step 2b generates a governance event summarizing new, modified, and deprecated controls, Step 2c prompts the agency, Step 2d triggers the update workflow, and Step 2e re-runs the assessment against the new baseline — whose results flow through Leg 1, closing the loop.](images/uiao-005-diagram-03-leg2-inbound-recalibration.png){#fig-uiao-005-leg2 fig-alt="A loop diagram. A navy source box of CISA publish surfaces and an amber 'Without UIAO-core' risk callout sit on the left. Five teal step boxes (2a–2e) run clockwise from the watcher through to recalibrated assessment, which feeds a teal Leg 1 box; a navy return arrow closes the loop back to the watcher. A key-architectural-insight panel runs across the bottom." width="92%"}

### 5.1 How CISA Publishes Policy Updates

CISA does not push policy updates to agencies through a live channel. There is no webhook, no pub/sub topic, no push notification. Instead, CISA publishes updates through three surfaces:

cisagov/ScubaGear GitHub Releases. New Rego rules, updated baseline versions, removed or deprecated policies, and structural changes to the assessment logic are published as tagged releases on the cisagov/ScubaGear GitHub repository.

CISA's SCuBA Baselines Page. Updated Secure Configuration Baseline documents — the human-readable policy specifications that define "Shall," "Should," and "May" controls — are published on CISA's SCuBA web page.

BOD 25-01 Implementation Guidance. Updated mandatory configuration lists and implementation timelines are published as amendments or supplements to the original directive.

Without UIAO-core, the inbound signal is invisible. A human must notice the GitHub release, read the changelog, understand which Rego rules changed, determine whether new "Shall" controls were added, manually update ScubaGear to the new version, and hope the next assessment run picks up the changes. If the human is on leave, or if the release falls during a sprint cycle, the agency runs assessments against stale baselines — potentially for weeks or months — while believing it is compliant.

### 5.2 Step-by-Step Inbound Flow

With UIAO-core, the inbound leg becomes governed:

**Step 2a — Upstream Policy Watch. UIAO-core's Upstream Policy Watcher monitors the cisagov/ScubaGear GitHub repository for new releases. Detection occurs via GitHub webhook (real-time) or scheduled poll (e.g., every 6 hours). The watcher tracks release tags, Rego file diffs, and baseline version increments.**

**Step 2b — Governance Event Generation. On detection of a new release, the Governance Event Engine generates a structured governance event: "New Baseline v1.x released: N new Shall controls added to [product]. M existing controls modified. K controls deprecated." The event includes the full diff of Rego changes, mapped to human-readable control descriptions.**

**Step 2c — Agency Prompt. The governance event prompts the agency security team via dashboard flag, email alert, or ticketing system integration. The prompt includes the release summary, the list of affected controls, and a recommended action (update ScubaGear, re-run assessment, review new Shall controls).**

**Step 2d — Update Trigger. The Governance Event Engine triggers a ScubaGear/ScubaConnect update workflow via GitHub Actions. This can be configured as automatic (update immediately on detection) or gated (update after human approval). The update workflow pulls the new ScubaGear release, updates the Rego rules, and validates the installation.**

**Step 2e — Recalibrated Assessment. The updated ScubaConnect instance re-runs the assessment against the new policy baseline. Results flow through Leg 1 — closing the loop. The agency's compliance posture is now evaluated against the latest mandatory controls, and any new Shall violations are immediately surfaced.**

### 5.3 Key Architectural Insight

Leg 2 exists only because UIAO-core watches the upstream. CISA publishes policy updates through pull-only surfaces — GitHub releases, the SCuBA Baselines page, and BOD 25-01 guidance — with no live push channel to agencies. Without an automated watcher, absorbing a new mandatory control depends entirely on a human noticing the release. UIAO-core converts that silent signal into a governance event, prompts the agency, and triggers recalibration — so a new baseline automatically becomes an updated assessment whose results flow back through Leg 1, closing the loop.

### Table 3: Two-Way Architecture Summary

@tbl-uiao-005-two-way summarizes both legs along the prompt-and-conversion axis that defines the architecture.

| Leg | Direction | Trigger source | Prompt | Conversion | Outcome |
|---|---|---|---|---|---|
| Leg 1 | Outbound | New assessment results from ScubaConnect | New run detected (parallel feed, Step 1f) | Results → governed, versioned artifacts | Drift detection and violation alerting |
| Leg 2 | Inbound | New baseline / Rego release on cisagov/ScubaGear | Upstream Policy Watcher detects a release | Policy diff → governance event | Agency prompt and assessment recalibration — closing the loop |

: Two-way architecture summary. {#tbl-uiao-005-two-way}

## 6. The Six Value Pillars

### 6.1 Continuous Compliance Instead of Point-in-Time Checks

SCuBA alone produces quarterly snapshots. UIAO-core produces continuous compliance visibility.

Daily assessment runs via non-interactive, certificate-based authentication — no human trigger required

Real-time posture awareness through continuously updated governance artifacts and drift reports

Eliminates human bottlenecks: no administrator needs to remember, log in, or run a script

Configuration drift is detected within 24 hours, not discovered at the next quarterly review

Why it matters: BOD 25-01 requires continuous monitoring, not quarterly snapshots. Agencies that rely on point-in-time assessments are non-compliant with the directive's intent and exposed to configuration drift between runs.

### 6.2 Deterministic, Zero-Touch Execution

SCuBA alone requires a human at a keyboard. UIAO-core requires nothing but a clock.

GitHub Actions orchestration with Service Principal and certificate-based authentication — fully non-interactive

Every run is predictable, reproducible, and audit-ready: same inputs produce same outputs

No credential sprawl, no shared passwords, no interactive login sessions that expire or require rotation by a human

Why it matters: The April 25, 2025 automation mandate in BOD 25-01 requires exactly this model. Interactive authentication is explicitly incompatible with the directive's requirements for automated assessment tools.

### 6.3 Closed-Loop Governance Feedback System

SCuBA alone watches one direction. UIAO-core watches both.

Two-way prompt-and-conversion architecture covering both outbound (assessment results) and inbound (policy updates)

Outbound: assessment results are converted into governed, versioned artifacts with drift detection and violation alerting

Inbound: upstream policy changes are detected, governance events are generated, and assessment recalibration is triggered

The loop closes automatically: a new CISA baseline triggers an updated assessment, which triggers new governance artifacts, which surface new violations

Why it matters: No other component in the SCuBA ecosystem watches both directions. Without UIAO-core, the inbound leg is invisible — agencies must rely on human vigilance to notice and absorb new mandatory controls.

### 6.4 Drift-Resistant Canonical Repository

SCuBA alone produces ephemeral reports. UIAO-core produces a permanent compliance record.

Every assessment run becomes a versioned, immutable artifact in the Canonical Artifact Repository — never overwritten, always traceable

Strict separation between machine-generated content (assessment results) and human-authored content (governance decisions, exemption approvals)

Full provenance chain: from raw assessment output to governance event to canonical artifact to drift report to remediation ticket

Why it matters: Agencies need a single source of truth for configuration compliance history. Auditors need an immutable record. Inspector General reviews require traceability. Ephemeral reports that exist only on an administrator's workstation satisfy none of these requirements.

### 6.5 Agency-Side Visibility Before CISA Sees the Data

SCuBA alone sends results to CISA. UIAO-core lets agencies see their own posture first.

Mirrors the same results sent to CISA's CDM Dashboard — without intercepting or modifying the official data path

Internal dashboards, analytics, and remediation pipelines give agencies operational visibility into their compliance posture

Agencies can identify, triage, and begin remediating violations before federal dashboards update — reducing the gap between detection and response

Why it matters: Federal-grade visibility without federal-grade latency. Agencies should not learn about their own compliance failures from a CISA dashboard notification. UIAO-core ensures they see the data first.

### 6.6 Future-Proof Compliance Architecture

SCuBA alone is a tool. UIAO-core is a governance platform.

Reusable automation pattern applicable to future CISA tools, future BODs, and future cloud platforms beyond M365 and Google Workspace

Governance OS architecture that scales across multiple clouds, multiple tenants, and multiple assessment frameworks

Modular, extensible compliance substrate: new assessment tools plug into the same governance event engine, canonical repository, and drift detection pipeline

Why it matters: UIAO-core is not a SCuBA integration. It is a governance platform that happens to integrate with SCuBA today. When CISA releases the next tool, the next baseline, or the next directive, UIAO-core absorbs it through the same two-way architecture.

## 7. Positioning Statement

UIAO-core transforms SCuBA from a manual assessment tool into a continuous, governed, automated compliance pipeline that satisfies BOD 25-01, eliminates human-dependent workflows, and provides agencies with a deterministic, audit-ready governance substrate. It is the only component in the SCuBA ecosystem that creates a two-way governance loop — converting assessment results into actionable artifacts on the outbound leg, and prompting recalibration from upstream policy changes on the inbound leg. UIAO-core is not middleware. It is not a SCuBA plugin. It is the governance envelope that turns a compliance pipeline into a governance feedback system.

## 8. Audience-Ready Formats

The following subsections provide condensed, drop-in-ready versions of the UIAO-core value proposition, formatted for specific audiences and delivery contexts.

### 8.1 One-Page Executive Summary

For leadership briefings, board presentations, and executive decision memos.

BOD 25-01 requires Federal Civilian Executive Branch agencies to run automated, continuous SCuBA assessments and to implement every future mandatory policy update. SCuBA (ScubaGear and ScubaGoggles) supplies the assessment logic and ScubaConnect automates its execution — but neither governs the result. They produce data, not meaning. UIAO-core supplies the missing half as a two-way governance envelope that wraps the entire SCuBA data path without ever sitting inline. Outbound, it converts assessment results into governed, versioned, drift-aware artifacts in parallel with CISA's official feed. Inbound, it watches CISA's upstream policy releases, generates governance events, and triggers assessment recalibration. The result is a deterministic, audit-ready compliance pipeline that satisfies the directive's automation and continuous-monitoring mandates and eliminates the human-dependent workflows of the legacy manual model.

### 8.2 Pitch-Deck Slide

Single-slide format for investor, analyst, and partner decks.

**UIAO-core — the governance envelope for SCuBA.**

- **SCuBA assesses. ScubaConnect automates. UIAO governs.** UIAO-core is the only component that closes a two-way governance loop around the SCuBA data path.
- **Outbound (Leg 1):** assessment results → governed, versioned artifacts, with drift detection and "Shall" violation alerting — in parallel, never inline.
- **Inbound (Leg 2):** upstream CISA policy releases → governance events → automatic assessment recalibration.
- **Not middleware, not a plugin:** a reusable governance platform that absorbs the next CISA tool, baseline, or directive through the same architecture.

### 8.3 GitHub README Section

For the uiao-core repository README.md.

> **UIAO-core** wraps the CISA SCuBA data path as a two-way governance envelope. SCuBA assesses, ScubaConnect automates, and UIAO-core governs. On the outbound leg it captures assessment results in parallel with CISA's official CDM feed, converts them into versioned, immutable governance artifacts, and detects drift against prior baselines. On the inbound leg it watches the `cisagov/ScubaGear` repository for new releases, generates governance events, and triggers assessment recalibration — closing the loop. UIAO-core never sits inline on the sacrosanct CDM path; it operates on a read-only, non-blocking copy. The outcome is a deterministic, audit-ready compliance pipeline aligned to BOD 25-01.

### 8.4 Federal CIO/CISO Narrative

For DHS, civilian agency, and interagency briefings.

BOD 25-01 imposes two standing obligations: deploy automated SCuBA assessment tools, and implement all future updates to mandatory SCuBA policies. The legacy manual model — interactive logins, local execution, quarterly snapshots, and manual CyberScope uploads — is explicitly the model the directive requires agencies to retire. ScubaConnect delivers the automation; UIAO-core delivers the governance. It gives agency security teams a governed, versioned record of their own posture before CISA's dashboards update, without intercepting or delaying the official data path that CISA owns. Critically, it also governs the inbound direction: when CISA publishes a new baseline, UIAO-core detects it, surfaces the affected "Shall" controls, and recalibrates the assessment — so compliance no longer depends on a human noticing a GitHub release. For an Authorizing Official or Inspector General, the canonical, immutable artifact history provides the traceability that ephemeral workstation reports cannot.

## Appendix A: Diagram Source Reference

The canonical figure for the two-way architecture (@fig-uiao-005-envelope) is authored as a committed, house-style SVG and rasterized to PNG by `scripts/render_svg_images.py`. Per [ADR-093](adr/adr-093-image-generation-svg.md), the SVG is the single source of truth and the PNG is a build artifact; no diagram is generated at render time, so the rendered text is always exactly what the SVG says. This supersedes the prior PlantUML companion file (`uiao-scuba-two-way-governance.puml`): the legacy PlantUML source is retired and is not part of the build.

Figure sources for this document live alongside it under `docs/canon/images/`:

| Figure | Source SVG |
|---|---|
| @fig-uiao-005-value-stack | `uiao-005-diagram-04-assess-automate-govern.svg` |
| @fig-uiao-005-envelope | `uiao-005-diagram-01-two-way-governance-envelope.svg` |
| @fig-uiao-005-leg1 | `uiao-005-diagram-02-leg1-outbound-pipeline.svg` |
| @fig-uiao-005-leg2 | `uiao-005-diagram-03-leg2-inbound-recalibration.svg` |

Each SVG encodes the three bounded contexts (CISA Domain, Agency Cloud Environment, UIAO Governance Envelope), both legs of the two-way architecture, the sacrosanct CDM data path, and the color-coded legend, against the house palette in `src/uiao/canon/svg-style/`. The SVGs are version-controlled alongside this document and should be updated — then re-rendered with `python scripts/render_svg_images.py` — whenever the architecture evolves.

## Appendix B: Object List

| Object ID | Type | Title |
|---|---|---|
| DIAGRAM-01 | Diagram | Two-way governance envelope around the SCuBA data path |
| DIAGRAM-02 | Diagram | Leg 1 outbound pipeline (Steps 1a–1j) |
| DIAGRAM-03 | Diagram | Leg 2 inbound policy-update and recalibration loop (Steps 2a–2e) |
| DIAGRAM-04 | Diagram | Three-layer value stack — SCuBA assesses, ScubaConnect automates, UIAO governs |
| TABLE-01 | Table | Manual vs. automated assessment models |
| TABLE-02 | Table | Outbound data transformation pipeline |
| TABLE-03 | Table | Two-way architecture summary |

UIAO-core Value Proposition · Controlled · Michal Doroszewski · April 2026

CONTROLLED
