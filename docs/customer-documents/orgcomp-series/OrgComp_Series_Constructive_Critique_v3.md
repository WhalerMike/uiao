---
title: "Federal Application-Aware Networking Series — Constructive Critique (v3)"
subtitle: "External verification round — Vol 0's factual claims checked against primary sources, with verdicts, and the doctrine claims stress-tested"
author: "Independent review (Claude Code, at author request)"
date: "2026-07-15"
---

> **INTERNAL — CONSTRUCTIVE PEER REVIEW · NOT AN ASSESSMENT RESULT**
>
> This is the third independent, constructive critique of the Federal
> Application-Aware Networking (AAN) series, prepared at the author's request.
> Where v1 and v2 reviewed the corpus *internally* (consistency, claim
> hygiene, structure), **v3 does what no prior round did: it checks Vol 0's
> externally-checkable factual claims against primary sources** — FedRAMP's
> canonical GitHub publication repos, CISA directives, NIST/CMVP, NSA CNSA 2.0,
> the FedRAMP Marketplace dataset, AWS and Microsoft documentation. It is a
> peer review meant to strengthen the work before a hostile reader (an ISSO,
> a 3PAO, or a technically fluent reviewer) sees it — **not** a security
> control assessment or an authorization opinion. Every criticism is paired
> with a recommendation; where the series verified clean, that is stated
> plainly to its credit.
>
> **Scope reviewed:** `Vol_0_Book_00_OrgComp_Executive_Summary.qmd` at HEAD
> (Date Code 2026-07-14), with excursions into Vol I Books 05–06 where Vol 0
> summarizes them. **Baseline:** the v2 critique (2026-07-13) — v2's internal
> findings are not repeated here; v2 Concern 5 ("necessity claims still lack
> a co-located rebuttal") is directly serviced by findings E4 and E9 below.

## Method and epistemic status

Verification ran on 2026-07-15 via a fan-out research harness: 105 subagents,
23 sources fetched, 87 falsifiable claims extracted, 25 adversarially verified
by independent 3-vote panels (a claim needed to survive attempted refutation).
Three tiers of confidence apply below, and each verdict is labeled:

- **[3-0 voted]** — survived unanimous adversarial verification against primary
  sources.
- **[primary-source]** — verbatim quote pulled from an authoritative document
  (FedRAMP GitHub org, CISA guidance, Microsoft Learn, AWS docs, NSA FAQ), not
  separately re-voted.
- **[arithmetic]** — checkable by computation from physical constants.

Access caveat: `fedramp.gov`, `cisa.gov`, and `marketplace.fedramp.gov`
returned HTTP 403 to direct sandbox fetches; verification of FedRAMP content
used the **FedRAMP GitHub organization** (`FedRAMP/2026`,
`FedRAMP/2026-markdown`, `FedRAMP/rules`, `FedRAMP/marketplace-fedramp-gov-data`),
which is the authoritative publication source for the website. CISA findings
rest on the implementation-guidance page plus corroborating secondary coverage.
CR26 is on a rolling changelog (release 2026.07.14.01 was one day old at
verification time) — counts and deadlines can move.

## Bottom line up front

**The program-timeline spine of Vol 0 is solid — impressively so.** Every
FedRAMP 20x milestone date matches the official timeline verbatim; "CR26" and
"Class A/B/C" are genuine FedRAMP terminology (three weeks old at time of
writing, and the series had them right); the 46-indicator / 10-theme KSI count
matches a mechanical grep of the official catalog; the FIPS 140-2 sunset,
BOD 25-01, SP 800-53 Release 5.2.0, the Route 53 DNSSEC platform gap, and the
latency physics all check out.

**But three load-bearing claims failed verification, and they are not nits:**

1. **BOD 26-04 is mischaracterized.** The directive is a *risk-based
   remediation* order; "VDR/VER" in the FedRAMP response means *Vulnerability
   Detection and Response / Vulnerability Evaluation and Reporting* — not
   vulnerability-disclosure documents — and **no SBOM or VEX requirement
   exists in BOD 26-04**. Vol 0's timeline row ("SBOM + vendor disclosure
   required") and Vol IV Book 02's "BOD 26-04 Gate" framing attribute the
   series' SBOM/VDR/VEX pipeline to the wrong instrument.
2. **The Kerberos-multipath motif is contradicted by Microsoft's own
   documentation.** Windows Kerberos does not put client IPs in tickets by
   default — precisely because of DHCP and NAT — so SD-WAN path steering does
   not "structurally break" Kerberos. The 45-second-logon phenomenon the
   series describes is real, but its stated mechanism is wrong.
3. **The series' own canon contradicts Book 05's flagship appendix.** The
   repo's FINDING-001 fixture (with a verbatim Microsoft Learn citation)
   records that **Informed Network Routing is unavailable in GCC Moderate** —
   the very cloud variant Book 05's "Cisco Catalyst SD-WAN + Microsoft INR,
   FedRAMP Moderate / M365 GCC" appendix is scoped to.

And one doctrinal overstatement needs a co-located rebuttal (v2 Concern 5,
now with the receipts): **FedRAMP's own Rev 5 SC-8 guidance is
protocol-agnostic and admits non-IPsec closure paths**, so "there is no second
way to encrypt a DIA circuit at the network layer" cannot survive a reviewer
who has read the FedRAMP blog post it collides with. The defensible core of
the necessity claim survives; the absolutist phrasing does not.

---

## Part 1 — External verification scorecard

| # | Vol 0 claim | Verdict | Basis |
|---|---|---|---|
| E1 | FedRAMP 20x hard-deadline table (Jul 6 / Jul 28 / Aug 3 / Aug 31, 2026; Jan 1, 2027; Jun 11, 2027) | **CONFIRMED** — all six dates verbatim in the official timeline | [3-0 voted] |
| E2 | "Class A/B/C" and "CR26" are real FedRAMP terminology | **CONFIRMED** — `FedRAMP/schemas`: "Consolidated Rules 26 (CR26)"; `FedRAMP/2026` class.md defines Classes A–D | [3-0 voted] |
| E3 | KSI catalog: "46 indicators across 10 themes" | **CONFIRMED** — mechanical count of `reference/key-security-indicators.md` = exactly 46 IDs, 10 themes | [3-0 voted] |
| E4 | "Consolidated Rules … effective June 25, 2026" | **IMPRECISE** — launched Jun 24 (patch 2026.06.25.01 on Jun 25); optional adoption Jul 4, 2026; mandatory effect Jan 1, 2027 | [3-0 voted] |
| E5 | BOD 26-04 exists; Aug 7, 2026 agency-policy deadline | **CONFIRMED** — issued Jun 10, 2026, "Prioritizing Security Updates Based on Risk"; Aug 7 verbatim in CISA guidance | [3-0 voted] |
| E6 | Dec 7, 2026 = "BOD 26-04 VDR/VER deadline — SBOM + vendor disclosure required" | **WRONG AS STATED** — Dec 7 is (a) agencies begin risk-tiered remediation and (b) FedRAMP VDR/VER rules become mandatory (NTC-0014). VDR = Vulnerability *Detection and Response*, VER = Vulnerability *Evaluation and Reporting*. **No SBOM/VEX requirement found in the BOD** | [3-0 voted] |
| E7 | Infoblox FedRAMP Moderate DDI, "CSO FR2017257053, authorized January 2023, AWS GovCloud" | **SUPERSEDED — the DDI scope wasn't authorized in 2022/2023 at all.** CSO ID, Moderate level, and GovCloud hosting are confirmed for FR2017257053, and the correct original authorization date is Dec 15, 2022 (Agency: US Census/Commerce) — but that action covered **BloxOne Threat Defense Federal Cloud** (a DNS-security/threat-intel product: CSP, TIDE, Dossier), not DDI/IPAM, per Infoblox's own Jan 26, 2023 press release. The v3 "DDI SaaS ... confirmed" verdict below was reading the *current* FedRAMP Marketplace page, which now reflects a **July 22, 2026** boundary expansion (Universal DDI Management, NIOS-X Servers, Universal Asset Insights added to the same CSO, rebranded Infoblox Government Cloud) — an event three weeks after this critique was written. Every downstream doc citing "FR2017257053" for DDI closure must anchor to the July 2026 event, not the 2022/2023 one. | [correction 2026-07-28] |
| E8 | FIPS 140-2 certificates → CMVP Historical List Sept 21, 2026 | **CONFIRMED** | [primary-source] |
| E9 | SC-8/SC-8(1) on DIA "can only be closed by an IPsec overlay; TLS provides no closure" | **OVERSTATED** — see Concern 4. FedRAMP's Rev 5 SC-8 guidance requires "FIPS 140 validated encryption," names no protocol, admits a physical path (SC-8(5)/CAA) and inheritance | [primary-source] |
| E10 | TIC 3.0: DIA "permissible only when the security-capabilities catalog is satisfied at the distributed enforcement point" | **DIRECTIONALLY CONFIRMED, slightly stronger than the text** — the guidance standard is "commensurate level of protection based on the agency's risk tolerance"; also, Branch Office Use Case **v3.0 (July 2025)** exists and should be the cited version | [primary-source] |
| E11 | M365 Optimize/Allow/Default categories and local-egress principles | **CONFIRMED** | [primary-source] |
| E12 | Microsoft INR exists and integrates with partner SD-WAN | **CONFIRMED — but unavailable in GCC Moderate/GCC High/DoD**, per the Microsoft doc the repo's own FINDING-001 quotes. See Concern 2 | [primary-source] |
| E13 | CNSA 2.0: "Jan 1, 2027 acquisition gate (NSS) — ML-KEM-1024 + ML-DSA-87 for new NSS acquisitions" | **LARGELY CONFIRMED, one word strong** — NSA FAQ v2.1: new NSS acquisitions must **support** CNSA 2.0 from Jan 1, 2027 "unless an exception is explicitly noted"; exclusive use lands 2033. Algorithm names/parameter sets correct | [primary-source] |
| E14 | SP 800-53 Release 5.2.0, Aug 27, 2025, adding SA-15(13), SA-24, SI-2(7) | **CONFIRMED exactly** (plus SI-7(12) revision) | [primary-source] |
| E15 | "2-year cadence from Release 5.2.0" → next 800-53 release ~Aug 2027 | **UNSUPPORTED** — NIST announces no release cadence; this is extrapolation presented as schedule | [primary-source] |
| E16 | Route 53 private hosted zones cannot be DNSSEC-signed | **CONFIRMED** — AWS: signing "on public zones" only. Bonus constraints worth citing: KMS key must be ECC_NIST_P256 **in us-east-1**; TTLs capped at one week; no multi-vendor configs | [primary-source] |
| E17 | BOD 25-01 (SCuBA for M365) "issued December 2024" | **CONFIRMED** — Dec 17, 2024; M365 was the only finalized baseline at issuance, matching the series' characterization | [primary-source] |
| E18 | GEO ≈238 ms one-way; LEO ~550 km, 20–40 ms; fiber ≈200,000 km/s vs 299,792 km/s vacuum | **CONFIRMED** — 2×35,786 km ÷ 299,792 km/s = 238.7 ms; fiber at n≈1.47 → ~204,000 km/s; Starlink altitude and latency figures consistent with published measurements | [arithmetic] |
| E19 | Kerberos "ticket bound to a network session breaks structurally under SD-WAN multipath" | **CONTRADICTED** — Windows KILE ships with `ClientIpAddresses = 0` (no IPs in tickets) *"because of Dynamic Host Configuration Protocol and network address translation issues"*; the Caddr field is optional and enforcement is opt-in on the resource server | [primary-source] |
| E20 | The internal "29-rule KSI decomposition" | **Matches nothing in official sources** — as the series' own CR26 reconciliation already discloses. External check confirms: zero occurrences of any 29-rule structure in the CR26 corpus | [3-0 voted] |

Two refinements from the verification that Vol 0 should absorb even where it
was right:

- **KSI applicability is now by Class, not by Low/Moderate baseline.** The
  catalog no longer labels indicators by impact level; Class B has five
  optional indicators, Class C mandates the full set. Vol 0's "for Moderate"
  framing of the 46 is an approximation that a current reader of the catalog
  will notice.
- **Class-assurance ordering deserves one explicit sentence.** Per
  `class.md`, Class A covers "most non-sensitive use cases and *some* Low,
  Moderate, or High security objectives," Class C "most Low **and Moderate**"
  — one verification thread initially read Class A as the top tier and had to
  be refuted by the source text. Vol 0 uses the classes correctly (it puts
  SSA's inherited Moderate providers in the Class C pipeline) but never states
  the ordering; a reader who assumes A > B > C will misread the Aug 3 milestone
  exactly the way that thread did.

---

## Part 2 — Concerns, in priority order

### Concern 1 — BOD 26-04 is mischaracterized, and Vol IV Book 02 is built on the mischaracterization (NEW, HIGH)

Vol 0's Broader Federal Clock and hard-deadline rows render Dec 7, 2026 as
"**BOD 26-04 VDR/VER deadline | SBOM + vendor disclosure required;
KSI-011–014 become evaluable**," and the Vol IV Book 02 summary frames the
SBOM/VDR/VEX pipeline as "the BOD 26-04 Gate."

What the primary sources say [3-0 voted]:

- BOD 26-04, "Prioritizing Security Updates Based on Risk" (June 10, 2026,
  superseding BOD 19-02 and BOD 22-01), is a **risk-tiered vulnerability
  remediation** directive (KEV/exposure/automatability/impact; 3/14/60-day
  tiers). CISA's guidance: "By December 7, 2026, agencies must begin
  evaluating and remediating vulnerabilities following the timelines in
  BOD 26-04."
- FedRAMP's response is Public Notice **NTC-0014** (2026-06-16), which makes
  its **VDR** (*Vulnerability Detection and Response*) and **VER**
  (*Vulnerability Evaluation and Reporting*) rule sets mandatory 2026-12-07
  (optional adoption 2026-07-04, grace ends 2027-03-07), for both 20x and
  Rev 5 offerings.
- Targeted searches of the directive, its implementation guidance, and the
  FedRAMP response found **no SBOM, VEX, or vendor-disclosure-document
  requirement**. The series' "VDR = Vulnerability Disclosure Report" expansion
  appears to be a conflation — plausibly with NIST SBOM/VDR practice
  documents or the EU Cyber Resilience Act (whose SBOM deadlines do land in
  Dec 2026).

Why it matters: this is not a date error — the date is right — it is an
**instrument attribution error**. The SBOM/VDR/VEX pipeline in Vol IV Book 02
is good engineering and defensible on other authorities (EO 14028 §4, OMB
M-22-18/M-23-16 attestations, SR-family controls, NIST SP 800-161). But a
reviewer who pulls up BOD 26-04 and finds a patching directive where the
series promised an SBOM mandate will downgrade every other authority citation
in the corpus. The fix is cheap; the credibility cost of not fixing it is not.

**Recommendation.** (a) Reword the two Vol 0 rows: Dec 7, 2026 = "BOD 26-04
risk-tiered remediation in force; FedRAMP VDR/VER rules mandatory
(NTC-0014)." (b) Re-anchor Vol IV Book 02's SBOM/VDR/VEX pipeline to its real
authorities and let BOD 26-04 support only the remediation-timeline half.
(c) Expand VDR/VER correctly on first use. (d) Sweep the corpus for other
"BOD 26-04" citations (the compliance spine's `cisa-bod` driver tags
included) — this error propagates through generated artifacts.

### Concern 2 — The repo's own FINDING-001 contradicts Book 05's INR appendix (NEW, HIGH)

Book 05's Appendix A ("Cisco Catalyst SD-WAN and Microsoft 365 Informed
Network Routing: Federal Implementation Reference") is explicitly scoped to
"**FedRAMP Moderate — civilian federal agencies operating M365 GCC
tenants**," and its integration tables, KSI evidence contracts, and TIC
alignment all presume INR activation.

The repo's own canon knows better:
`tests/fixtures/contract/m365/informed-network-routing-unavailable-gcc-moderate.yaml`
codifies **FINDING-001** with a verbatim Microsoft Learn citation (accessed
2026-04-17): *"Microsoft 365 informed network routing supports tenants in WW
Commercial cloud but not the GCC Moderate, GCC High, DoD, Germany, or China
clouds."* The external check confirms the Microsoft doc and the feature's
existence [primary-source]; the unavailability quote is Microsoft's own text.

So the substrate ships a fixture proving the adapter must gracefully handle
INR being *absent* in exactly the tenant class for which Book 05's appendix
prescribes INR. Vol 0 endorses Book 05 wholesale and never surfaces the
caveat. This is the same failure class as v2's Concerns 1–2 (two pages of the
corpus disagreeing), except here one of the pages is machine-enforced canon —
which makes it worse: the series' *strongest* evidence artifact refutes its
*most detailed* vendor appendix.

**Recommendation.** Add a prominent FINDING-001 callout to Book 05 Appendix A:
INR telemetry integration is a **commercial-cloud capability**; in GCC
Moderate the appendix's architecture degrades to Cloud OnRamp probe-based
steering against published M365 endpoints (which works and still satisfies the
appendix's control table) *without* the Microsoft-fed telemetry channel.
State what is lost, what remains, and cite FINDING-001. One paragraph
converts a contradiction into a demonstration that the drift machinery works.

### Concern 3 — The Kerberos-multipath motif is technically wrong as stated (NEW, HIGH)

The claim appears at least three times (Vol 0's Book 03 summary: "a Kerberos
ticket bound to a network session breaks structurally under SD-WAN multipath";
Book 05: Kerberos is "session-based, network-location-dependent"; Book 06 is
named as documenting "the mechanism"). Microsoft's KILE documentation
contradicts the premise [primary-source]:

- The `ClientIpAddresses` KDC/client setting that would put IP addresses into
  the ticket Caddr field **defaults to 0 (disabled)** — and Microsoft's stated
  reason is verbatim *"because of Dynamic Host Configuration Protocol and
  network address translation issues."* Tolerating source-address change is a
  design property of the deployed protocol, and SD-WAN path steering is,
  from the KDC's perspective, just another NAT/DHCP-like address event.
- Addresses are not added to TGS_REP by default, and Caddr enforcement is an
  opt-in choice of the resource server — not a structural property of
  Kerberos.

What *is* real: the 45-second field-office logon under **active-passive
failover** — TCP sessions to the DC time out, CLDAP/DC-locator re-discovers,
tickets get re-requested. That is a transport-availability phenomenon, and
active-active multipath genuinely fixes it. The series has the right
prescription attached to the wrong pathology.

**Recommendation.** Rewrite the motif everywhere it appears: Kerberos does not
break because tickets are path-bound (they aren't, by default); Kerberos
*logon experience* breaks when the transport under it fails over slowly, and
the deeper modernization argument (Entra tokens carry cryptographic
authorization that survives any transport; Kerberos depends on continuous
line-of-sight to a DC) stands on its own without the false claim. A hostile
reviewer with a protocol background will find this in minutes, and it sits at
the foundation of the series' identity-modernization argument.

### Concern 4 — The SC-8 necessity claim collides with FedRAMP's own published guidance (CARRIED FROM v2 Concern 5, now with receipts, MED-HIGH)

Vol 0's Closure Necessity Doctrine: SD-WAN is required because "there is no
second way to encrypt a DIA circuit at the network layer," and Book 05's
callout adds that application-layer TLS "provides no network-layer guarantee"
so nothing but an IPsec overlay closes SC-8 on DIA.

FedRAMP's Rev 5 SC-8 data-in-transit guidance
(fedramp.gov, "The Rev. 5 Approach to SC-8, and Protecting Data-in-Transit,"
2023-07-13) says, verbatim [primary-source]:

- "Implement **FIPS 140 validated encryption** from the data center edge to
  every other data center edge" — **protocol-agnostic**; IPsec is never
  mandated, and FIPS-validated TLS is not excluded.
- Rev 5 split the concepts: encryption stays in SC-8(1), **physical
  protection moved to SC-8(5)** — FedRAMP's Rev 4 PDS requirement became a
  Controlled Access Area requirement, satisfiable through PE-family controls.
  A non-cryptographic closure path exists in the control family itself.
- SC-8/SC-8(1)/SC-8(5) are **inheritable**: traffic originating and
  terminating inside an authorized IaaS/PaaS boundary meets SC-8 with no
  customer overlay at all.

And Cisco's own TIC 3.0 Architecture Guide — the vendor the series uses as its
SD-WAN reference — states the DIA security protections "are **not exclusive to
SD-WAN**" [primary-source]. Mechanism-class honesty cuts both ways: plain
site-to-site IPsec, ZTNA tunnels, and WireGuard-class overlays are all
network-layer encryption without being SD-WAN.

To be fair to the doctrine, its defensible core is strong and worth keeping:

1. On a branch DIA circuit, per-application TLS covers only the flows that
   negotiate it; DNS, legacy protocols, and misconfigured apps ride bare. An
   overlay is the only mechanism that covers **all** flows uniformly,
   regardless of application behavior — that argument survives.
2. The CAA/physical path and boundary inheritance don't apply to a field
   office egressing over the public internet.
3. Among overlay mechanisms, SD-WAN is the one that *also* delivers the SC-5
   traffic-class and SI-4 telemetry closures the doctrine bundles with it.

**Recommendation.** Keep the necessity table but restate the SC-8 row as a
**coverage-completeness** claim, not an exclusivity claim: "application-layer
TLS closes SC-8 per-flow and is accepted by FedRAMP when FIPS-validated;
only a network-layer overlay closes it for *all* flows on the circuit
simultaneously, and among overlay classes SD-WAN uniquely co-delivers SC-5 and
SI-4." Then add the co-located rebuttal box v2 asked for, citing the FedRAMP
SC-8 post directly — pre-empting the strongest counter-source instead of
leaving it for the reviewer to discover.

### Concern 5 — TIC 3.0 phrasing is one notch stronger than the guidance, and the cited use case is two versions stale (MED)

The Branch Office Use Case supports the series' direction emphatically — it
calls the branch-to-web pattern "the riskiest," requiring "the greatest amount
of rigor … applied to security capabilities in the PEP at the branch office"
[primary-source]. But the operative TIC 3.0 standard is a **risk-tolerance**
test — "commensurate level of protection based on the agency's risk
tolerance" at distributed enforcement points — not Vol 0's "permissible *only
when* the security-capabilities catalog is satisfied." The distinction matters
to exactly the audience Vol 0 addresses: an AO can lawfully accept a
distributed PEP that implements a risk-appropriate subset of the catalog.
Separately, CISA posted **Branch Office Use Case v3.0 in July 2025**; the
series' framing traces to the April 2021 v1.0. Nothing found suggests v3.0
undercuts the argument, but a 2026 document citing a 2021 version of a
guidance that revised twice since is an easy credibility ding.

**Recommendation.** Soften "only when the catalog is satisfied" to "only
behind a distributed PEP providing protections commensurate with agency risk
tolerance (TIC 3.0), which in practice means the applicable security
capabilities catalog entries," and re-cite against v3.0 after checking it.

### Concern 6 — Small factual burrs that are one-line fixes (LOW, but do them)

- **"CR26 … effective June 25, 2026"** → launched June 24, 2026 (announcement
  post June 25); optional adoption July 4, 2026; mandatory January 1, 2027.
  "Effective" is the one word a FedRAMP-literate reader will snag on. [3-0 voted]
- **Infoblox authorization date** → December 15, 2022 (FedRAMP Marketplace
  dataset; agency authorization via Census/Commerce), not "January 2023" —
  the doc echoes the vendor press-release date. [3-0 voted] **Superseded
  2026-07-28: the Dec 2022 action authorized BloxOne Threat Defense Federal
  Cloud, not DDI — see the E7 correction above. DDI (Universal DDI
  Management) was added to the CSO's boundary July 22, 2026; that is the
  date every DDI-closure claim in this series should cite.**
- **"~Aug 2027 next NIST SP 800-53 release (2-year cadence)"** → NIST
  announces no cadence. Label it an assumption or drop it; everything else in
  that row (5.2.0 date, SA-15(13)/SA-24/SI-2(7)) verified exactly. [primary-source]
- **CNSA 2.0 row** → "must *support* CNSA 2.0 algorithms unless an exception
  is explicitly noted" is the FAQ's wording; the row's harder "gate" framing
  slightly overstates a requirement that carries a documented exception path.
  ML-KEM-1024 / ML-DSA-87 verified correct. [primary-source]
- **KSI "for Moderate" framing** → applicability is now per-Class (B/C), not
  per-baseline; and consider one sentence stating the Class ordering
  (A = least assurance information, D = most) so readers don't invert it. [3-0 voted]

---

## Part 3 — What verified clean (credit where due)

The verification round is not all bad news — the opposite. For a corpus this
young citing a rule set three weeks old:

- **All six hard-deadline dates verbatim-match** FedRAMP's official timeline,
  including the obscure ones (Aug 10 Rev 5 Ready-conversion window). [3-0 voted]
- **The terminology is real and current** — "CR26" and Class A/B/C appear in
  FedRAMP's own schemas and site source, exactly as the series uses them.
  A verification thread that asserted CR26 was invented terminology was
  *refuted by the primary sources*. The series was ahead of its skeptics. [3-0 voted]
- **46 KSIs / 10 themes** — exact mechanical match, and the series' CR26
  reconciliation already discloses the 19/46-mapped status honestly. [3-0 voted]
- **Route 53 private-zone DNSSEC gap** — confirmed, and AWS's additional
  constraints (us-east-1 P-256 KMS key, one-week TTL cap, no multi-vendor)
  actually *strengthen* Vol I Book 01's platform-gap argument; cite them. [primary-source]
- **BOD 25-01, FIPS 140-2 sunset, SP 800-53 5.2.0 contents, M365
  Optimize/Allow/Default, and every latency/physics number** — confirmed.
  The G.114 and propagation arithmetic is exactly right. [primary-source / arithmetic]

## Prioritized actions

1. **Fix the BOD 26-04 characterization** in Vol 0 (two rows) and re-anchor
   Vol IV Book 02's SBOM pipeline to its real authorities; sweep generated
   artifacts for the propagated citation. (Concern 1)
2. **Add the FINDING-001 caveat to Book 05 Appendix A** and state the
   degraded-mode architecture for GCC Moderate. (Concern 2)
3. **Rewrite the Kerberos-multipath motif** in Vol 0's Book 03/05 summaries
   and wherever Book 06 documents "the mechanism" — failover latency, not
   ticket path-binding. (Concern 3)
4. **Restate the SC-8 necessity row as coverage-completeness** and add the
   co-located rebuttal citing FedRAMP's SC-8 guidance. (Concern 4; closes v2
   Concern 5)
5. **Soften the TIC 3.0 phrasing and re-cite against Branch Office Use Case
   v3.0.** (Concern 5)
6. **Apply the one-line date/wording fixes.** (Concern 6)

## Closing

v2 ended by observing that the series' dominant risk had shifted from
over-claiming to self-contradiction. v3's external round sharpens that: **the
series is factually excellent where facts are lookup-shaped** — dates,
terminology, catalogs, platform limits — **and vulnerable where facts are
mechanism-shaped**: what a directive actually mandates, what a protocol
actually binds, what a control family actually accepts. All three HIGH
findings are of the second kind, and all three are fixable without weakening
the series' thesis, because in each case the *prescription* (SBOM pipeline,
SD-WAN overlay, token-based identity) is right even where the cited
*compulsion* is wrong. Fix the compulsions; the architecture argument is
strong enough to stand on accurate ones.
