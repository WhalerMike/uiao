# Phase I — Legacy: A Detailed Reference for Pure Active Directory Domain Join

## Scope and definition

The legacy phase of Windows endpoint governance is defined by an architecture in which device identity, user identity, configuration, application delivery, patching, and access control all originate from on-premises infrastructure, and in which the corporate network perimeter is the principal boundary of trust. A device entering service in this model is imaged, joined to an on-premises Active Directory domain, governed by Group Policy retrieved from a domain controller, supplied with applications by Microsoft Configuration Manager (formerly System Center Configuration Manager, formerly Systems Management Server), patched by Configuration Manager or Windows Server Update Services, equipped with certificates issued by Active Directory Certificate Services, and granted access to corporate resources through Kerberos tickets validated against the same Active Directory infrastructure that authenticated the user at logon. There is no cloud identity, no mobile device management plane, no continuous compliance evaluation, and no native concept of device posture as an input to access decisions.

This phase was the dominant model for enterprise Windows estates from approximately 2000 through approximately 2015, and remains in active service in many organizations today, particularly where regulatory, operational, or geographic constraints limit cloud adoption. Understanding it precisely is the foundation for understanding what the subsequent phases of modernization replace, what they preserve, and what they fail to replicate.

## Architecture overview

The legacy architecture is hierarchical and on-premises. The diagram below illustrates the principal components and their relationships.

```
                       ON-PREMISES PERIMETER
   +-----------------------------------------------------------+
   |                                                           |
   |   +-------------------+    +-------------------+          |
   |   |  Active Directory |    |     AD CS         |          |
   |   |  Domain           |    |  (Issuing CAs,    |          |
   |   |  Controllers      |<-->|   Certificate     |          |
   |   |  (KDC, LDAP,      |    |   Templates,      |          |
   |   |   DNS, SYSVOL)    |    |   Autoenrollment) |          |
   |   +---------+---------+    +---------+---------+          |
   |             |                        |                    |
   |             |     +---------+--------+                    |
   |             |     |                                       |
   |   +---------+-----+-+   +-------------------+             |
   |   |   Configuration  |  |   File & Print    |             |
   |   |   Manager        |  |   Servers (DFS,   |             |
   |   |   (Site Server,  |  |   SMB shares,     |             |
   |   |   DPs, SUP,      |  |   NTFS perms)     |             |
   |   |   Reporting)     |  +-------------------+             |
   |   +---------+--------+                                    |
   |             |                                             |
   |             |     +-------------------+                   |
   |             |     |   WSUS            |                   |
   |             +---->|  (Sync from MU    |                   |
   |                   |   Catalog,        |                   |
   |                   |   SUSDB)          |                   |
   |                   +-------------------+                   |
   |                                                           |
   |   +-------------------+    +-------------------+          |
   |   |   Exchange        |    |   SharePoint /    |          |
   |   |   Server          |    |   Lync/Skype      |          |
   |   |   (Mailbox, CAS)  |    |   for Business    |          |
   |   +-------------------+    +-------------------+          |
   |                                                           |
   |             +-------------+-------------+                 |
   |             |  Domain-Joined Endpoints  |                 |
   |             |  (Imaged, AD-joined,      |                 |
   |             |   GPO-governed, ConfigMgr |                 |
   |             |   client, ADCS certs)     |                 |
   |             +---------------------------+                 |
   +-----------------------------------------------------------+
       ^                                            ^
       |                                            |
  Corporate LAN                                VPN / DirectAccess
  (trusted)                                    (extended perimeter)
```

The perimeter is enforced by a combination of network controls (firewalls, routing, network access control), authentication (Kerberos, NTLM fallback, optional smart card), and physical security (datacenters, branch office wiring closets). A device inside the perimeter, authenticated against the domain, is implicitly trusted to a high degree. A device outside the perimeter must traverse the VPN concentrator or DirectAccess gateway before it is treated as inside.

## Identity foundations

Every device in the legacy phase has a computer object in Active Directory. The computer object holds a machine account credential — functionally equivalent to a user password but managed by the operating system — that the device uses to authenticate to the domain. The machine account password is rotated automatically on a regular cadence (default thirty days) by the netlogon service; the rotation is invisible to users and administrators under normal conditions but can break if the device is offline for a sufficiently long period that the on-device cached credential diverges from the directory-stored credential.

User identity is similarly an Active Directory object, with a sAMAccountName (the legacy down-level logon name), a user principal name (typically in email-address form), a security identifier (SID), and membership in one or more security groups and one or more organizational units. The organizational unit placement is the principal mechanism by which Group Policy is targeted, and the security group membership is the principal mechanism by which resource access is granted.

Kerberos is the authentication protocol of record. A user signing in presents credentials to the Local Security Authority Subsystem Service, which exchanges those credentials with a domain controller's Key Distribution Center for a ticket-granting ticket. The ticket-granting ticket is held in memory for the session and used to obtain service tickets for individual resources (file servers, mail servers, web applications, etc.) on demand. NTLM remains available as a fallback for services or scenarios that cannot use Kerberos, but Kerberos is preferred and is the only mechanism that supports modern security features such as smart card logon and mutual authentication.

The device's local security authority caches credentials in memory and, for some scenarios, in the local registry's LSA secrets. This caching enables offline logon (the device can authenticate a user who has signed in previously, even with no domain controller reachable) but introduces a credential-theft attack surface that has been the subject of substantial security research and remediation guidance.

## Configuration delivery via Group Policy

Group Policy is the configuration delivery mechanism for the legacy phase. Group Policy Objects, authored in the Group Policy Management Console and stored in the directory's SYSVOL share, encode settings that are retrieved by the Group Policy Client service on each domain-joined device and applied locally. The applicable set of Group Policy Objects for a given device-user combination is determined by the device's organizational unit placement, the user's organizational unit placement, the site of the device, and the domain to which the device is joined, in an evaluation order traditionally summarized as Local, Site, Domain, Organizational Unit (LSDOU). Block-inheritance flags, enforcement flags, security filtering by group membership, and Windows Management Instrumentation filters refine the applicable set.

The configuration surface available through Group Policy is vast. Administrative Templates expose tens of thousands of registry-backed settings that govern operating system behavior. Security Settings expose user rights, account policies, audit policies, and security options. Software Settings can deploy software packages or assign user-specific shortcuts. Windows Settings expose folder redirection, scripts, drive maps, network connections, public-key policies, software restriction policies, and IP security policies. Group Policy Preferences, introduced in Windows Server 2008, expose drive mappings, printer connections, scheduled tasks, registry preferences, file deployment, and a number of other items that historically required custom scripting.

Group Policy refresh occurs at logon and at a configurable interval thereafter (default ninety minutes plus a randomized offset of up to thirty minutes). Some changes require a logoff/logon cycle or a reboot to take effect, particularly those involving security descriptors or scripts. The `gpupdate` command can force an immediate refresh; the `gpresult` command reports the resultant set of policy for diagnostic purposes.

Replication of Group Policy Objects between domain controllers is handled by FRS or DFS Replication (depending on the domain functional level). Replication latency between sites — particularly for organizations with many sites or constrained WAN bandwidth — can produce inconsistencies in which devices in different sites receive different versions of a recently-modified policy. Replication topology design and monitoring are skill areas that experienced Active Directory administrators carry; smaller organizations often run into replication issues that they do not have the expertise to diagnose.

## Application delivery via Microsoft Configuration Manager

Application delivery in the legacy phase is handled primarily by Microsoft Configuration Manager. A Configuration Manager site hierarchy consists of a central administration site (in larger deployments), one or more primary sites that hold device records and serve as administrative boundaries, and distribution points that host application content. Each managed device runs a Configuration Manager client agent that registers with a management point, polls for assigned deployments, downloads content from a nearby distribution point, and installs applications, updates, or operating systems according to deployment instructions.

The Configuration Manager application model expresses an application as a logical entity (the thing the user wants — Microsoft Office, Adobe Acrobat, the corporate VPN client) with one or more deployment types (concrete installers — an MSI for one architecture, an EXE for another, an App-V package for a third). Detection rules determine whether the application is already installed; requirements determine whether the device is eligible to receive it (operating system version, RAM, disk space, primary device of a specific user, etc.); dependencies and supersedence relationships define how applications interact when deployed together.

Operating system deployment uses task sequences — ordered lists of steps that, taken together, image a device from bare metal to production state. A task sequence typically begins with a boot to Windows Preinstallation Environment over the network (using a PXE-enabled distribution point), formats the disk, applies the reference image (a WIM file), injects drivers appropriate to the hardware model, joins the domain, installs the Configuration Manager client, and proceeds to install the assigned applications and updates. The completed task sequence can take from forty-five minutes to several hours depending on image size, network bandwidth, and the application set.

Software inventory and hardware inventory are collected by the client agent and stored in the Configuration Manager database. Reporting Services integration provides ad-hoc and scheduled reports against the inventory data, used for license compliance, hardware refresh planning, and audit response.

## Patching infrastructure

Patching in the legacy phase is delivered by Windows Server Update Services or by Configuration Manager's Software Update Point (which extends WSUS). WSUS synchronizes from the Microsoft Update Catalog on a configured cadence, downloads patch metadata and (optionally) patch binaries, and presents the patches to a management console where administrators approve them for deployment. Approved patches are delivered to client devices over the next Windows Update scan cycle, installed at the configured deadline (immediately, on next reboot, at a maintenance window), and reported back to WSUS for compliance tracking.

Configuration Manager extends WSUS with several capabilities important at enterprise scale: automatic deployment rules that apply approval, deadline, and reboot behavior to patches matching specified criteria (typically used for monthly cumulative updates); deployment rings that stage rollout across pilot, broad, and laggard cohorts; maintenance windows that prevent installation during business hours or production-critical windows; and compliance reporting that surfaces devices missing required patches.

Third-party patching — Adobe Reader, Java, Google Chrome, application-specific patches — is supported through partner products that integrate with Configuration Manager (Patch My PC, Ivanti, Adobe's deployment tooling) or through custom Configuration Manager applications wrapping the vendor installer.

## Public key infrastructure

Active Directory Certificate Services provides certificate issuance for the legacy phase. A typical deployment includes a root certificate authority (offline in mature deployments, online in simpler ones), one or more issuing certificate authorities (online, joined to the domain, integrated with directory-stored certificate templates), and a certificate revocation list distribution point (often a web server or LDAP location) that clients consult to verify the validity of presented certificates.

Certificate templates in the directory define the type of certificates that can be issued, the cryptographic parameters, the application policies (server authentication, client authentication, smart card logon, code signing, etc.), the subject naming conventions, and the security permissions that determine which users or computers can enroll for the template. Group Policy delivers the autoenrollment policy that causes domain-joined devices to request certificates for any templates they are permitted to enroll for.

Common use cases include machine certificates for Wi-Fi authentication (802.1X/EAP-TLS), smart card logon certificates for users requiring high-assurance authentication, code signing certificates for internal developers, SSL/TLS certificates for internal web services, and IPsec certificates for site-to-site or client-to-site security associations.

## Endpoint security

Endpoint security in the legacy phase consists of several layered controls. The host firewall (Windows Firewall, configured via Group Policy) restricts inbound and outbound network traffic according to policy. Antivirus and antimalware (historically Microsoft Forefront Endpoint Protection / System Center Endpoint Protection, more recently Microsoft Defender Antivirus) provides signature-based and heuristic detection of malicious code. BitLocker provides full-disk encryption, typically configured to use the device's Trusted Platform Module for key protection with the BitLocker recovery key escrowed to an Active Directory attribute on the computer object.

Software restriction is handled by Software Restriction Policies (legacy), AppLocker (deprecating), or Windows Defender Application Control (modern). Each restricts which executables, scripts, and installers can run, by path, by publisher signature, by file hash, or by network zone.

Network Access Protection, a Windows Server 2008-era feature that quarantined devices failing posture checks, was deprecated in Windows 10 and has no direct successor in the legacy phase; its capabilities are subsumed by Conditional Access and Intune compliance in subsequent phases.

## Imaging and provisioning workflow

A new device entering production in the legacy phase follows a multi-step workflow. The device is procured according to the organization's standard purchasing channel and delivered to a staging area maintained by the deployment team. A deployment technician boots the device into Windows Preinstallation Environment from a PXE-enabled distribution point or from a USB drive. The technician selects a task sequence appropriate to the device class (executive laptop, standard desktop, kiosk, etc.) and the task sequence runs unattended for the duration of the deployment.

The completed device is joined to the domain, has the Configuration Manager client installed, has the standard application set assigned (which may install during the task sequence or post-deployment), has security baselines applied through Group Policy, and is associated with a user account in Active Directory through one of several mechanisms (manual placement in the user's organizational unit, primary device assignment in Configuration Manager, ownership tagging in the asset management database).

The device is then shipped or hand-delivered to the user. User onboarding includes signing in for the first time (which provisions the user profile and applies user-targeted Group Policy), connecting to corporate Wi-Fi (which uses the machine certificate to authenticate, with no user interaction), and confirming that mail, file shares, and intranet applications work correctly.

The imaging team typically handles tens to hundreds of devices per month at a medium-sized organization, and the imaging team's throughput is one of the operational constraints on hardware refresh cycles.

## Joiner, mover, and leaver workflows

Identity lifecycle in the legacy phase is handled through Active Directory directly, occasionally supplemented by an identity management product that orchestrates the directory work.

A new hire (joiner) workflow creates a user object in Active Directory in the appropriate organizational unit, populates required attributes from human-resources information, sets an initial password (delivered to the manager or new hire through a secure channel), adds the user to security groups appropriate to their role, provisions a mailbox in Exchange, and assigns standard applications and resources. The work is typically split among helpdesk (account creation), identity team (group memberships), Exchange administrators (mailbox), and the new hire's manager (resource-specific access).

A role change (mover) workflow updates the user's organizational unit placement, security group memberships, and possibly job-title or department attributes. The change cascades to Group Policy applicability (different OU may receive different policies), license entitlements (different groups may carry different application or access rights), and resource permissions (different groups may have different file share or application access).

A departure (leaver) workflow disables the user account in Active Directory (preserving the SID for reference), hides the user from the global address list in Exchange, removes the user from security groups, transfers ownership of files and resources, and eventually deletes the account after a retention window. Group membership cleanup is notoriously incomplete in many organizations, with departed users retaining membership in groups for years.

## User experience

The user experience in the legacy phase is anchored at the Windows logon screen. Ctrl+Alt+Del summons the Secure Attention Sequence (Microsoft's mechanism for preventing credential-capturing fake-logon overlays), the user enters domain credentials, the system authenticates against a domain controller, and the user profile loads. The profile may be local-only (created on each device the user signs in to, with no synchronization between devices), roaming (centrally stored on a file server and copied to the local device on each sign-in), or hybrid using folder redirection plus offline files.

Once signed in, the user sees mapped network drives (delivered through Group Policy Preferences), default browser configuration including security zones and proxy settings (also delivered through Group Policy), and the standard application set (deployed through Configuration Manager). Outlook auto-configures from Active Directory attributes that point at the user's Exchange mailbox. Internal web applications often support Kerberos single sign-on through Internet Explorer integrated authentication (deprecated in Edge but supported by Edge's Internet Explorer Mode).

Remote work uses either a virtual private network connection to a corporate gateway or, in mature deployments, DirectAccess (which provides transparent intranet access without requiring the user to initiate a connection). Both mechanisms extend the corporate perimeter to the remote device for the duration of the connection.

## Operational profile

The information technology organization required to operate a legacy estate is substantial. Domain administrators (a security-critical role with broad-reaching privilege) manage the directory itself, the trust relationships, the domain controller infrastructure, and the related DNS and replication topology. Configuration Manager administrators manage the application catalog, task sequences, software update infrastructure, and reporting. Imaging technicians perform the device-by-device imaging work. Helpdesk (tier one and tier two) handles user-facing issues including password resets, Group Policy troubleshooting, certificate issues, and application installation failures. Server administrators handle the underlying infrastructure including domain controllers, file servers, Exchange servers, SharePoint servers, and the network equipment. A separate public-key-infrastructure administrator may manage Certificate Services.

Staffing for a legacy estate typically runs in the range of one information technology full-time equivalent per seventy-five to one hundred fifty end users, with significant variation depending on the complexity of the environment, the geographic distribution of staff, and the maturity of the operational processes. Larger organizations achieve better ratios through specialization and automation; smaller organizations often run worse ratios because they cannot specialize.

## Compliance and audit posture

Compliance evidence in the legacy phase is assembled from event logs, configuration reports, and ad-hoc queries. Active Directory event logs (on each domain controller) record authentication activity, account changes, and access to security-sensitive operations. File server event logs (if auditing is enabled) record access to monitored files and folders. Configuration Manager reports provide inventory and compliance data. Group Policy reports show which policies are applied to which devices. Certificate Services logs record certificate issuance and revocation.

Audit response typically requires manual assembly of evidence from multiple sources, often performed under deadline pressure during an audit window. Compliance frameworks (Sarbanes-Oxley, the Health Insurance Portability and Accountability Act, the Payment Card Industry Data Security Standard, federal frameworks such as the National Institute of Standards and Technology 800-53) map to specific Group Policy settings, security configurations, and operational procedures that must be demonstrably in place.

Continuous compliance — the property of being able to demonstrate at any moment that the estate is in compliance with policy — is largely aspirational in the legacy phase. The audit evidence is point-in-time, assembled retrospectively, and dependent on the operational logs being preserved and accessible.

## Strengths

The legacy model has genuine strengths that explain its long dominance. The configuration surface available through Group Policy is the most granular and well-documented in enterprise computing. The supporting ecosystem of administrative tools, third-party integrations, training, certifications, and community knowledge is vast. The trust boundaries are simple to reason about: a device inside the perimeter is trusted, a device outside the perimeter is not. The failure modes are well understood and well documented. The model has been operationally proven for two decades.

For organizations with a stable physical premises, a workforce co-located with corporate infrastructure, and a relatively small inventory of cloud-resident resources, the legacy model continues to perform well. Replacing it for the sake of modernization, without a concrete operational driver, is a defensible decision to defer.

## Weaknesses

The weaknesses of the legacy model become acute when its assumptions begin to fail. A workforce that is geographically distributed, mobile, or working from home strains the implicit assumption of network proximity to domain controllers. Devices that spend long periods disconnected from corporate networks drift out of policy alignment because Group Policy refresh depends on directory reachability. The on-premises infrastructure that supports the legacy model — domain controllers, Configuration Manager, file servers, Exchange, SharePoint, certificate authorities — represents substantial capital and operational expense that the cloud-native models gradually replace.

Cloud-resident services and applications cannot consume Kerberos tickets issued by on-premises directories without explicit federation, which is operationally complex to maintain. Mobile devices (smartphones and tablets) are largely outside the legacy model's scope, requiring either a separate mobile device management plane or no enterprise governance at all. Compliance posture is point-in-time rather than continuous. Imaging pipelines are bottlenecks for hardware refresh cycles. The credential-theft attack surface, particularly the in-memory caching of credentials by the Local Security Authority Subsystem Service, is well-known and difficult to fully mitigate in the legacy model.

## Common failure modes

The legacy model has a characteristic set of failure modes. Stale computer objects accumulate as devices are retired without being removed from the directory, eventually numbering in the hundreds or thousands of dormant records that complicate inventory, compliance, and security work. Trust relationships break when a device's cached machine credential diverges from the directory-stored credential, typically because the device has been offline for longer than the machine password rotation interval; the symptom is the user being unable to sign in to the device with a domain account, with the resolution requiring rejoining the domain. Group Policy replication lag between domain controllers, particularly across sites, causes inconsistent application of recently-modified policies. Windows Management Instrumentation corruption on a device prevents Group Policy from evaluating correctly and prevents Configuration Manager inventory from collecting; the resolution typically involves rebuilding the WMI repository, which is operationally non-trivial.

Time skew between a device and the domain controller infrastructure breaks Kerberos authentication; the protocol requires the device clock to be within five minutes of the domain controller, and devices that have lost time synchronization (typically through a depleted CMOS battery) cannot authenticate until time is corrected. Certificate expiry, particularly for machine certificates used in Wi-Fi authentication, can cause widespread connectivity failures on the expiry date if renewal has not occurred. Domain controller unavailability in a small office or branch location causes complete loss of authentication for that location until connectivity is restored or a local domain controller is brought up.

## Migration triggers

Organizations begin moving out of the legacy phase in response to specific triggers rather than as a general modernization initiative. The most common triggers include the adoption of Microsoft 365 (which introduces cloud identity requirements that pull users out of pure on-premises identity), the acquisition of cloud-resident software-as-a-service applications that cannot federate cleanly with on-premises identity, the geographic distribution of the workforce (which strains the assumption of network proximity to domain controllers), the proliferation of mobile devices that require management, hardware refresh cycles that prompt re-evaluation of imaging workflows, audit findings that highlight compliance posture gaps, and security incidents that expose the credential-theft attack surface or the broader weaknesses of perimeter-based trust.

Once one or more of these triggers becomes operationally significant, the organization enters the early transition phase described in the next document in this series.

## References

The legacy phase is documented exhaustively in Microsoft's product documentation and in third-party references. The most authoritative starting points are Microsoft Learn's Active Directory Domain Services documentation, the Group Policy documentation, the Microsoft Configuration Manager documentation, and the Active Directory Certificate Services documentation. The Microsoft Security Compliance Toolkit provides the canonical security baselines for Windows in this model. Third-party references include Brian Desmond, Joe Richards, Robbie Allen, and Alistair Lowe-Norris's *Active Directory* (5th edition, O'Reilly Media), Jeremy Moskowitz's *Group Policy: Fundamentals, Security, and the Managed Desktop* (Sybex), and the Microsoft Press *Mastering Windows Server* series.
