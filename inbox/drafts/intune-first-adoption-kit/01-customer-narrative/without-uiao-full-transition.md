# Phase IV — Full Transition: A Detailed Reference for Pure Microsoft Entra Join and Intune-First Onboarding

## Scope and definition

The full transition phase of Windows endpoint governance is defined by a clean cloud-native architecture in which net-new devices are provisioned directly to Microsoft Entra ID and Microsoft Intune from the moment they are powered on for the first time, without ever joining an on-premises Active Directory domain. A device in this phase has a single identity (a Microsoft Entra ID device object), a single management plane (Microsoft Intune), no relationship with on-premises directory infrastructure for the purposes of device authentication or configuration, and is governed entirely through cloud-delivered policy. The device emerges from its first boot already enrolled, already configured, already evaluated for compliance, already inside the appropriate Conditional Access scope, and ready for the user to begin work without intermediate provisioning steps.

This phase is the terminal state of the modernization journey for new hardware. Organizations entering this phase typically do so by changing their procurement and provisioning workflows for net-new devices rather than by migrating existing devices in place. Existing hybrid-joined devices (from Phase III) typically remain hybrid-joined until they are retired through hardware refresh, while new device acquisitions begin to land directly in Phase IV. The two populations coexist for the duration of a hardware refresh cycle (typically three to four years), with the Phase IV population growing and the Phase III population declining until the organization is entirely cloud-native.

The full transition phase is enabled by Microsoft technologies that have matured to operational parity with the on-premises equivalents they replace: Windows Autopilot for provisioning, Microsoft Entra ID for identity, Microsoft Intune for management, Conditional Access for policy enforcement, Cloud Kerberos Trust for on-premises resource reach-back, and Microsoft Defender for Endpoint for security. The maturity is recent enough that organizations adopting this phase before approximately 2022 encountered significant gaps that have since been closed; organizations adopting it from 2023 forward generally find the technology adequate for production use.

## Architecture overview

The full transition architecture is cloud-resident, with optional reach-back to on-premises resources where they remain in service.

```
                              MICROSOFT CLOUD
   +-----------------------------------------------------------+
   |                                                           |
   |               +-------------------------------+           |
   |               |    Microsoft Entra ID         |           |
   |               |  (Device identity, user       |           |
   |               |   identity, PRT issuance,     |           |
   |               |   authentication plane,       |           |
   |               |   token issuance)             |           |
   |               +---------------+---------------+           |
   |                               |                           |
   |               +---------------+---------------+           |
   |               |   Conditional Access          |           |
   |               |  (policy decision point;      |           |
   |               |   consumes device compliance, |           |
   |               |   user risk, sign-in risk,    |           |
   |               |   location, application)      |           |
   |               +---------------+---------------+           |
   |                               |                           |
   |     +-------------------------+--------------------+      |
   |     |                                              |      |
   |  +--+------------------+              +------------+----+ |
   |  |   Microsoft Intune  |  Compliance  |   Microsoft 365 | |
   |  |  (policy, apps,     +--Signal----->+   Azure, SaaS   | |
   |  |   compliance,       |              |   applications, | |
   |  |   baselines,        |              |   protected     | |
   |  |   Defender for      |              |   APIs)         | |
   |  |   Endpoint)         |              |                 | |
   |  +--+------------------+              +-----------------+ |
   |     |                                                     |
   |     | Autopilot provisioning                              |
   |     | + native MDM enrollment                             |
   |     |                                                     |
   |  +--+--------------------+                                |
   |  |  Entra-Joined,        |                                |
   |  |  Intune-Enrolled      |                                |
   |  |  Endpoint             |                                |
   |  |  (no AD computer      |                                |
   |  |   object, no GPO,     |                                |
   |  |   no imaging,         |                                |
   |  |   PRT bound to TPM)   |                                |
   |  +-----------------------+                                |
   |                                                           |
   +-----------------------------------------------------------+
                              |
                              |  Optional reach-back via
                              |  Microsoft Entra Kerberos
                              |  (Cloud Kerberos Trust)
                              v
        +----------------------------------------+
        |   ON-PREMISES (legacy reach-back)      |
        |   - Domain Controllers (resource forest)|
        |   - File servers / SMB shares          |
        |   - Legacy line-of-business apps       |
        +----------------------------------------+
```

The device's relationship with on-premises infrastructure is optional and limited. The device does not authenticate to a domain controller, does not retrieve Group Policy, and does not need network proximity to any on-premises asset for its own operation. If the user needs to access on-premises resources (file shares, line-of-business applications), Microsoft Entra Kerberos (Cloud Kerberos Trust) provides the reach-back; the user authenticates to Entra ID, receives a partial Kerberos ticket, and presents it to an on-premises domain controller to obtain service tickets for the resources required.

## Windows Autopilot provisioning

Windows Autopilot is the cloud-resident provisioning service that replaces traditional imaging for net-new Windows devices. The Autopilot service maintains a database of devices registered to each Microsoft Entra tenant, identified by hardware hash (a stable identifier derived from device hardware characteristics) and serial number. A device that is registered to a tenant, on its first connection to the internet, contacts the Autopilot service, identifies itself by hardware hash, receives its assigned deployment profile, and follows the profile's instructions through the out-of-box experience.

The deployment profile specifies the join type (Microsoft Entra Join for Phase IV; Microsoft Entra hybrid joined for hybrid scenarios that are out of scope for this document), the user-experience mode (user-driven, self-deploying, or pre-provisioned), the username hidden or shown, the language and region defaults, the privacy and licensing screens behavior, the device name template, and several other behaviors. Most organizations have a small number of deployment profiles (typically two to five) corresponding to different device classes or business units.

The Autopilot service is provisioned per-tenant; multiple tenants do not share Autopilot device records. Device registration occurs through several paths: direct purchase from Microsoft (which registers automatically into the customer's tenant), reseller registration through the Cloud Solution Provider API (the predominant path for indirect purchases), manual registration of hardware hashes through the Intune admin center, or programmatic registration through Microsoft Graph. The procurement-handoff workflow that produces correct registration on every order is the subject of a separate document in this kit.

The out-of-box experience for an Autopilot-registered device begins when the device is first powered on. After language and keyboard selection, the device connects to the network (Ethernet or Wi-Fi), contacts the Autopilot service, and retrieves its profile. The corporate-branded sign-in page appears, the user authenticates with their work credentials, the device joins Microsoft Entra ID, automatic Intune enrollment runs, and the Enrollment Status Page tracks the application of configuration profiles, security baselines, compliance policies, and required applications. When the Enrollment Status Page completes, the user reaches the desktop on a device that is fully governed.

The duration of the Autopilot experience varies. A self-deploying scenario with minimal apps can complete in fifteen to twenty minutes. A user-driven scenario with substantial app deployment can take forty-five minutes to an hour. The duration is largely determined by the application set required to be installed before the user reaches the desktop; reducing the "Block device use until apps are installed" set shortens the experience.

## Pure Microsoft Entra Join

Microsoft Entra Join is the act of joining a device to the cloud directory without any on-premises directory relationship. The join is performed during Autopilot or, less commonly, manually by a user signing in to a new device with their work credentials through Settings > Accounts > Access work or school. The result is a device object in Microsoft Entra ID with a unique device identifier, a registration certificate issued by the Microsoft Entra device registration service, and a Primary Refresh Token bound to the device's Trusted Platform Module.

The Primary Refresh Token (PRT) is the device-bound token that authorizes the user's interactive sign-ins to cloud applications on this specific device. The PRT is sealed to the TPM, which provides hardware-rooted protection against credential theft (an adversary who exfiltrates a copy of the PRT cannot use it on a different device because the unwrap requires the original TPM). The PRT is refreshed periodically and is invalidated when the user changes their password, when the device's TPM is cleared, or when the device is removed from the tenant.

Authentication of the user on a Microsoft Entra-joined device proceeds through the PRT for cloud applications. The user signs in to the device with their work credentials (or Windows Hello for Business, or a FIDO2 security key); the local security authority validates the credentials against the cached PRT (in the online case, also against Entra ID); the user reaches the desktop with a session that automatically receives tokens for cloud applications as needed, without further authentication prompts.

The user can sign in to a Microsoft Entra-joined device when the device is offline (using cached credentials from a prior successful online sign-in) and when the device is online (using fresh credential validation). Offline sign-in has been supported since the introduction of Microsoft Entra Join and is fully equivalent in user experience to offline sign-in on a domain-joined device.

## Microsoft Intune as the policy plane

Microsoft Intune is the sole device management plane in Phase IV. There is no Configuration Manager involvement, no Group Policy delivery, and no legacy management agent. The device's configuration, application set, compliance evaluation, security posture, and update cadence are all delivered through Intune.

Intune policies are expressed against the Windows Configuration Service Provider surface — a tree of configuration nodes maintained by Microsoft that exposes the Windows operating system's configurable settings to the MDM protocol. Each CSP node corresponds to a specific Windows behavior; collectively the nodes cover the substantial majority of the configuration surface that was historically addressable through Group Policy, with continuing expansion to cover the remaining gaps. The GPO-to-Intune-matrix artifact in this kit catalogs the translations for common settings.

Intune policies are authored in the Intune admin center as configuration profiles (general settings), security baselines (coordinated security configurations derived from Microsoft's baselines or custom), compliance policies (evaluation criteria for the Conditional Access compliance signal), administrative templates (Group Policy-flavored settings ingested into Intune from ADMX templates), settings catalog policies (the modern unified surface for most settings), and several other policy types. Policies are assigned to Microsoft Entra security groups; group membership can be static or dynamic (driven by Entra group membership rules).

Application deployment uses the Win32 app model (`.intunewin` packages wrapping arbitrary Windows installers), the Microsoft Store integration (for store-delivered applications), and the Microsoft 365 Apps integration (for Microsoft 365 Apps for enterprise, formerly Office 365 ProPlus). The Win32 app model is the predominant mechanism for traditional desktop applications. Applications can be deployed as "Required" (installed without user action), "Available" (visible in the Company Portal for user-initiated install), or "Uninstall" (removed if previously installed).

Updates are governed by Windows Update for Business policies, with deployment rings, deadlines, and pause windows controlled through Intune. Feature updates, quality updates, and driver updates can each be controlled independently. The Windows Update for Business reports surface compliance and deployment status with substantially richer reporting than is available on Windows Server Update Services.

## Conditional Access at the center

Conditional Access is the principal access-control mechanism in Phase IV. Where the legacy phase used network location and domain membership as proxies for trust, Phase IV uses Conditional Access to evaluate the actual posture of the device, the user, and the sign-in attempt at the moment of access.

The signals available to Conditional Access include the user's identity and group memberships, the user's risk score (from Microsoft Entra ID Protection), the sign-in risk score, the device's join type (Microsoft Entra joined, hybrid joined, registered, or none), the device's compliance state (from Intune), the device's platform (Windows, macOS, iOS, Android, etc.), the client application (browser, modern auth client, legacy client), the sign-in location (geographic or named location), and several others.

The grant controls available include Block access (deny outright), Require multi-factor authentication, Require device to be marked as compliant, Require Microsoft Entra hybrid joined device, Require approved client app, Require app protection policy, Require password change, and Require terms of use acceptance. Multiple grant controls can be combined with logical AND or OR.

A mature Phase IV Conditional Access posture typically includes policies that block legacy authentication entirely; require multi-factor authentication for all interactive sign-ins; require device compliance for access to sensitive applications; block sign-ins from disallowed locations; require both multi-factor authentication and device compliance for administrative roles; and apply adaptive controls based on sign-in risk and user risk scores. The conditional-access-rollout-playbook artifact in this kit covers the deployment discipline.

## Compliance evaluation continuous

Compliance evaluation in Phase IV is continuous rather than point-in-time. The Intune Management Extension on each enrolled device evaluates the assigned compliance policy on a recurring cadence (typically eight hours, configurable), reports the result to Intune, and the result is made available to Conditional Access for use in access decisions. A device that drifts out of compliance — because BitLocker was disabled, the operating system fell behind on updates, the endpoint protection signatures grew stale, or a required application was uninstalled — is denied access to compliance-protected resources within hours of the drift.

The compliance evaluation is independent of the configuration that produces the compliance state. A security baseline can configure BitLocker to be enabled, but the compliance policy is what evaluates whether BitLocker is actually enabled and reports the result. A misconfigured compliance policy (one whose criteria do not match the actual configuration) can mark devices non-compliant even when they are configured correctly; a missing compliance policy means devices have no compliance signal at all and cannot satisfy Conditional Access policies requiring compliance.

## Cloud Kerberos Trust

A pure Microsoft Entra-joined device does not, by default, possess Kerberos tickets usable against on-premises domain controllers. The default authentication mechanism is the Primary Refresh Token issued by Entra ID, which is recognized by cloud-aware services but not by services that authenticate through on-premises Kerberos (file shares on Windows file servers, legacy line-of-business applications that require Kerberos, internal web applications that use integrated Windows authentication).

Microsoft Entra Kerberos (sometimes referred to as Cloud Kerberos Trust) addresses this gap. With Cloud Kerberos Trust configured, Microsoft Entra ID issues partial Kerberos ticket-granting tickets on behalf of synchronized hybrid users, using a trust relationship established between Entra ID and the on-premises Active Directory forest. The user authenticates to Entra ID, receives a partial ticket, and presents it to an on-premises domain controller, which completes the ticket into a full Kerberos credential usable for accessing on-premises resources.

The configuration of Cloud Kerberos Trust involves creating a Microsoft Entra Kerberos object in the on-premises directory (using the AzureADHybridAuthenticationManagement PowerShell module), enabling the trust in the Microsoft Entra admin center, and ensuring that the relevant users are synchronized hybrid identities. Once configured, the user experience is essentially seamless: an Entra-joined device, signed in to Entra ID, can access an on-premises file share by SMB path with no additional authentication prompt.

Cloud Kerberos Trust has limitations. It supports synchronized hybrid users, not cloud-only users (because the on-premises directory must have a record of the user to issue the eventual Kerberos ticket). It requires the device to have network reachability to an on-premises domain controller at the moment of access (the partial ticket must be completed by the domain controller). It does not support every Kerberos use case (delegation scenarios in particular can be problematic). For most file-share and legacy-application reach-back scenarios, it is sufficient; for more complex scenarios, retaining hybrid join may be the better choice.

## Microsoft Defender for Endpoint integration

Phase IV typically includes Microsoft Defender for Endpoint as the endpoint security platform. Defender for Endpoint is licensed separately from Intune (often included in Microsoft 365 E5 or Microsoft Defender for Endpoint Plan 2) and provides endpoint detection and response, automated investigation and response, threat and vulnerability management, and integration with the broader Microsoft Defender XDR portfolio.

The integration with Intune is bidirectional. Intune configures Defender for Endpoint through security baselines and configuration profiles; Defender for Endpoint provides risk signals that flow back into Intune compliance evaluation and into Conditional Access. A device whose Defender for Endpoint risk score crosses a configured threshold can be marked non-compliant automatically, triggering Conditional Access denial until the underlying threat is resolved.

The Defender for Endpoint console (security.microsoft.com) provides visibility into endpoint security events, supports investigation of detected threats, and integrates with Microsoft Sentinel for broader security operations workflows. The console is operated by the security operations team; the Intune-side configuration is operated by the endpoint management team.

## Zero Trust posture

Phase IV operationalizes the Zero Trust security architecture. The core Zero Trust principles — verify explicitly (every access is authenticated and authorized), use least-privileged access (each access is scoped to the minimum required), and assume breach (the security posture assumes adversaries are already inside the environment) — are directly supported by the Phase IV architecture. Verification is performed continuously by Conditional Access, with multi-factor, device compliance, risk evaluation, and location signals at each access. Least-privileged access is supported through application-scoped Conditional Access policies and Microsoft Entra Privileged Identity Management for just-in-time elevation of administrative roles. The assume-breach posture is supported by Microsoft Defender for Endpoint's detection capabilities and by the cloud-resident nature of the management plane (an adversary who compromises a single device cannot easily move to compromise the management plane itself).

The Zero Trust architecture is not a Phase IV exclusive — elements of Zero Trust can be implemented in Phases II and III — but Phase IV represents the cleanest architectural realization. The legacy assumptions (network perimeter as trust boundary, domain join as a sufficient identity signal, on-premises infrastructure as authoritative) that the Zero Trust model rejects are simply absent in Phase IV.

## Operational profile

The information technology organization for Phase IV is the leanest of any phase. The on-premises infrastructure that supported the legacy and hybrid phases — domain controllers, Configuration Manager, on-premises certificate authorities — can be retained for the residual hybrid population but is not required for new devices. The imaging team is no longer required for net-new devices (the device boots, Autopilot provisions it, the user receives it ready to use; no technician touches the hardware between manufacturer and user). The Configuration Manager team can transition to retirement or migration roles. The cloud teams (identity engineering, modern endpoint management, security operations) grow accordingly.

Staffing in this phase typically returns to or improves on the legacy-phase ratios, despite the much larger functional surface area, because the on-premises operational burden is dramatically reduced. The cost profile inverts from capital-heavy (servers, storage, datacenter) to subscription-heavy (Microsoft 365 and Intune licensing, Defender for Endpoint licensing), with the total cost typically lower than the legacy or hybrid phases for organizations at scale.

User experience in this phase is meaningfully better than in prior phases. New hires can be onboarded by shipping a device directly to their home address; the device arrives in its retail box, the user unboxes it, signs in with their work account, and reaches the desktop ready for work. Hardware replacement is similarly streamlined. Travel and remote work require no special handling. The friction surfaces that historically required helpdesk intervention (Wi-Fi configuration, VPN setup, application installation) are largely absent.

## Failure modes characteristic of the full transition

The failure modes characteristic of Phase IV are concentrated at the Autopilot enrollment boundary. A device that is not registered to the tenant at Autopilot time provisions to consumer Windows rather than corporate Windows, requiring either a reset and re-provisioning (after correcting the registration gap) or post-provisioning manual remediation. A device registered to the wrong tenant cannot be added to the correct tenant until removed from the incorrect one, which may take up to 24 hours of propagation delay. A device whose Autopilot profile is incorrect provisions with the wrong configuration. The enrollment-diagnostic-cookbook artifact in this kit covers these failure modes in detail.

Once successfully enrolled, Phase IV devices have characteristically fewer failure modes than prior phases. The narrow surface area (one identity, one management plane, no on-premises dependencies) eliminates many of the cross-plane reconciliation failures of Phase III. Policy delivery is reliable, compliance evaluation is timely, and Conditional Access decisions are based on current signals. The remaining failure modes — Conditional Access misconfiguration, compliance policy errors, application deployment issues — are addressed through standard Intune troubleshooting and Conditional Access discipline.

## What persists

Some on-premises elements typically persist into Phase IV even at organizations that have committed fully to the cloud-native architecture. A small on-premises Active Directory may remain in service to support legacy line-of-business applications that cannot be migrated, file servers serving on-premises shares, or specific compliance requirements. On-premises certificate authorities may persist if there are non-Microsoft systems that require certificates from a corporate PKI. The persistence is bounded — typically a small number of servers serving specific use cases rather than the broad on-premises infrastructure of the legacy phase — and is managed as a legacy footprint rather than as growing infrastructure.

## References

Authoritative documentation includes Microsoft's Windows Autopilot documentation at Microsoft Learn (the "Windows Autopilot overview" article and the connected deployment-mode, scenario, and troubleshooting articles); the Microsoft Entra Join planning and deployment documentation; the Microsoft Intune service documentation including configuration profiles, security baselines, and compliance policies; the Conditional Access documentation including policy authoring, common policy patterns, and report-only mode discipline; the Microsoft Entra Kerberos (Cloud Kerberos Trust) configuration documentation; and the Microsoft Defender for Endpoint integration documentation. The "Zero Trust deployment plan with Microsoft 365" at Microsoft Learn maps the Phase IV architecture to the Zero Trust principles. The Microsoft Endpoint Configuration Manager and Microsoft Intune "Modern Workplace" reference architectures provide end-to-end deployment guidance suitable for organizations entering Phase IV.
