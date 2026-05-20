# Old AD vs New EntraID — A Foundational Reference

> A self-contained learning reference covering languages, protocols, cryptography, APIs, IaC, CI/CD, compliance description, and hybrid bridges across the on-premises Active Directory world and the cloud Microsoft Entra ID world. Aimed at architects, engineers, and assessors who need to hold both worlds in their head at once.

---

## 1. The shift in one paragraph

Microsoft identity moved from a **directory-and-tickets** world to a **token-and-API** world. In the old world, an on-premises Active Directory domain controller was the trust root: it issued Kerberos tickets, answered LDAP queries, and replicated SYSVOL over SMB. Clients spoke proprietary or directory-specific protocols (Kerberos, NTLM, LDAP, MS-RPC) directly against domain controllers; cryptography was MD4 / RC4 / SHA-1 with AES bolted on later; admins automated against COM objects and `ActiveDirectory` PowerShell cmdlets. In the new world, **Entra ID** is the trust root: it issues OAuth 2.0 access tokens and OpenID Connect ID tokens, exposes everything through the **Microsoft Graph** REST API, and federates with SaaS via SAML and OIDC. Cryptography is JWS signatures (RS256, ES256, ES384), TLS 1.2+, FIPS-validated HSM-backed keys, FIDO2 / WebAuthn for users, and certificate-based auth for privileged personnel. Admins automate against Graph SDKs in any modern language, and the operating environment around identity is **Infrastructure-as-Code** (Bicep, ARM, Terraform) plus **CI-as-Code** (YAML pipelines) plus **Compliance-as-Code** (OSCAL) — three layers that essentially did not exist around old AD.

The languages mostly carry over (PowerShell, Python, .NET stay relevant). The **protocols** change wholesale. The **cryptography** modernizes. And new layers stack on top.

[IMAGE-03: `old-ad-vs-new-entra-reference-image-03-trust-root-shift.png` A clean 16:9 conceptual side-by-side diagram contrasting the two identity paradigms. Left half titled "Old: Directory-and-Tickets" — a central on-prem Active Directory Domain Controller as the trust root, with outward arrows to: a Kerberos TGT/Service-Ticket flow, a domain-joined user workstation, and a file server. Right half titled "New: Token-and-API" — a central Microsoft Entra ID tenant as the trust root, with outward arrows to: OAuth 2.0 access tokens, OpenID Connect ID tokens, and a Microsoft Graph API endpoint. Center column comparison list — Trust root: "DC + KDC" → "Entra tenant"; Currency: "Tickets" → "JWT tokens"; Wire: "LDAP/Kerberos/SMB" → "HTTPS REST"; Policy: "GPO" → "Conditional Access"; Crypto: "MD4/RC4/SHA-1" → "ES256/ES384/HSM". Blue palette on the left half, purple palette on the right half. Clean technical sans-serif labels. No people, no logos.]

---

## 2. The world at a glance

| Dimension | "Old" Active Directory | "New" Entra ID |
|---|---|---|
| Trust root | On-prem AD domain controllers + KDC | Entra ID tenant (Microsoft-operated multi-tenant service) |
| Primary auth protocol | Kerberos v5; NTLM (legacy) | OAuth 2.0 + OpenID Connect |
| Directory wire protocol | LDAP / LDAPS | Microsoft Graph REST API over HTTPS |
| Federation | WS-Federation, WS-Trust, SAML 1.1/2.0 (via ADFS) | OIDC primary; SAML 2.0 supported; WS-Fed legacy |
| Multi-factor auth | Smartcard via ADCS; RSA SecurID add-ons | FIDO2/WebAuthn, Certificate-Based Auth, Authenticator app, OATH-TOTP |
| Password hash | NT hash (MD4) | PBKDF2-HMAC-SHA256, stored in HSM-backed boundary |
| Federation signatures | Kerberos AES-CTS-HMAC; SAML XML Signature (RSA + SHA-1/256) | JWS — RS256, PS256, ES256, ES384 |
| Session unit | Kerberos TGT + Service Tickets | JWT access tokens + ID tokens + refresh tokens |
| Wire confidentiality | Kerberos sign+seal; LDAPS over TLS | TLS 1.2/1.3; DPoP; mTLS-bound tokens |
| Policy plane | Group Policy Objects (GPO) | Conditional Access; Intune device policy; Authentication Methods Policy |
| Account lifecycle | AD Users & Computers; manual workflows | Entra ID Governance; Lifecycle Workflows; access reviews |
| Provisioning to apps | LDAP binds; custom connectors | SCIM 2.0 (outbound) |
| Audit pipeline | Windows Security Event Log; WEC; SIEM forwarding | Graph `auditLogs` / `signIns`; Microsoft Sentinel; Defender |
| Code-side identity SDK | ADSI, `System.DirectoryServices`, `python-ldap` | MSAL family + Microsoft Graph SDK family |
| Infrastructure-as-Code | (Essentially none native to AD) | Bicep, ARM templates, Terraform `azurerm`, Pulumi |
| CI-as-Code | (Essentially none) | YAML pipelines (GitHub Actions, Azure DevOps, GitLab) |
| Compliance authoring | Word + Excel SSP documents | OSCAL (Catalog, Profile, Component Definition, SSP, AP, AR, POA&M) |

[IMAGE-01: `old-ad-vs-new-entra-reference-image-01-old-ad-architecture-topology.png` A clean 16:9 technical schematic showing the on-premises Active Directory architecture topology. Center: an AD forest containing two domain trees (`corp.local` and `internal.corp.local`). Inside each domain: multiple Domain Controllers labeled "DC" connected by replication arrows; Organizational Units (OU) labeled "Users", "Computers", "Servers"; Group Policy Objects (GPO) linked to OUs with dotted arrows; a SYSVOL share replicated between DCs over SMB. Around the perimeter: end-user Windows workstations binding to a DC via Kerberos and LDAP. Lower right corner: a small ADCS Certificate Authority box. Lower left corner: a legend listing the protocols in play (LDAP, Kerberos, NTLM, MS-RPC, SMB). Blue and slate-gray color palette. Clean sans-serif labels. No people, no clip-art.]

[IMAGE-02: `old-ad-vs-new-entra-reference-image-02-entra-architecture-topology.png` A clean 16:9 technical schematic showing the Microsoft Entra ID cloud architecture topology. Center: a large rounded rectangle representing the Entra ID tenant. Inside the tenant rectangle: smaller labeled boxes for "Identity store" (users, groups, devices), "Authentication service" (issues tokens), "Token-signing HSM" (FIPS 140-2 Level 3), and "Conditional Access engine". Above the tenant: a single "Microsoft Graph API endpoint" (graph.microsoft.com) shown as the unified REST surface. Below the tenant: "Microsoft Defender" and "Microsoft Sentinel" as observability tiers. Around the perimeter: client applications — a web app, a mobile app, a daemon/service, and a single-page app — connecting via OAuth 2.0 and OIDC over HTTPS. Far right: SaaS apps connected via SCIM 2.0 outbound provisioning and SAML 2.0 federation. Purple and teal palette. Clean technical sans-serif labels. No people, no logos.]

---

## 3. Languages and where they fit

### 3.1 C++

| | Old AD | New Entra |
|---|---|---|
| Role | **The native server tier.** AD itself (`ntdsa.dll`, LSASS, SAMSRV) is C/C++. Client-side: Win32 ADSI (`activeds.dll`), the LDAP API (`wldap32.dll`), Kerberos SSPI through `secur32.dll`, NTLM through `msv1_0.dll`. Native admin tools, drivers, and the LSA all sit here. | **Minimal first-party app surface.** Windows Hello for Business uses C++ for TPM and WebAuthn paths. The Entra Connect sync engine has C++ components. Native Defender / endpoint agents. **Almost no greenfield cloud apps start in C++.** |
| Typical APIs | `IADs*` COM interfaces; `ldap_search_ext_s`; `AcquireCredentialsHandle` / `InitializeSecurityContext`; `LsaLookupSids`. | TPM API; WebAuthn API on Windows; native HTTP + JWT libraries when needed (no first-party MSAL C++ for general app use). |
| Code character | Pointer-heavy, COM-flavored, lots of `HRESULT`. | Sparse. Usually wraps higher-level HTTP + JOSE. |

### 3.2 Visual Basic family

| | Old AD | New Entra |
|---|---|---|
| Variants | VBScript (`cscript.exe` / `wscript.exe`), VBA (Office macros), VB6, VB.NET. | VBA still works against Microsoft Graph via OAuth token brokers; otherwise effectively retired. |
| Role | **Massive historical footprint.** ADSI from VBScript was the default AD admin language for ~15 years. Logon scripts via GPO ran VBScript. Office macros queried AD for org charts. | **No idiomatic "VB for Entra" pattern.** Anything VB-tier should call Graph from VBA using MSAL through a COM wrapper, or be replaced with PowerShell. |
| Example | `Set objUser = GetObject("LDAP://CN=jdoe,OU=Users,DC=corp,DC=local")` | (Rare — use PowerShell or C#) |

### 3.3 .NET

| | Old AD | New Entra |
|---|---|---|
| Era | .NET Framework 2.0+ | Modern .NET 6 / 7 / 8+ |
| Identity namespaces | `System.DirectoryServices` (ADSI bridge), `System.DirectoryServices.AccountManagement` (high-level user/group ops), `System.DirectoryServices.Protocols` (raw LDAP), `System.IdentityModel` (WS-Fed / WIF), `WindowsIdentity` (Kerberos / NTLM through SSPI). | **MSAL.NET** (`Microsoft.Identity.Client`), **Microsoft.Identity.Web** (ASP.NET Core integration), **Microsoft Graph SDK** (`Microsoft.Graph`), **Azure.Identity** (`DefaultAzureCredential`), JWT via `Microsoft.IdentityModel.Tokens`. |
| Old code shape | `var ctx = new PrincipalContext(ContextType.Domain); var user = UserPrincipal.FindByIdentity(ctx, "jdoe");` | |
| New code shape | | `var token = await app.AcquireTokenInteractive(scopes).ExecuteAsync(); var graph = new GraphServiceClient(new TokenCredential(...)); var user = await graph.Users["jdoe@contoso.com"].GetAsync();` |
| Why .NET stays dominant | Native to Windows. Big surface for both AD and Entra. | First-party Microsoft. Graph SDK is generated from the same OpenAPI spec the service speaks. |

### 3.4 Python

| | Old AD | New Entra |
|---|---|---|
| Old libraries | `pywin32` (`win32com.client` → ADSI), `python-ldap` (binds OpenLDAP + GSSAPI), `ldap3` (pure-Python LDAP + SASL), `gssapi` / `pykerberos`, `impacket` (offensive + forensic LDAP/Kerberos). | |
| New libraries | | **`msal`** (MSAL for Python), **`msgraph-sdk`** (`microsoft-graph` Python SDK), **`azure-identity`**, **`azure-sdk-for-python`** for ARM-side resources. |
| Old code shape | `import ldap3; conn = ldap3.Connection('ldap://dc01.corp.local', user='CORP\\svcacct', password='...', authentication='NTLM'); conn.search('OU=Users,DC=corp,DC=local', '(sAMAccountName=jdoe)', attributes=['mail','memberOf'])` | |
| New code shape | | `from azure.identity import InteractiveBrowserCredential; from msgraph import GraphServiceClient; client = GraphServiceClient(credentials=InteractiveBrowserCredential()); user = await client.users.by_user_id('jdoe@contoso.com').get()` |
| Why Python is growing | Already a major language for governance and automation; cloud SDKs are first-class. | |

### 3.5 PowerShell

| | Old AD | New Entra |
|---|---|---|
| Modules | `ActiveDirectory` (RSAT-installed), `GroupPolicy`, `ADCSAdministration`, raw `[ADSI]` and `[ADSISearcher]` accelerators, DSC for declarative config. | **`Microsoft.Graph`** PowerShell SDK (replaces EOL `AzureAD` and `MSOnline` modules), **`Az`** PowerShell (`Az.Accounts`, `Az.Resources`, `Az.KeyVault`, etc.), **`Microsoft365DSC`** for desired-state config across Microsoft 365. |
| Old code shape | `Get-ADUser jdoe -Properties memberOf, lastLogonDate` | |
| New code shape | | `Connect-MgGraph -Scopes "User.Read.All"; Get-MgUser -UserId jdoe@contoso.com -Property displayName,memberOf,signInActivity` |
| Reality on the ground | PowerShell stayed the **primary Microsoft admin language** through the transition. Same scripts, different modules. |

### 3.6 YAML

| | Old AD | New Entra |
|---|---|---|
| Role | **Edge use only.** Ansible playbooks targeting AD via `community.windows.win_domain_*` modules; some CI configs. No native YAML in AD itself. | **Native to the stack.** Azure DevOps Pipelines, GitHub Actions, Bicep parameter files, Azure Policy as Code, OPA/Rego configs, `Microsoft365DSC` configurations, Conditional Access as Code exports, Defender for Cloud recommendation exports. |
| Example | A playbook with `win_domain_user: name=jdoe state=present` tasks. | A GitHub Actions workflow file that deploys a Bicep template containing Entra app registrations. |

### 3.7 C# (.NET subset)

Effectively the same story as .NET above. Worth calling out because in cloud-side new development, **C# is the de facto first-party language** for Microsoft-stack apps targeting Entra. ASP.NET Core + `Microsoft.Identity.Web` is the canonical "secure a web API" path.

### 3.8 TypeScript and JavaScript

| | Old AD | New Entra |
|---|---|---|
| Role | Classic ASP / IIS web admin UIs. Rare. | **MSAL.js** (browser + Node), **`@microsoft/microsoft-graph-client`**, SPA apps using PKCE, Azure Functions Node runtime, web hooks consuming Graph change notifications. |
| Example (new) | `import { PublicClientApplication } from "@azure/msal-browser"; const msalInstance = new PublicClientApplication({ auth: { clientId, authority, redirectUri }}); await msalInstance.loginPopup({ scopes: ["User.Read"] });` |

### 3.9 Go, Java, Rust

| Language | Old AD | New Entra |
|---|---|---|
| Go | Some LDAP libraries (`go-ldap`); niche. | Growing: **`microsoftgraph/msgraph-sdk-go`**, **`Azure/azure-sdk-for-go`**, MSAL-Go (`github.com/AzureAD/microsoft-authentication-library-for-go`), Azure Functions Go runtime. |
| Java | **JNDI + LDAP**, GSS-API for Kerberos. Big in enterprise Java AD-integrated apps. | **MSAL4J**, **`microsoft-graph`** Java SDK, Spring Security + Entra (`spring-cloud-azure-starter-active-directory`). |
| Rust | Niche. | Emerging — `azure_identity` crate, MSAL via FFI; not yet first-tier. |

### 3.10 Other relevant tools

- **`kinit` / `klist` / `kdestroy`** — MIT Kerberos client utilities; both worlds use them, especially on Linux.
- **`ldapsearch`** (OpenLDAP) — still the universal LDAP probe.
- **`gpresult`** — Group Policy result inspector (old).
- **`dsregcmd /status`** — Entra device join state (new).
- **`msal-cli`** — useful for manual token acquisition during development.

---

## 4. Authentication and federation protocols

### 4.1 The old protocol stack

| Protocol | Spec | Role |
|---|---|---|
| **Kerberos v5** | RFC 4120 | Primary authentication in AD. Three-party protocol: client, KDC, service. Exchanges: AS-REQ/AS-REP (get TGT), TGS-REQ/TGS-REP (get service ticket). |
| **Kerberos FAST** | RFC 6113 | Pre-auth armoring. Protects against offline password attacks on AS-REQ. |
| **SPNEGO** | RFC 4178 | Negotiation wrapper that picks between Kerberos and NTLM at HTTP-auth time. |
| **NTLMv1 / NTLMv2** | Microsoft proprietary | Challenge-response fallback. NTLMv1 is broken; NTLMv2 is deprecated. Both lack zero-trust signals (no device, no risk). |
| **MS-PAC** | `[MS-PAC]` | Privilege Attribute Certificate embedded in Kerberos tickets. Carries group SIDs and claims. |
| **LDAP** | RFC 4511 | Directory query protocol. Bind operation authenticates; search returns directory objects. |
| **LDAPS** | de facto | LDAP over TLS on port 636. |
| **LDAP + SASL/GSSAPI** | RFC 4513 + RFC 4752 | Kerberos-bound LDAP — integrity and confidentiality via the GSS-API negotiated context. |
| **MS-RPC / DCE-RPC** | `[MS-RPCE]` | Most AD admin operations ride MS-RPC over named pipes or TCP. |
| **SMB 1/2/3** | `[MS-SMB]`, `[MS-SMB2]` | File access; also SYSVOL replication and NETLOGON. |
| **WS-Trust / WS-Federation** | OASIS | Federation protocols spoken by ADFS. WS-Trust is the RST/RSTR token-issuance dialog; WS-Federation is the passive (browser) profile. |
| **SAML 1.1 / SAML 2.0** | OASIS | XML-based assertions for federation. ADFS speaks SAML 2.0 as well. |
| **Group Policy Protocol** | `[MS-GPSO]`, `[MS-GPOL]` | LSDOU evaluation; LDAP retrieval of GPO containers; SMB fetch of policy templates from SYSVOL. |

[IMAGE-04: `old-ad-vs-new-entra-reference-image-04-kerberos-sign-in-flow.png` A clean 16:9 sequence diagram showing the Kerberos v5 authentication flow against Active Directory. Five vertical participant lanes left to right: "User", "Workstation", "Domain Controller (KDC)", "File Server (Service)". Numbered arrows top to bottom: (1) User logs in to Workstation; (2) Workstation sends AS-REQ to KDC (Authentication Server Request, includes pre-auth); (3) KDC returns AS-REP containing TGT (Ticket Granting Ticket) encrypted with user's long-term key; (4) Workstation later sends TGS-REQ to KDC requesting a service ticket for the file server, presenting the TGT; (5) KDC returns TGS-REP containing ST (Service Ticket) encrypted with the file server's machine-account key; (6) Workstation presents ST to File Server over SMB; (7) File Server validates ST signature, extracts PAC (Privilege Attribute Certificate) containing group SIDs, evaluates the share ACL, grants access. Each numbered step labeled with the protocol exchange name. Blue and slate-gray palette. Clean sans-serif. Dashed line separating the two ticket-acquisition phases (AS exchange and TGS exchange) from the service presentation.]

### 4.2 The new protocol stack

| Protocol | Spec | Role |
|---|---|---|
| **OAuth 2.0** | RFC 6749 | Authorization framework. Defines flows: authorization code, client credentials, device code, refresh token. Tokens are opaque from the framework's POV (Entra uses JWT). |
| **PKCE** | RFC 7636 | "Proof Key for Code Exchange." Required modifier on the authorization code flow for public clients (mobile, SPA, CLI). Prevents code-interception attacks. |
| **OpenID Connect Core 1.0** | OIDF | Identity layer on top of OAuth 2.0. Adds the ID token (JWT carrying user identity) + discovery (`/.well-known/openid-configuration`) + UserInfo endpoint. |
| **OIDC Discovery + JWKS** | OIDF | `jwks_uri` publishes the IdP's signing public keys. Verifiers fetch + cache. Entra rotates keys; clients re-fetch on `kid` miss. |
| **Device Authorization Grant** | RFC 8628 | "Device Code" flow. User authorizes on a second device with a short code. Right for input-constrained clients (TVs, CLI tools). |
| **Token Exchange** | RFC 8693 | Trade one token for another. Used in workload-identity federation and on-behalf-of flows. |
| **Refresh Token Rotation** | de facto | Each refresh issues a new refresh token; the old one is invalidated. Defends against refresh-token theft. |
| **DPoP** | RFC 9449 | "Demonstrating Proof of Possession." Client signs a per-request proof JWT with its private key; the access token is bound to that key. Stops bearer-token replay. |
| **mTLS-bound tokens** | RFC 8705 | TLS client cert thumbprint embedded as a `cnf` claim in the token. Same goal as DPoP via a different binding mechanism. |
| **JAR** | RFC 9101 | "JWT-Secured Authorization Request." Send the authorization request itself as a signed JWT instead of URL query parameters. |
| **OIDC Logout** | OIDF | `end_session_endpoint`, front-channel + back-channel logout protocols. |
| **FIDO2 / WebAuthn** | W3C WebAuthn + CTAP2 | Phishing-resistant authentication. Public/private key pair generated on an authenticator (TPM, security key, phone); browser calls `navigator.credentials.create()` / `.get()`. |
| **SAML 2.0** | OASIS | Still here. Entra is a full SAML IdP for SaaS that doesn't speak OIDC. Same XML signatures and assertions as the old world. |
| **WS-Federation** | OASIS | Legacy, supported, discouraged. |
| **SCIM 2.0** | RFC 7644 | "System for Cross-domain Identity Management." Entra provisions users/groups outbound into SaaS apps via SCIM. |
| **Microsoft Graph REST API** | Microsoft | HTTPS + OAuth bearer. The directory query and admin surface — `GET /users/{id}`, `POST /groups`, etc. |
| **Conditional Access** | Microsoft | Policy engine. Signals (user, device, location, app, risk) → decisions (allow, block, require MFA, require compliant device). Defined as policy objects via Graph. |
| **Continuous Access Evaluation (CAE)** | Microsoft + draft IETF | Server-push token revocation. When risk changes (user disabled, password changed, IP risk), Entra notifies resource servers — sessions terminate mid-flight rather than waiting for token expiry. |
| **Workload Identity Federation** | Microsoft | External IdP issues a token (e.g., GitHub Actions OIDC token); Entra trusts it and exchanges for an Entra access token. No client secret required. |

[IMAGE-05: `old-ad-vs-new-entra-reference-image-05-oauth-pkce-sign-in-flow.png` A clean 16:9 sequence diagram showing the OAuth 2.0 Authorization Code Flow with PKCE against Microsoft Entra ID. Four vertical participant lanes left to right: "User", "Browser", "Web App (Confidential Client)", "Entra ID Authorization Server (login.microsoftonline.com)". Numbered arrows top to bottom: (1) User clicks Sign In; (2) Web App generates random code_verifier and derives code_challenge = SHA256(code_verifier); (3) Web App redirects Browser to /authorize endpoint with response_type=code, client_id, redirect_uri, scope, state, nonce, code_challenge, code_challenge_method=S256; (4) User authenticates at Entra (Windows Hello / FIDO2 prompt); (5) Entra evaluates Conditional Access policies; (6) Entra redirects Browser back to Web App callback with authorization code + state; (7) Web App POSTs to /token endpoint with code + code_verifier + client_id + client_secret; (8) Entra verifies SHA256(code_verifier) matches the stored code_challenge, then returns ID token (JWT) + access token + refresh token; (9) Web App validates ID token signature against jwks_uri-published public keys and establishes session. Purple palette. Clean sans-serif. Mark PKCE-specific steps with a distinct accent color so the reader sees what PKCE adds vs plain auth-code flow.]

[IMAGE-06: `old-ad-vs-new-entra-reference-image-06-oauth-device-code-flow.png` A clean 16:9 sequence diagram showing the OAuth 2.0 Device Authorization Grant (RFC 8628). Four vertical participant lanes: "User", "Device (input-constrained client, e.g. CLI tool or TV app)", "Entra ID Device Authorization Endpoint", "Second Device (phone or laptop browser)". Numbered arrows: (1) Device requests a device_code and user_code by POSTing to /devicecode with client_id; (2) Entra returns device_code, user_code (short human-readable like ABC-XYZ), verification_uri (https://microsoft.com/devicelogin), expires_in, interval; (3) Device displays the verification_uri and user_code to the user; (4) User on Second Device opens the URL, enters the user_code, authenticates with MFA; (5) Device polls /token endpoint with device_code at the recommended interval; (6) Once user has authorized on Second Device, Entra responds to the next poll with access_token + refresh_token; before that, Entra returns authorization_pending. Mark the polling loop visually as a back-arrow with "poll every N seconds" annotation. Purple palette. Clean sans-serif.]

[IMAGE-07: `old-ad-vs-new-entra-reference-image-07-federation-triangle-saml-and-oidc.png` A clean 16:9 conceptual diagram showing the three-party federation triangle. Three nodes arranged as a triangle: top center — "User in Browser"; bottom left — "Identity Provider (IdP, e.g. Entra ID)"; bottom right — "Service Provider (SP, e.g. SaaS App)". Numbered arrows around the triangle: (1) User requests SP resource; (2) SP redirects User to IdP with an authentication request (AuthnRequest for SAML, /authorize for OIDC); (3) User authenticates at IdP; (4) IdP issues a signed assertion (SAML 2.0 XML assertion or OIDC ID token JWT) back to the Browser; (5) Browser POSTs assertion to SP's ACS endpoint (SAML) or returns to redirect_uri with code (OIDC); (6) SP validates assertion signature, establishes session. Two-column legend at the bottom comparing the protocol details — SAML 2.0 (XML, HTTP-POST binding, Subject + Attributes, XML Signature) vs OIDC (JSON Web Token, ID token, claims, JWS). Clean palette with the triangle shape clearly visible.]

[IMAGE-08: `old-ad-vs-new-entra-reference-image-08-fido2-webauthn-ceremony.png` A clean 16:9 two-phase sequence diagram showing the FIDO2 / WebAuthn ceremonies. Four vertical participant lanes: "User", "Browser (Relying Party Client)", "Web App (Relying Party Server)", "Authenticator (TPM or YubiKey or Phone)". Top half titled "Registration": (1) RP Server generates a random challenge; (2) RP Server sends PublicKeyCredentialCreationOptions to Browser; (3) Browser calls navigator.credentials.create(); (4) Authenticator prompts user (touch / PIN / biometric); (5) Authenticator generates a new public/private key pair specific to this RP, returns the public key plus an attestation object signed with the authenticator's attestation key; (6) RP Server verifies attestation, stores the public key bound to the user. Bottom half titled "Authentication": (7) RP Server generates a new challenge; (8) RP Server sends PublicKeyCredentialRequestOptions to Browser; (9) Browser calls navigator.credentials.get(); (10) Authenticator prompts user; (11) Authenticator signs the challenge with the previously-registered private key; (12) RP Server verifies the signature using the stored public key, establishes session. Annotate clearly: "Private key NEVER leaves the authenticator." Clean palette. Crisp distinction between the two phases.]

[IMAGE-09: `old-ad-vs-new-entra-reference-image-09-scim-outbound-provisioning.png` A clean 16:9 sequence diagram showing Microsoft Entra ID provisioning a user outbound to a SaaS app via SCIM 2.0 (RFC 7644). Three vertical participant lanes: "Entra ID Provisioning Service", "SCIM Connector / Endpoint", "Target SaaS Application". Numbered arrows: (1) HR system or admin adds user to Entra group "Salesforce Users"; (2) Entra Provisioning Service detects the scope-membership change during its sync interval; (3) Provisioning Service POSTs to the SaaS app's SCIM endpoint: POST /scim/v2/Users with a JSON body containing userName, name.givenName, name.familyName, emails, active=true, externalId; (4) SaaS app creates the user, returns 201 Created with the assigned internal ID; (5) Entra stores the mapping (Entra objectId ↔ SaaS app SCIM id); (6) Subsequent attribute changes flow as PATCH operations against /scim/v2/Users/{id} with JSON Patch syntax. Bottom strip: legend showing the core SCIM 2.0 endpoints (/Users, /Groups, /Schemas, /ServiceProviderConfig, /ResourceTypes). Purple palette. Clean sans-serif.]

### 4.3 Side-by-side: "How do I sign in?"

**Old AD path** (user, Windows workstation, internal file server):

```
1. User logs into Windows workstation.
2. Workstation winlogon → LSASS authenticates user via Kerberos AS-REQ to DC.
3. DC returns TGT (encrypted with user's long-term key derived from password hash).
4. User opens \\fileserver\share.
5. Workstation requests Service Ticket for cifs/fileserver via TGS-REQ.
6. DC returns ST encrypted with file server's machine account key.
7. Workstation presents ST to file server over SMB.
8. File server validates ST, extracts PAC (groups), evaluates ACL on the share.
9. Access granted.
```

**New Entra path** (user, Entra-joined laptop, cloud-native web app):

```
1. User signs into Windows with Windows Hello (FIDO2 against TPM).
2. Workstation receives Primary Refresh Token (PRT) from Entra ID.
3. User opens app in browser; app redirects to https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize
   with response_type=code, code_challenge (PKCE), scope, state, nonce.
4. Browser presents PRT-derived cookie; Entra evaluates Conditional Access; issues authorization code.
5. App backend exchanges code at /oauth2/v2.0/token using code_verifier; receives ID token + access token.
6. App validates ID token signature against Entra's published JWKS; extracts claims.
7. App calls Graph using access token: GET https://graph.microsoft.com/v1.0/me
8. Graph validates token, returns user object.
9. App authorizes user via OAuth scopes / app roles.
10. CAE subscription means if user is disabled mid-session, Entra pushes revocation.
```

The difference is not a UI thing. It's an **architectural** thing: in the old world, the workstation and file server share a trust root and Kerberos handles authentication. In the new world, every API call is a separate token presentation, the trust is signature-based not ticket-based, and the policy decision is made fresh on every authentication.

### 4.4 Risk-based authentication and Entra ID Protection

**Entra ID Protection** is the risk-assessment layer that sits behind Conditional Access. It produces structured risk signals that Conditional Access policies can consume as inputs — turning static rule-based policy into adaptive policy.

**Two risk surfaces:**

| Risk surface | What it scores | Examples of detectors |
|---|---|---|
| **User risk** | The likelihood that the **identity itself** is compromised — a state property of the user account, persisting across sign-ins until remediated. | Leaked credentials (Microsoft's dark-web telemetry matched against credential pairs), Microsoft Entra threat intelligence matches, anomalous account activity over time. |
| **Sign-in risk** | The likelihood that **this specific sign-in event** is not the legitimate user — a per-event property, evaluated at authentication time. | Atypical travel (impossible-velocity sign-ins from geographically distant locations), anonymous IP address (Tor / known anonymizers), unfamiliar sign-in properties (new IP / device / browser), malware-linked IP, password spray pattern, suspicious browser, primary refresh token replay. |

Both risks are computed by Microsoft's ML pipeline against signals from across the global tenant base (over a billion identities), and surfaced via the Graph endpoints `riskyUsers`, `riskDetections`, and `riskySignIns`. Each carries a risk level: `none` / `low` / `medium` / `high`.

**How Conditional Access consumes risk:**

- A policy can name **sign-in risk** as a condition: "If sign-in risk = high → grant only with MFA AND require password change."
- A policy can name **user risk** as a condition: "If user risk = high → block access entirely until administrator remediates."
- Risk policies typically chain to **self-service password reset (SSPR)** so that low-and-medium-risk events can self-remediate without admin intervention.

**Remediation paths:**

1. **Self-service** — user resets password via SSPR (requires SSPR to be enabled + the user to have registered authentication methods).
2. **Admin-driven** — admin dismisses or confirms the risk in the Entra portal; confirmation feeds back into the ML model as labeled data.
3. **Automatic** — Conditional Access policy remediates inline (force re-auth, force password change, force MFA).

**Telemetry destinations:** all risk events stream to Microsoft Sentinel (if connected), Defender XDR, and the Graph `auditLogs` and `signIns` endpoints. This is where SIEM-based incident response picks up the signal.

[IMAGE-11: `old-ad-vs-new-entra-reference-image-11-conditional-access-evaluation.png` A clean 16:9 decision-flow diagram for Microsoft Entra ID Conditional Access policy evaluation. Left side: a vertical column of input-signal boxes, each labeled — "User" (identity, group membership, role), "Device" (compliant, hybrid-joined, OS, compliance posture), "Location" (named locations, IP range, country, trusted network), "Application" (which app is being accessed, app type), "Sign-in risk" (Entra ID Protection low/medium/high), "User risk" (Entra ID Protection state). All arrows feed into the center. Center: a large rule-evaluation engine labeled "Conditional Access Policies" containing a stack of horizontal rule rows (just enough to convey "rules evaluated top-to-bottom"). Right side: three terminal decision-outcome boxes — "GRANT (with conditions: require MFA, require compliant device, require app protection policy, sign-in frequency)", "BLOCK", "REPORT-ONLY (log only, no enforcement)". Below the engine: a thin horizontal annotation "Re-evaluated on every authentication AND continuously via CAE". Purple palette. Clean technical sans-serif.]

[IMAGE-12: `old-ad-vs-new-entra-reference-image-12-continuous-access-evaluation.png` A clean 16:9 sequence diagram showing Continuous Access Evaluation (CAE) — the server-push token-revocation mechanism. Four vertical participant lanes: "User", "Resource App (e.g. Exchange Online, SharePoint Online)", "Microsoft Entra ID", "Admin / Risk Engine". Numbered arrows: (1) User authenticates to Entra and receives an access token with a longer lifetime (e.g. up to 28 hours, claim cae=true); (2) User accesses Resource App with the access token; (3) Time passes — token would normally be cached and re-presented for the remainder of its lifetime; (4) Admin disables the user account in Entra (OR the risk engine detects compromise OR the user changes password); (5) Entra publishes a revocation event on the CAE pub/sub channel; (6) Resource App receives the revocation event and updates its session state; (7) On the next API call from the user, Resource App rejects with HTTP 401 and a claims challenge ("WWW-Authenticate: Bearer error=insufficient_claims"); (8) Client receives challenge, attempts silent re-authentication; (9) Entra denies the re-auth attempt; user is signed out mid-session within seconds, not hours. Add a side callout: "Without CAE: session remains valid until token expires (potentially hours of delayed revocation)." Purple palette.]

---

## 5. Cryptography

### 5.1 Old AD crypto

| Primitive | Used for | Status today |
|---|---|---|
| **Kerberos enctype DES-CBC-CRC, DES-CBC-MD5** | Kerberos ticket encryption (legacy) | **Broken.** Banned in modern Windows. |
| **Kerberos enctype RC4-HMAC-MD5** | Kerberos ticket encryption (legacy Windows default through 2008R2) | Deprecated. Vulnerable to Kerberoasting if used for service accounts. |
| **AES128-CTS-HMAC-SHA1-96 / AES256-CTS-HMAC-SHA1-96** | Kerberos ticket encryption (modern default) | Current. AES256 preferred. |
| **AES256-CTS-HMAC-SHA384-192** | Kerberos ticket encryption (newer) | Supported in current Windows; preferred where available. |
| **NT hash** | Storage of user password (input to Kerberos key derivation and to NTLMv2) | `MD4(UTF-16LE(password))`. MD4 is cryptographically broken; hash is only as good as password entropy. |
| **LM hash** | Storage of password (legacy) | DES-based. Disabled in modern Windows. **Should not exist** in any current environment. |
| **NTLMv2 challenge-response** | NTLMv2 authentication | HMAC-MD5 over server challenge + client challenge + NT hash. Deprecated. |
| **DPAPI** | Local credential / secret protection on Windows | Per-user master key + AES + HMAC. Still in active use; not removed. |
| **TLS 1.0 / 1.1** | LDAPS, ADFS, ADCS web enrollment (old) | **Banned in current FIPS-tracked builds.** |
| **TLS 1.2** | LDAPS, ADFS, ADCS web enrollment | Current minimum. |
| **RSA-1024** | ADCS certificate keys (legacy) | **Below modern minimum.** Banned for new issuance. |
| **RSA-2048 / RSA-4096** | ADCS certificate keys | Current. |
| **ECDSA P-256 / P-384** | ADCS certificate keys (modern) | Current. |
| **SHA-1** | Certificate signatures (legacy), Kerberos PAC checksum (legacy), Authenticode (legacy) | **Deprecated** for signatures. Still appears in legacy estates. |
| **SHA-256 / SHA-384** | Certificate signatures, Authenticode | Current. |

### 5.2 New Entra crypto

| Primitive | Used for | Status |
|---|---|---|
| **RS256** (RSA-PKCS1-v1.5 + SHA-256) | JWT signing — default for Entra access tokens and ID tokens | Current default. Verifier fetches public key from `jwks_uri`. |
| **RS384, RS512** | JWT signing — higher-strength options | Available. |
| **PS256, PS384** (RSA-PSS) | JWT signing | Preferred over RS* in some federal profiles (PSS is provably secure under broader assumptions). |
| **ES256** (ECDSA P-256 + SHA-256) | JWT signing | Smaller signatures, faster verification. Common in FIDO2. |
| **ES384** (ECDSA P-384 + SHA-384) | JWT signing | Federal-personnel preferred algorithm class (matches Federal Common Policy CA G2). |
| **EdDSA Ed25519** | JWT signing | Emerging; not yet first-tier in Entra. |
| **HS256** (HMAC-SHA-256) | Symmetric JWT signing | Rare in Entra. Used in some client-credential-flow scenarios. |
| **RSA-OAEP / RSA-OAEP-256** | JWE key wrapping | Encrypted token payload (rare). |
| **ECDH-ES + A256GCM** | JWE — ECDH key agreement + AES-256-GCM | Encrypted tokens. |
| **AES-256-GCM** | At-rest encryption inside Microsoft data centers | FIPS 140-2 / FIPS 140-3 validated cryptographic modules. |
| **HSM-backed signing keys** | Entra ID's own token-signing private keys | Microsoft-managed FIPS 140-2 Level 3 HSMs. Auto-rotated. |
| **Key Vault HSM / Managed HSM** | Customer-managed signing and encryption keys | FIPS 140-2 Level 3. Non-exportable private keys. |
| **PBKDF2-HMAC-SHA256 (1000 iter) + per-user salt** | Cloud password hash (cloud-only accounts) | Entra's stated scheme. Sits behind an HSM boundary. |
| **PBKDF2-HMAC-SHA256 of NT hash** | Password Hash Sync from on-prem AD | Entra Connect hashes the NT hash with PBKDF2-SHA256 (1000 iter) + salt; encrypts in transit; the cloud-side stored value is the PBKDF2 output, never the NT hash itself. |
| **ECDSA P-256, RSA-PKCS1, EdDSA** | FIDO2 / WebAuthn authenticator keys | Authenticator-dependent. ECDSA P-256 is most common. |
| **CTAP2 attestation** | FIDO2 device attestation | `packed`, `tpm`, `u2f`, `apple`, `none`. Entra accepts certain attestation classes per Authentication Methods Policy. |
| **Cloud Kerberos Trust enctype: AES256-CTS-HMAC-SHA1-96** | Tickets issued by Entra for hybrid Kerberos | Preferred. Legacy enctypes are refused. |
| **Entra Certificate-Based Authentication (CBA)** | User authentication via X.509 cert | SAN binding to UPN; chains to a trusted CA registered with the tenant. PIV/CAC chains to Federal Common Policy CA G2. |
| **DPoP proof JWT** | Per-request proof signed by client's private key | Algorithm matches the public-key thumbprint that's bound to the access token. |
| **mTLS-bound tokens** | TLS client-cert SHA-256 thumbprint in `cnf` claim | Token usable only over a TLS connection with that client cert. |
| **Sigstore / cosign (Fulcio + Rekor)** | OSS-flavored signing of compliance artifacts | Optional, transparency-log-backed; emerging in the compliance space. |

### 5.3 The cryptographic delta in one paragraph

The old world's foundational hash was **MD4** (NT hash) — broken for decades; the old world's foundational symmetric was **RC4** (Kerberos, NTLMv2 paths) — also broken; signatures were SHA-1; key storage was the LSA secrets blob protected by DPAPI on the domain controller. The new world's foundational hash is **SHA-256 / SHA-384**, foundational signatures are **RS256 / ES384**, password hashing is **PBKDF2-HMAC-SHA256** sitting behind an **HSM boundary**, and the user authenticator is increasingly an **asymmetric key in TPM or FIDO2 hardware** rather than a hash of a password.

[IMAGE-14: `old-ad-vs-new-entra-reference-image-14-cryptographic-primitive-lineage.png` A clean 16:9 timeline / lineage diagram showing the evolution of cryptographic primitives across the Old AD → New Entra transition. X-axis: time from approximately 1995 to 2026. Three horizontal swim lanes stacked top to bottom. Top lane "Hashes": markers in chronological order for MD4 (labeled with NT hash use, marked broken in red), MD5 (marked broken), SHA-1 (marked deprecated in amber), SHA-256 (marked current in green), SHA-384 (marked current in green). Middle lane "Symmetric ciphers": DES (broken/red), 3DES (deprecated/amber), RC4 (deprecated/amber), AES-128-CBC (current/green), AES-256-CBC (current/green), AES-256-GCM (current/green). Bottom lane "Signature algorithms": RSA-PKCS1 + SHA-1 (deprecated/amber), RSA-PKCS1 + SHA-256 = RS256 (current/green), RSA-PSS = PS256/PS384 (current/green), ECDSA P-256 = ES256 (current/green), ECDSA P-384 = ES384 (current/green, marked "federal-preferred"), EdDSA Ed25519 (emerging/blue). On the far right of the timeline, a vertical column labeled "Where stored" with a downward arrow from "On-disk + DPAPI master key" (old) to "HSM, FIPS 140-2 Level 3, non-exportable" (new). Clean technical style. Color-code each primitive: red = broken, amber = deprecated, green = current, blue = emerging.]

---

## 6. Directory and identity APIs

### 6.1 Old: ADSI and LDAP

**ADSI (Active Directory Service Interfaces)** is a COM-based abstraction over LDAP that ships with every Windows install. It's accessible from C++, VB, VBScript, JScript, Perl, Python (via `pywin32`), and .NET (`System.DirectoryServices`).

```powershell
# PowerShell using ADSI accelerators
$user = [ADSI]"LDAP://CN=John Doe,OU=Users,DC=corp,DC=local"
$user.mail
$user.memberOf

# PowerShell using ActiveDirectory module (cleaner abstraction over the same protocol)
Get-ADUser -Identity jdoe -Properties mail, memberOf
```

```python
# Python ldap3
from ldap3 import Server, Connection, NTLM
conn = Connection(Server('dc01.corp.local'), user='CORP\\admin', password='...', authentication=NTLM, auto_bind=True)
conn.search('OU=Users,DC=corp,DC=local', '(sAMAccountName=jdoe)', attributes=['mail','memberOf'])
print(conn.entries)
```

### 6.2 New: Microsoft Graph

Microsoft Graph is a single REST API over HTTPS at `https://graph.microsoft.com`. It exposes Entra ID (users, groups, applications, directory roles, sign-ins), Microsoft 365 (Exchange, Teams, SharePoint, OneDrive), Intune, Defender, and more.

```powershell
# PowerShell Microsoft.Graph SDK
Connect-MgGraph -Scopes "User.Read.All","Group.Read.All"
Get-MgUser -UserId jdoe@contoso.com -Property displayName,mail,memberOf
Get-MgUserMemberOf -UserId jdoe@contoso.com
```

```python
# Python msgraph-sdk
from azure.identity import InteractiveBrowserCredential
from msgraph import GraphServiceClient
client = GraphServiceClient(credentials=InteractiveBrowserCredential(), scopes=["User.Read.All"])
user = await client.users.by_user_id("jdoe@contoso.com").get()
```

```csharp
// .NET Microsoft.Graph SDK
var credential = new InteractiveBrowserCredential();
var graph = new GraphServiceClient(credential);
var user = await graph.Users["jdoe@contoso.com"].GetAsync();
```

### 6.3 Why the API shift matters beyond syntax

The directory protocol delta is about **scope of authorization**:

- LDAP authorization is **all-or-nothing per bind**. A bound principal can search anything within its directory permissions. There's no "this app may only read mail addresses, not group memberships."
- Graph authorization is **scope-based per token**. A token issued with `User.Read.All` can read users; that same token cannot create users (`User.ReadWrite.All`) or read groups (`Group.Read.All`). Scopes are intersected with admin consent and Conditional Access at issuance.

This is what makes least-privilege actually expressible for cloud identity.

---

## 7. Infrastructure-as-Code and configuration languages

### 7.1 Old AD: barely any IaC

Old AD's configuration model was **imperative**: scripts ran against a domain to create users, set GPOs, install ADCS templates. Some declarative idioms existed:

- **DSC (Desired State Configuration)** — PowerShell-flavored declarative configuration; could enforce AD-related state with the `xActiveDirectory` resource module.
- **Group Policy itself** is declarative — but its serialization format (a tree of `.pol`, `.inf`, `.adm` / `.admx` files in SYSVOL) is not human-IaC-friendly.
- **`.reg` files, `secedit.exe`** — partial state expression.

There was no "Bicep for AD." Greenfield AD environments were stood up by scripts that imperatively created users, groups, OUs, GPOs, and certificate templates.

### 7.2 New Entra: a real IaC layer

| Tool | What it covers |
|---|---|
| **Bicep** | Microsoft's Azure Resource Manager DSL. Compiles to ARM JSON. Covers Azure subscriptions, resource groups, Key Vault, Log Analytics, storage, VMs, and increasingly **Entra ID via the preview Microsoft.Graph Bicep extension** (app registrations, service principals, group assignments). |
| **ARM templates (JSON)** | Bicep's predecessor and compile target. Still authoritative. |
| **Terraform with `azurerm` and `azuread` providers** | Cross-cloud-friendly IaC. `azuread` provider covers Entra ID resources. |
| **Pulumi** | Code-as-IaC in TS, Python, C#, Go. |
| **Microsoft365DSC** | PowerShell DSC dialect covering Microsoft 365 — Entra, Exchange, Teams, SharePoint, Intune, Defender. |
| **Azure Policy** | Compliance enforcement engine. Policies authored in JSON, often emitted from YAML or Bicep. |
| **Conditional Access as Code** | Export/import Conditional Access policy as JSON; manage in Git; deploy via Graph. |

### 7.3 A Bicep example: register a confidential client app in Entra

```bicep
extension microsoftGraph

resource app 'Microsoft.Graph/applications@v1.0' = {
  displayName: 'My Service'
  signInAudience: 'AzureADMyOrg'
  web: {
    redirectUris: ['https://app.contoso.com/signin-oidc']
  }
  requiredResourceAccess: [
    {
      resourceAppId: '00000003-0000-0000-c000-000000000000' // Microsoft Graph
      resourceAccess: [
        { id: 'df021288-bdef-4463-88db-98f22de89214', type: 'Role' } // User.Read.All (app)
      ]
    }
  ]
}
```

The exact resource type names and the Bicep `extension microsoftGraph` directive are still maturing; the point is that **declarative authoring of Entra resources is now a thing**, and it didn't exist for old AD.

---

## 8. CI / CD as code (YAML pipelines)

Same story as IaC: old AD had **no native CI/CD culture**. Deployments were "log into a jump host and run a script." The new world's expectation is:

- **GitHub Actions** (`.github/workflows/*.yml`) running on every PR — lint Bicep, validate Conditional Access JSON, run unit tests against MSAL flows in a test tenant.
- **Azure DevOps Pipelines** (`azure-pipelines.yml`) — same shape, hosted in Azure DevOps.
- **GitLab CI** (`.gitlab-ci.yml`) — same shape.

A typical YAML pipeline for Entra-affecting deployments:

```yaml
name: Deploy Entra app registration
on:
  push:
    branches: [main]
permissions:
  id-token: write   # OIDC token for Workload Identity Federation
  contents: read

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: azure/login@v2
        with:
          client-id: ${{ vars.AZURE_CLIENT_ID }}
          tenant-id: ${{ vars.AZURE_TENANT_ID }}
          subscription-id: ${{ vars.AZURE_SUBSCRIPTION_ID }}
      - run: az deployment sub create --location eastus2 \
               --template-file infra/main.bicep \
               --parameters env=prod
```

The OIDC `id-token: write` permission + `azure/login@v2` is the **Workload Identity Federation** flow in practice — the runner gets a short-lived OIDC token from GitHub, Entra trusts GitHub as a federated IdP, exchanges that for an Entra access token, and the deployment runs as a service principal. **No client secret ever lives in the repo.** This pattern is the cloud-side replacement for "service account password in a script."

[IMAGE-10: `old-ad-vs-new-entra-reference-image-10-workload-identity-federation-flow.png` A clean 16:9 sequence diagram showing Workload Identity Federation — a GitHub Actions workflow obtaining a Microsoft Entra ID access token without any client secret. Four vertical participant lanes: "GitHub Actions Runner", "GitHub OIDC Token Service", "Microsoft Entra ID Token Endpoint", "Azure Resource (e.g. Storage Account, Resource Group)". Numbered arrows: (1) Workflow requests an OIDC token from GitHub, having declared "permissions: id-token: write" in its YAML; (2) GitHub OIDC Service issues a short-lived JWT signed by GitHub's keys, with claims including repository (e.g. "repo:contoso/my-app:ref:refs/heads/main"), workflow, environment, sha; (3) Workflow POSTs this JWT to Entra at /oauth2/v2.0/token using client_assertion_type=urn:ietf:params:oauth:client-assertion-type:jwt-bearer; (4) Entra validates GitHub's signature against GitHub's published JWKS at https://token.actions.githubusercontent.com/.well-known/openid-configuration, verifies the issuer claim, verifies the federated credential trust configuration on the app registration matches the GitHub subject claim; (5) Entra returns an Entra access token bound to the app registration's service principal; (6) Workflow calls Azure Resource Manager / Microsoft Graph using the Entra access token. Bold red callout: "NO CLIENT SECRET — federation replaces stored credentials with cryptographic proof of the workflow's identity". Purple palette.]

---

## 9. Compliance description (OSCAL)

### 9.1 What OSCAL is

**OSCAL** — Open Security Controls Assessment Language — is NIST's family of schemas for expressing the entire compliance lifecycle as machine-readable JSON / YAML / XML documents instead of Word and Excel.

| OSCAL model | What it is |
|---|---|
| **Catalog** | A library of controls. E.g., NIST SP 800-53 Rev 5. |
| **Profile** | A tailored baseline that selects + modifies controls. E.g., FedRAMP Moderate. |
| **Component Definition** | How a specific product implements controls. E.g., "Microsoft Entra ID for FedRAMP High." |
| **System Security Plan (SSP)** | A system's controls + implementation statements + responsible roles. |
| **Assessment Plan (AP)** | What the assessor intends to evaluate. |
| **Assessment Results (AR)** | The findings from an assessment. |
| **POA&M** | Plan of Action & Milestones. Open findings tracked to remediation. |

Each model is published as equivalent JSON, YAML, and XML against a normative metaschema. The serializations are interconvertible.

[IMAGE-15: `old-ad-vs-new-entra-reference-image-15-oscal-model-relationships.png` A clean 16:9 entity-relationship diagram showing the seven OSCAL model documents and how they connect to each other. Seven labeled boxes arranged left-to-right and connected by directional arrows with relationship labels: (1) "Catalog" (e.g. NIST SP 800-53 Rev 5 — the source library of controls); arrow labeled "tailored by" to (2) "Profile" (e.g. FedRAMP Moderate baseline — selects + modifies controls); arrow labeled "implemented by" to (3) "Component Definition" (e.g. Microsoft Entra ID FedRAMP High component — how a product satisfies controls); arrow labeled "imported into" to (4) "System Security Plan (SSP)" (the system + its controls + implementation statements); arrow labeled "assessed per" to (5) "Assessment Plan (AP)" (what the assessor will evaluate); arrow labeled "produces" to (6) "Assessment Results (AR)" (the findings); arrow labeled "open findings tracked in" to (7) "POA&M" (Plan of Action & Milestones — remediation tracker). Each of the seven boxes uses a distinct accent color. Bottom strip: a small caption "All seven models are interconvertible JSON / YAML / XML against the normative OSCAL metaschema." Clean professional palette. Clean sans-serif.]

### 9.2 Old AD vs Entra in OSCAL terms

- **Old AD: no first-party OSCAL component definitions exist.** Agencies wrote OSCAL SSPs (or pre-OSCAL Word SSPs) that *mentioned* AD as the identity provider and described controls hand-authored against it. Evidence was screenshots, GPO exports, manual log reviews.
- **New Entra: Microsoft publishes OSCAL component definitions for Azure services**, including Entra ID, mapped against FedRAMP Rev 5 baselines. Microsoft Defender for Cloud's "Regulatory Compliance" view is the runtime side of this — it scores live tenant state against the same control set the OSCAL component definitions describe.

### 9.3 Toolchain

| Tool | Language | Role |
|---|---|---|
| **`compliance-trestle`** ([IBM](https://github.com/IBM/compliance-trestle)) | Python | The dominant Python OSCAL toolkit. Author / transform / validate. Round-trips OSCAL JSON ↔ markdown for human editing. |
| **`oscal-cli`** ([NIST](https://github.com/usnistgov/oscal-cli)) | Java | NIST's reference validator and converter (XML ↔ JSON ↔ YAML). |
| **`liboscal-java`** | Java | The underlying library `oscal-cli` is built on. |
| **`@easydynamics/oscal-react-library`** | TypeScript | Web viewers for OSCAL documents. |
| **`lula`** ([Defense Unicorns](https://github.com/defenseunicorns/lula)) | Go | Kubernetes-flavored OSCAL validation. |
| **FedRAMP automation** ([GSA](https://github.com/GSA/fedramp-automation)) | (multi) | FedRAMP profiles + SSP templates + validation rules. |

### 9.4 Quick `trestle` flow

```powershell
pip install compliance-trestle
mkdir my-ato-workspace; cd my-ato-workspace
trestle init
# Import NIST 800-53 Rev 5 catalog from a downloaded JSON file:
trestle import -f NIST_SP-800-53_rev5_catalog.json -o nist-800-53-rev5
# Import the FedRAMP Moderate profile:
trestle import -f FedRAMP_rev5_MODERATE-baseline_profile.json -o fedramp-rev5-moderate
# Generate per-control markdown for human authoring:
trestle author ssp-generate -n my-system -p fedramp-rev5-moderate -o ./markdown
# (Edit markdown for each control.)
# Re-assemble back into OSCAL JSON:
trestle author ssp-assemble -n my-system -m ./markdown
# Validate:
trestle validate -f system-security-plans/my-system/system-security-plan.json
```

Trestle does not fetch live evidence from Graph / Defender / Sentinel — that's the integration seam external tooling fills. Trestle is the authoring + validation toolchain; the **evidence pipeline is yours to build**.

---

## 10. Hybrid bridges (the things that exist during migration)

Migrating off old AD typically takes years, not weeks. The following components exist specifically to keep the lights on while the migration is in progress:

| Bridge | What it does |
|---|---|
| **Entra Connect Sync** (formerly AAD Connect) | Server-based sync from on-prem AD to Entra ID. Filtered attribute mapping; one-way (with optional writeback for specific objects); SQL Server backend. |
| **Entra Connect Cloud Sync** | Lightweight agent-based alternative to Connect Sync. Better for multi-forest or filtered scopes. |
| **Password Hash Sync (PHS)** | Optional Connect feature: hashes the NT hash with PBKDF2-HMAC-SHA256 + per-user salt, syncs the result to Entra. Allows users to authenticate to Entra with their on-prem password even if on-prem AD is unreachable. |
| **Pass-Through Authentication (PTA)** | Alternative to PHS. Entra forwards the user's password to an on-prem PTA agent which validates against AD. No hash leaves on-prem. |
| **Seamless SSO** | When the user is already on a domain-joined endpoint, Entra issues a Kerberos challenge against `aadg.windows.net.nsatc.net`; the workstation's Kerberos client responds; Entra accepts the silent SSO. |
| **Cloud Kerberos Trust** | Entra issues Kerberos TGTs against a synthetic computer object in on-prem AD. Lets Entra-joined (not domain-joined) devices acquire Kerberos tickets for legacy on-prem resources (file shares, print queues). |
| **Entra App Proxy** | Cloud-side reverse proxy that fronts on-prem web applications. Users authenticate to Entra; the proxy forwards the request to the on-prem app with the appropriate identity context (Kerberos Constrained Delegation or header injection). |
| **Entra Domain Services** | Managed AD-compatible LDAP service in Azure. For apps that absolutely cannot stop binding to a domain controller and cannot be modernized. |
| **ADFS** | Legacy federation server. Being retired in favor of cloud-native Entra federation. Still exists in some environments. |
| **Kerberos to OAuth bridges** (KCD, KCD with constrained delegation, then cloud) | The chain of trust hops that lets a Kerberos-authenticated user reach an OAuth-protected resource. |

[IMAGE-13: `old-ad-vs-new-entra-reference-image-13-hybrid-identity-bridges.png` A clean 16:9 architecture diagram showing the bridge components between on-premises Active Directory (left half) and Microsoft Entra ID (right half). Left half: an on-prem AD environment with Domain Controllers, a couple of file servers, and a workstation. Right half: the Entra ID tenant cloud with Microsoft Graph and Conditional Access. Down the center: a vertical column of nine labeled bridge components, each drawn as a small box with arrows touching both the left (on-prem) and right (cloud) sides where applicable: (1) "Entra Connect Sync" — server with one-way attribute-sync arrow from AD to Entra; (2) "Password Hash Sync" — annotated "NT hash → PBKDF2-HMAC-SHA256 → cloud"; (3) "Pass-Through Authentication" — agent forwarding bind requests; (4) "Seamless SSO" — Kerberos challenge against aadg.windows.net.nsatc.net; (5) "Cloud Kerberos Trust" — Entra issues Kerberos TGTs back to legacy on-prem SMB resources; (6) "Entra Application Proxy" — reverse proxy fronting on-prem web apps with OAuth at the cloud edge; (7) "Entra Domain Services" — managed AD-compatible LDAP service in Azure; (8) "ADFS" — faded grey, labeled "legacy, retiring"; (9) "Kerberos-to-OAuth bridges (KCD)" — chain of constrained-delegation hops. Blue palette on left, purple palette on right, gray bridges in center. Clean technical sans-serif. No people, no logos.]

---

## 11. Identity lifecycle and governance

Cloud identity is not just sign-in. The identity has a full lifecycle — joiner, mover, leaver, re-verifier — and the cloud world treats lifecycle as a first-class governable surface, where AD treated it as administrative process around an inert directory object.

### 11.1 Lifecycle Workflows

**Lifecycle Workflows** is the Entra ID feature for **automating joiner/mover/leaver actions**. A workflow is a JSON document describing:

- **Trigger** — typically a date-relative trigger, e.g. "7 days before `employeeHireDate`" or "on the day of `employeeLeaveDateTime`."
- **Scope** — which users the workflow applies to, expressed as a Graph filter (e.g., `department eq 'Engineering' and userType eq 'Member'`).
- **Tasks** — an ordered list of actions. Built-in tasks include: enable user account, generate a Temporary Access Pass, send welcome email, add to groups, assign licenses, set manager, request user access package, disable account, remove from all groups, remove all licenses, delete user.
- **Custom tasks** — extend the built-in set via Azure Logic Apps (HTTPS callbacks triggered by Entra).

Example joiner workflow: "7 days before hire date, generate a Temporary Access Pass, email it to the new hire's personal address from HR records, pre-assign them to the `Engineering-All` group and the `M365-E5` license, set their manager from `manager` attribute."

Example leaver workflow: "On the day of departure, disable account, revoke all sessions, remove from all groups, hand off OneDrive content to manager, remove all licenses, schedule account deletion in 30 days."

### 11.2 Access Reviews

**Access Reviews** is the periodic-recertification feature. It answers "who still needs the access they have?"

- **Scope of review**: a group's membership, an app's user assignments, a privileged role's assignments, or an access-package assignment.
- **Reviewer types**: the user themselves (self-review), the user's manager, group owners, or a designated list of reviewers.
- **Cadence**: one-time, weekly, monthly, quarterly, semi-annually, annually.
- **Outcomes**: approve, deny, or no-decision (with a fallback policy: typically "deny" for inactive reviewers).
- **Decision aids**: Entra surfaces "user has signed in 0 times in the last 90 days" or "user has never used this app" recommendations.
- **Automatic apply**: when configured, denied reviews automatically remove the user from the group / app / role at close.

This is the cloud-native analog of "audit the AD security group memberships every quarter," but driven from a continuously evaluated state with built-in reviewer workflow and audit trail.

### 11.3 Entitlement Management

**Entitlement Management** packages multiple related access items together as **access packages**:

- An **access package** bundles groups, applications, SharePoint sites, and (optionally) other access packages into one request unit.
- A **catalog** scopes packages to a particular business unit or function.
- An **access-package policy** defines who can *request* the package, who *approves*, whether external (B2B) users can request, expiration rules, and review cadence.
- **Connected organizations** — vetted partner tenants whose users can request access packages directly, with automatic B2B guest provisioning.

This is the "self-service access portal" pattern, governed end-to-end: the user requests, the policy routes to approver, approval grants the bundle, expiration revokes, review re-confirms.

### 11.4 Privileged Identity Management (PIM)

**PIM** is the just-in-time elevation feature for privileged roles:

- **Eligible vs Active**: a user can be *eligible* for a role (e.g., Global Administrator) without holding it. To use the role, they *activate* it.
- **Activation requirements**: MFA, justification text, ticket number (optional), and (optionally) approval from a designated approver.
- **Activation duration**: typically capped (e.g., 8 hours max). Auto-expires.
- **Coverage**: Entra ID directory roles, Azure RBAC roles, Microsoft 365 roles, and group memberships.
- **Audit**: every eligibility change, activation, and approval is captured in Entra `auditLogs`.

This is the cloud-native analog of "give the admin a separate `-admin` account that they only log in to when needed," but with structured activation, time-bounding, and audit baked in.

### 11.5 Permissions Management (formerly CloudKnox)

**Permissions Management** is the **cross-cloud entitlement** product: it observes used vs granted permissions across Azure, AWS, and GCP, computes a **Permission Creep Index** per identity, and offers right-sizing recommendations. Important when an organization has identities spanning multiple clouds and wants to apply least-privilege uniformly.

### 11.6 Verified ID

**Microsoft Entra Verified ID** is Microsoft's implementation of **decentralized identity** based on the W3C Verifiable Credentials and Decentralized Identifiers specifications. The tenant issues credentials (e.g., "this person is an employee," "this person holds a specific clearance"), the holder stores them in a wallet app, and a verifier (any tenant, not just the issuer) can cryptographically verify the credential without contacting the issuer. The DID method underneath is `did:web` and historically `did:ion` (Sidetree on Bitcoin).

### 11.7 Why this matters at the architectural level

The old AD model treated the directory object as the canonical fact: "user exists, user is in group X, user has password Y." All lifecycle was administrative process *around* the object.

The new Entra model treats the **lifecycle and governance state** as canonical: a user has an eligibility *for* a role, not just an assignment; a group membership has a *review state* and a *recertification cadence*; access has an *expiration* and an *approval trail*. The directory object is still there — but it carries policy state with it.

This is why governance, not just identity, is the cloud-native model. The directory is the easy half. Lifecycle, access reviews, just-in-time elevation, and entitlement management are the half that determines whether the organization is actually running zero-trust or just claiming to.

---

## 12. End-to-end side by side — "Reset a user's password"

### Old AD

```powershell
# Admin runs from a domain-joined workstation with Domain Admin or Account Operator rights:
Import-Module ActiveDirectory
$NewPassword = ConvertTo-SecureString "..." -AsPlainText -Force
Set-ADAccountPassword -Identity jdoe -NewPassword $NewPassword -Reset
Unlock-ADAccount -Identity jdoe
Set-ADUser -Identity jdoe -ChangePasswordAtLogon $true
```

- **Wire**: LDAP modify operation, Kerberos-bound.
- **Authorization**: AD ACL on the user object — `User-Change-Password` or `User-Force-Change-Password` extended right.
- **Audit**: Security event log event 4724 on the DC that processed the change.
- **MFA?** Not unless the agency added a third-party PAM layer.

### New Entra

```powershell
Connect-MgGraph -Scopes "UserAuthenticationMethod.ReadWrite.All"
# Issue a temporary access pass (TAP) — phishing-resistant, time-bound, one-time-use credential:
$tap = @{
  isUsableOnce = $true
  lifetimeInMinutes = 60
}
New-MgUserAuthenticationTemporaryAccessPassMethod -UserId jdoe@contoso.com -BodyParameter $tap
```

- **Wire**: HTTPS POST to `https://graph.microsoft.com/v1.0/users/{id}/authentication/temporaryAccessPassMethods`, bearer-token authenticated.
- **Authorization**: Graph scope `UserAuthenticationMethod.ReadWrite.All` + an admin role (Authentication Administrator, etc.); Conditional Access policy on the admin themselves.
- **Audit**: Graph `auditLogs` entry; flows into Microsoft Sentinel if configured; entry is queryable for years.
- **MFA?** The admin's own session is gated by Conditional Access; Phishing-resistant MFA + privileged-access workstation policies typically required.

Same operational intent. Wildly different mechanism, governance model, and audit trail.

---

## 13. Glossary

| Term | Definition |
|---|---|
| **Access Package** | An Entitlement Management bundle of groups, apps, and sites granted as a single requestable unit. |
| **Access Review** | Periodic recertification of group / app / role assignments. |
| **AD DS** | Active Directory Domain Services. The on-prem service. |
| **ADCS** | Active Directory Certificate Services. On-prem CA. |
| **ADFS** | Active Directory Federation Services. On-prem SAML / WS-Fed IdP. |
| **ADSI** | Active Directory Service Interfaces. COM abstraction over LDAP. |
| **CBA** | Certificate-Based Authentication (in Entra). |
| **Claim** | A name/value statement carried in a token. |
| **Conditional Access** | Entra's policy engine. Signals + rules + decisions. |
| **CAE** | Continuous Access Evaluation. Push-based token revocation. |
| **DID** | Decentralized Identifier. The identity primitive Verified ID is built on. |
| **DPAPI** | Data Protection API. Windows local-secret protection. |
| **DPoP** | Demonstrating Proof of Possession. Token-binding mechanism. |
| **Eligible (PIM)** | A user who may activate a role but does not currently hold it. |
| **Entitlement Management** | Entra ID Governance feature for access-package self-service request and approval. |
| **Entra ID** | Microsoft's cloud identity service (formerly Azure Active Directory). |
| **Entra ID Protection** | Risk-scoring layer for users and sign-ins. Feeds Conditional Access. |
| **FIDO2** | W3C WebAuthn + CTAP2. Phishing-resistant authenticator standard. |
| **Graph** | Microsoft Graph. The unified REST API. |
| **GPO** | Group Policy Object. AD's policy plane. |
| **HSM** | Hardware Security Module. FIPS-validated boundary for keys. |
| **JCS** | JSON Canonicalization Scheme (RFC 8785). |
| **JWS / JWE / JWT** | JSON Web Signature / Encryption / Token. |
| **JWKS** | JSON Web Key Set. Public-key document at `jwks_uri`. |
| **KDC** | Key Distribution Center. The Kerberos service in a DC. |
| **Lifecycle Workflows** | Entra ID Governance feature for joiner/mover/leaver automation. |
| **MSAL** | Microsoft Authentication Library. The token-acquisition library family. |
| **NT hash** | `MD4(UTF-16LE(password))`. AD password storage. |
| **OIDC** | OpenID Connect. Identity layer on OAuth 2.0. |
| **OSCAL** | Open Security Controls Assessment Language. NIST compliance schemas. |
| **PAC** | Privilege Attribute Certificate. SIDs and claims inside a Kerberos ticket. |
| **Permissions Management** | Cross-cloud entitlement product (formerly CloudKnox). |
| **PHS** | Password Hash Sync. Entra Connect feature. |
| **PIM** | Privileged Identity Management. Just-in-time role elevation. |
| **PIV / CAC** | Personal Identity Verification / Common Access Card. US federal smartcards. |
| **PKCE** | Proof Key for Code Exchange (RFC 7636). |
| **PRT** | Primary Refresh Token. Entra device-level token from which app tokens are derived. |
| **PTA** | Pass-Through Authentication. Entra Connect feature. |
| **Risk (user / sign-in)** | Entra ID Protection risk scores at the identity or per-event level. |
| **SAML** | Security Assertion Markup Language. XML federation protocol. |
| **SCIM** | System for Cross-domain Identity Management (RFC 7644). |
| **SID** | Security Identifier. AD's principal identifier. |
| **SPN** | Service Principal Name. Kerberos identifier for a service. |
| **SSPI** | Security Support Provider Interface. Windows auth API. |
| **TAP** | Temporary Access Pass. One-time time-bound bootstrap credential. |
| **TGT / ST** | Ticket-Granting Ticket / Service Ticket. Kerberos. |
| **UPN** | User Principal Name. `user@domain` identifier. |
| **Verified ID** | Microsoft Entra's decentralized-identity / verifiable-credentials product. |
| **WIF** | Workload Identity Federation. External-IdP token → Entra token exchange. |
| **WS-Federation / WS-Trust** | OASIS federation protocols. ADFS dialect. |

---

## 14. References

### Specifications

- **Kerberos v5** — RFC 4120 ([ietf.org/rfc/rfc4120](https://datatracker.ietf.org/doc/html/rfc4120))
- **Kerberos FAST** — RFC 6113
- **SPNEGO** — RFC 4178
- **LDAP** — RFC 4511 (technical specification), RFC 4513 (SASL)
- **OAuth 2.0** — RFC 6749
- **PKCE** — RFC 7636
- **OAuth Device Authorization Grant** — RFC 8628
- **OAuth Token Exchange** — RFC 8693
- **mTLS Client Authentication and Certificate-Bound Access Tokens** — RFC 8705
- **DPoP** — RFC 9449
- **JWT** — RFC 7519; **JWS** — RFC 7515; **JWE** — RFC 7516; **JWK / JWKS** — RFC 7517
- **JWS Detached Payload Option** — RFC 7797
- **JSON Canonicalization Scheme (JCS)** — RFC 8785
- **OpenID Connect Core 1.0** — [openid.net/specs/openid-connect-core-1_0.html](https://openid.net/specs/openid-connect-core-1_0.html)
- **SCIM 2.0 Protocol** — RFC 7644; **SCIM 2.0 Core Schema** — RFC 7643
- **WebAuthn Level 2** — W3C Recommendation; **CTAP 2.1** — FIDO Alliance
- **SAML 2.0** — OASIS Standard
- **W3C Verifiable Credentials Data Model** — [w3.org/TR/vc-data-model/](https://www.w3.org/TR/vc-data-model/)
- **W3C Decentralized Identifiers (DIDs)** — [w3.org/TR/did-core/](https://www.w3.org/TR/did-core/)

### Microsoft documentation

- **Microsoft Graph reference** — `https://learn.microsoft.com/graph/`
- **MSAL Python** — `https://learn.microsoft.com/entra/msal/python/`
- **MSAL.NET** — `https://learn.microsoft.com/entra/msal/dotnet/`
- **MSAL.js** — `https://learn.microsoft.com/entra/msal/javascript/`
- **Microsoft.Graph PowerShell SDK** — `https://learn.microsoft.com/powershell/microsoftgraph/`
- **Az PowerShell** — `https://learn.microsoft.com/powershell/azure/`
- **Bicep** — `https://learn.microsoft.com/azure/azure-resource-manager/bicep/`
- **Conditional Access** — `https://learn.microsoft.com/entra/identity/conditional-access/`
- **Continuous Access Evaluation** — `https://learn.microsoft.com/entra/identity/conditional-access/concept-continuous-access-evaluation`
- **Workload Identity Federation** — `https://learn.microsoft.com/entra/workload-id/workload-identity-federation`
- **Entra ID Certificate-Based Authentication** — `https://learn.microsoft.com/entra/identity/authentication/concept-certificate-based-authentication`
- **Cloud Kerberos Trust** — `https://learn.microsoft.com/entra/identity/devices/concept-azure-ad-kerberos`
- **Entra ID Protection** — `https://learn.microsoft.com/entra/id-protection/`
- **Entra ID Governance — Lifecycle Workflows** — `https://learn.microsoft.com/entra/id-governance/lifecycle-workflows/`
- **Entra ID Governance — Access Reviews** — `https://learn.microsoft.com/entra/id-governance/access-reviews-overview`
- **Entra ID Governance — Entitlement Management** — `https://learn.microsoft.com/entra/id-governance/entitlement-management-overview`
- **Privileged Identity Management** — `https://learn.microsoft.com/entra/id-governance/privileged-identity-management/`
- **Microsoft Entra Permissions Management** — `https://learn.microsoft.com/entra/permissions-management/`
- **Microsoft Entra Verified ID** — `https://learn.microsoft.com/entra/verified-id/`

### NIST + FedRAMP

- **NIST SP 800-63-3 / -63B** — Digital Identity Guidelines
- **NIST SP 800-53 Rev 5** — Security and Privacy Controls
- **NIST OSCAL** — [pages.nist.gov/OSCAL/](https://pages.nist.gov/OSCAL/) and [github.com/usnistgov/OSCAL](https://github.com/usnistgov/OSCAL)
- **FedRAMP Automation** — [github.com/GSA/fedramp-automation](https://github.com/GSA/fedramp-automation)

### Tooling

- **compliance-trestle** — [github.com/IBM/compliance-trestle](https://github.com/IBM/compliance-trestle)
- **oscal-cli** — [github.com/usnistgov/oscal-cli](https://github.com/usnistgov/oscal-cli)
- **Sigstore / cosign** — [sigstore.dev](https://www.sigstore.dev/)

---

*End of foundational reference. A companion document layering on "how a governance substrate assists in this transformation" follows separately.*
