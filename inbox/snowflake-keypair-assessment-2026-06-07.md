# Snowflake Key-Pair Conversion — Assessment vs. UIAO Doctrine

> **Status:** scratch / non-canon (per `inbox/README.md`). This is a traceable
> assessment record, not a governance artifact. Nothing here is SSOT. External
> Snowflake-product facts are cited at a confidence level appropriate for an
> internal assessment and are flagged where they must be re-verified against
> Snowflake's own documentation before any customer-facing or canonical use.

**Date:** 2026-06-07
**Subject:** Snowflake's migration of account authentication from passwords to
**RSA key-pair authentication** ("key-pair conversions"), assessed against the
UIAO authentication-transformation doctrine.
**Question put:** *Assess Snowflake for Key Pair conversions vs UIAO.* — i.e.,
does Snowflake's password→key-pair conversion align with how UIAO governs
credential modernization, where does it land on UIAO's interim-vs-steady-state
axis, and what would it take for UIAO to govern it.

---

## 1. Executive verdict

Snowflake key-pair conversion is **directionally correct but is an interim
posture, not the UIAO steady state.** It is the Snowflake-platform analogue of
the SQL Server *type-S → type-E* transformation governed by **ADR-091**: it
retires a replayable, IdP-invisible shared secret (the password) and moves to
public-key authentication, which is the direction **IA-5(2)** and **IA-2(8)**
point. That much UIAO endorses without qualification.

But a Snowflake RSA key pair, as conventionally deployed, is a **software-held,
exportable private key in a PEM file** — a *stored bootstrap credential*. UIAO
doctrine treats stored bootstrap secrets (SP-with-secret, vault-held key, raw
certificate file) not as the destination but as a **documented, compensating-
control-bound, sunset-dated exception** — exactly the role **ADR-068** assigns
to Certificate-Based Authentication as the *interim* NTLM-replacement posture,
and exactly the reasoning the SQL narrative used to reject "SP/vault reintroduces
a stored bootstrap secret" (`inbox/sql-narrative-assessment-2026-06-06.md`,
critique #3).

The UIAO-aligned **steady state** for Snowflake is the same shape as everywhere
else in the substrate: **federate the credential authority to the IdP (Entra)**
so that Conditional Access and Defender see the sign-in, and for non-human
principals use **workload identity federation (an Azure Managed Identity → a
short-lived token), not a stored key**. Key-pair conversion is the right *first*
move off passwords; it is the bridge, not the bank.

| Axis | Password (today) | Key-pair (the conversion) | UIAO steady state |
|---|---|---|---|
| Replay-resistant (IA-2(8)) | ❌ | ✅ (signed JWT, per-auth) | ✅ |
| Public-key based (IA-5(2)) | ❌ | ✅ | ✅ |
| IdP-visible / Conditional-Access-evaluable | ❌ | ❌ (auth terminates at Snowflake) | ✅ (Entra SSO / OAuth) |
| Credential-free (no stored secret) | ❌ | ❌ (PEM private key at rest) | ✅ (Managed Identity / WIF) |
| Non-exportable key custody (TPM/HSM) | n/a | ⚠️ only if explicitly engineered | ✅ |
| UIAO disposition | **must end** | **authorized interim / exception** | **target** |

---

## 2. What Snowflake key-pair conversion actually is

> ⚠️ **Verify against Snowflake docs before canonical use.** The following is
> the assessment author's understanding as of the knowledge cutoff; treat the
> specifics (key sizes, parameter names, deprecation dates) as claims to confirm.

- Snowflake supports **key-pair authentication**: a user is assigned an RSA
  **public** key via `ALTER USER <u> SET RSA_PUBLIC_KEY='...'`; the client holds
  the matching **private** key (a PEM file, optionally passphrase-encrypted) and
  authenticates by signing a JWT that Snowflake verifies against the stored
  public key. RSA 2048-bit is the documented minimum.
- **Key rotation** is first-class: `RSA_PUBLIC_KEY` + `RSA_PUBLIC_KEY_2` allow a
  make-before-break rotation of the active key.
- The **conversion driver** is Snowflake's deprecation of single-factor
  password authentication, accelerated after the 2024 credential-theft campaign
  against Snowflake customer accounts (stolen passwords, no MFA). Snowflake's
  response: **authentication policies**, MFA enforcement for human users, and a
  hard push to **key-pair or OAuth for programmatic / service accounts**, which
  cannot do interactive MFA.
- So "key-pair conversion" in practice = **migrating service/programmatic
  accounts off passwords onto RSA key pairs**, while human users move to
  MFA/SSO. The service-account leg is where the stored-key tension lives.

---

## 3. Mapping onto UIAO doctrine

UIAO already has a fully-formed doctrine for this exact problem shape — it was
written for SQL Server and Kerberos/NTLM, but the logic is platform-agnostic.

### 3.1 The password is a `type-S` login — it must end (ADR-091 §3)

ADR-091 §3: *"SQL Authentication produces no Entra ID sign-in events and is
invisible to Conditional Access and Defender for Identity; it is not an
acceptable steady-state credential."* A Snowflake password is the identical
object class: a platform-local shared secret, replayable, invisible to the IdP.
UIAO's position on it is not "rotate it" — it is **eliminate it**. Snowflake's
own deprecation agrees, which is why the conversion is endorsed.

### 3.2 The key pair is the interim posture, not the destination (ADR-068)

ADR-068 establishes the pattern that a cryptographic, non-password credential
can be the **authorized *interim* posture** while the IdP-federated steady state
is stood up — "**Certificate-Based Authentication is the authorized interim
posture**" (ADR-091 §4, citing ADR-068). A Snowflake RSA key pair occupies that
slot precisely: better than a password, but it is still a **stored credential
the workload holds**, and the authentication terminates at Snowflake, so
**Conditional Access never evaluates it**. Under UIAO doctrine that makes raw
key-pair auth an **exception-register entry**, requiring (per ADR-068 / ADR-091
§4 exception process): the inability-to-federate reason, a named compensating
control, a maximum duration, and a **sunset date**.

### 3.3 The stored private key is the anti-pattern UIAO already named

The SQL narrative assessment (critique #3) records UIAO's rejection of the
alternatives to Managed Identity precisely because **"SP-with-secret / vault
reintroduces a stored bootstrap credential."** A Snowflake `.p8` private key is
that stored bootstrap credential. It is exportable software key material unless
deliberately engineered otherwise; it can be copied, checked into a repo, baked
into a container image, or left on a developer laptop. This is the same risk
class UIAO rejects for Azure service principals — the conversion does **not**
escape it, it relocates it from "password in a config file" to "private key in a
PEM file."

### 3.4 The steady state is IdP federation / workload identity (ADR-002)

ADR-002 makes the **Managed Identity the credential-free destination** (no
stored secret; the platform mints a short-lived token). The Snowflake-native
equivalents that reach this bar:

- **Humans:** Entra **SAML SSO / External OAuth** to Snowflake → the sign-in is
  an Entra event, **Conditional Access + Identity Protection apply**, and MFA /
  device compliance / location signals are enforced at the IdP. This is the
  IA-2(8)/IA-5(2) *and* AC-17/OMB-M-22-09 alignment the SQL narrative critique #1
  insisted on.
- **Service accounts:** **workload identity federation** — an Azure **Managed
  Identity** (or other OIDC workload identity) exchanged for a short-lived
  Snowflake token via External OAuth, **with no RSA private key at rest.** This
  is the Snowflake analogue of "Arc Managed Identity, not SP-with-secret."

  > ⚠️ Confirm current Snowflake support/GA status for Azure managed-identity /
  > workload-identity federation before asserting it customer-facing; if it is
  > not GA for a given workload, key-pair auth is the correct *interim* fallback,
  > which is exactly the ADR-068 interim-posture pattern.

### 3.5 Closure is continuous, not point-in-time (ADR-091 §"continuously verified")

ADR-091 closes a transformation only under *continuous* verification — drift
events (a new type-S login appearing, mode reverting) are violations. The
Snowflake equivalent of a closed conversion: **zero users with password auth
enabled outside the exception register; every key-pair user inside SLA on key
rotation; every key pair carrying a sunset date toward federation.** A new
password-enabled user or an over-age key is a **DRIFT-IDENTITY** event.

---

## 4. Where this lands in the UIAO substrate (if it were to be built)

Snowflake is a **Commercial-cloud SaaS data platform** — it is **outside the
current GCC-Moderate deployment boundary** (AGENTS.md "Cloud boundary"), and it
is **not** one of the two named Commercial exceptions (Amazon Connect,
SailPoint). So before any Snowflake adapter is contemplated, the boundary
question is a gating ADR decision, not an engineering one: a Snowflake exception
would need its own `gcc-boundary` enum value added **in lockstep with an
authorizing ADR** (the pattern ADR-059 set for SailPoint). **This assessment
does not authorize that** — it only locates where it would sit.

*If* authorized, the natural shape:

- **Adapter class × mission-class:** a **modernization / identity** adapter
  (per UIAO_003 §4) — read the Snowflake user inventory + their `TYPE` and
  authentication policy, classify each as `password` / `keypair` / `federated`,
  plan the conversion, and (dry-run-default, like every OrgPath writer) apply
  `ALTER USER` changes. Conformance-axis (read-only) counterpart: assess current
  auth posture without writing.
- **Drift surface:** password-enabled accounts and over-age keys re-surface as
  **DRIFT-IDENTITY**, mirroring the OrgPath brownfield-inventory pattern.
- **KSI:** a key-rotation-cadence + password-elimination KSI family (shape like
  KSI-RECIP), feeding `uiao ksi evaluate`.
- **Evidence binding:** conversion records bind to **IA-5(2)** (public-key auth),
  **IA-2(8)** (replay resistance), and **IA-2/AC-17** (the OMB M-22-09 zero-trust
  anchor) in the control library.

---

## 5. Recommendations

1. **Endorse the conversion as a Phase-A move, not a finish line.** Killing
   Snowflake passwords is unambiguously correct (ADR-091 §3 logic). Say so
   plainly. Do **not** describe key-pair auth as "the secure end state."
2. **Classify raw key-pair auth as the authorized interim posture** (ADR-068
   pattern): every key-pair user is an exception-register entry with a named
   compensating control (mandatory passphrase encryption + restricted key
   custody, ideally HSM/KMS-held and non-exportable), a rotation SLA, and a
   **sunset date toward federation**.
3. **Name the steady state explicitly:** Entra SAML/OAuth SSO for humans (so
   Conditional Access applies), workload-identity federation / Managed-Identity
   OAuth for service accounts (so there is **no stored key**). Verify Snowflake
   GA status before committing this customer-facing.
4. **Treat the PEM private key as a stored bootstrap secret** in all risk
   framing — do not let "we moved off passwords" obscure that an exportable
   credential still exists. This is the critique-#3 lesson applied to Snowflake.
5. **Make closure continuous:** password-enabled-account count and key-age are
   drift signals, not one-time audit checks.
6. **Do not build a Snowflake adapter or claim boundary coverage without a
   gating boundary ADR** (ADR-059 / ADR-033 pattern). Snowflake is Commercial
   SaaS outside the current boundary.

## 6. Not actioned (deliberately)

- **No canon edits, no `UIAO_NNN` allocation, no ADR.** This is a non-canon
  inbox assessment. A real Snowflake position (boundary exception, adapter,
  KSI family, control-library `implemented_by` additions) is **doctrinal** and
  must flow through the canon-change process (ADR + governance review), not a
  scratch note.
- **No Snowflake adapter code.** Section 4 is a placement sketch, not an
  authorization to build.
- **No change to existing IA-5(2) / IA-2(8) control narratives.** They are
  currently scoped to Entra/Intune/AD-CS/CyberArk and `status: not-implemented`;
  adding Snowflake to `implemented_by` is a canon edit out of scope here.

## 7. Provenance

- UIAO doctrine cited: `src/uiao/canon/adr/adr-091-sql-server-authentication-transformation.md`
  (type-S→type-E, interim/exception, continuous closure);
  `src/uiao/canon/adr/adr-068-kerberos-ntlm-elimination.md` (CBA interim
  posture, exception register);
  `src/uiao/canon/adr/adr-002-arc-entra-join-no-domain-join.md` (Managed
  Identity as credential-free destination);
  `src/uiao/canon/adr/adr-059-sailpoint-adapter-family.md` +
  `adr-033-gcc-boundary-drift-class.md` (Commercial-exception boundary pattern).
- Control anchors: `src/uiao/canon/data/control-library/ia/IA-5(2).yml`,
  `IA-2(8).yml`; AC-17/IA-2/OMB M-22-09 zero-trust anchor per
  `inbox/sql-narrative-assessment-2026-06-06.md`.
- Boundary doctrine: `AGENTS.md` "Repository identity → Cloud boundary".
- Snowflake product facts: author knowledge as of cutoff — **flagged for
  re-verification** against Snowflake documentation (§2, §3.4).
