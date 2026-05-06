# IMAGE-PROMPTS-fedramp-moderate.md

Image-generation prompts for the externalized FedRAMP Moderate assessment documents.
Output PNGs are written to `images/` next to this file. The generator (`generate_images_from_prompts.py`)
hashes each prompt and skips regeneration when the hash already exists in the cache.

**Target model:** `gemini-3-pro-image-preview` (Nano Banana Pro) — chosen because every figure here is
an information-graphic with labels, arrows, and short text that needs to be legible. Pro renders text
in-image significantly more reliably than the Flash variant.

**Visual style applied to every prompt** (do not omit when refining):

- Clean, professional, infographic style. Flat vector aesthetic. No 3D, no photorealism, no clutter.
- Color palette: navy `#1F3864`, mid-blue `#5B9BD5`, light-blue fill `#EAF1FB`, amber callout `#ED7D31`,
  steel-gray text `#595959`, white background `#FFFFFF`. Use these and only these.
- Typography: a clean sans-serif (Calibri / Inter / Source Sans) for any in-image text. Title at top
  in 28-32pt navy bold; labels in 12-14pt steel-gray.
- White background. No drop shadows. No gradients. Thin (1.5pt) outlines on shapes; navy preferred.
- Aspect ratio: 16:9 unless otherwise noted. Render at 1920x1080 minimum.
- No fictional logos. No real corporate brand logos. Generic boxes labeled by name.
- Text in the image must be spelled correctly and match the labels listed in each prompt verbatim.

---

## fig_combined_01 — FedRAMP Moderate boundary overview

**Output:** `images/fig_combined_01.png`
**Aspect ratio:** 16:9
**Document position:** End of §0 in the combined assessment.

**Prompt:**

A clean, professional information-graphic diagram in flat vector style. Title at top: "FedRAMP Moderate
Authorization Boundary." A large rounded rectangle in the center labeled "Agency Tenant — M365 GCC-Moderate
(.com)" with a navy outline and a light blue fill, occupying about 45% of the canvas. Inside it, four small
boxes labeled "Entra ID," "Intune," "M365 Core Apps," and "Sentinel / Log Analytics." On the right side of the
canvas, outside the boundary, another rounded rectangle labeled "Microsoft Commercial Multi-Tenant Analytics"
with three small boxes inside labeled "Identity Protection ML," "Endpoint Analytics Advanced," and "Adoption
Score / INR." Between the two boundaries, draw a vertical filter strip labeled "NIST 800-53 Boundary Filter"
with four pill-shaped labels stacked vertically: "SI-4," "AU-2," "AU-3," "SC-7." Draw three thin arrows from
the agency tenant attempting to cross the filter to the right; each arrow is broken / blocked by the filter
strip with a small red "blocked" marker. Use only the specified colors. Clean sans-serif typography. White
background. No logos, no clutter, no decorative elements.

---

## fig_combined_02 — Telemetry blocked at the FedRAMP Moderate boundary

**Output:** `images/fig_combined_02.png`
**Aspect ratio:** 16:9
**Document position:** Start of §5 in the combined assessment.

**Prompt:**

A clean information-graphic diagram in flat vector style. Title at top: "Telemetry Blocked at the FedRAMP
Moderate Boundary." On the left, three stacked rounded rectangles labeled top-to-bottom "Entra ID,"
"Intune," and "M365 Core Apps." Each emits a thin labeled arrow rightward. The Entra arrow is labeled
"sign-in risk telemetry"; the Intune arrow is labeled "compliance + EPM analytics"; the M365 arrow is
labeled "Office Optional + Copilot telemetry." All three arrows hit a vertical filter strip in the center
labeled "FedRAMP Moderate Boundary (SI-4 / AU-2 / AU-3 / SC-7)" with a navy outline and amber fill. Each
arrow has a small red X over it where it meets the filter, indicating blocked. To the right of the filter,
show a single dimmed gray rounded rectangle labeled "Microsoft Commercial ML Pipelines" representing the
unreachable destination. Below the filter, draw one diverted thin arrow that turns 90 degrees and flows
downward to a separate rounded rectangle labeled "Agency Sentinel + Log Analytics (in-boundary)" — this
is the only working telemetry destination. Use only navy, mid-blue, light-blue, amber, steel-gray, white,
and a small red for the blocked markers. Clean sans-serif typography. White background.

---

## fig_combined_03 — MITRE ATT&CK Chain A flow diagram

**Output:** `images/fig_combined_03.png`
**Aspect ratio:** 16:9
**Document position:** §7.5 in the combined assessment, immediately after the Chain A description.

**Prompt:**

A clean MITRE ATT&CK kill-chain flow diagram in flat vector style. Title at top: "Chain A — Delayed-Patch
to Token-Theft to Label-Stripped Exfiltration." Three large rounded rectangles arranged left-to-right with
thick navy arrows connecting them. Box 1 label (top): "T1190 — Exploit Public-Facing Application." Box 1
sublabel: "Delayed-patched Intune device." Box 2 label: "T1550.001 — Application Access Token." Box 2
sublabel: "Token theft, no CAE." Box 3 label: "T1048.003 — Exfiltration Over Web Service." Box 3 sublabel:
"Label-stripped OneDrive link." Below each box, a small horizontal divider, then two rows of text:
above the divider in green "Commercial: detected in <30 min by [signal]" — for Box 1 "WUfB trend
telemetry," for Box 2 "Identity Protection ML risk + CAE," for Box 3 "Behavioral DLP." Below the divider
in red "GCC-Moderate: no signal — gap." Below all three boxes, a thin amber bar spanning the full width
labeled "End-to-end commercial detection: <30 min   |   GCC-Moderate: days to weeks." Use only navy,
mid-blue, light-blue, amber, steel-gray, white, plus muted green and muted red for the signal/gap rows.
Clean sans-serif typography. White background.

---

## fig_combined_04 — MITRE ATT&CK Chain B flow diagram

**Output:** `images/fig_combined_04.png`
**Aspect ratio:** 16:9
**Document position:** §7.5 in the combined assessment, immediately after the Chain B description.

**Prompt:**

A clean MITRE ATT&CK kill-chain flow diagram in flat vector style, matching the visual language of
Chain A but for Chain B. Title at top: "Chain B — Credential Stuffing to Privilege Escalation to MITM."
Three large rounded rectangles left-to-right with thick navy arrows. Box 1 label: "T1110.004 — Credential
Stuffing." Box 1 sublabel: "Password spray, no Entra risk score." Box 2 label: "T1068 — Exploitation for
Privilege Escalation." Box 2 sublabel: "EPM bypass, no analytics." Box 3 label: "T1557 — Adversary-in-the-
Middle." Box 3 sublabel: "INR-blind routing, no path telemetry." Under each box, the same green/red
two-row treatment: green row "Commercial: detected in minutes by [signal]" — for Box 1 "Identity
Protection ML," for Box 2 "EPM operational analytics," for Box 3 "INR real-time path telemetry." Red row:
"GCC-Moderate: no signal — gap." Below all three boxes, a thin amber bar: "End-to-end commercial
detection: minutes   |   GCC-Moderate: undetected until manual investigation." Same color palette and
typography as Chain A so the two diagrams read as a matched pair. White background.

---

## fig_combined_05 — ZTMM pillar maturity ceiling

**Output:** `images/fig_combined_05.png`
**Aspect ratio:** 16:9
**Document position:** End of §8 in the combined assessment.

**Prompt:**

A clean grouped bar chart in flat vector style. Title at top: "ZTMM Pillar Maturity Ceiling — GCC-Moderate."
On the X-axis, seven category labels (each in a slightly rotated label or stacked two-line label as needed
for fit): "Identity," "Devices," "Networks," "Apps & Workloads," "Data," "Visibility & Analytics,"
"Automation & Orchestration." On the Y-axis, four discrete tick labels: "Traditional," "Initial," "Advanced,"
"Optimal." For each pillar, three vertical bars in this left-to-right order: a steel-gray bar showing
"baseline (no agency analytics)" — for Identity, Devices, Networks, Automation reaching only "Initial";
for the rest reaching "Initial" or partly into "Advanced." A mid-blue bar showing "with agency analytics"
— reaching "Advanced" for all pillars. A navy bar showing "Optimal target" — reaching "Optimal" for all
pillars. Above the chart, a thin amber dashed horizontal line at the "Advanced" tick labeled "Realistic
ceiling without Microsoft platform changes." Legend at top-right: "Baseline" (steel-gray), "With agency
analytics" (mid-blue), "Optimal target" (navy). Use only the specified palette. Clean sans-serif typography.
White background.

---

## fig_combined_06 — MAS 2026 boundary refinement (before / after)

**Output:** `images/fig_combined_06.png`
**Aspect ratio:** 16:9
**Document position:** End of §12 in the combined assessment.

**Prompt:**

A clean two-panel before/after comparison diagram in flat vector style. Title at top: "MAS 2026 Boundary
Refinement." Left panel header: "Today — boundary blocks the data flow." Left panel content: a large
rounded rectangle labeled "Agency ATO Scope" containing three small boxes labeled "Entra ID," "Intune,"
"M365 Apps." A thick navy boundary outline. Outside this boundary on the right, three small dimmed boxes
labeled "Identity Protection ML," "Endpoint Analytics Advanced," "Adoption Score." Three arrows from
inside try to reach them; each is blocked at the boundary by a small red X. Right panel header:
"Post-MAS-2026 — narrowed scope, telemetry pipelines outside ATO." Right panel content: the same agency
boundary, now visibly tighter (smaller rectangle), containing only the three core service boxes. The
three Microsoft analytics boxes outside are now drawn solid (not dimmed) because they're reachable, with
arrows flowing out from inside the boundary to them — un-blocked. A small label between the two
boundaries reads "data flow now permitted because receiving service is out of ATO scope, not blocked at
network." Use only the specified palette plus a muted green to highlight the "post" state's working flows.
Clean sans-serif typography. White background.

---

## fig_combined_07 — Compensating-architecture stack

**Output:** `images/fig_combined_07.png`
**Aspect ratio:** 16:9
**Document position:** End of §13.2 in the combined assessment.

**Prompt:**

A clean layered architecture diagram in flat vector style. Title at top: "Agency-Side Compensating
Architecture Stack." Five horizontal layers stacked top-to-bottom, each a wide rounded rectangle:
Top layer (navy) labeled "Local Risk-Scoring Overlay" with sublabel "feeds the Policy Engine for
continuous user-risk and device-risk decisions." Second layer (mid-blue) labeled "Custom Analytic Rules"
with sublabel "impossible travel · MFA fatigue · low-and-slow spraying · behavioral DLP." Third layer
(light-blue) split into two side-by-side boxes: "Defender XDR Connector" (CloudAppEvents, EmailEvents,
DeviceEvents, identity tables) and "Purview Unified Audit" (Power Platform + Office activity). Fourth
layer (light-blue) labeled "Microsoft Sentinel + Log Analytics Workspace" with sublabel "all M365 / Entra
/ Intune diagnostic settings routed in." Bottom layer (steel-gray, full width) labeled "Long-Term Forensic
Store — 1+ year audit, 10 years for high-impact." On the right side of the stack, a vertical narrow
column labeled "Third-Party SD-WAN / SASE — INR-equivalent path telemetry + MITM/DNS-manipulation
detection," shown as a parallel pillar bridging all five layers. Show small upward arrows connecting
each layer to the one above to suggest data flow. Use only the specified palette. Clean sans-serif
typography. White background.

---

## fig_te_01 — Three GCC-Moderate boundary postures

**Output:** `images/fig_te_01.png`
**Aspect ratio:** 16:9
**Document position:** §1 in the ThousandEyes memo, immediately after the §1 intro paragraph.

**Prompt:**

A clean three-panel comparison diagram in flat vector style. Title at top: "Three GCC-Moderate Boundary
Postures." Three vertical panels of equal width, each with a panel header in navy bold. Panel 1 header:
"M365 GCC-Moderate (.com)." Panel 1 contents: a single navy-outlined rounded rectangle labeled "Agency
M365 tenant" with three small boxes inside: "Adoption Score (unavailable)," "INR (unavailable),"
"Endpoint Analytics Advanced (inferred unavailable)." Panel 1 footer: "Boundary scoped to .com commercial
cloud under FedRAMP Moderate." Panel 2 header: "Intune GCC-Moderate." Panel 2 contents: a separate navy-
outlined rounded rectangle labeled "Sibling tenant — intune.microsoft.com" with two small boxes inside:
"Compliance state," "EPM telemetry." Panel 2 footer: "Treated as a sibling tenant, not a sub-feature of
M365." Panel 3 header: "Azure (must be disambiguated)." Panel 3 contents: three stacked sub-panels — top
solid navy "Azure Commercial under Moderate ATO (in scope)," middle dimmed gray "Azure Government .us
(out of scope)," bottom mid-blue "Hybrid (M365 GCC-M + Azure Commercial subs)." A thin amber connector
labeled "shared Entra ID identity plane" runs horizontally across the bottom of all three panels,
visualizing the cross-boundary trust edge. Use only the specified palette. Clean sans-serif typography.
White background.

---

## fig_te_02 — ThousandEyes pillar coverage

**Output:** `images/fig_te_02.png`
**Aspect ratio:** 16:9
**Document position:** §2.1 in the ThousandEyes memo, immediately after the "Net assessment" paragraph.

**Prompt:**

A clean coverage-map diagram in flat vector style. Title at top: "ThousandEyes Coverage Against the Seven
ZTMM Pillars." Seven labeled rectangles arranged in a horizontal row, each the same size: "Identity,"
"Devices," "Networks," "Apps & Workloads," "Data," "Visibility & Analytics," "Automation & Orchestration."
Color-fill rule: the "Networks" rectangle is fully shaded mid-blue with a small green checkmark icon and
a sublabel "Fully addressed." All six other rectangles are unshaded (white fill, steel-gray outline) with
a small steel-gray "—" symbol and sublabel "Not addressed." Below the row of pillars, a single shaded
amber band labeled "Primary value: BGP / DNS / MITM detection chain (Chain B network half)." Beneath
that, a clear summary line in navy bold: "Closes ~1 of 7 ZTMM pillars." On the right side, a small
secondary callout box (light-blue) labeled "Two integrity caveats" with two short bullets: "Verify SKU
FedRAMP Moderate authorization," "Cloud Agent egress = cross-boundary metadata." Use only the specified
palette plus muted green for the checkmark. Clean sans-serif typography. White background.

---

## fig_20x_01 — Three FedRAMP 20x deployment surfaces

**Output:** `images/fig_20x_01.png`
**Aspect ratio:** 16:9
**Document position:** End of §1.3 in the FedRAMP 20x Assessment memo.

**Prompt:**

A clean three-track flow diagram in flat vector style. Title at top: "FedRAMP 20x — Three Deployment
Surfaces." Three horizontal swim lanes stacked top-to-bottom, each the same width, separated by thin
steel-gray dividers. Top lane (navy filled) labeled on the left "Phase 2 Pilot — REQUIRED" with a small
sublabel "Full 20x path" and on the right side three small connected boxes labeled "MAS-CSO scope,"
"KSI evidence payload," "Phase 2 authorization." Middle lane (mid-blue filled) labeled "Rev5 Balance
Improvement Releases — OPTIONAL" with sublabel "Opt-in for existing Rev5-authorized packages" and on
the right three small boxes "Minimum Assessment Scope," "Significant Change Notifications,"
"Vulnerability Detection & Response." Bottom lane (steel-gray, dimmed) labeled "Phase 1 Pilot — ARCHIVED"
with sublabel "Reference only — see Phase 1 Minimum Assessment Standard." On the far left of all three
lanes, a single starting box labeled "Currently Rev5-authorized CSP (e.g., Microsoft GCC-Moderate)" with
three thin arrows fanning right into each lane — the arrow into the middle lane (Balance Improvement
Releases) is drawn solid and labeled "realistic near-term path"; the arrow into the top lane is drawn
thin and labeled "full-program path"; the arrow into the bottom lane is dotted and labeled "not
applicable." Use only navy #1F3864, mid-blue #5B9BD5, light-blue #EAF1FB, amber #ED7D31, steel-gray
#595959, white background. Clean sans-serif typography. No logos, no clutter.

---

## fig_20x_02 — GCC-Moderate gap inventory mapped against MAS-CSO

**Output:** `images/fig_20x_02.png`
**Aspect ratio:** 16:9
**Document position:** End of §2 in the FedRAMP 20x Assessment memo.

**Prompt:**

A clean coverage-map diagram in flat vector style. Title at top: "GCC-Moderate Gap Inventory vs. FedRAMP
20x Minimum Assessment Scope." Six labeled rectangles arranged in a 3-column-by-2-row grid, each the same
size, with the signal class as the box label and a small status icon and short verdict text inside. Each
box is color-coded by net effect:

Top-left box (light green fill, dark green outline, green checkmark icon): "Network path metrics"
sublabel "Latency / jitter / packet-loss" and verdict text "FAVORABLE — descopable as metadata."
Top-middle box (light green fill, green checkmark icon): "Endpoint performance counters" sublabel
"Boot time / AppCrashCount / processor usage" and verdict text "FAVORABLE (with caveats)."
Top-right box (light amber fill, amber outline, warning-triangle icon): "Adoption Score baselines"
sublabel "Chat/email ratios / mobility / content collab" and verdict text "MIXED — likely-impact reads in."
Bottom-left box (light red fill, red outline, X icon): "Entra Identity Protection ML" sublabel
"Impossible travel / atypical IP / leaked creds" and verdict text "UNFAVORABLE — handles federal data."
Bottom-middle box (light red fill, X icon): "DLP / sensitivity-label / Copilot" sublabel "Behavioral
analytics / prompt richness" and verdict text "UNFAVORABLE — content-adjacent."
Bottom-right box (light gray fill, steel-gray outline, dash icon): "CAE real-time revocation" sublabel
"Sub-second token revocation paths" and verdict text "NEUTRAL — not a scope problem."

Below the grid, a thin horizontal navy bar labeled "Net: ~30–40% of the gap matrix has a path under
MAS-CSO-MDI; the identity / data / behavioral end does not." Use only navy #1F3864, light-green #E2F0D9,
muted-green #70AD47, light-amber #FFF2CC, amber #ED7D31, light-red #FBE5D6, muted-red #C00000,
steel-gray #595959, light-gray #F2F2F2, white background. Clean sans-serif typography.

---

## fig_20x_03 — Boundary semantics before and after MAS-CSO

**Output:** `images/fig_20x_03.png`
**Aspect ratio:** 16:9
**Document position:** End of §5 in the FedRAMP 20x Assessment memo.

**Prompt:**

A clean two-panel before/after diagram in flat vector style. Title at top: "Boundary Semantics — Before
and After Minimum Assessment Scope." A vertical thin gray divider splits the canvas into two panels of
equal width.

Left panel header (in navy bold): "Pre-20x — single thick boundary." Left panel content: a single large
rounded rectangle with a thick navy outline (4pt) labeled "Agency Tenant — Authorization Boundary"
filled light blue, occupying about 80% of the left panel. Inside, four small boxes labeled "Federal
customer data," "Sign-in events," "Endpoint perf counters," "Network path metrics." On the right edge
of the boundary, four thin outbound arrows attempting to leave; each arrow has a small red X over it
where it meets the boundary, indicating SI-4 / AU-2 / AU-3 / SC-7 blocking. A small label below the box
reads "Everything inside, telemetry blocked at the edge."

Right panel header (in navy bold): "Post-20x with MAS-CSO — narrowed scope." Right panel content: a
smaller rounded rectangle with a thick navy outline labeled "Minimum Assessment Scope" filled light
blue, occupying about 50% of the right panel and centered. Inside, only two small boxes labeled "Federal
customer data" and "Sign-in events (handles federal data)." Outside the smaller boundary but still on
the right panel, two boxes labeled "Endpoint perf counters" and "Network path metrics" drawn in mid-blue
fill — clearly outside the scope but still part of the agency tenant. Two outbound arrows from these
descoped boxes flow rightward and OUT of the panel area, drawn solid with a small green checkmark, with
a label "machine-readable KSI evidence — flows freely." A small label below reads "Federal data still
fully protected; descoped metadata flows out as KSI evidence."

Use only navy #1F3864, mid-blue #5B9BD5, light-blue #EAF1FB, muted green #70AD47, muted red #C00000,
steel-gray #595959, white background. Clean sans-serif typography. No logos.
