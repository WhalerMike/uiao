// App Insights alert rules for the UIAO SaaS plane.
// Covers: failed tenant onboards, slow provisioning, auth failures,
// and service availability.
@description('Resource name prefix.')
param namePrefix string
param location string
param tags object

@description('App Insights resource ID (from monitoring module output).')
param appInsightsId string

@description('Action group resource ID to notify on alert. Leave empty to skip notifications.')
param actionGroupId string = ''

// -----------------------------------------------------------------
// Failed tenant onboards — HTTP 4xx/5xx on POST /control/v1/tenants
// -----------------------------------------------------------------
resource alertFailedOnboards 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: '${namePrefix}-alert-failed-onboards'
  location: 'global'
  tags: tags
  properties: {
    description: 'HTTP 4xx or 5xx responses on POST /control/v1/tenants indicate failed tenant onboards.'
    severity: 1
    enabled: true
    scopes: [ appInsightsId ]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT15M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.MultipleResourceMultipleMetricCriteria'
      allOf: [
        {
          criterionType: 'StaticThresholdCriterion'
          name: 'FailedOnboards'
          metricName: 'requests/failed'
          metricNamespace: 'microsoft.insights/components'
          operator: 'GreaterThan'
          threshold: 0
          timeAggregation: 'Count'
          dimensions: [
            {
              name: 'request/urlPath'
              operator: 'Include'
              values: [ '/control/v1/tenants' ]
            }
          ]
        }
      ]
    }
    actions: empty(actionGroupId) ? [] : [
      { actionGroupId: actionGroupId }
    ]
  }
}

// -----------------------------------------------------------------
// Slow provisioning — average server response time > 10 s
// -----------------------------------------------------------------
resource alertSlowProvisioning 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: '${namePrefix}-alert-slow-provisioning'
  location: 'global'
  tags: tags
  properties: {
    description: 'Average server response time on /control/v1/tenants exceeds 10 seconds — provisioning is degraded.'
    severity: 2
    enabled: true
    scopes: [ appInsightsId ]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT15M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.MultipleResourceMultipleMetricCriteria'
      allOf: [
        {
          criterionType: 'StaticThresholdCriterion'
          name: 'SlowProvisioning'
          metricName: 'requests/duration'
          metricNamespace: 'microsoft.insights/components'
          operator: 'GreaterThan'
          threshold: 10000   // milliseconds
          timeAggregation: 'Average'
          dimensions: [
            {
              name: 'request/urlPath'
              operator: 'Include'
              values: [ '/control/v1/tenants' ]
            }
          ]
        }
      ]
    }
    actions: empty(actionGroupId) ? [] : [
      { actionGroupId: actionGroupId }
    ]
  }
}

// -----------------------------------------------------------------
// Auth failures — HTTP 401 rate > 5 per minute over a 5-minute window
// -----------------------------------------------------------------
resource alertAuthFailures 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: '${namePrefix}-alert-auth-failures'
  location: 'global'
  tags: tags
  properties: {
    description: 'HTTP 401 response rate exceeds 5 per minute — possible token misconfiguration or attack.'
    severity: 1
    enabled: true
    scopes: [ appInsightsId ]
    evaluationFrequency: 'PT1M'
    windowSize: 'PT5M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.MultipleResourceMultipleMetricCriteria'
      allOf: [
        {
          criterionType: 'StaticThresholdCriterion'
          name: 'AuthFailures'
          metricName: 'requests/count'
          metricNamespace: 'microsoft.insights/components'
          operator: 'GreaterThan'
          threshold: 25    // 5/min × 5-minute window
          timeAggregation: 'Count'
          dimensions: [
            {
              name: 'request/resultCode'
              operator: 'Include'
              values: [ '401' ]
            }
          ]
        }
      ]
    }
    actions: empty(actionGroupId) ? [] : [
      { actionGroupId: actionGroupId }
    ]
  }
}

// -----------------------------------------------------------------
// Availability — falls below 99 %
// -----------------------------------------------------------------
resource alertAvailability 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: '${namePrefix}-alert-availability'
  location: 'global'
  tags: tags
  properties: {
    description: 'Service availability dropped below 99 % — SLA breach imminent.'
    severity: 0
    enabled: true
    scopes: [ appInsightsId ]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT1H'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.MultipleResourceMultipleMetricCriteria'
      allOf: [
        {
          criterionType: 'StaticThresholdCriterion'
          name: 'LowAvailability'
          metricName: 'availabilityResults/availabilityPercentage'
          metricNamespace: 'microsoft.insights/components'
          operator: 'LessThan'
          threshold: 99
          timeAggregation: 'Average'
        }
      ]
    }
    actions: empty(actionGroupId) ? [] : [
      { actionGroupId: actionGroupId }
    ]
  }
}

output alertFailedOnboardsId string = alertFailedOnboards.id
output alertSlowProvisioningId string = alertSlowProvisioning.id
output alertAuthFailuresId string = alertAuthFailures.id
output alertAvailabilityId string = alertAvailability.id
