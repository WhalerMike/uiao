# Identity and Directory
Id: DOM_ID_DIR
PlaneId: PLN_IDENTITY

## Description
Human identity, directory services, and identity assurance.

## Source State
- Active Directory domains and forests
- X.500 OU trees
- AD security groups and distribution lists
- Kerberos/NTLM authentication
- LDAP-dependent applications

## Target State
- Entra ID as primary identity provider
- OrgPath attributes and dynamic groups
- Administrative Units and scoped roles
- Modern auth (OAuth2/OIDC, SAML, CBA)
- Entra ID App Proxy and app registrations

## Key Transformations
- X.500 OU Tree -> OrgPath Attributes + Dynamic Groups
- AD Security Groups -> Entra ID Groups
- OU-Scoped Delegation -> Administrative Units + Scoped Roles
- Kerberos/NTLM -> Modern Auth Protocols
- LDAP-Dependent Applications -> Entra ID App Proxy + SAML/OIDC

## Dependencies
- LC_HUMAN
- LC_WORKLOAD
- LC_POLICY

## Detailed Design
_To be elaborated in Phase 2 design sessions._
