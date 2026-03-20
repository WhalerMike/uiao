// Microsoft Sentinel Scheduled Alert Rules for Atlas
// Deploy with: az deployment group create --resource-group <rg> --template-file sentinel_alerts.bicep

param workspaceName string
param location string = resourceGroup().location

resource workspace 'Microsoft.OperationalInsights/workspaces@2022-10-01' existing = {
  name: workspaceName
}

resource atlasPrivilegedLeaver 'Microsoft.SecurityInsights/alertRules@2023-02-01-preview' = {
  name: guid(workspace.id, 'Atlas-Privileged-Leaver')
  scope: workspace
  kind: 'Scheduled'
  properties: {
    displayName: 'Atlas: Privileged Leaver Detected'
    description: 'Alerts when a high-value asset account is disabled in Entra ID.'
    severity: 'High'
    enabled: true
    query: '''
      AuditLogs
      | where OperationName == "Disable user"
      | extend TargetUser = tostring(TargetResources[0].userPrincipalName)
      | join kind=inner (
          IdentityInfo
          | where IsHighValueAsset == true
      ) on $left.TargetUser == $right.AccountUPN
    '''
    queryFrequency: 'PT1H'
    queryPeriod: 'PT1H'
    triggerOperator: 'GreaterThan'
    triggerThreshold: 0
    suppressionDuration: 'PT5H'
    suppressionEnabled: false
    incidentConfiguration: {
      createIncident: true
      groupingConfiguration: {
        enabled: false
        reopenClosedIncident: false
        lookbackDuration: 'PT5H'
        matchingMethod: 'AllEntities'
      }
    }
    tactics: [
      'InitialAccess'
      'PrivilegeEscalation'
    ]
  }
}

resource atlasComplianceDrift 'Microsoft.SecurityInsights/alertRules@2023-02-01-preview' = {
  name: guid(workspace.id, 'Atlas-Compliance-Drift')
  scope: workspace
  kind: 'Scheduled'
  properties: {
    displayName: 'Atlas: Device Compliance Drift'
    description: 'Identifies devices falling out of compliance in Intune for potential isolation.'
    severity: 'Medium'
    enabled: true
    query: '''
      IntuneDevices
      | where ComplianceState == "Noncompliant"
      | summarize arg_max(TimeGenerated, *) by DeviceId
      | project TimeGenerated, DeviceName, UserEmail, ComplianceState, OS
    '''
    queryFrequency: 'PT15M'
    queryPeriod: 'PT15M'
    triggerOperator: 'GreaterThan'
    triggerThreshold: 0
    incidentConfiguration: {
      createIncident: true
      groupingConfiguration: {
        enabled: false
        reopenClosedIncident: false
        lookbackDuration: 'PT5H'
        matchingMethod: 'AllEntities'
      }
    }
    tactics: [
      'DefenseEvasion'
    ]
  }
}

resource atlasOrchestratorFailure 'Microsoft.SecurityInsights/alertRules@2023-02-01-preview' = {
  name: guid(workspace.id, 'Atlas-Orchestrator-Failure')
  scope: workspace
  kind: 'Scheduled'
  properties: {
    displayName: 'Atlas: Orchestrator Health Failure'
    description: 'Monitors the Atlas GitHub Actions pipeline for failures requiring manual intervention.'
    severity: 'High'
    enabled: true
    query: '''
      GitHubRepoLogs_CL
      | where status_s == "failure"
      | where workflow_name_s has "Atlas"
      | project TimeGenerated, workflow_name_s, run_id_s, error_message_s
    '''
    queryFrequency: 'PT30M'
    queryPeriod: 'PT30M'
    triggerOperator: 'GreaterThan'
    triggerThreshold: 0
    incidentConfiguration: {
      createIncident: true
      groupingConfiguration: {
        enabled: false
        reopenClosedIncident: false
        lookbackDuration: 'PT5H'
        matchingMethod: 'AllEntities'
      }
    }
    tactics: [
      'Impact'
    ]
  }
}
