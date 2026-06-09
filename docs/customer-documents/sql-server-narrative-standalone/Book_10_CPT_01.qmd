---
title: "Where SQL Server Touches ADCS"
doc-type: sql-server-narrative-chapter
audience: [Technical, Customer]
family: sql-server-narrative
book: "10"
series-order: 1
status: draft
lifecycle: active
tiers_adopted: []
lifecycle_review: 2027-01-01
---

# Chapter 1 — Where SQL Server Touches ADCS

*The certificate dependencies a decommission plan cannot see, named before any decommission plan exists.*

::: {.callout-note}
## In this chapter
The three distinct SQL Server capabilities that depend on ADCS-issued certificates — TLS encryption of client connections, certificate-mapped logins, and Certificate-Based Authentication as the authorized NTLM-replacement interim posture — why each one breaks if ADCS is decommissioned before it is migrated, and why this book documents a transformation for which no normative ADR has yet been authored.
:::

The transformation inventory identifies the Active Directory Certificate Services to Cloud PKI transformation as "Not Yet Defined." As the series opening established, that label means the destination may be known but the normative canon governing how to reach it has not been authored. For most of this series, the missing record has been the substrate architecture decision; for Book 10, the gap is more fundamental still. No architecture decision record governs the certificate authority transformation at all.

There is no architecture decision equivalent to point to. The transformation is identified as necessary in the transformation inventory, the discovery instrument exists, but the normative decision about the replacement CA, the enrollment mechanism, and the sequencing of ADCS decommission has not been made. This book is therefore analytical and motivational rather than prescriptive. It documents why the certificate gap matters specifically for SQL Server, and it cites no normative ADCS-migration architecture decision because none exists.

It matters specifically because SQL Server has certificate dependencies that are not visible to most of the teams that will plan the ADCS decommission. Three distinct capabilities depend on ADCS-issued certificates: TLS encryption of client connections, certificate-mapped SQL Server logins, and Certificate-Based Authentication as the authorized NTLM replacement for connections that cannot reach Kerberos or Entra OAuth before the deadline. `Get-CertBasedAuthAudit.ps1` is the instrument for discovering them.

## SQL Server TLS/SSL Certificates

The first and most commonly recognized SQL Server certificate dependency is the TLS certificate the engine presents for encryption of client connections. When SQL Server is configured to use TLS encryption — which is required under this program's FedRAMP-Moderate posture — it presents a server certificate to connecting clients as part of the TLS handshake.

In most federal environments, that certificate is issued by the organization's ADCS infrastructure. The administrator submitted a request to the ADCS Certificate Authority, the CA issued a certificate carrying the SQL Server's hostname as the Subject Alternative Name, and the certificate was installed in the instance's certificate store and bound through SQL Server Configuration Manager. The certificate has an expiration date.

When ADCS is decommissioned, that certificate will not be renewed automatically — there is no CA left to issue the renewal. If the TLS certificate expires after ADCS decommission, clients configured to validate the server certificate, which is the correct security posture, will reject the connection with a certificate validation error. The encryption that FedRAMP-Moderate requires becomes the thing that breaks the connection.

The certificate-audit script captures the TLS certificate for every instance in scope: the subject, the SAN, the issuing CA, and the expiration date. Any instance whose TLS certificate is ADCS-issued is a dependency the migration plan must address. The replacement certificate must come from the new CA — whether Microsoft Cloud PKI or an alternative — and must be installed and bound before the ADCS-issued certificate expires or before ADCS goes offline, whichever comes first.

## Certificate-Mapped SQL Server Logins

The second dependency is less commonly known. SQL Server supports a login type — the type-C login — that maps an X.509 certificate to a SQL Server login using the `CREATE LOGIN [name] FROM CERTIFICATE [cert_name]` syntax. When a client connects with a certificate-mapped login, it presents its certificate as the authentication credential. SQL Server validates the certificate's signature against the certificate object stored in `master`, and on success accepts the connection with the associated login's permissions.

Certificate-mapped logins are uncommon in standard deployments, but they appear in specific scenarios: service accounts using certificate-based rather than password-based authentication, SQL Server integration with PKI-based authentication systems, and legacy configurations for Service Broker endpoints. Each is the kind of arrangement that survives quietly across an estate for years without anyone documenting it.

If a certificate-mapped login exists on a production instance and the certificate backing it was issued by ADCS, that login will fail when ADCS is decommissioned and the certificate expires. The preferred migration path is to replace certificate-mapped logins with type-E service-principal logins backed by Entra ID authentication, as described in Book 05. The certificate-audit script captures every certificate-mapped login and the issuing CA of its associated certificate, providing the inventory the migration needs.

## CBA as the NTLM Replacement Interim Posture

The third dependency is the most consequential for the NTLM elimination timeline. The Kerberos/NTLM-elimination program designates CBA as the authorized replacement for NTLM connections that cannot be migrated to Kerberos or Entra ID OAuth 2.0 tokens within the required timeline. CBA allows a client to authenticate with an X.509 client certificate rather than a password or Kerberos ticket — a strong mechanism that is not subject to the NTLM protocol weaknesses Book 01 described.

For connections that cannot reach Entra ID auth before the 2027-04-01 NTLM backstop — Category 3 instances still pre-2022, or applications still in the deferred class — CBA is the authorized interim posture. The connection authenticates by certificate rather than NTLM, satisfying the program's NTLM-elimination commitment without requiring the full Entra ID migration that pre-2022 instances cannot complete. It is the bridge that keeps an un-migratable connection compliant.

The problem is that CBA certificates must be issued by a CA. If the plan is to deploy CBA as the NTLM-replacement posture for connections that cannot yet reach Entra auth, and ADCS is being decommissioned, the replacement CA must already be in place and issuing CBA certificates before ADCS goes offline. The interim posture has its own certificate dependency, and that dependency points at the same authority the program intends to remove.

## The Sequencing Dependency

The three dependencies converge on a single sequencing question. TLS certificates must be re-issued before they expire; certificate-mapped logins must be migrated to type-E before their backing certificates lapse; and CBA, the very mechanism the Kerberos/NTLM-elimination program relies on to cover connections that cannot meet the deadline, must have a CA issuing its certificates before ADCS is retired.

If the ADCS decommission timeline runs earlier than the replacement-CA and CBA-deployment timeline, the program loses the interim posture the Kerberos/NTLM-elimination program depends on at precisely the moment it is most needed — connections that could not migrate to Entra auth in time would have no compliant fallback. The sequencing of ADCS decommission against the 2027-04-01 NTLM deadline is therefore a critical dependency, and it is one the as-yet-unwritten ADCS-migration architecture decision must explicitly address before any decommission date is set.

::: {.callout-note title="What Book 10 establishes — Chapter 1"}
SQL Server touches ADCS in three places that a decommission plan rarely sees: the TLS certificate the engine presents for FedRAMP-Moderate connection encryption, type-C certificate-mapped logins, and Certificate-Based Authentication as the Kerberos/NTLM-elimination program's authorized NTLM-replacement interim posture. `Get-CertBasedAuthAudit.ps1` is the discovery instrument for all three. Because the transformation inventory marks the ADCS-to-Cloud-PKI transformation "Not Yet Defined" and no normative architecture decision governs it, this book is analytical rather than prescriptive — its central finding is that the sequencing of ADCS decommission against the 2027-04-01 NTLM deadline is a critical dependency the as-yet-unwritten ADCS-migration architecture decision must resolve.
:::
