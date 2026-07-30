# `x_fed_compliance` — Live Validation: Microsoft 365 Developer Tenant

**Date Code:** 2026-07-30 11:34 ET · **Scope:** FedRAMP Moderate / GCC Moderate ·
**Audience:** the implementer validating `ComplianceGate._checkWriteScope`
(SER-4) against a real Entra tenant for the first time

## 0. Why this exists, and what it does not prove

SER-4 was, until now, a deliberate gap: `_checkWriteScope` returned
`'unverified'` unconditionally in production, with a `TODO(per-tenant)` where
the Graph read belonged. The commit that closed it (see this repo's history
for the `ComplianceGate.js` change implementing the Graph read) added the
actual `appRoleAssignments` / `oauth2PermissionGrants` read, a name-shape match
against `*.ReadWrite.*` and other write-shaped Graph permission strings, and
two `test_mode` ATF specs (`atf/atf-scope-check-confirmed-readonly.xml`,
`atf/atf-scope-check-holds-write.xml`) that exercise the matching logic against
fixture data. That fixture pass is real coverage of the *matching logic* — it
is **not** proof the code correctly reads a real tenant's real
`appRoleAssignments` shape, correctly resolves an `appRoleId` GUID to its
permission string via the resource service principal's `appRoles` collection,
or correctly walks a real `oauth2PermissionGrants` response. A fixture cannot
be wrong about Graph's actual response shape in the way a live tenant can.

**What this validation round proves:** that `_checkWriteScope`, pointed at a
real Entra tenant through the same MID-routed `sys_rest_message` /
credential-alias wiring `ComplianceIngest` already uses, correctly returns
`'confirmed-readonly'` for a registration that genuinely holds only
read-shaped Graph grants, and `'holds-write'` for one that holds a
write-shaped grant — using two real app registrations with real, admin-consented
permissions, not stand-ins.

**What it does not prove:** that scope stays clean over time on any tenant
whose configuration is not otherwise locked down, or that a registration
cannot be reconfigured to add a write scope *between* two ComplianceGate runs
without this check catching it mid-window. See §5.

**What this tenant is not:** a FedRAMP-authorized boundary. It's a free
developer sandbox for validating that the code path itself works against real
Graph responses. Nothing here substitutes for standing up the production
tenant wiring, which still needs its own scope_check_enabled rollout plan,
its own credential-alias review, and its own decision about which resource
(s) count as "governed surfaces" for this tenant.

## 1. Get a tenant: the Microsoft 365 Developer Program

This step is yours to do — the instructions below describe what to click, not
something already done on your behalf.

1. Go to `developer.microsoft.com/microsoft-365/dev-program` (or search
   "Microsoft 365 Developer Program") and sign up. It's free, self-service,
   and requires only a Microsoft account.
2. Choose the **instant sandbox** option when prompted. This provisions a
   full Microsoft 365 tenant (a `*.onmicrosoft.com` domain) pre-loaded with an
   E5 developer subscription, test users, and sample data — no credit card,
   no purchase.
3. You'll land in the Microsoft 365 admin center for your new tenant, plus
   access to the Entra admin center (`entra.microsoft.com`) for the same
   tenant. Note the tenant ID (Entra ID > Overview) — you'll need it for the
   REST message endpoint / credential alias configuration in §3.
4. The dev tenant has an inactivity reclamation policy (currently ~90 days of
   no sign-in) — sign in periodically if you're spacing this work out, the
   same caution `CURRENT-STATE-PDI-VALIDATION.md` gives for a ServiceNow PDI
   hibernating.

## 2. Register two test app registrations

You need two, so both verdicts get exercised against a real tenant's real
`appRoleAssignments`, not just one path proven and the other taken on faith.

### 2a. The read-only registration (expect `'confirmed-readonly'`)

1. Entra admin center → **App registrations** → **New registration**. Name it
   something unambiguous, e.g. `x-fed-compliance-scope-test-readonly`.
   Single-tenant is fine for this test.
2. **API permissions** → **Add a permission** → **Microsoft Graph** →
   **Application permissions** (not Delegated — `ComplianceIngest` and the
   scope check both care about the app-only grant a service identity holds,
   not a signed-in user's delegated rights). Add:
   - `Directory.Read.All`
   - `Policy.Read.All`
   - `SecurityEvents.Read.All`

   These are the exact three the app's own `rest/README.md` documents as the
   intended production grant set (`Policy.Read.All, Directory.Read.All,
   SecurityEvents.Read.All`).
3. **Grant admin consent** for the tenant — as the dev-tenant Global Admin
   (your own account), click **Grant admin consent for <tenant>** on the API
   permissions page. Without this, the permissions show as "not granted" and
   won't appear in `appRoleAssignments` at all, which would make the read
   look empty rather than read-only — a different thing.
4. **Certificates & secrets** → create a client secret (or certificate, if
   your credential-alias setup in §3 uses one) — needed for the REST message
   credential, not for this app's own logic.
5. Under **Overview**, note the **Application (client) ID**. Then go to
   **Enterprise applications** (this is where the app's *service principal*
   lives, not the app registration itself), find the same app by name, and
   note its **Object ID** — this is the `service_principal_id` value
   `_checkWriteScope` actually queries against (`/servicePrincipals/{id}/...`),
   distinct from the application object ID and the client ID. Confusing these
   three IDs is the single most common setup mistake here.

### 2b. The write-scoped registration (expect `'holds-write'`)

1. Repeat the same steps under a second registration, e.g.
   `x-fed-compliance-scope-test-writescoped`.
2. Grant **Application permissions**: `Directory.Read.All`, `Policy.Read.All`
   (kept, so the fixture isn't *only* about the one flagged grant), plus
   **`Directory.ReadWrite.All`** — the canonical write-shaped Graph
   permission, and the one named explicitly in `ComplianceGate.js`'s own
   comments as the thing this check exists to catch.
3. **Grant admin consent** the same way as 2a.
4. Note this registration's service principal **Object ID** the same way.

You now have two real, admin-consented registrations: one that should read
back as clean, one that should trip the write-shaped match.

## 3. Wire the instance

Do this in a ServiceNow PDI or sub-prod instance where you've already built
`x_fed_compliance` per `update-set/README.md` (Script Includes imported, the
`x_fed_compliance.graph` REST message created per `rest/README.md`). If you
haven't built it yet, do that first — this validation exercises the built
app, it doesn't build it for you.

1. **Credential alias** — point the `x_fed_compliance.graph` REST message's
   OAuth 2.0 credential (or Connection & Credential alias, depending on your
   platform version) at the dev tenant: tenant ID from §1, client ID +
   secret/certificate from whichever registration you're testing in a given
   run. Because `_checkWriteScope` only ever reads (`appRoleAssignments`,
   `oauth2PermissionGrants`), the credential itself needs no write scope of
   its own to exercise this test — but see the judgment call at the end of
   this section.
2. **MID Server** — either use an existing in-boundary MID (if this sub-prod
   instance has one reachable to the internet / to `graph.microsoft.com`) or,
   for this validation only, leave `x_fed_compliance.mid_server` unset so the
   call routes through the instance's own outbound connectivity. Note which
   you used — a MID-routed pass and a direct pass are both informative, but
   they're not the same test, and production is MID-routed only.
3. Set properties:
   - `x_fed_compliance.test_mode` = `false` (you are explicitly testing the
     production Graph-read path here, not the fixture path — leaving
     `test_mode` on would silently exercise `_checkWriteScopeFixture` instead
     and prove nothing about the live tenant).
   - `x_fed_compliance.scope_check_enabled` = `true`.
   - `x_fed_compliance.service_principal_id` = the **Enterprise
     application Object ID** from §2a (start with the read-only one).
4. Confirm `gate.preflight(...)`'s SoD checks are satisfied for whatever task
   record you use to trigger this — or, more directly, just call
   `_checkWriteScope()` on a `ComplianceGate` instance from a background
   script / scoped script include test, exactly as the two new ATF specs call
   it, since `preflight` is not itself under test here.

## 4. Run it against both registrations

1. With `service_principal_id` pointed at the **read-only** registration
   (§2a), invoke:
   ```javascript
   var gate = new x_fed_compliance.ComplianceGate();
   gs.info('verdict: ' + gate._checkWriteScope());
   ```
   **Expected:** `confirmed-readonly`. If you instead get `unverified`, check
   (in order): admin consent actually granted (§2a step 3), the credential
   alias actually authenticating (inspect the REST message's transaction log
   for a non-200), and that `service_principal_id` is the Enterprise
   Application object ID, not the Application (client) ID.
2. Re-point `service_principal_id` at the **write-scoped** registration
   (§2b) and re-run the same call. **Expected:** `holds-write`.
3. This is the actual "SER-4 validated against real infrastructure" proof:
   both verdicts produced by the real Graph read against real, admin-consented
   `appRoleAssignments` on a real tenant — not by the `test_mode` fixture
   path, which only proves the string-matching logic in isolation.
4. As a negative control, temporarily set `service_principal_id` to a random
   GUID that isn't a real service principal in the tenant. **Expected:**
   `unverified` (the `/servicePrincipals/{id}/appRoleAssignments` read
   returns a non-200, and `_graphGet` returns `null`, and `_checkWriteScope`
   treats that as an unresolvable read, not an empty/clean one). This
   specifically confirms the fail-closed contract from `ComplianceGate.js`'s
   own comments — an unreadable identity must never look the same as a
   verified-clean one.

## 5. What's still not covered even after this round

- **Scope drift between checks.** `_checkWriteScope` is a point-in-time read.
  Nothing here (or in `ComplianceGate` generally) re-checks continuously — if
  someone grants `Directory.ReadWrite.All` to the read-only registration's
  service principal an hour after a `'confirmed-readonly'` verdict, the next
  task's `preflight` will catch it on its own next call, but there is no
  standing monitor, alert, or drift-detection job watching the grant between
  gate invocations. A compliance program that runs `preflight` infrequently
  has a correspondingly wide blind window.
- **A compromised or reconfigured app registration between checks.** This
  check answers "does the identity hold write scope right now," not "has this
  identity's configuration, ownership, or credential been tampered with since
  the last check." An attacker (or an unrelated admin action) who adds a
  write-shaped grant and then removes it again between two `preflight` calls
  would produce two clean reads bracketing an unobserved write-capable window
  — this is a real gap, not addressed here, and would need something like a
  Graph audit-log-driven alert on `appRoleAssignments`/`oauth2PermissionGrants`
  changes to this specific service principal, which is future work.
- **The credential alias behind the REST message itself.** This validation
  confirms `_checkWriteScope`'s own read logic; it says nothing about whether
  the credential used to make that read is itself over-scoped, long-lived, or
  shared with another integration. `rest/README.md` documents the intended
  read-only grant for `ComplianceIngest`'s own credential, but nothing in this
  round independently re-verifies that credential's actual grant — arguably
  the same check ought to be run against the REST-message credential's own
  service principal too, not only against a purpose-built test registration.
- **Per-resource scoping of "write-shaped."** `_isWriteShaped` (in
  `ComplianceGate.js`) flags any `*.ReadWrite.*` / `*.Write.*` /
  `*.FullControl.*` / `*.Manage.*` grant on the identity, regardless of Graph
  resource — deliberately broader than "only over the surfaces this app
  governs" (see the judgment call in that method's own comment). Whether that
  breadth is correct for your tenant's actual risk model, versus scoping the
  check to just Directory/Policy/SecurityEvents-shaped permissions, is a
  decision worth revisiting once this is wired for real, not something this
  round settles.
- **`Directory.AccessAsUser.All`-shaped delegated permissions.** Name-shape
  matching does not catch delegated grants that carry no "Write" token but
  inherit the signed-in user's own rights (which could include write). This
  registration-test setup used application permissions throughout for
  exactly that reason; if your production integration ever adds a delegated
  flow, this gap needs its own follow-up.

## 6. Teardown

Nothing here is destructive outside the dev tenant itself.

- Entra admin center → **App registrations** → delete both test
  registrations (this also removes their service principals and any
  consented grants).
- Revert the sub-prod instance's properties (`test_mode`,
  `scope_check_enabled`, `service_principal_id`) to whatever your normal
  build/test baseline is, so a later, unrelated ATF run doesn't inherit a
  live-tenant credential alias by accident.
- The M365 Developer Program tenant itself can be kept (it's free and
  reusable for future validation rounds) or allowed to lapse — there's no
  cleanup action required against Microsoft's side beyond deleting the test
  registrations above.
