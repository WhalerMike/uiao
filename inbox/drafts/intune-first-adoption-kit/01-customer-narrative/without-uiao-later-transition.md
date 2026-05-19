# Phase III — Later Transition: A Detailed Reference for Hybrid Microsoft Entra Join and Intune Co-Management

## Scope and definition

The later transition phase of Windows endpoint governance is defined by the extension of device identity into the cloud directory through Hybrid Microsoft Entra Join, the introduction of Microsoft Intune as a parallel device-management plane to Microsoft Configuration Manager, and the operationally complex period during which both planes operate simultaneously under co-management. A device in this phase has two identities (an Active Directory computer object and a Microsoft Entra ID device object) that are linked through directory synchronization, and is governed by two management planes (Configuration Manager and Intune) whose responsibilities are partitioned through configurable workload sliders. The user's experience is largely unchanged from the early transition phase, but the device-side architecture has become considerably more sophisticated.

This phase is the operationally most expensive phase of the entire modernization journey, because it preserves the entire on-premises infrastructure of the legacy phase, retains all of the cloud-identity-and-services infrastructure of the early transition phase, and adds the hybrid join machinery, the Intune service surface, the co-management workload coordination, and the dual-policy reconciliation effort. Organizations enter this phase when they need device-aware Conditional Access (which requires the device to be hybrid Entra-joined or compliant via Intune), and they leave it when they have either retired the on-premises management plane entirely or determined that they will do so on a clear timeline.

The hybrid model is positioned by Microsoft as a transition strategy rather than a permanent destination. The official guidance is to use hybrid join as a bridge from pure Active Directory Domain Join (Phase I) to pure Microsoft Entra Join (Phase IV), with Phase III being the necessary middle. Organizations that linger in Phase III indefinitely accumulate operational debt that becomes progressively harder to discharge.

## Architecture overview

The later transition architecture spans both on-premises and cloud planes, with bidirectional integration between them and parallel management planes operating on the same devices.

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
   +----------+------------+              +-------------+-------------+
              |                                         |
              |  Group Policy                           |  Automatic
              |  + Kerberos                             |  MDM
              |                                         |  Enrollment
              |                                         |
   +----------+------------+              +-------------+-------------+
   |                       |              |                           |
   |   Configuration       |   Workload   |   Microsoft Intune        |
   |   Manager             +<--Sliders--->+   (Policy, compliance,    |
   |   (Site server,       |              |    apps, baselines;       |
   |    Cloud Management   |              |    consumes hybrid        |
   |    Gateway, DP,       |              |    identity)              |
   |    SUP, App Catalog)  |              |                           |
   +----------+------------+              +-------------+-------------+
              |                                         |
              |                            +------------+--------------+
              |                            |  Conditional Access       |
              |                            |  (now device-aware:       |
              |                            |   can require hybrid      |
              |                            |   join AND/OR Intune      |
              |                            |   compliance)             |
              |                            +------------+--------------+
              |                                         |
              |                            +------------+--------------+
              |                            |  Microsoft Defender for   |
              |                            |  Endpoint, Intune         |
              |                            |  reporting, Endpoint      |
              |                            |  Analytics                |
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

The device in this phase is co-managed: it has a Configuration Manager client (continuing from the legacy phase) and is enrolled in Intune (new in this phase). Each of the two managers is authoritative for a defined set of workload domains, configurable through Configuration Manager's co-management workload sliders.

## Hybrid Microsoft Entra Join

Hybrid Microsoft Entra Join is the mechanism by which a domain-joined device additionally registers itself in Microsoft Entra ID, creating a device object in the cloud directory linked to the on-premises computer object. The join requires Microsoft Entra Connect to be synchronizing the computer's organizational unit (a configuration option in Entra Connect), and it requires the Service Connection Point (SCP) to be configured in the on-premises directory's configuration partition.

The Service Connection Point is a specially-named object in the on-premises directory's configuration container. Its `keywords` attribute holds two strings: `azureADName:<tenant-name>` and `azureADId:<tenant-guid>`. These strings tell domain-joined devices which Microsoft Entra tenant to register against. The SCP is typically created by Microsoft Entra Connect during its initial configuration; it can also be created manually using the `Initialize-ADSyncDomainJoinedComputerSync` cmdlet or by editing the directory directly with the `Adsiedit` tool.

The hybrid join handshake is initiated by a scheduled task on each domain-joined device, named "Automatic-Device-Join" under the `\Microsoft\Windows\Workplace Join\` task path. The task runs at logon and at recurring intervals; on each run, it consults the SCP, retrieves the tenant identifier, and attempts to register the device with Entra ID. The registration request includes proof of the device's identity in the on-premises directory (a certificate or a signed token derived from the machine credential), and is validated by Entra ID against the synchronized computer object. On successful registration, the device receives a cloud device certificate, the device object in Entra ID is marked as joined (state: Microsoft Entra hybrid joined), and the device becomes eligible for cloud-aware policies and automatic Intune enrollment.

Hybrid join is sensitive to several preconditions. The on-premises computer object must be synchronized to Entra ID and the synchronization must be complete (which can take up to thirty minutes after a new computer is joined to the domain). The device must be able to reach `enterpriseregistration.windows.net` and `login.microsoftonline.com` on port 443 (which fails under restrictive corporate proxy or firewall configurations). The device's clock must be within five minutes of the Entra service (which fails for devices with depleted CMOS batteries or recently restored from images with bad time configuration). The SCP must point to the intended tenant (which fails when an organization has multiple tenants and the SCP was configured for the wrong one). When any of these preconditions fails, the hybrid join attempt fails silently and the device remains domain-joined-only.

The silent failure mode is a defining characteristic of the later transition phase's operational complexity. A device that has failed to complete hybrid join continues to function as a domain-joined device, the user signs in successfully, applications work normally, and there is no user-visible indication that anything is wrong — until the user attempts to access a Conditional Access-protected resource that requires hybrid join, at which point access is denied. The denial may occur weeks or months after the underlying join failure, making root-cause analysis non-trivial.

## Microsoft Intune introduction

Microsoft Intune is the cloud-resident mobile device management and mobile application management service that handles policy, compliance, applications, and updates for devices enrolled into it. Intune accepts enrollment from Windows, macOS, iOS/iPadOS, Android, and Linux devices, with capability varying by platform. For Windows devices in the later transition phase, Intune is introduced as a co-management partner to Configuration Manager.

A hybrid-joined device becomes enrolled in Intune through automatic MDM enrollment, triggered by Group Policy (the policy is named "Enable automatic MDM enrollment using default Azure AD credentials" and is found under Computer Configuration > Administrative Templates > Windows Components > MDM). When the policy is applied, the device's MDM enrollment subsystem contacts Intune's enrollment endpoint, presents proof of the hybrid join, and enrolls. After enrollment, the device receives a configuration source service URL (the MDM URL visible in `dsregcmd /status`) and begins polling Intune for policy.

Intune policies are defined in the Microsoft Intune admin center and target Microsoft Entra ID security groups (or, for device-side policies, device groups). Each policy is a discrete object: a compliance policy defining what makes a device compliant, a configuration profile defining configuration settings to apply, a security baseline defining a coordinated set of security settings (typically derived from Microsoft's security baselines), an app deployment defining an application to install or make available, or one of several other policy types. Policy assignment is by group membership; policies do not have organizational unit equivalents in Intune.

## Co-management workloads

Co-management partitions device-management responsibility between Configuration Manager and Intune through a set of workload sliders. Each slider controls one workload domain and can be set to "Configuration Manager" (legacy plane is authoritative), "Pilot Intune" (a designated pilot collection receives the workload from Intune while the rest remains on Configuration Manager), or "Intune" (cloud plane is authoritative).

The workload domains are: Compliance policies (which defines what makes a device compliant for Conditional Access purposes); Resource access policies (Wi-Fi, VPN, certificate profiles); Device configuration (general configuration settings such as restrictions and customizations); Windows Update policies (Windows Update for Business deferral, deadlines, ring assignments); Endpoint Protection (Microsoft Defender Antivirus, Microsoft Defender SmartScreen, Microsoft Defender Application Control); Client apps (application deployment and management); Office Click-to-Run apps (Microsoft 365 Apps deployment); Microsoft Defender for Endpoint integration.

Each workload slider is independent. An organization can move Compliance policies to Intune immediately (to enable device-aware Conditional Access), keep Client apps on Configuration Manager indefinitely (because the application catalog is mature in Configuration Manager and migration is expensive), and treat Windows Update policies as a pilot for one cohort of devices while the rest continues on Configuration Manager.

The intent of the workload sliders is to allow staged migration with the ability to roll back individual workloads if operational problems emerge. The reality is more complicated: once a workload moves to Intune, the Configuration Manager-side configuration for that workload becomes inert but is not removed automatically, creating ambient configuration drift that complicates eventual full cutover. Organizations that move workloads to Intune typically need a parallel cleanup project on the Configuration Manager side to retire the corresponding policies and applications.

## The five-system identity reconciliation problem

A device in the later transition phase can appear in five distinct records, each with its own identifier and lifecycle. The Active Directory computer object in the on-premises directory is the on-premises identity. The Microsoft Entra ID device object in the cloud directory is the cloud identity, linked to the on-premises computer object through the hybrid join. The Microsoft Intune managed device record in the Intune service is the management identity, linked to the Entra device object through enrollment. The Microsoft Configuration Manager client record in the Configuration Manager database is the legacy management identity, linked to the Active Directory computer object through the client agent's registration. The Windows Autopilot device record (if the device is registered with Autopilot, which is uncommon in the later transition phase but possible) is the provisioning identity, linked to the device's hardware hash.

Each of these five records can change independently. A device can be reset and re-imaged without removing the prior records, producing duplicates. A device can be migrated between organizational units without its Configuration Manager collection membership updating. A device can have its Entra ID device object deleted manually without the on-premises computer object being affected. Each disagreement between the records is a potential compliance and Conditional Access hazard, because policies may evaluate against a different record than the one driving the device's actual behavior.

Reconciliation across the five records is one of the under-appreciated operational costs of the later transition phase. Tooling support for the reconciliation is limited: the Microsoft Entra admin center shows the device objects but not their links to the on-premises records; Configuration Manager shows its client records but not their links to the Entra device objects; Intune shows enrolled devices but not directly the underlying Configuration Manager or Active Directory records. Engineers performing reconciliation typically write PowerShell scripts that query multiple endpoints (Microsoft Graph for Entra and Intune, WMI or the Configuration Manager admin service for Configuration Manager, Active Directory cmdlets for the directory) and join the results by serial number, device name, and hardware hash.

## Conditional Access maturation

Conditional Access in the later transition phase becomes substantially more sophisticated than in the early transition phase, because device signals are now available. The new conditions available include "Require device to be marked as compliant" (which evaluates the Intune compliance state) and "Require Microsoft Entra hybrid joined device" (which evaluates the hybrid join state). Together they allow Conditional Access policies that require the user to be signing in from a managed corporate device, dramatically reducing the attack surface for credential-stuffing and adversary-in-the-middle attacks.

The policy set typically expands during this phase. The legacy-authentication blocks from the early transition phase remain. Multi-factor authentication requirements remain. New policies appear that require device compliance for sensitive applications (the Microsoft 365 services themselves, the Azure portal, internal SaaS applications). Administrative roles receive stricter policies that require both multi-factor authentication and compliant devices. Risk-based policies (using Microsoft Entra ID Protection signals) may be introduced to add adaptive controls.

The staged rollout discipline for Conditional Access (see the conditional-access-rollout-playbook artifact in this kit) becomes more important during this phase because the new policies have higher blast radius than the early transition phase's user-side-only policies.

## Compliance policies

A compliance policy in Microsoft Intune is a definition of what makes a device acceptable for access purposes. Common compliance criteria include: minimum operating system version (e.g., Windows 10 22H2 or later); BitLocker enabled; Secure Boot enabled; Trusted Platform Module present and active; Microsoft Defender Antivirus active and signatures current; Microsoft Defender SmartScreen enabled; device not jailbroken or rooted (for mobile platforms); password policy (length, complexity, history); machine risk score below a threshold (when Microsoft Defender for Endpoint is integrated).

The compliance policy is evaluated on the device by the Intune Management Extension, with the evaluation result reported back to Intune and made available to Conditional Access. A device that fails compliance is marked as non-compliant, and any Conditional Access policy requiring compliance will deny that device's sign-ins until compliance is restored.

Compliance policies do not enforce settings — they only evaluate them. A separate configuration profile or security baseline is needed to actually set the configuration. The pattern is: a security baseline sets BitLocker to enabled, a compliance policy evaluates whether BitLocker is actually enabled, and a Conditional Access policy denies access if the compliance evaluation fails. The three are independent: a misconfigured compliance policy can mark devices non-compliant even when they are configured correctly, and an enforced configuration profile does not automatically generate compliance signals.

## Operational profile at peak complexity

The information technology organization required to operate the later transition phase is the largest of any phase. The legacy infrastructure remains in service: domain controllers, Configuration Manager, file servers, certificate authorities, on-premises Exchange in some cases, on-premises SharePoint in some cases. The cloud infrastructure remains in service: Microsoft Entra ID administration, Microsoft 365 service administration, Conditional Access policy management. The hybrid integration requires Entra Connect operations, SCP management, and hybrid join monitoring. The Intune introduction requires policy authoring (compliance policies, configuration profiles, security baselines, app deployments), workload slider planning, Intune Management Extension troubleshooting, and Endpoint Analytics review. The reconciliation across five identity systems requires custom tooling and engineering judgment.

Staffing in this phase typically grows by ten to twenty percent compared to the legacy phase, with the growth concentrated in identity engineering and modern endpoint management. Cost in this phase is at its peak: licensing for Microsoft 365 and Intune, retention of all on-premises infrastructure, increased engineering staffing, and (often) consulting engagements to support the migration planning.

The duration of the later transition phase varies widely. Organizations with strong project discipline and tolerance for change move through this phase in twelve to twenty-four months. Organizations without project discipline can spend three to five years in this phase, accumulating operational debt that compounds. The total cost of the modernization effort is largely determined by the duration of Phase III.

## Failure modes characteristic of the later transition

Several failure modes are characteristic of this phase. Silent hybrid join failures, described earlier, are the most operationally consequential. Conditional Access policies that require both hybrid join and Intune compliance can deny access to devices that have one but not the other, with the diagnosis non-trivial because the sign-in log only indicates which policy failed, not which condition within the policy.

Duplicate device objects in Microsoft Entra ID accumulate as devices are reset, re-imaged, or re-joined without proper retirement of the prior object. Cleanup typically requires manual deletion or scripted reconciliation, and missed cleanups produce a long tail of stale objects that complicate reporting and compliance.

Workload slider transitions that move a workload from Configuration Manager to Intune without removing the corresponding Configuration Manager configuration produce ambient conflicts. The symptom is that the Intune-side configuration applies but the Configuration Manager-side configuration also continues to deliver, sometimes with different values, with the resulting behavior dependent on which provider last wrote to the underlying registry location.

Intune Management Extension failures (the agent that handles Win32 app installation, PowerShell script execution, and several other capabilities) cause apps to fail to install and scripts to fail to run. Diagnosis requires inspecting the IntuneManagementExtension.log and AgentExecutor.log files in `C:\ProgramData\Microsoft\IntuneManagementExtension\Logs`.

Microsoft Entra Connect lag, when a newly-created computer object has not yet synchronized to Entra ID at the moment the device first attempts hybrid join, causes the join to fail. The remediation is to wait for the next synchronization cycle and retry, but the user experience in the meantime is degraded.

## Migration triggers

Organizations move out of the later transition phase by completing the migration of all workloads to Intune (terminating co-management for new devices), retiring or pilot-converting the Configuration Manager infrastructure to Cloud Management Gateway mode, and transitioning new device acquisitions to Microsoft Entra Join (Phase IV) rather than hybrid join. The trigger for the move is typically the operational cost of maintaining the dual infrastructure becoming intolerable, or a strategic decision to commit to the cloud-native architecture by a specified date.

Hybrid-joined devices may continue to exist for years after new acquisitions are Phase IV, as the existing population is gradually retired through hardware refresh. The organization can be in Phase IV for new devices while still operating Phase III equipment for the installed base.

## References

Authoritative documentation includes Microsoft's hybrid Microsoft Entra Join planning guidance at Microsoft Learn (the "Plan your hybrid Microsoft Entra join implementation" article and the connected configuration and troubleshooting articles); the Microsoft Intune co-management overview and workload guidance; the Service Connection Point documentation in the Microsoft Entra Connect references; the Conditional Access planning and policy-authoring documentation including the device-aware conditions; and the Microsoft Defender for Endpoint integration documentation. The Intune Management Extension logs and diagnostic guidance are documented separately in the Intune troubleshooting section of Microsoft Learn. Microsoft's "Cloud Adoption Framework" includes scenario-based guidance for the later transition phase that is useful for migration planning.
