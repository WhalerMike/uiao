# Conditional Access Staged Rollout Playbook

**Audience:** Identity engineers, security policy owners, change advisory
board members, and project managers responsible for rolling out
Microsoft Entra ID Conditional Access policies in production
environments.

**Purpose:** This playbook describes a staged, low-risk approach to
deploying Conditional Access policies. It covers the sequencing of
policy introduction, the construction of break-glass exclusions to
prevent total lockout, the order in which different policy classes
should be introduced, and the rollback procedures for policies that
produce unexpected results in production.

**Scope:** Microsoft Entra ID Conditional Access. Azure role-based
access control, application-internal access controls, and other
non-Conditional-Access policy surfaces are out of scope.

**Why a staged rollout matters:** Conditional Access is the single
control plane between every user and every cloud resource. A
misconfigured policy can deny access to the entire organization within
seconds of being saved. A poorly-sequenced rollout can produce a cascade
of failed sign-ins that overwhelms helpdesk capacity before the
underlying cause is identified. The discipline of this playbook is
designed to make deployment safe rather than fast.

---

## 1. Pre-rollout preparation

Before any Conditional Access policy is deployed, three preconditions
must be in place.

**A documented set of break-glass accounts.** At least two cloud-only
administrator accounts must be created, kept entirely separate from the
day-to-day identity surface, and excluded from every Conditional Access
policy without exception. These accounts must use long, complex, non-
rotating credentials stored in a physically secure location. They must
have Global Administrator role assigned. Sign-in activity for these
accounts must be monitored continuously and alerted on; a sign-in from a
break-glass account is itself an incident.

**A staffed help line and a documented escalation path.** Before any
policy is enabled in enforce mode, the helpdesk must know how to
identify a Conditional Access-denied sign-in (the sign-in log shows the
policy and condition that matched), how to escalate to the identity
team for an exception, and how to verify the user's identity through an
out-of-band channel.

**An understanding of legacy authentication usage.** Microsoft Entra
sign-in logs include the client app and authentication protocol. Run a
report covering the past thirty days, filtered by legacy authentication
protocols (POP, IMAP, SMTP Basic, EWS, MAPI without modern auth), and
identify any user accounts or service accounts that depend on legacy
auth. These will need to be remediated by configuring the client for
modern auth, or explicitly exempted, before legacy auth is blocked.

---

## 2. Recommended policy sequence

Conditional Access policies should be introduced in the following order.
Each policy moves from report-only mode (logged but not enforced) to
enforce mode after a verification window during which sign-in logs are
reviewed for unexpected impact.

**Policy 1: Block legacy authentication.** Legacy authentication
protocols cannot be protected by multi-factor authentication, cannot be
challenged for risk, and are the predominant attack vector against
Microsoft Entra ID. This policy blocks all sign-ins using legacy clients
across all users and all applications, with break-glass accounts
excluded.

Construction: Users = All users. Cloud apps = All cloud apps. Conditions
= Client apps = Exchange ActiveSync clients + Other clients. Grant =
Block access. Exclusions = Break-glass accounts.

Report-only duration: fourteen days. Review sign-in logs filtered by
client application for any unexpected service-account or legacy-client
traffic. Remediate or exempt before enforcing.

**Policy 2: Require multi-factor authentication for all users.** Multi-
factor authentication is required for every interactive sign-in, with
documented exceptions only for break-glass accounts (and possibly for
sign-ins from trusted IP ranges, a deprecating exception that should
not be used long-term).

Construction: Users = All users. Cloud apps = All cloud apps. Grant =
Require multi-factor authentication. Exclusions = Break-glass accounts.

Report-only duration: fourteen days minimum, longer if MFA enrollment
is not yet complete. Pre-requisite: MFA enrollment campaign with at
least 95% user coverage before enforce mode.

**Policy 3: Require compliant or hybrid-joined device for sensitive
applications.** Sensitive applications (Microsoft 365, the Azure portal,
corporate SharePoint, internal SaaS applications) require the sign-in
to originate from a device that is either Microsoft Intune-compliant or
hybrid Microsoft Entra-joined. This is the policy that operationalizes
the Intune-first device model.

Construction: Users = All users. Cloud apps = Sensitive application set
(target a subset first, then expand). Grant = Require device to be
marked as compliant OR Require hybrid Microsoft Entra joined device
(use the "Require one of the selected controls" mode). Exclusions =
Break-glass accounts.

Report-only duration: thirty days. The longer window reflects the fact
that some devices may not yet have completed enrollment. Review sign-in
logs for users who would have been denied; those users either need
device remediation or exception authorization.

**Policy 4: Block sign-ins from disallowed locations.** Sign-ins from
specific geographic regions where the organization has no employees
should be blocked, both as attack mitigation and to limit the sign-in
attack surface.

Construction: Users = All users. Cloud apps = All cloud apps. Conditions
= Locations = Disallowed countries (built as a Named Location). Grant =
Block access. Exclusions = Break-glass accounts + documented travel
exceptions.

Report-only duration: seven days. Review for any legitimate travelers
whose presence in the country is authorized but undocumented in the
exception list.

**Policy 5: Require MFA + compliant device for privileged accounts.**
Administrator accounts (Global Administrator, Privileged Role
Administrator, Security Administrator, etc.) require both multi-factor
authentication and a compliant device, with no exception for trusted
IP ranges.

Construction: Users = Members of Microsoft Entra administrative roles.
Cloud apps = All cloud apps. Grant = Require multi-factor authentication
AND Require device to be marked as compliant. Exclusions = Break-glass
accounts only.

Report-only duration: fourteen days. Pre-requisite: every administrator
must have a compliant device available before this policy enforces.

**Policy 6: Sign-in risk-based policies.** Microsoft Entra ID Protection
generates sign-in risk scores; high-risk sign-ins should be blocked and
medium-risk sign-ins should be challenged for additional authentication
and password change.

Construction: Users = All users. Cloud apps = All cloud apps. Conditions
= Sign-in risk = High. Grant = Block access. (Plus a second policy with
Conditions = Sign-in risk = Medium, Grant = Require MFA + Require
password change.) Exclusions = Break-glass accounts.

Report-only duration: thirty days. Review the rate of triggered
policies and tune thresholds.

---

## 3. Verification during report-only mode

While a policy is in report-only mode, the Microsoft Entra sign-in log
includes Conditional Access detail indicating which report-only policies
matched and what the outcome would have been if enforced. Daily
verification during the report-only window includes:

Filter sign-in logs by the report-only policy. Identify sign-ins that
would have been blocked or challenged. Investigate each unexpected
match. Confirm break-glass accounts continue to show as excluded.
Confirm the policy has not silently fallen out of scope due to group
membership changes.

If the report-only window completes without unexpected impact, the
policy moves to enforce mode. If unexpected impact is identified, the
policy remains in report-only mode while the underlying issue is
resolved.

---

## 4. Enforce-mode transition

The transition from report-only mode to enforce mode is the highest-risk
moment in the rollout. It should be performed during business hours
when the identity team and helpdesk are fully staffed, after explicit
change advisory board approval, after confirmation that break-glass
accounts are working (test sign-in from a break-glass account within
the past twenty-four hours), and after a final sign-in log review
showing no unexpected report-only matches in the preceding twenty-four
hours.

Once enforced, monitor sign-in failures for the next four hours and the
next four business days. A sudden spike in Conditional Access-denied
sign-ins requires investigation; a sustained low rate of expected
denials is normal.

---

## 5. Rollback procedure

If a deployed policy produces unacceptable impact, rollback is performed
by setting the policy state to "Off" rather than by deleting the policy.
Disabling preserves the policy configuration for analysis and re-
enablement; deletion loses the configuration.

The rollback procedure:

Identify the affected policy from sign-in logs. In the Entra admin
center, navigate to *Protection > Conditional Access > Policies*, select
the policy, and change its state to Off. Save the change. Verify by
attempting an affected sign-in; it should now succeed. Document the
rollback in the change record, including the trigger, the affected user
population, the duration of impact, and the planned remediation before
re-enabling.

If a Conditional Access misconfiguration has locked all administrators
out of the tenant, sign in using a break-glass account, disable the
affected policy, and address the misconfiguration. The break-glass
account is the last line of defense; its existence is what makes
aggressive Conditional Access deployment safe.

---

## 6. Long-term maintenance

Once the staged rollout is complete, the Conditional Access policy set
should be reviewed quarterly. The review covers whether break-glass
accounts are still excluded from every enabled policy, whether any
exceptions are still in force that were intended as temporary, whether
any policies have fallen out of scope due to group restructuring,
whether sign-in patterns suggest the policy set is insufficient or
excessive, and whether new application or user populations have been
added without corresponding policy coverage.

Conditional Access is not a deploy-and-forget control. It is a living
control plane that requires ongoing maintenance.

---

## 7. Authoritative sources

- Microsoft Entra Conditional Access overview, Microsoft Learn.
  https://learn.microsoft.com/en-us/entra/identity/conditional-access/overview
- Manage emergency access accounts in Microsoft Entra ID, Microsoft
  Learn.
  https://learn.microsoft.com/en-us/entra/identity/role-based-access-control/security-emergency-access
- Conditional Access report-only mode, Microsoft Learn.
  https://learn.microsoft.com/en-us/entra/identity/conditional-access/concept-conditional-access-report-only
- Common Conditional Access policies, Microsoft Learn.
  https://learn.microsoft.com/en-us/entra/identity/conditional-access/concept-conditional-access-policy-common

*Verify URLs before distribution. Microsoft documentation is reorganized
frequently.*
