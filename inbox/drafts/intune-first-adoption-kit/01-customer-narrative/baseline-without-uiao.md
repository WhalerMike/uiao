# Modern Device Provisioning and Governance: A Four-Phase Narrative Assessment of the Journey from Active Directory Domain Join to Intune-First Cloud-Native Management

## Purpose and Scope

The modern Windows device ecosystem has undergone a fundamental architectural shift. Where organizations once relied on traditional Active Directory Domain Join, Group Policy, and imaging pipelines to provision and govern Windows endpoints, Microsoft now positions Windows Autopilot, Microsoft Intune enrollment, and Microsoft Entra ID join as the preferred model for cloud-first device identity, configuration, and compliance. The shift is rarely a single migration event. Most enterprises traverse it as a journey through four reasonably distinct phases: a legacy phase grounded entirely in on-premises infrastructure, an early transition phase in which cloud identity arrives for users while devices remain governed on premises, a later transition phase characterized by hybrid coexistence and co-management, and a full transition phase in which new hardware is provisioned directly into a cloud-native posture and on-premises directory dependencies are gradually retired. This document describes each phase in narrative form, illustrates the topology with text-based diagrams, and surfaces the architectural reasoning, operational mechanics, and failure modes characteristic of each state. It is intended as a customer-facing reference document for an enterprise preparing to adopt an Intune-first provisioning strategy for new laptops and Microsoft Surface devices, written without reliance on any particular governance overlay or proprietary framework.

---

## Phase I — Legacy: Pure Active Directory Domain Join

Before Microsoft Entra ID and Microsoft Intune existed in their current form, the governance model for Windows endpoints centered entirely on Active Directory Domain Services and the surrounding ecosystem of on-premises infrastructure that depended on it. The architecture is mature, well-understood, and continues to function for the majority of enterprises operating today. Understanding it precisely is the first step in understanding what the modern model replaces and what it preserves.

A device entering service in this model is first provisioned by imaging. The organization maintains a reference image, customarily constructed and stored on a deployment server running Microsoft Deployment Toolkit, Microsoft Configuration Manager, or a third-party imaging platform. The image contains a specific build of Windows, a curated set of drivers for the supported hardware models, the organization's standard application set, and configuration baselines applied through unattended setup files and provisioning scripts. The image is delivered to new hardware either through pre-boot execution of a network boot loader, through a bootable USB device prepared by a deployment technician, or through a vendor preload arrangement in which the manufacturer applies the image at the factory. The imaging process is sequential, time-consuming, and tightly coupled to the version of Windows currently in service; when a new feature update or quality update arrives, the image is typically rebuilt and retested before broad adoption.

Once imaged, the device is joined to an on-premises Active Directory domain. The domain join operation creates a computer object inside the directory, generates a machine account credential that the device stores in its local registry, and establishes a Kerberos trust relationship between the device and the domain controllers serving its site. From this point forward, the device authenticates to the directory using its machine account, and users authenticating interactively on the device receive Kerberos ticket-granting tickets that they can present to other domain-joined resources. The directory is the source of truth for both user identity and device identity, and the two are linked only loosely: a user is authorized to log in to a device because Group Policy or local configuration permits it, not because the directory expresses an explicit binding between the user and the device.

Configuration in this model flows through Group Policy. Administrators define Group Policy Objects in the directory, link them to organizational units, sites, or the domain root, and rely on the Group Policy Client service on each endpoint to retrieve and apply those settings on a recurring refresh interval, typically every ninety minutes plus a randomized offset. The Group Policy engine evaluates the settings applicable to the device and to the currently signed-in user, resolves conflicts according to a documented precedence order, and applies the resulting policy locally. The configuration surface available through Group Policy is vast, encompassing security baselines, software restriction, certificate enrollment, drive mapping, Internet Explorer maintenance, scheduled task creation, registry modification, file deployment, and innumerable application-specific administrative templates contributed by Microsoft and third-party software vendors.

Application delivery is handled through complementary infrastructure rather than through the directory itself. Microsoft Configuration Manager, deployed on premises with its own site servers, distribution points, and management points, delivers application packages, software updates, operating system upgrades, and reporting telemetry to its client agent installed on each endpoint. Smaller environments use Group Policy software installation, login scripts, or manual installation by support staff. Patching is governed either by Configuration Manager or by Windows Server Update Services, both of which depend on the device being able to reach the on-premises infrastructure regularly. Certificate enrollment flows through Active Directory Certificate Services, with autoenrollment policies delivered by Group Policy and certificate templates published in the directory.

Trust in this model is implicitly perimeter-based. A device on the corporate local area network, or connected to it through a virtual private network tunnel terminated at a corporate gateway, is assumed to be in a relatively trustworthy posture by virtue of being inside the perimeter. Access to file shares, line-of-business applications, intranet sites, departmental printers, and internal services is mediated through Kerberos tickets issued by domain controllers, with NTLM available as a fallback for clients or services that do not support Kerberos. There is no native concept of device compliance as an input to access decisions. A device that is domain-joined and reachable on the network can authenticate to corporate resources regardless of whether its disk is encrypted, whether its operating system is current on security updates, whether its endpoint protection agent is running, or whether its firewall is configured according to policy. The presumption is that the combination of domain join, network location, and Group Policy enforcement is sufficient to establish trust.

```
                       ON-PREMISES PERIMETER
   +-----------------------------------------------------------+
   |                                                           |
   |          +----------------------------------+             |
   |          |   Active Directory Domain        |             |
   |          |         Controllers              |             |
   |          |  (Kerberos KDC, LDAP, DNS, GPO   |             |
   |          |   storage in SYSVOL)             |             |
   |          +----------------+-----------------+             |
   |                           |                               |
   |   +-----------+-----------+-----------+-------------+     |
   |   |           |                       |             |     |
   | +-+-------+ +-+--------+ +------------+-+ +---------+--+  |
   | |  Group  | |   File   | | Configuration| |  AD CS     |  |
   | |  Policy | |   and    | |   Manager    | |  (PKI:     |  |
   | |  Engine | |   Print  | |  (Imaging,   | |  Issuing   |  |
   | | (GPOs)  | |  Servers | |   Apps,      | |  CAs,      |  |
   | |         | |  (SMB,   | |   Patching,  | |  Autoenr.) |  |
   | |         | |  NTFS)   | |   Inventory) | |            |  |
   | +-+-------+ +-+--------+ +------+-------+ +---+--------+  |
   |   |           |                 |             |           |
   |   +-----------+-----------------+-------------+           |
   |                           |                               |
   |                +----------+----------+                    |
   |                |   Domain-Joined     |                    |
   |                |     Endpoint        |                    |
   |                |  (Imaged from gold  |                    |
   |                |   image; Computer   |                    |
   |                |   object in AD DS;  |                    |
   |                |   GPO-governed)     |                    |
   |                +---------------------+                    |
   |                                                           |
   +-----------------------------------------------------------+
            ^                                       ^
            |                                       |
        Corporate LAN                          VPN Tunnel
        (presumed trustworthy)             (extended perimeter)
```

The operational profile of this phase is distinct. The information technology organization maintains substantial on-premises infrastructure, including domain controllers in multiple sites for redundancy and authentication latency, Configuration Manager primary sites and distribution points sized for the device population, certificate authorities for public key infrastructure, file and print services, and the deployment infrastructure required to image new hardware. Staffing is correspondingly substantial: domain administrators, Configuration Manager engineers, imaging technicians, and a help desk equipped to troubleshoot Group Policy application failures, certificate enrollment issues, and network connectivity problems that cause devices to fall out of policy. New employee onboarding is a logistical process involving the receipt of new hardware, imaging by a technician, configuration of asset records, and physical or remote handoff. New site deployments require careful planning of domain controller placement, network bandwidth provisioning, and replication topology.

The strengths of this model are real and worth acknowledging. Active Directory and Group Policy provide an extraordinarily mature, well-documented, and granular configuration surface. The trust boundaries are simple to reason about, the failure modes are well understood, and the supporting ecosystem of administrative tools is vast. For an organization with stable physical premises, a workforce that is co-located with its infrastructure, and a relatively small inventory of cloud-resident resources, the model continues to perform well.

The weaknesses become acute the moment the assumptions begin to fail. A workforce that is geographically distributed, mobile, or working from home strains the implicit assumption of network proximity to domain controllers. Devices that spend long periods disconnected from corporate networks drift out of policy alignment because Group Policy refreshes depend on directory reachability. Cloud-resident services and applications cannot consume Kerberos tickets issued by an on-premises directory without significant integration work. Compliance posture is not visible to access decisions, which means a compromised but still domain-joined device can be used to access sensitive resources until a human operator notices and intervenes. Imaging pipelines become bottlenecks for hardware refresh cycles, and the imaging process itself introduces configuration drift between successive builds. As these stresses accumulate, the organization begins to look for ways to extend identity, configuration, and access control into the cloud, and the early transition phase begins.

---

## Phase II — Early Transition: Cloud Identity for Users, On-Premises Governance for Devices

The early transition phase is the phase in which most enterprises spent the late 2010s, and in which many enterprises still operate today. The defining characteristic of this phase is that user identity has been extended into Microsoft Entra ID for purposes of accessing cloud-resident applications, while device identity, device configuration, and device governance remain entirely anchored in Active Directory. The cloud has touched the user, the mailbox, the document library, and the collaboration platform, but it has not yet touched the endpoint itself. The endpoint continues to be imaged, domain-joined, and governed by Group Policy exactly as it was in the legacy phase. What has changed is what the endpoint authenticates to.

The architectural bridge that enables this phase is Microsoft Entra Connect, formerly known as Azure AD Connect, which is installed on a server inside the organization's network and configured to synchronize identity objects from the on-premises Active Directory forest into the organization's Microsoft Entra tenant³. User accounts, group memberships, and certain object attributes are projected into the cloud directory at regular intervals, typically every thirty minutes by default. The result is a population of cloud identities that share their unique identifier with their on-premises counterparts and that authenticate, conceptually, against the same underlying credential material. Authentication itself can be configured to use password hash synchronization, in which a salted and hashed representation of the user's password is replicated into Entra ID and authentication is performed by Microsoft, or pass-through authentication, in which the cloud directory forwards authentication requests back through a lightweight agent to an on-premises domain controller for validation. Federated authentication using Active Directory Federation Services remains possible but has been progressively deprecated as the simpler models have matured.

Once cloud identity exists, cloud applications can consume it. Microsoft 365, in this phase, becomes the dominant driver of cloud adoption. Mailboxes are migrated from on-premises Exchange Server to Exchange Online, document libraries are migrated from on-premises SharePoint Server to SharePoint Online, and personal file shares are progressively replaced by OneDrive for Business. Microsoft Teams arrives as a unified communication and collaboration surface that is cloud-native from inception. Software-as-a-service applications outside the Microsoft estate are integrated through SAML or OpenID Connect federation, with Entra ID serving as the identity provider. Conditional Access, the policy engine that governs access to cloud resources, begins to appear in administrative consoles, initially used in basic configurations to require multi-factor authentication for cloud sign-ins, to block legacy authentication protocols that cannot be protected by modern controls, and to restrict access from specific geographic regions or network locations.

The endpoint, however, is largely untouched by this evolution. The device remains imaged from a gold image, joined to the on-premises Active Directory domain, and governed by Group Policy. The user signs in to the device using domain credentials, receives Kerberos tickets from a domain controller, and accesses on-premises resources exactly as before. When the user opens a modern Office client, the client uses modern authentication to obtain a token from Microsoft Entra ID, often using the user's domain credentials transparently through seamless single sign-on, and presents that token to Exchange Online or SharePoint Online. To the user, the experience is largely seamless: a single sign-in unlocks both on-premises and cloud resources. To the administrator, however, the device is still a domain-joined endpoint with no presence in the cloud directory whatsoever and no relationship to Microsoft Intune. The device has no device identity in Entra ID, no compliance state, and no cloud-managed configuration profile.

```
        ON-PREMISES                              MICROSOFT CLOUD
   +-----------------------+               +---------------------------+
   |                       |               |                           |
   |   Active Directory    |  Entra        |   Microsoft Entra ID      |
   |   Domain Controllers  +--Connect----->+   (User Identity Only;    |
   |   (Computer object,   |  Sync         |    NO Device Object;      |
   |    user object,       |               |    SSO Token Issuance     |
   |    Group Policy,      |               |    for Cloud Apps)        |
   |    Kerberos KDC)      |               |                           |
   |                       |               +-------------+-------------+
   +----------+------------+                             |
              |                                          |
              | Group                                    | OAuth / SAML
              | Policy                                   | Tokens
              | + Kerberos                               |
              |                                          |
              |                            +-------------+-------------+
              |                            |                           |
              |                            |   Microsoft 365 and       |
              |                            |   SaaS Applications       |
              |                            |  (Exchange Online,        |
              |                            |   SharePoint Online,      |
              |                            |   OneDrive, Teams,        |
              |                            |   third-party SaaS)       |
              |                            |                           |
              |                            +-------------+-------------+
              |                                          |
              |                            +-------------+-------------+
              |                            |   Conditional Access      |
              |                            |  (Cloud-app scope only;   |
              |                            |   MFA, location, legacy   |
              |                            |   protocol blocks)        |
              |                            +-------------+-------------+
              |                                          |
   +----------+--------------------------------------+   |
   |                                                 |   |
   |    Domain-Joined Endpoint                       |   |
   |    (Imaged, AD-joined, GPO-governed;            +<--+
   |     User signs in with domain credentials;      |  Cloud
   |     Office clients obtain tokens via            |  token
   |     seamless SSO; device itself is invisible    |  flow
   |     to Microsoft Entra ID)                      |  to user
   |                                                 |
   +-------------------------------------------------+
```

The operational profile of this phase preserves nearly all of the legacy infrastructure while adding new responsibilities in the cloud. Domain controllers, Configuration Manager, certificate authorities, file servers, and imaging infrastructure remain in service. The new additions are the Entra Connect synchronization server, the operational disciplines required to keep it healthy, the Conditional Access policy framework, the multi-factor authentication enrollment process for the user population, and the cloud administration consoles required to govern Microsoft 365 and any federated software-as-a-service applications. The information technology organization typically grows a new subspecialty in cloud identity engineering without shrinking any of the existing on-premises subspecialties. Cost increases before it decreases.

The pain points of this phase emerge from the fundamental asymmetry it creates. User identity is cloud-aware; device identity is not. Conditional Access policies can demand that a sign-in originates from a compliant device or a hybrid-joined device, but the devices in this phase satisfy neither condition because they have no presence in Entra ID and no enrollment in Intune. The organization is therefore forced to choose between weaker Conditional Access policies, which permit sign-in from any device regardless of its posture, and stronger policies that begin to lock the workforce out of cloud applications because their devices cannot prove compliance. Mobile devices, accessed through Office mobile applications, are often enrolled into Intune as a mobile application management surface even when corporate Windows devices are not, creating a confusing inconsistency in the management posture across form factors. Personal devices used for work, governed by neither Group Policy nor Intune, present a third unmanaged surface.

The pressure that pushes an organization out of this phase is the inability to apply meaningful device-aware Conditional Access without first establishing some form of device presence in the cloud directory. The next phase exists primarily to address that gap.

---

## Phase III — Later Transition: Hybrid Microsoft Entra Join and Intune Co-Management

The later transition phase begins when the organization extends the cloud directory's awareness from users to devices. The mechanism is Hybrid Microsoft Entra Join, in which a device that is already joined to an on-premises Active Directory domain additionally registers itself in Microsoft Entra ID as a hybrid-joined device, creating a device object in the cloud directory that is linked to the on-premises computer object⁴. The device now has two identities and, with the further step of automatic enrollment, two management planes. Group Policy continues to deliver configuration from the on-premises directory, and Microsoft Intune begins to deliver configuration from the cloud. The model is referred to as co-management, and the boundary between the two management planes is governed by a set of workload sliders in Configuration Manager that determine which configuration domain is authoritative for each policy area.

The hybrid join handshake is conceptually straightforward but operationally intricate. When a device joins the on-premises domain, a scheduled task on the device, populated through Group Policy, initiates a registration request to Microsoft Entra ID. The request includes proof of the device's identity in the on-premises directory, typically through a certificate or service-connection-point lookup, and is validated by the cloud directory against the synchronized device object that Entra Connect has projected. If the validation succeeds, the device receives a cloud device certificate, the device object in Entra ID is marked as joined, and the device becomes eligible for cloud-aware policies. If any link in the chain is broken, including Entra Connect lag, an incorrect service connection point, a misconfigured scheduled task, time skew between the device and the directory, or a network path that cannot reach the cloud, the registration fails silently and the device remains in a half-joined state from which recovery often requires manual intervention.

Once a device is hybrid-joined, it becomes eligible for automatic enrollment into Microsoft Intune. The enrollment trigger can be delivered through a Group Policy setting that directs the device to enroll using its hybrid identity, through a Configuration Manager client configuration that initiates enrollment as part of co-management onboarding, or through user action via the Company Portal application. Once enrolled, the device receives configuration profiles, security baselines, applications, and compliance policies from Intune in addition to whatever it is still receiving from Group Policy and Configuration Manager. Conflicts between the two configuration sources are possible and require careful attention; both Group Policy and Intune are capable of expressing many of the same settings, and the resolution of conflicts depends on which provider is the last writer to a particular registry location or configuration service provider node.

The workload sliders in Configuration Manager provide the formal mechanism for partitioning the management surface. Each slider corresponds to a workload domain, with the available domains including compliance policies, device configuration, endpoint protection, resource access policies, client applications, Office Click-to-Run apps, Windows Update policies, and Microsoft Defender for Endpoint integration. Each slider can be set to Configuration Manager, Pilot Intune, or Intune, with the Pilot setting permitting a subset of devices in a designated collection to receive the workload from Intune while the remainder continue to receive it from Configuration Manager. The intent is to allow staged migration of workloads, one domain at a time, with rollback available if a workload moves to Intune and operational problems emerge.

```
        ON-PREMISES                              MICROSOFT CLOUD
   +-----------------------+              +---------------------------+
   |                       |              |                           |
   |   Active Directory    |   Entra      |   Microsoft Entra ID      |
   |   Domain Controllers  +--Connect---->+   (Hybrid Device Object   |
   |   (Computer object,   |   Sync       |    linked to on-prem      |
   |    user object,       |              |    computer object;       |
   |    Group Policy,      |              |    user identity)         |
   |    Kerberos KDC)      |              |                           |
   |                       |              +-------------+-------------+
   +----------+------------+                            |
              |                                         |
              | Group Policy                            | Automatic
              | + Kerberos                              | MDM
              |                                         | Enrollment
              |                                         |
   +----------+------------+              +-------------+-------------+
   |                       |              |                           |
   |   Configuration       |   Workload   |   Microsoft Intune        |
   |   Manager             +<--Sliders--->+   (Policy, Compliance,    |
   |   (Imaging, Apps,     |              |    Apps, Baselines;       |
   |    Patching,          |              |    consumes hybrid        |
   |    Inventory)         |              |    identity)              |
   |                       |              |                           |
   +----------+------------+              +-------------+-------------+
              |                                         |
              |                            +------------+--------------+
              |                            |  Conditional Access       |
              |                            |  (Now device-aware:       |
              |                            |   can require hybrid      |
              |                            |   join AND/OR Intune      |
              |                            |   compliance)             |
              |                            +------------+--------------+
              |                                         |
              +-------------------+---------------------+
                                  |
                       +----------+----------+
                       |   Hybrid Entra-     |
                       |   Joined Endpoint   |
                       |   (Two identities:  |
                       |    AD computer +    |
                       |    Entra device;    |
                       |    Co-managed by    |
                       |    ConfigMgr and    |
                       |    Intune)          |
                       +---------------------+
```

The operational profile of this phase is the most demanding in the entire journey, because it preserves all of the on-premises infrastructure of the legacy phase, adds all of the cloud infrastructure of the early transition phase, and layers on additionally the hybrid join machinery, the co-management workload partitioning, and the dual policy reconciliation that the model requires. The information technology organization is now operating two management planes simultaneously and must maintain expertise in both. Help desk staff must understand both Group Policy resultant set of policy and Intune policy evaluation. Engineering staff must understand both Configuration Manager task sequences and Intune application packaging. Auditors must reconcile compliance evidence drawn from both planes. Cost is at its peak during this phase, and the duration of the phase determines the total cost of the modernization effort.

The pain points are characteristic and worth enumerating in prose. Devices that fail hybrid join silently are common, and the failure mode often does not surface until a user attempts to access a resource gated by device-aware Conditional Access and is denied. Duplicate device objects accumulate in the cloud directory when devices are re-imaged, re-joined, or replaced without proper retirement of their predecessor objects, and the duplicates degrade the accuracy of compliance reporting and access decisions. Group Policy and Intune occasionally express the same setting in incompatible ways, with the resulting behavior dependent on the order in which the two providers last applied their configuration. Conditional Access policies that require both hybrid join and Intune compliance can lock out devices that have one but not the other, and the diagnostic process to discover which condition is missing is non-trivial. Configuration Manager co-management requires careful planning around boundary groups, client communication modes, and certificate lifecycles. Time pressure to migrate workloads to Intune competes with the operational caution required to avoid disrupting production.

The pressure that pushes an organization beyond this phase comes from two directions. The first is the cumulative operational cost of running two management planes indefinitely, which most organizations conclude is unsustainable past a multi-year transition window. The second is the increasing maturity of the pure cloud-native model itself, which by the mid-2020s had reached a point where the limitations that historically motivated retaining Active Directory had been substantially closed by Microsoft's investment in Microsoft Entra ID, Microsoft Intune, Microsoft Entra Kerberos, and the surrounding ecosystem. New hardware acquired during this phase can increasingly be provisioned directly into the full transition state without ever being joined to the on-premises directory, and the population of pure cloud-native devices begins to grow alongside the hybrid population.

---

## Phase IV — Full Transition: Pure Microsoft Entra Join and Intune-Only Management

The terminal state of the journey is a device that has no relationship with on-premises Active Directory at any point in its lifecycle. The device is procured directly from a manufacturer or reseller participating in the Windows Autopilot program. Its hardware hash is registered into the organization's Microsoft Entra tenant before the device is shipped, either through the Cloud Solution Provider channel for direct Microsoft purchases or through the reseller's integration for indirect purchases. An Autopilot deployment profile is assigned to the device, specifying the join type as Microsoft Entra Join, the user experience as either user-driven or self-deploying, the enrollment status page configuration, and the application and policy assignments that will be applied during provisioning¹.

When the device is first powered on by its intended user, the out-of-box experience contacts the Autopilot service over the internet, retrieves the device's assigned profile, and walks the user through a corporate-branded sign-in experience. The user authenticates against Microsoft Entra ID using their cloud identity, completes any required multi-factor authentication challenges, and the device performs a native join to Microsoft Entra ID. Automatic enrollment into Microsoft Intune follows immediately. The enrollment status page tracks the application of configuration profiles, security baselines, compliance policies, and required applications, holding the user at a status screen until the device has reached its target configuration. When the status page completes, the user reaches the Windows desktop on a device that is already joined, already enrolled, already configured, already evaluated for compliance, and already inside the appropriate Conditional Access scope. No technician has touched the device. No image has been applied. No domain controller has been contacted.

Identity in this model is exclusively cloud-resident. The device object exists in Microsoft Entra ID and nowhere else. Authentication uses primary refresh tokens issued by Entra ID, which can be combined with Windows Hello for Business, FIDO2 security keys, certificate-based credentials, or passkey authentication for passwordless sign-in. The primary refresh token is bound to the device through the device's Trusted Platform Module and is refreshed periodically as long as the device remains in good standing. Tokens for individual cloud applications are derived from the primary refresh token through silent token acquisition, and the device's compliance state is evaluated continuously by Intune and surfaced to Conditional Access as an input to access decisions². A device that drifts out of compliance, whether because BitLocker is disabled, the operating system has fallen behind on updates, the endpoint protection signatures have grown stale, or a required application has been uninstalled, will be denied access to protected resources until the compliance state is restored.

Configuration flows through Microsoft Intune as Mobile Device Management policies expressed against the Windows Configuration Service Provider surface. Configuration profiles, security baselines, compliance policies, application deployments, certificate profiles, and update rings are authored in the Intune administrative console, scoped to device groups, and delivered to enrolled devices through the Mobile Device Management channel. Application delivery uses the Win32 app model for traditional Windows applications, the Microsoft Store integration for store-delivered applications, and the Microsoft 365 Apps integration for Office. Updates are governed by Windows Update for Business policies, with deployment rings and pause windows controlled through Intune. Endpoint protection is governed by Microsoft Defender for Endpoint integrated into the same policy surface, with detection telemetry flowing into Microsoft Sentinel or other security information and event management platforms.

```
                              MICROSOFT CLOUD
   +-----------------------------------------------------------+
   |                                                           |
   |               +-------------------------------+           |
   |               |    Microsoft Entra ID         |           |
   |               |  (Device Identity,            |           |
   |               |   User Identity,              |           |
   |               |   PRT issuance,               |           |
   |               |   Authentication Plane,       |           |
   |               |   Token Issuance)             |           |
   |               +---------------+---------------+           |
   |                               |                           |
   |               +---------------+---------------+           |
   |               |   Conditional Access          |           |
   |               |  (Policy Decision Point;      |           |
   |               |   consumes device             |           |
   |               |   compliance, user risk,      |           |
   |               |   sign-in risk, location)     |           |
   |               +---------------+---------------+           |
   |                               |                           |
   |     +-------------------------+--------------------+      |
   |     |                                              |      |
   |  +--+------------------+              +------------+----+ |
   |  |   Microsoft Intune  |  Compliance  |   Microsoft 365,| |
   |  |  (Policy plane,     +--Signal----->+   Azure, SaaS   | |
   |  |   compliance,       |              |   applications, | |
   |  |   apps, baselines,  |              |   protected     | |
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
   |  |  (No AD computer      |                                |
   |  |   object; no GPO;     |                                |
   |  |   no imaging;         |                                |
   |  |   PRT bound to TPM)   |                                |
   |  +-----------------------+                                |
   |                                                           |
   +-----------------------------------------------------------+
```

The model accommodates continued access to on-premises resources where they remain in service. A pure Entra-joined device does not, by default, possess Kerberos tickets usable against on-premises domain controllers, but Microsoft Entra Kerberos, sometimes referred to as Cloud Kerberos Trust, addresses the gap by allowing Microsoft Entra ID to issue partial Kerberos ticket-granting tickets on behalf of synchronized hybrid users⁵. The user authenticates to Entra ID, receives the partial ticket, and presents it to an on-premises domain controller, which completes the ticket into a full Kerberos credential usable for accessing on-premises file shares, applications, and other Kerberos-aware resources. The device itself does not need to be domain-joined to participate in this flow. The reach-back is transparent to the user and limited only by the requirement that the user be a synchronized identity and that the network path from the endpoint to a domain controller be available at the moment a service ticket is required.

The operational profile of this phase is the simplest of the four. Imaging infrastructure is no longer required, as the OEM-installed operating system is treated as the baseline and customization is layered on through Intune policy after enrollment. Configuration Manager can be retained for legacy device populations but is no longer required for new hardware. Group Policy infrastructure can be retained for legacy device populations but is similarly no longer required for the cloud-native fleet. Certificate enrollment, if required for cloud-joined devices, can flow through the Simple Certificate Enrollment Protocol or the Public Key Cryptography Standards #12 import mechanism integrated into Intune, with the certificate authority itself optionally remaining on premises. The information technology organization shifts its competency profile from on-premises infrastructure operations toward cloud policy authoring, identity governance, and continuous compliance assessment. Help desk troubleshooting becomes substantially simpler because most failure modes resolve to a single cloud-side configuration plane and a small set of diagnostic surfaces on the endpoint.

This model is not without limitations, and an honest assessment must acknowledge them. Microsoft Entra ID does not provide an organizational unit hierarchy in the Active Directory sense; organizational positioning must be expressed through groups, administrative units, dynamic membership rules, and attribute-driven scoping. Some legacy Group Policy settings have no equivalent on the Configuration Service Provider surface, requiring either reformulation as a different settings type, custom ingestion of administrative templates into Intune, or acceptance that the setting will not be enforced. Applications that have not been packaged for modern deployment, particularly those that depend on per-machine installers, unsigned drivers, or implicit assumptions about domain membership, may require remediation before they can be delivered cleanly through Intune. Devices in disconnected environments without reliable internet access cannot be governed cloud-natively and must remain on a legacy model. None of these limitations are insurmountable, and Microsoft's roadmap continues to close gaps with each release, but they should be understood and planned for rather than discovered in production.

For an enterprise preparing to adopt an Intune-first provisioning strategy for new laptops and Microsoft Surface devices, the practical recommendation that emerges from the four-phase journey is straightforward to state and operationally significant to execute. New hardware acquisitions should be treated as opportunities to deploy directly into the full transition model described in this section, bypassing the hybrid coexistence phase for any device that has no prior relationship with Active Directory. Existing legacy and hybrid-joined devices can remain in their current state until they reach natural hardware refresh, at which point their replacements will be provisioned into the pure cloud-native model. Reach-back to on-premises resources can be enabled where required without compromising the cloud-native posture of newly provisioned devices. Over a typical hardware refresh cycle of three to four years, the population of pure Intune-joined devices will grow, the population of hybrid-joined devices will shrink, the legacy infrastructure will see declining utilization, and the organization will arrive at a fully cloud-native endpoint estate without ever having executed a forced migration. The transition is governed by procurement decisions made today, and those decisions are the substance of the strategic choice this document supports.

---

## Footnotes

¹ Windows Autopilot user-driven Microsoft Entra join overview, Microsoft Learn. https://learn.microsoft.com/en-us/autopilot/tutorial/user-driven/azure-ad-join-workflow

² Plan your Microsoft Entra join implementation, Microsoft Learn. https://learn.microsoft.com/en-us/entra/identity/devices/plan-device-identity

³ What is Microsoft Entra Connect Sync, Microsoft Learn. https://learn.microsoft.com/en-us/entra/identity/hybrid/connect/whatis-azure-ad-connect

⁴ Plan your hybrid Microsoft Entra join implementation, Microsoft Learn. https://learn.microsoft.com/en-us/entra/identity/devices/how-to-hybrid-join

⁵ Enable passwordless security key sign-in to on-premises resources with Microsoft Entra ID (Cloud Kerberos Trust), Microsoft Learn. https://learn.microsoft.com/en-us/entra/identity/authentication/howto-authentication-passwordless-security-key-on-premises

*Note: All Microsoft Learn URLs above should be verified before publication. Microsoft has been actively renaming and relocating identity-related documentation as the Azure AD to Microsoft Entra ID rebrand continues, and stable-looking URLs occasionally redirect or return errors after a documentation reorganization. Citing the document title in addition to the URL preserves the reference even if the URL changes.*
