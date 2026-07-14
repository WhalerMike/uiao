# Track 2 — PIV → Entra Certificate-Based Auth + FIDO2 / Passkeys / WHfB

A self-contained learning module on how an Entra ID tenant migrates from
**PIV smartcard authentication via federation (ADFS / PKINIT)** to
**phishing-resistant authentication native to Entra**. Audience:
identity engineers, platform engineers, security architects, and IAM
operators in agencies or enterprises with HSPD-12 / PIV-card heritage.

The track covers two parallel target architectures, because no single
mechanism fits every user population:

- **Entra Certificate-Based Authentication (CBA)** — keeps the PIV
  card, removes ADFS from the path.
- **FIDO2 / Passkeys / Windows Hello for Business (WHfB)** — replaces
  the card with device-bound or platform-bound credentials.

Most real deployments run both: CBA for users who keep their PIV
card, FIDO2/WHfB for everyone else (mobile users, contractors, new
hires, kiosk workers).

The material is vendor-neutral and intended for self-study and team
sharing. The inventory script is read-only and meant to be read as a
worked example of Microsoft Graph SDK usage.

---

## Contents

1. [Why this matters](#why-this-matters)
2. [The starting point — PIV via ADFS](#the-starting-point--piv-via-adfs)
3. [Target architecture 1 — Entra CBA](#target-architecture-1--entra-cba)
4. [Target architecture 2 — FIDO2, Passkeys, WHfB](#target-architecture-2--fido2-passkeys-whfb)
5. [Supporting cast — TAP, Authentication Strengths, Conditional Access](#supporting-cast--tap-authentication-strengths-conditional-access)
6. [Common misconceptions](#common-misconceptions)
7. [Decision tree — which credential for which user?](#decision-tree--which-credential-for-which-user)
8. [Scope of this assessment](#scope-of-this-assessment)
9. [The inventory script — what it produces](#the-inventory-script--what-it-produces)
10. [Sample output (illustrative)](#sample-output-illustrative)
11. [How the script works (annotated walkthrough)](#how-the-script-works-annotated-walkthrough)
12. [Disposition classification](#disposition-classification)
13. [Migration playbooks](#migration-playbooks)
14. [Validation — confirming phishing-resistant adoption](#validation--confirming-phishing-resistant-adoption)
15. [Permissions required](#permissions-required)
16. [Risks and edge cases](#risks-and-edge-cases)
17. [Further reading](#further-reading)
18. [Glossary](#glossary)

---

## Why this matters

Federal identity began with HSPD-12 (2004) and FIPS 201, mandating PIV
smartcards as the workforce identity credential. The card holds X.509
certificates; the cryptographic operation (signing a challenge with
the private key) happens *on the card* and never leaks. PIV has been
phishing-resistant since before "phishing-resistant" was a category
name.

But PIV's typical Entra integration is **federation**: the user
authenticates with PIV against on-prem Active Directory (via PKINIT
in Kerberos, or via smartcard logon on Windows), AD Federation
Services (ADFS) issues a SAML assertion, and Entra trusts that
assertion. The path looks like:

```
PIV card  →  AD KDC (PKINIT)  →  ADFS  →  Entra  →  application
```

That path has problems:

- **ADFS is a single point of failure** for authentication. An ADFS
  outage means no one signs in.
- **ADFS is a single point of attack.** Multiple high-profile
  nation-state incidents (e.g. SolarWinds / Solorigate) exploited
  forged SAML tokens from compromised ADFS instances.
- **The federation hop is opaque to Entra-side telemetry.** Entra sees
  "SAML token presented" — it doesn't see *how* the user actually
  authenticated. Conditional Access policies that depend on
  *Authentication Strength* can't reliably evaluate what happened
  upstream.
- **ADFS infrastructure is operational debt.** Servers to patch,
  certificates to rotate, claim rules to maintain. Microsoft has
  formally encouraged migration off ADFS since 2018.
- **PIV cards alone don't help mobile or contractor users**, and ADFS
  doesn't help anyone who needs to authenticate from a device that
  isn't joined to the on-prem domain.

The modernization play is twofold:

1. **Move PIV authentication directly into Entra** with CBA, removing
   the ADFS hop. The same physical card is still used; only the path
   changes.
2. **Add FIDO2 / Passkeys / WHfB** for users who don't have a PIV or
   for whom the PIV path is impractical (mobile, contractor, BYOD,
   shared kiosk).

Both target the same property — **phishing-resistant authentication**,
which NIST 800-63B promotes as the AAL3 standard and Microsoft enforces
via Conditional Access "Authentication Strengths".

---

## The starting point — PIV via ADFS

A typical pre-migration topology:

```
                                                    ┌──────────────────┐
                                                    │   Application    │
                                                    │ (Entra-protected)│
                                                    └────────▲─────────┘
                                                             │
                                                       (SAML/OIDC)
                                                             │
                                                    ┌────────┴─────────┐
                                                    │      Entra       │
                                                    │     Tenant       │
                                                    │ (federated trust)│
                                                    └────────▲─────────┘
                                                             │
                                                       SAML assertion
                                                             │
   PIV card                                          ┌────────┴─────────┐
       │                                             │       ADFS       │
       │ PKINIT / smartcard logon                    │ (issues SAML for │
       ▼                                             │  federated      │
   ┌──────────────┐  Kerberos/NTLM       ┌──────────►│  domains)       │
   │  AD KDC      ◄──────────────────────┤           └──────────────────┘
   │  (on-prem)   │                      │
   └──────────────┘                      │
                                         │
                                  ┌──────┴──────┐
                                  │   User      │
                                  │  workstation│
                                  └─────────────┘
```

Entra sees the user as authenticated, but it has no insight into
*how*. The card could have been used, or it could have been replaced
by a password if ADFS allows fallback. Conditional Access policies
that *require* phishing-resistant auth must trust ADFS to enforce that
— and ADFS doesn't always tell Entra what it actually did.

The migration replaces this with one of two paths.

---

## Target architecture 1 — Entra CBA

The user keeps the PIV card. The card's cert is presented *directly
to Entra*, with no ADFS or AD KDC in the path for Entra
authentication. Entra evaluates the cert against issuer CAs that the
tenant administrator has uploaded.

```
   PIV card
       │
       │ TLS client-cert auth to Entra
       ▼
   ┌──────────────────────────────────────────────┐
   │  Entra ID                                    │
   │  ├─ Trusted issuer CAs (uploaded by admin)   │
   │  ├─ Authentication binding policy            │
   │  │  (cert subject → Entra user)              │
   │  ├─ Authentication strength: which CA roots, │
   │  │  which OIDs map to AAL3?                  │
   │  └─ Conditional Access evaluates auth        │
   │     strength against policy                  │
   └──────────────────────────────────────────────┘
              │
              ▼  access token
       Application
```

### Setup elements (admin)

| Element                                  | What it is                                                                              |
|------------------------------------------|-----------------------------------------------------------------------------------------|
| Trusted issuer CA                        | The PIV-issuing CA (DoD PIV CA, federal common policy CA, etc.) uploaded to the tenant. |
| User binding                             | Rule that maps cert → Entra user. Common choices: PrincipalName SAN, RFC822 SAN, SKI, Issuer+SerialNumber. |
| Authentication binding policy            | Which OIDs / issuer rules map to "single-factor" vs "multi-factor" auth.                |
| Authentication method policy (X509)      | Enable CBA; target groups; allowed issuers.                                             |
| Conditional Access strength              | Reference an Authentication Strength that *requires* CBA-MFA.                           |

### What stays the same

- The PIV card itself. No new hardware.
- Card middleware on the endpoint (ActivClient, YubiKey Manager,
  built-in Windows smartcard subsystem).
- Issuer CAs and their lifecycle (still managed by the original PIV
  card issuer).
- Card renewal and revocation processes.

### What goes away

- ADFS in the Entra authentication path (you may still keep ADFS for
  legacy SAML apps, but Entra no longer depends on it).
- Federation trust on the domain.
- Claim rules, ADFS extensions, ADFS HA infrastructure.

### What's new

- A tenant-side mapping from "user X with PIV card Y" to an Entra user
  object, configured per binding rule.
- Conditional Access policies that explicitly require an
  Authentication Strength satisfied by CBA-MFA.

---

## Target architecture 2 — FIDO2, Passkeys, WHfB

This is a *family* of related but distinct credentials. They all
share the WebAuthn / FIDO2 specification under the hood (a public-key
challenge/response exchange between authenticator and Entra), but
differ in how the private key is stored and made available.

### FIDO2 security key (hardware)

A USB / NFC / Bluetooth hardware token (YubiKey, Feitian, Titan Key,
Microsoft-branded keys, etc.). The private key never leaves the
device. The user touches/PINs the key to authorize a signing
operation. Cross-platform, interoperable, and traditionally the
canonical "phishing-resistant" credential.

```
   FIDO2 key (USB)
       │
       │ user touches key, PIN entered
       │ WebAuthn assertion signed
       ▼
   Browser  →  Entra
                │
                ├─ Validate signature against registered public key
                ├─ Check rpId binds to login.microsoftonline.com
                └─ Issue Entra token
```

Phishing-resistant by construction: the `rpId` binding means the key
will only sign for the exact origin it was registered against. A
phishing site at `login.microsoft-secure.evil` cannot get a valid
signature.

### Passkey (synced)

A FIDO2 credential whose private key is stored in a cloud-synced
keychain — Apple iCloud Keychain, Google Password Manager, 1Password,
Bitwarden, Microsoft Authenticator. The user authenticates with a
biometric or PIN on any device where the keychain is unlocked.

| Property                  | Hardware FIDO2 key      | Synced passkey           |
|---------------------------|-------------------------|--------------------------|
| Private key custody       | Device only             | Cloud-synced             |
| Cross-device usability    | Plug into each device   | Auto-available           |
| Phishing-resistant        | Yes                     | Yes                      |
| AAL3 (NIST 800-63B)       | Yes                     | Generally no             |
| Recovery model            | Backup key + admin reset| Cloud account recovery   |
| Typical fit               | High-assurance roles    | General workforce        |

The AAL3 gap matters for federal use. Synced passkeys *can* meet AAL3
if the cloud vendor implements specific custody controls, but most
deployments use them for AAL2.

### Passkey (device-bound)

A FIDO2 credential whose private key is bound to a specific device's
secure element (TPM, Secure Enclave). Available in Microsoft
Authenticator on iOS and Android in device-bound mode. Equivalent to
a hardware FIDO2 key in security properties, but living inside a
phone app instead of a separate token.

### Windows Hello for Business (WHfB)

Microsoft's device-bound implementation, specifically for
Windows-joined devices. The private key lives in the device's TPM;
the user unlocks it with a PIN, fingerprint, or face recognition (the
gesture is the *unlock*, not the credential — the credential is the
key in the TPM).

| Aspect                | WHfB                                                       |
|-----------------------|------------------------------------------------------------|
| Where the key lives   | Windows device TPM                                         |
| What unlocks the key  | PIN / Windows Hello biometric                              |
| Cross-device          | No — each device has its own credential                    |
| Joins                 | Entra-joined, Hybrid-joined, Entra-registered              |
| Federation impact     | Eliminates need for cached domain credentials              |
| Cloud Kerberos        | WHfB can act as Kerberos ticket source via cloud trust     |

WHfB is the canonical Windows passwordless story. For users on
managed Windows devices, it's often deployed first because it
requires no per-user hardware purchase.

### What stays the same (across all FIDO2 variants)

- The Entra-side trust: a `fido2AuthenticationMethodConfiguration`
  policy controlling who can register, which AAGUIDs are accepted,
  and whether attestation is enforced.
- Conditional Access enforcing Authentication Strength.

### What's new

- The credential itself — physical token, cloud-synced passkey, WHfB
  enrollment, or all of the above per user.
- Enrollment ceremony — first-time user registration at
  `aka.ms/mysecurityinfo`, typically bootstrapped by Temporary Access
  Pass.

---

## Supporting cast — TAP, Authentication Strengths, Conditional Access

Three Entra features that aren't credentials themselves but make the
migration possible.

### Temporary Access Pass (TAP)

A time-limited, single-use or reusable passcode that Entra issues for
**bootstrapping or recovery**. It is *not* a long-term credential — its
purpose is to get a user into a state where they can register a real
phishing-resistant credential.

Typical uses:

- **Day-one onboarding.** New hire arrives, has no PIV card yet and
  no FIDO2 key. Admin issues a TAP; user signs in once with the TAP;
  user registers a FIDO2 key during that session; TAP expires.
- **Card or key replacement.** User's PIV card is reissued; while
  waiting, a TAP keeps them productive without falling back to a
  password.
- **Recovery.** User loses their FIDO2 key. Admin issues a TAP after
  identity-proofing; user signs in and registers a replacement key.

TAP policy controls:
- Who can have a TAP (target groups).
- One-time-use vs reusable.
- Lifetime (minutes to days).
- Default duration.

### Authentication Strengths

A named bundle of acceptable methods that Conditional Access can
require. Built-in strengths:

| Strength                           | What it requires                                              |
|------------------------------------|---------------------------------------------------------------|
| Multi-factor authentication        | Any 2-of-N from a broad list (password+OTP, etc.)             |
| Passwordless MFA                   | FIDO2, WHfB, passkey, certificate-based                       |
| Phishing-resistant MFA             | FIDO2, WHfB, certificate-based (no SMS, no push)              |

Custom strengths let you narrow further (e.g. "only FIDO2 keys from
allowed AAGUIDs").

### Conditional Access

The policy engine that decides "can this sign-in proceed, and under
what conditions?" Inputs include user, group, device, location, app
target, risk, and — relevant here — Authentication Strength. A typical
CBA migration uses Conditional Access to *require* phishing-resistant
strength for a pilot group, then expand the assignment as adoption
grows.

---

## Common misconceptions

> "Entra CBA replaces the PIV card."

No. CBA validates *certificates from the same PIV card you already
have*. The card stays; the path from card-to-Entra changes (direct
instead of via ADFS).

> "FIDO2 and WHfB are the same thing."

Related but distinct. WHfB is Microsoft's Windows-specific,
device-bound implementation of a FIDO2-style credential. FIDO2 is the
open standard. A user can have both — a hardware FIDO2 key for
cross-device use plus WHfB on their primary workstation.

> "Passkeys are FIDO2."

Passkeys *use* FIDO2/WebAuthn under the hood. The differentiator is
how the private key is custody-managed: hardware FIDO2 keys are
device-only; synced passkeys live in a cloud keychain. The security
properties differ, and the AAL3 story diverges.

> "Microsoft Authenticator push is phishing-resistant because it has number matching."

No. Number matching defeats *accidental* approvals (user blindly taps
"Approve"), but a sophisticated phishing site can still trick a user
into entering the displayed number on the real Entra prompt. Push +
number match is a hardening; it's not the same security tier as
WebAuthn-based methods. Microsoft classifies it under "MFA", not
"Phishing-resistant MFA".

> "Disabling federation means setting up CBA at the same time."

Order matters. Stand up CBA → migrate users → confirm sign-in success
→ *only then* defederate. Doing the opposite locks users out.

> "Conditional Access enforces FIDO2 by default if I enable it on the policy."

No. You enable FIDO2 in the *authentication methods policy* (who can
register). You enforce FIDO2 in *Conditional Access* by requiring an
Authentication Strength that names FIDO2. These are two separate
levers.

> "If I require phishing-resistant MFA, my admins can't sign in anymore."

Possible if you misconfigure scope. Always exempt your break-glass
accounts from the policy and verify they can sign in before you
enforce. Conditional Access policies should be deployed first in
report-only mode, then to a pilot group, then expanded.

> "Cloud Kerberos with WHfB replaces all of AD."

No. WHfB with cloud Kerberos lets a user authenticate to on-prem
resources without a domain controller in the sign-in path — but
the resources still live in AD, and AD is still the directory of
record for those resources. WHfB-with-cloud-Kerberos is a *path*
modernization, not a directory replacement.

> "ADFS can be turned off the day after we enable CBA."

No. Plan a *defederation* window (usually weeks to months) where:
1. CBA / FIDO2 / WHfB are enabled and tested.
2. Each domain is switched from Federated → Managed via
   `Set-MsolDomainAuthentication` or the modern equivalent.
3. ADFS is left running until you've confirmed no legacy app still
   depends on it (often a separate retirement project).

> "PIV's two certs — auth cert and signing cert — both work for CBA."

Subtlety. Entra CBA uses the PIV *authentication* cert (often EKU
1.3.6.1.5.5.7.3.2 — Client Authentication). The signing cert is for
email signing and is not what CBA evaluates.

---

## Decision tree — which credential for which user?

```
START — user authenticates today (PIV via ADFS, or password+MFA)

  ├─ Is the user enabled and a Member (not Guest)?
  │     ├─ No → out of scope for this track
  │     └─ Yes ↓
  │
  ├─ Will this user have a PIV card for the foreseeable future?
  │     │
  │     ├─ Yes — federal employee / contractor with PIV ───────►  ENTRA CBA  (Playbook 1/2)
  │     │   │                                                       primary phishing-resistant method
  │     │   │
  │     │   └─ Also add a backup phishing-resistant method:
  │     │       FIDO2 key OR WHfB OR device-bound passkey
  │     │       (avoid lockout if card is lost or revoked)
  │     │
  │     └─ No / unclear:
  │           │
  │           ├─ Primary device is a managed Windows machine ────►  WHfB  (Playbook 4)
  │           │
  │           ├─ Mobile-first / multi-device worker ─────────────►  PASSKEY (device-bound or hardware FIDO2)
  │           │                                                      (Playbook 3)
  │           │
  │           ├─ Kiosk / shared workstation ─────────────────────►  HARDWARE FIDO2 KEY
  │           │                                                      (Playbook 3)
  │           │
  │           └─ Short-term contractor / new hire (pre-card) ────►  TAP for onboarding
  │                                                                   → Passkey or FIDO2 long-term
  │                                                                   (Playbooks 5 + 3)
  │
  └─ For every user: register at least TWO phishing-resistant methods.
        One primary, one backup. Avoid single-credential lockout.
```

---

## Scope of this assessment

**In scope:**

- All `User` objects in the tenant where `userType = Member` and
  `accountEnabled = true`.
- Per-user authentication method registration state.
- Tenant-wide authentication methods policy (CBA, FIDO2, WHfB, TAP).
- Trusted certificate authorities uploaded to the tenant.
- Conditional Access policies that reference Authentication Strengths.
- Domain federation status (which domains are still federated).

**Out of scope (separate tracks or different concerns):**

- Workload credentials (client secrets, MI, WIF) → Track 1.
- Stale user accounts → Track 3.
- Guest users (handled by their home tenant, not yours).
- Service-account passwords (workload identities, not user identities).
- ADFS-side configuration audit (this is an Entra-side assessment).

---

## The inventory script — what it produces

[`scripts/Get-EntraAuthMethodInventory.ps1`](./scripts/Get-EntraAuthMethodInventory.ps1)
combines a tenant-config audit with a per-user registration enumeration
and emits the following timestamped artifacts:

| Output file               | Granularity                  | Use                                  |
|---------------------------|------------------------------|--------------------------------------|
| `tenant-config-<ts>.json` | One JSON document            | Tooling pipelines, diff over time    |
| `tenant-config-<ts>.txt`  | Human-readable summary       | Quick-read tenant posture            |
| `users-<ts>.csv`          | One row per user             | Pivot by disposition, by org unit    |
| `users-<ts>.json`         | Structured per-user records  | Programmatic processing              |
| `summary-<ts>.txt`        | Tenant-wide counts           | At-a-glance progress tracker         |

### Per-user schema

| Column                       | Meaning                                                                  |
|------------------------------|--------------------------------------------------------------------------|
| `Upn`                        | userPrincipalName                                                        |
| `ObjectId`                   | User object ID                                                           |
| `DisplayName`                | Friendly name                                                            |
| `UserType`                   | `Member` or `Guest`                                                      |
| `AccountEnabled`             | true/false                                                               |
| `IsAdmin`                    | True if user holds any directory role (heuristic — verify before action) |
| `IsMfaRegistered`            | At least one MFA method registered                                       |
| `IsMfaCapable`               | Could perform MFA (registered + enabled methods exist)                   |
| `IsPasswordlessCapable`      | At least one passwordless method registered                              |
| `DefaultMfaMethod`           | User's default MFA method                                                |
| `MethodsRegistered`          | Semicolon-delimited list (e.g. `fido2SecurityKey;windowsHelloForBusiness`) |
| `HasPhishingResistant`       | true if any registered method is phishing-resistant (CBA / FIDO2 / WHfB) |
| `HasCBA`                     | true if certificate-based auth is registered                             |
| `HasFido2`                   | true if a FIDO2 security key is registered                               |
| `HasWHfB`                    | true if Windows Hello for Business is registered                         |
| `HasPasskey`                 | true if Microsoft Authenticator passkey (passwordless) is registered     |
| `HasTAP`                     | true if a Temporary Access Pass is registered                            |
| `LastSignIn`                 | ISO 8601 (from `signInActivity.lastSignInDateTime`)                      |
| `LastSignInDays`             | Integer days since last sign-in                                          |
| `Disposition`                | Starting classification (see below)                                      |
| `DispositionReasons`         | Why this disposition was assigned                                        |

### Tenant-config JSON (top-level fields)

```json
{
  "tenantId":                "...",
  "generatedUtc":            "...",
  "domains":                 [ { "id": "...", "authenticationType": "Federated|Managed", "isVerified": true } ],
  "federatedDomainCount":    1,
  "managedDomainCount":      4,
  "certificateAuthorities":  [ { "isRootAuthority": true, "issuer": "...", "expires": "..." } ],
  "cbaConfiguration":        { "state": "enabled|disabled", "includeTargets": [...], "excludeTargets": [...] },
  "fido2Configuration":      { "state": "enabled|disabled", "isAttestationEnforced": true, "isSelfServiceRegistrationAllowed": true, "keyRestrictions": { ... } },
  "whfbConfiguration":       { "state": "enabled|disabled" },
  "tapConfiguration":        { "state": "enabled|disabled", "defaultLifetimeInMinutes": 60, "isUsableOnce": true },
  "passkeyConfiguration":    { "state": "enabled|disabled" },
  "authenticationStrengths": [ { "id": "...", "displayName": "...", "policyType": "builtIn|custom", "allowedCombinations": [...] } ],
  "conditionalAccessPolicies": [ { "id": "...", "displayName": "...", "state": "enabled|disabled|enabledForReportingButNotEnforced", "authenticationStrength": { ... }, "users": { ... }, "applications": { ... } } ]
}
```

---

## Sample output (illustrative)

A real tenant has thousands of user rows. Five illustrative rows showing
different dispositions:

`users-2026-05-21T15-00-00.csv` (selected columns):

```csv
Upn,UserType,AccountEnabled,HasPhishingResistant,HasCBA,HasFido2,HasWHfB,MethodsRegistered,LastSignInDays,Disposition
alice@agency.gov,Member,True,True,True,False,True,certificateBasedAuthentication;windowsHelloForBusiness;temporaryAccessPass,1,PHISHING_RESISTANT_READY
bob@agency.gov,Member,True,False,False,False,False,mobilePhone;softwareOneTimePasscode,3,MFA_NOT_PHISHING_RESISTANT
carol@agency.gov,Member,True,False,False,False,False,,12,PASSWORD_ONLY_HIGH_RISK
dave@agency.gov,Member,True,True,True,False,False,certificateBasedAuthentication,8,CBA_ONLY_ADD_BACKUP
eve@contractor.com,Guest,True,False,False,False,False,,4,GUEST_OUT_OF_SCOPE
```

Walkthrough:

- **alice** — PIV holder, has registered CBA, WHfB, and TAP. Primary
  phishing-resistant method (CBA), secondary phishing-resistant
  method (WHfB), recovery method (TAP). Best-case posture.
- **bob** — MFA registered but only weak forms (SMS, TOTP). Sign-in
  works, but if Conditional Access requires phishing-resistant
  strength, he's locked out. Playbook 3 (FIDO2) or Playbook 4 (WHfB)
  candidate.
- **carol** — No MFA at all. Highest risk; most exposed if her
  password leaks. Even pre-modernization, this should be remediated.
- **dave** — Has CBA registered but no backup. If his PIV card is
  lost or revoked, he's locked out. Add a FIDO2 or WHfB backup.
- **eve** — Guest user. Her authentication is governed by her home
  tenant (contractor.com), not this tenant. Out of scope.

`tenant-config-2026-05-21T15-00-00.txt`:

```text
Tenant authentication posture
Tenant:    11111111-2222-3333-4444-555555555555
Generated: 2026-05-21T15:00:00Z

Domains:
  Federated (ADFS / external IdP):       1
    agency.gov
  Managed (Entra-native):                4
    onmicrosoft.com, agency.onmicrosoft.com, ...

Certificate Authorities uploaded:        3
  CN=US DoD PIV CA-23, expires 2027-09-10
  CN=Federal Common Policy CA, expires 2028-05-15
  CN=Test CA (dev), expires 2026-12-31

Authentication method policies:
  certificateBasedAuthentication:        enabled (target: All users)
  fido2:                                 enabled (target: PIV-Backup-FIDO2 group; attestation enforced)
  windowsHelloForBusiness:               enabled (target: All users)
  temporaryAccessPass:                   enabled (1-time use, 60 min default)
  microsoftAuthenticator:                enabled (push + passwordless)
  sms:                                   enabled (legacy — flagged)
  voice:                                 disabled

Authentication strengths defined:        5
  Built-in: MFA, Passwordless MFA, Phishing-resistant MFA
  Custom:   "Agency CBA-only", "Agency FIDO2 hardware-only"

Conditional Access policies referencing auth strength: 12 / 47
  Enforcing Phishing-resistant for:
    - All admins (enabled)
    - Pilot group "PIV-CBA-Pilot" (enabled)
    - Tier-0 admin role assignments (enabled)
  Report-only:
    - All users (gradual rollout — not yet enforced)
  ... and 8 more.

Federation status:
  Domain 'agency.gov' is FEDERATED to ADFS at https://sts.agency.gov.
  Defederation pending — see Playbook 7.
```

`summary-2026-05-21T15-00-00.txt`:

```text
Entra ID authentication method inventory
Tenant:    11111111-2222-3333-4444-555555555555
Generated: 2026-05-21T15:00:00Z

Users total (Member, enabled):           12,847
Users with phishing-resistant method:    8,103   (63%)
Users with CBA registered:               5,891   (46%)
Users with FIDO2 registered:             3,447   (27%)
Users with WHfB registered:              4,228   (33%)
Users with only weak MFA:                3,012   (23%)
Users with no MFA registered:            1,732   (14%)

Disposition breakdown:
  PHISHING_RESISTANT_READY              8,103
  CBA_ONLY_ADD_BACKUP                     412
  MFA_NOT_PHISHING_RESISTANT            3,012
  PASSWORD_ONLY_HIGH_RISK               1,732
  DISABLED_ACCOUNT                        843
  GUEST_OUT_OF_SCOPE                    2,194
```

---

## How the script works (annotated walkthrough)

Skip this section if you don't intend to read the script.

### 1. Two-phase enumeration

The script runs in two phases:

1. **Tenant config phase** — pulls singletons (auth methods policy,
   CBA configuration, federated domains, CA policies, authentication
   strengths). Output: one JSON + one summary text.
2. **User enumeration phase** — paginates through user registration
   details and joins each with the user's last-sign-in activity.
   Output: per-user CSV + JSON.

Either phase can be skipped (`-SkipTenantConfig`, `-SkipUserEnum`) for
faster targeted runs.

### 2. `userRegistrationDetails` beats per-user enumeration

For a 10,000-user tenant, calling `Get-MgUserAuthenticationMethod` per
user makes 10,000 separate Graph requests — minutes of throttled wall
time. Instead the script hits
`/beta/reports/authenticationMethods/userRegistrationDetails` *once*,
which returns a paged collection of per-user method registration with
the fields that matter (`methodsRegistered`, `isMfaCapable`,
`isPasswordlessCapable`, `userType`). Two orders of magnitude faster.

### 3. Phishing-resistant classification

`userRegistrationDetails.isPasswordlessCapable` is close to what we
want, but it conflates "passwordless" with "phishing-resistant" —
Microsoft Authenticator push (number-match) is passwordless but is
not classified as phishing-resistant by Authentication Strength
policies.

The script defines an explicit set of phishing-resistant method
strings:

```powershell
$phishingResistantMethods = @(
    'fido2SecurityKey',
    'windowsHelloForBusiness',
    'microsoftAuthenticatorPasswordless',
    'x509CertificateSingleFactor',
    'x509CertificateMultiFactor',
    'passKeyDeviceBound',
    'passKeyDeviceBoundAuthenticator',
    'passKeyDeviceBoundWindowsHello',
    'platformCredential'
)
```

A user is `HasPhishingResistant = true` iff their `methodsRegistered`
contains at least one of these. The list is conservative — when
Microsoft adds new phishing-resistant method types, this list needs
to be updated.

### 4. Disposition cascade

Same pattern as Track 1 — a single mutually-exclusive starting hint,
cascade order matters:

1. `GUEST_OUT_OF_SCOPE` — `userType = Guest` short-circuits.
2. `DISABLED_ACCOUNT` — `accountEnabled = false` short-circuits.
3. `PASSWORD_ONLY_HIGH_RISK` — `isMfaRegistered = false`.
4. `MFA_NOT_PHISHING_RESISTANT` — has MFA but none phishing-resistant.
5. `CBA_ONLY_ADD_BACKUP` — has CBA but no backup phishing-resistant
   method.
6. `FIDO2_ONLY_ADD_BACKUP` — has FIDO2 but no backup.
7. `PHISHING_RESISTANT_READY` — has at least one phishing-resistant
   method *and* a viable backup.

### 5. Tenant-config singletons

Most of the tenant config lives at well-known singleton endpoints:

| Resource                                   | Endpoint                                                                          |
|--------------------------------------------|-----------------------------------------------------------------------------------|
| Authentication methods policy              | `/policies/authenticationMethodsPolicy`                                           |
| Certificate-based auth configuration       | `/policies/authenticationMethodsPolicy/authenticationMethodConfigurations/X509Certificate` |
| FIDO2 configuration                        | `/policies/authenticationMethodsPolicy/authenticationMethodConfigurations/Fido2`  |
| WHfB configuration                         | `/policies/authenticationMethodsPolicy/authenticationMethodConfigurations/WindowsHelloForBusiness` |
| TAP configuration                          | `/policies/authenticationMethodsPolicy/authenticationMethodConfigurations/TemporaryAccessPass`     |
| Trusted certificate authorities            | `/organization/{tenantId}/certificateBasedAuthConfiguration`                      |
| Authentication strengths                   | `/policies/authenticationStrengthPolicies`                                        |
| Conditional Access policies                | `/identity/conditionalAccess/policies`                                            |
| Domains and federation type                | `/domains`                                                                        |

The script pulls each into a single `tenantConfig` hashtable and
serializes to JSON. Diffing JSON between runs shows policy drift.

### 6. Sign-in activity for users

`/users` exposes a `signInActivity` property that includes
`lastSignInDateTime` and `lastNonInteractiveSignInDateTime`. The
script uses these to flag stale users — useful both for this track
(de-prioritize dormant accounts) and as a feeder for Track 3
(stale-account review).

### 7. Federation detection

The `/domains` endpoint reports each verified domain's
`authenticationType` as `Federated` or `Managed`. A `Federated`
domain means Entra delegates authentication to an external IdP
(typically ADFS). Defederation = switching `authenticationType` to
`Managed` after CBA / FIDO2 are in place.

---

## Disposition classification

| Disposition                       | Trigger                                                                      | Recommended next step                            |
|-----------------------------------|------------------------------------------------------------------------------|--------------------------------------------------|
| `PHISHING_RESISTANT_READY`        | At least one phishing-resistant method registered, plus a viable backup      | No action — verify CA assignment includes them   |
| `CBA_ONLY_ADD_BACKUP`             | CBA registered, no FIDO2 / WHfB / passkey backup                             | Playbook 3 or 4 — add a backup phishing-resistant method |
| `FIDO2_ONLY_ADD_BACKUP`           | FIDO2 registered, no second phishing-resistant method                        | Playbook 3 or 4 — add a backup                   |
| `MFA_NOT_PHISHING_RESISTANT`      | MFA registered but only weak methods (SMS, voice, push without passkey, TOTP)| Playbook 3 / 4 — migrate to FIDO2 or WHfB        |
| `PASSWORD_ONLY_HIGH_RISK`         | No MFA method registered                                                     | Playbook 5 (TAP) → 3 / 4 — onboard immediately   |
| `DISABLED_ACCOUNT`                | `accountEnabled = false`                                                     | Skip — Track 3 candidate                         |
| `GUEST_OUT_OF_SCOPE`              | `userType = Guest`                                                           | Out of scope — handled by home tenant            |

---

## Migration playbooks

### Playbook 1 — Entra CBA pilot

1. **Upload trusted issuer CAs.**
   ```powershell
   $cert = [Convert]::ToBase64String((Get-Content .\piv-issuer-ca.cer -AsByteStream))
   $body = @{
       certificateAuthorities = @(
           @{
               isRootAuthority           = $true
               certificate               = $cert
               crlDistributionPoint      = 'http://crl.agency.gov/piv-ca.crl'
               deltaCrlDistributionPoint = 'http://crl.agency.gov/piv-ca-delta.crl'
           }
       )
   }
   Invoke-MgGraphRequest -Method PATCH `
       -Uri "https://graph.microsoft.com/v1.0/organization/$tenantId/certificateBasedAuthConfiguration" `
       -Body ($body | ConvertTo-Json -Depth 10)
   ```
2. **Configure the X509Certificate authentication method.** Open
   Entra admin center → Protection → Authentication methods →
   Certificate-based authentication. Enable; target a pilot group
   (`PIV-CBA-Pilot`).
3. **Set user binding.** Define how a cert maps to a user — most
   commonly `PrincipalName` SAN mapped to `userPrincipalName`. Other
   options: RFC822 SAN → mail, Subject DN → onPremisesUserPrincipalName.
4. **Define authentication binding policy.** Specify which cert OIDs
   count as "multi-factor" auth (typically the PIV-Auth OID
   `2.16.840.1.101.3.2.1.3.13` and similar).
5. **Create a custom Authentication Strength.** Name it "PIV-CBA
   MFA" — allowed combinations: `x509CertificateMultiFactor` only.
6. **Create a Conditional Access policy.** Assignment: pilot group.
   Target: All cloud apps. Grant: require this auth strength.
   **Start in report-only mode.**
7. **Pilot.** Walk a small group through `aka.ms/mysecurityinfo` to
   verify their PIV cert is recognized. Use the sign-in logs and
   policy-report to confirm the CBA path works.
8. **Enable the CA policy** for the pilot group.

### Playbook 2 — Expand CBA tenant-wide

1. **Identify all PIV holders.** Heuristics: AD attribute populated
   with the PIV UUID, group membership, HR data.
2. **Expand the X509Certificate method policy target.** From pilot
   group → broader OU / division → All users.
3. **Expand the Conditional Access policy target.** Same gradient.
4. **Monitor sign-in success metrics.** KQL queries below.
5. **Plan for cert renewal gaps.** Use TAP (Playbook 5) for users
   whose cert renewal is in flight.

### Playbook 3 — Deploy FIDO2 security keys

1. **Enable FIDO2 in the authentication methods policy.** Target a
   pilot group; require attestation; restrict allowed AAGUIDs to your
   procured key models (this prevents users from registering arbitrary
   keys).
   ```powershell
   $body = @{
       state                    = 'enabled'
       isAttestationEnforced    = $true
       isSelfServiceRegistrationAllowed = $true
       keyRestrictions = @{
           isEnforced       = $true
           enforcementType  = 'allow'
           aaGuids          = @('<your-key-aaguid-1>', '<your-key-aaguid-2>')
       }
       includeTargets = @(@{ targetType = 'group'; id = '<pilot-group-id>' })
   }
   Invoke-MgGraphRequest -Method PATCH `
       -Uri "https://graph.microsoft.com/v1.0/policies/authenticationMethodsPolicy/authenticationMethodConfigurations/Fido2" `
       -Body ($body | ConvertTo-Json -Depth 10)
   ```
2. **Procure and distribute keys.** Each user needs a primary key and
   ideally a backup key stored offline.
3. **Bootstrap enrollment with TAP.** New / no-MFA users can't get to
   the registration page without an existing method. Issue them a
   TAP (Playbook 5) for a 1-time enrollment session.
4. **User registers the key.** At `aka.ms/mysecurityinfo`, the user
   adds a security key. WebAuthn ceremony asks them to touch / PIN.
5. **Validate with sign-in.** User signs out and back in using the
   key.
6. **Expand to broader population.**

### Playbook 4 — Enable Windows Hello for Business

1. **Choose a join model.** Entra-joined devices use cloud-only WHfB;
   Hybrid-joined devices use cert-trust or key-trust to authenticate
   against on-prem AD too.
2. **Configure WHfB via Intune.** Devices → Enrollment →
   Windows enrollment → Windows Hello for Business. Set minimum PIN
   length, allow biometrics, require TPM.
3. **(Optional) Enable cloud Kerberos trust** for hybrid scenarios so
   users can reach on-prem resources without a domain-joined
   credential cache.
4. **Provision.** Users go through the first-sign-in WHfB enrollment
   flow on their managed device.
5. **Validate.** Sign in to a fresh app with WHfB; confirm it
   satisfies Conditional Access auth-strength requirements.

### Playbook 5 — Configure Temporary Access Pass

1. **Enable TAP in the authentication methods policy.** Target who
   can have a TAP (typically a small admin group plus the helpdesk
   role).
2. **Set policy defaults.** Lifetime (15–60 min for one-time
   onboarding; up to 30 days for special cases), reusable vs
   single-use, default duration.
3. **Issue TAP for individual users.**
   ```powershell
   $tap = @{
       lifetimeInMinutes = 60
       isUsableOnce      = $true
   }
   New-MgUserAuthenticationTemporaryAccessPassMethod `
       -UserId <upn> -BodyParameter $tap
   ```
   Returned object contains the passcode (one-time visible).
4. **Communicate.** Hand the user the TAP through an out-of-band
   channel (in person, secure call, ITSM record). Never email.
5. **User signs in with the TAP** and registers their phishing-resistant
   method during that session.
6. **TAP expires** after first use (single-use) or lifetime window.

### Playbook 6 — Enforce phishing-resistant auth via Conditional Access

1. **Create / pick an Authentication Strength.** Built-in
   "Phishing-resistant MFA" works for most cases. For stricter
   requirements (CBA-only, FIDO2-hardware-only), create a custom
   strength.
2. **Create a Conditional Access policy.** Initial scope: admins and
   pilot group. Target: All cloud apps. Grant: require auth strength.
3. **Start in report-only mode.** Watch the sign-in logs for users
   who *would* have been blocked. Investigate each: are they failing
   because their phishing-resistant method isn't registered? Push
   them through Playbook 3 / 4 first.
4. **Move to "On".** Once report-only shows zero unexpected blocks
   for the pilot group, enforce.
5. **Expand.** Same gradient pattern as Playbook 2 — pilot →
   division → org-wide.

### Playbook 7 — Defederate (retire ADFS)

This is the highest-blast-radius step. Plan a maintenance window with
rollback procedure documented.

1. **Confirm all users in the domain can authenticate via Entra-native
   methods.** Run the inventory script; verify every member user has
   `HasPhishingResistant = true` OR `IsMfaRegistered = true`.
2. **Test individual user sign-ins on the new path.** Confirm CBA /
   FIDO2 / WHfB all work end-to-end without ADFS in the loop.
3. **Switch the domain from Federated to Managed.**
   ```powershell
   # Modern equivalent of the legacy Set-MsolDomainAuthentication.
   Update-MgDomain -DomainId agency.gov -AuthenticationType Managed
   ```
   *This is the cutover.* All sign-ins from this domain now hit Entra
   directly.
4. **Validate** at all user populations: admins, end-users,
   service-account look-alikes.
5. **Decommission ADFS** when ready — usually weeks later, after
   confidence builds and any lingering ADFS-relying-party apps are
   migrated.

### Playbook 8 — Carve-outs

There will be users or apps that genuinely can't move to
phishing-resistant auth yet:

- **Legacy app that doesn't support modern auth.** Don't try to
  protect it with auth-strength CA policy; either block legacy auth
  via separate CA policy, or migrate the app.
- **Service accounts using passwords.** Migrate to workload identity
  (Track 1) rather than trying to fit them into Track 2.
- **Users on unsupported platforms** (very old browsers, custom
  thin-client OSes). Exempt from phishing-resistant strength;
  monitor; plan client refresh.

Carve-outs follow the same pattern as Track 1 — tag, document,
rotate, monitor, re-evaluate.

---

## Validation — confirming phishing-resistant adoption

```kql
// % of sign-ins satisfying phishing-resistant strength
SigninLogs
| where TimeGenerated > ago(30d)
| where UserType == "Member"
| extend strength = tostring(AuthenticationStrengthEnforced.requirements)
| summarize Total = count(),
            PhishingResistant = countif(strength == "phishingResistantMfa")
| extend PhishingResistantPct = round(100.0 * PhishingResistant / Total, 1)
```

```kql
// Users still authenticating with password as primary factor
SigninLogs
| where TimeGenerated > ago(30d)
| extend authDetails = parse_json(tostring(AuthenticationDetails))
| extend methods = strcat_array(extract_all(@'"authenticationMethod":"([^"]+)"', tostring(authDetails)), ",")
| where methods has "Password"
| summarize Count = count(), LastSignIn = max(TimeGenerated) by UserPrincipalName
| order by Count desc
```

```kql
// Sign-ins where Conditional Access blocked due to missing auth strength
SigninLogs
| where TimeGenerated > ago(30d)
| where ConditionalAccessStatus == "failure"
| extend caPolicies = ConditionalAccessPolicies
| mv-expand policy = caPolicies
| where policy.result == "failure"
| where policy.authenticationStrength != ""
| project TimeGenerated, UserPrincipalName, AppDisplayName,
          PolicyName = policy.displayName, RequiredStrength = policy.authenticationStrength
```

These queries require Entra ID diagnostic settings forwarding sign-in
logs to a Log Analytics workspace. Without it, the data is only in
the Entra portal for 30 days and isn't queryable via KQL.

---

## Permissions required

For the inventory script (read-only):

| Scope                                | Type                | Purpose                                                          |
|--------------------------------------|---------------------|------------------------------------------------------------------|
| `User.Read.All`                      | Delegated or App    | Enumerate users                                                  |
| `UserAuthenticationMethod.Read.All`  | Delegated or App    | Read per-user method registration                                |
| `Policy.Read.All`                    | Delegated or App    | Authentication methods policy, CA policies, strengths            |
| `AuditLog.Read.All`                  | Delegated or App    | Sign-in activity per user                                        |
| `Reports.Read.All`                   | Delegated or App    | `userRegistrationDetails` (beta)                                 |
| `Directory.Read.All`                 | Delegated or App    | Domains, federation type                                         |
| `Organization.Read.All`              | Delegated or App    | Tenant-level certificate authority list                          |

For remediation (Playbooks 1–7), additionally:

| Scope                                          | Used by                                                |
|------------------------------------------------|--------------------------------------------------------|
| `Policy.ReadWrite.AuthenticationMethod`        | Modify authentication methods policy (CBA, FIDO2 etc.) |
| `Policy.ReadWrite.ConditionalAccess`           | Create / modify CA policies                            |
| `UserAuthenticationMethod.ReadWrite.All`       | Issue TAP; reset methods                               |
| `Organization.ReadWrite.All`                   | Upload trusted CA certificates                         |
| `Domain.ReadWrite.All`                         | Defederate domains                                     |

---

## Risks and edge cases

- **Lockout from misconfigured Conditional Access.** Always exempt a
  break-glass account, deploy in report-only first, and verify before
  enforcement. The break-glass account should have its own *very
  long*, vaulted password as a last resort.
- **Cert renewal gaps.** PIV certs expire; if the new cert isn't
  enrolled before the old one expires, the user is locked out. TAP
  bridges the gap.
- **Browser / platform support for WebAuthn.** Most evergreen browsers
  support FIDO2; some thin-client / kiosk OSes do not. Audit before
  enforcing.
- **AAGUID restrictions** can lock out keys you didn't anticipate.
  Maintain an allowlist of procured models.
- **Synced passkeys ≠ AAL3.** For federal AAL3 requirements, use
  hardware FIDO2 keys or device-bound passkeys, not iCloud/Google
  synced passkeys.
- **ADFS still serves legacy apps.** Don't shut down the ADFS hosts
  the moment you defederate a domain — many environments have
  on-prem SAML apps that still rely on ADFS as their IdP. Plan
  separate retirements.
- **Hybrid identity sync (Entra Connect / Cloud Sync) interactions.**
  Defederation doesn't automatically reset cloud-sync settings; verify
  PHS (Password Hash Sync) or PTA (Pass-through Auth) is configured
  if you need fallback for accounts that can't yet do phishing-resistant
  auth.
- **Conditional Access auth-strength evaluation has lag.** A user
  registering a new method may take a few minutes before CA policies
  re-evaluate. Plan testing windows accordingly.
- **Number-matching push is not phishing-resistant.** Microsoft
  Authenticator push *with* number matching defeats accidental approval
  but is not classified under "Phishing-resistant MFA". Don't claim
  it as the target — it's a stopgap.

---

## Further reading

Microsoft Learn:

- **Microsoft Entra certificate-based authentication overview** —
  `https://learn.microsoft.com/entra/identity/authentication/concept-certificate-based-authentication`
- **Configure Entra CBA step by step** —
  `https://learn.microsoft.com/entra/identity/authentication/how-to-certificate-based-authentication`
- **FIDO2 security keys in Microsoft Entra** —
  `https://learn.microsoft.com/entra/identity/authentication/concept-authentication-passwordless#fido2-security-keys`
- **Passkeys in Microsoft Authenticator** —
  `https://learn.microsoft.com/entra/identity/authentication/how-to-enable-authenticator-passkey`
- **Windows Hello for Business deployment overview** —
  `https://learn.microsoft.com/windows/security/identity-protection/hello-for-business/`
- **Authentication strengths** —
  `https://learn.microsoft.com/entra/identity/authentication/concept-authentication-strengths`
- **Conditional Access overview** —
  `https://learn.microsoft.com/entra/identity/conditional-access/overview`
- **Temporary Access Pass** —
  `https://learn.microsoft.com/entra/identity/authentication/howto-authentication-temporary-access-pass`
- **Migrate from ADFS to Entra ID** —
  `https://learn.microsoft.com/entra/identity/hybrid/connect/migrate-from-federation-to-cloud-authentication`
- **`userRegistrationDetails` Graph API** —
  `https://learn.microsoft.com/graph/api/resources/userregistrationdetails`

Standards and policy:

- **NIST SP 800-63B** — Digital Identity Guidelines (AAL definitions) —
  `https://pages.nist.gov/800-63-3/sp800-63b.html`
- **FIPS 201** — Personal Identity Verification (PIV) of Federal
  Employees and Contractors — `https://csrc.nist.gov/publications/detail/fips/201/3/final`
- **HSPD-12** — Policy for a Common Identification Standard for
  Federal Employees and Contractors (2004)
- **FIDO Alliance Specifications** — `https://fidoalliance.org/specifications/`
- **WebAuthn (W3C)** — `https://www.w3.org/TR/webauthn-3/`
- **OMB M-22-09** — Moving the U.S. Government Toward Zero Trust
  Cybersecurity Principles (mandates phishing-resistant MFA for
  federal agencies)

---

## Glossary

| Term                          | Meaning                                                                                                |
|-------------------------------|--------------------------------------------------------------------------------------------------------|
| **PIV**                       | Personal Identity Verification — federal smartcard standard per HSPD-12 / FIPS 201.                    |
| **PKINIT**                    | Public Key Cryptography for Initial Authentication in Kerberos — how smartcards authenticate to AD.    |
| **CBA**                       | Certificate-Based Authentication — generic term; here, specifically Entra's native CBA feature.        |
| **ADFS**                      | Active Directory Federation Services — on-prem identity federation server.                             |
| **Federated domain**          | An Entra domain whose authentication is delegated to an external IdP (usually ADFS).                   |
| **Managed domain**            | An Entra domain whose authentication is performed by Entra natively.                                    |
| **FIDO2**                     | Fast Identity Online v2 — open standard for phishing-resistant auth, combining CTAP and WebAuthn.      |
| **WebAuthn**                  | W3C standard component of FIDO2 — browser-to-authenticator API.                                        |
| **CTAP**                      | Client-to-Authenticator Protocol — the other half of FIDO2 (USB/NFC/BLE link).                         |
| **Passkey**                   | A FIDO2 credential. May be device-bound (TPM/Secure Enclave) or synced (cloud keychain).               |
| **WHfB**                      | Windows Hello for Business — Microsoft's device-bound credential implementation in Windows TPM.        |
| **TAP**                       | Temporary Access Pass — short-lived passcode for Entra onboarding or recovery.                          |
| **AAGUID**                    | Authenticator Attestation GUID — identifies the make/model of a FIDO2 authenticator.                   |
| **Authentication Strength**   | An Entra-named bundle of accepted auth methods (e.g. "Phishing-resistant MFA").                        |
| **Conditional Access**        | Entra's policy engine that grants/blocks based on signals (user, device, location, risk, strength).    |
| **AAL**                       | Authenticator Assurance Level — NIST 800-63B grades from AAL1 (weakest) to AAL3 (strongest).           |
| **rpId**                      | Relying Party Identifier — the WebAuthn binding that anchors a key to a specific domain origin.        |
| **Number matching**           | Authenticator-app feature requiring user to type a 2-digit number shown on the sign-in screen.         |
| **Phishing-resistant**        | Authentication method that cryptographically binds the credential to the legitimate origin (no replay).|
| **Cloud Kerberos trust**      | WHfB feature allowing on-prem AD resource access via Entra-issued Kerberos tickets.                    |
