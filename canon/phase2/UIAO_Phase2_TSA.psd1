@{
    Metadata = @{
        Id              = 'UIAO_P2_TSA_001'
        Name            = 'UIAO Phase 2 Target State Architecture'
        Version         = '0.1.0'
        Owner           = 'UIAO Architecture'
        Phase           = '2'
        Description     = 'Canonical target state architecture outline for UIAO Phase 2.'
        SourceSpecs     = @(
            'UIAO_136',
            'Program Overview',
            'Entra ID Org Hierarchy Guide',
            'Phase 2 GOS',
            'HR Driven EntraID',
            'Choosing EntraID vs AD for SQL',
            'Operations Runbook'
        )
        LastUpdatedUtc  = '2026-04-29T00:00:00Z'
    }

    Planes = @(
        @{
            Id          = 'PLN_IDENTITY'
            Name        = 'Identity and Directory Plane'
            Description = 'Human, device, and workload identities; directory services; lifecycle and assurance.'
        }
        @{
            Id          = 'PLN_DEVICE'
            Name        = 'Endpoint and Server Plane'
            Description = 'Client endpoints, servers, and hybrid assets including Arc-enabled resources.'
        }
        @{
            Id          = 'PLN_ACCESS'
            Name        = 'Access and Policy Plane'
            Description = 'Conditional Access, Zero Trust policy overlay, and enforcement surfaces.'
        }
        @{
            Id          = 'PLN_GOV'
            Name        = 'Governance and Provenance Plane'
            Description = 'Baselines, drift detection, provenance chain, and compliance evidence.'
        }
        @{
            Id          = 'PLN_APP'
            Name        = 'Application and Integration Plane'
            Description = 'Line-of-business apps, SaaS, LDAP-dependent apps, and modern auth integration.'
        }
        @{
            Id          = 'PLN_NETWORK'
            Name        = 'Network and Name Resolution Plane'
            Description = 'DNS, named locations, and network-aware policy constructs.'
        }
    )

    Lifecycles = @(
        @{
            Id          = 'LC_HUMAN'
            Name        = 'Human Identity Lifecycle'
            Description = 'Joiner-Mover-Leaver lifecycle for human users driven by HR systems.'
            Drivers     = @('HR System', 'Entra ID Governance', 'Access Packages')
            KeyFlows    = @(
                'HR event -> Entra ID account provisioning',
                'Role or OrgPath change -> access re-evaluation',
                'Termination -> deprovisioning and access revocation'
            )
        }
        @{
            Id          = 'LC_DEVICE'
            Name        = 'Device Lifecycle'
            Description = 'Enrollment, configuration, compliance, and retirement for endpoints and servers.'
            Drivers     = @('Intune', 'Azure Arc', 'OrgPath', 'Compliance Policies')
            KeyFlows    = @(
                'Device enrollment -> OrgPath assignment -> policy targeting',
                'Compliance drift -> Conditional Access impact',
                'Server onboarding -> Arc enablement -> RBAC and telemetry'
            )
        }
        @{
            Id          = 'LC_WORKLOAD'
            Name        = 'Workload Identity Lifecycle'
            Description = 'Service accounts, managed identities, and service principals.'
            Drivers     = @('Entra Workload Identities', 'Managed Identity', 'Service Principal')
            KeyFlows    = @(
                'Legacy service account -> workload identity mapping',
                'Credential rotation and secretless auth',
                'Decommissioning workloads and identities'
            )
        }
        @{
            Id          = 'LC_POLICY'
            Name        = 'Policy and Baseline Lifecycle'
            Description = 'Definition, rollout, monitoring, and adjustment of identity and device baselines.'
            Drivers     = @('OSCAL Baselines', 'Governance Substrate', 'Drift Detection')
            KeyFlows    = @(
                'Baseline definition -> deployment -> drift monitoring',
                'Drift detection -> remediation orchestration',
                'Baseline versioning and evidence capture'
            )
        }
    )

    Domains = @(
        @{
            Id          = 'DOM_ID_DIR'
            Name        = 'Identity and Directory'
            PlaneId     = 'PLN_IDENTITY'
            Description = 'Human identity, directory services, and identity assurance.'
            SourceState = @(
                'Active Directory domains and forests',
                'X.500 OU trees',
                'AD security groups and distribution lists',
                'Kerberos/NTLM authentication',
                'LDAP-dependent applications'
            )
            TargetState = @(
                'Entra ID as primary identity provider',
                'OrgPath attributes and dynamic groups',
                'Administrative Units and scoped roles',
                'Modern auth (OAuth2/OIDC, SAML, CBA)',
                'Entra ID App Proxy and app registrations'
            )
            KeyTransformations = @(
                'X.500 OU Tree -> OrgPath Attributes + Dynamic Groups',
                'AD Security Groups -> Entra ID Groups',
                'OU-Scoped Delegation -> Administrative Units + Scoped Roles',
                'Kerberos/NTLM -> Modern Auth Protocols',
                'LDAP-Dependent Applications -> Entra ID App Proxy + SAML/OIDC'
            )
            Dependencies = @(
                'LC_HUMAN',
                'LC_WORKLOAD',
                'LC_POLICY'
            )
        }
        @{
            Id          = 'DOM_HR_PROV'
            Name        = 'HR-Driven Provisioning'
            PlaneId     = 'PLN_IDENTITY'
            Description = 'HR-agnostic provisioning architecture for human identities.'
            SourceState = @(
                'On-prem HR -> MIM -> AD',
                'Manual account creation',
                'Ticket-driven lifecycle changes'
            )
            TargetState = @(
                'Cloud HR connector (Workday or Oracle) -> Entra ID',
                'API-driven inbound provisioning',
                'Joiner-Mover-Leaver workflows in Entra ID Governance',
                'Attribute writeback to HR where required'
            )
            KeyTransformations = @(
                'On-prem HR -> MIM -> AD -> Entra Connect Sync -> Entra ID',
                'Cloud HR Connector -> Entra ID (Workday/Oracle)',
                'API-driven inbound provisioning for non-standard HR sources'
            )
            Dependencies = @(
                'LC_HUMAN',
                'DOM_ID_DIR'
            )
        }
        @{
            Id          = 'DOM_DEVICE'
            Name        = 'Device Identity and Compliance'
            PlaneId     = 'PLN_DEVICE'
            Description = 'Device identity, configuration, and compliance baselines.'
            SourceState = @(
                'Domain-joined Windows clients',
                'GPO-based configuration and loopback processing',
                'On-prem servers without cloud projection'
            )
            TargetState = @(
                'Entra ID-joined or hybrid-joined devices',
                'Intune configuration profiles and compliance policies',
                'Azure Arc-enabled servers with managed identities',
                'Device posture integrated into Conditional Access'
            )
            KeyTransformations = @(
                'Computer Objects -> Entra ID Device Identity + Arc',
                'GPO -> Intune Configuration Profiles + Compliance Policies',
                'GPO Loopback -> Device-Targeted Policy',
                'GPO Admin Scoping -> Intune Scope Tags'
            )
            Dependencies = @(
                'LC_DEVICE',
                'LC_POLICY',
                'DOM_ID_DIR'
            )
        }
        @{
            Id          = 'DOM_ACCESS'
            Name        = 'Access and Conditional Policy'
            PlaneId     = 'PLN_ACCESS'
            Description = 'Conditional Access, Zero Trust enforcement, and policy overlay.'
            SourceState = @(
                'Static firewall rules',
                'GPO security filtering',
                'One-time authentication decisions'
            )
            TargetState = @(
                'Conditional Access policies with device compliance requirements',
                'Policy Overlay with continuous evaluation',
                'Named locations and risk-based controls'
            )
            KeyTransformations = @(
                'Security Filtering -> Conditional Access',
                'Policy Overlay -> Continuous enforcement layer',
                'AD Sites & Subnets -> Named Locations + Conditional Access'
            )
            Dependencies = @(
                'DOM_ID_DIR',
                'DOM_DEVICE',
                'DOM_NETWORK',
                'LC_POLICY'
            )
        }
        @{
            Id          = 'DOM_GOV'
            Name        = 'Governance and Provenance'
            PlaneId     = 'PLN_GOV'
            Description = 'Baselines, provenance, and governance substrate.'
            SourceState = @(
                'Manual CA/MFA/PIM policy management',
                'Email/ticket-based governance',
                'Manual device config review'
            )
            TargetState = @(
                'Entra ID Identity Baselines (UIAO_BL_001, BL_002)',
                'Endpoint Compliance Baselines (UIAO_BL_007, BL_008)',
                'Governance Substrate with SHA-256-linked provenance chain',
                'Automated drift detection and remediation orchestration'
            )
            KeyTransformations = @(
                'Identity Baselines -> Canonical OSCAL baselines with drift detection',
                'Endpoint Compliance Baselines -> Intune governance',
                'Governance Substrate -> Provenance chain and evidence generation'
            )
            Dependencies = @(
                'LC_POLICY',
                'DOM_ID_DIR',
                'DOM_DEVICE'
            )
        }
        @{
            Id          = 'DOM_NETWORK'
            Name        = 'Network and Name Resolution'
            PlaneId     = 'PLN_NETWORK'
            Description = 'DNS, named locations, and hybrid network constructs.'
            SourceState = @(
                'AD-integrated DNS',
                'On-prem-only name resolution',
                'AD Sites and Subnets'
            )
            TargetState = @(
                'Azure DNS / Hybrid DNS',
                'Named locations feeding Conditional Access',
                'Hybrid DNS orchestration'
            )
            KeyTransformations = @(
                'DNS (AD-Integrated) -> Azure DNS / Hybrid DNS',
                'AD Sites & Subnets -> Named Locations + Conditional Access'
            )
            Dependencies = @(
                'DOM_ACCESS'
            )
        }
        @{
            Id          = 'DOM_APP'
            Name        = 'Application and Integration'
            PlaneId     = 'PLN_APP'
            Description = 'Application identity, auth, and integration patterns.'
            SourceState = @(
                'LDAP-bound applications',
                'SQL Server using Windows Auth and SQL Auth',
                'Apps bound to AD groups and OUs'
            )
            TargetState = @(
                'Entra ID app registrations and enterprise apps',
                'Entra ID auth for SQL Server 2022+',
                'Workload identity federation',
                'App Proxy for on-prem apps'
            )
            KeyTransformations = @(
                'SQL Server Authentication -> Entra ID Auth',
                'LDAP-Dependent Applications -> Entra ID App Proxy + SAML/OIDC',
                'AD Service Accounts -> Entra Workload Identities'
            )
            Dependencies = @(
                'LC_WORKLOAD',
                'DOM_ID_DIR',
                'DOM_DEVICE'
            )
        }
    )
}
