# Table of contents {#table-of-contents .TOC-Heading}

[Executive Summary [2](#executive-summary)](#executive-summary)

[1 What Is a Federal Cloud Landing Zone? [3](#what-is-a-federal-cloud-landing-zone)](#what-is-a-federal-cloud-landing-zone)

[1.1 SSA's Multi-Cloud Landing Zone Scope [4](#ssas-multi-cloud-landing-zone-scope)](#ssas-multi-cloud-landing-zone-scope)

[2 SDN and the End of Traditional DHCP [5](#sdn-and-the-end-of-traditional-dhcp)](#sdn-and-the-end-of-traditional-dhcp)

[2.1 VMware NSX-T: DHCP Server Profiles and VCF 9.1 Native Integration [5](#vmware-nsx-t-dhcp-server-profiles-and-vcf-9.1-native-integration)](#vmware-nsx-t-dhcp-server-profiles-and-vcf-9.1-native-integration)

[2.2 Microsoft Azure Government: The Fabric Replaces DHCP [6](#microsoft-azure-government-the-fabric-replaces-dhcp)](#microsoft-azure-government-the-fabric-replaces-dhcp)

[2.3 AWS GovCloud: VPC DHCP Options and the Nitro Hypervisor [6](#aws-govcloud-vpc-dhcp-options-and-the-nitro-hypervisor)](#aws-govcloud-vpc-dhcp-options-and-the-nitro-hypervisor)

[2.4 Oracle OCI: VCN DHCP Options and the VNIC Overlay [7](#oracle-oci-vcn-dhcp-options-and-the-vnic-overlay)](#oracle-oci-vcn-dhcp-options-and-the-vnic-overlay)

[3 InfoBlox as the SDN-Aware IPAM Control Plane [7](#infoblox-as-the-sdn-aware-ipam-control-plane)](#infoblox-as-the-sdn-aware-ipam-control-plane)

[3.1 What InfoBlox Provides That SDN Cannot [7](#what-infoblox-provides-that-sdn-cannot)](#what-infoblox-provides-that-sdn-cannot)

[3.2 Microsoft Partnership: M365 GCC Endpoint Lifecycle [8](#microsoft-partnership-m365-gcc-endpoint-lifecycle)](#microsoft-partnership-m365-gcc-endpoint-lifecycle)

[3.3 AWS Partnership: BloxOne Runs ON AWS GovCloud [10](#aws-partnership-bloxone-runs-on-aws-govcloud)](#aws-partnership-bloxone-runs-on-aws-govcloud)

[3.4 Oracle Cloud / OCI: OPM HRIT Future Integration [11](#oracle-cloud-oci-opm-hrit-future-integration)](#oracle-cloud-oci-opm-hrit-future-integration)

[4 Certificate Management and Cloud PKI Integration [12](#certificate-management-and-cloud-pki-integration)](#certificate-management-and-cloud-pki-integration)

[4.1 The Certificate Lifecycle in a Multi-Cloud SDN Environment [12](#the-certificate-lifecycle-in-a-multi-cloud-sdn-environment)](#the-certificate-lifecycle-in-a-multi-cloud-sdn-environment)

[4.2 Integration with Each Cloud Certificate Manager [13](#integration-with-each-cloud-certificate-manager)](#integration-with-each-cloud-certificate-manager)

[5 NIST SP 800-53 Rev 5 Control Mapping [14](#nist-sp-800-53-rev-5-control-mapping)](#nist-sp-800-53-rev-5-control-mapping)

[6 CISA Zero Trust Maturity Model v2.0 Alignment [16](#cisa-zero-trust-maturity-model-v2.0-alignment)](#cisa-zero-trust-maturity-model-v2.0-alignment)

[6.1 Networks Pillar (Deepest Alignment) [16](#networks-pillar-deepest-alignment)](#networks-pillar-deepest-alignment)

[6.2 Identity Pillar (Network-Layer Support) [17](#identity-pillar-network-layer-support)](#identity-pillar-network-layer-support)

[6.3 Cross-Cutting: Visibility and Analytics [17](#cross-cutting-visibility-and-analytics)](#cross-cutting-visibility-and-analytics)

[6.4 Cross-Cutting: Automation and Orchestration [17](#cross-cutting-automation-and-orchestration)](#cross-cutting-automation-and-orchestration)

[7 FedRAMP Boundary Enforcement [18](#fedramp-boundary-enforcement)](#fedramp-boundary-enforcement)

[8 FedRAMP Moderate and FedRAMP 20x Controls [19](#fedramp-moderate-and-fedramp-20x-controls)](#fedramp-moderate-and-fedramp-20x-controls)

[8.1 FedRAMP Moderate: The Evidence Package [19](#fedramp-moderate-the-evidence-package)](#fedramp-moderate-the-evidence-package)

[8.2 FedRAMP 20x: Automated KSI Enforcement [19](#fedramp-20x-automated-ksi-enforcement)](#fedramp-20x-automated-ksi-enforcement)

[9 Inter-Agency SaaS Integration: The OPM HRIT Template [20](#inter-agency-saas-integration-the-opm-hrit-template)](#inter-agency-saas-integration-the-opm-hrit-template)

[10 Architecture Summary [21](#architecture-summary)](#architecture-summary)

[11 Recommended Buildout Roadmap [22](#recommended-buildout-roadmap)](#recommended-buildout-roadmap)

[Phase 0 --- Procurement and Architecture (Month 1) [22](#phase-0-procurement-and-architecture-month-1)](#phase-0-procurement-and-architecture-month-1)

[Phase 1 --- On-Premises Foundation (Months 1--3) [22](#phase-1-on-premises-foundation-months-13)](#phase-1-on-premises-foundation-months-13)

[Phase 2 --- VMware VCF 9.1 Integration (Months 2--4) [22](#phase-2-vmware-vcf-9.1-integration-months-24)](#phase-2-vmware-vcf-9.1-integration-months-24)

[Phase 3 --- Azure Government Integration (Months 3--5) [23](#phase-3-azure-government-integration-months-35)](#phase-3-azure-government-integration-months-35)

[Phase 4 --- AWS GovCloud Integration (Months 5--7) [23](#phase-4-aws-govcloud-integration-months-57)](#phase-4-aws-govcloud-integration-months-57)

[Phase 5 --- OCI OPM HRIT Integration (Months 7--9) [23](#phase-5-oci-opm-hrit-integration-months-79)](#phase-5-oci-opm-hrit-integration-months-79)

[Phase 6 --- FedRAMP Continuous Monitoring (Months 9--12) [23](#phase-6-fedramp-continuous-monitoring-months-912)](#phase-6-fedramp-continuous-monitoring-months-912)

[References [24](#references)](#references)

------------------------------------------------------------------------

## Executive Summary

The Social Security Administration operates four distinct cloud environments --- on-premises VMware Cloud Foundation, Microsoft Azure Government (GCC Moderate), AWS GovCloud, and Oracle Cloud Infrastructure (OCI) for OPM HRIT integration. Each environment uses a different Software Defined Networking fabric that replaces traditional broadcast DHCP with fabric-native IP assignment. Without a unified control layer, SSA has no cross-environment IP visibility, no unified DNS security policy, no automated certificate lifecycle, and must collect FedRAMP compliance evidence from four separate sources.

**InfoBlox DDI** --- the market-leading platform for DNS, DHCP, and IP Address Management --- solves all four problems from a single FedRAMP-authorized control plane. **This is a six-day-old fact, not a three-year-old one:** CSO FR2017257053 was authorized December 15, 2022 (Census/Commerce sponsored) for BloxOne Threat Defense Federal Cloud --- a DNS-security/threat-intelligence service, not DDI. Only on July 22, 2026 did the same CSO, rebranded Infoblox Government Cloud and hosted on AWS GovCloud, get recertified FedRAMP Moderate with an expanded boundary covering Universal DDI Management, NIOS-X Servers, and Universal Asset Insights.

**The three business outcomes this document demonstrates:**

**1. Operational Risk Elimination.** A single Infoblox deployment replaces four separate DNS systems, four separate IP inventory processes, and four separate certificate-tracking tools. When a new cloud workload spins up in any environment, Infoblox automatically allocates an IP (cross-cloud conflict checked), creates DNS A and PTR records, and enrolls a machine certificate via SCEP --- in seconds, without a change ticket. When a workload decommissions, all three are revoked atomically.

**2. Continuous FedRAMP Compliance.** Infoblox is the only DDI platform with its own FedRAMP Moderate CSO authorization, meaning SSA inherits the DDI layer controls rather than re-proving them. Evidence for SC-20/21 (DNSSEC), CM-8 (inventory), IA-5(2) (certificates), AU-12 (audit), and IR-4 (incident response) is generated continuously and automatically --- not assembled manually for annual assessments.

**3. M365 GCC Boundary Enforcement.** Microsoft publishes M365 GCC endpoint changes up to 12 times per year. Without automation, each change requires four manual updates across NSG rules, VPC security groups, RPZ policies, and VPN split-tunnel configurations --- during which a gap exists between when Microsoft changes an endpoint and when SSA's controls reflect it. Infoblox polls the Microsoft 365 IP & URL Web Service API daily and pushes all four enforcement updates simultaneously, closing the boundary gap window to minutes.

**Vendor relationships:** InfoBlox has formal technology partnerships with all three of SSA's primary cloud vendors. InfoBlox BloxOne's own FedRAMP-authorized service runs *on* AWS GovCloud, making AWS the infrastructure foundation. InfoBlox is a Microsoft Azure Technology Alliance Partner with native Microsoft Sentinel, Defender Threat Intelligence, and Entra ID integrations. InfoBlox is available on the Oracle Cloud Marketplace with OCI connector support for the OPM HRIT integration path.

**The recommendation is clear: procure InfoBlox DDI via the AWS GovCloud Marketplace** (no separate IDIQ required), deploy Grid Members in each environment, and build the landing zone DNS and IPAM layer on InfoBlox from day one. Every workload deployed after that point inherits FedRAMP-compliant DNS, IP management, and certificate lifecycle automatically.

------------------------------------------------------------------------

## 1 What Is a Federal Cloud Landing Zone?

A Cloud Landing Zone is the foundational, pre-configured environment that a federal agency provisions *before* any workload is deployed. It establishes the guardrails --- network topology, identity controls, logging pipelines, encryption policies, and security baselines --- that every subsequent workload inherits automatically.

For SSA operating under FedRAMP Moderate, the landing zone must satisfy four overlapping frameworks simultaneously:

- **NIST SP 800-53 Rev 5** --- the control catalog from which FedRAMP Moderate baselines are drawn
- **CISA Zero Trust Maturity Model v2.0** --- five pillars with three cross-cutting capabilities
- **FedRAMP Moderate** --- boundary definition, continuous monitoring, evidence packaging
- **FedRAMP 20x** (emerging) --- automated, machine-readable compliance evidence enforced by infrastructure-as-code

  ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  ![](media/image1.png){width="0.16666666666666666in" height="0.16666666666666666in"} **Important**

  **The Core Insight:** DNS, DHCP, and IP address management (DDI) are not optional infrastructure services --- they are foundational security controls. Every device that joins a network, every cloud workload that provisions, every certificate that authenticates a service depends on DNS and IP assignment working correctly. A landing zone without unified DDI has a structural security gap at its foundation.
  ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

### 1.1 SSA's Multi-Cloud Landing Zone Scope

![InfoBlox DDI as the Unified Control Plane for SSA's Four-Environment Landing Zone](media/image2.png){width="5.833333333333333in" height="3.4027777777777777in"}

SSA's landing zone spans four discrete cloud environments that must behave as a single logical security domain:

  ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  **Environment**               **Platform**        **SDN Technology**                      **DHCP/IP Model**                                        **FedRAMP Boundary**
  ----------------------------- ------------------- --------------------------------------- -------------------------------------------------------- -------------------------------
  On-Premises DC                VMware VCF / ESXi   NSX-T overlay (VXLAN/Geneve)            NSX-T DHCP Server Profiles on T1/T0 Gateways             Agency ATO

  Azure Government GCC          Microsoft Azure     Azure VNet (SDN fabric, no broadcast)   Azure fabric assigns IPs; DHCP is abstracted away        Azure Government FedRAMP High

  AWS GovCloud                  Amazon AWS          VPC with ENI/Nitro hypervisor           VPC DHCP Options Sets; EC2 metadata service              AWS GovCloud FedRAMP High

  Oracle Cloud OCI (OPM HRIT)   Oracle OCI          VCN with VNIC overlay                   OCI DHCP options; instance metadata at 169.254.169.254   OPM ATO (external)
  ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

  : SSA Multi-Cloud Environments

The critical observation: **none of these four environments uses traditional broadcast DHCP.** Each uses a form of SDN where IP address assignment is managed by the hypervisor fabric --- not a classic DHCP server. Without a unified IPAM overlay, these four IP spaces are opaque to each other and to SSA's security operations center.

------------------------------------------------------------------------

## 2 SDN and the End of Traditional DHCP

![SDN Replaces Broadcast DHCP --- InfoBlox Restores Enterprise Visibility](media/image3.png){width="5.833333333333333in" height="3.111111111111111in"}

Traditional DHCP (RFC 2131) depends on Layer 2 broadcast. This model fundamentally breaks in Software Defined Networking environments because SDN uses overlay protocols (VXLAN, Geneve, STT) that operate at Layer 3 and suppress Layer 2 broadcasts by design.

### 2.1 VMware NSX-T: DHCP Server Profiles and VCF 9.1 Native Integration

VMware NSX-T replaces broadcast DHCP with **DHCP Server Profiles** attached to T1 Gateways. The NSX-T control plane intercepts DHCP requests at the logical switch level --- the request never hits the physical network. Traditional DHCP servers are completely bypassed.

VMware Cloud Foundation **9.1** (released May 2026) introduced native InfoBlox DDI integration as a first-class feature:

1.  VCF Automation tenant requests a new network segment
2.  VCF background service calls InfoBlox NIOS WAPI or BloxOne REST API to reserve an IP block
3.  NSX-T creates the logical segment using the InfoBlox-allocated CIDR
4.  InfoBlox records the segment name, CIDR, VLAN/VNI, and tenant as extensible attributes
5.  When VMs deploy, NSX-T DHCP assigns IPs; InfoBlox receives assignments via the IPAM plugin
6.  DNS A/PTR records for each VM are created automatically --- no manual DNS entry required

  ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  ![](media/image4.png){width="0.16666666666666666in" height="0.16666666666666666in"} **Tip**

  **VCF 9.1 Significance:** Before VCF 9.1, NSX-T InfoBlox integration required custom scripts and manual configuration. VCF 9.1 makes InfoBlox the native, default IPAM backend for VMware Cloud Foundation --- meaning every new VCF deployment at SSA can have InfoBlox IPAM built in from day one.
  ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

### 2.2 Microsoft Azure Government: The Fabric Replaces DHCP

Azure Virtual Networks do not use DHCP in the traditional sense. When a VM is deployed, the Azure hypervisor fabric directly assigns the IP --- the VM receives the IP via a synthetic DHCP response injected by the Azure host agent. There is no DHCP broadcast.

Azure reserves five IP addresses in every subnet that cannot be assigned (x.x.x.0 network, x.x.x.1 gateway, x.x.x.2--3 Azure DNS, x.x.x.255 broadcast). Beyond these, IP assignment is managed entirely by the Azure control plane.

InfoBlox's **Azure connector** continuously pulls VNet subnet configurations and VM NIC IP assignments via the Azure Resource Manager API, writing every Azure IP into the Azure-GCC Network View in the InfoBlox IPAM database.

### 2.3 AWS GovCloud: VPC DHCP Options and the Nitro Hypervisor

AWS VPCs use **DHCP Options Sets** to specify DNS servers and domain names, but the actual IP assignment is managed by the AWS Nitro hypervisor --- not a traditional DHCP server. EC2 instances receive IPs via a synthetic DHCP interaction at the VPC CIDR +2 address.

Replacing the default AmazonProvidedDNS with the InfoBlox Grid Member IP in the VPC DHCP Options Set directs all EC2 DNS queries through the enterprise RPZ and DNSSEC validation layer. InfoBlox's **AWS connector** syncs EC2 instance IP assignments, subnet CIDRs, and VPC IPAM pool allocations into the AWS-GovCloud Network View.

### 2.4 Oracle OCI: VCN DHCP Options and the VNIC Overlay

OCI uses Virtual Network Interface Cards (VNICs) inside Virtual Cloud Networks. OCI's internal DHCP implementation is fabric-native --- the OCI hypervisor responds to DHCP requests on behalf of each subnet from the metadata service at 169.254.169.254.

For OPM HRIT, SSA cannot control OCI DHCP Options because OPM manages the tenancy. However, SSA can document all known OPM HRIT service IPs as external host records in InfoBlox (read-only OCI Network View) and configure conditional forwarders for OPM HRIT FQDNs routing through the FastConnect path.

------------------------------------------------------------------------

## 3 InfoBlox as the SDN-Aware IPAM Control Plane

InfoBlox DDI operates as a **control plane over SDN environments** --- not replacing the SDN fabric's internal IP assignment mechanisms, but serving as the authoritative record and policy engine above them.

### 3.1 What InfoBlox Provides That SDN Cannot

  --------------------------------------------------------------------------------------------------------------------------------
  **Capability**           **What SDN Platforms Provide**        **What InfoBlox Adds**
  ------------------------ ------------------------------------- -----------------------------------------------------------------
  IP assignment            Per-environment only                  Cross-cloud conflict detection before allocation

  DNS                      Per-environment resolver              Authoritative + recursive with DNSSEC, unified across all four

  DHCP inventory           Per-VPC/VNet/segment dashboard        Single CM-8-ready inventory spanning all environments

  Certificate management   None / per-CA                         Certificate Tracker links cert to IP host record, expiry alerts

  Threat blocking          Per-environment (DNS Firewall, NSG)   Single RPZ policy propagated to all Grid Members in seconds

  Audit logging            Per-environment log silo              Single syslog stream to SIEM, AU-12 evidence

  IaC integration          Per-cloud provider only               Terraform InfoBlox provider works across all environments
  --------------------------------------------------------------------------------------------------------------------------------

  : InfoBlox Value-Add Over Native SDN

### 3.2 Microsoft Partnership: M365 GCC Endpoint Lifecycle

![Microsoft × InfoBlox Technology Partnership --- Six Integration Points](media/image5.png){width="5.833333333333333in" height="3.3055555555555554in"}

InfoBlox and Microsoft have a formal **Azure Technology Alliance Partnership** with six distinct integration points:

  -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  **Integration**                           **What It Does**
  ----------------------------------------- -------------------------------------------------------------------------------------------------------------------------------------
  **Microsoft Sentinel Native Connector**   First-party Sentinel content pack --- DNS Security Events, DHCP events, RPZ blocks stream to Sentinel without custom parsing

  **Defender Threat Intelligence (MDTI)**   Bidirectional IOC sharing between InfoBlox TIDE and MDTI --- a domain blocked by MDTI is also blocked by InfoBlox RPZ

  **Entra ID / Azure AD SSO**               InfoBlox Grid Manager and BloxOne portal support Entra ID SAML/OIDC --- Grid admin auth governed by SSA Conditional Access policies

  **Azure Government Marketplace**          BloxOne DDI Federal is procurable via existing Azure EA/ELA agreements --- no separate IDIQ

  **AD-Integrated DNS Migration**           Documented migration tooling from Windows DNS zones to InfoBlox Grid --- AD still replicates, InfoBlox serves authoritative records

  **M365 GCC Endpoint Lifecycle**           InfoBlox polls Microsoft 365 IP & URL Web Service API and auto-updates all enforcement layers
  -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

  : Microsoft-InfoBlox Integration Points

#### 3.2.1 M365 GCC Boundary Enforcement

![M365 GCC Endpoint Lifecycle Automation --- One Poll, Four Enforcement Updates](media/image6.png){width="5.833333333333333in" height="2.8194444444444446in"}

Microsoft publishes M365 endpoint changes (IP ranges + FQDNs) via the Office 365 IP and URL Web Service API. For GCC Moderate specifically, Microsoft publishes a separate GCC endpoint list --- the commercial and GCC IP ranges are different and must not be mixed. A workstation accidentally reaching a commercial Microsoft 365 endpoint instead of the GCC endpoint is a **FedRAMP boundary violation**.

InfoBlox provides the automated enforcement pipeline:

1.  **Daily poll** of the Microsoft M365 GCC endpoint API (version-change detection)
2.  **RPZ passthrough allow-list** --- GCC FQDNs explicitly allowed through threat blocking
3.  **RPZ block list** --- commercial M365 FQDNs (non-GCC) blocked at DNS layer
4.  **Azure NSG IP Group** update --- GCC Optimize IP ranges pushed to Azure Government
5.  **AWS GovCloud Security Group** update --- GCC IP ranges for outbound rules
6.  **VPN split-tunnel DNS** --- M365 Optimize FQDNs route via local interface, not VPN tunnel
7.  **Sentinel alert** --- any DNS query from an in-boundary workload to a commercial M365 endpoint triggers an IR ticket

  -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  ![](media/image7.png){width="0.16666666666666666in" height="0.16666666666666666in"} **Warning**

  **Without InfoBlox automation:** Each of Microsoft's 8--12 annual endpoint changes requires four separate change tickets across NSG, Security Groups, RPZ, and VPN config --- during which SSA has a boundary gap window. With InfoBlox, all four update within minutes of Microsoft's API publishing the change.
  -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

### 3.3 AWS Partnership: BloxOne Runs ON AWS GovCloud

![AWS GovCloud × InfoBlox --- BloxOne DDI Federal Hosted on AWS, LZA DNS Alignment](media/image8.png){width="5.833333333333333in" height="3.111111111111111in"}

The AWS relationship is the deepest of all three cloud vendors: **InfoBlox's own FedRAMP-authorized cloud service (Infoblox Government Cloud, CSO FR2017257053) is hosted on AWS GovCloud.** This makes AWS the infrastructure foundation for InfoBlox's SaaS control plane. Note the DDI-specific scope of this authorization is new: FR2017257053 was authorized December 15, 2022 for BloxOne Threat Defense Federal Cloud (DNS security only); Universal DDI Management was added to its boundary July 22, 2026.

  ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  ![](media/image4.png){width="0.16666666666666666in" height="0.16666666666666666in"} **Tip**

  **Key Point:** When SSA uses Infoblox Government Cloud, the control plane is hosted on AWS GovCloud infrastructure. SSA inherits the InfoBlox DDI CSO (FR2017257053) at Moderate; AWS GovCloud's own (higher) authorization is a leveraged authorization inside InfoBlox's package, not a second, separate inheritance for SSA.
  ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

AWS-specific InfoBlox capabilities:

- **AWS Landing Zone Accelerator (LZA) Integration:** LZA is the AWS-published IaC package for FedRAMP-compliant landing zones. InfoBlox integrates as the DNS customization layer, replacing the default Route 53 Resolver-only DNS with Grid Member + RPZ + DNSSEC. FedRAMP 20x KSIs are enforced via SCP + InfoBlox RPZ policy.
- **AWS Security Hub:** InfoBlox RPZ block events flow natively to Security Hub findings and correlate with GuardDuty detections.
- **ACM Private CA Integration:** InfoBlox auto-creates DNS validation CNAME records for ACM certificate issuance; ACM PCA certificate expiry is tracked in InfoBlox Certificate Tracker.
- **AWS IPAM Sync:** AWS IPAM pool allocations are imported into InfoBlox's AWS-GovCloud Network View --- cross-cloud CIDR conflict detection includes native AWS IPAM-managed ranges.
- **AWS GovCloud Marketplace Procurement:** BloxOne DDI Federal is procurable via the GovCloud Marketplace against existing EA agreements --- no separate IDIQ or procurement action required.

  -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  ![](media/image9.png){width="0.16666666666666666in" height="0.16666666666666666in"} **Note**

  **Route 53 Private Zone DNSSEC Gap:** AWS Route 53 private hosted zones *cannot* be DNSSEC-signed --- this is a documented AWS platform limitation as of 2026. InfoBlox Grid Members sign all internal zones including private SDN segments, closing this gap. This is a key differentiator for FedRAMP SC-20/SC-21 evidence.
  -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

### 3.4 Oracle Cloud / OCI: OPM HRIT Future Integration

![OPM HRIT on Oracle OCI --- SSA Inter-Agency Integration via InfoBlox Certificate Monitor](media/image10.png){width="5.833333333333333in" height="3.2083333333333335in"}

OPM is migrating HRIT (federal HR and benefits processing) to Oracle HCM Cloud on OCI. As OPM's HRIT moves to OCI-hosted SaaS, SSA's integration path changes from a mainframe handoff to a cloud API call from SSA's environment to OPM's OCI-hosted service endpoints.

**The challenge:** OPM controls their OCI tenancy. SSA has no visibility into OPM's certificate rotation schedule, IP range changes, or maintenance windows. When OPM rotates their HRIT API TLS certificate without SSA's trust stores being updated, the HRIT API call fails --- personnel action feeds stop, benefits enrollment breaks.

**InfoBlox manages SSA's side of the integration:**

  ------------------------------------------------------------------------------------------------------------------------------------------------
  **Integration Layer**               **InfoBlox Capability**
  ----------------------------------- ------------------------------------------------------------------------------------------------------------
  DNS resolution                      Conditional forwarder: `*.opm.gov` → OCI DNS endpoint; InfoBlox resolves from SSA network

  IP documentation                    OPM HRIT OCI IPs imported as external host records (read-only OCI Network View); SA-9 table auto-generated

  Certificate monitoring              InfoBlox Certificate Tracker polls OPM HRIT HTTPS endpoints; captures TLS cert thumbprint + expiry

  Expiry alerting                     90/30/7-day alerts give SSA advance notice of OPM cert rotation

  Trust store prep                    New OPM cert thumbprint pre-staged in InfoBlox before rotation day --- zero-downtime update
  ------------------------------------------------------------------------------------------------------------------------------------------------

  : OPM HRIT Integration via InfoBlox

  -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  ![](media/image1.png){width="0.16666666666666666in" height="0.16666666666666666in"} **Important**

  **The OPM HRIT Pattern Repeats:** OPM HRIT on OCI is the first of many federal inter-agency SaaS integrations (OPM, DHS, IRS, VA are all moving shared services to cloud SaaS). InfoBlox gives SSA the monitoring layer it needs for every inter-agency dependency: conditional DNS forwarders, Certificate Tracker, and external host records --- from SSA's side, without requiring API access to the partner agency's cloud tenancy.
  -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

------------------------------------------------------------------------

## 4 Certificate Management and Cloud PKI Integration

Software Defined Networking eliminates IP address broadcasts but creates a new requirement: in an SDN environment where workloads are ephemeral and IPs change frequently, every service-to-service call must be mutually authenticated with certificates. Certificate subject names (CN and SAN fields) must match DNS names registered in the DNS system --- which InfoBlox manages. InfoBlox is therefore the natural integration point for certificate lifecycle management.

### 4.1 The Certificate Lifecycle in a Multi-Cloud SDN Environment

The complete certificate lifecycle for a cloud workload follows this sequence:

1.  VM or container provisioned by VCF Automation, Terraform, or cloud-native IaC
2.  InfoBlox IPAM allocates an IP from the correct Network View (cross-cloud conflict-checked)
3.  InfoBlox Grid automatically creates a DNS A record: `workload-name.environment.agency.gov → IP`
4.  Workload bootstrap sends SCEP or EST enrollment to the agency CA using the DNS name as the certificate SAN
5.  CA (ADCS, Azure Key Vault with SCEP, AWS ACM Private CA) issues a certificate binding the SAN to the workload
6.  InfoBlox Certificate Tracker receives the certificate thumbprint, expiry, and issuing CA, binding it to the IP host record
7.  mTLS is active: the workload presents the certificate to authenticate to other services
8.  90/30/7 days before expiry, InfoBlox Certificate Tracker generates alerts for timely renewal

### 4.2 Integration with Each Cloud Certificate Manager

  -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  **Platform**                  **Integration Method**                              **InfoBlox Role**
  ----------------------------- --------------------------------------------------- -------------------------------------------------------------------------------------------------------
  **ADCS (On-Prem)**            SCEP/EST connector; InfoBlox SCEP auto-enrollment   Triggers enrollment on IP host record creation; binds cert thumbprint to IP record

  **Azure Key Vault (GCC)**     Azure Key Vault REST API polling                    Imports cert metadata; correlates cert to Azure VM NIC IP; alerts on expiry

  **AWS ACM Private CA**        ACM API; DNS validation CNAME auto-creation         Creates ACM validation CNAMEs in Grid; tracks ACM PCA cert expiry

  **Oracle OCI Certificates**   HTTPS endpoint polling (no OCI API needed)          Imports OPM HRIT endpoint cert thumbprint; 90/30/7-day alerts to SSA team

  **Keyfactor / Sectigo CLM**   Bidirectional API integration                       InfoBlox as DNS name SSOT for cert SAN validation; CLM uses InfoBlox IP ranges for discovery scanning
  -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

  : Certificate Manager Integrations

  --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  ![](media/image4.png){width="0.16666666666666666in" height="0.16666666666666666in"} **Tip**

  **Zero Trust Enabler:** Certificate-to-IP binding in InfoBlox is the technical foundation of 'never trust, always verify' at the network layer. When every IP host record carries a certificate thumbprint and expiry date, the network infrastructure itself becomes identity-aware --- a core requirement of CISA's Zero Trust Maturity Model Networks pillar at Advanced/Optimal level.
  --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

------------------------------------------------------------------------

## 5 NIST SP 800-53 Rev 5 Control Mapping

The following table maps InfoBlox DDI landing zone capabilities to specific NIST SP 800-53 Rev 5 controls. A single InfoBlox deployment provides evidence for 16 controls that would otherwise require separate evidence collection from four separate platforms.

  ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  **Control**       **What InfoBlox DDI Provides**                                                                                    **Evidence Artifact**                            **Satisfies**
  ----------------- ----------------------------------------------------------------------------------------------------------------- ------------------------------------------------ -----------------
  **SC-20**         DNSSEC signing of all DNS zones including internal SDN segments                                                   DNSSEC key log; DS record at .gov registrar      SC-20, SC-20(1)

  **SC-21**         Recursive DNSSEC validation on all Grid Members; RPZ with CISA Protective DNS feed                                RPZ hit log → SIEM; validation failure alert     SC-21

  **SC-22**         Network Insight auto-generates DDI topology; Grid Master-to-Member map                                            Network Insight export; SSP Appendix J           SC-22

  **SC-7**          RPZ enforces domain-level egress blocking across all four SDN environments; DNS exfiltration detection            RPZ block rate dashboard; exfil alert config     SC-7, SC-7(7)

  **SC-8**          mTLS between workloads via certificate-to-IP binding; SCEP/EST enrollment before service traffic                  Certificate Tracker report; mTLS config          SC-8, SC-8(1)

  **CM-8**          Every IP host record = CM-8 inventory item; SDN connector enriches with VM name, OS, owner, cloud region          IP host record export to ServiceNow CMDB         CM-8, CM-8(1)

  **CM-2**          IaC integration creates IP+DNS+cert records atomically and destroys them on decommission                          Terraform state; IP lifecycle audit log          CM-2, CM-6

  **SA-9**          External DNS registered as governed external services; all forwarded queries logged; OPM HRIT documented          Forwarder config export; SSP SA-9 table          SA-9

  **IA-5(2)**       Certificate Tracker links cert thumbprint+expiry+issuer to IP host record; ADCS/Key Vault/ACM/OCI cert metadata   Cert inventory report; expiry alert log          IA-5(2)

  **IA-9**          Every SDN workload receives a certificate via SCEP/EST automation at provisioning time                            SCEP enrollment log; cert-to-IP binding report   IA-9

  **AU-2**          DNS query events, DHCP lease events, IP allocation events, and cert enrollment events defined and logged          SIEM event catalog; AU-2 event list              AU-2

  **AU-12**         Single syslog stream from all Grid Members across all four SDN environments; RFC 5424 format; 3-year retention    SIEM dashboards; retention policy                AU-12

  **IR-4**          RPZ block events auto-generate SIEM IR tickets; DNSSEC failure triggers SOC alerts; DNS exfil detection           IR playbook; RPZ alert→ticket pipeline           IR-4, IR-5

  **SI-3**          DNS-layer malware blocking via RPZ prevents resolution of C2 domains, ransomware, phishing                        RPZ block count by threat category               SI-3, SI-3(1)

  **PL-8**          Unified DDI architecture in SSP; InfoBlox FedRAMP ATO cited as inherited control for DDI layer                    SSP Section 13 architecture narrative            PL-8
  ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

  : NIST SP 800-53 Rev 5 Control Coverage

------------------------------------------------------------------------

## 6 CISA Zero Trust Maturity Model v2.0 Alignment

CISA's Zero Trust Maturity Model v2.0 (April 2023) defines five pillars and three cross-cutting capabilities across four maturity stages: Traditional → Initial → Advanced → Optimal.

### 6.1 Networks Pillar (Deepest Alignment)

  ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  **CISA ZT Network Requirement**            **InfoBlox DDI Implementation**                                                                                                                    **ZT Maturity Level**
  ------------------------------------------ -------------------------------------------------------------------------------------------------------------------------------------------------- -----------------------
  Encrypt DNS traffic (DoH/DoT)              Grid Members support DoH/DoT for client queries; DNSSEC validates response integrity end-to-end                                                    Advanced → Optimal

  Implement Protective DNS                   RPZ with CISA Protective DNS feed + TIDE commercial threat intel; blocks C2, phishing, DNS tunneling across all SDN environments                   Initial → Advanced

  DNS visibility for all workloads           Unified syslog from all Grid Members; every DNS query logged with client IP, query name, response, latency                                         Initial → Advanced

  IPAM as segmentation enforcement           Network Views enforce CIDR segregation; IaC cannot allocate overlapping CIDRs; segment-level records map to NSX-T security groups and Azure NSGs   Advanced

  SDN micro-segmentation integration         NSX-T security groups can reference InfoBlox IPAM tags (workload classification, owner) as dynamic membership criteria                             Advanced → Optimal

  Certificate-based network authentication   Certificate Tracker ensures every IP host record has a bound certificate; IP reputation replaced by certificate identity                           Advanced → Optimal
  ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

  : CISA Zero Trust Networks Pillar Alignment

### 6.2 Identity Pillar (Network-Layer Support)

InfoBlox supports the Identity pillar through certificate lifecycle management --- the mechanism by which workload identity is established at the network layer:

- SCEP/EST automation issues certificates to every new workload at provisioning time, establishing machine identity before the first connection
- Certificate-to-IP binding enables network devices to verify workload identity from the DNS/IPAM layer without agent deployment
- Certificate expiry alerting prevents identity credential expiration --- a common cause of authentication outages

### 6.3 Cross-Cutting: Visibility and Analytics

InfoBlox contributes three telemetry streams to CISA's Visibility and Analytics capability:

- **DNS query telemetry:** every DNS resolution event from every SDN workload, with client IP, query type, response, latency, and RPZ action
- **DHCP/IP event telemetry:** every IP allocation, renewal, and release with device metadata
- **Certificate telemetry:** every expiry warning and enrollment event

All three streams flow to the SIEM in consistent syslog format --- enabling correlation across DNS, IP, and certificate events that individually appear innocuous but together may indicate lateral movement or data exfiltration.

### 6.4 Cross-Cutting: Automation and Orchestration

InfoBlox's IaC integrations directly enable the CISA Automation and Orchestration capability:

- Network resource provisioning (IP, DNS, cert) is automated in IaC pipelines --- no manual steps that bypass policy
- VCF 9.1 native InfoBlox integration automates DDI for VMware workloads from day one
- RPZ updates are automated from threat intelligence feeds --- human review required only for false positive exceptions

------------------------------------------------------------------------

## 7 FedRAMP Boundary Enforcement

![InfoBlox DDI as the FedRAMP Authorization Boundary Enforcement Layer](media/image11.png){width="5.833333333333333in" height="3.3055555555555554in"}

InfoBlox DDI enforces the FedRAMP authorization boundary at three layers simultaneously:

**Layer 1 --- IP Inventory = Boundary Definition.** The FedRAMP authorization boundary is defined by IP address ranges. InfoBlox IPAM *is* the authoritative record of every IP inside the boundary. The CM-8 IP inventory export *is* the boundary IP list --- no separate reconciliation required.

**Layer 2 --- DNS = Boundary Enforcement at Egress.** Every DNS query from every workload passes through the InfoBlox Grid Member (because all VPC/VNet/NSX-T DHCP Options point to it). InfoBlox enforces:

- RPZ blocks commercial M365 endpoints (prevents FedRAMP data reaching non-GCC Microsoft infrastructure)
- RPZ blocks non-FedRAMP SaaS FQDNs (prevents workloads from reaching unauthorized cloud services)
- Conditional forwarders for external services generate the SA-9 documentation automatically
- DNSSEC validation required --- DNS spoofing that could redirect traffic outside the boundary is rejected
- Query logging for all workloads --- AU-12 evidence: every external communication visible in DNS logs

**Layer 3 --- Certificate Binding = Boundary Identity.** Only IP host records within the InfoBlox IPAM database can receive certificates via SCEP/EST enrollment automation. Certificate possession = boundary membership --- a powerful assertion for boundary documentation and IA-9 satisfaction.

------------------------------------------------------------------------

## 8 FedRAMP Moderate and FedRAMP 20x Controls

### 8.1 FedRAMP Moderate: The Evidence Package

InfoBlox DDI produces a complete evidence package for FedRAMP Moderate annual assessments without manual evidence collection:

  -------------------------------------------------------------------------------------------------------------------------------------------
  **Control Family**   **Evidence Source**                                         **Format**                     **Collection**
  -------------------- ----------------------------------------------------------- ------------------------------ ---------------------------
  SC-20 / SC-21        InfoBlox DNSSEC key rotation log; RPZ hit log               Grid audit log export          Automated

  CM-8                 InfoBlox IP host record database                            CSV / ServiceNow CMDB sync     API export on demand

  IA-5(2)              InfoBlox Certificate Tracker                                Certificate inventory report   API export on demand

  AU-2 / AU-12         SIEM fed by InfoBlox syslog stream                          SIEM query results             Pre-built SIEM dashboards

  IR-4                 SIEM IR playbook execution logs; RPZ alert ticket history   ServiceNow tickets             ITSM integration

  SA-9                 InfoBlox External DNS Server config; SSP SA-9 table         InfoBlox config export         Grid config snapshot

  SC-22                InfoBlox Network Insight topology report                    PDF / JSON topology export     Network Insight scheduler
  -------------------------------------------------------------------------------------------------------------------------------------------

  : FedRAMP Moderate Evidence Package

### 8.2 FedRAMP 20x: Automated KSI Enforcement

FedRAMP 20x replaces periodic evidence collection with continuously-verified Key Security Indicators enforced by infrastructure-as-code guardrails:

  ----------------------------------------------------------------------------------------------------------------------------------------------------------------
  **FedRAMP 20x KSI**                                **InfoBlox Enforcement**                                                    **Automated?**
  -------------------------------------------------- --------------------------------------------------------------------------- ---------------------------------
  All DNS traffic encrypted or integrity-protected   DNSSEC on all zones; DoH/DoT endpoint on Grid Members                       **Yes** --- Grid policy

  Protective DNS for all workloads                   Grid Member = resolver for all VPC/VNet DHCP options; RPZ active            **Yes** --- DHCP Options + RPZ

  IP address inventory current and complete          API connectors sync in near-real-time; CM-8 report on demand                **Yes** --- API connectors

  No CIDR overlap between environments               Terraform InfoBlox provider blocks overlapping allocation at request time   **Yes** --- Terraform

  Certificate expiry monitored and auto-renewed      Certificate Tracker 90/30/7-day alerts; SCEP/EST auto-renewal workflow      **Yes** --- Certificate Tracker

  Every workload has machine identity (cert)         SCEP/EST enrollment triggered at IP host record creation                    **Yes** --- Auto-enrollment

  DNS change events auditable                        All DNS/DHCP/IP changes logged; syslog to SIEM in real time                 **Yes** --- Syslog + SIEM
  ----------------------------------------------------------------------------------------------------------------------------------------------------------------

  : FedRAMP 20x KSI Automation

  -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  ![](media/image4.png){width="0.16666666666666666in" height="0.16666666666666666in"} **Tip**

  **FedRAMP 20x Positioning:** InfoBlox DDI positions SSA ahead of the FedRAMP 20x transition. The machine-readable IP inventory (WAPI), automated KSI enforcement via IaC, and real-time SIEM integration align directly with FedRAMP 20x's shift from periodic assessment to continuous automated verification.
  -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

------------------------------------------------------------------------

## 9 Inter-Agency SaaS Integration: The OPM HRIT Template

OPM HRIT on OCI is the **first of many** federal inter-agency SaaS integrations. OPM, SSA, DHS, IRS, and VA are all moving shared services to cloud-hosted SaaS platforms. The pattern repeats every time:

1.  Agency A moves a shared service to cloud SaaS (OPM HRIT → OCI)
2.  Agency B (SSA) becomes an API consumer of that SaaS
3.  Agency B has no visibility into Agency A's certificate rotation, endpoint changes, or IP range changes
4.  InfoBlox gives Agency B the monitoring layer it needs --- **from SSA's side, without requiring access to the partner agency's cloud**

**InfoBlox's inter-agency integration toolkit:**

- **Conditional DNS forwarders** --- always know where the service resolves, even when the partner agency changes DNS
- **Certificate Tracker endpoint polling** --- always know when the partner's TLS cert will expire
- **External host records** --- always document the partner's IP ranges for SA-9 without API access to their cloud
- **RPZ passthrough entries** --- ensure InfoBlox RPZ does not block the inter-agency API calls
- **Sentinel alerts** --- detect if the inter-agency connection's certificate has changed unexpectedly (potential MITM)

------------------------------------------------------------------------

## 10 Architecture Summary

  ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  **Layer**              **On-Premises VMware**             **Azure Government**                **AWS GovCloud**                    **Oracle OCI (OPM)**            **InfoBlox Role**
  ---------------------- ---------------------------------- ----------------------------------- ----------------------------------- ------------------------------- ---------------------------------
  **IP Assignment**      NSX-T DHCP Profiles (VCF 9.1)      Azure fabric / ARM API              VPC DHCP Options / Nitro            OCI VNIC / 169.254.169.254      IPAM SSOT via connectors

  **DNS Resolver**       Grid Member (replaces AD DNS)      Azure DNS Private Resolver → Grid   VPC DHCP Options → Grid             OCI resolver → Grid forwarder   Unified recursive + DNSSEC

  **DNS Authority**      Grid Master (agency.gov)           Grid Member + Azure Private DNS     Grid Member + Route 53 private      Grid forwarder + OCI DNS        Grid Master as SSOT

  **DHCP**               InfoBlox Grid DHCP (HA pair)       Azure fabric (no Grid DHCP)         AWS VPC DHCP                        OCI DHCP                        On-prem native; cloud via API

  **IPAM**               On-Premises Network View           Azure-GCC Network View              AWS-GovCloud Network View           OCI-OPM Network View (RO)       Single DB, 4 Network Views

  **Certificates**       ADCS via SCEP/EST                  Azure Key Vault; ARM API polling    ACM Private CA; validation CNAMEs   OCI Certs (OPM); cert polling   Certificate Tracker

  **Threat / RPZ**       RPZ on Grid Members; TIDE + CISA   RPZ on Azure Grid Member            RPZ on AWS Grid Member              Grid forwarder RPZ              Single policy, all environments

  **Audit / SIEM**       Syslog from Grid Members           Syslog from Azure Grid Member       Syslog from AWS Grid Member         Syslog from Grid forwarder      One syslog stream

  **FedRAMP Controls**   SC-20/21, CM-8, AU-12, IR-4        SC-20/21, SA-9, IA-5(2), CM-8       SC-20/21, SA-9, IA-5(2), CM-8       SA-9, IA-5(2)                   Single evidence source
  ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

  : Full Landing Zone Architecture Summary

------------------------------------------------------------------------

## 11 Recommended Buildout Roadmap

Each phase produces immediately usable compliance evidence and security value --- there is no 'big bang' dependency before the first phase delivers results.

### Phase 0 --- Procurement and Architecture (Month 1)

- Procure Infoblox Government Cloud (Universal DDI) via **AWS GovCloud Marketplace** against existing EA (no new IDIQ)
- Reference FedRAMP Marketplace CSO **FR2017257053** in procurement documentation --- confirm at procurement time that the DDI scope (added July 22, 2026) is still current and check for an agency-specific ATO vs. a P-ATO/JAB designation
- Design Network View CIDR allocation plan: audit all existing IP ranges across on-prem, Azure VNet, AWS VPC, OCI VCN for overlaps
- Engage InfoBlox Professional Services for VCF 9.1 DDI integration workshop

### Phase 1 --- On-Premises Foundation (Months 1--3)

- Deploy Grid Master HA pair; import all AD DNS zones; enable DNSSEC for agency.gov
- Submit DS record to .gov TLD registrar (closes SC-20 gap)
- Migrate Windows Server DHCP scopes to InfoBlox Grid DHCP; enable DHCP fingerprinting
- Configure syslog forwarding from all Grid Members to SIEM (Splunk/Sentinel); verify AU-12 event receipt
- Deploy SCEP connector to ADCS; test automated cert enrollment from new IP host record
- Generate first CM-8 IP inventory export; reconcile against existing CMDB

### Phase 2 --- VMware VCF 9.1 Integration (Months 2--4)

- Update VCF to 9.1; configure VCF-A to use InfoBlox WAPI as external IPAM backend
- Update NSX-T DHCP Server Profiles to route DNS to InfoBlox Grid Member IP
- Verify NSX-T VM IP assignments appear in InfoBlox On-Premises Network View within 60 seconds

### Phase 3 --- Azure Government Integration (Months 3--5)

- Deploy InfoBlox Grid Member as Azure VM in Hub VNet; configure Azure DNS Private Resolver to forward to Grid Member
- Register all Azure VNet/subnet CIDRs in InfoBlox Azure-GCC Network View; enable Azure connector
- Configure Azure Key Vault Certificate Manager polling in InfoBlox Certificate Tracker
- Configure M365 GCC endpoint API polling; test RPZ passthrough and commercial M365 RPZ block

### Phase 4 --- AWS GovCloud Integration (Months 5--7)

- Deploy InfoBlox Grid Member as EC2 instance in Transit VPC
- Update VPC DHCP Options Sets to use Grid Member IP as domain-name-server
- Enable InfoBlox AWS connector; register all VPC CIDR allocations in AWS-GovCloud Network View
- Configure ACM DNS validation CNAME automation; test certificate issuance for an internal ALB
- Integrate InfoBlox RPZ events with AWS Security Hub findings

### Phase 5 --- OCI OPM HRIT Integration (Months 7--9)

- Import all known OPM HRIT service endpoint IPs and FQDNs as external host records
- Configure InfoBlox conditional forwarder for OPM HRIT FQDNs through FastConnect path
- Connect InfoBlox Certificate Tracker to OPM HRIT HTTPS endpoints; verify 90-day cert expiry alert fires
- Document OCI integration in SSP SA-9 external services table with OPM as system owner

### Phase 6 --- FedRAMP Continuous Monitoring (Months 9--12)

- Complete InfoBlox FedRAMP ATO documentation in SSP; reference CSO FR2017257053 for DDI layer control inheritance, citing the July 22, 2026 boundary expansion (Universal DDI Management) as the specific authorization event --- not the December 2022 BloxOne Threat Defense authorization
- Configure all eight FedRAMP control evidence exports as scheduled reports
- Implement IaC Terraform pipeline: IP allocation → DNS record → SCEP cert enrollment as single atomic pipeline
- Configure FedRAMP 20x KSI automation checks (DNSSEC status, RPZ coverage, cert expiry, CIDR conflict) as CI/CD pipeline tests

------------------------------------------------------------------------

## References

  ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  **Source**                                                  **URL**
  ----------------------------------------------------------- ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  InfoBlox FedRAMP Marketplace (CSO FR2017257053) --- authorized Dec 15, 2022 for BloxOne Threat Defense Federal Cloud; Universal DDI Management added to the boundary July 22, 2026             [fedramp.gov/marketplace/products/FR2017257053](https://www.fedramp.gov/marketplace/products/FR2017257053/)

  Infoblox's BloxOne Threat Defense Federal Cloud Clears FedRAMP Authorization (Jan 26, 2023 press release; scopes the Dec 2022 authorization to threat-defense, not DDI)   [infoblox.com/news](https://www.infoblox.com/news/news-events/press-releases/infobloxs-bloxone-threat-defense-federal-cloud-clears-fedramp-authorization-for-data-security/)

  Infoblox Government Cloud Achieves FedRAMP Moderate Certification (Jul 22, 2026; Universal DDI Management, NIOS-X Servers, Universal Asset Insights)   [infoblox.com/blog](https://www.infoblox.com/blog/company/infoblox-universal-ddi-comes-to-infoblox-government-cloud/)

  VMware VCF 9.1 InfoBlox DDI Integration (May 2026)          [blogs.vmware.com/cloud-foundation](https://blogs.vmware.com/cloud-foundation/2026/05/15/vcf-networking-9-1-seamless-ddi-integration-with-infoblox/)

  Register InfoBlox NIOS DDI with NSX --- Broadcom TechDocs   [techdocs.broadcom.com/.../integrate-nsx-with-infoblox](https://techdocs.broadcom.com/us/en/vmware-cis/vcf/vcf-9-0-and-later/9-1/advanced-network-management/ip-address-management-ipam/integrate-nsx-with-infoblox.html)

  Microsoft 365 IP and URL Web Service                        [docs.microsoft.com/en-us/microsoft-365/enterprise/microsoft-365-ip-web-service](https://docs.microsoft.com/en-us/microsoft-365/enterprise/microsoft-365-ip-web-service)

  AWS VPC IP Address Manager (IPAM)                           [docs.aws.amazon.com/vpc/latest/ipam](https://docs.aws.amazon.com/vpc/latest/ipam/what-it-is-ipam.html)

  Azure Virtual Network Manager IPAM (preview)                [learn.microsoft.com/en-us/azure/virtual-network-manager/concept-ip-address-management](https://learn.microsoft.com/en-us/azure/virtual-network-manager/concept-ip-address-management)

  CISA Zero Trust Maturity Model v2.0 (April 2023)            [cisa.gov/sites/default/files/2023-04/zero_trust_maturity_model_v2_508.pdf](https://www.cisa.gov/sites/default/files/2023-04/zero_trust_maturity_model_v2_508.pdf)

  FedRAMP 20x KSI Enforcement --- AWS Public Sector           [aws.amazon.com/blogs/publicsector/preventive-controls-for-fedramp-20x](https://aws.amazon.com/blogs/publicsector/preventive-controls-for-fedramp-20x-using-scps-and-guardrails-to-enforce-ksis/)

  InfoBlox NIOS 9.0 Certificate Management                    [docs.infoblox.com/space/nios90/280266962](https://docs.infoblox.com/space/nios90/280266962)

  AWS Landing Zone Accelerator on AWS (LZA)                   [github.com/awslabs/landing-zone-accelerator-on-aws](https://github.com/awslabs/landing-zone-accelerator-on-aws)

  InfoBlox IPAM and DHCP Solutions                            [infoblox.com/solutions/ipam-dhcp](https://www.infoblox.com/solutions/ipam-dhcp/)

  Configure DHCP for Azure VMware Solution (NSX-T)            [learn.microsoft.com/en-us/azure/azure-vmware/configure-dhcp-azure-vmware-solution](https://learn.microsoft.com/en-us/azure/azure-vmware/configure-dhcp-azure-vmware-solution)
  ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

  : References
