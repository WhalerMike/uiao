# Application and Integration
Id: DOM_APP
PlaneId: PLN_APP

## Description
Application identity, auth, and integration patterns.

## Source State
- LDAP-bound applications
- SQL Server using Windows Auth and SQL Auth
- Apps bound to AD groups and OUs

## Target State
- Entra ID app registrations and enterprise apps
- Entra ID auth for SQL Server 2022+
- Workload identity federation
- App Proxy for on-prem apps

## Key Transformations
- SQL Server Authentication -> Entra ID Auth
- LDAP-Dependent Applications -> Entra ID App Proxy + SAML/OIDC
- AD Service Accounts -> Entra Workload Identities

## Dependencies
- LC_WORKLOAD
- DOM_ID_DIR
- DOM_DEVICE

## Detailed Design
_To be elaborated in Phase 2 design sessions._
