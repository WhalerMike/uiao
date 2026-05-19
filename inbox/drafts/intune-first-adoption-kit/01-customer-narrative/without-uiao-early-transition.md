# Phase II — Early Transition: A Detailed Reference for Cloud Identity Adoption with On-Premises Device Governance

## Scope and definition

The early transition phase of Windows endpoint governance is defined by an architectural asymmetry: user identity has been extended into the cloud through Microsoft Entra ID (formerly Azure Active Directory) for purposes of accessing cloud-resident applications, while device identity, device configuration, and device governance remain entirely anchored in on-premises Active Directory. Users authenticate to cloud applications using cloud-aware credentials derived from their on-premises identity through directory synchronization. Devices continue to be imaged, joined to the on-premises domain, governed by Group Policy, supplied with applications by Microsoft Configuration Manager, and patched by the on-premises patching infrastructure. The cloud has touched the user, the mailbox, the document library, and the collaboration platform, but it has not touched the endpoint itself.

This phase is the phase in which most enterprises spent the late 2010s, and in which many enterprises continue to operate today. It is the natural consequence of adopting Microsoft 365 without simultaneously committing to a device management transformation. The architectural commitment is partial, the operational cost increases (because both on-premises and cloud infrastructure must be maintained), and the governance posture for devices is unchanged from the legacy phase. What changes is the user-facing surface: where the user previously interacted exclusively with on-premises Exchange, on-premises SharePoint, on-premises Lync or Skype for Business, and on-premises file shares, the user now interacts with Exchange Online, SharePoint Online, Microsoft Teams, and OneDrive for Business, with the on-premises services either retired or running in parallel during migration.

## Architecture overview

The early transition architecture spans two planes: on-premises and cloud. The on-premises plane is largely unchanged from the legacy phase. The cloud plane introduces new components that consume synchronized identity and serve cloud-resident applications.

```
        ON-PREMISES                              MICROSOFT CLOUD
   +-----------------------+               +---------------------------+
   |                       |               |                           |
   |   Active Directory    |               |   Microsoft Entra ID      |
   |   Domain Controllers  |               |   (User identity,         |
   |   (Computer object,   |               |    group membership,      |
   |    user object,       +--Entra ID---->+    token issuance for     |
   |    Group Policy,      |   Connect     |    cloud apps;            |
   |    Kerberos KDC)      |   Sync        |    NO device object       |
   |                       |               |    in this phase)         |
   +----------+------------+               +-------------+-------------+
              |                                          |
              |  Group Policy                            |  OAuth 2.0
              |  + Kerberos                              |  SAML 2.0
              |                                          |  OpenID Connect
              |                                          |
              |                            +-------------+-------------+
              |                            |                           |
              |                            |   Microsoft 365 services  |
              |                            |   - Exchange Online       |
              |                            |   - SharePoint Online     |
              |                            |   - OneDrive for Business |
              |                            |   - Microsoft Teams       |
              |                            |   - Microsoft Defender    |
              |                            |     for Office 365        |
              |                            +-------------+-------------+
              |                                          |
              |                            +-------------+-------------+
              |                            |   Conditional Access      |
              |                            |   (cloud-app scope:       |
              |                            |    MFA, location,         |
              |                            |    legacy auth blocking;  |
              |                            |    NO device-aware        |
              |                            |    conditions yet)        |
              |                            +-------------+-------------+
              |                                          |
              |                            +-------------+-------------+
              |                            |   Third-party SaaS        |
              |                            |   (SAML-federated to      |
              |                            |    Entra ID as IdP)       |
              |                            +-------------+-------------+
              |                                          |
   +----------+--------------------------------------+   |
   |                                                 |   |
   |    Domain-Joined Endpoint                       |   |
   |    (Imaged, AD-joined, GPO-governed,            +<--+
   |     ConfigMgr-managed; user signs in            |
   |     with domain credentials; Office             |  Cloud
   |     clients obtain modern-auth tokens           |  token
   |     via seamless single sign-on; the            |  flow to
   |     device itself is invisible to Entra ID)     |  Office
   +-------------------------------------------------+  client
```

The architectural bridge between the two planes is Microsoft Entra Connect (formerly Azure Active Directory Connect), which runs on a domain-joined server inside the on-premises network and synchronizes selected directory objects to the cloud tenant. The synchronization is configured through the Entra Connect installation wizard and the Microsoft Entra Connect Synchronization Service Manager. Synchronization occurs on a default thirty-minute cycle for incremental changes; full synchronization runs less frequently.

## Microsoft Entra Connect

Entra Connect is a complex piece of software with several deployment topologies. The simplest is a single Entra Connect server with a SQL Express database, sufficient for tenants up to approximately one hundred thousand objects. Larger deployments use Entra Connect with a SQL Server database (Standard or Enterprise edition) and may run a secondary Entra Connect server in staging mode for high availability.

The synchronization scope is configurable. Most deployments synchronize all user objects, security groups, contacts, and certain attributes. Computer objects can be synchronized but typically are not in the early transition phase, because there is no device-side feature that would benefit from their presence in the cloud directory until hybrid Entra Join is introduced in the later transition phase.

Authentication options for the synchronized identities are configurable through Entra Connect. Password Hash Synchronization, the default and recommended option, synchronizes a salted hash of the user's password (specifically, a hash of the on-premises hash, not the password itself) to the cloud directory, allowing the cloud directory to authenticate the user directly without forwarding the request back to the on-premises directory. Pass-Through Authentication uses lightweight agents installed on domain-joined servers to forward authentication requests from the cloud directory back to an on-premises domain controller for validation. Federated authentication using Active Directory Federation Services or a third-party federation provider keeps the authentication mechanism on premises while the cloud directory issues tokens after the federation handshake. Password Hash Synchronization is the simplest, most resilient, and most widely deployed option in modern environments; federated authentication is the most complex and has been progressively deprecated in Microsoft's recommended architectures.

Entra Connect health and performance monitoring is provided through the Microsoft Entra Connect Health service, which collects telemetry from the Entra Connect servers and presents it in the Microsoft Entra admin center. Common health issues include synchronization errors (typically caused by duplicate proxy addresses, invalid UPN formats, or attribute size limits), staging-mode misconfigurations, certificate expiry, and connectivity issues to the cloud endpoints.

## Cloud identity establishment

Once Entra Connect is operational, the cloud directory begins to receive user identities, groups, and selected attributes from the on-premises directory. The synchronized identities are immediately available to cloud applications that integrate with Microsoft Entra ID for authentication.

The user's cloud identity carries the same user principal name as the on-premises identity (assuming the UPN is in a format that is also a verified domain in the tenant, which is the recommended configuration). The user's password (or rather, the cloud-stored hash) is kept in sync with the on-premises password, so a password change in either location propagates to the other (with a brief synchronization delay).

Group memberships are synchronized for groups marked in scope. Most security groups synchronize; distribution lists synchronize differently and may require Exchange-specific configuration. Dynamic groups in the cloud (whose membership is determined by attribute-based rules) can be defined natively in Microsoft Entra ID and do not require on-premises representation.

Roles in the cloud directory — Global Administrator, User Administrator, Conditional Access Administrator, and so on — are assigned in the cloud directory directly and are separate from on-premises Active Directory privileged group memberships such as Domain Admins. The separation is intentional and important: compromise of the on-premises directory does not directly grant cloud directory administrative access.

## Authentication mechanics in the cloud plane

Cloud applications authenticate users through one of several modern protocols. OpenID Connect (built on OAuth 2.0) is the predominant protocol for modern web and mobile applications and for the Microsoft 365 services themselves. Security Assertion Markup Language version 2 is the predominant protocol for older enterprise software-as-a-service applications that have not yet adopted OpenID Connect. WS-Federation persists in some legacy scenarios. OAuth 2.0 by itself (without OpenID Connect) is used for API-to-API authorization scenarios.

A user signing in to a cloud application is redirected to Microsoft Entra ID's sign-in endpoint (login.microsoftonline.com). The user presents credentials, which Entra ID validates against its synchronized password hash or forwards through pass-through authentication, depending on the configuration. After successful authentication, Entra ID returns an identity token (and optionally an access token) to the application, which uses the token to establish a session and authorize access.

Multi-factor authentication can be required by configuration. The factors supported include phone-based methods (SMS or voice call to a registered number), the Microsoft Authenticator application (push notification or time-based one-time password), hardware tokens implementing OATH-TOTP, FIDO2 security keys, and Windows Hello for Business. Multi-factor authentication can be required for all sign-ins, for sign-ins matching certain conditions (a Conditional Access policy that evaluates user, application, location, risk, and other signals), or only for specific privileged roles.

Modern authentication in Office clients (Outlook, Word, Excel, PowerPoint, Teams) uses the same OAuth 2.0 / OpenID Connect flows. The first sign-in prompts the user for credentials and possibly multi-factor authentication; subsequent sign-ins are typically silent because the client has cached refresh tokens that it exchanges for new access tokens as needed. Seamless single sign-on, configured in Entra Connect, enables the Office clients to silently authenticate domain-joined devices' users by exchanging Kerberos tickets for cloud tokens, eliminating even the first sign-in prompt for users on the corporate network.

## Conditional Access in the early transition

Conditional Access in the early transition phase is largely focused on user-side and sign-in-side conditions rather than device-side conditions, because device identity has not yet been extended into the cloud directory. The conditions available at this stage include user or group membership, application being accessed, sign-in location (geographic or IP-range), sign-in risk score (from Microsoft Entra ID Protection), user risk score, client application (browser vs. modern auth client vs. legacy auth client), and a small set of others.

Common Conditional Access policies in the early transition phase include blocking legacy authentication protocols (POP, IMAP, SMTP Basic, MAPI without modern auth, EWS Basic) because legacy authentication cannot be challenged for multi-factor and is the predominant vector for credential-stuffing attacks; requiring multi-factor authentication for all interactive sign-ins to cloud applications; blocking sign-ins from specific high-risk countries; requiring multi-factor authentication when the sign-in risk score is medium or higher; and requiring multi-factor authentication for administrative role members on every sign-in.

What Conditional Access cannot do in the early transition phase is require that a sign-in originate from a device that is compliant with corporate policy, because there is no device compliance signal flowing into Conditional Access yet. A device-aware Conditional Access posture requires the device to be hybrid Entra-joined or Entra-joined and enrolled in Microsoft Intune, neither of which occurs in the early transition phase.

## Microsoft 365 services adoption

The early transition phase is, for most organizations, the period during which Microsoft 365 services replace their on-premises predecessors. Exchange Online replaces on-premises Exchange Server; SharePoint Online replaces on-premises SharePoint Server; OneDrive for Business replaces personal file shares; Microsoft Teams replaces Skype for Business and (often) third-party chat platforms.

The migration mechanics vary by service. Exchange mailbox migration uses one of several mailbox-move strategies: cutover migration for small tenants moving entirely in a single window; staged migration for larger Exchange 2003 or 2007 tenants moving in phases; remote-move migration for Exchange 2010 and later in a hybrid configuration; and the IMAP-based migration for moving from non-Exchange systems. SharePoint migration uses the SharePoint Migration Tool, the Migration Manager service, or third-party tools (ShareGate, AvePoint Fly, others). OneDrive migration uses the same SharePoint migration tooling for the most part.

Throughout the migration window, both on-premises and cloud services may run in parallel, with users either accessing one or the other depending on whether their mailbox or files have moved. The dual operating environment is operationally complex and is one of the cost drivers of the early transition phase.

## Software-as-a-service federation

Cloud-resident software-as-a-service applications outside Microsoft 365 are integrated with Microsoft Entra ID through federation, typically using SAML 2.0. The Microsoft Entra Application Gallery contains pre-configured federation templates for thousands of common applications (Salesforce, Workday, Box, Zoom, and many others), reducing the setup work to entering tenant identifiers and uploading metadata. Custom applications require manual SAML configuration on both the application side and the Microsoft Entra side.

The user experience is that the user signs in to the application's URL, the application redirects to Microsoft Entra ID for authentication, the user authenticates (with multi-factor and Conditional Access evaluated as usual), and the application receives a SAML assertion that establishes the session. Single sign-on across multiple federated applications is automatic — once the user has authenticated to Entra ID for one application, subsequent applications skip the credential prompt.

## The device perspective in the early transition

Devices in the early transition phase are largely unchanged from the legacy phase. They are imaged, domain-joined, governed by Group Policy, supplied with applications by Configuration Manager, and patched by the existing patching infrastructure. The user signing in to the device uses domain credentials, receives a Kerberos ticket-granting ticket from a domain controller, and proceeds to the desktop. Office clients on the device prompt the user once to sign in to cloud applications (or sign in silently through seamless single sign-on), cache a refresh token, and operate against the cloud services for the rest of the session.

The device has no device object in Microsoft Entra ID. It is not subject to Conditional Access device-compliance evaluation. It does not appear in Microsoft Intune. It is not subject to mobile-device-management policies. The device's posture (encryption, patching, antimalware, configuration baseline) is governed entirely through Group Policy and Configuration Manager as in the legacy phase.

This is the source of the early transition phase's principal pain point: the cloud-aware user surface and the on-premises-only device surface cannot meaningfully interact in terms of access control. The organization can require multi-factor authentication, can block legacy authentication, and can challenge risk-elevated sign-ins, but it cannot require that the user signing in be using a managed device. A compromised personal device, properly authenticated by a stolen credential and any required multi-factor factor, will access cloud resources successfully.

## Operational profile

The operational profile of the early transition phase is the legacy operational profile plus the cloud operational profile, running in parallel. The on-premises infrastructure is unchanged: domain controllers, Configuration Manager, file servers, possibly Exchange and SharePoint and Lync/Skype servers, certificate authorities, and the related operational disciplines remain in service. The cloud infrastructure adds Microsoft Entra ID administration (identity team, often the same team that runs on-premises Active Directory), Microsoft Entra Connect operations (typically the identity team), Conditional Access policy authoring and review (the identity team plus security policy owners), multi-factor authentication enrollment (the identity team plus the helpdesk), and Microsoft 365 service administration (Exchange Online administrators, SharePoint Online administrators, Teams administrators, which may be the same humans who administered the on-premises predecessors but now using different tools).

Cost in this phase is at a transitional peak. The organization is paying for Microsoft 365 licenses, the existing on-premises infrastructure has not yet been retired (typically because migration is still in progress), and the human cost of operating both planes is significant. The cost curve flattens or declines only after the on-premises predecessors of Microsoft 365 services have been fully retired, which typically requires twelve to twenty-four months from the start of migration.

## Failure modes characteristic of the early transition

Several failure modes are characteristic of the early transition phase. Microsoft Entra Connect synchronization errors, particularly when the on-premises directory has accumulated objects with duplicate proxy addresses, invalid UPN formats, or other attribute conflicts, cause specific users to fail to synchronize and consequently fail to access cloud services. Resolution requires identifying and remediating the offending on-premises objects, with the changes flowing through on the next synchronization cycle.

Password hash synchronization failures, less common but more consequential, cause users to be unable to sign in to cloud applications even though they can sign in to domain-joined devices. The symptom is "wrong password" errors against cloud applications while domain logon works correctly. Resolution typically requires forcing a re-synchronization of the user's password hash through the Set-AzureADSyncPasswordHashSyncFeature operation or its equivalent in newer versions of the Entra Connect tooling.

Federation failures, in the smaller number of tenants still using Active Directory Federation Services, cause cloud sign-ins to fail when the federation service is unreachable, when the federation certificate expires, when the federation service load is excessive, or when the federation trust configuration drifts. The blast radius of federation failure is the entire workforce's access to cloud services, making federation operationally more dangerous than the alternatives.

Conditional Access misconfiguration is a high-blast-radius failure mode. A policy that targets too broadly, blocks too aggressively, or fails to exclude break-glass accounts can deny all administrators access to the tenant, requiring break-glass account use to recover. Conditional Access rollout discipline (see the conditional-access-rollout-playbook artifact in this kit) exists specifically to prevent this failure mode.

Modern authentication client failures, particularly for older Office clients that have not been updated to support OAuth 2.0, cause specific clients to fall back to legacy authentication. If legacy authentication is blocked, the client cannot connect. Resolution requires updating the client to a version that supports modern authentication.

## Migration triggers

Organizations move out of the early transition phase when the asymmetry between cloud users and on-premises devices becomes operationally unacceptable. The most common trigger is the security team's recognition that Conditional Access policies are weaker than they should be because device compliance cannot be required. A second common trigger is the introduction of new categories of mobile devices (corporate-issued tablets, knowledge-worker laptops not on the corporate network, contractor-owned devices) that the legacy device management plane cannot govern. A third is the operational cost of running both planes indefinitely.

The natural next step is the later transition phase, in which device identity is extended into the cloud directory through hybrid Entra Join and Microsoft Intune co-management is introduced. The later transition phase preserves the on-premises device infrastructure while adding the cloud device-management plane in parallel, with workload-by-workload migration of responsibilities from Configuration Manager to Intune.

## References

Authoritative documentation for the early transition phase includes Microsoft Entra Connect installation and configuration guidance at Microsoft Learn (specifically, the "What is Microsoft Entra Connect" landing page and the connected articles on installation, synchronization, password hash sync, and pass-through authentication); the Microsoft 365 deployment guidance for Exchange Online, SharePoint Online, and Teams; the Conditional Access overview and policy-authoring guidance; the multi-factor authentication deployment guidance; and the Microsoft Entra ID administration documentation. Brian Desmond's *Microsoft 365 Identity and Services* (Microsoft Press) is a comprehensive reference. Microsoft FastTrack provides deployment-assistance services for Microsoft 365 customers and publishes detailed deployment playbooks for the Microsoft 365 services.
