using './main.bicep'

// ---------------------------------------------------------------------
// Example parameters for the UIAO Azure SaaS deployment (ADR-096).
// Copy to an environment-specific file (e.g. main.prod.bicepparam) and
// fill in the GUIDs. Never commit real secrets — pgAdminPassword and
// appClientId/publisherTenantId come from CI secrets / Key Vault.
// ---------------------------------------------------------------------

param workload = 'uiao'
param environmentName = 'dev'
param cloud = 'commercial'

// Set after the multi-tenant app registration is created.
param appClientId = ''
// Defaults to the deploying subscription's tenant if left empty in main.
param publisherTenantId = ''
param apiAudience = 'api://uiao'

// CI injects the container image after build/push; leave empty to default
// to <acr>/uiao-saas:latest on first stamp.
param containerImage = ''

param pgAdminLogin = 'uiaoadmin'
// Provided at deploy time: az deployment ... -p pgAdminPassword=$PG_PWD
param pgAdminPassword = ''

param minReplicas = 1
param maxReplicas = 10
