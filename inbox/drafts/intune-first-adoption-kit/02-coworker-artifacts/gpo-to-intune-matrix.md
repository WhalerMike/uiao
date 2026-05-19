# Group Policy to Microsoft Intune Settings Translation Matrix

**Audience:** Desktop engineering, security policy owners, and identity
engineers migrating Group Policy-delivered configuration to Microsoft
Intune.

**Purpose:** This matrix maps common Group Policy settings to their
Microsoft Intune equivalents, indicates whether each setting maps
cleanly, and notes what to do when it does not. It is intended as a
working reference during migration of a configuration baseline from
Group Policy delivery to Intune delivery.

**Scope:** Windows 10 and Windows 11 endpoints. Settings exclusive to
legacy Windows versions (7, 8.x) are excluded. Configuration that is
exclusively cloud-native (Microsoft Entra ID Conditional Access, Microsoft
365 application controls) is also excluded; this document covers the
workstation configuration surface, not the cloud-identity surface.

**How to use this matrix:** For each Group Policy setting in scope for
migration, locate the row in the table below. The "Intune equivalent"
column identifies the Intune mechanism (built-in template, security
baseline, settings catalog, custom OMA-URI, or ADMX ingestion). The
"Maps cleanly?" column indicates whether the migration is direct or
requires remediation. The "Notes" column describes considerations.

---

## Authoritative reference

Microsoft maintains a comprehensive policy CSP reference documenting
every Configuration Service Provider node that can be addressed through
Mobile Device Management. When in doubt about whether a specific setting
is addressable, consult the policy CSP reference¹ before assuming a gap.

The Microsoft security baselines for Windows are available both as
Group Policy Objects (via the Security Compliance Toolkit) and as Intune
configuration profiles (under *Endpoint security > Security baselines*).
For the majority of security-baseline content, the two are equivalent
and the migration is a profile-import operation rather than a per-
setting translation.

---

## Security baselines and core security policy

| Group Policy area | Intune equivalent | Maps cleanly? | Notes |
|---|---|---|---|
| Microsoft Security Baseline (Computer) | Intune Security Baseline (under Endpoint security) | Yes | Direct mapping; import the latest baseline version published by Microsoft |
| CIS Benchmark | Settings Catalog or custom configuration profile | Mostly | Most CIS items are CSP-addressable; gaps require custom OMA-URI or ADMX ingestion |
| User Rights Assignment | Settings Catalog under "User Rights" | Yes | Each right (LogonAsService, BackupPrivilege, etc.) is a separate setting |
| Local Security Policy / Local Policies | Settings Catalog under "Local Policies Security Options" | Yes | Most settings translate; a few require custom OMA-URI |
| Account Lockout Policy | Settings Catalog under "Account Policies Account Lockout" | Yes | Threshold, duration, observation window all available |
| Password Policy (domain-based) | Microsoft Entra ID password protection (cloud) plus local Account Policies | Partial | Domain password policy is set at the AD domain level for AD-joined devices; for Entra-joined devices, use Entra password protection |
| Audit Policy / Advanced Audit Policy | Settings Catalog under "Audit" categories | Yes | All audit subcategories addressable |

## BitLocker

| Group Policy area | Intune equivalent | Maps cleanly? | Notes |
|---|---|---|---|
| BitLocker Drive Encryption (Administrative Templates) | Endpoint security > Disk encryption > BitLocker | Yes | Direct mapping; Intune additionally manages recovery key escrow to Microsoft Entra ID |
| BitLocker recovery key storage | Microsoft Entra ID (automatic for Entra-joined devices) | Yes | Keys escrow to the Entra ID device object; visible to admins under *Devices > BitLocker keys* |
| TPM management | Endpoint security > Disk encryption > BitLocker (TPM-related settings) | Yes | TPM PIN, startup key, etc., all available |

## Microsoft Defender and endpoint security

| Group Policy area | Intune equivalent | Maps cleanly? | Notes |
|---|---|---|---|
| Microsoft Defender Antivirus | Endpoint security > Antivirus | Yes | Full feature parity for current Windows versions |
| Microsoft Defender Firewall | Endpoint security > Firewall | Yes | Rules and profiles addressable |
| Attack Surface Reduction rules | Endpoint security > Attack surface reduction | Yes | All ASR rules addressable; Audit/Block modes per rule |
| Microsoft Defender SmartScreen | Settings Catalog or Endpoint security > Web protection | Yes | Browser and Explorer SmartScreen both available |
| Microsoft Defender Application Control (WDAC) | Endpoint security > Account protection (Application control) | Partial | Basic policies straightforward; complex WDAC policies require XML import |
| Exploit Protection | Endpoint security > Attack surface reduction (Exploit protection) | Yes | XML import for custom policies |

## Windows Update

| Group Policy area | Intune equivalent | Maps cleanly? | Notes |
|---|---|---|---|
| Windows Update for Business policies | Devices > Update rings for Windows 10 and later | Yes | Deferral, pause, deadline all available; reporting in Intune is more comprehensive than on-premises WSUS |
| Feature update deployment | Devices > Feature updates for Windows 10 and later | Yes | Specific version targeting available |
| Quality update deployment | Devices > Quality updates for Windows 10 and later | Yes | Expedited updates supported |
| Driver update controls | Devices > Driver updates for Windows 10 and later | Yes | Driver inventory and approval workflow available |

## Windows Hello for Business and authentication

| Group Policy area | Intune equivalent | Maps cleanly? | Notes |
|---|---|---|---|
| Windows Hello for Business policies | Devices > Configuration > Identity protection template | Yes | PIN complexity, biometrics, TPM requirement all available |
| Smart card removal behavior | Settings Catalog under "Smart Card" | Yes | Behavior settings addressable |
| Credential Guard / Credential Manager | Endpoint security > Account protection | Yes | Credential Guard activation, LSA protection available |

## User experience and restrictions

| Group Policy area | Intune equivalent | Maps cleanly? | Notes |
|---|---|---|---|
| Removable storage access | Settings Catalog under "Removable Storage Access" | Yes | Per-class deny/allow available |
| Control Panel / Settings restrictions | Settings Catalog under "Control Panel" | Mostly | Most page restrictions available; a few legacy items have no CSP node |
| Start Menu / Taskbar layout | Configuration profile > Device restrictions (Start) | Yes | XML import for custom layouts |
| Lock screen image | Configuration profile > Device restrictions (Locked screen experience) | Yes | URL or device-local image |
| Desktop wallpaper | Settings Catalog under "Desktop" | Yes | URL or local path |
| Internet Explorer Maintenance | Largely deprecated; Microsoft Edge IE Mode policies replace it | Limited | IE itself is end-of-support; the modern policy target is Microsoft Edge |
| Folder redirection | Settings Catalog under "Folder Redirection" or OneDrive Known Folder Move | Partial | Traditional redirection works but OneDrive Known Folder Move is the cloud-native replacement |

## Drive and resource mappings (Group Policy Preferences)

| Group Policy area | Intune equivalent | Maps cleanly? | Notes |
|---|---|---|---|
| Drive mappings (GPP) | PowerShell script via Intune, or transition to cloud storage | No clean CSP | No native CSP for drive mappings; deliver a PowerShell script or migrate users to SharePoint/OneDrive |
| Printer deployment (GPP) | Microsoft Universal Print, or Intune-delivered driver plus script | No clean CSP | Universal Print is the cloud-native replacement; for legacy print servers, use a PowerShell deployment |
| Logon and startup scripts | Intune > Devices > Scripts (PowerShell), or packaged as a Win32 app | Yes | PowerShell scripts run in SYSTEM by default; user-context scripts run via Intune Management Extension |
| Scheduled tasks (GPP) | PowerShell script that calls New-ScheduledTask, delivered as Intune script | No clean CSP | Construct the task in PowerShell rather than relying on the GPP delivery mechanism |
| Registry preferences (GPP) | Settings Catalog (if corresponds to ADMX) or custom OMA-URI | Partial | Most useful registry keys are exposed through ADMX templates or have CSP equivalents; the remainder require OMA-URI |

## Certificates and PKI

| Group Policy area | Intune equivalent | Maps cleanly? | Notes |
|---|---|---|---|
| Certificate autoenrollment | Devices > Configuration > Certificates (SCEP or PKCS) | Partial | Intune SCEP and PKCS profiles replace autoenrollment; requires Intune Certificate Connector for on-premises CA integration |
| Trusted Root CA distribution | Configuration profile > Trusted certificate | Yes | Direct mapping; deploys CER files |
| Smart card root CAs | Configuration profile > Trusted certificate | Yes | Same mechanism as general trusted roots |

## Network and connectivity

| Group Policy area | Intune equivalent | Maps cleanly? | Notes |
|---|---|---|---|
| Proxy settings | Configuration profile > Network (per-platform proxy template) | Yes | Per-user and per-device proxy available |
| Wi-Fi profiles | Configuration profile > Wi-Fi | Yes | XML export from a configured profile, or build directly in Intune |
| VPN profiles | Configuration profile > VPN | Yes | Per-app VPN, Always On VPN, certificate or username/password auth all supported |
| DirectAccess / Always On VPN | Configuration profile > VPN (Always On VPN) | Yes | Direct mapping with policy-based traffic filtering |

## Telemetry and diagnostics

| Group Policy area | Intune equivalent | Maps cleanly? | Notes |
|---|---|---|---|
| Allow Telemetry (DataCollection) | Settings Catalog under "System > Allow Telemetry" | Yes | Required for Windows Update for Business reporting and Endpoint Analytics |
| Connected User Experiences and Telemetry | Same as above | Yes | Same CSP node, same configuration semantics |
| Diagnostic Data Viewer | Local Windows feature; can be enabled or disabled via Settings Catalog | Yes | User-facing feature toggle |

---

## What does not map cleanly

A small number of Group Policy capabilities have no direct Configuration
Service Provider equivalent and require workarounds.

**Group Policy Preferences (GPP) as a category** includes drive mappings,
printer mappings, scheduled tasks, registry preferences, Internet Explorer
maintenance, and a few other items. The CSP surface does not include most
of these. The migration paths are summarized in the GPP section of the
table above.

**WMI filtering on Group Policy Objects** has no direct Intune equivalent.
Use dynamic device groups in Microsoft Entra ID, with membership rules
expressed over device attributes, to achieve targeted application of
configuration profiles.

**Loopback processing mode** has no direct Intune equivalent. Use device
configuration profiles applied to device groups for device-scope settings
and user configuration profiles for user-scope settings.

**Legacy third-party ADMX templates** that are not present in the Intune
ADMX library can be ingested through *Devices > Configuration > Import
ADMX*. After ingestion, settings appear in the Settings Catalog and can
be deployed normally.

**Software Installation through Group Policy** has no direct Intune
equivalent because Intune treats application deployment as a first-class
concern through the Win32 app and Microsoft Store integration. Migrate
each GPSI deployment to a Win32 app, a Microsoft Store app, or a Microsoft
365 Apps deployment as appropriate.

---

## Recommended migration sequence

The settings that are most worth migrating early are those with the
highest security or compliance value and the cleanest mapping:
BitLocker, Microsoft Defender Antivirus, Windows Update for Business,
Attack Surface Reduction rules, and the relevant security baseline.
These have direct Intune equivalents, ship with out-of-box Intune
profile templates, and produce the largest improvement in governance
posture per hour of engineering effort.

Settings that should be deferred include Group Policy Preferences items
requiring non-trivial scripting replacement (especially drive mappings
and complex scheduled tasks), and application-specific ADMX templates
whose application itself is a candidate for deprecation or replacement.

Settings that should be eliminated rather than migrated include legacy
Internet Explorer policies (Microsoft Edge replaces IE), legacy folder
redirection to file shares (OneDrive Known Folder Move replaces it),
and any policy whose purpose was to compensate for a problem solved
natively in the cloud-native model — most notably perimeter-based or
network-location-based trust assumptions, which are subsumed by
Conditional Access.

---

## Footnotes

¹ Policy CSP reference, Microsoft Learn.
https://learn.microsoft.com/en-us/windows/client-management/mdm/policy-configuration-service-provider

Additional Microsoft Learn references:

- Windows security baselines and the Security Compliance Toolkit.
  https://learn.microsoft.com/en-us/windows/security/operating-system-security/device-management/windows-security-configuration-framework/windows-security-baselines
- Microsoft Intune security baselines.
  https://learn.microsoft.com/en-us/mem/intune/protect/security-baselines
- Microsoft Intune Settings Catalog.
  https://learn.microsoft.com/en-us/mem/intune/configuration/settings-catalog
- Import administrative templates (ADMX) into Microsoft Intune.
  https://learn.microsoft.com/en-us/mem/intune/configuration/administrative-templates-import-custom

*Verify URLs before distribution. Microsoft documentation is reorganized
frequently.*
